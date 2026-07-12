#!/usr/bin/env python3
"""Blueprint LINTER — mechanizes the §4.2a authoring discipline (docs/concepts/leanmill_architecture.md):
"carry the PROBLEM and the VOCABULARY, never the DECOMPOSITION".

WHY a REPORTER (Gate/Reporter/Move law): every rule here flags a *maintainer authoring* smell whose failure
mode downstream is iatrogenic (a tautology bullet, a true-but-WEAK theorem, a decidable toy) — but a blueprint
is advisory input (Principle 7), so the linter warns and NEVER blocks. Nothing here touches soundness: a bad
blueprint at worst wastes a campaign; the kernel + firewall still gate every closure.

WHY deterministic-only (no LLM): the traps this catches are *structural* (a definition posed as a lemma, a
formalization choice typed into the NL target). The statement⊨ambition gap that needs judgment is §4.2b's
frontier, deliberately out of scope here.

Parsing is line-based markdown STRUCTURE (mirrors `autoformalize_notes.parse_notes`: a `##` line opens a
section, `-`/`*` lines under `## Lemmas` are bullets) — no regex on structure; small word-boundary regexes
only where matching prose verbs, where a substring test would false-positive on "proven"/"showed".

CLI: `python -m ztare.leanmill.blueprint_lint <file.md>` — prints `⚠ [rule] L<line>: msg`, exit 0 ALWAYS
(reporter, never a gate). `--strict` flips to exit 1 on warnings for CI use.
"""
from __future__ import annotations

import re
import sys

# Rule c — a `## Lemmas` bullet is a FORCED sub-target (`attack_fn(bullet)`), so a DEFINITION bullet can only
# formalize as `X ↔ X's own body` (Iff.rfl) — the tautology trap the firewall then (correctly) rejects.
_DEFINITION_STARTS = ("introduce", "define", "definition of", "the notion of")

# Rule e — NL `## Target` phrases that historically typed a FORMALIZATION CHOICE into the claim (the Topkis
# lesson: "linearly ordered" + "the unique maximizer" → a true-but-weak 1-D corollary, faithfully proven).
_AMBITION_CUES = ("the unique ", "a unique ", "exactly one", "linearly ordered", "a linear order",
                  "totally ordered", "strictly ordered choices")

# Rule f — a concrete tiny carrier as THE type of the claim collapses it to a decidable toy the non-triviality
# leg rejects. Case-sensitive (Lean identifiers); \b after the digit so `Fin 25` / `ZMod 2^n` don't match.
_TINY_INSTANCE = re.compile(r"\b(ZMod 2|ZMod 3|Fin 2|Fin 3)\b")

# Rule d — "define X and show/prove Y" in ONE bullet: the def belongs in `## Theory file`, the property in its
# own lemma. Word-boundary verbs (a substring test would fire on "proven"/"showed"/"well-defined").
_DEFINE_AND_SHOW = re.compile(r"\b(define|defines|introduce|introduces)\b.*?\b(and|then|,)\b.*?"
                              r"\b(show|shows|prove|proves)\b", re.IGNORECASE | re.DOTALL)

# Rule g — a TOP-LEVEL restatement cue in `## Target` ("Equivalently, …", "i.e.", "that is,", "in other words").
# A restatement of the CONCLUSION tends to be CONJOINED by the autoformalizer into a redundant `A ∧ B` where A⟹B
# (median-voter: "m is a Condorcet winner … Equivalently, no alternative beats the median" → `CondorcetWinner ∧
# ∀ y, ¬ Beats …`), which the deterministic conjunctive split must then carry. Advisory. Excludes a PARENTHETICAL
# "(equivalently, …)" clarifying a DEFINITION (paren depth > 0) and mid-sentence uses (only sentence-leading fires).
_RESTATE_CUES = ("equivalently", "in other words", "that is,", "i.e.")

# Rule h — a `## Lemmas` bullet that carries the PROOF STRATEGY / decomposition, not a claim (RCA 2026-07-04, CLOB:
# the capstone bullet "…at every reachable state: … by induction on the sequence, discharging each step with the
# per-operation lemmas" pre-wrote the whole decomposition — a FORCED split the apparatus never chose, and whose
# forced per-op lemmas were false as formalized). The authoring rule (arch §): a blueprint carries the PROBLEM +
# vocabulary, NOT the decomposition — be agnostic in NL. These cues are proof-METHOD verbs, unambiguous vs a claim.
_STRATEGY_CUES = ("by induction", "discharging each", "per-operation lemma", "per-op lemma", "the per operation",
                  "discharge each", "then compose", "by composing the", "using the lemmas above", "each step with")


def _sections(text: str) -> "list[tuple[str, int, list[tuple[int, str]]]]":
    """Split into (section_name_lower, heading_line_1based, [(line_1based, line_text), ...]) — the same
    structural convention as `parse_notes` (any `##`-prefixed line opens a new section; text before the
    first heading is the preamble, named "")."""
    out: "list[tuple[str, int, list[tuple[int, str]]]]" = [("", 0, [])]
    for i, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        if s.startswith("##"):
            out.append((s.lstrip("#").strip().lower(), i, []))
        else:
            out[-1][2].append((i, line))
    return out


def _bullets(body: "list[tuple[int, str]]") -> "list[tuple[int, str]]":
    """Join multi-line `-`/`*` bullets into (start_line, full_text) — a bullet's continuation lines are the
    non-bullet lines that follow it (mirrors how `parse_notes` treats the Lemmas block)."""
    items: "list[tuple[int, str]]" = []
    for ln, line in body:
        s = line.strip()
        if s.startswith(("-", "*")):
            items.append((ln, s.lstrip("-*").strip()))
        elif s and items:
            items[-1] = (items[-1][0], items[-1][1] + " " + s)
    return items


def _strip_name_marker(bullet: str) -> str:
    """Drop the leading `**(decl_name)**` campaign naming marker so the VERB check sees the prose start."""
    m = re.match(r"\*\*\(.*?\)\*\*\s*", bullet)
    return bullet[m.end():] if m else bullet


def _restatement_hits(body: "list[tuple[int, str]]") -> "list[tuple[int, str]]":
    """Sentence-leading restatement cues (Rule g) in the `## Target` prose that sit OUTSIDE parentheses. Paren
    depth is carried across lines (a `(equivalently, …)` clarifying a DEFINITION is depth > 0 ⇒ excluded); a cue
    fires only when it LEADS a sentence (line start, or right after `.`/`:`/`;`) so a mid-clause 'that is' doesn't
    false-match. Returns [(line, cue)]."""
    hits: "list[tuple[int, str]]" = []
    depth = 0
    for ln, line in body:
        low = line.lower()
        for cue in _RESTATE_CUES:
            k = 0
            while (j := low.find(cue, k)) != -1:
                d = depth + line[:j].count("(") - line[:j].count(")")
                pre = line[:j].rstrip()
                if d == 0 and (pre == "" or pre.endswith((".", ":", ";"))):
                    hits.append((ln, cue.strip().rstrip(",")))
                k = j + len(cue)
        depth += line.count("(") - line.count(")")
    return hits


def lint_blueprint(text: str) -> "list[dict]":
    """Deterministic §4.2a authoring checks. Returns [{"rule", "line", "msg"}] — advisory only; callers must
    never block on the result (this is a REPORTER)."""
    warnings: "list[dict]" = []
    secs = _sections(text)
    names = {name for name, _, _ in secs}

    if "domain" not in names:
        warnings.append({"rule": "missing_domain", "line": None,
                         "msg": "no `## Domain` section — the P0 time-to-closure segmentation stamp reads it; "
                                "unsegmented campaigns pollute the forecast priors"})
    if "target" not in names:
        warnings.append({"rule": "missing_target", "line": None,
                         "msg": "no `## Target` section — the blueprint must carry the PROBLEM (the NL theorem); "
                                "without it the campaign has nothing to prove"})

    for name, _hln, body in secs:
        if name == "lemmas":
            for ln, bullet in _bullets(body):
                prose = _strip_name_marker(bullet)
                low = prose.lower()
                if low.startswith(_DEFINITION_STARTS) or "as the definition" in low:
                    warnings.append({"rule": "definition_bullet_in_lemmas", "line": ln,
                                     "msg": "bullet reads as a DEFINITION, not a provable claim — a definition "
                                            "bullet forces `X ↔ X's own body` (tautology trap, firewall-rejected); "
                                            "move the def to `## Theory file`"})
                elif _DEFINE_AND_SHOW.search(prose):
                    warnings.append({"rule": "define_and_show_bullet", "line": ln,
                                     "msg": "bullet both defines AND shows/proves — split it (def → `## Theory "
                                            "file`, property → its own lemma); one bullet is one forced sub-target"})
                elif any(cue in low for cue in _STRATEGY_CUES):
                    warnings.append({"rule": "strategy_in_lemmas", "line": ln,
                                     "msg": "bullet encodes a PROOF STRATEGY / decomposition (\"by induction … "
                                            "discharging each step with the per-operation lemmas\"), not a claim — "
                                            "the blueprint must NOT carry the decomposition (be agnostic in NL). A "
                                            "forced split the apparatus never chose recurs as false-as-formalized "
                                            "sub-lemmas; drop it and let the planner decompose (arch §authoring rule)"})
        elif name == "target":
            for ln, line in body:
                low = line.lower()
                for cue in _AMBITION_CUES:
                    if cue in low:
                        warnings.append({"rule": "ambition_restriction_cue", "line": ln,
                                         "msg": f"target phrase {cue.strip()!r} historically encoded a "
                                                "formalization choice that narrows the claim (the Topkis "
                                                "true-but-weak trap) — state the content at full ambition and "
                                                "let the autoformalizer pick the structure"})
                        break                     # one cue warning per line is enough signal
                m = _TINY_INSTANCE.search(line)
                if m:
                    warnings.append({"rule": "fixed_tiny_instance", "line": ln,
                                     "msg": f"target fixes the tiny carrier `{m.group(1)}` — a fixed instance "
                                            "collapses to a decidable toy the non-triviality leg rejects; "
                                            "parameterize (e.g. `∀ n`) instead"})
            for ln, cue in _restatement_hits(body):
                warnings.append({"rule": "restatement_in_target", "line": ln,
                                 "msg": f"target restates the conclusion after {cue!r} — the autoformalizer tends "
                                        "to CONJOIN a top-level restatement into a redundant `A ∧ B` (A⟹B) that the "
                                        "deterministic split must then carry; state the claim ONCE (drop/fold the "
                                        "restatement). A parenthetical '(equivalently, …)' clarifying a def is fine"})
    return warnings


def main(argv: "list[str] | None" = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    strict = "--strict" in args
    paths = [a for a in args if a != "--strict"]
    if not paths:
        print("usage: python -m ztare.leanmill.blueprint_lint [--strict] <blueprint.md> [...]", file=sys.stderr)
        return 0                                  # reporter: even usage errors don't gate
    fired = 0
    for p in paths:
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError as e:
            print(f"⚠ [read_error] {p}: {e}", file=sys.stderr)
            continue
        for w in lint_blueprint(text):
            loc = f"L{w['line']}" if w["line"] is not None else "L?"
            prefix = f"{p}: " if len(paths) > 1 else ""
            print(f"⚠ [{w['rule']}] {prefix}{loc}: {w['msg']}")
            fired += 1
    return 1 if (strict and fired) else 0         # default exit 0 ALWAYS — reporter, never a gate


if __name__ == "__main__":
    sys.exit(main())
