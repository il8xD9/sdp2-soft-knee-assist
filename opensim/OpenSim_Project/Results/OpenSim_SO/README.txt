OpenSim static-optimization results - EXECUTED
Run: 27 Oct 2026, OpenSim 4.6 GUI (Jython 2.5.2), Scripts/run_opensim_knee_SO.py
116 of 116 conditions in 69.4 s (quick test 12/12 in 23.5 s before). See run_log.txt.
Baseline: CALC-BIO-03 inputs, CAD V4.1 actuator (T_max = 10.7555 N.m), working case alpha = 0.20.
Checks: device torque read back from the model = input file (max diff <= 8.9e-16 N.m);
max |reserve| <= 0.013 N.m; baselines identical to the quick test and to the 8 Oct run.
Post-processed by Scripts/05_postprocess_opensim_results.py (window = actuator torque > 1e-6 N.m;
baseline antagonists evaluated over the same window as the assisted case).
