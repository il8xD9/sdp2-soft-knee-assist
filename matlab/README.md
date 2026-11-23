# MATLAB / Simulink model of the pneumatic system (Rev 27)

Time-domain model of the pneumatic system of the knee assist (one leg): pump receiver, inlet and exhaust valves,
4 mm tube, bladder and the controller logic, run over the stance phase of the reference patient. It gives the
pneumatic results of the final report (set point, venting, fault cases, air supply) and draws the pneumatic and
analytical figures of the report (Figures 4.2, 4.8–4.10, 5.4–5.6, 6.7–6.12, M.2–M.9 and M.11–M.14).

All files are in this one folder; the scripts find each other and their output folder by themselves.

## Requirements

- MATLAB with Simulink (checked with MATLAB R2026b). Simulink is needed only for the Simulink check
  (`run27_simulink`, `sim_ka_simulink`, `make_report_figures('simulink')`).
- Input data in `data/`: `B3_deficit.csv`, `B3_patient_moment_opt2.csv` and `B4_knee_angle.csv`
  (stance-phase deficit, patient moment and knee angle of the reference patient). These files are needed to
  reproduce the values of the report. Without them the model still runs, but `ka_gait_data` uses a built-in
  approximation of the curves and the results differ from the report.

## How to run

Open MATLAB, set the current folder to `matlab/`, then:

| Step | Command | Time | What it gives |
|---|---|---|---|
| 1. Quick test | `ka_quick_demo` | 1–2 min | One stride at the design point: pressure, torque, valve states |
| 2. Report figures | `make_report_figures` | about 4 min | Analytical figures 4.2, 4.8, 4.9, 4.10, 6.10, M.2–M.4; copies the simulation figures of the last full run |
| | `make_report_figures('simulink')` | 5–15 min | as above, and rebuilds and checks the Simulink model (Figures 5.5, 5.6, M.6–M.9) |
| | `make_report_figures('full')` | 1–1.5 h | runs the whole model first, then every report figure |
| 3. Whole model | `run_all_rev27` | 1–1.5 h | Every study (N1–N7) and `results/rev27_results.csv`, each value next to its hand calculation |

Output goes to `results/` and `results/report_figures/` (PNG and FIG); `report_figure_index.csv` lists which
report figure each file is. The `results/` folder is made by the run and is not stored in the repository.

## Files

| Group | Files | Purpose |
|---|---|---|
| Start here | `ka_quick_demo.m`, `make_report_figures.m`, `run_all_rev27.m` | Quick test, report figures, whole model |
| Inputs and parameters | `ka_params.m`, `ka_setup.m`, `ka_prepare.m`, `ka_derived.m`, `ka_set_option.m`, `ka_set_window.m`, `ka_case.m`, `ka_default_cfg.m`, `ka_gait_data.m`, `ka_deficit.m`, `ka_torque_req.m`, `ka_print_hardware.m` | All model inputs in one place (`ka_params.m`), pressure case, assistance window, gait curves |
| Pneumatic plant | `ka_plant_deriv.m`, `ka_iso6358.m`, `ka_series_flow.m`, `ka_tube_dp.m`, `ka_lookup_in.m`, `ka_lookup_ex.m`, `ka_excol.m`, `ka_exhaust_from_qn.m`, `ka_relief_flow.m`, `ka_stuck_open.m`, `ka_open_fill.m`, `ka_ff.m` | Valve flow (ISO 6358), tube loss, bladder energy balance, receiver |
| Controller and simulation | `ka_logic_step.m`, `ka_fill_timing.m`, `ka_simulate.m` | Controller rules, fill timing, time stepping |
| Measures | `ka_metrics_demand.m`, `ka_metrics_pulse.m`, `ka_metrics_fault.m`, `ka_report.m` | N1–N7 measures; model value next to the hand calculation |
| Studies | `run27_inputs.m`, `run27_n1_n4.m`, `run27_n2_n3.m`, `run27_n5.m`, `run27_n6.m`, `run27_n7.m`, `ka_get_P.m` | N1/N4 onset pressure and knee flexion, N2/N3 set point and exposure, N5 fail-safe venting, N6 wrong-time assistance, N7 air supply and pump duty |
| Simulink | `knee_assist_rev27.slx`, `build_ka_simulink.m`, `ka_simulink_setup.m`, `sl_ka_logic.m`, `sl_ka_plant.m`, `sim_ka_simulink.m`, `run27_simulink.m` | Simulink version of the same model and its check against the script model |
| Report figures | `rpt_base.m`, `rpt_fig_4_2.m`, `rpt_fig_4_8.m`, `rpt_fig_4_9.m`, `rpt_fig_6_10.m`, `rpt_fig_M2.m`, `rpt_fig_M3.m`, `rpt_fig_M4.m`, `rpt_folder.m`, `rpt_savefig.m` | One file per analytical report figure |
| Plot helpers | `ka_colours.m`, `ka_savefig.m`, `ka_system_diagram.m` | Colours, figure saving, system diagram (Figure 4.10) |

The equations of the model are given in Appendix I and the hand calculations it is checked against in Appendix J
of the final report ([`../appendices/`](../appendices/)).
