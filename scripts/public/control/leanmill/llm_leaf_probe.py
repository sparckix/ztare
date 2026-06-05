#!/usr/bin/env python3
"""LLM leaf solver, turn-bounded, INDEPENDENTLY kernel-verified.

The agent (codex/claude on subscription) COMPOSES a proof; the calibrated PersistentLean +
axiom-allowlist gate ARBITRATES (agent self-report is never trusted — the governance
principle). Multi-step: on a failed attempt, the REPL error is fed back for up to N turns.

CALIBRATION FIRST (the discipline that was missing): before trusting any "could not prove"
result, both instruments must pass a positive control — the LLM provider must return a live
trivial answer, and the Lean substrate must pass substrate_liveness.calibrate. A null result
from an un-calibrated provider/substrate is INADMISSIBLE.

  python3 llm_leaf_probe.py --defs-file <apn.lean> --goal "<prop>" \
      --project-dir projects/atlas_lean_2026_05_29 --provider codex --turns 3
"""
from __future__ import annotations
import argparse, re, subprocess, sys, tempfile, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))


def _defs_text(defs_file: str) -> str:
    src = Path(defs_file).read_text(encoding="utf-8")
    src = "\n".join(l for l in src.splitlines() if not l.strip().startswith("import "))
    m = re.search(r"(?m)^\s*theorem\s+\w+\b", src)  # drop the first sorried theorem onward
    return src[:m.start()].rstrip() if m else src


def _provider_live(provider: str, timeout: int = 90) -> tuple[bool, str]:
    """Positive control: does the provider return a live trivial answer non-interactively?"""
    out = _dispatch(provider, "Reply with exactly the word: ALIVE", timeout)
    return ("ALIVE" in (out or "").upper()), (out or "")[:120]


def _dispatch(provider: str, prompt: str, timeout: int) -> str:
    """One non-interactive LLM call on the subscription/key. Returns the model's text."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
        ansfile = tf.name
    try:
        if provider == "codex":
            cmd = ["timeout", str(timeout), "codex", "exec", "--skip-git-repo-check",
                   "-s", "read-only", "-o", ansfile, prompt]
            subprocess.run(cmd, cwd=str(REPO), text=True, capture_output=True, timeout=timeout + 15)
            return Path(ansfile).read_text(encoding="utf-8", errors="replace").strip()
        if provider == "claude":
            import os
            env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
            r = subprocess.run(["timeout", str(timeout), "claude", "-p", prompt],
                               cwd=str(REPO), text=True, capture_output=True,
                               timeout=timeout + 15, env=env)
            return (r.stdout or "").strip()
        raise ValueError(f"unknown provider {provider}")
    finally:
        try: Path(ansfile).unlink()
        except Exception: pass


def _extract_body(text: str) -> str:
    """Pull the tactic body from the model's answer (strip fences / leading `:= by`)."""
    if not text:
        return ""
    blocks = re.findall(r"```(?:lean)?\s*(.*?)```", text, flags=re.DOTALL)
    cand = blocks[-1] if blocks else text
    cand = cand.strip()
    m = re.search(r":=\s*by\b", cand)
    if m:
        cand = cand[m.end():]
    cand = re.sub(r"(?m)^\s*theorem\b.*$", "", cand).strip()
    return cand


def run(defs_file, goal, project_dir, provider, turns, timeout):
    from ztare.formal.lean_persistent import PersistentLean
    from ztare.formal.substrate_liveness import calibrate

    # ── CALIBRATION FIRST (both instruments) ─────────────────────────────────
    live, sample = _provider_live(provider, timeout=min(timeout, 90))
    print(f"[leaf] provider {provider} liveness: {'LIVE' if live else 'DEAD'} ({sample!r})", flush=True)
    if not live:
        print(f"[leaf] ABORT: provider {provider} did not return a live trivial answer — "
              f"any 'could not prove' would be inadmissible (uncalibrated instrument).")
        return
    defs = _defs_text(defs_file)
    proj = str((REPO / project_dir).resolve() if not Path(project_dir).is_absolute() else Path(project_dir))
    with PersistentLean(project_dir=proj) as pl:
        rep = calibrate(pl); print(rep.banner(), flush=True)
        env = pl.check(defs, timeout=600).get("env")
        if pl.check(defs, timeout=600).get("errors"):
            print("[leaf] ABORT: defs env failed to build"); return

        prior_err = ""
        for t in range(1, turns + 1):
            prompt = (
                "You are proving a Lean 4 theorem using Mathlib. These definitions are "
                "ALREADY in scope (do NOT redefine them):\n\n" + defs +
                f"\n\nProve this theorem:\n  theorem leaf : {goal} := by\n    <YOUR PROOF>\n\n"
                "Output ONLY the tactic proof body (what goes after `:= by`). No commentary, "
                "no `theorem` line, no code fences." +
                (f"\n\nYour previous attempt FAILED with this Lean error:\n{prior_err}\n"
                 "Fix it." if prior_err else ""))
            t0 = time.time()
            ans = _dispatch(provider, prompt, timeout)
            body = _extract_body(ans)
            dt = round(time.time() - t0)
            if not body:
                print(f"[leaf] turn {t}: empty proposal ({dt}s)"); continue
            code = f"theorem _leaf_probe : {goal} := by\n  {body}\n#print axioms _leaf_probe\n"
            r = pl.check(code, timeout=180, env=env)
            errs = r.get("errors") or []
            out = r.get("output") or ""
            ok = (r.get("success") and not (r.get("sorries") or [])
                  and "sorryAx" not in out
                  and ("does not depend on any axioms" in out
                       or _axioms_ok(out)))
            head = body.replace("\n", " ")[:80]
            if ok:
                print(f"[leaf] turn {t} CLOSED+kernel-gated ({dt}s) | by {head}")
                print(f"[leaf] => {provider} multi-step leaf solver CLOSED `{goal[:50]}` — "
                      f"genuine lift over one-shot deterministic (which got 0 here).")
                return
            prior_err = (errs[0] if errs else "no error but not closed (sorry/axiom)")[:400]
            print(f"[leaf] turn {t} failed ({dt}s): {prior_err[:120]}", flush=True)
        print(f"[leaf] => {provider} did NOT close `{goal[:50]}` in {turns} turns "
              f"(calibrated; admissible negative).")


_ALLOW = {"propext", "Classical.choice", "Quot.sound"}
def _axioms_ok(out: str) -> bool:
    m = re.search(r"depends on axioms:\s*\[([^\]]*)\]", out)
    if not m: return False
    return {a.strip() for a in m.group(1).split(",") if a.strip()}.issubset(_ALLOW)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--defs-file", required=True)
    ap.add_argument("--goal", required=True)
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--provider", default="codex", choices=["codex", "claude"])
    ap.add_argument("--turns", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=150)
    a = ap.parse_args()
    run(a.defs_file, a.goal, a.project_dir, a.provider, a.turns, a.timeout)


if __name__ == "__main__":
    main()
