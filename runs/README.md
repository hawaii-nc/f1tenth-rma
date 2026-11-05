# Final checkpoints (November 2026)

Only the checkpoints the results cite are committed; intermediate ones (dagger.pt, onpolicy_round*.pt, latest.pt) are not. Paths match the `phase1` / `phase2` arguments recorded in every `results/retrain_nov2026/**/provenance.json`, which also give each file's SHA-256. Load with `f1tenth_research.models.load_actor_critic` / `load_adaptation`.

| Path | What |
|---|---|
| phase1_retrain/selected.pt | base policy, linear tire (DAgger checkpoint, selected by validation) |
| phase2_retrain/final.pt | φ, linear tire, oracle-driven data (original configuration) |
| phase2_onpolicy/final.pt | φ, linear tire, on-policy rounds (P1) |
| phase1_fc/final.pt, phase1_fc_seed1/, phase1_fc_seed2/ | base policy, friction-circle tire, training seeds 0/1/2 (P2, Q) |
| phase2_fc/final.pt, phase2_fc_seed1/, phase2_fc_seed2/ | φ, friction-circle tire, on-policy (P2), seeds 0/1/2 |
| phase1_fc_holdout/, phase2_fc_holdout/ | P2 trained without mco/silverstone/budapest (R3) |
| phase1_robust_fc/final.pt | robust baseline, no grip information (R2) |
| phase2_fc_k200/final.pt | φ with a 200-step window (amendment 4) |
| phase2_fc_probe_seed{0,1,2}/final.pt | φ_Q: grip probe + proprioceptive input (amendment 6) |
| phase2_fc_probe_holdout/final.pt | φ_Q on the held-out base policy (amendment 7) |
| real_phase1_seed{0,1,2}/final.pt | base policy, configuration R: car sensors, braking probe, racing expert (amendment 8) |
| real_phase2_seed{0,1,2}/final.pt | φ, configuration R (blind without wheel slip: RESULTS section 7) |
| **real_phase2_slipdr_seed{0,1,2}/final.pt** | **φ, configuration R with the slip model randomized (amendment 10): use these on the car** |
| real_phase1_holdout/, real_phase2_holdout/ | R trained without mco/silverstone/budapest (amendment 9) |
