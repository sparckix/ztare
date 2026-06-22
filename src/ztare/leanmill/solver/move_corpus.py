"""THE single registry of every research/proof MOVE the LeanMill agent can elect — the source of truth that
both the SOLVER (leaf + planner) and the THEORY-BUILDER consume, so a move/card/technique can never again be
"forgotten" (the recurring frankenstein: a parallel surface bolted on because nobody remembered the menu).

Why this exists (operator 2026-06-20): the moves were scattered across FOUR catalogues with no unifying view —
  1. EXOGENOUS-TOOL cards   `move_cards._TOOL_SPECS`                 (witness / abduct / hammer / sos / …)
  2. STRUCTURAL moves        `governed_dag_search.MOVE_*` + the planner `_PLAN_ACTIONS`
                             (decompose / specialize / generalize / falsify / reflection / corroborate / …)
  3. TRANSPORT techniques    `isomorphism_decompose.TRANSPORTABLE_TECHNIQUES`
                             (orthogonality·polynomial-method / Hankel-rank / obstruction-descent / …)
  4. MATH research moves     `research_director.universal_research_ops.VOCABULARY_V5`
                             (the two-cultures reconciled catalogue: Decomposition&Recomposition / Transfer / …)
This module REUSES all four (no new catalogue, no duplicated content) and presents ONE uniform `MoveEntry`
list. It is the corpus the semantic `move_atlas` embeds and the renderer surfaces. Adding a move anywhere in the
four homes flows through here automatically; the architecture doc (`docs/concepts/leanmill_architecture.md`
§ "Move corpus & consumer surfaces") names every home + every consumer so the next agent reads ONE place.

Discipline (Goldilocks): this registry decides NOTHING about soundness. It orders/surfaces the menu; the
governed scheduler applies liveness/cost gates and the kernel ratifies every closure. A move present here that
turns out wrong fails HONESTLY through the same gates — the corpus can only change WHICH move is tried first.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MoveEntry:
    """One electable move, uniform across the four source catalogues. `move_id` is the dedupe/identity key
    (also the `move_calibration` receipt key when the move is calibrated)."""
    move_id: str            # canonical id / calibration key (e.g. "witness_transport", "conjecture_lemma")
    name: str               # display label
    kind: str               # "tool" | "structural" | "technique" | "research_op"
    when: str               # the PATTERN — when this move earns its place (clean_proceed_condition)
    avoid: str = ""         # the ANTI-PATTERN — the nearest confuser / when NOT to use it
    mechanism: str = ""     # how it works (techniques / research_ops carry their structural mechanism)
    cli: str = ""           # shell invocation (exogenous tools only; "" otherwise)
    source: str = ""        # provenance — which catalogue home this came from (for the audit trail)
    aliases: tuple = field(default_factory=tuple)   # cross-catalogue names (research_ops collapse tb_/ps_ ops)

    def searchable(self) -> str:
        """The text the semantic atlas embeds for this move (name + pattern + anti-pattern + mechanism + the
        collapsed-ALIAS names). Aliases MUST embed: a primitive collapsed into another op (e.g. `tb_NEW_POLYA
        Strategic Specialization` → `broad_05` Extremal) carries its OWN trigger vocabulary only in the alias,
        so omitting it from the embedding makes the recall blind to that trigger forever (2026-06-21 RCA: the
        witness/instance move never surfaced for abstract ∃/iff goals because its discriminating language lived
        only in a non-embedded `aliases_collapsed` field)."""
        parts = (self.name, self.when, self.avoid, self.mechanism) + tuple(self.aliases or ())
        return "  ".join(p for p in parts if p).strip()


# ── STRUCTURAL moves NOT already carried by an exogenous-tool card (these were the AMNESIA: live moves in
#    governed_dag_search with NO agent-facing card — reflection / corroborate / functor_lift / specialize /
#    generalize / decompose). Descriptions reuse the planner `_PLAN_ACTIONS` where present; the rest are authored
#    tight from the governed_dag_search move comments. move_id = the MOVE_* calibration key. ──────────────────
_STRUCTURAL_EXTRAS = [
    {
        "move_id": "conjecture_lemma", "name": "DECOMPOSE / build a prerequisite",
        "when": "G needs a piece of THEORY that does not exist yet — name the MOST GENERAL missing prerequisite "
                "lemma (or break G into sub-lemmas whose conjunction implies G); the apparatus proves it as its "
                "own rung, BANKS it, and G closes by citing it.",
        "avoid": "NOT when an existing result applies (run `search` first) and NOT a tactic gap (use `goalstate`/"
                 "`hammer`). State it GENERAL + load-bearing or the conjecture_advances kernel gate rejects it.",
    },
    {
        # 2026-06-21 re-mint of the witness/minimal-instance lineage (research: `research_log.md` "constructive
        # witness extraction"; `pec_e` Sharpness/Failure-Witness Construction; `tb_NEW_POLYA Strategic
        # Specialization`). The RCA: that lineage was TEXT-COLLAPSED into the generic `broad_05` Extremal Method
        # and dropped from the live port, so the atlas had NO embedded text expressing "abstract ∃/obstruction →
        # instantiate the smallest concrete witness" and never surfaced it for abstract goals (consciousness
        # Čech ∃-goal gapped on exactly this). NOTE the research's prior null: functional-uplift from primitive
        # prompt TEXT was a measured NULL — which is why the load-bearing channel is the STRUCTURAL trigger
        # (`move_atlas._witness_goal_shape`), not this card's embedding; the card makes it electable, the
        # trigger makes it un-missable, and `move_engagement.jsonl` MEASURES whether it actually lifts closure.
        "move_id": "instances_first", "name": "INSTANCES-FIRST / REDUCE-TO-WITNESS (minimal concrete instance)",
        "when": "the goal is an ABSTRACT EXISTENCE / obstruction / UNIVERSAL / IFF claim over a CONSTRUCTED or "
                "arbitrary structure (`∃ x : <built type>, P x`; `∀ … ↔ …` over a built carrier; '∃ a thing with "
                "no global section / a non-trivial class') and the GENERAL proof is OUT OF REACH — do NOT grind "
                "the abstract statement. EXHIBIT the MINIMAL CONCRETE WITNESS: the smallest finite instance that "
                "realizes the phenomenon (a 2-3 element example, a cyclic / degenerate / boundary case, a single "
                "non-trivial cocycle / `ZMod 2` / `Fin n`). Prove that instance as its own rung, BANK it, then "
                "LIFT to the general claim. The minimal witness both discharges the existential AND reveals the "
                "general argument (Polya's decisive special case).",
        "avoid": "NOT when the general proof is already in reach (don't detour). The witness must REALIZE the "
                 "phenomenon — a vacuous/degenerate instance that trivializes the claim is laundering (kernel-caught).",
        "source": "research_op:tb_NEW_POLYA+pec_e (witness/instance lineage, 2026-06-21 re-mint)",
        "aliases": ("Strategic Specialization", "Constructive Witness Extraction",
                    "Sharpness / Failure-Witness Construction", "minimal instance", "smallest concrete case",
                    "decisive special case", "toy example", "construct a witness"),
    },
    {
        "move_id": "specialize", "name": "SPECIALIZE",
        "when": "prove a STRONGER, more explicit statement B that IMPLIES G — when the general goal is out of "
                "reach but a concrete instantiation (a closed form, a rational sub-case) is provable.",
        "avoid": "NOT when B is no easier than G; the chain must actually derive G from B.",
    },
    {
        "move_id": "generalize", "name": "GENERALIZE",
        "when": "prove a MORE GENERAL lemma H of which G is an instance — when the induction/recursion only "
                "closes for a stronger hypothesis (the load-bearing generalization).",
        "avoid": "NOT vacuous over-generalization; G must instantiate from H by a short step.",
    },
    {
        "move_id": "reflection", "name": "REFLECTION (decision procedure)",
        "when": "G is a DECIDABLE proposition the leaf can discharge by writing a verified decidable checker / "
                "`decide`-style computation — a finite case split, a computable predicate.",
        "avoid": "NOT for goals over infinite domains with no decidable instance; native_decide laundering is "
                 "axiom-audited out, so a fake decide fails the gate.",
    },
    {
        "move_id": "corroborate", "name": "CORROBORATE (consequence-refutation)",
        "when": "the Popper DUAL of falsify — derive a CONSEQUENCE K of G and try to refute K; surviving "
                "corroboration raises confidence G is true before investing the full proof.",
        "avoid": "ADVISORY — corroboration never CLOSES G (the kernel proof does); a refuted consequence means G "
                 "is false as written.",
    },
    {
        "move_id": "functor_lift", "name": "FUNCTOR / SPECTRAL LIFT",
        "when": "a stuck DISCRETE goal is lifted to a continuous/spectral domain where the structure is solved, "
                "proved there, then transported back (the domain-lift transport edge).",
        "avoid": "NOT when the lift loses the discreteness the goal depends on; the back-transport must be "
                 "kernel-checked.",
    },
    {
        "move_id": "transport", "name": "TRANSPORT (bring exogenous compute / cross-substrate)",
        "when": "G yields to an EXOGENOUS fact — a witness, a hammered premise, a cross-substrate (Isabelle/SMT) "
                "result, or a Lean-internal Equiv/to_additive transport-of-structure. Pick the matching TOOL.",
        "avoid": "an exogenous ACCEPT is not a Lean closure; the kernel still needs the spliced Lean term.",
    },
]


def _tool_entries() -> "list[MoveEntry]":
    """Source 1 — the exogenous-tool cards (`move_cards._TOOL_SPECS`). Lazy import (move_cards/atlas would
    otherwise cycle)."""
    out = []
    try:
        from ztare.leanmill.solver.move_cards import _TOOL_SPECS
    except Exception:  # noqa: BLE001
        return out
    for s in _TOOL_SPECS:
        out.append(MoveEntry(
            move_id=(s.get("move_key") or f"tool_{s['tool']}"),
            name=s["tool"], kind="tool",     # bare tool name; the renderer prefixes "TOOL" + reuses _tool_backend_live
            when=s.get("when", ""), avoid=s.get("confuser", ""),
            cli=s.get("cli", ""), source="move_cards._TOOL_SPECS",
        ))
    return out


def _structural_entries(seen: set) -> "list[MoveEntry]":
    """Source 2 — structural moves not already carried by a tool card (the amnesia set)."""
    out = []
    for s in _STRUCTURAL_EXTRAS:
        if s["move_id"] in seen:
            continue
        out.append(MoveEntry(
            move_id=s["move_id"], name=s["name"], kind="structural",
            when=s["when"], avoid=s.get("avoid", ""),
            source=s.get("source", "governed_dag_search.MOVE_* / planner _PLAN_ACTIONS"),
            aliases=tuple(s.get("aliases", ()) or ()),   # collapsed-primitive names must reach searchable() (RCA)
        ))
    return out


def _technique_entries() -> "list[MoveEntry]":
    """Source 3 — the transportable-attack technique library (`isomorphism_decompose.TRANSPORTABLE_TECHNIQUES`)."""
    out = []
    try:
        from ztare.leanmill.solver.isomorphism_decompose import TRANSPORTABLE_TECHNIQUES
    except Exception:  # noqa: BLE001
        return out
    for name, how in TRANSPORTABLE_TECHNIQUES:
        slug = "tech_" + "".join(c if c.isalnum() else "_" for c in name)[:48].strip("_").lower()
        out.append(MoveEntry(
            move_id=slug, name=name, kind="technique",
            when=f"transport this named attack when the goal's structure matches it: {how[:200]}",
            mechanism=how, source="isomorphism_decompose.TRANSPORTABLE_TECHNIQUES",
        ))
    return out


def _research_op_entries() -> "list[MoveEntry]":
    """Source 4 — the math research-move catalogue (`universal_research_ops.VOCABULARY_V5`), the two-cultures
    reconciled superset (each op collapses the tb_/ps_ culture-specific moves)."""
    out = []
    try:
        from ztare.research_director.universal_research_ops import VOCABULARY_V5
    except Exception:  # noqa: BLE001
        return out
    for op in VOCABULARY_V5.values():
        mech = " ".join((getattr(op, "structural_mechanism", "") or "").split())
        out.append(MoveEntry(
            move_id=f"op_{op.op_id}", name=getattr(op, "name", op.op_id), kind="research_op",
            when=f"the mathematician's move when the goal calls for it: {mech[:200]}",
            mechanism=mech, source="universal_research_ops.VOCABULARY_V5",
            aliases=tuple(getattr(op, "aliases_collapsed", ()) or ()),
        ))
    return out


_CORPUS_CACHE: "list[MoveEntry] | None" = None


def build_corpus(*, refresh: bool = False) -> "list[MoveEntry]":
    """THE corpus — every move from all four catalogues, deduped by `move_id` (a tool card wins over a bare
    structural move of the same calibration key, since it carries the richer WHEN/NOT + CLI). Cached (the four
    catalogues are static within a process); `refresh=True` rebuilds. Reuse-only: never authors move content
    that already lives in a source catalogue."""
    global _CORPUS_CACHE
    if _CORPUS_CACHE is not None and not refresh:
        return _CORPUS_CACHE
    entries: "list[MoveEntry]" = []
    seen: set = set()
    for e in _tool_entries():               # source 1 first (richest representation wins the dedupe)
        if e.move_id not in seen:
            entries.append(e); seen.add(e.move_id)
    for e in _structural_entries(seen):     # source 2 — only the moves no tool card already covers
        if e.move_id not in seen:
            entries.append(e); seen.add(e.move_id)
    for e in _technique_entries():          # source 3
        if e.move_id not in seen:
            entries.append(e); seen.add(e.move_id)
    for e in _research_op_entries():        # source 4
        if e.move_id not in seen:
            entries.append(e); seen.add(e.move_id)
    _CORPUS_CACHE = entries
    return entries


def corpus_by_kind() -> "dict":
    """{kind: [MoveEntry,…]} — for the static (no-atlas) fallback render order and the doc/health view."""
    out: "dict" = {}
    for e in build_corpus():
        out.setdefault(e.kind, []).append(e)
    return out


def atlas_entries() -> "list[dict]":
    """The corpus shaped for `common.embeddings.build_atlas` (each needs `id` + `text`; other keys → meta).
    The `cli` is serialized in its PORTABLE form (relative `PYTHONPATH=src python3 …`) — the committed atlas
    artifact must be machine-independent (the live render re-derives the absolute prefix from the local repo)."""
    from ztare.leanmill.solver.move_cards import portable_cli as _portable_cli  # lazy: avoid an import cycle
    rows = []
    for e in build_corpus():
        rows.append({"id": e.move_id, "text": e.searchable(), "name": e.name, "kind": e.kind,
                     "when": e.when, "avoid": e.avoid, "cli": _portable_cli(e.cli), "source": e.source})
    return rows


def _selftest() -> int:
    fails = []
    corpus = build_corpus()
    ids = [e.move_id for e in corpus]
    if len(ids) != len(set(ids)):
        fails.append(f"duplicate move_ids: {[i for i in ids if ids.count(i) > 1]}")
    kinds = {e.kind for e in corpus}
    if not {"tool", "structural", "technique", "research_op"} <= kinds:
        fails.append(f"missing a source kind: have {kinds}")
    # the amnesia moves (no tool card) MUST appear as structural entries
    for amnesiac in ("specialize", "generalize", "reflection", "corroborate", "functor_lift", "conjecture_lemma"):
        if amnesiac not in ids:
            fails.append(f"previously-unsurfaced move missing from corpus: {amnesiac}")
    # every entry has searchable text + a provenance source
    for e in corpus:
        if not e.searchable():
            fails.append(f"empty searchable: {e.move_id}")
        if not e.source:
            fails.append(f"no provenance: {e.move_id}")
    rows = atlas_entries()
    if len(rows) != len(corpus) or any("id" not in r or "text" not in r for r in rows):
        fails.append("atlas_entries shape")
    print(f"move_corpus self-test {'PASS' if not fails else 'FAIL ' + str(fails)} "
          f"({len(corpus)} moves: " + ", ".join(f"{k}={len(v)}" for k, v in corpus_by_kind().items()) + ")")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
