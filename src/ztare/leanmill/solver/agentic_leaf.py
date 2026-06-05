"""Agentic LLM-leaf solver — the validated multi-step proof-search lever, productionized.

Empirically established 2026-06-02 (GP-246 seam): an agentic LLM leaf (codex/claude on the
operator's SUBSCRIPTION, iterating against `lake`) closes leaves that one-shot deterministic
search cannot — by INVENTING helper lemmas and decomposing — and reduces hard theorems to
proven scaffolding + a localized mathematical core. The deterministic vocabulary/router added
zero lift in one-shot mode; the lever is the agentic iterate-against-the-kernel loop.

This module codifies that loop as a reusable, SUBSTRATE-NEUTRAL primitive (works for any Lean
goal in any lake project — no APN/NS specifics). Three non-negotiable invariants, each a hard
lesson from this thread:

  1. CALIBRATION FIRST (fail-closed). Before any "could not prove" is admissible, BOTH
     instruments pass a positive control run through the SAME path the real work uses:
     the LLM provider must return a live trivial answer, AND the Lean substrate must pass
     substrate_liveness. A null from an un-calibrated instrument is INADMISSIBLE — that is
     how the dead REPL / dead-key / prompt-not-delivered episodes masqueraded as real
     negatives. (see substrate_liveness; feedback_negative_inadmissible_without_calibration)
  2. AGENT COMPOSES, KERNEL ARBITRATES. The agent's self-report ("it compiles") is never
     trusted. THIS module independently re-verifies: the proof compiles, no `sorry`, and
     `#print axioms ⊆ {propext, Classical.choice, Quot.sound}` (no sorryAx, no smuggled axiom).
  3. SUBSCRIPTION ONLY for OpenAI(codex)/Anthropic(claude). Never the metered API.

Dispatch + verify are injected callables (defaults provided) so the loop is unit-testable
offline and the substrate specifics live in the caller, not here.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

AXIOM_ALLOWLIST = {"propext", "Classical.choice", "Quot.sound"}
_AXIOM_LINE = re.compile(r"depends on axioms:\s*\[([^\]]*)\]")


# ── independent kernel gate (agent self-report is never trusted) ─────────────
def verify_lean_proof(probe_path: str | Path, target: str, *, lake_bin: str,
                      project_dir: str | Path, timeout: int = 250,
                      retries: int = 1) -> tuple[bool, str]:
    """Compile the probe via `lake env lean` and gate on #print axioms. Returns
    (closed, reason). closed iff: compiles, no `sorry`, axioms ⊆ allowlist.

    Hardened against TRANSIENTS (the verify itself must not produce a false negative): the
    agent runs its OWN concurrent `lake` builds during the agentic dispatch, which can race
    a verify and surface a spurious error/timeout. So a non-clean first result is RE-RUN on a
    fresh read before being trusted — a real error reproduces; a transient/race does not."""
    import os
    p = Path(probe_path)
    txt = p.read_text(encoding="utf-8", errors="replace")
    if f"#print axioms {target}" not in txt:
        p.write_text(txt + f"\n#print axioms {target}\n", encoding="utf-8")
    # ABSOLUTE lean arg: cwd=project_dir, so a repo-relative probe path would DOUBLE
    # (project_dir/project_dir/probe → file-not-found → spurious 'error'). abspath fixes it.
    lean_arg = os.path.abspath(str(p))
    last = (False, "not_run")
    for attempt in range(retries + 1):
        try:
            r = subprocess.run([str(lake_bin), "env", "lean", lean_arg], cwd=str(project_dir),
                               text=True, capture_output=True, timeout=timeout)
            last = parse_verify_output((r.stdout or "") + (r.stderr or ""))
        except subprocess.TimeoutExpired:
            last = (False, "verify_timeout(transient?)")
        if last[0]:           # clean → trust immediately
            return last
        # not clean: if more attempts remain, re-run (defeats a build-race false negative)
    return last


def parse_verify_output(out: str) -> tuple[bool, str]:
    """Pure parser (unit-testable): classify a `lake env lean` + #print-axioms transcript."""
    low = out.lower()
    if "error" in low:
        return False, "compile_error"
    if "sorry" in low:  # 'declaration uses sorry' / sorryAx
        return False, "uses_sorry"
    if "does not depend on any axioms" in out:
        return True, "clean(no axioms)"
    m = _AXIOM_LINE.search(out)
    if not m:
        return False, "no_axiom_line"
    ax = {a.strip() for a in m.group(1).split(",") if a.strip()}
    return (ax.issubset(AXIOM_ALLOWLIST),
            "clean " + str(sorted(ax)) if ax.issubset(AXIOM_ALLOWLIST)
            else "BAD_AXIOMS " + str(sorted(ax - AXIOM_ALLOWLIST)))


# ── dispatch (subscription CLI only) ─────────────────────────────────────────
def default_dispatch(prompt: str, *, runtime: str, repo: str | Path, timeout: int) -> str:
    """Agentic dispatch on the operator's SUBSCRIPTION (codex/claude) via the shared
    `common/subscription_agent_runtime` wrapper — NOT a bespoke subprocess, and never the
    metered API. workspace-write so the agent can edit the probe + run lake; `repo` is the
    cwd (the lake project). `default_codex_model="account-default"` omits `--model` so codex
    uses the strong account default rather than a weak pinned model."""
    from ztare.common.subscription_agent_runtime import run_subscription_agent_with_recovery
    run = run_subscription_agent_with_recovery(
        runtime=runtime, prompt=prompt, agent_id="agentic_leaf",
        repo=repo, session_state=None, timeout_seconds=timeout,
        codex_sandbox="workspace-write", default_codex_model="account-default")
    return (run.result.stdout or "") + "\n" + (run.result.stderr or "")


def provider_live(runtime: str, repo: str | Path, dispatch: Callable, timeout: int = 90) -> tuple[bool, str]:
    """Positive control: does the provider return a live trivial answer? (never read a
    'could not prove' off a dead/hung provider — the dead-codex lesson)."""
    try:
        out = dispatch("Reply with exactly the word: ALIVE", runtime=runtime, repo=repo, timeout=timeout)
        return ("ALIVE" in (out or "").upper()), (out or "")[:80]
    except Exception as e:
        return False, f"dispatch error: {str(e)[:80]}"


# ── the loop ─────────────────────────────────────────────────────────────────
@dataclass
class LeafResult:
    closed: bool
    target: str
    goal: str
    reason: str
    rounds: int = 0
    decomposed: bool = False
    calibration: dict = field(default_factory=dict)
    inadmissible: bool = False   # True ⇒ a negative here is NOT real (instrument not calibrated)


def _probe_text(defs: str, goal: str, target: str) -> str:
    return f"{defs.rstrip()}\n\ntheorem {target} : {goal} := by\n  sorry\n"


def solve_leaf(
    goal: str,
    *,
    defs: str,
    project_dir: str | Path,
    repo: str | Path,
    lake_bin: str,
    probe_name: str = "AgenticLeafProbe.lean",
    target: str = "leaf",
    runtime: str = "codex",
    timeout: int = 600,
    decompose: bool = True,
    dispatch: Callable = default_dispatch,
    verify: Optional[Callable] = None,
    substrate_calibrate: Optional[Callable] = None,
) -> LeafResult:
    """Solve one Lean leaf with the agentic loop. SUBSTRATE-NEUTRAL: pass the project's `defs`
    (in-scope declarations, no imports — base env carries Mathlib), `project_dir`, `lake_bin`.

    Calibration-first & fail-closed: if the provider or substrate is not live, returns
    inadmissible=True (NOT closed=False-as-signal). Agent composes; this fn verifies."""
    project_dir, repo = Path(project_dir), Path(repo)
    res = LeafResult(closed=False, target=target, goal=goal, reason="")

    # 1) CALIBRATION FIRST — both instruments, fail-closed.
    live, sample = provider_live(runtime, repo, dispatch)
    res.calibration["provider"] = {"runtime": runtime, "live": live, "sample": sample}
    if not live:
        res.reason = f"provider {runtime} not live ({sample}) — INADMISSIBLE"
        res.inadmissible = True
        return res
    if substrate_calibrate is not None:
        try:
            res.calibration["substrate"] = substrate_calibrate()
        except Exception as e:
            res.reason = f"substrate calibration failed: {str(e)[:120]} — INADMISSIBLE"
            res.inadmissible = True
            return res

    probe = project_dir / probe_name
    if verify is None:
        verify = lambda: verify_lean_proof(probe, target, lake_bin=lake_bin,
                                           project_dir=project_dir, timeout=250)

    # 2) direct agentic attempt
    probe.write_text(_probe_text(defs, goal, target), encoding="utf-8")
    direct = (f"Prove the theorem `{target}` in {probe_name} (currently `sorry`): "
              f"theorem {target} : {goal}. Edit the file to replace the sorry with a real "
              f"proof, then run `lake env lean {probe_name}` and iterate until it compiles "
              f"with zero errors and no sorry. The needed definitions are already in the file. "
              f"Do not add axioms or sorry.")
    dispatch(direct, runtime=runtime, repo=repo, timeout=timeout)
    res.rounds = 1
    ok, why = verify()
    res.reason = why
    if ok:
        res.closed = True
        return res

    # 3) decomposition fallback (the conjecture-DAG move): ask for helper lemmas, reassemble
    if decompose:
        decomp = (f"The theorem `{target}` : {goal} in {probe_name} is hard and still has a "
                  f"sorry. DECOMPOSE it: state and prove auxiliary helper lemmas (lemma/have) "
                  f"that build toward it, then assemble `{target}` from them. Run "
                  f"`lake env lean {probe_name}` and iterate until ZERO errors and NO sorry "
                  f"anywhere. Do not add axioms.")
        dispatch(decomp, runtime=runtime, repo=repo, timeout=timeout)
        res.rounds = 2
        res.decomposed = True
        ok, why = verify()
        res.reason = why
        res.closed = ok
    return res


def solve_robust(
    goal: str,
    *,
    defs: str,
    project_dir: str | Path,
    repo: str | Path,
    lake_bin: str,
    providers: tuple[str, ...] = ("codex",),
    attempts_per_provider: int = 1,
    target: str = "leaf",
    timeout: int = 600,
    decompose: bool = True,
    dispatch: Callable = default_dispatch,
    verify: Optional[Callable] = None,
    substrate_calibrate: Optional[Callable] = None,
) -> LeafResult:
    """Best-of-N agentic solve across providers × attempts. The agentic leaf is STOCHASTIC
    (codex closed P1 d0 in ~1 of 3 runs); retrying and crossing providers (codex/claude/
    deepseek — different reasoning) raises the closure RATE and adds cross-family coverage,
    which is the cheapest scientific-progress lever on the tractable bucket. Returns the FIRST
    kernel-clean closure; if none closes, the most-informative admissible attempt (so the
    residual is still localized). Each attempt is independently calibrated + kernel-arbitrated;
    a closure from ANY attempt is a real closure (the kernel does not care which model found it)."""
    attempts: list[LeafResult] = []
    for provider in providers:
        for i in range(attempts_per_provider):
            r = solve_leaf(goal, defs=defs, project_dir=project_dir, repo=repo, lake_bin=lake_bin,
                           probe_name=f"RobustProbe_{provider}_{i}.lean", target=target,
                           runtime=provider, timeout=timeout, decompose=decompose,
                           dispatch=dispatch, verify=verify, substrate_calibrate=substrate_calibrate)
            attempts.append(r)
            if r.closed:
                r.calibration["best_of"] = {"attempts_tried": len(attempts), "winner": provider}
                return r
    # none closed: prefer an admissible attempt (real negative) over an inadmissible one
    admissible = [a for a in attempts if not a.inadmissible]
    best = (admissible[-1] if admissible else (attempts[-1] if attempts else
            LeafResult(closed=False, target=target, goal=goal, reason="no_attempts")))
    best.calibration["best_of"] = {"attempts_tried": len(attempts),
                                   "all_inadmissible": not admissible}
    return best


# ── offline self-test (the loop's logic, no live provider/lake) ──────────────
def _self_test() -> int:
    fails = []
    # parse_verify_output: kernel-clean
    ok, _ = parse_verify_output("'leaf' depends on axioms: [propext, Classical.choice, Quot.sound]")
    if not ok: fails.append("clean-allowlist should pass")
    # sorryAx must fail
    ok, _ = parse_verify_output("'leaf' depends on axioms: [propext, sorryAx, Classical.choice]")
    if ok: fails.append("sorryAx must fail")
    # bad axiom must fail
    ok, why = parse_verify_output("'leaf' depends on axioms: [propext, myCustomAxiom]")
    if ok or "BAD_AXIOMS" not in why: fails.append("smuggled axiom must fail")
    # no-axiom proof passes
    ok, _ = parse_verify_output("'leaf' does not depend on any axioms")
    if not ok: fails.append("no-axiom proof should pass")
    # compile error fails
    ok, _ = parse_verify_output("Probe.lean:5:2: error: unknown identifier")
    if ok: fails.append("compile error must fail")
    # dead provider ⇒ inadmissible, not closed=False
    r = solve_leaf("True", defs="", project_dir=".", repo=".", lake_bin="lake",
                   dispatch=lambda *a, **k: "", verify=lambda: (True, "x"))
    if not r.inadmissible or r.closed:
        fails.append("dead provider must be INADMISSIBLE, not a real negative")
    # live provider + verify True ⇒ closed
    r = solve_leaf("True", defs="", project_dir=".", repo=".", lake_bin="lake",
                   dispatch=lambda p, **k: "ALIVE", verify=lambda: (True, "clean"))
    if not r.closed:
        fails.append("live provider + passing verify must close")
    # solve_robust: first live+passing attempt closes
    r = solve_robust("True", defs="", project_dir=".", repo=".", lake_bin="lake",
                     providers=("codex", "claude"), dispatch=lambda p, **k: "ALIVE",
                     verify=lambda: (True, "clean"))
    if not r.closed or r.calibration.get("best_of", {}).get("attempts_tried") != 1:
        fails.append("solve_robust must return first closing attempt")
    # solve_robust: all providers dead ⇒ inadmissible best (never a fake negative)
    r = solve_robust("True", defs="", project_dir=".", repo=".", lake_bin="lake",
                     providers=("codex", "claude"), dispatch=lambda *a, **k: "",
                     verify=lambda: (True, "x"))
    if r.closed or not r.calibration.get("best_of", {}).get("all_inadmissible"):
        fails.append("solve_robust all-dead must be inadmissible, not a fake negative")
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
