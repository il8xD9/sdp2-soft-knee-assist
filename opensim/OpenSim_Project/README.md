# OpenSim_Project: Wearable Knee Assist (SDP-II)

Healthy vs ACL (pre-op, 2, 4, 6, 12 months), with and without the posterior-knee pneumatic actuator.

**Contents and results:**
- OpenSim 4.6 knee static optimisation of 116 conditions.
  Outputs: `Results/OpenSim_SO/` (116 conditions + ALL_conditions_SO_*.csv + run_log), `Tables/T12-T14`, `Graphs/Fig03/04/08/11/14/20`.
- Biomechanics inputs = CALC-BIO-03 (12/12 reconciliation checks PASS, `Results/CALC-BIO-03_reconciliation.csv`); 34/34 verification checks PASS.
- Actuator in the assisted runs = CAD V4.1 (A = 3140.3 mm2, r = 34.25 mm, T_max = 10.76 N.m at 100 kPa); working case alpha = 0.20.
- `Graphs/Fig21*`: knee angle, knee moment and knee power, healthy vs ACL 2 months (no-device baseline), stance only, with the stance
  phases and the two assist windows (Option 1 8.43-44 %, Option 2 13-36 %). Made by `Scripts/08_plot_knee_healthy_vs_ACL2mo.py`.
- `Models/` contains the .osim files of the run: `gait2392_scaled_70kg_170cm.osim` + 12 primary condition models (`Healthy/` 2, `ACL/` 10),
  each 92 muscles, 70 kg, with the `knee_assist_r` actuator and its PrescribedController (controls stored inside the model).
- Only the NO-DEVICE results of this package are used in the project report; the assisted conditions are included for completeness.
  The run with the final bladder actuator is in `../Actuator_Run/`.
- Full report: `Docs/PROJECT_REPORT.md`; how to run: `Docs/HOW_TO_RUN_OpenSim.md`.

```
OpenSim_Project/
├── README.md
├── Docs/          PROJECT_REPORT.md · HOW_TO_RUN_OpenSim.md · Data_Inspection_Available_Missing_Used.csv
├── Input_Data/    tidy CSV tables extracted from the workbook + Source_Files/ (original 3 files)
├── Models/        Healthy/ ACL/  -> .osim files are written here by the OpenSim run (see Models/README.md)
├── Actuator/      parameters, OpenSim actuator component, torque/force/pressure/power profiles, checks
├── Simulations/   116 condition folders: .mot (kinematics), .sto (knee speed, net moment, actuator controls),
│                  PrescribedController .xml, AnalyzeTool setup .xml, inputs_and_actuator.csv
│   ├── Healthy_Baseline/            ├── Healthy_Assisted/{a010 ... a100, aXXX_lim, a020cap}/
│   ├── ACL_PreOp/{Baseline, Assisted_a010 ... Assisted_a100, Assisted_aXXX_lim, Assisted_a020cap}/
│   ├── ACL_2Months/ ... ACL_4Months/ ... ACL_6Months/ ... ACL_12Months/ (same sub-folders)
│   ├── Healthy_FullGait_Winter/{Baseline,Assisted_a020}/
│   └── conditions_manifest.csv
├── Results/       metrics_all_conditions_computed.csv · over_assistance_alpha_guard.csv ·
│                  verification_checks.csv · OpenSim_SO/ (filled by the OpenSim run)
├── Graphs/        Fig01-Fig21 (PNG, 300 dpi); Fig03/04/08/11/14/20 from the OpenSim run; Fig21 = healthy vs ACL 2 months (knee angle / moment / power)
├── Tables/        T1-T11 (.csv) + OpenSim_Project_Results.xlsx (muscle sheets added after the OpenSim run)
└── Scripts/       01-07 Python pipeline (07 = CALC-BIO-03 reconciliation) · 08 Fig21 plot · run_opensim_knee_SO.py (OpenSim) · run_all_python_steps.py
```

Re-run every Python step: `python Scripts/run_all_python_steps.py` (pandas, numpy, scipy, matplotlib, openpyxl).


## Running on another computer

Requirements and steps:
1. Windows with **OpenSim 4.6** installed (the GUI ships `gait2392_simbody.osim`, which the run needs).
2. Place the folder in a path with **English letters only** (e.g. `C:\sdp2_opensim\OpenSim_Project`) - OpenSim cannot open non-ASCII paths.
3. OpenSim GUI -> Scripts -> Run -> `Scripts/run_opensim_knee_SO.py` (or `run_opensim_QUICK_TEST_12.py` for a 12-condition test).
   The script finds the project folder and the gait2392 model by itself; if not, set `PROJECT_DIR` / `MODEL_PATH` at the top.
   It re-writes the .osim models in `Models/` and the results in `Results/OpenSim_SO/`.
4. Python steps (no OpenSim needed): `python Scripts/run_all_python_steps.py` (pandas, numpy, scipy, matplotlib, openpyxl).

## Package properties
- `run_all_python_steps.py` runs end to end: steps 01-04, 06 (34/34 verification PASS), 05 (muscle tables from the included OpenSim results), 08 (Fig21).
- All 116 conditions in `Simulations/conditions_manifest.csv` have their 4 input files (.mot, knee speed, net moment, controls); the 12 primary conditions have their AnalyzeTool setup .xml.
- The scripts and setup files contain no absolute paths (relative paths / auto-detect only).
- `run_opensim_knee_SO.py` runs in the OpenSim 4.6 GUI (Jython) and in CPython with the `opensim` package.
- The 12 AnalyzeTool setup files point to `Models/<group>/<condition>.osim`; all 12 files are included and the names match.
- The 13 .osim files: OpenSim format 40600 (4.x), 92 muscles each, total mass 70.0 kg, no absolute paths; bone meshes (.vtp) are
  taken from the OpenSim 4.6 installation (Geometry folder) - without it the model still runs, only the bones are not drawn.
- With the models included, a user can also open `Models/<group>/<condition>.osim` in the GUI and run Tools > Analyze with the
  condition's `_Setup_MuscleAnalysis.xml` directly, without running the script first. Running the script again re-writes the models.
