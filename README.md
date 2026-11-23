# Soft pneumatic knee assist after ACL reconstruction – SDP II

**Analytical and Simulation-Based Feasibility Study of a Soft Pneumatic Knee Assist Concept for Post-ACL Reconstruction Gait**

Design Project II (ME 400_481) · Yanbu Industrial College · 1st Semester 2026–2027

| Team members |
|---|
| Mohannad Ahmed Aljawi |
| Nawaf Ahmed Masoud |
| Meshal Baothman |
| Basem Aymen Aljohani |

Supervised by Dr. Akram Faqeeh

## Abstract 

After anterior cruciate ligament reconstruction (ACLR), quadriceps weakness persists and published gait data show a smaller internal knee-extension moment in the operated limb during the first half of stance. This project assesses, by calculation and simulation only, whether a wearable soft-pneumatic device, a thermoplastic-polyurethane bladder behind the knee filled and vented once per stride, can supply part of that missing moment.

For a reference patient (70 kg, 1.70 m, two months after ACLR) the deficit, derived from digitised published waveforms, peaks at 33 N·m at 21 % of stance; the torque target, an engineering test value and not a clinical prescription, is a fraction α = 0.20 of it, 6.60 N·m. An adopted design limit of 20 kPa on the mean skin contact pressure, derived from pain data of a knee cuff in healthy adults with an assumed patient factor, sets the design point at a bladder pressure of 20 kPa(g).

Under rigid coupling, the ideal capability at this pressure lies between 4.14 N·m (analytical design basis, 63 % of the target) and about 6.9 N·m (idealised finite element model at the gait peak), so whether the target is reachable even in the ideal case is not settled. A finite element model of the complete device on a soft leg predicts at most 0.12 N·m at 20 and 27 kPa(g) (not mesh-converged): the transfer of the bladder force to the knee is the main open problem. The modelled pneumatic system holds its set point and vents in time; with two inlet valves it misses 5.7 % of the requested torque–time, the swing-squeeze requirement is not met and the pump runs above its documented continuous-duty limit.

The feasibility study was completed; on the analytical design basis the studied device does not reach its torque target, and the moment it would transfer to the knee is not established. All results are calculated or simulated, not measured, and no safety or clinical claim is made.

## Contents

```
sdp2-soft-knee-assist/
├── appendices/   Appendices A–P of the final report (PDF)
├── opensim/      Musculoskeletal model: knee moments and muscle forces (OpenSim 4.6)
├── matlab/       Pneumatic system model: valves, bladder, controller (MATLAB / Simulink)
└── fea/          Finite element model of the bladder actuator (Inventor Nastran)
```

| Folder | What it holds | Software | Start with |
|---|---|---|---|
| [`appendices/`](appendices/) | Appendices A–P of the final report: [all in one PDF](appendices/SDP_II_Final_Report_Appendices_A-P.pdf) (236 pages, with bookmarks) and one folder per appendix. | PDF reader | [`appendices/README.md`](appendices/README.md) |
| [`opensim/`](opensim/) | Knee static optimisation of a healthy subject and of ACL patients (pre-op, 2, 4, 6 and 12 months), without the device (116 conditions) and with the bladder actuator (44 conditions): models, inputs, results, tables and figures. | OpenSim 4.6; Python 3 for post-processing | [`opensim/README.md`](opensim/README.md) |
| [`matlab/`](matlab/) | Time-domain model of the pneumatic system (Rev 27): set point, venting, fault cases, air supply, and the pneumatic and analytical figures of the report. | MATLAB + Simulink | [`matlab/README.md`](matlab/README.md) |
| [`fea/`](fea/) | The idealised reference finite element model of the bladder (Appendix P): [report](fea/report/FEA_Idealised_Reference_Report.pdf), results, input decks, CAD and scripts. | Autodesk Inventor Nastran 2026; Python 3 | [`fea/README.md`](fea/README.md) |

The raw solver output of the FEA (12 zip files, 0.45 GB) is attached to the release
[`raw-solver-output`](https://github.com/il8xD9/sdp2-soft-knee-assist/releases/tag/raw-solver-output).

To download everything: **Code → Download ZIP** on this page (the release zips are downloaded separately).

## Appendices

| Appendix | Title | Pages |
|---|---|---|
| [A](appendices/A-FEA-Result-Tables/) | [FEA Result Tables](appendices/A-FEA-Result-Tables/Appendix_A.pdf) | 16 |
| [B](appendices/B-CAD-Component-Dimensions-and-Drawings/) | [CAD Component Dimensions and Drawings](appendices/B-CAD-Component-Dimensions-and-Drawings/Appendix_B.pdf) | 7 |
| [C](appendices/C-Simulation-Record/) | [Simulation Record](appendices/C-Simulation-Record/Appendix_C.pdf) | 7 |
| [D](appendices/D-Biomechanics-Calculation-Record/) | [Biomechanics Calculation Record](appendices/D-Biomechanics-Calculation-Record/Appendix_D.pdf) | 1 |
| [E](appendices/E-Equation-Parameter-Assumption-and-Conflict-Registers/) | [Equation, Parameter, Assumption and Conflict Registers](appendices/E-Equation-Parameter-Assumption-and-Conflict-Registers/Appendix_E.pdf) | 20 |
| [F](appendices/F-Open-Technical-Issues/) | [Open Technical Issues](appendices/F-Open-Technical-Issues/Appendix_F.pdf) | 4 |
| [G](appendices/G-Governing-Equations-and-Derivations/) | [Governing Equations and Derivations](appendices/G-Governing-Equations-and-Derivations/Appendix_G.pdf) | 6 |
| [H](appendices/H-Supplementary-Design-Calculations-and-Material-Data/) | [Supplementary Design Calculations and Material Data](appendices/H-Supplementary-Design-Calculations-and-Material-Data/Appendix_H.pdf) | 19 |
| [I](appendices/I-Pneumatic-System-Equations/) | [Pneumatic System Equations](appendices/I-Pneumatic-System-Equations/Appendix_I.pdf) | 13 |
| [J](appendices/J-Pneumatic-Hand-Calculations/) | [Pneumatic Hand Calculations](appendices/J-Pneumatic-Hand-Calculations/Appendix_J.pdf) | 17 |
| [K](appendices/K-Project-Records-Member-Schedules-and-Meeting-Minutes/) | [Project Records: Member Schedules and Meeting Minutes](appendices/K-Project-Records-Member-Schedules-and-Meeting-Minutes/Appendix_K.pdf) | 5 |
| [L](appendices/L-Development-Record-of-the-Earlier-Design-Stages/) | [Development Record of the Earlier Design Stages](appendices/L-Development-Record-of-the-Earlier-Design-Stages/Appendix_L.pdf) | 38 |
| [M](appendices/M-Supplementary-Evidence-of-the-Design-Record/) | [Supplementary Evidence of the Design Record](appendices/M-Supplementary-Evidence-of-the-Design-Record/Appendix_M.pdf) | 17 |
| [N](appendices/N-Pneumatic-Results-Detailed-Discussion-Record/) | [Pneumatic Results: Detailed Discussion Record](appendices/N-Pneumatic-Results-Detailed-Discussion-Record/Appendix_N.pdf) | 10 |
| [O](appendices/O-Tissue-Tolerance-Workbook-Record/) | [Tissue-Tolerance Workbook Record](appendices/O-Tissue-Tolerance-Workbook-Record/Appendix_O.pdf) | 9 |
| [P](appendices/P-Idealised-Reference-FEA-Source-Record/) | [Idealised Reference FEA: Source Record](appendices/P-Idealised-Reference-FEA-Source-Record/Appendix_P.pdf) | 47 |

The pages are the same as in the final report, except that in the error log of Appendix P (report pages 374, 375 and 380)
a local Windows folder path was replaced by `<PROJECT>`.

## Licence

All rights reserved; see [LICENSE](LICENSE).
