# Models folder

The OpenSim models in this folder are written by `Scripts/run_opensim_knee_SO.py` from OpenSim's bundled
`gait2392_simbody.osim` (23 DOF / 92 muscles), which is part of the OpenSim 4.6 installation.
Running the script again re-writes them.

This folder contains:

| File | Content |
|---|---|
| `gait2392_scaled_70kg_170cm.osim` | gait2392 uniformly scaled x0.9444 (1.70 / 1.80 m), mass 70 kg |
| `Healthy/<condition>.osim` | scaled model + `knee_assist_r` actuator + PrescribedController (healthy conditions) |
| `ACL/<condition>.osim` | same for every ACL epoch / alpha condition |

Bodies, joints (hip, knee, ankle), coordinates, ground and the 92 Hill-type muscles are those of gait2392.
No external loads / contact elements are added because no GRF/COP data exist (see Docs).
