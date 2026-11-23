# CHANGELOG

## 12 Nov 2026 - Fig21, models, status texts corrected
| Item | Change |
|---|---|
| Graphs | Fig21 (panel) + Fig21a-d: stance phases and assist windows; knee angle, knee moment, knee power; healthy vs ACL 2 months, no-device baseline, stance only |
| Scripts | 08_plot_knee_healthy_vs_ACL2mo.py (reads Simulations/*/..._inputs_and_actuator.csv; power = M x knee_angle_r speed); added to run_all_python_steps.py |
| Models | 13 .osim files of the executed run added (scaled gait2392 + 12 primary conditions; 92 muscles, 70 kg, knee_assist_r + PrescribedController) |
| Docs / Tables | PROJECT_REPORT, Data_Inspection, T1/T3 and the results workbook: 'not executed' -> results in T12-T14; capability 10.76 N.m (CAD V4.1); Fig21 footer run date 30 Oct |
| README | Status: the OpenSim run was executed (results 30 Oct); Models/ included; "Running on another computer" checks |

## 27 Oct 2026 - reconciliation before the final OpenSim run
| Item | Before (8 Oct package) | Now | Source |
|---|---|---|---|
| Biomechanics reference | CALC-BIO-02 DRAFT | CALC-BIO-03 Rev 0 (DRAFT) | Biomechanics_Master_Data_CALC-BIO-03.xlsx |
| Numerical inputs | - | unchanged: stance angle/moment identical (max diff 0), full-deficit peaks within 0.006 N.m, windows switch on the same 1 % frames, stance durations identical | Scripts/07 -> Results/CALC-BIO-03_reconciliation.csv (12/12 PASS) |
| Contact area A | 3109.9 mm2 (actuator V4) | 3140.3 mm2 | CAD V4.1 |
| Device capability T_max | 10.651 N.m | 10.756 N.m (10.76) = 100 kPa x 3140.3 mm2 x 34.25 mm | CAD V4.1, Eq. 4.14 |
| Primary (working) alpha | 0.30 | 0.20 (2 months: 6.59 N.m, 61.3 kPa) | SDP-II report / CALC-BIO-03 Table 6B |
| Primary 12 conditions | 6 baselines + alpha 0.30 | 6 baselines + alpha 0.20 | conditions_manifest.csv |
| Capped / Winter full-cycle conditions | a030cap / Assisted_a030 | a020cap / Assisted_a020 | Scripts/02 |
| Verification | 34/34 PASS | 34/34 PASS (V5-V7 references updated to CAD V4.1 / alpha 0.20) | Results/verification_checks.csv |

Total conditions still 116 (67 requested, 36 device-limited, 7 baselines, 6 capped).
The alpha 0.20 conditions are within capability at every epoch, so they do not depend on T_max.

### Open (team decision)
- Device limit in OpenSim = contact design basis 10.76 N.m. FEA delivered net torque is 4.965-7.356 N.m (rigid cover).
  A 'delivered-net' sensitivity (clip at the FEA value) can be added once the team chooses the value.
- OpenSim run must be repeated (quick test 12, then 116).
