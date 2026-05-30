#!/usr/bin/env python3
"""GP-230 Layer-4 Archetype-Catalog ablation harness.

Reviewer-mandated 5-mode ablation experiment over Lean rows in the carleson
sandbox. Per-row JSON trace + aggregate.

Modes
-----
  A  basic_tactics_only   : try each Lean basic tactic (linarith / nlinarith /
                            omega / ring / ring_nf / simp / simp_all / aesop /
                            norm_num / positivity / decide / polyrith /
                            field_simp / gcongr) individually with a per-tactic
                            timeout (default 60s). Report if ANY closes.
  B  route_c_alone        : LLM-proposed proof attempts (scaffold-only here;
                            no LLM is invoked per operator constraint).
  C  structural_only      : L2 structural-content classifier picks default
                            tactic family (scaffold-only).
  D  archetype_only       : L4 archetype classifier picks recommended tactics
                            from v30_layer4_archetype_catalog.json (scaffold-
                            only — predicted archetype is logged but no LLM
                            ranking is performed).
  Full                    : structural-op + archetype + anti-pattern guard +
                            Route C (scaffold-only).

Only mode A actually compiles Lean here. Modes B/C/D/Full record a predicted
label (where deterministic) and are explicitly marked `scaffold_only: true`.

Safe-runner principles (operator-mandated)
  - nice -n 10 on every `lake env lean` invocation
  - per-tactic timeout (default 60s)
  - max 2 parallel workers
  - kill grandchildren on timeout via os.setsid + os.killpg
  - sleep between batches if 1-min load > N_CORES * 1.5

CLI
  route_c_archetype_runner.py --row-file <path> --mode <A|B|C|D|Full|all>
                              [--out <json>] [--budget 60] [--workers 2]
                              [--rows <path> ...]

For `--rows`, multiple row files can be supplied and results are aggregated.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
SANDBOX = ROOT / (
    "analytics/public/leanmill/external_benchmarks/"
    "sandboxes/v28A_carleson_baseline/carleson"
)
ARCHETYPE_CATALOG = ROOT / (
    "analytics/public/leanmill/results/v30_layer4_archetype_catalog.json"
)
ARCHETYPE_V3_CATALOG = ROOT / (
    "analytics/public/leanmill/results/v30_layer4_v3_pattern_seed_catalog.json"
)

# Import the reviewer-spec ARCH-001..008 classifier.
import sys as _sys
_sys.path.insert(0, str(ROOT / "scripts/public/control"))
try:
    from archetype_classifier import classify as classify_arch_reviewer_spec  # type: ignore
    HAVE_REVIEWER_CLASSIFIER = True
except Exception:  # noqa: BLE001
    HAVE_REVIEWER_CLASSIFIER = False

# Direct tactics from ARCH-001..008 `recommended_tactic_sequence` that are
# argument-free and safely executable without an LLM/premise oracle. Indirect
# entries like `exact ?lemma` / `apply ?lemma` / `calc ...` / `induction ...`
# are filtered out — those need Route C wiring.
ARCH_DIRECT_TACTICS = {
    "ARCH-001_direct_library_chain": [],  # all need lemma name
    "ARCH-002_calc_inequality_chain": ["linarith", "nlinarith", "gcongr"],
    "ARCH-003_normalization_first": ["ring", "ring_nf", "norm_num", "field_simp; ring"],
    "ARCH-004_constructor_refine_decomposition": [],  # all need witnesses
    "ARCH-005_induction_recursion": [],  # induction needs hand-written branches
    "ARCH-006_monotonicity_gcongr_chain": ["gcongr", "nlinarith"],
    "ARCH-007_duality_holder_cs_route": [],  # apply specific named lemma
    "ARCH-008_measure_measurability_automation": ["measurability", "fun_prop"],
}

# Operator-blessed Lean "basic tactics" — pure builtins / Mathlib mainline
# automation. NO hammer, NO route-C synthesis, NO premise oracles.
BASIC_TACTICS = [
    "linarith",
    "nlinarith",
    "omega",
    "ring",
    "ring_nf",
    "simp",
    "simp_all",
    "aesop",
    "norm_num",
    "positivity",
    "decide",
    "polyrith",
    "field_simp",
    "gcongr",
]

# ---------------------------------------------------------------------------
# resource discipline
# ---------------------------------------------------------------------------

def now() -> str:
    return time.strftime("%H:%M:%S")


def n_cores() -> int:
    try:
        return os.cpu_count() or 4
    except Exception:
        return 4


def get_load() -> float:
    try:
        return os.getloadavg()[0]
    except OSError:
        return 0.0


def wait_for_load(threshold_mult: float = 1.5) -> None:
    threshold = n_cores() * threshold_mult
    while True:
        load = get_load()
        if load < threshold:
            return
        print(f"  [{now()}] load={load:.2f} > {threshold:.0f}, sleeping 10s...")
        time.sleep(10)


# ---------------------------------------------------------------------------
# Lean compile primitive
# ---------------------------------------------------------------------------

LEAN_ERR_RE = re.compile(r"^\S*\.lean:\d+:\d+: error:", re.MULTILINE)


def run_lean_safe(file_rel: str, timeout: int = 60) -> dict:
    """Run `nice -n 10 lake env lean <file_rel>` from SANDBOX.

    Returns {compiled, elapsed, stdout_tail, rc, timed_out?}.
    """
    started = time.time()
    try:
        proc = subprocess.Popen(
            ["nice", "-n", "10", "lake", "env", "lean", file_rel],
            cwd=str(SANDBOX),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            elapsed = round(time.time() - started, 2)
            out = (stdout or "") + "\n" + (stderr or "")
            err = bool(LEAN_ERR_RE.search(out))
            compiled = (proc.returncode == 0) and (not err)
            return {
                "compiled": compiled,
                "elapsed": elapsed,
                "stdout_tail": out[-400:],
                "rc": proc.returncode,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), 9)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
            return {
                "compiled": False,
                "elapsed": float(timeout),
                "stdout_tail": "",
                "rc": None,
                "timed_out": True,
            }
    except Exception as e:
        return {
            "compiled": False,
            "elapsed": round(time.time() - started, 2),
            "stdout_tail": "",
            "rc": None,
            "timed_out": False,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# row reading / variant synthesis
# ---------------------------------------------------------------------------

HAMMER_TAIL_RE = re.compile(r":=\s*by\s+hammer\s*$", re.MULTILINE)
BY_TAIL_RE = re.compile(r":=\s*by\s+([A-Za-z_][\w']*)\s*$", re.MULTILINE)


def read_row(row_path: Path) -> dict:
    src = row_path.read_text()
    # Pull a goal_before approximation: the example signature line.
    sig_match = re.search(r"^(example|theorem|lemma)\b.*", src, re.MULTILINE | re.DOTALL)
    goal = ""
    if sig_match:
        text = sig_match.group(0)
        # Trim at `:= by`
        idx = text.find(":= by")
        if idx >= 0:
            text = text[:idx].strip()
        goal = text.strip()
    return {"src": src, "goal_before": goal}


def synth_variant(src: str, tactic: str) -> str:
    """Replace the trailing `by hammer` / `by <anything>` with `by <tactic>`.

    Falls back to appending if no match (defensive).
    """
    if HAMMER_TAIL_RE.search(src):
        return HAMMER_TAIL_RE.sub(f":= by {tactic}", src, count=1)
    if BY_TAIL_RE.search(src):
        return BY_TAIL_RE.sub(f":= by {tactic}", src, count=1)
    # Fallback: append
    return src.rstrip() + f"\n-- fallback append\n:= by {tactic}\n"


# ---------------------------------------------------------------------------
# scaffold predictors (no LLM)
# ---------------------------------------------------------------------------

def predict_l2_op(goal_text: str) -> str:
    """Cheap keyword heuristic for the L2 structural op signature.

    Deterministic, no LLM. Returns the catalog op tag or a fallback.
    """
    g = goal_text.lower()
    if "‖" in goal_text or "norm" in g or "triangle" in g:
        return "core_03_decomposition"
    if "continuous" in g or "differen" in g or "deriv" in g or "fderiv" in g:
        return "PDE_op_11_external_theorem_typed_import"
    if re.search(r"\^|pow|cube|square", g):
        return "PDE_op_07_representation"
    if re.search(r"\bnat\b|ℕ|\binduction\b", g):
        return "core_02_generalization_abstraction"
    if re.search(r"≤|<|≥|>|inequal", goal_text):
        return "PDE_op_05_sharpness_failure_witness"
    return "core_03_decomposition"


def predict_l4_archetype(goal_text: str, catalog: dict) -> str:
    """Cheap keyword heuristic for the L4 archetype.

    Looks at the rendered goal and picks an archetype id. Deterministic.
    """
    g = goal_text.lower()
    # k-fold monotonicity / triangle / dist chain --> gcongr
    if ("‖" in goal_text and "+" in goal_text and "≤" in goal_text):
        return "A08_gcongr_monotonicity"
    if re.search(r"\bring\b|polynomial|=|identity", g) and ("^" in goal_text or "*" in goal_text):
        return "A05_ring_close"
    if "continuous" in g or "epsilon" in g or "δ" in goal_text or "delta" in g:
        return "A09_apply_named_lemma"
    if re.search(r"\binduction\b|\bnat\b|ℕ", g):
        return "A03_induction_step"
    if re.search(r"\bcases\b|\brcases\b|by_cases", g):
        return "A04_case_split"
    if re.search(r"\^|pow_sub_pow|pow_lt_pow", g):
        return "A06_linarith_close"
    return "A99_other_uncategorized"


# ---------------------------------------------------------------------------
# mode runners
# ---------------------------------------------------------------------------

def mode_A_basic_tactics(
    row_path: Path,
    row_src: str,
    budget: int,
    workers: int,
) -> dict:
    """Try each BASIC_TACTIC individually, sequentially in chunks of `workers`.

    Stops early once a tactic closes. Reports the first closer (priority is
    the BASIC_TACTICS list order).
    """
    started = time.time()
    tactics_tried: list[dict] = []
    closing: Optional[str] = None

    # Stage temp variants in a tmpdir UNDER SANDBOX so `lake env` resolves
    # mathlib/Hammer the same way.
    tmpdir = Path(tempfile.mkdtemp(prefix="route_c_modeA_", dir=str(SANDBOX)))
    try:
        # Write all variants
        variant_paths: list[tuple[str, Path]] = []
        for tac in BASIC_TACTICS:
            variant_src = synth_variant(row_src, tac)
            variant_path = tmpdir / f"{row_path.stem}__{tac}.lean"
            variant_path.write_text(variant_src)
            variant_paths.append((tac, variant_path))

        # Chunked parallel execution; stop early if any closes
        idx = 0
        while idx < len(variant_paths) and closing is None:
            chunk = variant_paths[idx : idx + workers]
            wait_for_load(1.5)
            chunk_started = time.time()
            print(
                f"  [{now()}] modeA chunk {idx // workers + 1}: "
                f"{[t for t, _ in chunk]}"
            )
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
                fut_to_tac = {
                    ex.submit(
                        run_lean_safe,
                        str(p.relative_to(SANDBOX)),
                        budget,
                    ): (tac, p)
                    for tac, p in chunk
                }
                chunk_results: list[dict] = []
                for fut in concurrent.futures.as_completed(fut_to_tac):
                    tac, p = fut_to_tac[fut]
                    res = fut.result()
                    rec = {
                        "tactic": tac,
                        "compiled": res["compiled"],
                        "elapsed_s": res["elapsed"],
                        "timed_out": res.get("timed_out", False),
                        "stdout_tail": res.get("stdout_tail", "")[-200:],
                    }
                    chunk_results.append(rec)
                    mark = (
                        "OK"
                        if res["compiled"]
                        else ("TO" if res.get("timed_out") else "..")
                    )
                    print(
                        f"    [{now()}] {mark} {tac:<12} "
                        f"compiled={res['compiled']} elapsed={res['elapsed']}s"
                    )
            # Append in BASIC_TACTICS priority order
            for tac, _ in chunk:
                for rec in chunk_results:
                    if rec["tactic"] == tac:
                        tactics_tried.append(rec)
                        if rec["compiled"] and closing is None:
                            closing = tac
            idx += workers
    finally:
        # Cleanup variant tempdir
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

    return {
        "compiled": closing is not None,
        "closing_tactic": closing,
        "elapsed_total_s": round(time.time() - started, 2),
        "tactics_tried": tactics_tried,
    }


def mode_B_route_c(row_path: Path, row_src: str) -> dict:
    return {
        "compiled": False,
        "scaffold_only": True,
        "note": (
            "Route C (LLM-proposed proof) not invoked: operator constraint "
            "in this harness pass. Wire codex/claude subagent + premise oracle "
            "downstream."
        ),
    }


def mode_C_structural_only(row_path: Path, row_src: str, goal: str) -> dict:
    return {
        "compiled": False,
        "L2_op_predicted": predict_l2_op(goal),
        "scaffold_only": True,
        "note": (
            "Default-tactic-family routing from L2 op is not executed here. "
            "Predicted op is logged for downstream comparison."
        ),
    }


def mode_D_archetype_only(
    row_path: Path,
    row_src: str,
    goal: str,
    catalog: dict,
    budget: int = 60,
) -> dict:
    """Predict ARCH-001..008 archetype and execute its direct (argument-free)
    recommended tactics. Indirect tactics requiring lemma names / witnesses /
    induction branches are flagged but not executed (those need Route C).
    """
    legacy_arche = predict_l4_archetype(goal, catalog)
    legacy_meta = catalog.get("archetypes", {}).get(legacy_arche, {})

    # Reviewer-spec ARCH-001..008 classification
    reviewer = None
    if HAVE_REVIEWER_CLASSIFIER:
        try:
            reviewer = classify_arch_reviewer_spec(row_src)
        except Exception as e:  # noqa: BLE001
            reviewer = {"error": str(e)}

    reviewer_arch = (reviewer or {}).get("predicted_L4_archetype", "")
    direct_tactics = ARCH_DIRECT_TACTICS.get(reviewer_arch, [])

    # If reviewer-spec gave an executable archetype, run its direct tactics.
    tactics_tried: list[dict] = []
    closing: Optional[str] = None
    elapsed_total = 0.0

    if direct_tactics:
        started = time.time()
        tmpdir = Path(tempfile.mkdtemp(prefix="route_c_modeD_", dir=str(SANDBOX)))
        try:
            for tac in direct_tactics:
                if closing is not None:
                    break
                wait_for_load(1.5)
                variant_src = synth_variant(row_src, tac)
                variant_path = tmpdir / f"{row_path.stem}__D_{tac.split()[0]}.lean"
                variant_path.write_text(variant_src)
                res = run_lean_safe(str(variant_path.relative_to(SANDBOX)), budget)
                rec = {
                    "tactic": tac,
                    "compiled": res["compiled"],
                    "elapsed_s": res["elapsed"],
                    "timed_out": res.get("timed_out", False),
                    "stdout_tail": res.get("stdout_tail", "")[-200:],
                }
                tactics_tried.append(rec)
                if res["compiled"]:
                    closing = tac
        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
        elapsed_total = round(time.time() - started, 2)

    return {
        "compiled": closing is not None,
        "closing_tactic": closing,
        "elapsed_total_s": elapsed_total,
        "tactics_tried": tactics_tried,
        "L4_archetype_predicted_legacy": legacy_arche,
        "L4_archetype_predicted_reviewer_spec": reviewer_arch,
        "L4_archetype_confidence": (reviewer or {}).get("confidence"),
        "L3_anti_pattern_flags": (reviewer or {}).get("predicted_L3_anti_pattern_flags", []),
        "L2_structural_ops": (reviewer or {}).get("predicted_L2_structural_ops", []),
        "direct_tactics_executed": direct_tactics,
        "indirect_tactics_skipped": [
            t for t in (reviewer or {}).get("recommended_tactic_sequence", [])
            if t not in direct_tactics
        ],
        "scaffold_only": not bool(direct_tactics),
        "note": (
            "Mode D now executes argument-free recommended tactics from the "
            "reviewer-spec ARCH-001..008 classifier; indirect tactics requiring "
            "lemma names / witnesses / induction branches are listed but skipped "
            "(those require Route C / LLM wiring)."
        ),
    }


def mode_Full(
    row_path: Path,
    row_src: str,
    goal: str,
    catalog: dict,
) -> dict:
    return {
        "compiled": False,
        "L2_op_predicted": predict_l2_op(goal),
        "L4_archetype_predicted": predict_l4_archetype(goal, catalog),
        "anti_pattern_guard": "scaffold_only",
        "route_c_attempt": "scaffold_only",
        "scaffold_only": True,
        "note": (
            "Full mode combines C + D + anti-pattern guard + Route C. "
            "Scaffolded here pending LLM wiring."
        ),
    }


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def run_modes_for_row(
    row_path: Path,
    modes: list[str],
    budget: int,
    workers: int,
    catalog: dict,
) -> dict:
    info = read_row(row_path)
    src = info["src"]
    goal = info["goal_before"]
    results: dict = {}

    if "A" in modes:
        print(f"\n[{now()}] === row={row_path.name} mode=A ===")
        results["A_basic_tactics_only"] = mode_A_basic_tactics(
            row_path, src, budget, workers
        )
    if "B" in modes:
        results["B_route_c_alone"] = mode_B_route_c(row_path, src)
    if "C" in modes:
        results["C_structural_only"] = mode_C_structural_only(row_path, src, goal)
    if "D" in modes:
        results["D_archetype_only"] = mode_D_archetype_only(
            row_path, src, goal, catalog, budget
        )
    if "Full" in modes:
        results["Full"] = mode_Full(row_path, src, goal, catalog)

    honest_count = {
        "A_closed": bool(results.get("A_basic_tactics_only", {}).get("compiled", False)),
        "B_closed": bool(results.get("B_route_c_alone", {}).get("compiled", False)),
        "C_closed": bool(results.get("C_structural_only", {}).get("compiled", False)),
        "D_closed": bool(results.get("D_archetype_only", {}).get("compiled", False)),
        "Full_closed": bool(results.get("Full", {}).get("compiled", False)),
    }

    return {
        "row_id": row_path.stem,
        "row_file": str(row_path),
        "goal_before": goal,
        "results": results,
        "honest_count": honest_count,
    }


def expand_modes(arg: str) -> list[str]:
    if arg == "all":
        return ["A", "B", "C", "D", "Full"]
    valid = {"A", "B", "C", "D", "Full"}
    if arg not in valid:
        raise SystemExit(f"--mode must be one of {valid | {'all'}}, got {arg!r}")
    return [arg]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row-file", help="single Lean row file")
    ap.add_argument("--rows", nargs="+", default=None, help="multiple Lean row files")
    ap.add_argument(
        "--mode", default="all", help="A | B | C | D | Full | all (default all)"
    )
    ap.add_argument("--out", default=None)
    ap.add_argument("--budget", type=int, default=60, help="per-tactic timeout (s)")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()

    if not args.row_file and not args.rows:
        ap.error("must provide --row-file or --rows")

    row_files: list[Path] = []
    if args.row_file:
        row_files.append(Path(args.row_file))
    if args.rows:
        row_files.extend(Path(r) for r in args.rows)

    for p in row_files:
        if not p.exists():
            raise SystemExit(f"row file does not exist: {p}")

    catalog = json.loads(ARCHETYPE_CATALOG.read_text())
    modes = expand_modes(args.mode)

    print(
        f"[route_c_archetype_runner] {len(row_files)} rows, modes={modes}, "
        f"budget={args.budget}s, workers={args.workers}, nice +10"
    )

    rows_out = []
    for rp in row_files:
        rec = run_modes_for_row(rp, modes, args.budget, args.workers, catalog)
        rows_out.append(rec)

    aggregate = {
        "n_rows": len(rows_out),
        "modes": modes,
        "budget_s": args.budget,
        "workers": args.workers,
        "totals": {
            "A_closed": sum(1 for r in rows_out if r["honest_count"]["A_closed"]),
            "B_closed": sum(1 for r in rows_out if r["honest_count"]["B_closed"]),
            "C_closed": sum(1 for r in rows_out if r["honest_count"]["C_closed"]),
            "D_closed": sum(1 for r in rows_out if r["honest_count"]["D_closed"]),
            "Full_closed": sum(1 for r in rows_out if r["honest_count"]["Full_closed"]),
        },
    }

    out_blob = {
        "version": "route_c_archetype_runner_v1_2026_05_15",
        "aggregate": aggregate,
        "rows": rows_out,
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out_blob, indent=2, sort_keys=True))
        print(f"\n[route_c_archetype_runner] wrote {out_path}")
    else:
        print(json.dumps(out_blob, indent=2, sort_keys=True))

    print("\n=== AGGREGATE ===")
    print(json.dumps(aggregate, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
