"""Governed proof repair / Mathlib version-migration (#17).

A proof that compiled under Mathlib vX often breaks under vY (renamed lemmas, changed signatures,
tightened elaboration). The BohrMean v4.29→v4.30 breakage is a live instance. Repairing it is the
SAME shape as the ad-hoc entry: the theorem STATEMENT is fixed and known-true; only the proof BODY
needs to be re-derived against the current toolchain. So repair reuses the full governed pipeline
(`solve_adhoc`) rather than a new loop — the only repair-specific layers are:

  1. CONFIRM-THE-BREAK-FIRST (calibrate, fail-closed): a "repair" is only admissible if the proof
     ACTUALLY fails to compile under the current toolchain. If it still compiles, there is nothing
     to repair (return repaired=False, already_compiles=True) — never fabricate a repair.
  2. WARM-START HINT: the broken body is preserved as a comment above the `sorry`, so the agent can
     migrate it (rename a lemma, adjust a binder) instead of re-deriving from scratch.
  3. MIGRATION DIFF: on a clean closure, emit (old_body → new_body) so the change is auditable.

Non-iatrogenic: a NEW entry; existing solve paths are unchanged. The repaired proof is still
independently kernel-gated + leakage-gated (via solve_adhoc), so a repair can never be a false
closure. Substrate-generic: works for any toolchain pair, not just BohrMean.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class _Decl:
    name: str
    signature: str   # `theorem NAME <binders> : <type>` (up to but excluding `:=`)
    body: str        # everything after `:=` for the target decl (the proof to repair)
    start: int
    end: int


def _find_decl(source: str, target: str) -> "_Decl | None":
    """Locate `theorem/lemma target … := <body>` and split signature from body at the `:=` that
    follows the declaration head (depth-0, not a binder/term `:=`). The body runs to the next
    top-level decl/terminator or EOF."""
    m = re.search(rf"(?m)^(?:private\s+|protected\s+|noncomputable\s+|scoped\s+)*"
                  rf"(?:theorem|lemma)\s+{re.escape(target)}\b", source)
    if not m:
        return None
    head = m.start()
    # find the `:=` at bracket-depth 0 after the head
    depth = 0
    i = m.end()
    assign = -1
    # include Lean's strict-implicit binder brackets ⦃ ⦄ (cold-review 2026-06-03) so a `:=` inside
    # them is not mistaken for the proof assignment. Known limitation: a top-level `let x := …` IN
    # THE TYPE (rare in theorem statements) has a depth-0 `:=` and would still mis-split — callers
    # repairing such a statement should pass an explicit goal.
    pairs = {"(": ")", "[": "]", "{": "}", "⟨": "⟩", "⦃": "⦄"}
    closes = set(pairs.values())
    while i < len(source) - 1:
        c = source[i]
        if c in pairs:
            depth += 1
        elif c in closes:
            depth = max(0, depth - 1)
        elif depth == 0 and source[i:i + 2] == ":=":
            assign = i
            break
        i += 1
    if assign < 0:
        return None
    # body end = next top-level decl-start / terminator after the body begins, or EOF
    rest = source[assign + 2:]
    nxt = re.search(r"(?m)^(?:private\s+|protected\s+|noncomputable\s+|scoped\s+)*"
                    r"(?:theorem|lemma|def|abbrev|instance|namespace|end|section|#)\b", rest)
    body_end = assign + 2 + (nxt.start() if nxt else len(rest))
    return _Decl(name=target, signature=source[head:assign].rstrip(),
                 body=source[assign + 2:body_end].strip(), start=head, end=body_end)


def make_sorried_with_hint(source: str, target: str) -> "tuple[str, str]":
    """Return (sorried_source, old_body): the source with `target`'s broken body replaced by
    `:= by sorry`, the old body preserved as a `-- [repair] previous body:` comment above the decl
    (the warm-start hint). Raises if the target decl is not found."""
    d = _find_decl(source, target)
    if d is None:
        raise ValueError(f"target decl not found: {target}")
    hint = "-- [repair] previous (broken-under-current-toolchain) body — migrate, don't re-derive:\n"
    hint += "".join(f"--   {ln}\n" for ln in d.body.splitlines()[:40])
    new_decl = f"{hint}{d.signature} := by\n  sorry"
    sorried = source[:d.start] + new_decl + source[d.end:]
    return sorried, d.body


def repair(source_text: str, target: str, *, project_dir: str, lake_bin: str,
           solve_adhoc, compile_fn, provider=None, timeout_s: int = 500,
           substrate=None, force: bool = False) -> dict:
    """Repair `target`'s proof through the governed pipeline.

    `solve_adhoc` and `compile_fn(source_text)->(*ok*, tail)` are injected (so this module stays
    import-light and unit-testable). Steps: confirm-the-break (unless `force`), strip+hint, route
    through solve_adhoc, emit the migration diff. Returns a structured repair record."""
    # 1) confirm the break (calibrate, fail-closed): a repair is only admissible if it FAILS now.
    if not force:
        ok, tail = compile_fn(source_text)
        if ok:
            return {"target": target, "repaired": False, "already_compiles": True,
                    "note": "proof still compiles under the current toolchain — nothing to repair.",
                    "compile_tail": (tail or "")[-300:]}
    # 2) strip the broken body to sorry, keep it as a warm-start hint.
    sorried, old_body = make_sorried_with_hint(source_text, target)
    # 3) re-prove through the FULL governed pipeline (kernel + leakage gated).
    res = solve_adhoc(target, sorried, "", provider=provider, timeout_s=timeout_s,
                      substrate=substrate)
    r0 = (res.get("results") or [{}])[0]
    repaired = r0.get("outcome") == "closed"
    new_body = (r0.get("proof_text") or "").strip()
    return {"target": target, "repaired": repaired,
            "already_compiles": False,
            "old_body": old_body, "new_body": new_body if repaired else "",
            "migration_diff": {"from": old_body, "to": new_body} if repaired else None,
            "in_repo_reference_check": r0.get("in_repo_reference_check"),
            "frontier_triage": r0.get("frontier_triage"),
            "adhoc_result": res}


def _self_test() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    src = (
        "import Mathlib\n"
        "open MeasureTheory\n\n"
        "theorem foo (n : ℕ) (h : 0 < n) : n + 0 = n := by\n"
        "  simpa using Nat.add_zero n  -- renamed/broken under new Mathlib\n\n"
        "theorem bar : True := trivial\n")

    d = _find_decl(src, "foo")
    ok("finds_target_decl", d is not None and d.name == "foo")
    ok("signature_has_binders_and_type",
       "(n : ℕ)" in d.signature and "(h : 0 < n)" in d.signature and ": n + 0 = n" in d.signature)
    ok("body_is_old_proof", "simpa using Nat.add_zero n" in d.body)
    ok("body_stops_at_next_decl", "theorem bar" not in d.body)

    sorried, old_body = make_sorried_with_hint(src, "foo")
    ok("sorried_has_sorry", "foo (n : ℕ) (h : 0 < n) : n + 0 = n := by" in sorried and "sorry" in sorried)
    ok("hint_preserved_as_comment", "[repair] previous" in sorried and "Nat.add_zero n" in sorried)
    ok("other_decls_untouched", "theorem bar : True := trivial" in sorried)
    ok("old_body_returned", "Nat.add_zero" in old_body)

    # REGRESSION (cold-review): a `:=` inside strict-implicit binders ⦃ ⦄ must NOT be mistaken for
    # the proof assignment.
    src2 = "theorem baz ⦃x : Nat⦄ (h : x = 0) : x + 0 = x := by\n  simp\n"
    d2 = _find_decl(src2, "baz")
    ok("strict_implicit_binder_not_mis_split",
       d2 is not None and "⦃x : Nat⦄" in d2.signature and ": x + 0 = x" in d2.signature
       and "simp" in d2.body and ":=" not in d2.signature.split("⦄")[-1])

    # confirm-the-break: if it already compiles, repair() does NOT fabricate a repair.
    calls = {"n": 0}

    def fake_solve_adhoc(*a, **k):
        calls["n"] += 1
        return {"results": [{"outcome": "closed", "proof_text": "by simp"}]}

    rep_noop = repair(src, "foo", project_dir="x", lake_bin="lake",
                      solve_adhoc=fake_solve_adhoc, compile_fn=lambda s: (True, "ok"))
    ok("already_compiles_skips_repair", rep_noop["repaired"] is False
       and rep_noop["already_compiles"] and calls["n"] == 0)

    # break confirmed (compile fails) → routes to solve_adhoc → repaired + migration diff.
    rep = repair(src, "foo", project_dir="x", lake_bin="lake",
                 solve_adhoc=fake_solve_adhoc, compile_fn=lambda s: (False, "error: unknown identifier"))
    ok("break_confirmed_routes_to_pipeline", calls["n"] == 1)
    ok("repaired_emits_migration_diff", rep["repaired"] and rep["new_body"] == "by simp"
       and "simpa using Nat.add_zero" in rep["migration_diff"]["from"]
       and rep["migration_diff"]["to"] == "by simp")

    # force=True bypasses the break-confirm (for known-broken inputs / batch migration).
    calls["n"] = 0
    repair(src, "foo", project_dir="x", lake_bin="lake", solve_adhoc=fake_solve_adhoc,
           compile_fn=lambda s: (True, "ok"), force=True)
    ok("force_bypasses_confirm", calls["n"] == 1)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
