"""
Phase 2 Training: Adaptation Module φ Supervised Learning
=========================================================

Implements Zhang et al. (2025) Section III-D: training the adaptation module φ
to estimate intrinsics from state-action history without ground-truth physics.

Process:
1. Roll out Phase 1 trained policy (π + μ) across randomized environments
2. Collect (state-action history, ground-truth zt) pairs
3. Train φ via MSE loss: L = ||z - ẑ||^2 using Adam optimizer

The adaptation module φ becomes the deployment-time intrinsics estimator,
replacing μ which required ground-truth physics parameters.

Reference: Zhang et al. (2025) Algorithm 2
"""

import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
from collections import deque, defaultdict
from typing import Dict, Tuple, List, Optional
import yaml

from ..models import AdaptationModule, load_actor_critic
from ..envs import F1TenthRMAEnv, PhysicsRandomizer, SampleMode


class AdaptationDataBuffer:
    """
    Episode-structured buffer of (state-action, intrinsics) sequences.

    Windows are only cut from inside a single episode, and each window is
    labelled with the intrinsics at its last step (bugs C8, C9).
    """

    def __init__(self, max_size: int = 1_000_000, window_size: int = 10):
        self.max_size = max_size
        self.window_size = window_size
        self.episodes = deque()      # list of (sa: (T, D) array, z: (T, 8) array, e: (T, 7) array)
        self.size = 0

    def add_episode(self, state_actions, intrinsics, physics=None):
        sa = np.asarray(state_actions, dtype=np.float32)
        z = np.asarray(intrinsics, dtype=np.float32)
        e = np.asarray(physics, dtype=np.float32) if physics is not None else np.zeros((len(sa), 7), np.float32)
        if len(sa) < self.window_size:
            return
        self.episodes.append((sa, z, e))
        self.size += len(sa)
        while self.size > self.max_size and len(self.episodes) > 1:
            old = self.episodes.popleft()
            self.size -= len(old[0])

    def get_batch(self, batch_size: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Returns:
            histories: (batch_size, window_size, state_action_dim)
            intrinsics: (batch_size, 8): label at the window's last step
            physics: (batch_size, 7): raw e at the window's last step
        """
        if not self.episodes:
            raise RuntimeError("Not enough data in buffer for window_size")
        # Sample episodes proportionally to their number of valid windows
        n_windows = np.array([len(ep[0]) - self.window_size + 1 for ep in self.episodes])
        ep_idx = np.random.choice(len(self.episodes), size=batch_size, p=n_windows / n_windows.sum())
        histories, labels, phys = [], [], []
        for i in ep_idx:
            sa, z, e = self.episodes[i]
            start = np.random.randint(0, len(sa) - self.window_size + 1)
            end = start + self.window_size
            histories.append(sa[start:end])
            labels.append(z[end - 1])
            phys.append(e[end - 1])
        return (torch.from_numpy(np.stack(histories)),
                torch.from_numpy(np.stack(labels)),
                torch.from_numpy(np.stack(phys)))

    def __len__(self) -> int:
        return self.size


class Phase2Trainer:
    """
    Supervised training for adaptation module φ.
    
    Reference: Zhang et al. (2025) Section III-D
    """
    
    def __init__(
        self,
        actor_critic_checkpoint: str,
        config: Dict,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        log_dir: str = 'logs/phase2',
        checkpoint_dir: str = 'checkpoints/phase2',
    ):
        """
        Initialize Phase 2 trainer.
        
        Args:
            actor_critic_checkpoint: Path to Phase 1 trained model
            config: Configuration dictionary
            device: 'cuda' or 'cpu'
            log_dir: Directory for TensorBoard logs
            checkpoint_dir: Directory for checkpoints
        """
        self.device = torch.device(device)
        self.config = config
        self.log_dir = log_dir
        self.checkpoint_dir = checkpoint_dir
        
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # Load Phase 1 trained policy
        # sized from the checkpoint itself (bug C10)
        self.actor_critic, _ = load_actor_critic(actor_critic_checkpoint, self.device)
        
        # Initialize adaptation module
        phase2_config = config.get('phase2_training', {})
        adaptation_config = config.get('networks', {}).get('adaptation', {})
        
        self.adaptation = AdaptationModule(
            state_action_dim=adaptation_config.get('state_action_dim', 7),
            history_window=adaptation_config.get('history_window', 10),
            intrinsics_dim=adaptation_config.get('intrinsics_dim', 8),
        ).to(self.device)
        
        # Optional auxiliary head: predict the raw physics vector e from ẑ,
        # weighted per parameter (final config weights grip 3×). This keeps
        # grip information from being washed out by the 7 other latent dims.
        # Reconstructed from the phase2_crashtol config keys; the head is
        # saved under 'aux_head' and is not needed at deployment.
        self.aux_weight = float(phase2_config.get('aux_loss_weight', 0.0))
        self.aux_param_weights = torch.tensor(
            phase2_config.get('aux_param_weights', [1.0] * 7), dtype=torch.float32, device=self.device)
        self.aux_head = nn.Linear(adaptation_config.get('intrinsics_dim', 8), 7).to(self.device)
        params = list(self.adaptation.parameters())
        if self.aux_weight > 0:
            params += list(self.aux_head.parameters())

        # Optimizer
        self.optimizer = optim.Adam(
            params,
            lr=phase2_config.get('learning_rate', 1.0e-3),
        )
        
        # Data buffer
        self.buffer = AdaptationDataBuffer(
            max_size=phase2_config.get('buffer_size', 1_000_000),
            window_size=adaptation_config.get('history_window', 10),
        )
        
        # Environment
        self.env = F1TenthRMAEnv(config=config)
        
        # Logging
        self.writer = SummaryWriter(log_dir)
        self.global_step = 0
        self.metrics = defaultdict(list)
    
    def _true_intrinsics(self, info) -> torch.Tensor:
        e = torch.as_tensor(info['physics_vector'], dtype=torch.float32, device=self.device)
        return self.actor_critic.get_intrinsics(e)

    def collect_data(self, num_episodes: int):
        """
        Collect state-action-intrinsics data by rolling out the Phase 1 policy
        with ground-truth intrinsics. Labels track mid-episode grip drops,
        because info['physics_vector'] reflects the physics actually applied.

        phase2_training.num_envs > 1 runs that many simulators in parallel
        (training/env_pool.py); each env's episodes are kept separate.
        """
        n = int(self.config.get('phase2_training', {}).get('num_envs', 1))
        print(f"[Data Collection] Collecting {num_episodes} episodes with {n} env(s)...")
        if n > 1:
            return self._collect_parallel(num_episodes, n)

        with torch.no_grad():
            for episode in range(num_episodes):
                obs, info = self.env.reset(options={'training': True})
                done = False
                sa_seq, z_seq, e_seq = [], [], []

                while not done:
                    obs_tensor = torch.as_tensor(obs, dtype=torch.float32, device=self.device)
                    intrinsics = self._true_intrinsics(info)
                    mean, _ = self.actor_critic.policy(obs_tensor, intrinsics)
                    action = mean.cpu().numpy()

                    sa_seq.append(np.concatenate([obs, action]))
                    z_seq.append(intrinsics.cpu().numpy())
                    e_seq.append(info['physics_vector'])

                    obs, reward, terminated, truncated, info = self.env.step(action)
                    done = terminated or truncated

                self.buffer.add_episode(sa_seq, z_seq, e_seq)

                if (episode + 1) % max(1, num_episodes // 10) == 0:
                    print(f"  Episode {episode + 1}/{num_episodes}, Buffer size: {len(self.buffer)}", flush=True)

        print(f"[Data Collection] Complete. Buffer has {len(self.buffer)} transitions")

    def _collect_parallel(self, num_episodes: int, n: int):
        from .env_pool import make_pool
        cfg = dict(self.config)
        cfg['phase1_training'] = dict(cfg.get('phase1_training', {}), il={'use_expert_actions': False})
        pool = make_pool(cfg, n, seed=int(self.config.get('phase2_training', {}).get('seed', 12345)))
        obs, infos, _ = pool.reset()
        seqs = [([], [], []) for _ in range(n)]
        done_eps = 0
        report = max(1, num_episodes // 10)
        with torch.no_grad():
            while done_eps < num_episodes:
                e = torch.from_numpy(np.stack([inf['physics_vector'] for inf in infos])).to(self.device)
                z = self.actor_critic.get_intrinsics(e)
                mean, _ = self.actor_critic.policy(torch.from_numpy(obs).to(self.device), z)
                act = mean.cpu().numpy()
                zn = z.cpu().numpy()
                for i in range(n):
                    seqs[i][0].append(np.concatenate([obs[i], act[i]]))
                    seqs[i][1].append(zn[i])
                    seqs[i][2].append(infos[i]['physics_vector'])
                obs, _, dones, infos, _, _ = pool.step(act)
                for i in np.where(dones > 0)[0]:
                    if done_eps < num_episodes:
                        self.buffer.add_episode(*seqs[i])
                        done_eps += 1
                        if done_eps % report == 0:
                            print(f"  Episode {done_eps}/{num_episodes}, Buffer size: {len(self.buffer)}", flush=True)
                    seqs[i] = ([], [], [])
        pool.close()
        print(f"[Data Collection] Complete. Buffer has {len(self.buffer)} transitions")

    def train_epoch(self, num_epochs: int, batch_size: int):
        """
        Train adaptation module for multiple epochs.
        
        Args:
            num_epochs: Number of training epochs
            batch_size: Batch size for SGD
        """
        loss_fn = nn.MSELoss()
        
        for epoch in range(num_epochs):
            epoch_loss = 0.0
            num_batches = 0
            
            # Mini-batch training (optionally capped by phase2_training.max_grad_steps:
            # 100 full epochs over a 2M-transition buffer is ~780k steps, fine on
            # a GPU but ~30 h on a 4-core CPU)
            max_steps = int(self.config.get('phase2_training', {}).get('max_grad_steps', 0))
            if max_steps and self.global_step >= max_steps:
                print(f"[Training] reached max_grad_steps={max_steps}", flush=True)
                break
            while num_batches < len(self.buffer) // batch_size:
                if max_steps and self.global_step >= max_steps:
                    break
                if num_batches and num_batches % 1000 == 0:
                    print(f"  [Epoch {epoch}] step {self.global_step}: running loss {epoch_loss / num_batches:.6f}", flush=True)
                try:
                    histories, intrinsics, physics = self.buffer.get_batch(batch_size)
                except RuntimeError:
                    # Not enough data yet
                    break
                
                histories = histories.to(self.device)
                intrinsics = intrinsics.to(self.device)
                physics = physics.to(self.device)
                
                # Forward pass
                estimated_intrinsics = self.adaptation(histories)
                loss = loss_fn(estimated_intrinsics, intrinsics)
                if self.aux_weight > 0:
                    pred_e = self.aux_head(estimated_intrinsics)
                    aux = (self.aux_param_weights * (pred_e - physics) ** 2).mean()
                    loss = loss + self.aux_weight * aux
                
                # Backward pass
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                
                epoch_loss += loss.item()
                num_batches += 1
                self.global_step += 1
            
            if num_batches > 0:
                avg_loss = epoch_loss / num_batches
                print(f"[Epoch {epoch}] Loss: {avg_loss:.6f} (step {self.global_step})", flush=True)
                self.writer.add_scalar('train/mse_loss', avg_loss, self.global_step)
            # Data collection alone takes hours: never lose a run to a crash
            # late in training. Overwritten each time (one file, not per epoch).
            if (epoch + 1) % 10 == 0:
                self.save_checkpoint('latest.pt')
    
    def evaluate(self, num_episodes: int = 50) -> Dict[str, float]:
        """
        Evaluate adaptation module on held-out test episodes.
        
        Compares estimated intrinsics ẑ vs ground-truth z.
        
        Args:
            num_episodes: Number of test episodes
            
        Returns:
            Dictionary with evaluation metrics
        """
        print(f"[Evaluation] Evaluating on {num_episodes} test episodes...")
        
        errors = []
        
        with torch.no_grad():
            for episode in range(num_episodes):
                obs, info = self.env.reset(options={'training': True})
                done = False
                
                # Build state-action history
                history = deque(maxlen=self.buffer.window_size)
                
                while not done:
                    obs_tensor = torch.from_numpy(obs if isinstance(obs, np.ndarray) else np.array(obs)).float().to(self.device)
                    
                    ground_truth_z = self._true_intrinsics(info)
                    
                    # Get action
                    mean, _ = self.actor_critic.policy(obs_tensor, ground_truth_z)
                    action = mean
                    
                    # Build history
                    state_action = np.concatenate([obs, action.cpu().numpy()])
                    history.append(state_action)
                    
                    # Estimate intrinsics if history is full
                    if len(history) == self.buffer.window_size:
                        hist_tensor = torch.from_numpy(np.stack(history)).unsqueeze(0).float().to(self.device)
                        estimated_z = self.adaptation(hist_tensor).squeeze(0)
                        
                        # Compute error
                        error = torch.norm(estimated_z - ground_truth_z).item()
                        errors.append(error)
                    
                    # Step environment
                    obs, reward, terminated, truncated, info = self.env.step(action.cpu().numpy())
                    done = terminated or truncated
        
        metrics = {
            'mean_error': np.mean(errors) if len(errors) > 0 else float('inf'),
            'std_error': np.std(errors) if len(errors) > 0 else 0.0,
            'min_error': np.min(errors) if len(errors) > 0 else 0.0,
            'max_error': np.max(errors) if len(errors) > 0 else 0.0,
        }
        
        print(f"[Evaluation] Mean error: {metrics['mean_error']:.6f}")
        for key, val in metrics.items():
            self.writer.add_scalar(f'eval/{key}', val, self.global_step)
        
        return metrics
    
    def train(self):
        """
        Main Phase 2 training loop.
        
        1. Collect data from Phase 1 policy
        2. Train adaptation module φ
        3. Evaluate and save checkpoints
        """
        phase2_config = self.config.get('phase2_training', {})
        
        # Data collection
        num_eval_episodes = phase2_config.get('num_eval_episodes', 500)
        self.collect_data(num_eval_episodes)
        
        # Training
        num_epochs = phase2_config.get('num_epochs', 100)
        batch_size = phase2_config.get('batch_size', 64)
        
        print(f"[Training] Training for {num_epochs} epochs with batch size {batch_size}...")
        self.train_epoch(num_epochs, batch_size)
        
        # Evaluation
        print("[Training] Evaluating...")
        metrics = self.evaluate()
        
        # Save final model
        self.save_checkpoint('final.pt')
        
        print("[Training Complete] Phase 2 training finished")
    
    def save_checkpoint(self, filename: str):
        """Save adaptation module checkpoint."""
        path = os.path.join(self.checkpoint_dir, filename)
        torch.save({
            'adaptation': self.adaptation.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'global_step': self.global_step,
            'aux_head': self.aux_head.state_dict(),
            'config': self.config,
        }, path)
        print(f"Checkpoint saved to {path}")
    
    def load_checkpoint(self, filename: str):
        """Load adaptation module checkpoint."""
        path = os.path.join(self.checkpoint_dir, filename)
        checkpoint = torch.load(path, map_location=self.device, weights_only=True)
        self.adaptation.load_state_dict(checkpoint['adaptation'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.global_step = checkpoint['global_step']
        print(f"Checkpoint loaded from {path}")


def main():
    """Entry point for Phase 2 training."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 2 Training: Adaptation Module')
    parser.add_argument('--phase1_checkpoint', type=str, required=True,
                       help='Path to Phase 1 trained model')
    parser.add_argument('--config', type=str, default='configs/rma_config.yaml',
                       help='Path to config YAML')
    parser.add_argument('--tire_model', type=str, default=None, choices=['linear', 'friction_circle'],
                        help="override environment.tire_model in the config (default: config's, else linear)")
    parser.add_argument('--device', type=str, default='auto',
                       help='Device: cuda, cpu, or auto')
    parser.add_argument('--log_dir', type=str, default='logs/phase2')
    parser.add_argument('--checkpoint_dir', type=str, default='checkpoints/phase2')
    parser.add_argument('--num_envs', type=int, default=None,
                        help='parallel simulators for data collection (phase2_training.num_envs)')
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    if args.tire_model:
        config.setdefault('environment', {})['tire_model'] = args.tire_model
    print(f"Tire model: {config.get('environment', {}).get('tire_model', 'linear')}")
    if args.num_envs:
        config.setdefault('phase2_training', {})['num_envs'] = args.num_envs
    torch.set_num_threads(int(os.environ.get('TORCH_THREADS', '4')))

    # Determine device
    if args.device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    else:
        device = args.device
    
    print(f"Training on device: {device}")
    
    # Create trainer and train
    trainer = Phase2Trainer(args.phase1_checkpoint, config, device=device,
                            log_dir=args.log_dir, checkpoint_dir=args.checkpoint_dir)
    trainer.train()


if __name__ == '__main__':
    main()
