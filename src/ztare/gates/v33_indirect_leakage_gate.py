#!/usr/bin/env python3
"""v33_indirect_leakage_gate.py — leakage-independent simp/fun_prop indirect-leakage organ.

Fourth forward gate (after vacuity + paraphrase + single-lemma-exact).
Catches the 4th/5th new anti-patterns this session: a "closure" via bare
`simp` / `simp_all` / `fun_prop` / `aesop` / `continuity` / `measurability`
where the GLOBAL @[simp]/@[fun_prop] attribute set silently carries the
gold lemma — zero explicit lemma citation. Functionally a single-apply of
the gold lemma laundered through the global automation set.

Same proven pattern, ZERO audit verdict:

  Component 1 (instant shape, no proof exec): indirect_leakage_suspect iff
    the closing tactic is a GLOBAL-SET automation tactic with NO explicit
    `[lemma,...]` args and NO non-automation composition (no have/calc/
    linarith chaining ≥2 steps).

  Component 2 (independent — two Lean compiles, no audit verdict):
    (a) trivial-floor probe: `:= by first | rfl | trivial | simp only []
        | norm_num | decide`  — does the goal close WITHOUT any lemma set?
    (b) automation probe: `:= by <the flagged automation tactic>`
    CONFIRMED indirect leakage iff (a) FAILS and (b) SUCCEEDS:
      the goal is NON-trivial yet the global automation set closes it with
      ZERO explicit citation — the global set carried a gold lemma.
    If (a) succeeds → it's floor-trivial (different category, NOT this).

Ground-truth validation:
  + Continuous (fun x:ℝ => 2*x+1)  via fun_prop  -> (a) fails, (b) ok -> CONFIRM
  - (1:ℝ) = 1                       via simp      -> (a) ok            -> NOT (floor-trivial)
  - H07 4-term triangle (have+linarith)           -> Component-1 clean -> NOT
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
DEFAULT_SANDBOX = ROOT / ("analytics/public/leanmill/external_benchmarks/"
                          "sandboxes/v28A_carleson_baseline/carleson")
LEAN_ERR_RE = re.compile(r"^\S*\.lean:\d+:\d+: error:", re.MULTILINE)
GLOBAL_SET_TACTICS = ("simp_all", "simp", "fun_prop", "aesop", "continuity", "measurability")


def detect_shape(row_text: str) -> dict:
    m = re.search(r":=\s*by\b(.*)$", row_text, re.DOTALL)
    body = (m.group(1).strip() if m else "")
    if not body:
        return {"indirect_leakage_suspect": False, "reason": "no tactic body"}
    # closing automation tactic with NO explicit [lemma] args
    closer = None
    for t in GLOBAL_SET_TACTICS:
        # match `t` not followed by `[` (no explicit lemma list) and not `simp only`
        if re.search(rf"\b{t}\b(?!\s*only)(?!\s*\[)", body):
            closer = t
            break
    n_have = len(re.findall(r"\bhave\b", body))
    has_composition = any(c in body for c in ("calc", "linarith", "nlinarith")) and n_have >= 2
    explicit_lemma_args = bool(re.search(r"\b(?:simp|simp_all|aesop)\s*\[", body))
    suspect = (closer is not None) and (not has_composition) and (not explicit_lemma_args)
    return {
        "indirect_leakage_suspect": bool(suspect),
        "closer_tactic": closer,
        "n_have": n_have,
        "has_multistep_composition": has_composition,
        "explicit_lemma_args": explicit_lemma_args,
        "body_preview": body[:140],
    }


def _compile(probe: str, sandbox: Path, timeout: int) -> bool | None:
    tmpdir = sandbox / "V33IndirectProbe"
    tmpdir.mkdir(exist_ok=True)
    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".lean", dir=str(tmpdir), delete=False)
    tf.write(probe); tf.close()
    rel = Path(tf.name).relative_to(sandbox)
    try:
        p = subprocess.run(["nice", "-n", "10", "lake", "env", "lean", str(rel)],
                            cwd=str(sandbox), text=True, capture_output=True,
                            timeout=timeout, check=False)
        out = (p.stdout or "") + "\n" + (p.stderr or "")
        return (p.returncode == 0) and (not LEAN_ERR_RE.search(out))
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def independent_verify(row_text: str, closer: str, sandbox: Path, timeout: int = 70) -> dict:
    if not sandbox.exists():
        return {"indirect_leakage_confirmed": None, "error": "sandbox missing"}
    floor = re.sub(r":=\s*by\b.*$",
                   ":= by first | rfl | trivial | simp only [] | norm_num | decide",
                   row_text.strip(), count=1, flags=re.DOTALL)
    autom = re.sub(r":=\s*by\b.*$", f":= by {closer}",
                   row_text.strip(), count=1, flags=re.DOTALL)
    started = time.time()
    floor_ok = _compile(floor, sandbox, timeout)
    autom_ok = _compile(autom, sandbox, timeout)
    confirmed = (floor_ok is False) and (autom_ok is True)
    return {
        "indirect_leakage_confirmed": confirmed,
        "trivial_floor_closes": floor_ok,
        "global_automation_closes": autom_ok,
        "elapsed_s": round(time.time() - started, 2),
        "interpretation": ("global automation set carried a NON-trivial closure with zero "
                           "explicit citation — indirect leakage"
                           if confirmed else
                           ("floor-trivial (different category)" if floor_ok
                            else "automation did not close / inconclusive")),
    }


def preflight_probe_goal(row_text: str, sandbox: Path, timeout: int = 70) -> dict:
    """Preflight: does the BARE goal fail trivial-floor yet close via a
    global-set automation tactic (fun_prop / simp / aesop)? If so, any LLM
    'moat closure' here is indirect-leakage-equivalent — Lean's own global
    set already solves it. Leakage-independent (Lean only, no audit verdict)."""
    if not sandbox.exists():
        return {"preflight_indirect_leakage": None, "error": "sandbox missing"}
    floor = re.sub(r":=\s*by\b.*$|:=\s*sorry\s*$",
                   ":= by first | rfl | trivial | simp only [] | norm_num | decide",
                   row_text.strip(), count=1, flags=re.DOTALL)
    if ":=" not in floor:
        floor = row_text.strip() + " := by first | rfl | trivial | simp only [] | norm_num | decide"
    floor_ok = _compile(floor, sandbox, timeout)
    if floor_ok is True:
        return {"preflight_indirect_leakage": False, "trivial_floor_closes": True,
                "interpretation": "floor-trivial — not indirect leakage"}
    for closer in ("fun_prop", "simp", "aesop"):
        probe = re.sub(r":=\s*by\b.*$|:=\s*sorry\s*$", f":= by {closer}",
                       row_text.strip(), count=1, flags=re.DOTALL)
        if ":=" not in probe:
            probe = row_text.strip() + f" := by {closer}"
        if _compile(probe, sandbox, timeout) is True:
            return {
                "preflight_indirect_leakage": True,
                "trivial_floor_closes": False,
                "global_automation_closer": closer,
                "interpretation": (f"bare goal is NON-trivial yet Lean's own `{closer}` "
                                   f"closes it via the global @[{closer}]/@[simp] set — "
                                   f"an LLM 'moat closure' here is indirect-leakage-"
                                   f"equivalent. Leakage-independent (Lean only)."),
            }
    return {"preflight_indirect_leakage": False, "trivial_floor_closes": False,
            "interpretation": "neither floor nor global automation closes — genuine target"}


GT = [
    ("positive_funprop",
     "import Mathlib\nexample : Continuous (fun x : ℝ => 2 * x + 1) := by fun_prop", True),
    ("negative_floor",
     "import Mathlib\nexample : (1 : ℝ) = 1 := by simp", False),
    ("negative_H07",
     "import Mathlib\nexample {E : Type*} [SeminormedAddCommGroup E] (a b c d : E) : "
     "‖a - d‖ ≤ ‖a - b‖ + ‖b - c‖ + ‖c - d‖ := by\n"
     "  have h1 : ‖a - d‖ ≤ ‖a - c‖ + ‖c - d‖ := norm_sub_le_norm_sub_add_norm_sub a c d\n"
     "  have h2 : ‖a - c‖ ≤ ‖a - b‖ + ‖b - c‖ := norm_sub_le_norm_sub_add_norm_sub a b c\n"
     "  linarith", False),
]


def run_validation(sandbox: Path) -> dict:
    res = {}
    for tag, src, expect in GT:
        s = detect_shape(src)
        v = None
        if s["indirect_leakage_suspect"]:
            v = independent_verify(src, s["closer_tactic"], sandbox)
        confirmed = bool(v and v.get("indirect_leakage_confirmed"))
        res[tag] = {"shape": s, "verify": v, "expect_confirmed": expect, "got_confirmed": confirmed,
                    "pass": (confirmed == expect)}
    allok = all(r["pass"] for r in res.values())
    res["verdict"] = "INDIRECT_LEAKAGE_GATE_VALIDATED" if allok else "GATE_FAILS_GROUND_TRUTH"
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.validate:
        r = run_validation(DEFAULT_SANDBOX)
        print(json.dumps(r, indent=2, ensure_ascii=False))
        if args.out:
            Path(args.out).write_text(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if r["verdict"] == "INDIRECT_LEAKAGE_GATE_VALIDATED" else 1
    if args.file:
        txt = Path(args.file).read_text()
        s = detect_shape(txt)
        v = independent_verify(txt, s["closer_tactic"], DEFAULT_SANDBOX) if s["indirect_leakage_suspect"] else None
        print(json.dumps({"shape": s, "verify": v}, indent=2, ensure_ascii=False))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
