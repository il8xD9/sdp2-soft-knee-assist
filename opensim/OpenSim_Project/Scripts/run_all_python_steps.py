#!/usr/bin/env python3
"""
run_all_python_steps.py - re-runs every NON-OpenSim step in order (CPython 3 with pandas,
numpy, scipy, matplotlib, openpyxl):
   01 extract data -> 02 build conditions/actuator -> 03 OpenSim setup files ->
   04 computed results/figures/tables -> 06 verification -> 05 muscle results (only if the
   OpenSim run exists)
The OpenSim step itself is Scripts/run_opensim_knee_SO.py (run it in OpenSim).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
steps = ["01_extract_input_data.py", "02_build_conditions.py", "03_write_opensim_setups.py",
         "04_analysis_figures_tables.py", "06_verification_checks.py",
         "08_plot_knee_healthy_vs_ACL2mo.py"]
so = os.path.join(os.path.dirname(HERE), "Results", "OpenSim_SO", "ALL_conditions_SO_summary.csv")
if os.path.isfile(so):
    steps.append("05_postprocess_opensim_results.py")
else:
    print("NOTE: OpenSim results not found -> step 05 skipped (run run_opensim_knee_SO.py first).")
for s in steps:
    print("\n=== %s ===" % s)
    r = subprocess.run([sys.executable, os.path.join(HERE, s)], cwd=HERE)
    if r.returncode != 0:
        sys.exit("step failed: " + s)
print("\nall steps finished.")
