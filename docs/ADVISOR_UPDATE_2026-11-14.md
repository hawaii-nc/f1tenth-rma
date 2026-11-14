# Update for Prof. Modekurthy (Nov 14, 2026)

For Nathan to send or adapt. Everything below is in the repo `hawaii-nc/f1tenth-rma`; numbers are from `docs/RESULTS_NOV2026.md`.

## Why this email is due now

His last message (Oct 31) asked for four things and ended: *"If you can send me a reminder in 2 weeks, I can put you in touch with a grad student that may coordinate with you and run some experiments on the car."* Two weeks from Oct 31 is today. So the follow-up is the reminder, plus the answers below.

## What he asked, and where it stands

| He asked (Oct 31) | Status |
|---|---|
| "Start training with the correct script" | **Done.** Everything was rebuilt and retrained from the fixed pipeline (3 training seeds), evaluated with paired episodes and pre-registered predictions. The July numbers (44% gap closure) are superseded and flagged as not citable. |
| "Look into new tire models" | **Done.** Three tire models were tested: the stock linear one, a friction-circle tire I added (force saturates at μg), and a Fiala brush tire. |
| "If the tire models are not representative, learn on the fly in the real world ... could be a novel contribution for a full paper" | **This is, in effect, what the results point to.** In all three tire models, the car's ordinary motion carries no grip information (grip R² ≈ 0 when the car's own actions are kept independent of grip). Reading grip requires *deliberately exciting* the tires. A brief braking/speed pulse does that, and grip then becomes readable (R² 0.84–0.93). That is online grip learning with active excitation. It is shown in simulation only. |
| Reminder, then an intro to a grad student for car experiments | **Requested below.** |

## Results so far (all simulation)

1. **Passive adaptation cannot work here.** Adaptation modules that looked successful were reading the controller's own actions or just driving slowly; a speed-capped non-adaptive car matches them.
2. **A 0.1 s probe on straights makes grip observable.** Grip R² 0.89–0.93 with ideal sensors; 0.84–0.87 with the car's real sensing (wheel-odometry speed, kinematic yaw rate, 40 Hz LiDAR).
3. **With the probe, adaptation beats any fixed speed limit.** At grip 0.4 the adaptive car crashes 2–8% of episodes against 33–47% for a non-adaptive car matched to its speed (3 seeds, 100 paired episodes each, p ≤ 6×10⁻⁸). With the car's real sensing and a racing expert: 28–39% against 84–86%.
4. **It depends on the wheel-slip model.** Randomizing that model in training beats the non-adaptive car in all 30 comparisons.
5. **Newest (Nov 13): a cold-start fix.** Before its first probe, the adaptive car runs on a nominal belief; 37–44% of its low-grip crashes happen in the first 2 s. Assuming low grip until the first probe cuts crashes at grip 0.4 from 0.33 to 0.22 (pooled, p = 2×10⁻⁵, 300 paired episodes) with no cost at higher grip. About 0.2 of crash rate remains and is not yet explained.
6. **Failed or negative results are reported, not dropped**: a 2 s memory and a faster probe did not help; held-out-track transfer at grip 0.4 misses its margin; one cross-grip variance check fails even for the oracle.

## What is *not* shown

- **Nothing about the probe has run on the real car.** The one assumption the whole method rests on is that VADER's wheels respond to a braking pulse the way the simulator assumes. Stage 1 tests exactly that. It needs one lab session, no learned policy.
- The July real-car pilot (81 trials, 4 tire wraps) used the old pipeline with no probe. Its steering difference between bare and electrical tape survives correction for multiple comparisons; the yaw-rate difference does not. It shows the policy responds to a real tire change, not that the probe works.
- Whether this is enough novelty for a full paper is his call. My honest read: the observability result plus the probe is a clearer contribution than the July framing, but a real-car result is what would make it a full paper; without it, a workshop paper is the safe target.

## In progress right now

Pre-registered amendment 13, running on the 4-core container: (B) does biasing the grip estimate toward low grip remove the remaining crashes, and what does it cost in speed; (T) does retraining the adaptation module with the cold-start fix help. Results will be in the repo when done; predictions were committed before the runs. I expect arm T to show little change.

## What is ready for the car

- `docs/STAGE1_RUN_SHEET.md`: a one-page, step-by-step sheet for the lab session (what to bring, what to check on the car first, 20 trials on each of 3 tire wraps, how to read the result).
- Analysis tool tested on simulated trials, including a messy session (no IMU, no wall in range, an aborted trial). It also reports whether the wheels actually slip, which is the assumption being tested.
- Car node fixed and tested: default braking probe matches the trained models (it was the wrong sign), cold-start fix included, launch scripts point at the November models. **Not yet run on hardware.**

## What I need from him

1. **The introduction to the grad student** who can run Stage 1 (and later closed-loop trials) on VADER, with access to the car and TBE B150.
2. **Is a full paper still the goal, or the workshop?** The call for workshop papers should come after Dec 1; the deadline he gave is February 2027.
3. **His preference on tire models for the paper:** the friction-circle and brush tires are in; Gazebo or a measured real surface are the next options (`docs/SIM_FIDELITY.md`).
4. **Orin AGX power check** (hand-off item): the 76 W power board needs re-checking against the AGX before it is installed.

## Draft email

Subject: Re: Summer work update and a couple of questions [Smart Cities 2026]

Hi Dr. Modekurthy,

This is the reminder you asked for. I hope the submission went well.

On your last email: I retrained everything from the fixed pipeline (3 training seeds, pre-registered predictions) and tested three tire models: the stock one, a friction-circle tire, and a brush tire. In all of them the car's ordinary motion carries no information about grip, which is why my July results were not real. A short active probe (a 0.1 s braking pulse on straights) makes grip readable, and with it the adaptive car crashes 2–8% of episodes at low grip versus 33–47% for a non-adaptive car driving at the same speed. It also holds up with the car's real sensors, though less well at the lowest grip. This is your "learn on the fly" idea in simulation. All of it is in https://github.com/hawaii-nc/f1tenth-rma (start with docs/RESULTS_NOV2026.md).

Nothing has been tested on the real car yet, and that is the next step. I wrote a one-page run sheet (docs/STAGE1_RUN_SHEET.md) for a single lab session: braking pulses on bare, duct-tape and electrical-tape tires, no learned policy. It checks the one assumption everything rests on, that the real wheels respond to the pulse the way the simulator assumes.

Could you put me in touch with the grad student you mentioned, so we can schedule that session? I'm happy to join a call or walk them through the code. I can also meet at any time that works for you this week.

Thanks,
Nathan
