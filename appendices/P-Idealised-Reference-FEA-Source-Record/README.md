# Appendix P – Idealised Reference FEA: Source Record

Appendix P of the SDP II final report *Analytical and Simulation-Based Feasibility Study of a Soft Pneumatic Knee Assist Concept for Post-ACL Reconstruction Gait*.

- **File:** [Appendix_P.pdf](Appendix_P.pdf) (47 pages, 1497 kB)
- **All appendices:** [list A–P](../)

## Contents

- Symbols, abbreviations and names used in this report
- §1 Summary
- §2 Task, scope and what changed during the work
- §3 The hand calculation being checked
- §4 Model and set-up
  - §4.1 Geometry
  - §4.2 The core model (what is in, what is out)
  - §4.3 Materials and properties
  - §4.4 Boundary conditions and kinematics
  - §4.5 Pressure loading
  - §4.6 Load sequences
  - §4.7 Solver settings
- §5 Assumptions - hand calculation and FEA side by side
- §6 Making the model converge - problems, causes, fixes and evidence
- §7 Results
  - §7.1 Run matrix and solver status
  - §7.2 Fixed-angle cases - FEA against p k
  - §7.3 Gait cycles - window 13-36 % stance
  - §7.4 Pressure and volume
  - §7.5 Stresses and factor of safety
  - §7.6 Deformed shape
  - §7.7 Assist ratio given to the patient
- §8 Discussion - why the FEA and the hand calculation differ where they differ
- §9 Conclusions
- §10 Limitations
- §11 Recommended next steps
- Appendix B - Error log (E-60 onwards)

## Model files

The finite element model, scripts and results of this appendix, organised for readers, are in [`fea/`](../../fea/) of this repository.

## Note

The pages are the same as in the final report, except that in the error log of Appendix P (report pages 370, 371 and 376) a local Windows folder path was replaced by `<PROJECT>`.
