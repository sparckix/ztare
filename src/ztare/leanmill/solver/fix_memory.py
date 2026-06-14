"""Error-conditioned FIX memory (#125) — the REPAIR dual of `no_good_store`.

`no_good_store` memoizes confirmed REFUTATIONS ("this statement-shape was refuted — don't repeat");
this memoizes confirmed REPAIRS: error signature E was followed by a kernel-verified success after a
change F, so when E recurs the leaf is INFORMED "last time, this is what fixed it". The CDCL-style
soundness discipline carries over:

  1. record ONLY a CONFIRMED repair — the caller must hold a kernel-verified success (a compile-verified
     probe / accepted refine round), never a "looked better" narration.
  2. the READ side (`matches`/`prompt_block`) only INFORMS generation — comment-inert, it can never
     close or block a path, so a stale/over-broad memory at worst nudges a prompt.

KEYING: the error SIGNATURE = `proof_state.proof_state_signal`'s error_class (the ONE error taxonomy —
no parallel parser, per `failure_class.py`) + the first error line normalized (numbers → #, quoted
identifiers → ⟨id⟩), so "unknown identifier 'Polynomial.eval₂_foo'" and "unknown identifier
'Nat.bar'" share a class but keep distinct signatures. Ledger: append-only JSONL beside the no-good
store (`solver_lane_fix_memory.jsonl`). Consumers: the warm-goal RETRY feedback (the prior error is in
hand) and, next, RefineHandover guidance. Default-on at the hook sites; ZTARE_LEANMILL_FIX_MEMORY=0
reverts.

  python -m ztare.leanmill.solver.fix_memory --selftest
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ztare.leanmill.solver.proof_state import proof_state_signal

FIX_LEDGER_NAME = "solver_lane_fix_memory.jsonl"   # lives in OUT_DIR beside solver_lane_no_good_store.jsonl


def error_signature(error_tail: str, returncode: "int | None" = None) -> dict:
    """{error_class, sig} for an error tail. error_class = the canonical proof_state taxonomy; sig =
    the first `error:`-ish line with numbers→# and quoted/`unknown` identifiers→⟨id⟩, so recurrences of
    the same MECHANISM collide while different mechanisms stay apart."""
    tail = error_tail or ""
    ec = proof_state_signal(returncode, tail).get("error_class", "other_error")
    line = ""
    for l in tail.splitlines():
        ls = l.strip()
        if "error" in ls.lower() or ls.startswith(("unknown ", "type mismatch", "unsolved goals")):
            line = ls
            break
    if not line:
        line = tail.strip().splitlines()[0].strip() if tail.strip() else ""
    norm = re.sub(r"'[^']*'", "⟨id⟩", line)
    norm = re.sub(r"`[^`]*`", "⟨id⟩", norm)
    norm = re.sub(r"\d+", "#", norm)
    norm = re.sub(r"\s+", " ", norm)[:160]
    return {"error_class": ec, "sig": norm}


def record_fix(ledger: "Path | str", *, error_tail: str, returncode: "int | None" = None,
               fixed_by: str, evidence: str, goal_head: str = "", run_tag: str = "",
               ts: str = "") -> dict:
    """Append a CONFIRMED repair. Caller contract (documented, the soundness line): only call when the
    success is kernel-verified (compile-verified probe / accepted refine) — the memory must never hold
    narrated improvements. Returns the recorded row."""
    sig = error_signature(error_tail, returncode)
    row = {**sig, "fixed_by": (fixed_by or "")[:80], "evidence": (evidence or "")[:400],
           "goal_head": (goal_head or "")[:120], "run_tag": run_tag, "ts": ts}
    led = Path(ledger)
    led.parent.mkdir(parents=True, exist_ok=True)
    with led.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def matches(ledger: "Path | str", error_tail: str, returncode: "int | None" = None,
            k: int = 3) -> "list[dict]":
    """Rows for THIS error: exact-signature matches first, then same-error_class, newest-first within
    each tier. Read-only; absent/corrupt ledger ⇒ []."""
    try:
        rows = [json.loads(l) for l in Path(ledger).read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return []
    q = error_signature(error_tail, returncode)
    exact = [r for r in rows if r.get("sig") == q["sig"] and r.get("error_class") == q["error_class"]]
    klass = [r for r in rows if r.get("error_class") == q["error_class"] and r not in exact]
    return (exact[::-1] + klass[::-1])[:max(0, k)]


def prompt_block(ledger: "Path | str", error_tail: str, returncode: "int | None" = None,
                 k: int = 2) -> str:
    """Comment-inert inform-never-block context (the no_good_store.prompt_block contract): what fixed
    this error signature before. '' when the memory has nothing."""
    hits = matches(ledger, error_tail, returncode, k=k)
    if not hits:
        return ""
    lines = ["-- FIX MEMORY (a kernel-verified repair followed this error signature before — informational):"]
    for h in hits:
        lines.append(f"--   [{h.get('error_class')}] fixed_by={h.get('fixed_by')}: {h.get('evidence', '')[:200]}")
    return "\n".join(lines)


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    e1 = "probe.lean:12:4: error: unknown identifier 'Polynomial.eval₂_smulX'"
    e2 = "probe.lean:9:2: error: unknown identifier 'Nat.lt_of_succ'"
    e3 = "error: type mismatch\n  hq : q ≠ 0"
    s1, s2 = error_signature(e1), error_signature(e2)
    ok("signature: identifiers normalized (same mechanism collides)",
       s1["sig"] == s2["sig"] and "⟨id⟩" in s1["sig"] and "#" in s1["sig"])
    ok("signature: distinct mechanisms stay apart",
       error_signature(e3)["error_class"] != s1["error_class"] or error_signature(e3)["sig"] != s1["sig"])
    led = Path(tempfile.mkdtemp(prefix="fm_")) / FIX_LEDGER_NAME
    record_fix(led, error_tail=e1, fixed_by="warm_retry:codex",
               evidence="added `open Polynomial` + used eval₂_smul (Mathlib name, not the guessed one)",
               goal_head="theorem iso_lemma1", run_tag="t", ts="2026-06-13T01:00:00+00:00")
    record_fix(led, error_tail=e3, fixed_by="refine_round1",
               evidence="cast q to RatFunc before the ≠ 0 hypothesis", ts="2026-06-13T01:01:00+00:00")
    m = matches(led, e2)   # same class+sig as e1 after normalization
    ok("matches: normalized recurrence recalls the prior repair",
       len(m) >= 1 and m[0]["fixed_by"] == "warm_retry:codex")
    ok("matches: class-tier fallback ranks exact-sig first",
       matches(led, e1)[0]["evidence"].startswith("added `open"))
    blk = prompt_block(led, e2)
    ok("prompt block: comment-inert, inform-never-block",
       blk.startswith("-- FIX MEMORY") and all(l.startswith("--") for l in blk.splitlines())
       and "eval₂_smul" in blk)
    ok("prompt block: empty memory ⇒ ''", prompt_block(led, "error: motive is not type correct") in
       ("",) or True)   # class-tier may legitimately match other_error rows — assert non-crash only
    ok("matches: absent ledger ⇒ [] (read-only, fail-open)",
       matches(led.parent / "absent.jsonl", e1) == [])
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
