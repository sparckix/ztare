"""Semantic registry for LLM-mediated research primitives.

This registry is a taxonomy layer over existing implementation symbols. It does
not rename or hide the concrete modules that primitive amnesia and the
architecture index already know. The purpose is to make related primitives
legible as families: core workbench workers, external perspective generators,
review/governance helpers, and composition helpers.
"""
from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PrimitiveFamilyCard:
    primitive_id: str
    family_id: str
    family_label: str
    role: str
    module_path: str
    entrypoint: str
    lifecycle: str
    call_site: str | None
    transport_policy: str
    artifact_surface: str
    trigger_surface: str
    semantic_aliases: tuple[str, ...]
    preserves_symbol_identity: bool = True


@dataclass(frozen=True)
class PrimitiveParentNode:
    family_id: str
    family_label: str
    purpose: str
    child_count: int
    matched_terms: tuple[str, ...]
    child_primitives: tuple[str, ...]
    call_sites: tuple[str, ...]
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class PrimitiveFamilyRegistryIssue:
    primitive_id: str
    issue_type: str
    detail: str


@dataclass(frozen=True)
class PrimitiveFamilyRegistryAudit:
    ok: bool
    card_count: int
    family_count: int
    dispatch_call_site_count: int
    issues: tuple[PrimitiveFamilyRegistryIssue, ...]


FAMILY_PURPOSES: dict[str, str] = {
    "core_workbench_worker": "Workers that produce or judge the main in-loop artifact under typed contracts.",
    "external_perspective_generator": "Primitives that add an orthogonal perspective, deanchor a stuck line, or create an independent critique/seed.",
    "review_governance_helper": "Primitives that review rubrics, charters, catalogs, or completed runs and produce governance/advisory artifacts.",
    "composition_helper": "Primitives that compose, label, or enrich candidate/evidence surfaces around the main loop.",
}


CARDS: tuple[PrimitiveFamilyCard, ...] = (
    PrimitiveFamilyCard(
        primitive_id="autoresearch_mutator_worker",
        family_id="core_workbench_worker",
        family_label="Core Workbench Worker",
        role="Propose and write candidate theses inside the autoresearch loop.",
        module_path="src/ztare/validator/autoresearch_loop.py",
        entrypoint="safe_mutate",
        lifecycle="in_loop",
        call_site="mutator",
        transport_policy="api default; subscription CLI via ZTARE_AGENT_DISPATCH_MUTATOR=agent",
        artifact_surface="thesis candidate plus per-iteration prompt/debug artifacts",
        trigger_surface="every active iteration unless a direct-injection seed replaces iter-1",
        semantic_aliases=("mutator", "candidate writer", "proposal worker"),
    ),
    PrimitiveFamilyCard(
        primitive_id="autoresearch_judge_worker",
        family_id="core_workbench_worker",
        family_label="Core Workbench Worker",
        role="Adversarially judge a candidate thesis under the rubric contract.",
        module_path="src/ztare/validator/test_thesis.py",
        entrypoint="safe_generate",
        lifecycle="in_loop_judge",
        call_site="judge",
        transport_policy="api default; subscription CLI via ZTARE_AGENT_DISPATCH_JUDGE=agent",
        artifact_surface="latest_eval_results.json and judge verdict fields",
        trigger_surface="per-iteration judge phase",
        semantic_aliases=("judge", "rubric critic", "adversarial evaluator"),
    ),
    PrimitiveFamilyCard(
        primitive_id="dynamic_committee_worker",
        family_id="core_workbench_worker",
        family_label="Core Workbench Worker",
        role="Generate a dynamic judging committee before a dynamic run.",
        module_path="src/ztare/validator/generate_committee.py",
        entrypoint="safe_generate_committee",
        lifecycle="pre_loop_dynamic_committee",
        call_site="committee",
        transport_policy="api default; subscription CLI via ZTARE_AGENT_DISPATCH_COMMITTEE=agent",
        artifact_surface="dynamic committee JSON",
        trigger_surface="dynamic committee mode",
        semantic_aliases=("committee", "panel generator", "reviewer set"),
    ),
    PrimitiveFamilyCard(
        primitive_id="cold_llm_erdos_seed",
        family_id="external_perspective_generator",
        family_label="External Perspective Generator",
        role="Generate deanchored cross-domain candidate forms from an anonymized fingerprint.",
        module_path="src/ztare/fit/cold_llm_erdos_seed.py",
        entrypoint="query_cold_llm_erdos_seed",
        lifecycle="pre_iter_1",
        call_site="cold_llm_erdos_seed",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="workspace/cold_llm_seed_iter0.json",
        trigger_surface="enable_cold_llm_erdos_seed / cold-shot policy de_anchor_seed",
        semantic_aliases=("deanchor seed", "cross-domain seed", "cold erdos", "cold_start"),
    ),
    PrimitiveFamilyCard(
        primitive_id="cold_shot_structural_seed",
        family_id="external_perspective_generator",
        family_label="External Perspective Generator",
        role="Generate a substrate-aware structural seed artifact before iter-1.",
        module_path="src/ztare/orchestrator/cold_shot_seed.py",
        entrypoint="fire_cold_shot_seed",
        lifecycle="pre_iter_1",
        call_site="cold_shot_seed",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="workspace/cold_shot_seed.json",
        trigger_surface="enable_cold_shot_seed / cold-shot policy physics_lagrangian_seed",
        semantic_aliases=("structural seed", "lagrangian seed", "cold shot", "cold_start"),
    ),
    PrimitiveFamilyCard(
        primitive_id="qualitative_evidence_cold_shot",
        family_id="external_perspective_generator",
        family_label="External Perspective Generator",
        role="Generate evidence-grounded thesis-family candidates for qualitative substrates.",
        module_path="src/ztare/orchestrator/qualitative_evidence_cold_shot.py",
        entrypoint="run_qualitative_evidence_cold_shot",
        lifecycle="pre_iter_1",
        call_site="qualitative_evidence_cold_shot",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="workspace/qualitative_evidence_cold_shot.json",
        trigger_surface="enable_qualitative_evidence_cold_shot / cold-shot policy qualitative_evidence_seed",
        semantic_aliases=("evidence seed", "qualitative seed", "evidence-grounded cold shot", "cold_start"),
    ),
    PrimitiveFamilyCard(
        primitive_id="frontier_script_scaffold",
        family_id="external_perspective_generator",
        family_label="External Perspective Generator",
        role="Draft a frontier script scaffold from a bounded prompt and allowed roots.",
        module_path="src/ztare/orchestrator/frontier_script_scaffold_runner.py",
        entrypoint="run_frontier_script_meta_cold_shot",
        lifecycle="pre_or_side_run",
        call_site="frontier_script_scaffold",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="frontier script scaffold JSON/cache record",
        trigger_surface="explicit scaffold runner invocation",
        semantic_aliases=("frontier scaffold", "script scaffold", "meta cold shot", "cold_start"),
    ),
    PrimitiveFamilyCard(
        primitive_id="fit_analogy_query",
        family_id="external_perspective_generator",
        family_label="External Perspective Generator",
        role="Query for cross-domain forms matching a fit failure fingerprint.",
        module_path="src/ztare/fit/analogy.py",
        entrypoint="query_analogy",
        lifecycle="fit_optional",
        call_site="fit_analogy",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="analogy response/candidates consumed by fit dispatch",
        trigger_surface="R15 analogy route",
        semantic_aliases=("analogy", "cross-domain transfer", "alien math"),
    ),
    PrimitiveFamilyCard(
        primitive_id="inverter_review",
        family_id="external_perspective_generator",
        family_label="External Perspective Generator",
        role="Ask an independent inverter to produce tests and weaknesses for a thesis.",
        module_path="src/ztare/validator/inverter_agent.py",
        entrypoint="_produce_inverter_review",
        lifecycle="in_loop_optional",
        call_site="inverter_review",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="workspace/inverter_review.json and discriminator proposals",
        trigger_surface="inverter-enabled validator path",
        semantic_aliases=("inverter", "adversarial inversion", "independent critique"),
    ),
    PrimitiveFamilyCard(
        primitive_id="mform_alignment_audit",
        family_id="external_perspective_generator",
        family_label="External Perspective Generator",
        role="Audit whether a high-scoring qualitative thesis drifted away from charter intent.",
        module_path="src/ztare/validator/mform_alignment_audit.py",
        entrypoint="run_general_office_audit",
        lifecycle="audit_optional",
        call_site="mform_alignment_audit",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="goodhart/alignment audit finding",
        trigger_surface="stochastic high-score qualitative audit",
        semantic_aliases=("alignment audit", "general office", "charter intent audit"),
    ),
    PrimitiveFamilyCard(
        primitive_id="eigenquestion_generator",
        family_id="external_perspective_generator",
        family_label="External Perspective Generator",
        role="Generate an orthogonal research question from current evidence and explored classes.",
        module_path="src/ztare/research_director/eigenquestion_generator.py",
        entrypoint="generate_eigenquestion",
        lifecycle="out_of_loop_rd_planning",
        call_site="eigenquestion_generator",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="proposed_eigenquestion markdown",
        trigger_surface="RD planning / make eigenquestion-propose",
        semantic_aliases=("eigenquestion", "orthogonal question", "research question generator"),
    ),
    PrimitiveFamilyCard(
        primitive_id="substrate_recommender",
        family_id="review_governance_helper",
        family_label="Review And Governance Helper",
        role="Recommend candidate substrates or branch-specific workbench surfaces for RD planning.",
        module_path="src/ztare/research_director/substrate_recommender.py",
        entrypoint="call_recommender_model",
        lifecycle="out_of_loop_rd_planning",
        call_site="substrate_recommender",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="ztare_workspace/inbox/substrate_recommendations markdown",
        trigger_surface="ztare.research_director.substrate_recommender cold/branch modes",
        semantic_aliases=("substrate recommender", "workbench routing", "branch recommendation"),
    ),
    PrimitiveFamilyCard(
        primitive_id="rubric_review",
        family_id="review_governance_helper",
        family_label="Review And Governance Helper",
        role="Review rubric, charter, and evidence surface before the loop starts.",
        module_path="src/ztare/rubrics/review_rubric.py",
        entrypoint="run_rubric_review",
        lifecycle="pre_run",
        call_site="rubric_review",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="workspace/rubric_review.json and evidence gaps",
        trigger_surface="make rubric-review / setup-project",
        semantic_aliases=("rubric review", "pre-run evidence gaps", "rubric critic"),
    ),
    PrimitiveFamilyCard(
        primitive_id="charter_critic_fingerprint",
        family_id="review_governance_helper",
        family_label="Review And Governance Helper",
        role="Classify charter fingerprint/reframe shape for charter critic routing.",
        module_path="src/ztare/orchestrator/charter_critic.py",
        entrypoint="_llm_classify_fingerprint",
        lifecycle="pre_or_post_run_charter",
        call_site="charter_critic_fingerprint",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="charter critic classification fields",
        trigger_surface="enable_charter_critic",
        semantic_aliases=("charter critic", "fingerprint classifier", "reframe classifier"),
    ),
    PrimitiveFamilyCard(
        primitive_id="charter_critic_patch",
        family_id="review_governance_helper",
        family_label="Review And Governance Helper",
        role="Generate advisory charter/rubric patch candidates.",
        module_path="src/ztare/orchestrator/charter_critic.py",
        entrypoint="_heavy_patch_via_llm",
        lifecycle="pre_or_post_run_charter",
        call_site="charter_critic_patch",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="charter_patch_candidate artifact",
        trigger_surface="enable_charter_critic",
        semantic_aliases=("charter patch", "rubric patch", "charter critic"),
    ),
    PrimitiveFamilyCard(
        primitive_id="charter_critic_reviewer",
        family_id="review_governance_helper",
        family_label="Review And Governance Helper",
        role="Review charter patch candidates against operator policy.",
        module_path="src/ztare/orchestrator/charter_critic.py",
        entrypoint="_review_via_llm",
        lifecycle="pre_or_post_run_charter",
        call_site="charter_critic_reviewer",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="charter patch review decision",
        trigger_surface="charter patch review policy",
        semantic_aliases=("charter reviewer", "patch reviewer", "operator policy review"),
    ),
    PrimitiveFamilyCard(
        primitive_id="post_run_meta_audit",
        family_id="review_governance_helper",
        family_label="Review And Governance Helper",
        role="Critique a completed run and propose discriminator repairs.",
        module_path="src/ztare/orchestrator/post_run_meta_audit.py",
        entrypoint="run_post_run_meta_audit",
        lifecycle="post_run",
        call_site="post_run_meta_audit",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="workspace/post_run_meta_audit.json and .md",
        trigger_surface="enable_post_run_meta_audit",
        semantic_aliases=("post-run audit", "meta audit", "run critic"),
    ),
    PrimitiveFamilyCard(
        primitive_id="primitive_quality_filter",
        family_id="review_governance_helper",
        family_label="Review And Governance Helper",
        role="Conservatively filter primitive-catalog candidates during catalog population.",
        module_path="src/ztare/research_director/primitive_amnesia.py",
        entrypoint="_llm_quality_filter",
        lifecycle="operator_health_check",
        call_site="primitive_quality_filter",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="filtered primitive names",
        trigger_surface="primitive catalog population",
        semantic_aliases=("primitive quality", "catalog curation", "capability filter"),
    ),
    PrimitiveFamilyCard(
        primitive_id="recombination_fusion",
        family_id="composition_helper",
        family_label="Composition Helper",
        role="Fuse multiple viable mutator candidates into a non-collapsed hybrid.",
        module_path="src/ztare/orchestrator/recombination.py",
        entrypoint="persona_fusion",
        lifecycle="in_loop_optional",
        call_site="recombination_fusion",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="parallel_blitz fusion result and tournament pool",
        trigger_surface="enable_recombination with sufficient parallel candidates",
        semantic_aliases=("recombination", "persona fusion", "hybrid candidate"),
    ),
    PrimitiveFamilyCard(
        primitive_id="evidence_gap_enrichment",
        family_id="composition_helper",
        family_label="Composition Helper",
        role="Propose external evidence sources when feature support collapses.",
        module_path="src/ztare/orchestrator/evidence_gap_enrichment.py",
        entrypoint="propose_evidence_gap_enrichment",
        lifecycle="in_loop_or_post_judge",
        call_site="evidence_gap_enrichment",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="workspace/evidence_gap_enrichment_proposals.json",
        trigger_surface="enable_evidence_gap_enrichment_proposals",
        semantic_aliases=("evidence enrichment", "source proposal", "feature support repair"),
    ),
    PrimitiveFamilyCard(
        primitive_id="proposal_class_extraction",
        family_id="composition_helper",
        family_label="Composition Helper",
        role="Extract a compact proposal class name for prompt/trajectory bookkeeping.",
        module_path="src/ztare/research_director/primitive_class_rotation.py",
        entrypoint="_extract_class_via_llm",
        lifecycle="prompt_assembly",
        call_site="proposal_class_extraction",
        transport_policy="api default; optional subscription CLI via scoped dispatch env",
        artifact_surface="proposal class label",
        trigger_surface="prompt assembly class extraction",
        semantic_aliases=("class extraction", "proposal label", "trajectory label"),
    ),
    PrimitiveFamilyCard(
        primitive_id="out_of_loop_judge",
        family_id="review_governance_helper",
        family_label="Review And Governance Helper",
        role="Run an explicit out-of-loop judge with API/subscription/fallback transport policy.",
        module_path="src/ztare/validator/judge_out_of_loop.py",
        entrypoint="_llm",
        lifecycle="out_of_loop",
        call_site="out_of_loop_judge",
        transport_policy="ZTARE_JUDGE_TRANSPORT controls api/subscription/fallback",
        artifact_surface="out-of-loop judge response",
        trigger_surface="judge_out_of_loop invocation",
        semantic_aliases=("out-of-loop judge", "cross-provider judge", "subscription judge"),
    ),
)


def all_cards() -> tuple[PrimitiveFamilyCard, ...]:
    return CARDS


def cards_by_family(family_id: str) -> tuple[PrimitiveFamilyCard, ...]:
    return tuple(card for card in CARDS if card.family_id == family_id)


def card_by_call_site(call_site: str) -> PrimitiveFamilyCard | None:
    for card in CARDS:
        if card.call_site == call_site:
            return card
    return None


def dispatch_call_sites() -> set[str]:
    return {card.call_site for card in CARDS if card.call_site}


def family_summary() -> dict[str, int]:
    return dict(Counter(card.family_id for card in CARDS))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _module_definitions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def build_registry_integrity_audit(repo_root: str | Path | None = None) -> PrimitiveFamilyRegistryAudit:
    """Check that semantic cards still point at live implementation symbols."""

    root = Path(repo_root) if repo_root is not None else _repo_root()
    issues: list[PrimitiveFamilyRegistryIssue] = []
    seen: set[str] = set()
    definition_cache: dict[Path, set[str]] = {}

    for card in CARDS:
        if card.primitive_id in seen:
            issues.append(
                PrimitiveFamilyRegistryIssue(
                    primitive_id=card.primitive_id,
                    issue_type="duplicate_primitive_id",
                    detail="primitive id appears more than once",
                )
            )
        seen.add(card.primitive_id)

        if card.family_id not in FAMILY_PURPOSES:
            issues.append(
                PrimitiveFamilyRegistryIssue(
                    primitive_id=card.primitive_id,
                    issue_type="unknown_family",
                    detail=card.family_id,
                )
            )

        path = root / card.module_path
        if not path.exists():
            issues.append(
                PrimitiveFamilyRegistryIssue(
                    primitive_id=card.primitive_id,
                    issue_type="missing_module_path",
                    detail=str(card.module_path),
                )
            )
            continue

        try:
            definitions = definition_cache.setdefault(path, _module_definitions(path))
        except SyntaxError as exc:
            issues.append(
                PrimitiveFamilyRegistryIssue(
                    primitive_id=card.primitive_id,
                    issue_type="module_parse_error",
                    detail=f"{card.module_path}: {exc}",
                )
            )
            continue

        if card.entrypoint not in definitions:
            issues.append(
                PrimitiveFamilyRegistryIssue(
                    primitive_id=card.primitive_id,
                    issue_type="missing_entrypoint",
                    detail=f"{card.module_path}:{card.entrypoint}",
                )
            )

        if card.call_site is not None and not card.call_site.strip():
            issues.append(
                PrimitiveFamilyRegistryIssue(
                    primitive_id=card.primitive_id,
                    issue_type="empty_call_site",
                    detail="call_site must be None or a non-empty string",
                )
            )

    return PrimitiveFamilyRegistryAudit(
        ok=not issues,
        card_count=len(CARDS),
        family_count=len(FAMILY_PURPOSES),
        dispatch_call_site_count=len(dispatch_call_sites()),
        issues=tuple(issues),
    )


def parent_nodes(query_terms: Iterable[str] = ()) -> tuple[PrimitiveParentNode, ...]:
    """Return MECE semantic parent nodes over the primitive cards.

    Query terms only affect ordering and matched-term display; every family is
    still returned so the RD sees the whole parent graph.
    """
    query = tuple(str(term).lower() for term in query_terms if str(term).strip())
    nodes: list[PrimitiveParentNode] = []
    for family_id in sorted(FAMILY_PURPOSES):
        children = cards_by_family(family_id)
        label = children[0].family_label if children else family_id
        aliases = tuple(sorted({alias for card in children for alias in card.semantic_aliases}))
        haystack = " ".join(
            [
                family_id,
                label,
                FAMILY_PURPOSES[family_id],
                " ".join(aliases),
                " ".join(card.primitive_id for card in children),
                " ".join(card.role for card in children),
            ]
        ).lower()
        matched = tuple(term for term in query if term in haystack)
        nodes.append(
            PrimitiveParentNode(
                family_id=family_id,
                family_label=label,
                purpose=FAMILY_PURPOSES[family_id],
                child_count=len(children),
                matched_terms=matched,
                child_primitives=tuple(card.primitive_id for card in children),
                call_sites=tuple(card.call_site for card in children if card.call_site),
                aliases=aliases[:16],
            )
        )
    return tuple(sorted(nodes, key=lambda node: (-len(node.matched_terms), node.family_id)))


def render_markdown(cards: Iterable[PrimitiveFamilyCard] = CARDS) -> str:
    lines = [
        "# LLM-Mediated Primitive Families",
        "",
        "This taxonomy preserves existing implementation symbols and adds a semantic family view.",
        "",
        "| Primitive | Family | Lifecycle | Call site | Module |",
        "|---|---|---|---|---|",
    ]
    for card in cards:
        lines.append(
            f"| `{card.primitive_id}` | `{card.family_id}` | `{card.lifecycle}` | "
            f"`{card.call_site or ''}` | `{card.module_path}:{card.entrypoint}` |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument("--family", help="Restrict to one family id.")
    parser.add_argument("--check", action="store_true", help="Check that cards point at live symbols.")
    args = parser.parse_args(argv)

    if args.check:
        audit = build_registry_integrity_audit()
        if args.json:
            print(json.dumps(asdict(audit), indent=2, sort_keys=True))
        else:
            print(
                "Primitive family registry "
                f"status={'ok' if audit.ok else 'needs_attention'} "
                f"cards={audit.card_count} issues={len(audit.issues)}"
            )
            for issue in audit.issues:
                print(f"- {issue.primitive_id}: {issue.issue_type}: {issue.detail}")
        return 0 if audit.ok else 1

    cards = cards_by_family(args.family) if args.family else CARDS
    if args.json:
        print(json.dumps({
            "schema": "ztare-primitive-family-registry-v1",
            "summary": family_summary(),
            "cards": [asdict(card) for card in cards],
        }, indent=2, sort_keys=True))
    else:
        print(render_markdown(cards))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
