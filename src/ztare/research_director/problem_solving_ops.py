"""GP-216 / paper 5b — Problem-solving sister vocabulary v1.

Sister to `theory_building_ops.py`. Six operations mined from 8 problem-solving
arcs (Erdős discrepancy resolution, Green-Tao, Hales-Jewett polymath, Szemerédi
regularity, Roth 3-AP, Behrend AP-free, Furstenberg ergodic, Ramsey-Erdős-
Szekeres). Validated through:

  - Pass 1c: 152 moves enumerated by Sonnet 4.6 + Gemini 2.5 Pro independently
  - Pass 2c: 6 clusters with ≥3-arc cross-spread; 33 outliers preserved
  - Pass 3c: vocabulary tested on theory-builder corpus → 19.1% mean h+m coverage
  - Pass 3d: vocabulary tested on own corpus → 65.9% mean h+m coverage
  - Cross-distribution (Pass 5b/4): symmetric ~42pp gap with theory-building vocabulary in
    both directions; 3 of 6 ops are problem-solver-specific (zero TB instances)

Honest scope limit:

  - DESCRIPTIVE not GENERATIVE: ~66% h+m coverage on own corpus; ~34% of
    problem-solving moves do NOT fit any op here
  - Coverage residue includes: Behrend's geometric construction (domain-specific);
    Green-Tao's number-theoretic toolkit (domain-specific); polymath sociology;
    Erdős's research-style heuristics
  - The vocabulary RECOGNIZES recurring structural moves; it does not GENERATE
    next moves for a stuck researcher
  - Three ops have ZERO theory-builder instances (genuinely problem-solver-
    specific): ps_02, ps_05, ps_06
  - Three ops have non-zero theory-builder instances (shared core / general
    mathematical research): ps_01, ps_03, ps_04
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ProblemSolvingOp:
    """A single problem-solving operation."""

    op_id: str
    name: str
    tier: str  # "psp_specific" | "shared_core"
    structural_mechanism: str
    arc_examples: tuple[str, ...]
    own_corpus_instances: int  # ≥medium-confidence count on PS held-out corpus
    opposite_corpus_instances: int  # ≥medium-confidence count on TB held-out corpus
    overlaps_with: tuple[str, ...]  # cross-vocabulary equivalents
    deployable: bool


VOCABULARY_PS_V1: Dict[str, ProblemSolvingOp] = {
    # ─── Problem-solver-specific tier (3 ops, ZERO TB-corpus instances) ───
    "ps_02": ProblemSolvingOp(
        op_id="ps_02",
        name="Governed Iterative Refinement",
        tier="ps_specific",
        structural_mechanism=(
            "An iterative process is proven to terminate by defining a scalar potential "
            "function that is guaranteed to improve monotonically at each step and is "
            "bounded by a fixed ceiling (Roth's density-increment iteration; Szemerédi's "
            "mean-square energy potential; Tao's entropy decrement)."
        ),
        arc_examples=("roth_3ap", "szemeredi_regularity", "erdos_discrepancy", "hales_jewett_polymath"),
        own_corpus_instances=11,
        opposite_corpus_instances=0,
        overlaps_with=(),  # No theory-building analog
        deployable=True,
    ),
    "ps_05": ProblemSolvingOp(
        op_id="ps_05",
        name="Induction on Structural Rank",
        tier="ps_specific",
        structural_mechanism=(
            "A proof proceeds by induction or recursion on a complexity measure derived "
            "from a structural decomposition of the objects under study (Furstenberg's "
            "induction on tower height in the structure theorem; Ramsey induction on "
            "color/depth)."
        ),
        arc_examples=("furstenberg_ergodic_szemeredi", "ramsey_erdos_szekeres", "hales_jewett_polymath"),
        own_corpus_instances=4,
        opposite_corpus_instances=0,
        overlaps_with=(),
        deployable=True,
    ),
    "ps_06": ProblemSolvingOp(
        op_id="ps_06",
        name="Proof by Estimate Chaining",
        tier="ps_specific",
        structural_mechanism=(
            "A conclusion is reached not by introducing new conceptual objects, but by "
            "establishing a chain of precise quantitative bounds on existing structures "
            "(Roth's Fourier-coefficient bounds chained to density-increment; Erdős's "
            "probabilistic method; Behrend's geometric counting; Erdős-Szekeres double-"
            "counting)."
        ),
        arc_examples=("roth_3ap", "behrend_construction", "erdos_discrepancy", "ramsey_erdos_szekeres", "green_tao"),
        own_corpus_instances=9,
        opposite_corpus_instances=0,
        overlaps_with=(),
        deployable=True,
    ),

    # ─── Shared-core tier (3 ops, non-zero on both corpora) ───
    "ps_01": ProblemSolvingOp(
        op_id="ps_01",
        name="Structural Partitioning",
        tier="shared_core",
        structural_mechanism=(
            "An arbitrary object is decomposed into a canonical set of well-behaved "
            "(structured) and chaotic (pseudorandom) components to isolate complexity "
            "(Szemerédi's regularity partition; Furstenberg structure theorem; Green-"
            "Tao decomposition into structured + pseudorandom integers)."
        ),
        arc_examples=("szemeredi_regularity", "furstenberg_ergodic_szemeredi", "green_tao", "hales_jewett_polymath", "erdos_discrepancy"),
        own_corpus_instances=7,
        opposite_corpus_instances=2,
        overlaps_with=("tb_06 Tacit Pattern Formalization (partial)",),
        deployable=True,
    ),
    "ps_03": ProblemSolvingOp(
        op_id="ps_03",
        name="Formal Equivalence Transfer",
        tier="shared_core",
        structural_mechanism=(
            "A problem is translated into an equivalent form in a different mathematical "
            "domain, allowing the application of that domain's native tools and structures "
            "(Furstenberg's correspondence translating density-A into multiple-recurrence; "
            "Green-Tao transference principle; Behrend's lift to Z^d)."
        ),
        arc_examples=("furstenberg_ergodic_szemeredi", "green_tao", "behrend_construction", "erdos_discrepancy", "hales_jewett_polymath", "ramsey_erdos_szekeres"),
        own_corpus_instances=16,
        opposite_corpus_instances=7,
        overlaps_with=("tb_02 Cross-Domain Unification (strongest cross-cultural overlap)",),
        deployable=True,
    ),
    "ps_04": ProblemSolvingOp(
        op_id="ps_04",
        name="Black-Box Theorem Application",
        tier="shared_core",
        structural_mechanism=(
            "A major theorem is treated as a self-contained module, and the primary work "
            "becomes proving that a new problem setting satisfies the theorem's "
            "preconditions (Green-Tao using Szemerédi as black-box; polymath1 reducing "
            "DHJ to Szemerédi-style increment in IP-rich sets)."
        ),
        arc_examples=("green_tao", "hales_jewett_polymath", "erdos_discrepancy"),
        own_corpus_instances=5,
        opposite_corpus_instances=3,
        overlaps_with=("tb_NEW_POLYA Strategic Specialization", "tb_03 Surrogate Problem Substitution"),
        deployable=True,
    ),
}


def by_tier(tier: str) -> List[ProblemSolvingOp]:
    """Return all ops in a given tier."""
    return [op for op in VOCABULARY_PS_V1.values() if op.tier == tier]


def deployable() -> List[ProblemSolvingOp]:
    """Return ops a stuck researcher can deploy."""
    return [op for op in VOCABULARY_PS_V1.values() if op.deployable]


def get(op_id: str) -> Optional[ProblemSolvingOp]:
    """Look up an op by id."""
    return VOCABULARY_PS_V1.get(op_id)


def render_vocabulary_summary() -> str:
    """Render a human-readable summary of vocabulary v1 with empirical notes."""
    lines = ["# Problem-Solving Sister Vocabulary v1 (paper 5b)", ""]
    lines.append("**Status:** descriptive (not generative); ~66% h+m coverage on own (PS) corpus; ~19% on theory-builder corpus")
    lines.append("**Source:** mined from 8 Gowers/Tao-tradition problem-solver arcs")
    lines.append("**Cross-corpus gap:** −46.8 pp own-corpus advantage (vs theory-builder vocabulary's −37.4 pp)")
    lines.append("")
    for tier_name, tier_label in (
        ("ps_specific", "Problem-Solver-Specific (3 ops, zero theory-builder instances)"),
        ("shared_core", "Shared core (3 ops, non-zero in both corpora)"),
    ):
        lines.append(f"## {tier_label}")
        for op in by_tier(tier_name):
            lines.append(f"- **{op.op_id}** {op.name}")
            lines.append(f"  - Mechanism: {op.structural_mechanism}")
            lines.append(f"  - Arc examples: {', '.join(op.arc_examples)}")
            lines.append(f"  - Own corpus instances: {op.own_corpus_instances}; opposite corpus: {op.opposite_corpus_instances}")
            if op.overlaps_with:
                lines.append(f"  - Overlaps: {', '.join(op.overlaps_with)}")
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "VOCABULARY_PS_V1",
    "ProblemSolvingOp",
    "by_tier",
    "deployable",
    "get",
    "render_vocabulary_summary",
]


if __name__ == "__main__":
    print(render_vocabulary_summary())
