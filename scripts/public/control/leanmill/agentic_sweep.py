#!/usr/bin/env python3
"""Agentic LLM-leaf sweep — the multi-step solver test, kernel-arbitrated.

Confirmed lever (2026-06-02): an agentic LLM leaf (codex on subscription, iterating against
`lake`) closed P1 d=0 kernel-clean by INVENTING a helper lemma + decomposing — a leaf the
one-shot deterministic battery (0/12) and read-only multi-step both failed. This sweeps that
leaf across components to get the real closure rate vs the one-shot 1/12.

Governance: the agent composes/iterates; THIS script independently re-verifies every claimed
closure with `lake env lean` + `#print axioms` ⊆ {propext, Classical.choice, Quot.sound}
(no sorryAx). The agent's self-report is never trusted.

Run ON the VPS (codex authed + lake). Each component is bounded by a wall-clock timeout.
"""
from __future__ import annotations
import argparse, re, subprocess, sys, time
from pathlib import Path

ATLAS = Path.home() / "figs_activist_loop/projects/atlas_lean_2026_05_29"
APN = Path.home() / "figs_activist_loop/projects/gp_spectral_apn_seed_2026_05_28/candidates/hilbert_functions_2_sorried.lean"
LAKE = Path.home() / ".elan/bin/lake"
ALLOW = {"propext", "Classical.choice", "Quot.sound"}

# components to attempt (P1 remaining arithmetic + the P2 sequence-property frontier)
COMPONENTS = [
    ("P1_d1", "pureOSequence GammaP1 1 = 3"),
    ("P1_d2", "pureOSequence GammaP1 2 = 4"),
    ("P1_d3", "pureOSequence GammaP1 3 = 2"),
    ("P2_unimodal", "ProblemP2Type1Unimodal"),
    ("P2_logconcave", "ProblemP2Type1LogConcave"),
]


def _defs():
    src = APN.read_text(encoding="utf-8")
    return src[:re.search(r"(?m)^\s*theorem\s+P2\b", src).start()]


def _verify(goal_name: str) -> tuple[bool, str]:
    """Independent kernel gate: compile the probe + scan #print axioms."""
    f = ATLAS / "SweepProbe.lean"
    txt = f.read_text(encoding="utf-8")
    if "#print axioms leaf" not in txt:
        f.write_text(txt + "\n#print axioms leaf\n", encoding="utf-8")
    r = subprocess.run([str(LAKE), "env", "lean", str(f)], cwd=str(ATLAS),
                       text=True, capture_output=True, timeout=200)
    out = (r.stdout or "") + (r.stderr or "")
    if "error" in out.lower() or "sorry" in out.lower():
        return False, "compile_error_or_sorry"
    if "does not depend on any axioms" in out:
        return True, "clean(no axioms)"
    m = re.search(r"depends on axioms:\s*\[([^\]]*)\]", out)
    if not m:
        return False, "no_axiom_line"
    ax = {a.strip() for a in m.group(1).split(",") if a.strip()}
    return (ax.issubset(ALLOW)), ("clean " + str(sorted(ax)) if ax.issubset(ALLOW) else "BAD_AXIOMS " + str(sorted(ax)))


def _run_component(name, goal, defs, timeout):
    probe = ATLAS / "SweepProbe.lean"
    probe.write_text(defs + f"\ntheorem leaf : {goal} := by\n  sorry\n", encoding="utf-8")
    prompt = (f"Prove the theorem named leaf in SweepProbe.lean (currently sorry): "
              f"theorem leaf : {goal}. Edit the file to replace sorry with a real proof, "
              f"then run: lake env lean SweepProbe.lean — iterate until it compiles with zero "
              f"errors and no sorry. The APN defs are already in the file. Do not add axioms.")
    t0 = time.time()
    try:
        subprocess.run(["timeout", str(timeout), "codex", "exec", "--skip-git-repo-check",
                        "-s", "workspace-write", "-o", "/tmp/sweep_ans.txt", prompt],
                       cwd=str(ATLAS), stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=timeout + 30)
    except subprocess.TimeoutExpired:
        pass
    dt = round(time.time() - t0)
    try:
        ok, why = _verify(name)
    except Exception as e:
        ok, why = False, f"verify_err:{str(e)[:50]}"
    return ok, why, dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--only", default=None, help="comma-sep component names")
    a = ap.parse_args()
    defs = _defs()
    comps = COMPONENTS
    if a.only:
        keep = set(a.only.split(","))
        comps = [(n, g) for n, g in COMPONENTS if n in keep]
    print(f"[sweep] agentic LLM-leaf over {len(comps)} components, {a.timeout}s each", flush=True)
    closed = 0
    for name, goal in comps:
        ok, why, dt = _run_component(name, goal, defs, a.timeout)
        if ok:
            closed += 1
        print(f"  [{name:14}] {'CLOSED' if ok else 'open  '} ({dt}s) {why} | ⊢ {goal[:50]}", flush=True)
    print(f"\n[sweep] agentic leaf closed {closed}/{len(comps)} "
          f"(one-shot deterministic baseline closed 0 of these). "
          f"Residual = the genuine invention frontier for THIS corpus.")


if __name__ == "__main__":
    main()
