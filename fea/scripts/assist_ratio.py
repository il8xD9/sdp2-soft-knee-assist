# -*- coding: utf-8 -*-
r"""Assist ratio of the idealised reference relative to the reference patient's knee-moment deficit.
Per window frame (13-36 % stance) of the gait-cycle runs:
  alpha_FEA   = M_dev / dM_def           (share of the patient's knee-moment deficit that the device moment fills;
                                          design value alpha 0.20, limit 0.254)
  target      = MIN(0.20 x deficit, patient moment)  -> M_dev / target
  cap check   = M_dev / M_ACLR           (> 1 = the device gives more than the patient's own moment)
  % healthy   = (M_ACLR + M_dev) / M_healthy
Inputs: results/tables/cycle_moment.csv (collect_cycles.py) and inputs/patient_waveform_option2.csv (per-frame knee
angle, deficit and patient moment of the reference patient; healthy = deficit + patient).
Output: results/tables/assist_ratio.csv, results/figures/assist_ratio.png
Usage: python -P assist_ratio.py"""
import csv, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(R, "inputs", "patient_waveform_option2.csv")
TAB = os.path.join(R, "results", "tables"); IMG = os.path.join(R, "results", "figures")
ALPHA_TEST, ALPHA_LIM = 0.20, 0.254


def waveform():
    wf = {}
    for r in csv.DictReader(ln for ln in open(WF) if not ln.startswith("#")):
        f = int(float(r["stance_pct"]))
        if 13 <= f <= 36:
            d, m = float(r["deficit_Nm"]), float(r["M_aclr_Nm"])
            wf[f] = dict(M_healthy=d + m, M_ACLR=m, deficit=d, target=min(ALPHA_TEST * d, max(m, 0.0)), theta=float(r["flexion_deg"]))
    assert len(wf) == 24, len(wf)
    return wf


def fl(v):
    try: return float(v)
    except (TypeError, ValueError): return None


def main():
    wf = waveform(); out = []
    for x in csv.DictReader(open(os.path.join(TAB, "cycle_moment.csv"))):
        if x["phase"] != "W" or x["run"] == "HCC_P0":
            continue
        f = int(x["stance_pct"]); w = wf[f]; md = fl(x["M_device_Nm"]); fs = fl(x.get("fold_state"))
        state = "-" if md is None else ("main" if fs in (None, 0.0) else ("squeezed" if fs > 0 else "relaxed"))
        out.append(dict(run=x["run"], stance_pct=f, theta_deg=fl(x["theta_deg"]), p_kPa=fl(x["p_kPa"]), fold_state=state,
                        M_healthy_Nm=w["M_healthy"], M_ACLR_Nm=w["M_ACLR"], deficit_Nm=w["deficit"], target_alpha020_Nm=w["target"],
                        M_device_Nm=md, alpha_FEA=(md / w["deficit"] if md is not None else None),
                        device_over_target=(md / w["target"] if md is not None else None),
                        device_over_patient=(md / w["M_ACLR"] if md is not None else None),
                        over_cap=("yes" if md is not None and md > w["M_ACLR"] else ("no" if md is not None else "-")),
                        pct_healthy_patient=100 * w["M_ACLR"] / w["M_healthy"],
                        pct_healthy_with_device=(100 * (w["M_ACLR"] + md) / w["M_healthy"] if md is not None else None)))
    with open(os.path.join(TAB, "assist_ratio.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, list(out[0])); wr.writeheader(); wr.writerows(out)
    print("written assist_ratio.csv", len(out))
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    fr = sorted(wf)
    ax[0].plot(fr, [wf[f]["deficit"] for f in fr], "k-", lw=1.6, label="patient deficit (healthy - ACLR)")
    ax[0].plot(fr, [wf[f]["M_ACLR"] for f in fr], "k:", lw=1.4, label="patient's own moment (ACLR) = Option-2 cap")
    ax[0].plot(fr, [wf[f]["target"] for f in fr], "k--", lw=1.2, label="biomechanics target, alpha 0.20 (capped)")
    cols = {"HCC_P20": "tab:blue", "HCC_PROJ": "tab:green", "HCC_P40": "tab:orange", "HCC_P60": "tab:red"}
    for run, c in cols.items():
        d = [o for o in out if o["run"] == run and o["fold_state"] == "main"]
        s = [o for o in out if o["run"] == run and o["fold_state"] in ("squeezed", "relaxed")]
        if d:
            ax[0].plot([o["stance_pct"] for o in d], [o["M_device_Nm"] for o in d], "o-", ms=4, color=c, label=run + " FEA (main shape)")
            ax[1].plot([o["stance_pct"] for o in d], [o["alpha_FEA"] for o in d], "o-", ms=4, color=c, label=run)
        if s:
            ax[0].plot([o["stance_pct"] for o in s], [o["M_device_Nm"] for o in s], "x", ms=6, color=c)
            ax[1].plot([o["stance_pct"] for o in s], [o["alpha_FEA"] for o in s], "x", ms=6, color=c)
    ax[1].axhline(ALPHA_TEST, color="k", ls="--", lw=1.2, label="alpha 0.20 (design value)")
    ax[1].axhline(ALPHA_LIM, color="k", ls=":", lw=1.4, label="alpha 0.254 (limit, B5)")
    ax[0].set_xlabel("% stance"); ax[0].set_ylabel("moment (N m)"); ax[0].set_title("Device moment against the patient's need")
    ax[1].set_xlabel("% stance"); ax[1].set_ylabel("assist ratio alpha = M_dev / deficit"); ax[1].set_title("Assist ratio (crosses = other fold shape)")
    ax[1].set_ylim(0, 0.8); ax[0].set_ylim(0, 50)
    ax[0].legend(fontsize=6.5, loc="upper center", ncol=2, framealpha=0.9); ax[1].legend(fontsize=7, loc="upper center", ncol=2)
    for a in ax: a.set_xlim(12.5, 36.5); a.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(IMG, "assist_ratio.png"), dpi=160); plt.close(fig); print("figure assist_ratio.png")


if __name__ == "__main__":
    main()
