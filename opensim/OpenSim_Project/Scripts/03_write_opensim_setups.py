#!/usr/bin/env python3
"""
03_write_opensim_setups.py
--------------------------
PURPOSE : Write one OpenSim AnalyzeTool setup file per condition
          (Simulations/<folder>/<cond>_Setup_MuscleAnalysis.xml) running the native
          MuscleAnalysis (moment arms, fibre lengths, multipliers about knee_angle_r) and
          Actuation (force of 'knee_assist_r' read from the model's PrescribedController).
          The files can be run by run_opensim_knee_SO.py automatically, or by hand in the
          GUI: Tools > Analyze... > Load... (select the setup) > Run.
          Paths are relative to the setup file, so the project folder can be moved.
INPUT   : Simulations/conditions_manifest.csv
OUTPUT  : Simulations/<folder>/<cond>_Setup_MuscleAnalysis.xml
"""
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM = os.path.join(ROOT, "Simulations")
man = pd.read_csv(os.path.join(SIM, "conditions_manifest.csv"))

TEMPLATE = """<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40000">
  <AnalyzeTool name="{cid}">
    <!-- model written by Scripts/run_opensim_knee_SO.py (gait2392 + knee_assist_r actuator) -->
    <model_file>{model}</model_file>
    <replace_force_set>false</replace_force_set>
    <force_set_files />
    <results_directory>./MuscleAnalysis</results_directory>
    <output_precision>8</output_precision>
    <initial_time>{t0:.6f}</initial_time>
    <final_time>{t1:.6f}</final_time>
    <solve_for_equilibrium_for_auxiliary_states>true</solve_for_equilibrium_for_auxiliary_states>
    <maximum_number_of_integrator_steps>20000</maximum_number_of_integrator_steps>
    <maximum_integrator_step_size>1</maximum_integrator_step_size>
    <minimum_integrator_step_size>1e-08</minimum_integrator_step_size>
    <integrator_error_tolerance>1e-05</integrator_error_tolerance>
    <AnalysisSet name="Analyses">
      <objects>
        <MuscleAnalysis name="MuscleAnalysis">
          <on>true</on>
          <start_time>{t0:.6f}</start_time>
          <end_time>{t1:.6f}</end_time>
          <step_interval>1</step_interval>
          <in_degrees>true</in_degrees>
          <muscle_list> all</muscle_list>
          <moment_arm_coordinate_list> knee_angle_r</moment_arm_coordinate_list>
          <compute_moments>true</compute_moments>
        </MuscleAnalysis>
        <Actuation name="Actuation">
          <on>true</on>
          <start_time>{t0:.6f}</start_time>
          <end_time>{t1:.6f}</end_time>
          <step_interval>1</step_interval>
          <in_degrees>true</in_degrees>
        </Actuation>
      </objects>
      <groups />
    </AnalysisSet>
    <ControllerSet name="Controllers">
      <objects />
      <groups />
    </ControllerSet>
    <external_loads_file />
    <states_file />
    <coordinates_file>{mot}</coordinates_file>
    <speeds_file />
    <lowpass_cutoff_frequency_for_coordinates>-1</lowpass_cutoff_frequency_for_coordinates>
  </AnalyzeTool>
</OpenSimDocument>
"""

n = 0
for _, c in man.iterrows():
    folder = os.path.join(SIM, c["folder"])
    group = "Healthy" if str(c["group"]).startswith("Healthy") else "ACL"
    model_abs = os.path.join(ROOT, "Models", group, c["cond_id"] + ".osim")
    model_rel = os.path.relpath(model_abs, folder).replace(os.sep, "/")
    xml = TEMPLATE.format(cid=c["cond_id"], model=model_rel, t0=c["t_start"], t1=c["t_end"],
                          mot=c["mot"])
    with open(os.path.join(folder, c["cond_id"] + "_Setup_MuscleAnalysis.xml"), "w") as f:
        f.write(xml)
    n += 1
print("setup files written:", n)
