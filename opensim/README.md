# OpenSim Run

Wearable knee assist (SDP-II): OpenSim 4.6 knee static optimisation, **without** and **with** the pneumatic knee actuator, in one repository with one launcher.

| Folder | What it is | Main script |
|---|---|---|
| `OpenSim_Project/` | Run **without actuator**: Healthy vs ACL (pre-op, 2, 4, 6, 12 months), 116 conditions | `Scripts/run_opensim_knee_SO.py` |
| `Actuator_Run/` | Run **with actuator**: final bladder actuator, Healthy + ACL 2 months, 44 conditions | `Scripts/run_actuator_bag_SO.py` |
| `RUN_OpenSim.bat` | One launcher for both runs | — |

## How to run

1. Install **OpenSim 4.6** at `C:\OpenSim 4.6`. If it is somewhere else, edit `OSIM` at the top of `RUN_OpenSim.bat`.
2. Put this folder on a path with **English letters only**, e.g. `C:\opensim-run`. OpenSim cannot open paths with non-ASCII (for example Arabic) letters.
3. Double-click `RUN_OpenSim.bat` and choose:
   - `1`: without actuator (116 conditions)
   - `2`: quick test without actuator (12 conditions)
   - `3`: with actuator (44 conditions)
   - `4`: both runs

   Or skip the menu: `RUN_OpenSim.bat 3`

Results:
- Without actuator: `OpenSim_Project/Results/OpenSim_SO/` (`run_log.txt`)
- With actuator: `Actuator_Run/Results/` (`run_log.txt`)

You can also run each script from the OpenSim GUI: **Scripts → Run…** → pick the `.py` file.

## Python post-processing (no OpenSim needed)

```
python OpenSim_Project/Scripts/run_all_python_steps.py
```
Needs pandas, numpy, scipy, matplotlib, openpyxl.

Actuator report: run `Actuator_Run/build_report.ps1` to rebuild `Actuator_Run/OpenSim_Actuator_Report.html`.

More details are in `OpenSim_Project/README.md` and `OpenSim_Project/Docs/HOW_TO_RUN_OpenSim.md`.

---

## Quick reference

- `OpenSim_Project`: the run **without** the actuator.
- `Actuator_Run`: the run **with** the actuator.
- Run `RUN_OpenSim.bat` and choose a number: 1 without actuator, 2 quick test, 3 with actuator, 4 both.
- OpenSim 4.6 must be installed, and the folder must be on a path written in English letters only.
