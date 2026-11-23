# Models folder

The OpenSim models are generated ON YOUR COMPUTER by `Scripts/run_opensim_knee_SO.py`, because the
base model (OpenSim's bundled `gait2392_simbody.osim`, 23 DOF / 92 muscles) is part of your OpenSim
installation and could not be downloaded into the cloud workspace (no network access there).

After the run this folder contains:

| File | Content |
|---|---|
| `gait2392_scaled_70kg_170cm.osim` | gait2392 uniformly scaled x0.9444 (1.70 / 1.80 m), mass 70 kg |
| `Healthy/<condition>.osim` | scaled model + `knee_assist_r` actuator + PrescribedController (healthy conditions) |
| `ACL/<condition>.osim` | same for every ACL epoch / alpha condition |

Bodies, joints (hip, knee, ankle), coordinates, ground and the 92 Hill-type muscles are those of gait2392.
No external loads / contact elements are added because no GRF/COP data exist (see Docs).
