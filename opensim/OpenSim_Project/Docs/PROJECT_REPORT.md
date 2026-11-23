# OpenSim Knee-Assist Project: Healthy vs ACL Recovery, With and Without the Actuator

SDP-II "Design and Simulation of a Wearable Knee Assist System for Gait Rehabilitation" (Yanbu Industrial College).
Inputs: the biomechanics workbooks `Biomechanics_Master_Data.xlsx` and `Biomechanics_Master_Data_CALC-BIO-03.xlsx` (CALC-BIO-03, Appendix D of the report; the extracted inputs are numerically identical to CALC-BIO-03, `Results/CALC-BIO-03_reconciliation.csv`), the CAD V4.1 actuator data (T_max = 10.76 N.m = 100 kPa x 3140.3 mm2 x 34.25 mm) and `WBDSinfo.csv`. Working case alpha = 0.20.

**Basis of the numbers in this document.** The current computed tables and figures (CAD V4.1, alpha = 0.20) are in `Tables/` and `Graphs/`; the OpenSim muscle results are in `Tables/T12-T14` and `Results/OpenSim_SO/`. Sections 6.2-6.6 below are a comparison case: alpha = 0.30 on the CAD V4 actuator basis (contact area 3109.9 mm2, capability 10.65 N.m). Their torques and moment reductions do not depend on the contact area; their pressures and the device-limited (delivered) values do.

---

## 0. Package contents: what was computed and where

| Part | Method | Where |
|---|---|---|
| Data extraction, unit/coordinate conversion, time normalisation | Python | `Scripts/01`, `Scripts/02`, `Input_Data/`, `Simulations/` |
| OpenSim input files (.mot, .sto, controller .xml, AnalyzeTool setups), 116 conditions incl. alpha sweep 0.10-1.00 | Python (generated files) | `Simulations/**` |
| Actuator torque / force / pressure / power / work / impulse | Python (computed from data) | `Actuator/`, `Tables/T4`, Fig05, Fig06, Fig06b |
| Knee angle and net knee moment results (all conditions) | Python (computed from data) | `Tables/T1-T5`, Fig01, Fig02, Fig09, Fig10 |
| Biological (muscle-required) knee moment with the actuator, knee-moment reduction | Python (computed from data) | `Tables/T1, T3, T4`, Fig07, Fig12, Fig13 |
| Verification against published reference values (34 checks) | **34 / 34 PASS** | `Results/verification_checks.csv` |
| **OpenSim model building + knee static optimization (muscle forces & activations)** | OpenSim 4.6 (Tables T12-T14) | `Scripts/run_opensim_knee_SO.py` |
| Quadriceps force / activation, muscle force reduction (Fig03, 04, 08, 11, 14, 20; muscle tables) | Post-processing of the OpenSim results (Tables T12-T14) | `Scripts/05_postprocess_opensim_results.py` |

Sections 1-6.6 are **computed from the input data** (group-mean waveforms) for the design patient 70 kg / 1.70 m; they are
not OpenSim muscle simulations. The OpenSim muscle results are summarised in Section 6.7.

---

## 1. Phase 1: data inspection (full table: `Docs/Data_Inspection_Available_Missing_Used.csv`)

**Available**
- Knee flexion angle: healthy full gait cycle (Winter 1987, N = 19, mean +/- SD, 2 %GC); stance 1-100 % for matched controls, ACLR and uninvolved limbs at pre-op, 2, 4, 6 and 12 months (Buttner 2025, digitised).
- Internal knee moment: Winter (N.m/kg, full cycle); Buttner (BW x height, stance, all groups and epochs). The healthy-minus-ACL deficit per epoch (Table 5A).
- Vertical GRF waveform (Winter only); walking speed per epoch; stance durations (ASM-BIO-04, derived); healthy stride time and toe-off (Winter).
- Actuator: torque rule and window, capability (100 kPa, 3140.3 mm2, r = 34.25 mm, 314.0 N, 10.76 N.m; CAD V4.1), timing deadlines, direction, on-leg mass.
- WBDS metadata: 51 subject IDs with age, height, mass, leg length, speed (young group mean 68.4 kg, 1.71 m).

**Missing**
- Marker trajectories (.trc/.c3d): WBDSinfo lists file names only; the motion files are not part of the data set.
- 3-D GRF / centre of pressure, hip and ankle angles and moments (healthy and ACL).
- Muscle forces, muscle activations, EMG.
- Any ACL swing-phase data; ACL cadence / stride time / stance fraction.
- Individual body mass, stature and segment parameters (only design scenarios).
- Actuator stroke, flow/speed, valve time t_system, rated power, angle-dependent moment arm r_eff(theta).

**Data used in the model**
- Knee angle and net internal knee moment waveforms (Buttner 2025 for the 12 primary conditions; Winter 1987 for the supplementary full-cycle pair).
- Deficit dM(phi), candidate windows, and the torque rule T = alpha x m x g x h x dM of the biomechanics calculation.
- Stance durations (Table 8 / ASM-BIO-04), m = 70 kg and h = 1.70 m (ASM-BIO-02/03), actuator capability and direction.

---

## 2. Model

- Base model: OpenSim **gait2392_simbody** (23 DOF, 92 Thelen2003 muscles; bodies, hip/knee/ankle joints and ground from the generic model), scaled uniformly x0.9444 (1.70 / 1.80 m) to 70 kg. The run script builds it from the gait2392 model of the local OpenSim 4.6 installation.
- Because only the **knee** angle and **net knee moment** exist, the muscle analysis is a **knee static optimization**: at every frame minimise sum(a_i^2) + a_res^2 subject to sum(r_i x a_i x F_i,max(FLV)) + reserve = M_net - T_device, with OpenSim moment arms (`computeMomentArm`) and OpenSim rigid-tendon force-length-velocity capacities (`calcInextensibleTendonActiveFiberForce`), which is the same muscle formulation as OpenSim's StaticOptimization tool. The solver is exact (verified against SciPy SLSQP on 300 random cases).
- The net knee moment is taken directly from the source studies' inverse dynamics (no GRF exists to recompute it). Hip and ankle are held at 0 deg (no data), adjustable in the script.

## 3. Gait-data processing (automatic)
- Units: BW x height to N.m via M = KEM x m x g x h (g = 9.80665); N.m/kg x 70 kg; deg to rad for speeds.
- Coordinates: project knee flexion (+) to gait2392 `knee_angle_r` (flexion -). Internal knee moment (extension +) equals the `knee_angle_r` generalized force (extension +), so no sign flip is needed.
- Time: % stance x T_stance (controls 0.655 s; pre-op 0.708 s; 2/4/6/12 mo 0.705/0.685/0.683/0.677 s); Winter % gait cycle x 1.1396 s.
- Filtering: none. The curves are smooth vector-extracted group means, and a 6 Hz Butterworth would have shifted the angle by up to 0.57 deg. Velocities use second-order central differences.
- Synchronisation: angle, moment, deficit and torque share the same 1 % stance grid (same source panels).

## 4. Actuator representation
- **CoordinateActuator `knee_assist_r`** on `knee_angle_r` (optimal force 1, so control = N.m), **extension only** (min control 0), **max 10.756 N.m** (100 kPa x 3140.3 mm2 x 34.25 mm, CAD V4.1), driven by a **PrescribedController** (PiecewiseLinearFunction of time) per condition. The script reads the torque back from the model at each frame.
- This represents the bladder as the knee couple it produces (F = pA on the shank at r = 34.25 mm); a fixed r is used because no angle-dependent r_eff(theta) is available.
- Torque profile: the rule T = alpha x m x g x h x dM(phi) inside the candidate window (9-44 % stance; 9-40 % at 12 mo; 9-37 % pre-op), zero outside. It reproduces Table 6A of the biomechanics workbook within 0.006 N.m.
- **alpha = 0.20 (working case)** for the primary conditions. **alpha = 0.30** (comparison case, Sections 6.2-6.5) is the largest tabulated alpha the 100 kPa actuator meets at every epoch. The alpha sweep 0.10-1.00 is in Section 6.6; on the CAD V4 basis alpha_max (the alpha reached at 100 kPa) is 0.534 / 0.323 / 0.416 / 0.411 / 0.593 (pre-op / 2 / 4 / 6 / 12 mo). A **capped** profile T <= max(M_net, 0) is also run; it is an over-assistance guard studied here and is **not** part of the device torque specification.
- Healthy + Actuator: assist-as-needed gives zero torque for a healthy limb (no deficit), so the healthy case is driven with the **device design command**, the 2-month (governing) profile x alpha.

## 5. Simulation matrix (116 conditions, `Simulations/conditions_manifest.csv`)
- 12 primary: Healthy, ACL pre-op, 2, 4, 6 and 12 months, each **without** and **with** the actuator (alpha 0.20).
- Alpha sweep: alpha = 0.10, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00 for each of the six groups. Each value is run as **requested torque** (ideal torque source, 66 runs). Where the request exceeds the 100 kPa capability (10.65 N.m on the CAD V4 basis, 10.76 N.m with CAD V4.1; the same 36 runs in both cases) it is also run as **delivered torque**, i.e. clipped at the 100 kPa capability (36 extra runs).
- 6 capped runs (alpha 0.20, T <= max(M_net, 0)) and 2 Winter full-cycle runs.

## 6. Results (computed from data; 70 kg, 1.70 m)

### 6.1 Knee angle and net knee moment (no actuator)
| Condition | LR peak flexion (deg) | Stance ROM (deg) | Peak ext. moment (N.m / N.m/kg) | % healthy | Peak flex. moment (N.m) |
|---|---:|---:|---:|---:|---:|
| Healthy (controls) | 12.27 | 32.76 | 41.41 / 0.59 | 100 | -25.31 |
| ACL Pre-op | 11.86 | 29.21 | 21.54 / 0.31 | 52.0 | -9.49 |
| ACL 2 months | 5.78 | 29.73 | 8.66 / 0.12 | 20.9 | -15.80 |
| ACL 4 months | 7.24 | 32.24 | 15.87 / 0.23 | 38.3 | -18.78 |
| ACL 6 months | 6.85 | 32.59 | 15.58 / 0.22 | 37.6 | -21.64 |
| ACL 12 months | 8.35 | 34.14 | 23.54 / 0.34 | 56.8 | -19.97 |
| Healthy full cycle (Winter) | 21.67 (peak 64.86 in swing) | 64.32 (full cycle) | 43.05 / 0.615 | - | -19.67 |

Peak extension (minimum flexion) in stance: healthy -1.53, pre-op +1.77, 2 mo -1.92, 4 mo -2.31, 6 mo -2.94, 12 mo -2.62 deg.

### 6.2 Actuator (alpha = 0.30, CAD V4 basis)
| Condition | Peak torque (N.m) | Peak force (N) | Pressure (kPa) | On-off (ms after IC) | Peak power +/- (W) | Net work (J) | Total assistance, impulse (N.m.s) |
|---|---:|---:|---:|---|---:|---:|---:|
| Healthy (design cmd) | 9.89 | 288.8 | 92.9 | 59-288 | +6.28 / -16.91 | -0.155 | 1.480 |
| Pre-op | 5.99 | 174.8 | 56.2 | 64-262 | +1.96 / -7.35 | -0.257 | 0.837 |
| 2 months | 9.89 | 288.8 | 92.9 | 63-310 | +2.52 / -10.16 | -0.328 | 1.592 |
| 4 months | 7.69 | 224.5 | 72.2 | 62-301 | +3.39 / -10.62 | -0.232 | 1.234 |
| 6 months | 7.78 | 227.1 | 73.0 | 61-301 | +3.54 / -11.21 | -0.235 | 1.281 |
| 12 months | 5.39 | 157.3 | 50.6 | 61-271 | +2.86 / -8.39 | -0.169 | 0.823 |

All profiles stay within the 10.76 N.m / 100 kPa capability. Net work is negative: from about 9 to 21 % stance the knee is flexing against the extension torque, so the device absorbs energy; it does positive work only from about 21 to 44 % stance.

### 6.3 Knee effect: muscle-required knee extension moment, same gait assumed (hypothesis H1; alpha = 0.30)
M_bio = M_net - T_device (internal, extension +, N.m on both sides).

| Condition | Early-stance peak M_bio without -> with (N.m) | Reduction, peak (%) | Reduction, window impulse (%) | Window over-assisted (%) | Capped profile: peak / window (%) |
|---|---|---:|---:|---:|---|
| Healthy | 41.41 -> 31.56 | 23.8 | 26.6 | 8.3 | 23.8 / 26.3 |
| Pre-op | 21.54 -> 15.63 | 27.5 | 28.3 | 6.9 | 27.5 / 27.5 |
| 2 months | 8.66 -> -0.88 | **110 (over-assisted)** | 169 | **100** | 100 / 100 |
| 4 months | 15.87 -> 8.24 | 48.1 | 66.1 | 36.1 | 48.1 / 56.5 |
| 6 months | 15.58 -> 7.86 | 49.5 | 73.7 | 41.7 | 49.5 / 60.0 |
| 12 months | 23.54 -> 18.17 | 22.8 | 27.9 | 9.4 | 22.8 / 27.1 |
| Healthy full cycle (Winter) | 43.05 -> 33.41 | 22.4 | 23.9 | 0 | - |

Device contribution at the instant of the baseline peak: healthy 23.8 %, pre-op 27.7 %, 2 mo 112 %, 4 mo 48.3 %, 6 mo 49.7 %, 12 mo 22.8 %.

**Over-assistance finding.** The torque rule sizes the torque from the healthy-minus-ACL deficit, but under H1 the muscles must still produce M_net minus the device torque. At 2 months the patient's own extensor moment is only 21 % of healthy, so 0.30 x deficit exceeds it everywhere in the window. The muscle moment then turns flexor (down to -8.4 N.m), and static optimization would recruit hamstrings against the device. The device torque equals the patient's net moment at the deficit peak when alpha = 0.254 (2 mo), 0.612 (4 mo), 0.593 (6 mo), 1.07 (pre-op) and 1.30 (12 mo). At the window edges the ACL net moment is already <= 0 (2 mo 33 %, 4 mo 22 %, 6 mo 25 % of window frames), so any positive torque there over-assists. The capped profile removes this.

### 6.4 Restoration view (hypothesis H2 = ASM-BIO-08: device adds to the patient's own moment)
Peak net extension moment as % of healthy, without -> with (alpha 0.30 comparison case): pre-op 52 -> 66, 2 mo 21 -> 45, 4 mo 38 -> 57, 6 mo 38 -> 56, 12 mo 57 -> 70 (Fig13).

### 6.5 Recovery effect (pre-op -> 12 months)
- Peak extension moment, % of healthy: 52 -> **21** -> 38 -> 38 -> 57. Surgery causes the largest drop; it partly recovers by 4 months, plateaus to 6 months, improves again by 12 months, and is still about 43 % below healthy at 12 months.
- Loading-response flexion: 11.9 -> **5.8** -> 7.2 -> 6.9 -> 8.4 deg (healthy 12.3): the stiff-knee pattern is largest at 2 months.
- Device demand at alpha 0.30 (comparison case): 6.0 -> **9.9** -> 7.7 -> 7.8 -> 5.4 N.m. The 2-month case governs the hardware but is also where H1 over-assists.

### 6.6 Alpha sweep 0.10 to 1.00 (CAD V4 basis; current tables: `Tables/T10_Alpha_Sweep_All.csv`, `T11_Sweep_*.csv`; Fig15-Fig19)
Requested peak actuator torque (N.m), with the required pressure in kPa in brackets. **Bold** = above 100 kPa, so the actuator cannot deliver it.

| alpha | Healthy (design cmd) | Pre-op | 2 mo | 4 mo | 6 mo | 12 mo |
|---|---:|---:|---:|---:|---:|---:|
| 0.10 | 3.30 (31) | 2.00 (19) | 3.30 (31) | 2.56 (24) | 2.59 (24) | 1.80 (17) |
| 0.20 | 6.59 (62) | 3.99 (37) | 6.59 (62) | 5.13 (48) | 5.19 (49) | 3.59 (34) |
| 0.25 | 8.24 (77) | 4.99 (47) | 8.24 (77) | 6.41 (60) | 6.48 (61) | 4.49 (42) |
| 0.30 | 9.89 (93) | 5.99 (56) | 9.89 (93) | 7.69 (72) | 7.78 (73) | 5.39 (51) |
| 0.40 | **13.19 (124)** | 7.98 (75) | **13.19 (124)** | 10.25 (96) | 10.37 (97) | 7.18 (67) |
| 0.50 | **16.48 (155)** | 9.98 (94) | **16.48 (155)** | **12.81 (120)** | **12.97 (122)** | 8.98 (84) |
| 0.60 | **19.78 (186)** | **11.97 (112)** | **19.78 (186)** | **15.38 (144)** | **15.56 (146)** | **10.78 (101)** |
| 0.70 | **23.08 (217)** | **13.97 (131)** | **23.08 (217)** | **17.94 (168)** | **18.15 (170)** | **12.57 (118)** |
| 0.80 | **26.37 (248)** | **15.96 (150)** | **26.37 (248)** | **20.50 (193)** | **20.74 (195)** | **14.37 (135)** |
| 0.90 | **29.67 (279)** | **17.96 (169)** | **29.67 (279)** | **23.06 (217)** | **23.34 (219)** | **16.16 (152)** |
| 1.00 | **32.97 (310)** | **19.96 (187)** | **32.97 (310)** | **25.63 (241)** | **25.93 (243)** | **17.96 (169)** |

These match the torque table of the actuator design data for the epochs it covers (rounding differences of 0.01 N.m at most).

Reduction of the muscle-required early-stance peak knee extension moment (%, H1). Each cell gives the requested value, then the delivered (device-limited) value after the slash.

| alpha | Healthy | Pre-op | 2 mo | 4 mo | 6 mo | 12 mo |
|---|---:|---:|---:|---:|---:|---:|
| 0.10 | 8 | 9 | 37 | 16 | 17 | 8 |
| 0.20 | 16 | 18 | 74 | 32 | 33 | 15 |
| 0.25 | 20 | 23 | 92 | 40 | 41 | 19 |
| 0.30 | 24 | 27 | 110* | 48 | 50 | 23 |
| 0.40 | 32 / 26 | 37 | 144* / 123* | 64 | 66 | 30 |
| 0.50 | 40 / 26 | 46 | 158* / 123* | 80 / 67 | 82 / 68 | 38 |
| 0.60 | 48 / 26 | 54 / 49 | 158* / 123* | 96 / 67 | 99 / 68 | 46 / 45 |
| 0.70 | 56 / 26 | 62 / 49 | 158* / 123* | 111* / 67 | 115* / 68 | 53 / 45 |
| 0.80 | 63 / 26 | 68 / 49 | 158* / 123* | 126* / 67 | 131* / 68 | 61 / 45 |
| 0.90 | 71 / 26 | 68 / 49 | 158* / 123* | 132* / 67 | 131* / 68 | 68 / 45 |
| 1.00 | 79 / 26 | 68 / 49 | 158* / 123* | 132* / 67 | 131* / 68 | 76 / 45 |

\* above 100 % means over-assisted: the device torque exceeds the patient's own net extensor moment, and the muscles would have to pull the other way.

What the sweep shows:
- **Feasibility at <= 100 kPa (CAD V4 basis):**
  - alpha <= 0.30 is achievable for every group.
  - alpha 0.40 works for pre-op, 4, 6 and 12 months, but not at 2 months.
  - alpha 0.50 works only for pre-op and 12 months.
  - alpha >= 0.60 needs more than 100 kPa for every group (12 months at 0.60 needs 101 kPa).
- **The benefit plateaus at the device limit.** The best delivered reduction is about 26 % (healthy), 49 % (pre-op), 67-68 % (4-6 months) and 45 % (12 months).
- **The requested curves also flatten at high alpha.** Pre-op stops at 68 % because the patient's extensor moment continues past the end of the actuator window (37 % stance). For 2 months, once over-assisted, the remaining peak lies outside the window.
- **2 months is over-assisted from about alpha 0.27** (92 % at 0.25, 110 % at 0.30). 4 and 6 months cross 100 % only at about alpha 0.6-0.65 with requested torque, and never with the delivered torque.
- **Over-assistance at the window edges.** The window frames where the device exceeds the patient's own net moment (Fig17) occur even at alpha 0.10 for 2, 4 and 6 months (42 %, 28 % and 31 % of the window). The reason is that at the edges of the healthy window (9-12 % and 37-44 % stance) the ACL limb's own moment is already flexor.
- **H2 restoration.** The peak net moment with the delivered torque reaches at most 78 % (pre-op), 47 % (2 mo), 64 % (4 mo), 63 % (6 mo) and 83 % (12 mo) of healthy (Fig18).

### 6.7 Muscle effect (quadriceps RF, VL, VM, VI)
OpenSim static optimization (alpha = 0.20, CAD V4.1). Muscle forces and activations: `Tables/T12-T14`, `Results/OpenSim_SO/`; figures Fig03, 04, 08, 11, 14 and 20.
Peak early-stance quadriceps force without the device (Table T12): healthy 985.5 N, pre-op 530.3 N, 2 months 235.8 N, 4 months 406.8 N, 6 months 399.7 N, 12 months 587.0 N.

## 7. Verification (`Results/verification_checks.csv`: 34 / 34 PASS)
- LR peak flexion and peak KEM match Table 2B of the biomechanics workbook (within 0.05 deg and 0.004 N.m/kg).
- Torque impulse and alpha = 1 peaks match Table 6B.
- The alpha reached at 100 kPa and the pressure needed for the working case match the CAD V4.1 capability and CALC-BIO-03 Table 6B.
- The torque-peak times match Table 9 (+/- 1 ms).
- The SO solver equals the SLSQP optimum, with a moment residual below 1e-6 N.m.

## 8. Limitations
1. Group-mean waveforms (ASM-BIO-01), not one patient. Mass/stature are scenarios (70 kg, 1.70 m), and stance durations are derived (ASM-BIO-04; pre-op also derived here).
2. Stance-only ACL data, so there are no ACL swing results.
3. No GRF/markers, so OpenSim inverse kinematics/dynamics could not be recomputed; the net knee moment comes from the source labs.
4. Knee-only static optimization: hip/ankle are neutral and their moments are unconstrained (rectus femoris and gastrocnemius shares are approximate). There are no passive forces, no co-contraction, and generic muscle strength (ACL quadriceps weakness is not modelled; `QUAD_STRENGTH_FACTOR` is available).
5. H1 (same gait with the device) and H2 (device restores the moment) are the two bounding hypotheses. Which happens requires a predictive simulation (e.g. OpenSim Moco) or experiments.
6. The actuator uses a fixed moment arm (+/-20 % r gives +/-20 % torque) and an ideal torque source: no pneumatic rise/vent dynamics (t_system unknown) and no 97 g device mass. The step at window onset is the torque rule on a 1 % grid (it is not a realisable rise rate).
7. The biomechanics inputs are digitised group means (CALC-BIO-03) that were not checked against an independent data set.

## 9. How to run
See `Docs/HOW_TO_RUN_OpenSim.md`. In short: OpenSim 4.6, then **Scripts > Run... > `Scripts/run_opensim_knee_SO.py`**; the results are written to `Results/OpenSim_SO`.
