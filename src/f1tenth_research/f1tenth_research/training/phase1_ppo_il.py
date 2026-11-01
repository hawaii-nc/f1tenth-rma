"""
Phase 1 Training: PPO + IL Joint Training
==========================================

Implements Zhang et al. (2025) Section II-D: combined RL + IL training loop.

Key components:
- PPO (Proximal Policy Optimization) for reinforcement learning
- Imitation Learning loss L_IL(π) = ||a_exp - a||^2
- Joint objective: R(π) = (1-α)·R_RL(π) - α·L_IL(π)
- Exponentially decaying IL weight: α = exp(-decay * t_epoch)

Architecture:
- Parallel environment rollouts (num_envs environments)
- Generalized Advantage Estimation (GAE) for variance reduction
- Clipped surrogate objective for PPO stability
- Shared encoder backbone (π, V, μ per Zhang)

Training scale: ~100M timesteps (scale to F1Tenth hardware/sim speed)
"""

import os
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
from typing import Dict, Tuple, Optional, List
import warnings
from collections import defaultdict
import yaml

from ..envs import F1TenthRMAEnv, PhysicsRandomizer, SampleMode
from ..models import RMAActorCritic, PolicyNetwork, IntrinsicsEncoder, ValueNetwork
from ..experts import PurePursuitExpert
from ..paths import centerline_path, raceline_path
from ..envs.reward import RewardComputer
from .env_pool import create_experts, expert_action, make_pool


class Phase1Trainer:
    """
    PPO + IL joint training for RMA policy.
    
    Reference: Zhang et al. (2025) Section II-D, Algorithm 1
    """
    
    def __init__(
        self,
        config: Dict,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        log_dir: str = 'logs/phase1',
        checkpoint_dir: str = 'checkpoints/phase1',
    ):
        """
        Initialize Phase 1 trainer.
        
        Args:
            config: Configuration dictionary (from YAML)
            device: 'cuda' or 'cpu'
            log_dir: Directory for TensorBoard logs
            checkpoint_dir: Directory for model checkpoints
        """
        self.config = config
        self.device = torch.device(device)
        self.log_dir = log_dir
        self.checkpoint_dir = checkpoint_dir
        
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # Initialize environments and components
        self.env_config = config.get('environment', {})
        self.training_config = config.get('phase1_training', {})
        self.expert_config = config.get('expert', {})
        
        # Determine training scale
        if self.training_config.get('debug_mode', False):
            self.total_timesteps = self.training_config.get('debug_timesteps', 100_000)
            print(f"[DEBUG MODE] Using {self.total_timesteps} timesteps")
        else:
            self.total_timesteps = self.training_config.get('total_timesteps', 100_000_000)
        
        # Full seeding: main-process numpy/torch (network init, DAgger mixing,
        # exploration noise); workers are seeded seed + 1000·i in env_pool.
        seed = int(self.training_config.get('seed', 0))
        np.random.seed(seed)
        torch.manual_seed(seed)
        # Robust (domain-randomization) baseline: the encoder only ever sees the
        # nominal physics vector, so π gets no grip information (RMA's "robust" baseline).
        self.blind_intrinsics = bool(self.training_config.get('blind_intrinsics', False))
        self._nominal_e = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0], np.float32)

        # Environment pool: one simulator per worker (num_envs), auto-reset,
        # per-env expert labels and physics. State persists across rollouts.
        self.num_envs = int(self.training_config.get('num_envs', 1))
        self.pool = make_pool(config, self.num_envs, seed=int(self.training_config.get('seed', 0)))
        self._obs, self._infos, self._experts = self.pool.reset()
        self.obs_dim = self._obs.shape[1]
        self.action_dim = 2
        self.env_params_dim = 7
        self.episode_stats = []

        # Initialize networks
        self.actor_critic = RMAActorCritic(
            obs_dim=self.obs_dim,
            action_dim=self.action_dim,
            intrinsics_dim=8,
            env_params_dim=self.env_params_dim,
        ).to(self.device)
        
        # Initialize expert controller
        self.expert = self._create_expert()

        # Adaptive IL rescue state
        self._reward_history = []       # rolling epoch rewards
        self._rescue_count = 0          # how many rescues triggered
        self._rescue_epoch = -999       # last epoch rescue triggered
        self._rescue_il_weight = 0.0    # current rescue boost (0 = not in rescue)
        
        # Optimizers
        ppo_config = self.training_config.get('ppo', {})
        self.optimizer = optim.Adam(
            self.actor_critic.parameters(),
            lr=ppo_config.get('learning_rate', 3.0e-4),
        )
        
        # Logging
        self.writer = SummaryWriter(log_dir)
        self.global_step = 0
        self.global_episode = 0
        self.epoch = 0
        self.metrics = defaultdict(list)
    
    def _create_expert(self):
        return create_experts(self.config)

    def compute_gae(
        self,
        rewards: np.ndarray,
        values: np.ndarray,
        next_value: float,
        dones: np.ndarray,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute Generalized Advantage Estimation (GAE) with episode masking.
        
        Args:
            rewards: Rewards received, shape (rollout_steps,)
            values: State values, shape (rollout_steps,)
            next_value: Bootstrap value after the final step
            dones: 1.0 if a step ended the episode, else 0.0
            gamma: Discount factor
            gae_lambda: GAE decay parameter
            
        Returns:
            Tuple of:
            - advantages: Computed advantages
            - returns: Cumulative returns (values + advantages)
        """
        advantages = np.zeros_like(rewards)
        gae = 0.0
        
        for step in reversed(range(len(rewards))):
            if step == len(rewards) - 1:
                next_val = next_value
            else:
                next_val = values[step + 1]
            
            mask = 1.0 - dones[step]
            delta = rewards[step] + gamma * next_val * mask - values[step]
            gae = delta + gamma * gae_lambda * mask * gae
            advantages[step] = gae
        
        returns = advantages + values
        return advantages, returns
    
    def get_expert_action(self, info: Dict) -> Optional[np.ndarray]:
        """Expert action from the privileged pose in info (bug C5: never from obs)."""
        return expert_action(self.expert, info)

    def _encoder_input(self, infos) -> np.ndarray:
        """Physics vectors fed to μ (all nominal when blind_intrinsics)."""
        e = np.stack([inf['physics_vector'] for inf in infos]).astype(np.float32)
        if self.blind_intrinsics:
            e[:] = self._nominal_e
        return e

    def rollout(self, num_steps: int) -> Dict:
        """
        Collect about num_steps transitions (num_steps // num_envs per env).

        Episodes continue across rollouts (no forced reset). GAE runs per env,
        bootstrapping each env from its own last observation. Each transition's
        intrinsics come from that env's physics, and its imitation label from
        that env's expert at that state (NaN + mask where no expert exists).
        """
        n = self.num_envs
        T = max(1, num_steps // n)
        obs_buf = np.zeros((T, n, self.obs_dim), np.float32)
        act_buf = np.zeros((T, n, self.action_dim), np.float32)
        logp_buf = np.zeros((T, n), np.float32)
        val_buf = np.zeros((T, n), np.float32)
        rew_buf = np.zeros((T, n), np.float32)
        done_buf = np.zeros((T, n), np.float32)
        intr_buf = np.zeros((T, n, 8), np.float32)
        phys_buf = np.zeros((T, n, 7), np.float32)
        exp_buf = np.full((T, n, self.action_dim), np.nan, np.float32)

        obs, infos, experts = self._obs, self._infos, self._experts
        with torch.no_grad():
            for t in range(T):
                e = torch.from_numpy(self._encoder_input(infos)).to(self.device)
                intr = self.actor_critic.get_intrinsics(e)
                obs_t = torch.from_numpy(obs).to(self.device)
                a, lp, _, v, _ = self.actor_critic.get_action_and_value(obs_t, intr)
                obs_buf[t], act_buf[t] = obs, a.cpu().numpy()
                logp_buf[t], val_buf[t] = lp.cpu().numpy(), v.reshape(-1).cpu().numpy()
                intr_buf[t] = intr.cpu().numpy()
                phys_buf[t] = e.cpu().numpy()
                for i, ea in enumerate(experts):
                    if ea is not None:
                        exp_buf[t, i] = ea
                env_action = torch.clamp(a, -1.0, 1.0).cpu().numpy()
                obs, rew_buf[t], done_buf[t], infos, experts, finished = self.pool.step(env_action)
                self.episode_stats.extend(finished)
                self.global_step += n

            e = torch.from_numpy(self._encoder_input(infos)).to(self.device)
            next_values = self.actor_critic.value(torch.from_numpy(obs).to(self.device),
                                                  self.actor_critic.get_intrinsics(e)).reshape(-1).cpu().numpy()
        self._obs, self._infos, self._experts = obs, infos, experts

        ppo_config = self.training_config.get('ppo', {})
        adv = np.zeros((T, n), np.float32)
        ret = np.zeros((T, n), np.float32)
        for i in range(n):
            adv[:, i], ret[:, i] = self.compute_gae(
                rew_buf[:, i], val_buf[:, i], float(next_values[i]), done_buf[:, i],
                gamma=ppo_config.get('gamma', 0.99), gae_lambda=ppo_config.get('gae_lambda', 0.95))

        def flat(x):  # env-major: each env's trajectory stays contiguous
            return np.ascontiguousarray(np.swapaxes(x, 0, 1).reshape(n * T, *x.shape[2:]))

        exp_flat = flat(exp_buf)
        mask = ~np.isnan(exp_flat).any(axis=1)
        return {
            'obs': flat(obs_buf), 'actions': flat(act_buf), 'log_probs': flat(logp_buf),
            'values': flat(val_buf), 'rewards': flat(rew_buf), 'dones': flat(done_buf),
            'intrinsics': flat(intr_buf), 'physics': flat(phys_buf), 'advantages': flat(adv), 'returns': flat(ret),
            'expert_actions': np.nan_to_num(exp_flat), 'expert_mask': mask,
        }

    def dagger_pretrain(self):
        """
        DAgger pre-training of π and μ before PPO (phase1_training.dagger).

        Iteration k: the pool drives with the expert's action with probability
        β_k = beta0 · decay^k per step (else the policy's mean + exploration
        noise); every visited state is labelled with the expert's action; π and
        μ are trained by MSE on the aggregated dataset. Pure IL inside PPO only
        ever saw the first metres of each track plus crash states (the policy
        crashed within ~100 steps), and plain behaviour cloning drifts off the
        expert's state distribution; DAgger fixes both (Ross et al., 2011).
        """
        dc = self.training_config.get('dagger', {})
        iters = int(dc.get('iterations', 0))
        if iters <= 0 or self.epoch > 0 or getattr(self, '_dagger_done', False):
            return
        steps = int(dc.get('steps_per_iter', 50_000))
        beta0, decay = float(dc.get('beta0', 1.0)), float(dc.get('beta_decay', 0.5))
        noise = float(dc.get('action_noise', 0.1))
        epochs, bs = int(dc.get('epochs', 10)), int(dc.get('batch_size', 512))
        n = self.num_envs
        X, E, Y = [], [], []
        opt = optim.Adam(list(self.actor_critic.policy.parameters()) +
                         list(self.actor_critic.encoder.parameters()), lr=float(dc.get('learning_rate', 3e-4)))
        obs, infos, experts = self._obs, self._infos, self._experts
        for k in range(iters):
            beta = beta0 * decay ** k
            for _ in range(max(1, steps // n)):
                e = self._encoder_input(infos)
                with torch.no_grad():
                    mean, _ = self.actor_critic.policy(torch.from_numpy(obs).to(self.device),
                                                       self.actor_critic.get_intrinsics(torch.from_numpy(e).to(self.device)))
                act = mean.cpu().numpy() + np.random.normal(0, noise, size=(n, 2))
                for i, ea in enumerate(experts):
                    if ea is not None:
                        X.append(obs[i]); E.append(e[i]); Y.append(ea)
                        if np.random.rand() < beta:
                            act[i] = ea + np.random.normal(0, noise, size=2)
                obs, _, _, infos, experts, finished = self.pool.step(np.clip(act, -1, 1).astype(np.float32))
                self.episode_stats.extend(finished)
            Xt = torch.from_numpy(np.array(X, np.float32)).to(self.device)
            Et = torch.from_numpy(np.array(E, np.float32)).to(self.device)
            Yt = torch.from_numpy(np.array(Y, np.float32)).to(self.device)
            for _ in range(epochs):
                perm = torch.randperm(len(Xt))
                for j in range(0, len(Xt), bs):
                    b = perm[j:j + bs]
                    mu, _ = self.actor_critic.policy(Xt[b], self.actor_critic.get_intrinsics(Et[b]))
                    loss = ((mu - Yt[b]) ** 2).mean()
                    opt.zero_grad(); loss.backward(); opt.step()
            eps, self.episode_stats = self.episode_stats, []
            crash = np.mean([x['crash'] for x in eps]) if eps else float('nan')
            ln = np.mean([x['length'] for x in eps]) if eps else float('nan')
            print(f"[DAgger {k}] beta={beta:.3f} dataset={len(X)} bc_mse={loss.item():.4f} | "
                  f"episodes={len(eps)} crash_rate={crash:.2f} mean_len={ln:.0f}", flush=True)
            self.writer.add_scalar('dagger/bc_mse', loss.item(), k)
        self._obs, self._infos, self._experts = obs, infos, experts
        # PPO's exploration std starts at DAgger's noise level: the default
        # (exp(-0.5) = 0.6 rad) exceeds the whole steering range and would undo DAgger.
        with torch.no_grad():
            self.actor_critic.policy.log_std.fill_(float(np.log(noise)))
        self._dagger_done = True
        self.save_checkpoint('dagger.pt')

    def update(self, rollout_data: Dict, epoch: int):
        """
        Update policy and value function using collected rollout.
        
        Implements:
        - PPO clipped surrogate objective for a Gaussian policy
        - IL loss for imitation: L_IL(π) = ||a_exp - mean||^2
        - α = exp(-decay * epoch)
        
        Args:
            rollout_data: Data from rollout()
            epoch: Current training epoch
        """
        # Compute IL weight: exponential decay + adaptive rescue
        il_config = self.training_config.get('il', {})
        il_decay = il_config.get('il_weight_decay', 0.001)
        il_weight_start = il_config.get('il_weight_start', 1.0)
        il_weight_end = il_config.get('il_weight_end', 0.01)

        # Standard exponential decay (Zhang et al.)
        base_il_weight = il_weight_start * np.exp(-il_decay * epoch)
        base_il_weight = max(base_il_weight, il_weight_end)

        # Rescue parameters
        rescue_config = il_config.get('rescue', {})
        plateau_window = rescue_config.get('plateau_window', 50)
        plateau_threshold = rescue_config.get('plateau_threshold', 0.01)
        rescue_weight = rescue_config.get('rescue_il_weight', 0.3)
        rescue_decay = rescue_config.get('rescue_decay', 0.05)
        max_rescues = rescue_config.get('max_rescues', 3)

        # Check for plateau and trigger rescue if needed
        if (len(self._reward_history) >= plateau_window * 2
                and self._rescue_count < max_rescues
                and epoch - self._rescue_epoch > plateau_window):
            recent = np.mean(self._reward_history[-plateau_window:])
            prior = np.mean(self._reward_history[-plateau_window*2:-plateau_window])
            improvement = recent - prior
            if improvement < plateau_threshold:
                self._rescue_count += 1
                self._rescue_epoch = epoch
                self._rescue_il_weight = rescue_weight
                print(f"[IL RESCUE #{self._rescue_count}] Plateau detected "
                      f"(improvement={improvement:.4f} < {plateau_threshold}). "
                      f"Boosting IL weight to {rescue_weight:.3f}")

        # Decay rescue weight if active
        if self._rescue_il_weight > il_weight_end:
            epochs_since_rescue = epoch - self._rescue_epoch
            self._rescue_il_weight = rescue_weight * np.exp(
                -rescue_decay * epochs_since_rescue
            )
            self._rescue_il_weight = max(self._rescue_il_weight, 0.0)

        # Final IL weight: max of base decay and active rescue
        il_weight = max(base_il_weight, self._rescue_il_weight)
        
        batch_size = self.training_config.get('batch_size', 256)
        num_epochs = self.training_config.get('num_epochs', 10)
        ppo_config = self.training_config.get('ppo', {})
        clip_eps = ppo_config.get('clip_eps', ppo_config.get('clip_ratio', 0.2))
        value_coeff = ppo_config.get('value_coeff', 0.5)
        entropy_coeff = ppo_config.get('entropy_coeff', 0.01)
        max_grad_norm = ppo_config.get('max_grad_norm', 0.5)
        
        # Convert rollout data to tensors
        obs_tensor = torch.from_numpy(np.array(rollout_data['obs'])).float().to(self.device)
        actions_tensor = torch.from_numpy(np.array(rollout_data['actions'])).float().to(self.device)
        returns_tensor = torch.from_numpy(np.asarray(rollout_data['returns'])).float().to(self.device)
        advantages_tensor = torch.from_numpy(np.asarray(rollout_data['advantages'])).float().to(self.device)
        intrinsics_tensor = torch.from_numpy(np.array(rollout_data['intrinsics'])).float().to(self.device)
        # Recompute μ(e) inside the loss so the encoder is trained with π (bug C21:
        # stored, detached intrinsics meant μ never received a gradient).
        physics_tensor = (torch.from_numpy(np.asarray(rollout_data['physics'])).float().to(self.device)
                          if 'physics' in rollout_data else None)
        old_log_probs_tensor = torch.from_numpy(np.array(rollout_data['log_probs'])).float().to(self.device)

        expert_actions_tensor = None
        expert_mask_tensor = None
        if il_config.get('enabled', False) and len(rollout_data['expert_actions']) == len(rollout_data['obs']):
            expert_actions_tensor = torch.from_numpy(np.array(rollout_data['expert_actions'])).float().to(self.device)
            mask = rollout_data.get('expert_mask')
            mask = np.ones(len(rollout_data['obs']), bool) if mask is None else np.asarray(mask, bool)
            if not mask.any():
                raise RuntimeError('IL is enabled but no transition has an expert action '
                                   '(lesson: a missing imitation signal must be loud)')
            expert_mask_tensor = torch.from_numpy(mask.astype(np.float32)).to(self.device)
        self._last_il_weight = il_weight
        
        # Normalize advantages
        advantages_tensor = (advantages_tensor - advantages_tensor.mean()) / (advantages_tensor.std() + 1e-8)
        
        # Training epochs
        for epoch_i in range(num_epochs):
            # Mini-batch updates
            indices = np.random.permutation(len(obs_tensor))
            
            for start_idx in range(0, len(obs_tensor), batch_size):
                batch_indices = indices[start_idx:start_idx + batch_size]
                
                obs_batch = obs_tensor[batch_indices]
                actions_batch = actions_tensor[batch_indices]
                returns_batch = returns_tensor[batch_indices]
                advantages_batch = advantages_tensor[batch_indices]
                intrinsics_batch = (self.actor_critic.get_intrinsics(physics_tensor[batch_indices])
                                    if physics_tensor is not None else intrinsics_tensor[batch_indices])
                old_log_probs_batch = old_log_probs_tensor[batch_indices]
                
                mean_batch, log_std_batch = self.actor_critic.policy(obs_batch, intrinsics_batch)
                std_batch = torch.exp(log_std_batch)
                dist = torch.distributions.Normal(mean_batch, std_batch)
                new_log_probs = dist.log_prob(actions_batch).sum(dim=-1)
                entropy = dist.entropy().sum(dim=-1).mean()
                values = self.actor_critic.value(obs_batch, intrinsics_batch)

                ratio = torch.exp(new_log_probs - old_log_probs_batch)
                surr1 = ratio * advantages_batch
                surr2 = torch.clamp(ratio, 1.0 - clip_eps, 1.0 + clip_eps) * advantages_batch
                policy_loss = -torch.min(surr1, surr2).mean()
                value_loss = ((values - returns_batch) ** 2).mean()
                
                il_loss = torch.tensor(0.0, device=self.device)
                if expert_actions_tensor is not None:
                    expert_actions_batch = expert_actions_tensor[batch_indices]
                    m = expert_mask_tensor[batch_indices]
                    per = ((mean_batch - expert_actions_batch) ** 2).mean(dim=-1)
                    il_loss = (per * m).sum() / m.sum().clamp(min=1.0)
                
                # Combined loss
                total_loss = policy_loss + value_coeff * value_loss - entropy_coeff * entropy
                
                if il_config.get('enabled', False):
                    total_loss += il_weight * il_loss
                if epoch < int(self.training_config.get('value_warmup_epochs', 0)):
                    # Fit V to the (DAgger-initialised) policy before letting PPO move π
                    total_loss = value_coeff * value_loss
                
                # Backward pass
                self.optimizer.zero_grad()
                total_loss.backward()
                
                grad_norm = nn.utils.clip_grad_norm_(
                    self.actor_critic.parameters(),
                    max_grad_norm
                )
                
                self.optimizer.step()

                with torch.no_grad():
                    clip_fraction = ((ratio - 1.0).abs() > clip_eps).float().mean()
                    approx_kl = (old_log_probs_batch - new_log_probs).mean()
                
                # Log metrics
                self.metrics['policy_loss'].append(policy_loss.item())
                self.metrics['value_loss'].append(value_loss.item())
                self.metrics['entropy'].append(entropy.item())
                self.metrics['clip_fraction'].append(clip_fraction.item())
                self.metrics['approx_kl'].append(approx_kl.item())
                if il_config.get('enabled', False):
                    self.metrics['il_loss'].append(il_loss.item())
                self.metrics['grad_norm'].append(grad_norm.item())
    
    def train(self):
        """
        Main training loop (Phase 1): rollout -> PPO + IL update -> log -> checkpoint.
        Resumable: load_checkpoint() restores the epoch, IL schedule and step count.
        """
        rollout_steps = self.training_config.get('rollout_steps', 2048)
        checkpoint_interval = self.training_config.get('checkpoint_interval', 10)
        log_interval = self.training_config.get('log_interval', 100)

        self.dagger_pretrain()
        while self.global_step < self.total_timesteps:
            epoch = self.epoch
            t0 = time.time()
            rollout_data = self.rollout(rollout_steps)
            t1 = time.time()
            self.update(rollout_data, epoch)
            t2 = time.time()

            if epoch % log_interval == 0:
                avg_reward = float(np.mean(rollout_data['rewards'])) if len(rollout_data['rewards']) else 0.0
                self._reward_history.append(avg_reward)  # track for adaptive IL rescue
                eps, self.episode_stats = self.episode_stats, []
                if eps:
                    crash = np.mean([e['crash'] for e in eps])
                    ep_len = np.mean([e['length'] for e in eps])
                    self.writer.add_scalar('episodes/crash_rate', crash, self.global_step)
                    self.writer.add_scalar('episodes/length', ep_len, self.global_step)
                    ep_txt = f"episodes={len(eps)} crash_rate={crash:.2f} mean_len={ep_len:.0f}"
                else:
                    ep_txt = "episodes=0"
                sps = len(rollout_data['rewards']) / max(t1 - t0, 1e-6)
                print(f"[Epoch {epoch}] Step {self.global_step}: Avg Reward = {avg_reward:.3f} | {ep_txt} | "
                      f"IL w={getattr(self, '_last_il_weight', 0.0):.3f} | {sps:.0f} steps/s, update {t2 - t1:.0f}s",
                      flush=True)
                self.writer.add_scalar('train/avg_reward', avg_reward, self.global_step)
                for key, values in self.metrics.items():
                    if len(values) > 0:
                        self.writer.add_scalar(f'train/{key}', np.mean(values), self.global_step)
                self.metrics.clear()

            self.epoch += 1
            if epoch % checkpoint_interval == 0:
                self.save_checkpoint(f'checkpoint_epoch_{epoch}.pt')
                self.save_checkpoint('latest.pt')

        print("[Training Complete] Phase 1 training finished")
        self.save_checkpoint('final.pt')
        self.pool.close()

    def save_checkpoint(self, filename: str):
        """Save model checkpoint."""
        path = os.path.join(self.checkpoint_dir, filename)
        torch.save({
            'actor_critic': self.actor_critic.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'global_step': self.global_step,
            'config': self.config,
            'epoch': self.epoch,
            'reward_history': [float(x) for x in self._reward_history],
            'rescue': [int(self._rescue_count), int(self._rescue_epoch), float(self._rescue_il_weight)],
        }, path)
        print(f"Checkpoint saved to {path}")
    
    def load_checkpoint(self, filename: str):
        """Load model checkpoint."""
        path = os.path.join(self.checkpoint_dir, filename)
        checkpoint = torch.load(path, map_location=self.device, weights_only=True)
        self.actor_critic.load_state_dict(checkpoint['actor_critic'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.global_step = checkpoint['global_step']
        self.epoch = int(checkpoint.get('epoch', 0))
        self._reward_history = list(checkpoint.get('reward_history', []))
        if 'rescue' in checkpoint:
            rc, re_, rw = checkpoint['rescue']
            self._rescue_count, self._rescue_epoch, self._rescue_il_weight = int(rc), int(re_), float(rw)
        print(f"Checkpoint loaded from {path} (epoch {self.epoch}, step {self.global_step})")


def main():
    """Entry point for Phase 1 training."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 1 Training: PPO + IL')
    parser.add_argument('--config', type=str, default='configs/rma_config.yaml',
                       help='Path to config YAML')
    parser.add_argument('--tire_model', type=str, default=None, choices=['linear', 'friction_circle'],
                        help="override environment.tire_model in the config (default: config's, else linear)")
    parser.add_argument('--device', type=str, default='auto',
                       help='Device: cuda, cpu, or auto')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--log_dir', type=str, default='logs/phase1',
                       help='Directory for TensorBoard logs')
    parser.add_argument('--checkpoint_dir', type=str, default='checkpoints/phase1',
                       help='Directory for model checkpoints')
    parser.add_argument('--num_envs', type=int, default=None,
                        help='override phase1_training.num_envs (parallel simulator processes)')
    parser.add_argument('--seed', type=int, default=None, help='override phase1_training.seed')
    parser.add_argument('--total_timesteps', type=int, default=None,
                        help='override phase1_training.total_timesteps (0 = DAgger only)')
    parser.add_argument('--blind_intrinsics', action='store_true',
                        help='robust baseline: train without grip information (nominal physics into μ)')
    parser.add_argument('--resume', action='store_true',
                        help='continue from <checkpoint_dir>/latest.pt if it exists')
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    if args.tire_model:
        config.setdefault('environment', {})['tire_model'] = args.tire_model
    print(f"Tire model: {config.get('environment', {}).get('tire_model', 'linear')}")
    
    if args.debug:
        config['phase1_training']['debug_mode'] = True
    if args.num_envs:
        config['phase1_training']['num_envs'] = args.num_envs
    if args.seed is not None:
        config['phase1_training']['seed'] = args.seed
    if args.total_timesteps is not None:
        config['phase1_training']['total_timesteps'] = args.total_timesteps
    if args.blind_intrinsics:
        config['phase1_training']['blind_intrinsics'] = True
    
    # Determine device
    if args.device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    else:
        device = args.device
    
    print(f"Training on device: {device}")
    
    # Create trainer and train
    torch.set_num_threads(1)  # the simulators get the cores; the MLPs are small
    trainer = Phase1Trainer(config, device=device, log_dir=args.log_dir, checkpoint_dir=args.checkpoint_dir)
    if args.resume and os.path.exists(os.path.join(args.checkpoint_dir, 'latest.pt')):
        trainer.load_checkpoint('latest.pt')
    trainer.train()


if __name__ == '__main__':
    main()
