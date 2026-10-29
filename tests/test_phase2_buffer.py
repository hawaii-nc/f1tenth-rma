import numpy as np

from f1tenth_research.training.phase2_adaptation import AdaptationDataBuffer


def make_episode(ep_id, T, D=4):
    sa = np.full((T, D), ep_id, dtype=np.float32)
    sa[:, 0] = np.arange(T)              # step index in channel 0
    z = np.full((T, 8), ep_id, dtype=np.float32)
    z[:, 0] = np.arange(T)
    return sa, z


def test_windows_never_cross_episodes_and_labels_align():
    buf = AdaptationDataBuffer(max_size=10_000, window_size=5)
    for ep in range(10):
        buf.add_episode(*make_episode(ep, T=20 + ep))
    h, z, e = buf.get_batch(512)
    assert h.shape == (512, 5, 4) and z.shape == (512, 8) and e.shape == (512, 7)
    ep_ids = h[:, :, 1]
    assert (ep_ids == ep_ids[:, :1]).all()                 # one episode per window
    assert (z[:, 1] == ep_ids[:, 0]).all()                 # label from same episode
    assert (z[:, 0] == h[:, -1, 0]).all()                  # label from the window's last step


def test_eviction_keeps_alignment():
    buf = AdaptationDataBuffer(max_size=100, window_size=5)
    for ep in range(50):
        buf.add_episode(*make_episode(ep, T=30))
    assert len(buf) <= 130
    h, z, _ = buf.get_batch(256)
    assert (z[:, 1] == h[:, 0, 1]).all()
    assert h[:, 0, 1].min() >= 46                          # only recent episodes remain


def test_short_episodes_skipped():
    buf = AdaptationDataBuffer(window_size=50)
    buf.add_episode(*make_episode(0, T=10))
    assert len(buf) == 0
