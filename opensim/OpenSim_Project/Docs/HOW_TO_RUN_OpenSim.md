# How to run the OpenSim step (one script)

## الخطوات (Steps)

1. فكّ ضغط `OpenSim_Project.zip` في مسار إنجليزي فقط (ASCII path)، مثل `C:\sdp2_opensim\OpenSim_Project`.
   لا تضع المجلد داخل مسار فيه حروف عربية، لأن OpenSim لا يفتح الملفات من مسار غير ASCII.
2. افتح **OpenSim 4.6** (GUI). لا تحتاج إلى فتح أي model.
3. من القائمة: **Scripts → Run…**، ثم اختر الملف `OpenSim_Project\Scripts\run_opensim_knee_SO.py`.
4. انتظر حتى تظهر في نافذة الرسائل (Messages) جملة `FINISHED: 116 of 116 conditions`، وقد يستغرق ذلك نحو 5 إلى 15 دقيقة. وللتجربة السريعة أولًا ضع `ONLY_PRIMARY_12 = True` (السطر 67) فيعمل على 12 حالة فقط.
5. لرسم الأشكال Fig03 و04 و08 و11 و14 و20 وإكمال جداول العضلات، شغّل:
   `python Scripts\05_postprocess_opensim_results.py`

## If something goes wrong

| Message in the log | Fix |
|---|---|
| `project folder not found` | Open the script in a text editor and set `PROJECT_DIR = r"C:\...\OpenSim_Project"` (line 53) |
| `gait2392_simbody.osim not found` | Set `MODEL_PATH` to your file, usually `C:\Users\<you>\Documents\OpenSim\4.6\Models\Gait2392_Simbody\gait2392_simbody.osim` |
| `scaling failed` | The run continues with the generic (unscaled) model, and this is written in `run_log.txt` |
| `native AnalyzeTool skipped` | Optional cross-check only; the static-optimization results are still complete |
| `ERROR in <condition>` | See `Results/OpenSim_SO/run_log.txt` for the cause |

## Alternative: Python instead of the GUI
```
conda create -n opensim -c opensim-org opensim matplotlib pandas openpyxl scipy
conda activate opensim
python Scripts\run_opensim_knee_SO.py
python Scripts\05_postprocess_opensim_results.py
```

## What the script writes
- `Models\gait2392_scaled_70kg_170cm.osim`, plus `Models\Healthy\*.osim` and `Models\ACL\*.osim` for the 12 primary conditions, each with the actuator `knee_assist_r` and its PrescribedController (set `SAVE_ALL_MODELS = True` to save all 116).
- `Results\OpenSim_SO\<condition>_SO_activation.sto / _SO_force.sto / _SO_moment_arm_knee.sto / _SO_summary.csv`
- `Results\OpenSim_SO\ALL_conditions_SO_summary.csv`, `ALL_conditions_SO_long.csv`, `run_log.txt`
- `Simulations\<condition>\MuscleAnalysis\*` (native OpenSim AnalyzeTool output, if available)

Settings you may change at the top of the script: `HIP_FLEXION_DEG`, `ANKLE_ANGLE_DEG` (default 0, since no data exist),
`QUAD_STRENGTH_FACTOR` (default 1.0; use < 1 to test quadriceps weakness), `ONLY_PRIMARY_12`.
