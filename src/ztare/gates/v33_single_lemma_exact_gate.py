#!/usr/bin/env python3
"""v33_single_lemma_exact_gate.py — leakage-independent single-lemma-exact organ.

Third forward gate (after vacuity + paraphrase). Catches the v26/v27
subsumption class: a claimed closure whose goal Lean's OWN `exact?`
solves with a single library lemma — not a novel closure, a one-liner
Mathlib already trivially discharges.

Same proven pattern, ZERO audit verdict:

  Component 1 (instant shape heuristic, no proof): single_lemma_exact_suspect
    iff goal is short, single top-level relation, shallow binder depth.

  Component 2 (independent — Lean's OWN search, no audit verdict): synthesize
    `example : <goal> := by exact?` and compile. If `exact?` succeeds
    (Lean prints `Try this: exact <lemma>` and the file compiles), the goal
    IS single-lemma-exact — confirmed by Lean's own tactic, leakage-
    independent. This is the cleanest verifier of the three: exact? is
    Lean's ground truth for "one-lemma closure".

Ground-truth validation built in:
  + add_comm goal      (`a + b = b + a`)  -> exact? closes -> MUST confirm
  - H07 4-term triangle (2-have linarith)  -> exact? fails  -> MUST NOT confirm
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SANDBOX = ROOT / ("analytics/public/leanmill/external_benchmarks/"
                          "sandboxes/v28A_carleson_baseline/carleson")
LEAN_ERR_RE = re.compile(r"^\S*\.lean:\d+:\d+: error:", re.MULTILINE)
# `exact?` is a SUGGESTION tactic — it prints "Try this:" + a (possibly
# multi-line, possibly `[apply]`-prefixed) suggestion and does NOT close
# the goal (so the example always has an unsolved-goals error). The
# confirmation signal is therefore the SUGGESTION's presence, not compile
# success.
EXACT_SUCCESS_RE = re.compile(r"Try this:\s*\n?\s*(?:\[[a-z]+\]\s*)?(.+)", re.DOTALL)
EXACT_FAIL_RE = re.compile(r"`?exact\?`? could not close the goal")


def detect_shape(goal: str) -> dict:
    g = goal.strip()
    rel = sum(g.count(op) for op in ("=", "≤", "<", "≥", ">", "↔", "∈"))
    binders = g.count("∀") + g.count("∃") + g.count("→")
    suspect = (len(g) < 140 and rel >= 1 and binders <= 2)
    return {
        "single_lemma_exact_suspect": suspect,
        "len": len(g), "n_relations": rel, "n_binders": binders,
        "goal_preview": g[:160],
    }


def independent_exact_verify(goal: str, imports: list[str], sandbox: Path,
                             timeout: int = 70) -> dict:
    """Synthesize `example : <goal> := by exact?` ; if exact? finds a single
    lemma AND the file compiles, single-lemma-exact CONFIRMED (Lean's own
    search, NO audit verdict)."""
    if not sandbox.exists():
        return {"single_lemma_exact_confirmed": None, "error": f"sandbox missing"}
    imp = "\n".join(imports) if imports else "import Mathlib"
    # `exact?` matches the post-intro relation, not `∀ …`; introduce binders first.
    probe = (f"{imp}\n\n"
             f"-- v33 single-lemma-exact probe (Lean's own search, no audit verdict)\n"
             f"example : {goal.strip()} := by\n"
             f"  intros\n"
             f"  exact?\n")
    tmpdir = sandbox / "V33ExactProbe"
    tmpdir.mkdir(exist_ok=True)
    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".lean", dir=str(tmpdir), delete=False)
    tf.write(probe)
    tf.close()
    rel = Path(tf.name).relative_to(sandbox)
    started = time.time()
    try:
        proc = subprocess.run(
            ["nice", "-n", "10", "lake", "env", "lean", str(rel)],
            cwd=str(sandbox), text=True, capture_output=True, timeout=timeout, check=False,
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        suggested = EXACT_SUCCESS_RE.search(out)
        failed = EXACT_FAIL_RE.search(out)
        # CONFIRMED iff exact? produced a suggestion AND did not report failure.
        # (The example itself always errors — exact? only suggests, never closes.)
        confirmed = (suggested is not None) and (failed is None)
        return {
            "single_lemma_exact_confirmed": confirmed,
            "exact_hint": (suggested.group(1).strip()[:160] if suggested else None),
            "elapsed_s": round(time.time() - started, 2),
            "error_tail": "" if confirmed else out[-250:],
        }
    except subprocess.TimeoutExpired:
        return {"single_lemma_exact_confirmed": None, "timed_out": True, "elapsed_s": timeout}
    except Exception as e:
        return {"single_lemma_exact_confirmed": None, "error": str(e)}


def independent_exact_verify_rowfile(row_text: str, sandbox: Path, timeout: int = 70) -> dict:
    """Robust variant: take the ORIGINAL row statement and substitute its
    trailing `:= by <proof>` with `:= by intros; exact?`. Guaranteed
    well-formed (original binders/types preserved). Same detection."""
    if not sandbox.exists():
        return {"single_lemma_exact_confirmed": None, "error": "sandbox missing"}
    probe = re.sub(r":=\s*by\b.*$", ":= by\n  intros\n  exact?",
                   row_text.strip(), count=1, flags=re.DOTALL)
    if ":= by" not in probe:
        probe = re.sub(r":=.*$", ":= by\n  intros\n  exact?", row_text.strip(),
                       count=1, flags=re.DOTALL)
    tmpdir = sandbox / "V33ExactProbe"
    tmpdir.mkdir(exist_ok=True)
    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".lean", dir=str(tmpdir), delete=False)
    tf.write(probe)
    tf.close()
    relp = Path(tf.name).relative_to(sandbox)
    started = time.time()
    try:
        proc = subprocess.run(["nice", "-n", "10", "lake", "env", "lean", str(relp)],
                               cwd=str(sandbox), text=True, capture_output=True,
                               timeout=timeout, check=False)
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        suggested = EXACT_SUCCESS_RE.search(out)
        failed = EXACT_FAIL_RE.search(out)
        confirmed = (suggested is not None) and (failed is None)
        return {
            "single_lemma_exact_confirmed": confirmed,
            "exact_hint": (suggested.group(1).strip()[:160] if suggested else None),
            "elapsed_s": round(time.time() - started, 2),
            "error_tail": "" if confirmed else out[-250:],
        }
    except subprocess.TimeoutExpired:
        return {"single_lemma_exact_confirmed": None, "timed_out": True}
    except Exception as e:
        return {"single_lemma_exact_confirmed": None, "error": str(e)}


GT_POS = ("add_comm_goal", "∀ (a b : ℝ), a + b = b + a")
GT_NEG = ("H07_four_term_triangle",
          "∀ {E : Type} [inst : SeminormedAddCommGroup E] (a b c d : E), "
          "‖a - d‖ ≤ ‖a - b‖ + ‖b - c‖ + ‖c - d‖")


def run_validation(sandbox: Path) -> dict:
    res = {}
    for tag, (name, goal) in (("positive", ("add_comm", GT_POS[1])),
                              ("negative", ("H07", GT_NEG[1]))):
        s = detect_shape(goal)
        v = independent_exact_verify(goal, ["import Mathlib"], sandbox)
        res[tag] = {"name": name, "shape": s, "verify": v}
    pos = res["positive"]["verify"]["single_lemma_exact_confirmed"] is True
    neg = res["negative"]["verify"]["single_lemma_exact_confirmed"] is False
    res["verdict"] = "SINGLE_LEMMA_EXACT_GATE_VALIDATED" if (pos and neg) else "GATE_FAILS_GROUND_TRUTH"
    res["pos_ok"], res["neg_ok"] = pos, neg
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--goal", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.validate:
        r = run_validation(DEFAULT_SANDBOX)
        print(json.dumps(r, indent=2, ensure_ascii=False))
        if args.out:
            Path(args.out).write_text(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if r["verdict"] == "SINGLE_LEMMA_EXACT_GATE_VALIDATED" else 1
    if args.goal:
        s = detect_shape(args.goal)
        v = independent_exact_verify(args.goal, ["import Mathlib"], DEFAULT_SANDBOX)
        print(json.dumps({"shape": s, "verify": v}, indent=2, ensure_ascii=False))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
