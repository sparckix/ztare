#!/usr/bin/env python3
"""Substrate classifier — pre-launch fingerprint + recommended-flags
generator for ZTARE rubric configuration.

Built 2026-04-26 in response to the gp163d burn (operator manually
configures rubric flags by reading prior-substrate seams; each new
substrate-class exposes a new combinatorial corner).

This tool examines a substrate at PRE-LAUNCH time (before iter 1 runs)
and emits:

  1. Statistical fingerprint of evidence.txt (y/x dynamic range,
     sparsity, feature dict structure, heteroscedasticity)
  2. Pre-flight fit probe (constant predictor + log-linear baseline)
  3. Charter parsing (asymptotes, extrapolation, K_law budget,
     ground-truth-known flag)
  4. Recommended rubric flags + pathology warnings

Usage:
    python3 scripts/public/control/classify_substrate.py <project_slug>
    python3 scripts/public/control/classify_substrate.py <slug> --json    # machine-readable
    python3 scripts/public/control/classify_substrate.py <slug> --apply   # write recs to rubric
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
PROJECTS_DIR = REPO / "projects"
RUBRICS_DIR = REPO / "rubrics"


# ── Phase 1: Statistical fingerprint of evidence.txt ─────────────────────


def _parse_evidence(text: str) -> list[tuple[float, ...]]:
    """Parse rows of numeric tuples from evidence.txt. Handles three
    common formats:
      1. Whitespace/tab-separated `1.5  2.0  0.072`
      2. Pipe-table markdown `| 1.5 | 2.0 | 0.072 |`
      3. Mixed (with comment headers, table separators)
    """
    rows: list[tuple[float, ...]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "----" in stripped or "===" in stripped:
            continue
        # Detect pipe-table format
        if stripped.startswith("|") and stripped.endswith("|") and "|" in stripped[1:-1]:
            parts = [p.strip() for p in stripped.split("|") if p.strip()]
            try:
                nums = tuple(float(p) for p in parts)
                if len(nums) >= 2:
                    rows.append(nums)
            except ValueError:
                continue
        else:
            # whitespace / tab format
            parts = stripped.split()
            try:
                nums = tuple(float(p) for p in parts if p)
                if len(nums) >= 2:
                    rows.append(nums)
            except ValueError:
                continue
    return rows


def statistical_fingerprint(project_dir: Path) -> dict[str, Any]:
    """Compute y/x dynamic range, sparsity, heteroscedasticity flags."""
    out: dict[str, Any] = {
        "evidence_rows_parsed": 0,
        "n_columns": 0,
        "y_dynamic_range_decades": None,
        "x_dynamic_range_decades": None,
        "y_min_nonzero": None,
        "y_max_abs": None,
        "y_sign_homogeneous": None,
        "feature_dict_substrate": False,
        "feature_keys": [],
        "sparse_categories": {},
        "heteroscedastic_y": None,
    }

    evidence_path = project_dir / "evidence.txt"
    if not evidence_path.exists():
        out["error"] = "evidence.txt missing"
        return out

    text = evidence_path.read_text(encoding="utf-8", errors="replace")
    rows = _parse_evidence(text)
    out["evidence_rows_parsed"] = len(rows)

    if not rows:
        # Maybe markdown-table format. Try parsing pipe-separated
        for line in text.splitlines():
            if "|" not in line or "----" in line:
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if not parts:
                continue
            try:
                nums = tuple(float(p) for p in parts)
                if len(nums) >= 2:
                    rows.append(nums)
            except ValueError:
                continue
        out["evidence_rows_parsed"] = len(rows)

    if rows:
        n_cols = max(len(r) for r in rows)
        out["n_columns"] = n_cols
        # Convention: last column is y; rest are x's
        ys = [r[-1] for r in rows if len(r) >= 2]
        if ys:
            ys_abs_nonzero = [abs(y) for y in ys if y != 0]
            if ys_abs_nonzero:
                ymin, ymax = min(ys_abs_nonzero), max(ys_abs_nonzero)
                out["y_min_nonzero"] = ymin
                out["y_max_abs"] = ymax
                if ymin > 0:
                    out["y_dynamic_range_decades"] = round(math.log10(ymax / ymin), 2)
            out["y_sign_homogeneous"] = all(y >= 0 for y in ys) or all(y <= 0 for y in ys)

        # First column dynamic range as proxy for x-range
        if n_cols >= 2:
            xs = [r[0] for r in rows]
            xs_abs_nonzero = [abs(x) for x in xs if x != 0]
            if xs_abs_nonzero:
                xmin, xmax = min(xs_abs_nonzero), max(xs_abs_nonzero)
                if xmin > 0:
                    out["x_dynamic_range_decades"] = round(math.log10(xmax / xmin), 2)

        # Heteroscedasticity proxy: split into low-x and high-x halves,
        # compare std(y)/mean(y) ratio across halves.
        if len(rows) >= 10 and n_cols >= 2:
            sorted_rows = sorted(rows, key=lambda r: r[0])
            half = len(sorted_rows) // 2
            low_ys = [r[-1] for r in sorted_rows[:half]]
            high_ys = [r[-1] for r in sorted_rows[half:]]

            def _cv(vs: list[float]) -> float:
                m = sum(vs) / len(vs) if vs else 0.0
                if abs(m) < 1e-300:
                    return 0.0
                v = sum((x - m) ** 2 for x in vs) / len(vs) if vs else 0.0
                return math.sqrt(v) / abs(m)

            cv_low, cv_high = _cv(low_ys), _cv(high_ys)
            if cv_low > 0 and cv_high > 0:
                ratio = max(cv_low, cv_high) / min(cv_low, cv_high)
                out["heteroscedastic_y"] = ratio > 2.0

    # Feature-dict substrate detection: features.py with FEATURES dict
    features_path = project_dir / "features.py"
    if features_path.exists():
        out["feature_dict_substrate"] = True
        try:
            sys.path.insert(0, str(project_dir))
            try:
                # Reload safely
                import importlib
                if "features" in sys.modules:
                    del sys.modules["features"]
                import features as _f
                if hasattr(_f, "FEATURES") and isinstance(_f.FEATURES, dict):
                    keys: set[str] = set()
                    for fd in _f.FEATURES.values():
                        if isinstance(fd, dict):
                            keys.update(fd.keys())
                    out["feature_keys"] = sorted(keys)
                    # Sparse-categorical detection
                    sparse: dict[str, dict[str, int]] = {}
                    for fd in _f.FEATURES.values():
                        if isinstance(fd, dict):
                            for k, v in fd.items():
                                if isinstance(v, str):
                                    sparse.setdefault(k, {})
                                    sparse[k][v] = sparse[k].get(v, 0) + 1
                    out["sparse_categories"] = {
                        k: {v: c for v, c in vc.items() if c < 3}
                        for k, vc in sparse.items()
                        if any(c < 3 for c in vc.values())
                    }
            finally:
                sys.path.pop(0)
        except Exception as e:
            out["features_load_error"] = str(e)[:200]

    return out


# ── Phase 2: Pre-flight fit probe ────────────────────────────────────────


def preflight_fit_probe(project_dir: Path, fingerprint: dict) -> dict[str, Any]:
    """Try the simplest possible baselines on visible data: constant
    predictor (y = mean(y)) and log-linear (log y = a + b·log x)."""
    out: dict[str, Any] = {
        "constant_predictor_mre": None,
        "log_linear_mre": None,
        "log_linear_slope": None,
        "baseline_difficulty": None,
    }
    evidence_path = project_dir / "evidence.txt"
    if not evidence_path.exists():
        return out
    rows = _parse_evidence(evidence_path.read_text(encoding="utf-8", errors="replace"))
    if not rows:
        return out

    ys = [r[-1] for r in rows if len(r) >= 2]
    if not ys:
        return out

    # Constant predictor: y_pred = mean(y), MRE on |y|
    mean_y = sum(ys) / len(ys)
    rel_errs = [abs(mean_y - y) / max(abs(y), 1e-300) for y in ys]
    out["constant_predictor_mre"] = round(sum(rel_errs) / len(rel_errs), 4)

    # Log-linear: only if y, x both positive
    if len(rows) >= 5 and all(len(r) >= 2 for r in rows):
        positive = [(r[0], r[-1]) for r in rows if r[0] > 0 and r[-1] > 0]
        if len(positive) >= 5:
            # Simple OLS on log-log
            log_xs = [math.log(x) for x, _ in positive]
            log_ys = [math.log(y) for _, y in positive]
            n = len(positive)
            mx = sum(log_xs) / n
            my = sum(log_ys) / n
            num = sum((log_xs[i] - mx) * (log_ys[i] - my) for i in range(n))
            den = sum((log_xs[i] - mx) ** 2 for i in range(n))
            if den > 1e-300:
                slope = num / den
                intercept = my - slope * mx
                out["log_linear_slope"] = round(slope, 4)
                # Compute MRE on full visible set (handle edge cases)
                pred_errs = []
                for x, y in positive:
                    pred = math.exp(intercept + slope * math.log(x))
                    pred_errs.append(abs(pred - y) / max(abs(y), 1e-300))
                out["log_linear_mre"] = round(sum(pred_errs) / len(pred_errs), 4)

    # Difficulty classification
    cmre = out["constant_predictor_mre"] or 999
    lmre = out["log_linear_mre"] if out["log_linear_mre"] is not None else 999
    best = min(cmre, lmre)
    if best < 0.05:
        out["baseline_difficulty"] = "trivial"
    elif best < 0.20:
        out["baseline_difficulty"] = "easy"
    elif best < 0.50:
        out["baseline_difficulty"] = "moderate"
    else:
        out["baseline_difficulty"] = "hard"

    return out


# ── Phase 3: Charter parsing ─────────────────────────────────────────────


def parse_charter(project_dir: Path) -> dict[str, Any]:
    """Heuristic charter extraction. Looks for asymptote claims, K_law
    budget, ground-truth-known flag, extrapolation requirements."""
    out: dict[str, Any] = {
        "asymptotes_declared": [],
        "extrapolation_required": False,
        "k_law_max": None,
        "ground_truth_known": None,
        "named_entity_denylist": [],
        "rubric_mode_hint": None,
        "multi_class_substrate": False,
        "discovery_mode_hint": None,
    }
    charter_path = project_dir / "project_charter.md"
    if not charter_path.exists():
        out["error"] = "project_charter.md missing"
        return out

    text = charter_path.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()

    # Asymptote claims
    asy_patterns = [
        (r"high\s+x.*[→\-]>\s*([^\n]{0,100})", "high_x"),
        (r"low\s+x.*[→\-]>\s*([^\n]{0,100})", "low_x"),
        (r"as\s+n\s*→\s*∞.*?([^\n]{0,80})", "n_infinity"),
        (r"asymptot(?:ic|e)\s+[^\n]{0,200}", "general"),
    ]
    for pat, label in asy_patterns:
        for m in re.finditer(pat, lower):
            snippet = m.group(0)[:120]
            out["asymptotes_declared"].append(f"{label}: {snippet}")
    out["asymptotes_declared"] = out["asymptotes_declared"][:10]

    # Extrapolation requirement
    if any(kw in lower for kw in ["farther-tail", "farther tail", "extrapolation",
                                    "validity horizon", "asymptotic"]):
        out["extrapolation_required"] = True

    # K_law budget
    m = re.search(r"k_?law\s*[<≤]\s*=?\s*(\d+)", lower)
    if not m:
        m = re.search(r"law\s+has\s+k_?law\s+(\d+)", lower)
    if m:
        try:
            out["k_law_max"] = int(m.group(1))
        except ValueError:
            pass

    # Ground-truth-known: heuristic — if charter mentions specific named laws
    # (Planck, KWW, Hardy-Ramanujan, etc.) it's likely Bucket B; if it uses
    # cold variable names + denylist, more likely Bucket C.
    if any(kw in lower for kw in ["cold variable", "do not reference", "denylist"]):
        out["ground_truth_known"] = "concealed"  # apparatus-test setup
    elif any(kw in lower for kw in ["closed-form known", "exact value known",
                                      "ground truth is", "true form is"]):
        out["ground_truth_known"] = True
    else:
        out["ground_truth_known"] = "indeterminate"

    # Denylist
    denylist_path = project_dir / ".denylist"
    if denylist_path.exists():
        out["named_entity_denylist"] = [
            ln.strip() for ln in denylist_path.read_text().splitlines() if ln.strip()
        ][:20]

    # Newton-mode (Generative Yield)
    if "secondary observable" in lower or "newton-mode" in lower or "generative yield" in lower:
        out["rubric_mode_hint"] = "newton"
    elif "discover" in lower and "secondary" not in lower:
        out["rubric_mode_hint"] = "discovery"

    # Multi-class substrate detection. Tightened 2026-04-26: bare "class
    # A" / "class B" keywords were over-matching on substrates that
    # mention class as a literary term (e.g. "ansatz class"). Require a
    # stronger signal: explicit `system_class` feature OR `class-conditional` /
    # `per-class` phrase.
    if any(kw in lower for kw in ["system_class", "class-conditional",
                                    "class_conditional", "per-class",
                                    "per_class", "hypothesis u", "hypothesis s",
                                    "universality versus", "universality vs"]):
        out["multi_class_substrate"] = True

    return out


# ── Phase 4: Recommended-flags generator ─────────────────────────────────


def recommended_flags(
    fingerprint: dict, preflight: dict, charter: dict
) -> dict[str, Any]:
    """Combine 1+2+3 into a JSON output the operator can copy into the rubric."""
    flags: dict[str, Any] = {}
    warnings: list[str] = []
    estimated_bucket: str = "indeterminate"

    # Rule 1: y_dynamic_range > 2 decades → fit_relative_residuals.
    # Fallback signal when evidence.txt parsing failed: check features.py
    # FEATURES dict for embedded y values (some substrates store visible
    # rows in features.py rather than evidence.txt).
    ydr = fingerprint.get("y_dynamic_range_decades")
    n_parsed = fingerprint.get("evidence_rows_parsed", 0) or 0
    if (ydr is None or ydr == 0.0) and n_parsed < 50 and fingerprint.get("feature_dict_substrate"):
        warnings.append(
            "evidence.txt parser produced <50 rows on a feature-dict substrate; "
            "y_dynamic_range may be unreliable. Run "
            "`python3 -c \"import features; ys=[y for _,y,_ in features.visible_rows()]; "
            "print(min(abs(y) for y in ys if y), max(abs(y) for y in ys))\"` "
            "in the substrate dir to confirm."
        )
    if ydr is not None and ydr > 2.0:
        flags["fit_relative_residuals"] = True
        warnings.append(
            f"y range spans {ydr} decades. Recommend fit_relative_residuals=True (F6) "
            f"so high-y rows do not dominate the objective."
        )

    # Rule 2: y at scale != order(1) → mutator must declare INIT_RANGE
    ymin = fingerprint.get("y_min_nonzero")
    ymax = fingerprint.get("y_max_abs")
    if ymin is not None and ymax is not None:
        ymed_log = (math.log10(ymin) + math.log10(ymax)) / 2 if ymin > 0 else None
        if ymed_log is not None and (ymed_log < -1 or ymed_log > 2):
            warnings.append(
                f"Data y is at scale ~1e{ymed_log:.1f}, far from order(1). "
                f"Mutator MUST declare INIT_RANGE for any param at this scale "
                f"(Bug A trap defense)."
            )

    # Rule 3: extrapolation required → farther_tail_region + holdout_hard_gate
    if charter.get("extrapolation_required"):
        flags["holdout_hard_gate"] = True
        flags["farther_tail_region"] = True
        warnings.append(
            "Charter declares extrapolation/asymptote requirements. "
            "Recommend holdout_hard_gate=True and farther_tail_region=True "
            "(Padé Trap defense)."
        )

    # Rule 4: feature-dict substrate → enable_fit_primitive_features
    if fingerprint.get("feature_dict_substrate"):
        flags["enable_fit_primitive_features"] = True
        warnings.append(
            "features.py present with FEATURES dict. Recommend "
            "enable_fit_primitive_features=True (N-D fit primitive)."
        )

    # Rule 5: Newton-mode hint from charter
    if charter.get("rubric_mode_hint") == "newton":
        flags["rubric_mode"] = "newton"
        warnings.append(
            "Charter declares Newton-mode (secondary observable + Generative "
            "Yield). Set rubric_mode='newton'."
        )

    # Rule 6: ground-truth-concealed (cold-variables + denylist) → likely Bucket C-test
    if charter.get("ground_truth_known") == "concealed":
        warnings.append(
            "Charter uses cold variable names + denylist (apparatus-test setup). "
            "Run a cold-LLM null pre-test to estimate Bucket A/B vs C before "
            "claiming novelty."
        )
        estimated_bucket = "C-candidate"
    elif charter.get("ground_truth_known") is True:
        estimated_bucket = "B"
        warnings.append(
            "Ground truth is named in the charter. This is a calibration / "
            "Bucket B substrate, NOT a discovery. Frame results as "
            "reproducibility + cold-variable rigor, not novelty."
        )

    # Rule 7: multi-class substrate → require Hypothesis pre-commit
    if charter.get("multi_class_substrate"):
        warnings.append(
            "Multi-class substrate detected (system_class or per-class hints). "
            "Charter should require Hypothesis U vs S pre-commit + AP-1 binding "
            "anti-pattern (no false fit on absent class data)."
        )

    # Rule 8: trivial baseline difficulty
    if preflight.get("baseline_difficulty") == "trivial":
        warnings.append(
            "Constant or log-linear baseline already achieves MRE < 5%. "
            "This is likely calibration / pre-known relationship; downgrade "
            "any 'discovery' framing."
        )
    elif preflight.get("baseline_difficulty") == "hard":
        warnings.append(
            "Constant + log-linear baselines both fail (MRE > 50%). "
            "Substrate is genuinely difficult — apparatus contribution is more "
            "likely to be Bucket C if it succeeds."
        )

    # Rule 9: heteroscedastic y → pathology guard tuning
    if fingerprint.get("heteroscedastic_y"):
        warnings.append(
            "y heteroscedasticity detected (CV varies >2× across x range). "
            "Default convergence threshold may misfire; consider "
            "fit_convergence_relative_threshold loosening (currently 0.01)."
        )

    # Rule 10: sparse categorical features
    if fingerprint.get("sparse_categories"):
        warnings.append(
            "Sparse categorical values found in features.py: "
            f"{list(fingerprint['sparse_categories'].keys())[:3]}. "
            "Sparse-indicator hard reject is enabled by default; substrates "
            "with intentional sparse categories may need "
            "disable_sparse_indicator_reject=True."
        )

    return {
        "recommended_flags": flags,
        "warnings": warnings,
        "estimated_bucket": estimated_bucket,
    }


# ── Phase 5: Public API ──────────────────────────────────────────────────


def classify_substrate(project_slug: str) -> dict[str, Any]:
    project_dir = PROJECTS_DIR / project_slug
    if not project_dir.exists():
        return {"error": f"project not found: {project_dir}"}

    fingerprint = statistical_fingerprint(project_dir)
    preflight = preflight_fit_probe(project_dir, fingerprint)
    charter = parse_charter(project_dir)
    recs = recommended_flags(fingerprint, preflight, charter)

    return {
        "project_slug": project_slug,
        "project_dir": str(project_dir),
        "fingerprint": fingerprint,
        "preflight_fit": preflight,
        "charter_extraction": charter,
        **recs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_slug")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--apply", action="store_true",
                       help="write recommended flags to rubric (interactive confirm)")
    args = parser.parse_args()

    result = classify_substrate(args.project_slug)
    if "error" in result and "project_dir" not in result:
        print(f"❌ {result['error']}")
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"═══ Substrate classifier: {args.project_slug} ═══")
    print()
    print("─── Statistical fingerprint ───")
    fp = result["fingerprint"]
    print(f"  evidence rows parsed:    {fp.get('evidence_rows_parsed')}")
    print(f"  y dynamic range:         {fp.get('y_dynamic_range_decades')} decades")
    print(f"  x dynamic range:         {fp.get('x_dynamic_range_decades')} decades")
    if fp.get('y_min_nonzero') is not None:
        print(f"  y range (abs, nonzero):  [{fp.get('y_min_nonzero'):.3e}, {fp.get('y_max_abs'):.3e}]")
    print(f"  feature-dict substrate:  {fp.get('feature_dict_substrate')}")
    if fp.get("feature_keys"):
        print(f"  feature keys:            {fp.get('feature_keys')[:8]}")
    print(f"  heteroscedastic y:       {fp.get('heteroscedastic_y')}")
    print()
    print("─── Pre-flight fit probe ───")
    pf = result["preflight_fit"]
    print(f"  constant predictor MRE:  {pf.get('constant_predictor_mre')}")
    print(f"  log-linear MRE:          {pf.get('log_linear_mre')}")
    print(f"  baseline difficulty:     {pf.get('baseline_difficulty')}")
    print()
    print("─── Charter extraction ───")
    ch = result["charter_extraction"]
    print(f"  K_law max declared:      {ch.get('k_law_max')}")
    print(f"  extrapolation required:  {ch.get('extrapolation_required')}")
    print(f"  ground truth status:     {ch.get('ground_truth_known')}")
    print(f"  rubric mode hint:        {ch.get('rubric_mode_hint')}")
    print(f"  multi-class substrate:   {ch.get('multi_class_substrate')}")
    print(f"  named-entity denylist:   {len(ch.get('named_entity_denylist', []))} terms")
    print()
    print(f"─── Recommended flags ──── (estimated bucket: {result['estimated_bucket']})")
    for k, v in (result["recommended_flags"] or {}).items():
        print(f"  {k}: {v}")
    print()
    print("─── Warnings ───")
    for i, w in enumerate(result["warnings"], 1):
        print(f"  {i}. {w}")

    if args.apply:
        rubric_path = RUBRICS_DIR / f"{args.project_slug}.json"
        if rubric_path.exists():
            with open(rubric_path) as f:
                rubric = json.load(f)
            print()
            print(f"─── Apply recommendations to {rubric_path}? ───")
            print("  (existing rubric values shown alongside)")
            for k, v in (result["recommended_flags"] or {}).items():
                cur = rubric.get(k, "(unset)")
                print(f"  {k}: {cur} → {v}")
            confirm = input("Apply these changes? [y/N]: ").strip().lower()
            if confirm == "y":
                rubric.update(result["recommended_flags"])
                with open(rubric_path, "w") as f:
                    json.dump(rubric, f, indent=2)
                print(f"✅ Applied. Wrote {rubric_path}")
            else:
                print("Skipped.")
        else:
            print(f"⚠️ Rubric file not found at {rubric_path}; recommendations not applied.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
