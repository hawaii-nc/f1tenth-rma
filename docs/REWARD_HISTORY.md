# Reward history

The reward went through four documented versions before the final map-agnostic runs. Reward-balance bugs caused several failed runs, so this history matters.

## V1: Zhang-style velocity tracking (runs 1–6, deprecated)

R = −w_s·|a_t − a_{t−1}|/max_diff + w_survival − w_v·|v − v_des|/max_v_err − w_yaw·|ω − ω_des|/max_ω_err

**Failure:** the policy commanded throttle ≈ −1, so v_des ≈ 0. It stood still with zero tracking error and scored 999.5/1000 while creeping at 0.02 m/s. This is a circular dependency: v_des is the policy's own command.

## V2: progress patch (deprecated)

V1 plus a speed bonus. Abandoned because the circular dependency was still there.

## V3: centerline progress (Paper 1 baseline)

R = 5.0·progress + smoothness + 0.01 alive − 1.0·collision − 0.5·[v < −0.05]

Progress is the arc length advanced along the centerline:

- idx_t = argmin‖p_t − c_i‖ and Δidx = (idx_t − idx_{t−1}) mod N
- Δidx > N/4 is treated as 0 (wrap and teleport guard)
- progress = min(Δidx·spacing, 0.5 m)

This cannot be gamed by commanding speed without moving. Result: 634–757 steps per lap, 0.163–0.199 m centerline deviation.

## V4: physics-limit-aware (Paper 2, 8 m/s era)

V3 − 0.2·(1 − min LiDAR) (wall proximity), plus a speed–turn coupling −0.5·max(0, |δ| − 0.15)·(v/8) and a close-wall term.

**Finding:** wall proximity improved precision and consistency but **not** speed regulation. The car held about 8 m/s into hard turns because the simulator did not punish it (see [SIM_FIDELITY.md](SIM_FIDELITY.md)).

## Final (v27–v42, map-agnostic, 3 m/s)

From `configs/final_phase1_v42.yaml`:

| Term | Weight / setting |
|---|---|
| progress (centerline arc length) | 5.0 |
| smoothness (\|Δa\| / 0.4) | 0.05 |
| alive | 0.01 |
| collision | 1.0 (and the episode terminates) |
| speed–turn coupling (steer threshold 0.15 rad) | 0.5 |
| centerline error (capped at 0.5 m) | 0.1 |
| wall proximity | off (`use_wall_proximity: false`) |
| velocity / yaw-rate tracking | 0.0 |
| reverse (v < −0.05) | −0.5 |

The curvature-aware speed limit, safe_speed = k/√(κ + ε), is implemented in `reward.py` but is not weighted in the final config. It is the seed of the grip-adaptive "Basic Speed Law" rule, which is now implemented as a runtime shield (`safety/shield.py`).

**Lessons:**

- Print the per-term reward breakdown before every long run. A 0.005 smoothness weight once overwhelmed the alive bonus.
- A reward near zero does not mean bad driving. Judge by crash rate and centerline deviation.
