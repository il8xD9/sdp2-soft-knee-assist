# Finite element analysis of the knee bladder – idealised reference model

Autodesk Inventor Nastran 2026, SOL 106 (nonlinear static, large displacement, follower pressure).
**Report:** [`report/FEA_Idealised_Reference_Report.pdf`](report/FEA_Idealised_Reference_Report.pdf)

> **What this model is.** The device is a TPU bladder in a fabric cover behind the knee; air pressure in the bladder
> pushes the knee into extension. The analytical design model (Model B of the final report) treats the thigh and shank
> as two rigid halves turning about the knee axis and gives the knee moment **M = p·k**, with k = 206 990 mm³, i.e.
> 0.207 N·m per kPa. This FEA uses exactly those assumptions – rigid leg halves, bladder bonded to them, no soft tissue,
> no pad, no straps, no friction – to check the formula and the way the moment is read from the FEA. It is not the moment
> of the real device on a leg.

## Results

| Case | 20 kPa | 40 kPa | 60 kPa |
|---|---|---|---|
| Knee fixed at 3° – FEA / p·k | 1.06 | 1.06 | 1.08 |
| Knee fixed at 7.28° – FEA / p·k | 1.39 | 1.28 | not reached (run stopped at about 41 kPa) |
| Gait cycle, peak frame 21 % stance (5.78°) – FEA / p·k | 1.66 | 1.24 | not reached (run stopped after 13 % stance) |
| Assist ratio α = device moment / patient's deficit, 21 % stance | 0.209 | 0.312 | – |

- **Model B is confirmed** where its assumptions hold: at 3° the FEA moment is linear in pressure and within 6–8 % of p·k.
- **At larger knee angles the FEA gives more than p·k**, because the inflated bladder bulges in the fold and the section
  the pressure acts on grows; Model B uses the undeformed cavity.
- **Project pressure profile** (6.9 → 20 → 2.8 kPa over 13–36 % stance): 6.89 N·m at 21 % stance, α = 0.209 = 104 % of
  the target (0.20 × 33 N·m = 6.60 N·m).
- **Stresses** up to 60 kPa: factor of safety 8.5 or more for the bladder, 1.9 or more for the cover.
- **Fold states:** the folded bladder can sit in more than one stable shape at the same angle and pressure. The moment of
  the lower-energy shape is used; the other frames are marked in the tables (`fold_state`).
- **Limits of the model:** the fixed-angle cases at 8.63°–19° stopped while the empty device was being bent (the fold and
  the cover wrinkle at about 5.4–7.9°). The angles that were reached (3° and 7.28°) bracket the assist window (3.28–5.78°).

## Runs

| Name in the final report | Run folder | Case |
|---|---|---|
| A3 | `CHK_FB` | knee fixed at 3.00°, 20–60 kPa |
| A7.3, A8.6, A9.8 | `HC_A7.3`, `HC_A8.6`, `HC_A9.8` | knee fixed at 7.28°, 8.63°, 9.78° (window angles + 4°) |
| A13, A16, A19 | `HC_A13.0`, `HC_A16.0`, `HC_A19.0` | knee fixed at 13°, 16°, 19° |
| C0, C20, C40, C60 | `HCC_P0`, `HCC_P20`, `HCC_P40`, `HCC_P60` | gait cycle, 0 (vented) / 20 / 40 / 60 kPa in the window 13–36 % stance |
| CP | `HCC_PROJ` | gait cycle with the project pressure profile |

## Folders

| Folder | Content |
|---|---|
| [`report/`](report/) | The FEA report (PDF) |
| [`results/tables/`](results/tables/) | `cycle_moment.csv` (every gait-cycle frame), `assist_ratio.csv`, `cycle_summary.csv`, `margin_moment.csv` |
| [`results/figures/`](results/figures/) | Every figure of the report |
| [`model/`](model/) | Mesh (`mesh_M0.pkl`), and one folder per run with the Nastran input deck (`.nas`), its mesh, step list and leak check; `run_list.txt` |
| [`runs/`](runs/) | Per run: solver log (`.LOG`), results (`_results.csv` / `.xlsx`), convergence history, run time |
| [`inputs/`](inputs/) | Knee angle and knee moments of the reference patient per stance frame |
| [`cad/`](cad/) | `inventor/`: Inventor CAD of the device (reference only); `geometry/`: the code that builds the CAD geometry, from which the mesh is made |
| [`scripts/`](scripts/) | Mesh, decks, leak check, run queue, post-processing, tables, figures, report |

The raw solver output (`.OUT`, `.FNO`, `.RSF`, console logs; 0.45 GB as zips) is attached to the release
[`raw-solver-output`](https://github.com/il8xD9/sdp2-soft-knee-assist/releases/tag/raw-solver-output), one zip per run.
Unzip a zip inside this `fea/` folder; each file lands in `runs/<run>/`.

## Re-run

Needs Autodesk Inventor Nastran 2026 (licensed), Windows PowerShell, Python 3 (`pip install -r requirements.txt`) and bash
(for example Git Bash). All commands start in this `fea/` folder.

```bash
# 1. (optional) rebuild the mesh and the 12 decks; they come out identical to the committed ones
bash scripts/build_decks.sh --mesh
```

```powershell
# 2. solve, one deck at a time (about 18 h for all 12 runs; each run is post-processed automatically)
powershell -ExecutionPolicy Bypass -File scripts\run_queue.ps1 -ListFile model\run_list.txt -Ram 2000 -Np 4 -StallMin 45
#    add -Exe "<path to Nastran.exe>" if Inventor Nastran is not in its default folder
```

```bash
# 3. tables, figures and report (step 3 also works with the raw output from the release instead of step 2)
cd scripts
python -P collect_cycles.py --ref_cyc HCC --ref_ang HC --p0_load_branch --stance_max 36 --state_flag
python -P assist_ratio.py
python -P make_figures.py          # needs the .OUT files; --skip_out draws only the charts
python -P build_report.py          # writes report/FEA_Idealised_Reference_Report.docx
```

The committed decks, result tables and figures were rebuilt from these scripts and the raw output, and came out the same.

## Source of the patient data

The knee-angle and knee-moment waveforms of the reference patient (man, 70 kg, 1.70 m, two months after ACL
reconstruction) and of healthy controls were digitised from C. Büttner et al., "Bilateral waveform analysis of gait
biomechanics presurgery to 12 months following ACL reconstruction compared to controls," *J. Orthop. Res.*, vol. 43,
no. 2, pp. 322–336, 2025, doi: [10.1002/jor.26001](https://doi.org/10.1002/jor.26001).
