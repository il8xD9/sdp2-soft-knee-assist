# -*- coding: utf-8 -*-
r"""Builds the FEA report (Word) from the results in this folder.
Inputs: runs/<run>/<run>_results.csv, runtime.txt, .LOG (post_process.py, run_queue.ps1); results/tables (collect_cycles.py,
assist_ratio.py); results/figures (make_figures.py).
Usage: python -P build_report.py   -> report/FEA_Idealised_Reference_Report.docx"""
import csv, datetime, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(HERE); sys.path.insert(0, HERE)
from docx_helpers import Doc, r, fr, sb, par, f2          # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH            # noqa: E402

IMG = os.path.join(R, "results", "figures"); TAB = os.path.join(R, "results", "tables")
K = 0.20699                                   # N m per kPa (k = 206 990 mm3)
ANG = [("3.00", "CHK_FB"), ("7.28", "HC_A7.3"), ("8.63", "HC_A8.6"), ("9.78", "HC_A9.8"), ("13.00", "HC_A13.0"),
       ("16.00", "HC_A16.0"), ("19.00", "HC_A19.0")]
CYC = ["HCC_P0", "HCC_P20", "HCC_PROJ", "HCC_P40", "HCC_P60"]
NAME = {"CHK_FB": "A3", "HC_A7.3": "A7.3", "HC_A8.6": "A8.6", "HC_A9.8": "A9.8", "HC_A13.0": "A13", "HC_A16.0": "A16",
        "HC_A19.0": "A19", "HCC_P0": "C0", "HCC_P20": "C20", "HCC_P40": "C40", "HCC_P60": "C60", "HCC_PROJ": "CP"}
LIM_BL, LIM_COV = 11.1, 37.2
REFS = [
    ("rep", "SDP II team, \"Analytical and Simulation-Based Feasibility Study of a Soft Pneumatic Knee Assist Concept for "
            "Post-ACL Reconstruction Gait\", final report, Yanbu Industrial College, 2026: Model B (Section 4.3.3), FEA "
            "(Sections 5.3, 6.3), material selection (Appendix H.6), idealised reference record (Appendix P)."),
    ("bt", "C. Büttner et al., \"Bilateral waveform analysis of gait biomechanics presurgery to 12 months following ACL "
           "reconstruction compared to controls,\" J. Orthop. Res., vol. 43, no. 2, pp. 322-336, 2025, doi:10.1002/jor.26001."),
    ("nas", "Autodesk Inventor Nastran 2026 (ADS NASTRAN 20.2), SOL 106 nonlinear static analysis, user documentation."),
]
RN = {k: i + 1 for i, (k, _) in enumerate(REFS)}


def c(*k):
    return "[" + ", ".join(str(RN[x]) for x in k) + "]"


def fl(v):
    try: return float(v)
    except (TypeError, ValueError): return None


def load(run):
    f = os.path.join(R, "runs", run, run + "_results.csv")
    if not os.path.exists(f): return None
    rows = list(csv.DictReader(open(f)))
    for x in rows:
        for k, v in list(x.items()):
            if k not in ("name", "kind"):
                fv = fl(v)
                if fv is not None or v == "": x[k] = fv
        x["converged"] = str(x.get("converged")) in ("True", "1", "1.0")
    return rows


def runtime(run):
    f = os.path.join(R, "runs", run, "runtime.txt")
    if not os.path.exists(f): return None, None
    t = open(f, encoding="utf-8-sig").read()
    s = re.search(r"seconds=(\d+)", t); m = re.search(r"peakMB=(\d+)", t)
    return (int(s.group(1)) if s else None), (int(m.group(1)) if m else None)


def csvrows(name):
    rows = list(csv.DictReader(open(os.path.join(TAB, name))))
    for x in rows:
        for k, v in list(x.items()):
            fv = fl(v)
            if fv is not None or v == "": x[k] = fv
    return rows


def angle_data():
    out = []
    for a, run in ANG:
        rr = load(run)
        vb = [x for x in rr if x["kind"] == "S" and x["converged"]]
        tgt = max(x["theta"] for x in rr if x["kind"] == "S")
        if not vb or abs(vb[-1]["theta"] - tgt) > 0.02:          # the vented bending stopped before the case angle
            ok_s = [x["theta"] for x in rr if x["kind"] in ("S", "S_sub") and x["converged"]]
            out.append(dict(angle=float(a), run=run, status="not reached", reached=max(ok_s) if ok_s else 0.0)); continue
        m0 = vb[-1]["M_knee_ext_Nm"]; v0 = vb[-1]["V_bladder_mid_cm3"]
        for x in rr:
            if x["kind"] != "W" or x["p_kPa"] > 60: continue
            md = (x["M_knee_ext_Nm"] - m0) if x["converged"] else None
            hc = K * x["p_kPa"]
            out.append(dict(angle=float(a), run=run, p=x["p_kPa"], conv=x["converged"], M=x["M_knee_ext_Nm"] if x["converged"] else None,
                            M0=m0, V0=v0, V=x["V_bladder_mid_cm3"] if x["converged"] else None, dev=md, hc=hc,
                            ratio=(md / hc if md is not None else None), status="ok"))
    return out


def main():
    out_dir = os.path.join(R, "report"); os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "FEA_Idealised_Reference_Report.docx")
    AD = angle_data(); CM = csvrows("cycle_moment.csv"); AS = csvrows("assist_ratio.csv")

    def asg(run, f):
        return next((x for x in AS if x["run"] == run and x["stance_pct"] == f), None)
    RUNS = [run for _, run in ANG] + CYC
    LD = {run: load(run) for run in RUNS}
    D = Doc()
    nm = lambda run: "%s (%s)" % (NAME[run], run)

    # ================================================================= title
    D.P("SDP II - Soft pneumatic knee assist after ACL reconstruction", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
    D.P("Finite element analysis of the knee bladder: idealised reference model", bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
    D.P("Autodesk Inventor Nastran 2026, SOL 106 (nonlinear static, large displacement, follower pressure) - Yanbu Industrial "
        "College, November 2026", size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
    D.P("Idealised reference: the leg is two rigid halves hinged on the knee axis and the bladder is bonded to them; there is no "
        "soft tissue, no pad, no straps and no friction. The model checks the analytical moment M = p k and the way the moment is "
        "read from the FEA. It does not give the moment of the real device on a leg.", bold=True, size=9.5,
        align=WD_ALIGN_PARAGRAPH.CENTER)

    # ================================================================= 1 summary
    D.H("1. Summary")
    D.P("The device is a thermoplastic-polyurethane bladder in a fabric cover behind the knee. Air pressure in the bladder "
        "pushes the leg into extension. The analytical design model (Model B " + c("rep") + ") treats the thigh and shank as "
        "rigid halves turning about the knee axis and gives the knee moment M = p k. This FEA uses exactly the same assumptions "
        "and asks one question: does the finite element model give the same moment? If it does, the formula and the moment "
        "extraction are both confirmed.")
    ok_ang = [x for x in AD if x.get("ratio") is not None]
    rows = [["%.2f" % x["angle"], NAME[x["run"]], "%.0f" % x["p"], f2(x["dev"]), f2(x["hc"]), f2(x["ratio"])]
            for x in ok_ang if x["p"] in (20.0, 40.0, 60.0)]
    D.T(["Knee angle (deg)", "Run", "p (kPa)", "FEA device moment (N m)", "Model B p k (N m)", "FEA / p k"], rows,
        "Key result: fixed-angle cases (knee bent with the bladder vented, then inflated). Device moment = knee moment at p "
        "minus the vented moment at the same angle.", size=8.5, widths=[2.4, 1.6, 1.6, 3.4, 3.2, 2.2])
    r3 = [x["ratio"] for x in ok_ang if abs(x["angle"] - 3.0) < 0.01]
    nr = [x for x in AD if x.get("status") == "not reached"]
    a21 = {run: asg(run, 21) for run in ("HCC_PROJ", "HCC_P20", "HCC_P40")}
    pm = [x for x in AS if x["run"] == "HCC_PROJ" and x["fold_state"] == "main" and 18 <= x["stance_pct"] <= 27]
    for t in [
        "At 3 deg the FEA reproduces Model B within %.0f-%.0f %% over 20-60 kPa (FEA / p k = %s): the moment grows linearly "
        "with pressure and has the size the formula predicts." % (100 * (min(r3) - 1), 100 * (max(r3) - 1), " / ".join(f2(v) for v in r3)),
        "At 7.28 deg the FEA moment is above p k (1.39 at 20 kPa, 1.28 at 40 kPa). The reason is geometric: the FEA bladder "
        "inflates against its cover and bulges in the fold, so the section the pressure acts on is larger than the undeformed "
        "cavity used by Model B (Section 7).",
        "The fixed-angle cases at %s deg stopped while the empty device was being bent, before any pressure step: the fold "
        "and the cover side edges wrinkle at about 5.4-7.9 deg. The two angles that were reached, 3.00 and 7.28 deg, bracket "
        "the knee angles of the assist window (3.28-5.78 deg)." % ", ".join("%.2f" % x["angle"] for x in nr),
        "Gait cycle with the project pressure profile (6.9 -> 20 -> 2.8 kPa over 13-36 %% stance): %s N m at the peak frame "
        "(21 %% stance), i.e. %.0f %% of the design target of 6.59 N m (0.20 of the patient's knee-moment deficit of %s N m)." %
        (f2(a21["HCC_PROJ"]["M_device_Nm"]), 100 * a21["HCC_PROJ"]["device_over_target"], f2(a21["HCC_PROJ"]["deficit_Nm"])),
        "The folded bladder has more than one stable shape at the same angle and pressure; the moment of the lower-energy "
        "shape is used, the others are reported and marked (Section 6.3).",
        "Stresses up to 60 kPa stay below the allowable values: factor of safety 8.5 or more for the bladder and 1.9 or more "
        "for the cover (Section 6.5).",
        "Outside the scope of this reference: pressures above 60 kPa, stance after 36 % and the real device on a soft leg "
        "with straps and friction."]:
        D.B(t)

    # ================================================================= 2 runs
    D.H("2. Runs")
    runs_ = [["A3", "CHK_FB", "fixed angle 3.00 deg, 20-60 kPa"],
             ["A7.3, A8.6, A9.8", "HC_A7.3, HC_A8.6, HC_A9.8", "fixed angles 7.28, 8.63, 9.78 deg (window angles + 4 deg)"],
             ["A13, A16, A19", "HC_A13.0, HC_A16.0, HC_A19.0", "fixed angles 13, 16, 19 deg"],
             ["C0, C20, C40, C60", "HCC_P0, HCC_P20, HCC_P40, HCC_P60", "gait cycle at 0 (vented), 20, 40, 60 kPa in the window"],
             ["CP", "HCC_PROJ", "gait cycle with the project pressure profile"]]
    D.T(["Name in the final report", "Run folder", "Case"], runs_, "The 12 runs. Figures and tables of this repository use "
        "the run folder names.", size=8, widths=[3.6, 5.6, 8.0])

    # ================================================================= 3 hand calc
    D.H("3. The analytical model being checked (Model B)")
    D.P("Model B " + c("rep") + " treats the thigh and shank as rigid halves that turn about the knee axis. The bladder cavity "
        "is cut by the plane at the knee line; when the knee flexes by dθ the cavity loses the volume k dθ. With a constant "
        "gauge pressure p, the work of the air equals the work of the knee moment:")
    D.EQ(sb(r("M"), r("z")) + r(" = p ") + fr(r("dV"), r("dθ")) + r(" = p k,   k = ") +
         "<m:nary><m:naryPr><m:chr m:val=\"∫\"/><m:limLoc m:val=\"subSup\"/><m:subHide m:val=\"1\"/><m:supHide m:val=\"1\"/>"
         "</m:naryPr><m:sub/><m:sup/><m:e>" + r("ρ dA") + "</m:e></m:nary>",
         "M_z knee extension moment; p gauge pressure; V cavity volume; θ knee flexion (rad); ρ distance of the area element dA "
         "of the cavity section at the knee line from the knee axis. k = 206 990 mm³ with the knee axis 65 mm in front of the "
         "back skin, so p k = 0.207 N m per kPa (4.14 N m at 20 kPa, 8.28 at 40, 12.42 at 60).")
    D.P("Assumptions of Model B: rigid halves; the bladder halves turn with them (no pad shear, no tissue deformation, no "
        "slip); no losses; constant pressure; quasi-static. The FEA below reproduces this set-up, so p k is the value it "
        "should meet.")

    # ================================================================= 4 model
    D.H("4. Model")
    D.H("4.1 Geometry and mesh", 2)
    D.P("The bladder and its fabric cover are meshed from the same geometry code that built the CAD (cad/geometry), so the "
        "mesh follows the CAD exactly. The inlet port and the two vent ports are modelled as closed wall: the valves are closed "
        "during inflation and the tubes carry no load. The knee axis is the z line through x = 4.0573 mm, y = 0, 65 mm in front "
        "of the back skin; flexion turns the shank half towards +x.")
    D.F(os.path.join(IMG, "cad_asm10_iso.png"), "CAD of the device on the leg; the bladder and the cover are modelled.", 11)
    D.F(os.path.join(IMG, "cad_actV11_iso.png"), "The bladder (CAD). Inlet on the top face, two vents on the sides - closed in "
        "the model.", 9)
    D.P("The model keeps only the parts that Model B has: the bladder, the cover and two rigid leg halves. The bladder floor and "
        "the cover sewing flange are bonded to the rigid halves outside a 50 mm fold band (|y| < 25 mm) around the knee line. "
        "In that band the bladder wall has 1 % of its modulus along the leg (full modulus round the hoop), so it folds like the "
        "mitre of Model B and carries no axial force across the crease; the band floor follows a smoothly bent copy of the leg "
        "surface.")
    D.F(os.path.join(IMG, "mesh_core_model.png"), "Mesh: bladder (blue), fold band (orange), cover (grey, transparent). "
        "Undeformed, 0 deg.", 9.5)
    msh = [["Bladder body / end caps (CQUAD4 + CTRIA3)", "1824 / 228", "t 2.0 mm, mid-surface; mean edge 4.3 mm (1.8-5.6)"],
           ["  of which in the fold band |y| < 25 mm", "513", "1 % axial modulus"],
           ["Cover body / end caps / sewing flange", "1610 / 180 / 204", "t 0.43 mm; mean edge 4.5 mm"],
           ["Bladder-cover contact (BSCONP, frictionless)", "80 pairs", "117 577 slave x master segment products"],
           ["Grids / elements in the deck", "26 777 / 4046", "bladder grids 2026; bonded: floor 168 (78 in the band), flange 272"],
           ["Rigid halves", "836 thigh / 748 shank grids", "all degrees of freedom prescribed"]]
    D.T(["Item", "Count", "Note"], msh, "Mesh (level M0).", size=8, widths=[7.5, 3.5, 6.5])
    D.H("4.2 Materials", 2)
    mat = [["Bladder wall", "TPU, Elastollan 1185A", "isotropic: E 7.2 MPa, ν 0.49", "2.0"],
           ["Bladder in the fold band", "same TPU, folding", "orthotropic: E along the leg 0.072 MPa, hoop 7.2 MPa, G 0.024 MPa", "2.0"],
           ["Cover body", "TPU-coated nylon 6.6 fabric", "orthotropic: E along the leg 4.98 MPa, hoop 498 MPa, G 4.98 MPa", "0.43"],
           ["Cover end caps, flange, end-facing body", "same fabric", "isotropic: E 498 MPa, ν 0.35", "0.43"],
           ["Leg halves", "-", "rigid (prescribed motion)", "-"]]
    D.T(["Part", "Material", "Model data", "t (mm)"], mat, "Materials " + c("rep") + ". Allowable von Mises stress for the factor "
        "of safety: bladder 11.1 MPa, cover 37.2 MPa.", size=8, widths=[3.8, 3.6, 7.6, 1.6])
    D.H("4.3 Boundary conditions and moment", 2)
    for t in ["Thigh half fixed. The shank half is rotated about the knee axis by prescribed displacements - an exact rigid "
              "rotation, so the bladder end on the shank turns with the knee.",
              "Bladder floor and cover flange bonded to the halves outside the fold band; inside the band the floor grids turn "
              "by θ s(y), with s = 0 at y = +25 mm (thigh) and 1 at y = -25 mm (shank).",
              "Air pressure: follower load on all 2052 bladder shells. A check of every deck confirms a closed shell (no free "
              "edges) with pressure on every bladder element and on nothing else.",
              "Knee moment: sum over the shank-half reactions of (x - H) x F about the knee centre H, z component, + = extension.",
              "Gravity and inertia off (quasi-static, as Model B)."]:
        D.B(t)
    D.EQ(sb(r("M"), r("dev")) + par(r("p, θ")) + r(" = ") + sb(r("M"), r("knee")) + par(r("p, θ")) + r(" − ") +
         sb(r("M"), r("knee")) + par(r("0, θ")) + r(",    ratio = ") + fr(sb(r("M"), r("dev")), r("p k")),
         "Device moment = what the air adds to the moment of the vented (0 kPa) device at the same knee angle; the vented part is "
         "the passive bending of the empty bladder and cover. In the gait cycles M(0, θ) comes from run HCC_P0 at the same "
         "frame; after the peak angle it is read from the loading branch of HCC_P0 at the same angle.")
    D.H("4.4 Load cases", 2)
    seq = [["Fixed angle (CHK_FB, HC_A*)", "bend vented to the angle (sub-steps <= 2.5 deg) -> 20 -> 40 -> 60 kPa -> vented again",
            "M(p) - M(vented, same angle) against p k"],
           ["Cycle HCC_P0 / P20", "stance 1-50 % every 1 %: vented bending 1-12 %, fill in 5 steps at 13 %, window 13-36 % at p",
            "reported to 36 %"],
           ["Cycle HCC_PROJ", "as P20 to 36 %, with the project pressure profile (6.9 kPa at 13 % -> 20.0 at 21 % -> 2.8 at 36 %)",
            "41 subcases"],
           ["Cycle HCC_P40 / P60", "frames 3, 6, 9, 12 (vented), fill at 13, then 13, 15, 18, ..., 36 % (every 3 %)",
            "18 subcases"]]
    D.T(["Run type", "Sequence", "Note"], seq, "Load sequences. Knee angle per stance frame from the reference patient's gait "
        "data " + c("bt") + ": 3.28 deg at 13 %, peak 5.78 deg at 21 %, 4.63 deg at 36 %.", size=7.5, widths=[3.8, 9.2, 4.0])
    D.H("4.5 Solver settings", 2)
    D.P("SOL 106 nonlinear static with large displacement (PARAM LGDISP 1, follower pressure); each subcase starts from the "
        "previous one " + c("nas") + ". 2-8 increments per subcase, stiffness update every iteration, at most 25 iterations, "
        "convergence on displacement, load and work (0.01 / 0.01 / 0.001), up to 10 bisections. Slide-line contact "
        "stabilisation SLINESTABKSFACT 1e-4; full-integration hexahedra. One job at a time with 2000 MB solver memory and 4 "
        "processors.")

    # ================================================================= 5 assumptions + numerics
    D.H("5. Assumptions and numerical treatment")
    asm = [["Leg", "two rigid halves on the knee hinge", "same (rigid, prescribed rotation)", "same"],
           ["Knee axis", "65 mm in front of the back skin", "z through x 4.0573, y 0 (65 mm)", "same"],
           ["Bladder attachment", "cavity halves turn with thigh / shank", "floor and flange bonded outside the fold band", "same"],
           ["Crease", "sharp mitre, wall carries nothing across", "50 mm band with 1 % axial modulus, floor bent smoothly", "close"],
           ["Cavity section k", "inner cavity, undeformed, 206 990 mm³", "mid-surface of a 2 mm wall, inflates to the cover",
            "not the same: FEA k larger, grows with p and angle"],
           ["Pressure", "constant, uniform", "prescribed, uniform, follower", "same"],
           ["Cover", "not in the formula", "fabric cover, frictionless contact", "FEA adds the cover"],
           ["Tissue, pad, straps, friction", "none", "none", "same"],
           ["Passive bending of the empty device", "zero", "computed (vented) and subtracted", "handled by the device moment"]]
    D.T(["Item", "Model B", "FEA", "Match"], asm, "Assumptions compared.", size=7.5, widths=[3.4, 4.6, 5.4, 4.1])
    D.P("Numerical treatment. The thin bladder and cover fold and touch each other in the crease, which makes the static "
        "solution hard to follow. Four measures make the model converge: (1) the core model (bladder, cover and rigid halves "
        "only) - with the pad and straps on rigid halves the crease locked; (2) slide-line contact stabilisation 1e-4, which "
        "stops the contact status alternating between iterations - a check on the vented 3 deg case showed it adds 0.26 N m "
        "to the vented moment and cancels in the device moment except for its pressure-dependent part; (3) isotropic "
        "properties for end-facing cover elements, where the fabric's leg direction is not defined; (4) the band floor bonded "
        "to a smoothly bent leg surface instead of a contact support.")

    # ================================================================= 6 results
    D.H("6. Results")
    D.H("6.1 Solver status", 2)
    st = []
    for run in RUNS:
        rr = LD[run]; sec, mb = runtime(run)
        nconv = sum(1 for x in rr if x["converged"])
        st.append([run, NAME[run], "%d / %d" % (nconv, len(rr)), "%.1f" % (sec / 3600.0) if sec else "-", str(mb or "-"),
                   "%d" % sum(int(x["iterations"] or 0) for x in rr)])
    D.T(["Run", "Report name", "Subcases converged", "Time (h)", "Peak memory (MB)", "Iterations"], st,
        "Solver status. Where a subcase did not converge the run ended there; the converged subcases are used.", size=8,
        widths=[2.8, 2.2, 3.0, 2.0, 3.0, 2.4])
    D.F(os.path.join(IMG, "solver_iterations.png"), "Newton iterations per subcase for every run (0 = not reached).", 16)
    D.P("Where runs stopped: CHK_FB above about 70 kPa and HCC_P60 in the first window step after the fill (about 3.6 deg) - "
        "the cover end region at the shank end becomes unstable at high pressure once the knee moves; HC_A7.3 at about 41 kPa "
        "- the cover wrinkles sideways at its side edges; HC_A8.6 to HC_A19.0 while the empty device was being bent (5.4-7.9 "
        "deg). These are limits of the idealised static model at high pressure or large angle; the assist window (3.28-5.78 "
        "deg, up to 40 kPa) is covered.")
    D.H("6.2 Fixed-angle cases", 2)
    rows = [["%.2f" % x["angle"], x["run"], "%.0f" % x["p"], f2(x["M0"]), f2(x["M"]), f2(x["dev"]), f2(x["hc"]),
             f2(x["ratio"]) if x["ratio"] is not None else "-"] for x in AD if x.get("status") == "ok"]
    D.T(["Angle (deg)", "Run", "p (kPa)", "M vented (N m)", "M at p (N m)", "Device (N m)", "p k (N m)", "FEA / p k"], rows,
        "Fixed-angle cases, 20-60 kPa.", size=7.5, widths=[1.7, 2.1, 1.4, 2.4, 2.2, 2.2, 2.0, 2.0])
    if nr:
        D.P("Not reached (the vented bending stopped before the case angle, so no pressure step was run): " +
            "; ".join("%s (%.2f deg) stopped after %.2f deg" % (x["run"], x["angle"], x["reached"]) for x in nr) + ".")
    D.F(os.path.join(IMG, "angle_cases_moment.png"), "Left: device moment against pressure for each angle, FEA (solid) and "
        "Model B p k (dashed). Right: FEA / p k against knee angle; hollow markers = gait-cycle frames 13-21 %.", 16.5)
    D.H("6.3 Gait cycles (window 13-36 % stance)", 2)
    D.P("The cycles apply the knee-angle history of the stance phase with the bladder at the test pressure. Unlike the "
        "fixed-angle cases, the bladder is pressurised while the knee bends and straightens, so the fold in the crease can "
        "settle in different shapes. HCC_P60 is shown at 13 % only (it stopped in the next step).")
    keyf = (13, 15, 18, 21, 24, 27, 30, 33, 36)
    rows = []
    for run in CYC[1:]:
        for x in CM:
            if x.get("run") == run and x.get("phase") == "W" and x.get("stance_pct") in keyf:
                fs = x.get("fold_state")
                rows.append([run, "%d" % x["stance_pct"], f2(x["theta_deg"]), f2(x["p_kPa"], 1), f2(x["M_knee_Nm"]),
                             f2(x["M_vented_Nm"]), f2(x["M_device_Nm"]), f2(x["M_handcalc_Nm"]), f2(x["ratio_FEA_to_hc"]),
                             "main" if fs in (0, 0.0) else ("squeezed" if isinstance(fs, float) and fs > 0 else ("relaxed" if isinstance(fs, float) else "-")),
                             f2(x.get("V_bladder_mL"), 1)])
    D.T(["Run", "Stance %", "Angle (deg)", "p (kPa)", "M_knee", "M vented", "Device", "p k", "Ratio", "Fold state", "V (mL)"], rows,
        "Gait-cycle results at the key frames (moments in N m). Fold state: main = the shape at the window onset; squeezed = "
        "higher-energy shape with less volume; relaxed = lower-energy shape with more volume.",
        size=7, widths=[1.9, 1.2, 1.3, 1.2, 1.4, 1.5, 1.4, 1.3, 1.3, 1.7, 1.4])
    D.F(os.path.join(IMG, "cycles_moment.png"), "Left: device moment over the window for each cycle run, FEA markers (crosses = "
        "other fold state) and p k (dashed). Right: bladder pressure per run and knee angle (dotted).", 16.5)
    D.F(os.path.join(IMG, "fold_states_proj.png"), "Fold states in HCC_PROJ: at almost the same angle and pressure the solver "
        "finds a shape with about 7 mL less volume and about 5 N m more moment (shaded frames).", 13)
    D.P("Both shapes are converged static solutions with a positive-definite stiffness matrix. In the squeezed shape the outer "
        "wall and the cover sit about 1.7 mm lower and the reactions at the bladder ends are about 45 % larger; it has more "
        "strain energy and less air volume, so its potential energy U - pV is higher. The device moment is therefore quoted for "
        "the main (lower-energy) shape; the other frames are kept in the tables and marked.")
    D.H("6.4 Pressure and volume", 2)
    rows = []
    for a_, run in ANG:
        xs = [x for x in AD if x["run"] == run and x.get("status") == "ok"]
        if xs:
            rows.append([a_, f2(xs[0]["V0"], 1)] + [f2(next((x["V"] for x in xs if x["p"] == p_), None), 1) for p_ in (20.0, 40.0, 60.0)])
    D.T(["Angle (deg)", "V at 0 kPa (mL)", "V at 20 kPa", "V at 40 kPa", "V at 60 kPa"], rows,
        "Bladder mid-surface volume at fixed angle.", size=8, widths=[2.5, 3.0, 3.0, 3.0, 3.0])
    D.F(os.path.join(IMG, "pressure_volume.png"), "Pressure against volume at fixed knee angle.", 12)
    D.P("From 0 to 20 kPa the volume rises by about 40 mL (3 deg) to 55 mL (7.28 deg), then by only about 20 mL per further "
        "20 kPa: once the bladder has inflated against the cover, the cover carries the hoop load. This growth is also why the "
        "FEA moment exceeds p k at larger angles.")
    D.H("6.5 Stresses and factor of safety", 2)
    rows = []
    for run in RUNS:
        w = [x for x in LD[run] if x["converged"] and (x["p_kPa"] or 0) > 0 and (x["p_kPa"] or 0) <= 60.0001]
        if not w: continue
        vb = max(w, key=lambda x: x["vm_max_bladder_MPa"] or 0); vc = max(w, key=lambda x: x["vm_max_cover_MPa"] or 0)
        rows.append([run, "%s (%s kPa)" % (vb["name"], f2(vb["p_kPa"], 1)), f2(vb["vm_max_bladder_MPa"]),
                     f2(LIM_BL / vb["vm_max_bladder_MPa"], 1), f2(vc["vm_max_cover_MPa"]), f2(LIM_COV / vc["vm_max_cover_MPa"], 1)])
    D.T(["Run", "Step of the bladder maximum", "Bladder vm max (MPa)", "FoS bladder", "Cover vm max (MPa)", "FoS cover"],
        rows, "Largest von Mises stress in the converged pressurised steps up to 60 kPa; FoS = allowable / stress "
        "(11.1 MPa bladder, 37.2 MPa cover).", size=7.5, widths=[2.2, 5.0, 2.4, 2.2, 2.4, 2.2])
    D.P("Every factor of safety is above 1: the bladder is lightly loaded (8.5 or more) and the cover carries the hoop load "
        "(1.9-2.6). The peaks sit at the cover end corners and in the fold band, where the idealised model concentrates load "
        "(bonded edges, sharp fold), so they are upper estimates. Fatigue is not assessed: no S-N data were available for the "
        "bladder TPU or the coated fabric.")
    D.H("6.6 Deformed shape", 2)
    D.F(os.path.join(IMG, "deformed_stress_21pct.png"), "Deformed bladder at the peak frame (21 % stance, 5.78 deg; true scale), "
        "coloured by bladder von Mises stress, cover transparent. Vented: the fold band wrinkles; pressurised: the bladder fills "
        "the cover.", 16.5)
    D.F(os.path.join(IMG, "section_midplane_21pct.png"), "Section near the mid-plane at 21 % stance: bladder (dots) and cover "
        "(crosses), vented and at 20 / 40 kPa; undeformed in grey; shaded = fold band.", 10)
    D.F(os.path.join(IMG, "p60_13pct_stop_point.png"), "HCC_P60 at its last converged state (13 % stance, 3.28 deg, 60 kPa). "
        "Star = grid 10899 at the junction of the cover body and the shank-end cover cap, where the next step stopped.", 15)
    D.H("6.7 Device moment against the patient's need", 2)
    D.P("The reference patient (man, 70 kg, 1.70 m, two months after ACL reconstruction) has, at each stance frame, a healthy "
        "knee extension moment M_healthy, an own moment M_ACLR and a deficit ΔM_def = M_healthy - M_ACLR " + c("bt") + ". The "
        "design target is the share α = 0.20 of the deficit (an engineering test value, not a clinical prescription), capped "
        "at the patient's own moment; the limit is α ≤ 0.25 (0.254 unrounded) " + c("rep") + ". The assist ratio of the FEA is:")
    D.EQ(r("α = ") + fr(sb(r("M"), r("dev")), r("Δ") + sb(r("M"), r("def"))) + r(",   ") + sb(r("τ"), r("target")) +
         r(" = min(0.20 Δ") + sb(r("M"), r("def")) + r(", ") + sb(r("M"), r("ACLR")) + r(")"),
         "α assist ratio; M_dev FEA device moment (Section 4.3); deficit and patient moments at the same stance frame. Over "
         "the cap = M_dev > M_ACLR (the device gives more than the patient's own moment).")
    rows = []
    for run in ("HCC_PROJ", "HCC_P20", "HCC_P40", "HCC_P60"):
        for x in AS:
            if x["run"] == run and x["stance_pct"] in keyf + (14,) and x.get("M_device_Nm") is not None:
                rows.append([run, "%d" % x["stance_pct"], f2(x["p_kPa"], 1), x["fold_state"], f2(x["deficit_Nm"]), f2(x["M_ACLR_Nm"]),
                             f2(x["target_alpha020_Nm"]), f2(x["M_device_Nm"]), f2(x["alpha_FEA"], 3),
                             "%.0f %%" % (100 * x["device_over_target"]), x["over_cap"]])
    rows.sort(key=lambda z: (("HCC_PROJ", "HCC_P20", "HCC_P40", "HCC_P60").index(z[0]), int(z[1])))
    D.T(["Run", "Stance %", "p (kPa)", "Fold state", "Deficit", "Patient M_ACLR", "Target (α 0.20)", "FEA M_dev", "α FEA",
         "M_dev / target", "Over the cap"], rows,
        "Assist ratio at the key frames (moments in N m). Squeezed / relaxed = other fold shape, shown for completeness. "
        "All frames: results/tables/assist_ratio.csv.", size=6.5, widths=[1.8, 1.1, 1.1, 1.5, 1.4, 1.6, 1.6, 1.5, 1.2, 1.6, 1.3])
    D.F(os.path.join(IMG, "assist_ratio.png"), "Left: device moment of each cycle run against the patient's deficit, the "
        "patient's own moment (the cap) and the target at α 0.20. Right: assist ratio α with the design value 0.20 and the "
        "limit 0.254. Dots = main fold shape, crosses = other fold shape.", 16.5)
    p2 = [x for x in AS if x["run"] == "HCC_P20" and x["fold_state"] == "main"]
    for t in ["Project profile (HCC_PROJ): in the main fold shape over 18-27 %% stance the FEA gives α = %s-%s, i.e. %.0f-%.0f %% "
              "of the target. The idealised bladder reaches the target, slightly exceeding it because the FEA moment is above p k." %
              (f2(min(x["alpha_FEA"] for x in pm), 3), f2(max(x["alpha_FEA"] for x in pm), 3),
               100 * min(x["device_over_target"] for x in pm), 100 * max(x["device_over_target"] for x in pm)),
              "At the window onset (13-14 % stance) the same profile gives α 0.14-0.19 but 1.6-2.0 times the patient's own "
              "moment: the target is capped at the small patient moment there, and the FEA moment per kPa is largest at the onset.",
              "Constant 20 kPa (HCC_P20): α = %s-%s over the window (0.209 at 21 %%); over the cap at 13-17 %% and 30-36 %%. "
              "Constant 40 kPa: α 0.31-0.63, over the cap at every frame." % (f2(min(x["alpha_FEA"] for x in p2), 3),
                                                                               f2(max(x["alpha_FEA"] for x in p2), 3)),
              "At the peak (21 %% stance) the patient alone has %.0f %% of the healthy moment; with the project profile patient plus "
              "device reach %.0f %%." % (a21["HCC_PROJ"]["pct_healthy_patient"], a21["HCC_PROJ"]["pct_healthy_with_device"]),
              "These are values of the idealised reference (rigid leg, bonded bladder), i.e. the best the bladder geometry can "
              "give. The full-device model on a soft leg predicts at most 0.12 N m at 20 and 27 kPa " + c("rep") + "; the "
              "transfer of the bladder force to the knee is the open problem, not the formula."]:
        D.B(t)

    # ================================================================= 7 discussion
    D.H("7. Discussion")
    for t in ["At small angle FEA and Model B agree (3 deg: +6 to +8 %). The bladder section at the knee line is then close to "
              "the undeformed cavity, and the FEA reads the moment the way the formula defines it. This validates Model B and the "
              "moment extraction.",
              "The FEA k is larger than the Model B k: the FEA bladder is a mid-surface shell, half a wall thickness outside the "
              "inner cavity, and it inflates against the cover.",
              "The ratio grows with angle (at 20 kPa: 1.06 at 3 deg, 1.39 at 7.28 deg) because the fold band, which is free to "
              "bulge, becomes part of the pressurised section as the crease closes; Model B assumes a sharp mitre that adds "
              "nothing.",
              "Once the knee is bent the ratio falls with pressure (7.28 deg: 1.39 at 20 kPa, 1.28 at 40 kPa), while at 3 deg it "
              "stays at 1.06-1.08: the cover limits the bulge.",
              "The cycle ratios at 20 kPa (main shape: 1.18 at 13 % rising to 1.66 at 21 %) are larger than at a fixed 3 deg "
              "because the bladder is inflated first and then bent; the order of loading changes the fold. The fixed-angle cases "
              "follow the order of Model B (bend, then pressurise) and are the cleaner comparison.",
              "Above about 7 deg the empty fold and the cover side edges are pushed sideways by the closing crease and wrinkle; "
              "the static solver cannot follow the wrinkle. The assist window (3.28-5.78 deg) is inside the range that was "
              "reached."]:
        D.B(t)

    # ================================================================= 8 conclusions
    D.H("8. Conclusions")
    for i, t in enumerate([
            "Model B (M = p k) is confirmed by an FEA with the same assumptions: at 3 deg the FEA gives 1.06 / 1.06 / 1.08 x p k "
            "at 20 / 40 / 60 kPa - linear in pressure and of the right size.",
            "The moment extraction (shank-half reactions about the knee centre, minus the vented state) is correct; a low "
            "moment of the full-device model therefore comes from the real-case effects (soft tissue, straps, slip), not from "
            "the formula or the post-processing.",
            "With the knee bent further the idealised device gives more than p k, because the inflated fold adds section; Model B "
            "gives the value of the undeformed cavity, not an upper bound of the inflated geometry.",
            "The folded bladder can sit in more than one stable shape; near the crease the moment is not unique to within about "
            "±15 % at 20 kPa. Bench tests should load the bladder repeatedly and report the spread.",
            "With the project pressure profile the idealised device fills α = 0.21 of the patient's deficit at the peak "
            "(6.89 of 32.96 N m; target 6.59 N m), 103-105 % of the target over 18-27 % stance.",
            "Stresses up to 60 kPa stay below the allowable values: factor of safety 8.5 or more for the bladder and 1.9 or more "
            "for the cover."], 1):
        D.P("%d. %s" % (i, t))

    # ================================================================= 9 limitations
    D.H("9. Limitations and next steps")
    for t in ["Idealised reference only: no tissue, pad, straps or friction, so no skin pressure, strap force or slip results.",
              "One mesh level (M0); a mesh study of this model was not run. The fold band (50 mm, 1 % axial modulus) is a "
              "modelling choice that represents a fabric fold; a different band changes the bulge and the ratio at larger angles.",
              "Static solver: no dynamics, no air flow, no fill time; pressures are prescribed.",
              "Results above 60 kPa, between 15 and 36 % stance at 60 kPa and at fixed angles above 7.28 deg are not available.",
              "Next steps: run the same cases on the soft leg with straps and friction and compare frame by frame; bench-test the "
              "moment on a hinged rigid two-part leg at 3-10 deg and 20-60 kPa, repeated per point to measure the spread."]:
        D.B(t)

    D.H("References")
    for i, (_, t) in enumerate(REFS, 1):
        D.P("[%d] %s" % (i, t), size=8.5)
    cp = D.d.core_properties
    cp.author = cp.last_modified_by = "SDP II team, Yanbu Industrial College"; cp.comments = ""; cp.revision = 1
    cp.title = "FEA of the knee bladder - idealised reference model"
    cp.created = cp.modified = datetime.datetime(2026, 11, 22, 12, 0)
    D.d.save(out); print("written", out)


if __name__ == "__main__":
    main()
