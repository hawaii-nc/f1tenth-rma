"""Amendment 6: φ input selection (channel subset, time stride) round-trips through a checkpoint."""
import torch

from f1tenth_research.models import AdaptationModule, load_adaptation


def test_proprio_strided_roundtrip(tmp_path):
    chans = [0, 1, 2, 3, 4, 113, 114]
    m = AdaptationModule(115, 197, 8, input_channels=chans, stride=4)
    assert m._steps[-1] == 196 and len(m._steps) == 50
    x = torch.randn(3, 197, 115)
    # channels outside the subset must not matter
    y = x.clone(); y[:, :, 5:113] = 0
    assert torch.allclose(m(x), m(y))
    p = tmp_path / 'phi.pt'
    torch.save({'adaptation': m.state_dict()}, p)
    m2, _ = load_adaptation(str(p))
    assert m2.history_window == 197 and m2.state_action_dim == 115 and m2.stride == 4
    assert torch.allclose(m(x), m2(x))


def test_default_module_unchanged(tmp_path):
    m = AdaptationModule(115, 50, 8)
    assert m.channel_idx is None and 'input_spec' not in m.state_dict()
    p = tmp_path / 'phi.pt'
    torch.save({'adaptation': m.state_dict()}, p)
    m2, _ = load_adaptation(str(p))
    x = torch.randn(2, 50, 115)
    assert torch.allclose(m(x), m2(x))
