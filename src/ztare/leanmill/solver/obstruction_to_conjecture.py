"""Obstruction-to-Conjecture — the REFUTATION→CONSTRUCTION dual (a novel solver primitive).

THE STRUCTURAL OBSERVATION (the "exogenous" (orthogonal-compute) read, 2026-06-05). When the leaf cannot prove a hard goal G
it sometimes CHEATS: it WEAKENS exactly the definition / hypothesis / signature that is the obstruction,
then closes the now-trivial goal. `statement_integrity` catches this and records WHICH decl was altered
and HOW (the `definition_altered` / `target_signature_altered` witness). The external ATP literature
(CEGIS, CDCL, prover counterexample handling) treats a refutation as PRUNING — "don't do this again."
The dual no one systematizes: the cheat is a CORRUPTED ORACLE for the bottleneck. The agent, under
duress, points at the precise mathematical obstruction — the exact predicate/field/hypothesis it had to
remove to make G fall. The diff (original decl − altered decl) LOCALIZES that obstruction Δ. So the
sound move the cheat was a shadow of is recoverable for free: "introduce, as a lemma, the bridge that Δ
would have provided, and prove the ORIGINAL G from it." The refutation hands you the missing lemma's
TARGET for free.

WHY THIS IS SOUND (survives the master discriminator: teeth iff the signal is EXOGENOUS, not narrated by
the agent). The obstruction Δ is extracted by a DETERMINISTIC decl diff over `statement_integrity`'s
exogenous verdict — the leaf does not get to choose or narrate it. The seed only makes MOVE_CONJECTURE's
prompt TARGETED; the conjectured lemma still goes through the unchanged kernel + L⇒G sorry-discipline +
load-bearing probe + governance, so a bad seed yields a no_advance, never a false closure.

WHERE IT SITS (canonical home, cited — not a parallel). This is the reusable extraction core; it feeds
two existing surfaces: (1) `residual_to_lever` (the audited-outcome→next_lever bridge) — this turns its
generic "restate the honest target" lever for the def-alteration class into a TARGETED
`next_target_statement`; (2) `conjecture.conjecture_generate` — the seed becomes a focused prompt instead
of the blind "invent one useful lemma." It consumes the `no_good_store` refutation witnesses (the def-
alteration no-goods) and `statement_integrity`'s decl parser. No new detector, no parallel governance.

SCOPE THIS MODULE (no-regret, A/B-independent, calibration-first): the DETERMINISTIC extraction +
targeted-prompt synthesis, with positive (the real P1 cheat class) + negative (a sound probe ⇒ no seed)
+ honest-miss (a non-alteration failure ⇒ no seed) controls through one code path. It is NECESSARY-NOT-
SUFFICIENT: it proves a targeted seed is recoverable from the cheat; whether the targeted seed LIFTS
closure over a blind conjecture is the leaf-validated A/B (deferred until the in-flight PutnamBench A/B
frees the box + a cold-adversary pass on the idea itself — a self-generated primitive must survive a
cold cross-provider skeptic before it is trusted as more than a hypothesis)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field

from ztare.leanmill.solver.statement_integrity import (
    check as _integrity_check, decl_blocks as _decl_blocks, _signature, _norm,
)
from ztare.leanmill.lean_source import signature_before_proof

_TOKEN = re.compile(r"[A-Za-z_][\w'.]*|[^\sA-Za-z_]")


def _tokens(s: str) -> list[str]:
    return _TOKEN.findall(_norm(s))


def _token_delta(original: str, altered: str) -> "dict":
    """Structural, order-insensitive token delta between two decl texts (comments/whitespace already
    normalized by `_norm`). `removed` = tokens in original but not altered (what the cheat dropped — the
    obstruction's raw material); `added` = tokens the cheat introduced. Multiset-aware so a duplicated
    token is not spuriously cancelled."""
    from collections import Counter
    o, a = Counter(_tokens(original)), Counter(_tokens(altered))
    removed = list((o - a).elements())
    added = list((a - o).elements())
    return {"removed": removed, "added": added}


@dataclass
class Obstruction:
    decl: str                       # the decl the cheat altered (the localized obstruction)
    kind: str                       # definition_weakened | signature_weakened | decl_deleted
    original_block: str
    altered_block: str              # "" for a deleted decl
    delta: dict = field(default_factory=dict)   # {removed:[...], added:[...]}

    def summary(self) -> str:
        if self.kind == "decl_deleted":
            return f"`{self.decl}` was DELETED (the goal depends on it)."
        rm = ", ".join(self.delta.get("removed", [])[:8]) or "—"
        ad = ", ".join(self.delta.get("added", [])[:8]) or "—"
        what = "signature" if self.kind == "signature_weakened" else "definition"
        return (f"`{self.decl}`'s {what} was altered — tokens REMOVED: [{rm}]; ADDED: [{ad}]. "
                f"The removed material is the likely obstruction.")


@dataclass
class ConjectureSeed:
    obstruction: Obstruction
    targeted_prompt: str            # the focused MOVE_CONJECTURE prompt (leaf consumes this)
    next_target_statement: str      # the residual_to_lever obligation (NL, proposed — not a proof)


def extract_obstructions(original_source: str, probe_source: str, target_name: str) -> "list[Obstruction]":
    """Deterministic: from a rejected probe that ALTERED a depended-on decl, localize each obstruction.
    Returns [] when the probe is integrity-clean (a sound probe / an honest compile-miss ⇒ no seed) —
    so this fires ONLY on the cheat class and is silent on honest failure (fail-quiet, never invents)."""
    verdict = _integrity_check(original_source, probe_source, target_name)
    if verdict.ok:
        return []
    orig = dict(_decl_blocks(original_source))
    probe = dict(_decl_blocks(probe_source))
    out: list[Obstruction] = []
    for v in verdict.violations:
        head, _, _detail = v.partition(":")
        m = re.search(r"`([^`]+)`", v)
        name = m.group(1) if m else ""
        if not name or name not in orig:
            continue
        ob = orig[name]
        if head.strip() == "deleted":
            out.append(Obstruction(name, "decl_deleted", ob, "", {"removed": _tokens(ob), "added": []}))
        elif head.strip() == "target_signature_altered" and name in probe:
            d = _token_delta(_signature(ob), _signature(probe[name]))
            out.append(Obstruction(name, "signature_weakened", ob, probe[name], d))
        elif head.strip() == "definition_altered" and name in probe:
            d = _token_delta(ob, probe[name])
            out.append(Obstruction(name, "definition_weakened", ob, probe[name], d))
    return out


def _goal_of(original_source: str, target_name: str) -> "tuple[str, str]":
    """(goal_statement, goal_head) for the target decl — both arms prove EXACTLY this."""
    blocks = dict(_decl_blocks(original_source))
    tgt = next((blocks[n] for n in blocks if n == target_name or n.endswith("." + target_name)), "")
    head = signature_before_proof(tgt).strip() if tgt else target_name
    return (tgt or target_name), head


def _build_prompt(goal_head: str, source: str, goal: str, obstruction_block: str = "") -> str:
    """Assemble a conjecture prompt by CONCATENATION (never .format — `source`/`goal` embed raw Lean
    that may contain braces). `{lname}` stays a literal token for `conjecture_generate` to substitute.
    The `obstruction_block` is the ONLY thing that differs between the blind and targeted arms — the
    context (full source + goal + the fenced contract) is held IDENTICAL, so the A/B isolates the value
    of the exogenous obstruction localization, NOT extra context."""
    return (
        "You are a Lean 4 prover reasoning BACKWARD. The goal below is hard to prove directly. INVENT "
        "exactly ONE genuinely-useful intermediate lemma L and prove the ORIGINAL goal USING it. "
        "Self-contained against `import Mathlib`; alter NO definition the goal depends on. Output "
        "EXACTLY:\nLEMMA:\n```lean\ntheorem {lname} : <your lemma statement> := by sorry\n```\n"
        "PROOF:\n```lean\n" + goal_head + " := by\n  <tactics that REFERENCE {lname}>\n```\n"
        "Rules: the lemma must NOT be trivially true; the PROOF must cite `{lname}` and contain NO "
        "sorry.\n" + (obstruction_block or "") +
        "ORIGINAL SOURCE (every declaration here is FIXED — preserve all of them):\n" + source.strip() +
        "\nGOAL (prove EXACTLY as given):\n" + goal.strip() + "\n"
    )


# Length/directiveness-matched NEUTRAL filler for the blind arm (no localization content) — so a measured
# lift reflects the OBSTRUCTION callout, not merely that the targeted prompt is longer/more directive
# (adversarial-review parity caveat 2026-06-05). Deliberately carries NO hint about which decl is hard.
_NEUTRAL_PAD = (
    "Take your time and reason step by step before writing the lemma. Aim for the SIMPLEST intermediate "
    "lemma that genuinely makes the goal follow, and prefer a standard, reusable statement.\n"
)


def matched_blind_prompt(original_source: str, target_name: str) -> str:
    """The CONTROL prompt for the A/B: IDENTICAL context (full source + goal) to the targeted prompt,
    plus a length-matched NEUTRAL pad (no obstruction localization). The fair baseline for the lift test."""
    goal, head = _goal_of(original_source, target_name)
    return _build_prompt(head, original_source, goal, obstruction_block=_NEUTRAL_PAD)


def _targeted_prompt(target_name: str, ob: Obstruction, original_source: str) -> str:
    goal, head = _goal_of(original_source, target_name)
    callout = (
        "A PRIOR attempt CHEATED on this goal: " + ob.summary() + " That weakening is NOT allowed — the "
        "declaration is FIXED — but it LOCALIZES the obstruction: the property the prover tried to "
        "assume away is exactly the bridge you must establish honestly from the ORIGINAL (un-weakened) "
        "`" + ob.decl + "`. Do NOT re-weaken any definition.\n"
    )
    return _build_prompt(head, original_source, goal, obstruction_block=callout)


def _next_target_statement(target_name: str, ob: Obstruction) -> str:
    rm = ", ".join(ob.delta.get("removed", [])[:6])
    if ob.kind == "decl_deleted":
        return (f"Bridge lemma: re-establish, honestly, the content of the deleted `{ob.decl}` that "
                f"`{target_name}` depends on (do not delete it).")
    return (f"Bridge lemma supplying the obstruction the prior cheat removed from `{ob.decl}` "
            f"(removed: [{rm}]), so `{target_name}` is provable without weakening `{ob.decl}`.")


def seeds_from_refutation(original_source: str, probe_source: str, target_name: str) -> "list[ConjectureSeed]":
    """One-call entry: rejected def-altering probe → targeted conjecture seeds. [] on a clean probe."""
    return [ConjectureSeed(ob, _targeted_prompt(target_name, ob, original_source),
                           _next_target_statement(target_name, ob))
            for ob in extract_obstructions(original_source, probe_source, target_name)]


def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # ---- POSITIVE control: the real P1 cheat CLASS (weaken a depended-on def to trivialize the goal) ----
    original = ("import Mathlib\n\ndef algebraicPoint (f : ℕ → ℝ) : Prop := ∀ n, f n = 0\n\n"
                "theorem tgt (f : ℕ → ℝ) : algebraicPoint f → f 3 = 0 := by sorry\n")
    cheat = ("import Mathlib\n\ndef algebraicPoint (f : ℕ → ℝ) : Prop := True\n\n"
             "theorem tgt (f : ℕ → ℝ) : algebraicPoint f → f 3 = 0 := by sorry\n")
    seeds = seeds_from_refutation(original, cheat, "tgt")
    ok("positive: a seed is extracted from the cheat", len(seeds) >= 1)
    ok("positive: obstruction localizes the altered decl",
       any(s.obstruction.decl == "algebraicPoint" for s in seeds))
    ok("positive: kind is definition_weakened",
       any(s.obstruction.kind == "definition_weakened" for s in seeds))
    ok("positive: delta surfaces the removed obstruction material",
       any("f" in s.obstruction.delta.get("removed", []) or "0" in s.obstruction.delta.get("removed", [])
           for s in seeds))
    ok("positive: targeted prompt names the decl + forbids re-weakening",
       any("algebraicPoint" in s.targeted_prompt and "NOT re-weaken" in s.targeted_prompt for s in seeds))
    ok("positive: next_target_statement is a proposed bridge (not a proof)",
       any("Bridge lemma" in s.next_target_statement for s in seeds))

    # ---- CONTEXT-PARITY (the A/B fairness guarantee, tested): blind & targeted share source+goal,
    #      differ ONLY in the obstruction callout (else targeted would win on context, not localization) ----
    blind = matched_blind_prompt(original, "tgt")
    ok("parity: matched-blind shares the source (sees the def) but has NO obstruction callout",
       "algebraicPoint" in blind and "CHEATED" not in blind and "LOCALIZES" not in blind)
    ok("parity: targeted carries the obstruction callout the blind lacks",
       "CHEATED" in seeds[0].targeted_prompt and "LOCALIZES" in seeds[0].targeted_prompt)
    ok("parity: both arms carry the SAME goal statement",
       "f 3 = 0" in blind and "f 3 = 0" in seeds[0].targeted_prompt)

    # ---- NEGATIVE control: a SOUND add-only probe ⇒ NO seed (never invents a lead from an honest proof) ----
    sound = ("import Mathlib\n\ndef algebraicPoint (f : ℕ → ℝ) : Prop := ∀ n, f n = 0\n\n"
             "theorem bridge (f : ℕ → ℝ) (h : algebraicPoint f) : f 3 = 0 := h 3\n\n"
             "theorem tgt (f : ℕ → ℝ) : algebraicPoint f → f 3 = 0 := fun h => bridge f h\n")
    ok("negative: sound add-only probe yields NO seed",
       seeds_from_refutation(original, sound, "tgt") == [])

    # ---- HONEST-MISS control: a probe that just leaves the sorry (no alteration) ⇒ NO seed ----
    miss = original  # unchanged: still `:= by sorry`, no decl altered
    ok("honest-miss: unaltered probe yields NO seed (fires only on the cheat class)",
       seeds_from_refutation(original, miss, "tgt") == [])

    # ---- DELETED-decl class ----
    deleted = ("import Mathlib\n\n"
               "theorem tgt (f : ℕ → ℝ) : algebraicPoint f → f 3 = 0 := by sorry\n")  # def removed
    dseeds = seeds_from_refutation(original, deleted, "tgt")
    ok("deleted: a deletion is localized as an obstruction",
       any(s.obstruction.kind == "decl_deleted" and s.obstruction.decl == "algebraicPoint"
           for s in dseeds))

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
