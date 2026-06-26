#!/usr/bin/env python3
"""PySR head-to-head baseline vs ZTARE on Mertens / prime gaps / abundant density.

Question addressed: does PySR return a spurious fit on incompressible substrates
where ZTARE correctly returned null? This is the missing baseline comparison
flagged by outside review of papers/experimental_math_letter/draft.md §2.7.

Protocol (matches ZTARE §2.7 gating):
  1. Fit PySR on visible evidence only.
  2. Evaluate residual on held-out farther-tail range.
  3. Decision: if max holdout residual > threshold -> null (matches ZTARE).
     Else -> report returned form.

Threshold matches the letter's abstract claim: "false-positive rate 0 on
incompressible substrates" — we use per-substrate thresholds from the
rubric when available, or 3x the visible-range stdev as fallback.

Install: pip install pysr && python -c "import pysr; pysr.install()"
Run:     python scripts/pysr_baseline.py [--substrates s1,s2,s3,lucky,pn]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]


def load_evidence(path: Path) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        xs.append(float(parts[0]))
        ys.append(float(parts[1]))
    return np.array(xs), np.array(ys)


SUBSTRATES = {
    "s1": {
        "label": "abundant density (letter §2.7 S1)",
        "project": "survey_s1",
        "ztare_verdict": "1/n form passes gates at n<=100k; 1/log(n) asymptote only at n>>10^6",
        "gate_mode": "normalized",
        "gate_threshold": 0.01,
    },
    "s2": {
        "label": "Mertens M(n)/sqrt(n) (letter §2.7 S2 / §1 abstract)",
        "project": "survey_s2",
        "ztare_verdict": "null (correct)",
        "gate_mode": "absolute",
        "gate_threshold": 0.08,
    },
    "s3": {
        "label": "prime gaps g(n)/log(p_n) (letter §2.7 S3 / §1 abstract)",
        "project": "survey_s3",
        "ztare_verdict": "null (correct)",
        "gate_mode": "absolute",
        "gate_threshold": 0.08,
    },
    "lucky": {
        "label": "Lucky density L(n)/n (letter §2.1 — sanity baseline)",
        "project": "oeis_a000959",
        "ztare_verdict": "recovered a*log(n) + b/n + c, a=1.200",
        "gate_mode": "absolute",
        "gate_threshold": 0.08,
    },
    "hr": {
        "label": "Hardy-Ramanujan log p(n) (letter §2.2 — sanity baseline)",
        "project": "gp088_calibration_a01",
        "ztare_verdict": "recovered pi*sqrt(2n/3) + b*log(n) + c",
        "gate_mode": "absolute",
        "gate_threshold": 0.08,
    },
}


def build_pysr_model(niterations: int, max_complexity: int, procs: int):
    """Construct a PySR regressor with a grammar mirroring ZTARE's grammar-expanded set."""
    from pysr import PySRRegressor

    return PySRRegressor(
        niterations=niterations,
        maxsize=max_complexity,
        binary_operators=["+", "-", "*", "/", "pow"],
        unary_operators=["log", "sqrt", "exp"],
        extra_sympy_mappings={},
        model_selection="best",
        procs=procs,
        progress=False,
        verbosity=0,
        random_state=0,
        deterministic=True,
        parallelism="serial",
        elementwise_loss="L2DistLoss()",
        warm_start=False,
    )


def evaluate(model, x_train, y_train, x_holdout, y_holdout, x_farther, y_farther):
    """Return dict with visible/holdout/farther residuals for the chosen equation."""
    pred_train = np.asarray(model.predict(x_train.reshape(-1, 1))).ravel()
    pred_hold = (
        np.asarray(model.predict(x_holdout.reshape(-1, 1))).ravel()
        if len(x_holdout) else np.array([])
    )
    pred_far = (
        np.asarray(model.predict(x_farther.reshape(-1, 1))).ravel()
        if len(x_farther) else np.array([])
    )

    def stats(y_true, y_pred):
        if len(y_true) == 0:
            return {"n": 0, "max_abs": None, "rmse": None}
        r = y_true - y_pred
        return {
            "n": int(len(y_true)),
            "max_abs": float(np.max(np.abs(r))),
            "rmse": float(np.sqrt(np.mean(r ** 2))),
        }

    return {
        "equation": str(model.sympy()),
        "complexity": int(model.get_best()["complexity"]),
        "visible": stats(y_train, pred_train),
        "holdout": stats(y_holdout, pred_hold),
        "farther_tail": stats(y_farther, pred_far),
    }


def decide(
    res: dict,
    y_visible: np.ndarray,
    gate_mode: str,
    gate_threshold: float,
) -> dict:
    """Return both PySR-default and PySR-under-ZTARE-gate verdicts.

    PySR-default: always returns the best-BIC equation, no null option.
    PySR-under-gate: ZTARE-style holdout gating (matches letter §2.1-§2.4).
      gate_mode='absolute'  -> max_abs residual gate
      gate_mode='normalized' -> max_abs / max(|y_visible|) gate (survey_s1 style)
    """
    hold_max = res["holdout"]["max_abs"]
    far_max = res["farther_tail"]["max_abs"]
    hold_nan = hold_max is not None and (hold_max != hold_max)  # NaN check
    far_nan = far_max is not None and (far_max != far_max)
    usable = [v for v in [hold_max, far_max] if v is not None and v == v]

    default_verdict = "form-claimed (no gate)"
    if hold_nan or far_nan:
        default_verdict = "form-claimed-but-NaN-on-extrapolation"

    if not usable:
        gated_verdict = "null-under-gate (NaN on extrapolation)"
    else:
        max_oos = max(usable)
        if gate_mode == "normalized":
            denom = max(abs(y_visible.max()), abs(y_visible.min()), 1e-12)
            metric = max_oos / denom
            label = "max_oos/max|y|"
        else:
            metric = max_oos
            label = "max_abs_oos"
        if hold_nan or far_nan or metric > gate_threshold:
            gated_verdict = (
                f"null-under-gate ({label}={metric:.4g} > {gate_threshold:.4g}"
                + (", NaN on some OOS points" if (hold_nan or far_nan) else "")
                + ")"
            )
        else:
            gated_verdict = f"form-passes-gate ({label}={metric:.4g} <= {gate_threshold:.4g})"

    return {
        "pysr_default_verdict": default_verdict,
        "pysr_gated_verdict": gated_verdict,
    }


def run_substrate(key: str, niterations: int, procs: int, max_complexity: int) -> dict:
    meta = SUBSTRATES[key]
    proj = REPO / "projects" / meta["project"]
    ev = proj / "evidence.txt"
    ho = proj / "evidence_holdout.txt"
    ft = proj / "evidence_farther_tail.txt"
    if not ev.exists():
        return {"key": key, "error": f"missing {ev}"}

    x_tr, y_tr = load_evidence(ev)
    x_ho, y_ho = load_evidence(ho) if ho.exists() else (np.array([]), np.array([]))
    x_ft, y_ft = load_evidence(ft) if ft.exists() else (np.array([]), np.array([]))

    t0 = time.time()
    model = build_pysr_model(niterations, max_complexity, procs)
    model.fit(x_tr.reshape(-1, 1), y_tr, variable_names=["n"])
    elapsed = time.time() - t0

    ev_res = evaluate(model, x_tr, y_tr, x_ho, y_ho, x_ft, y_ft)
    verdicts = decide(
        ev_res,
        y_visible=y_tr,
        gate_mode=meta.get("gate_mode", "absolute"),
        gate_threshold=meta.get("gate_threshold", 0.08),
    )

    return {
        "key": key,
        "label": meta["label"],
        "ztare_verdict": meta["ztare_verdict"],
        "gate_mode": meta.get("gate_mode", "absolute"),
        "gate_threshold": meta.get("gate_threshold", 0.08),
        "pysr_equation": ev_res["equation"],
        "pysr_complexity": ev_res["complexity"],
        "pysr_visible": ev_res["visible"],
        "pysr_holdout": ev_res["holdout"],
        "pysr_farther_tail": ev_res["farther_tail"],
        "pysr_default_verdict": verdicts["pysr_default_verdict"],
        "pysr_gated_verdict": verdicts["pysr_gated_verdict"],
        "pysr_elapsed_sec": round(elapsed, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--substrates",
        default="s1,s2,s3,lucky,hr",
        help="comma-separated keys from: " + ",".join(SUBSTRATES),
    )
    ap.add_argument("--niterations", type=int, default=40)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--max_complexity", type=int, default=20)
    ap.add_argument(
        "--out", default="papers/experimental_math_letter/evidence/pysr_baseline_results.json"
    )
    args = ap.parse_args()

    try:
        import pysr  # noqa: F401
    except ImportError:
        print(
            "pysr not installed. run:\n"
            "  pip install pysr\n"
            "  python -c 'import pysr; pysr.install()'",
            file=sys.stderr,
        )
        sys.exit(2)

    keys = [k.strip() for k in args.substrates.split(",") if k.strip()]
    results = []
    for key in keys:
        if key not in SUBSTRATES:
            print(f"unknown substrate: {key}", file=sys.stderr)
            continue
        print(f"=== {key}: {SUBSTRATES[key]['label']} ===", flush=True)
        r = run_substrate(key, args.niterations, args.procs, args.max_complexity)
        results.append(r)
        if "error" in r:
            print(f"  ERROR: {r['error']}")
            continue
        print(f"  PySR form:        {r['pysr_equation']}  (k={r['pysr_complexity']})")
        print(f"  ZTARE verdict:    {r['ztare_verdict']}")
        print(f"  PySR default:     {r['pysr_default_verdict']}")
        print(f"  PySR + ZTARE gate:{r['pysr_gated_verdict']}")
        print(f"  elapsed:          {r['pysr_elapsed_sec']}s")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": results}, indent=2))
    print(f"\nwrote {out}")

    print("\n=== §2.7 head-to-head summary ===")
    print(f"{'sub':<6} {'ZTARE':<38} {'PySR-default':<45} {'PySR+ZTARE-gate':<45}")
    for r in results:
        if "error" in r:
            continue
        print(
            f"{r['key']:<6} "
            f"{r['ztare_verdict'][:36]:<38} "
            f"{r['pysr_default_verdict'][:43]:<45} "
            f"{r['pysr_gated_verdict'][:43]:<45}"
        )


if __name__ == "__main__":
    main()
