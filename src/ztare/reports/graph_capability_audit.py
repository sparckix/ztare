"""Audit graph capability claims against implementation and standard methods.

The report is intentionally conservative. It separates:

* standard graph algorithms already covered by common libraries;
* ZTARE-specific extraction, conditioning, perturbation, and receipt layers;
* graph results that are wired into action-card or decision-receipt paths.

That makes the public claim auditable: the strongest current claim is the
recombination layer over research artifacts, not a replacement for NetworkX,
igraph, graph neural network libraries, or proof premise-selection systems.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from ztare.research_director.primitive_operator_cards import (
    OPERATOR_CARD_ATLAS_MANIFEST_PATH,
    OPERATOR_CARD_ATLAS_PATH,
    operator_card_atlas_freshness,
)


REPO = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class GraphCapabilityRow:
    method_id: str
    implementation_sites: tuple[str, ...]
    required_markers: tuple[str, ...]
    standard_framework_equivalent: str
    ztare_specific_layer: str
    decision_receipt_path: str
    release_wording_allowed: str
    status: str
    notes: str = ""
    literature_anchor: str = ""
    markers_found: tuple[str, ...] = field(default_factory=tuple)
    present: bool = False


def _rows() -> tuple[GraphCapabilityRow, ...]:
    ns_archive = (
        "projects/ns_millennium_hunt/scripts/_archive/"
        "decommissioned_graph_stack_2026_05_10/graph_stack/"
        "ns_constraint_basin_graph.py"
    )
    ns_front = "projects/ns_millennium_hunt/scripts/ns_graph.py"
    return (
        GraphCapabilityRow(
            method_id="lean_signature_extraction",
            implementation_sites=(ns_archive,),
            required_markers=(
                "def parse_lean_files",
                "def theorem_result_segment",
                "def extract_quantities",
                "def filter_plumbing",
            ),
            standard_framework_equivalent="none: graph libraries do not extract Lean theorem records",
            ztare_specific_layer=(
                "artifact extraction from proof files plus plumbing filters before graph construction"
            ),
            decision_receipt_path="constraint_basin_graph decision receipt after adapter",
            release_wording_allowed="ZTARE-specific extraction layer feeding standard graph algorithms",
            status="ztare_recombination_layer",
        ),
        GraphCapabilityRow(
            method_id="minimum_cut_bottleneck",
            implementation_sites=(ns_archive,),
            required_markers=("minimum_cut", "build_networkx_digraph"),
            standard_framework_equivalent="NetworkX/igraph minimum cut",
            ztare_specific_layer="proof-spine edge witness rendering and sink-conditioned interpretation",
            decision_receipt_path="graph decision receipt or NS workmap route receipt",
            release_wording_allowed="standard algorithm with ZTARE adapter and receipt discipline",
            status="standard_algorithm_with_ztare_adapter",
            literature_anchor="Network flow/min-cut method family",
        ),
        GraphCapabilityRow(
            method_id="target_dominators",
            implementation_sites=(ns_archive,),
            required_markers=("immediate_dominators", "compute_target_dominators"),
            standard_framework_equivalent="NetworkX immediate_dominators",
            ztare_specific_layer="synthetic super-source over sink ancestors and proof-route interpretation",
            decision_receipt_path="constraint basin route receipt",
            release_wording_allowed="standard dominator algorithm with ZTARE target conditioning",
            status="standard_algorithm_with_ztare_adapter",
        ),
        GraphCapabilityRow(
            method_id="target_edge_vitality",
            implementation_sites=(ns_archive,),
            required_markers=("compute_target_edge_vitality", "ancestor_loss", "root_loss"),
            standard_framework_equivalent="edge-removal sensitivity pattern over directed graphs",
            ztare_specific_layer="target-conditioned ancestor/root-loss score over proof basin",
            decision_receipt_path="route demotion or next-edge witness after graph validation",
            release_wording_allowed="ZTARE target-conditioned perturbation diagnostic",
            status="ztare_recombination_layer",
        ),
        GraphCapabilityRow(
            method_id="absorbing_sink_flow",
            implementation_sites=(ns_archive,),
            required_markers=("compute_absorbing_sink_flow", "np.linalg", "absorb"),
            standard_framework_equivalent="absorbing Markov-chain flow family",
            ztare_specific_layer="sink-conditioned flow over proof/constraint records",
            decision_receipt_path="route ranking only after stability and non-use receipt path",
            release_wording_allowed="custom sink-flow adapter over a research constraint graph",
            status="ztare_recombination_layer",
            literature_anchor="absorbing Markov chain diagnostics",
        ),
        GraphCapabilityRow(
            method_id="funnel_backbone",
            implementation_sites=(ns_archive,),
            required_markers=("compute_funnel_backbone", "shortest_path", "pagerank"),
            standard_framework_equivalent="PageRank plus shortest-path/backbone approximation",
            ztare_specific_layer="PageRank terminal selection plus inverse-capacity proof-route backbone",
            decision_receipt_path="candidate route witness or no-use receipt",
            release_wording_allowed="composed backbone heuristic, not a new graph algorithm",
            status="ztare_recombination_layer",
        ),
        GraphCapabilityRow(
            method_id="feedback_arc_cycle_participation",
            implementation_sites=(ns_archive,),
            required_markers=("simple_cycles", "feedback", "cycle"),
            standard_framework_equivalent="SCC/simple-cycle diagnostics; feedback arc set is a known family",
            ztare_specific_layer="cycle-to-bound-chain explanation and false-proof-edge warning",
            decision_receipt_path="circularity or route-demotion receipt",
            release_wording_allowed="cycle diagnostic adapter with research-route interpretation",
            status="standard_algorithm_with_ztare_adapter",
        ),
        GraphCapabilityRow(
            method_id="centrality_disagreement_ensemble",
            implementation_sites=(ns_archive, ns_front),
            required_markers=("pagerank", "edge_betweenness", "hits", "louvain"),
            standard_framework_equivalent="NetworkX PageRank/HITS/betweenness/Louvain/k-core",
            ztare_specific_layer=(
                "multi-method consensus/disagreement and retraction discipline after plumbing filters"
            ),
            decision_receipt_path="graph decision_receipt or advisory signal in ns_graph",
            release_wording_allowed="standard centralities recombined into a research diagnostic ensemble",
            status="ztare_recombination_layer",
        ),
        GraphCapabilityRow(
            method_id="counterfactual_edge_perturbation",
            implementation_sites=(ns_archive, ns_front),
            required_markers=("counterfactual", "edge", "perturb"),
            standard_framework_equivalent="perturb/recompute diagnostic pattern",
            ztare_specific_layer="route retraction or stability receipt when graph salience changes",
            decision_receipt_path="misleading_or_noise or no_strategy_change graph receipt",
            release_wording_allowed="counterfactual graph receipt discipline over research artifacts",
            status="ztare_recombination_layer",
        ),
        GraphCapabilityRow(
            method_id="residual_hypergraph_hitting_set",
            implementation_sites=(ns_front,),
            required_markers=("residual_hypergraph", "hitting", "residual_candidates"),
            standard_framework_equivalent="hypergraph/hitting-set family",
            ztare_specific_layer="open-residual overlay tied to route obligations",
            decision_receipt_path="workmap or pattern-action receipt if selected",
            release_wording_allowed="research-residual overlay; benchmark before stronger claim",
            status="research_candidate_needs_benchmark",
        ),
        GraphCapabilityRow(
            method_id="l3a_workmap_overlay",
            implementation_sites=(
                ns_front,
                "src/ztare/research_director/ns_l3a_workmap.py",
            ),
            required_markers=("workmap", "write_l3a_workmap", "l3a_workmap"),
            standard_framework_equivalent="no direct NetworkX equivalent; application-layer overlay",
            ztare_specific_layer="links graph salience to route obligations and ranked workmap targets",
            decision_receipt_path="workmap ordering; F-row trajectory overlay is not promoted yet",
            release_wording_allowed="ZTARE application-layer research-state overlay",
            status="ztare_recombination_layer",
            notes=(
                "Current support is workmap integration. A future F-row/trajectory "
                "overlay should be audited as a separate promotion once it has a "
                "concrete ledger adapter and decision receipt."
            ),
        ),
        GraphCapabilityRow(
            method_id="probability_dag_trace_carrier",
            implementation_sites=(
                "src/ztare/common/graph_carrier.py",
                "src/ztare/validator/probability_dag_carrier.py",
                "src/ztare/reports/autoresearch_trace.py",
            ),
            required_markers=(
                "validate_graph_carrier",
                "latest_probability_dag.json",
                "decision_receipt",
            ),
            standard_framework_equivalent="DAG data structure; no claim of new graph algorithm",
            ztare_specific_layer="in-loop graph record with validation and downstream decision receipt",
            decision_receipt_path="autoresearch trace graph_carriers[]",
            release_wording_allowed="graph record schema wired into an in-loop trace",
            status="ready_receipt_path",
        ),
        GraphCapabilityRow(
            method_id="source_claim_graph_trace_carrier",
            implementation_sites=(
                "src/ztare/common/graph_carrier.py",
                "src/ztare/validator/source_claim_graph_carrier.py",
                "src/ztare/reports/autoresearch_trace.py",
            ),
            required_markers=(
                "source_claim_graph",
                "workspace/source_index.json",
                "latest_evidence_gaps.json",
                "decision_receipt",
            ),
            standard_framework_equivalent="provenance graph data structure; no claim of new graph algorithm",
            ztare_specific_layer="source/evidence/gap graph record that lowers to recovery actions",
            decision_receipt_path="autoresearch trace graph_carriers[]",
            release_wording_allowed="source-claim graph record wired into autoresearch trace",
            status="ready_receipt_path",
        ),
        GraphCapabilityRow(
            method_id="source_freshness_graph_guard",
            implementation_sites=(
                "src/ztare/workspace/source_freshness.py",
                "src/ztare/validator/source_claim_graph_carrier.py",
                "src/ztare/reports/autoresearch_trace.py",
            ),
            required_markers=(
                "artifact_source_freshness",
                "raw_relative_path",
                "source_index_unverified",
                "evidence_compile_unverified",
                "misleading_or_noise",
            ),
            standard_framework_equivalent="no graph-library equivalent; provenance freshness guard",
            ztare_specific_layer=(
                "shared source-freshness check demotes stale or count-only source graph signals"
            ),
            decision_receipt_path="source-claim graph misleading_or_noise plus trace blockers",
            release_wording_allowed="source-bound graph record guarded against stale or unverifiable provenance",
            status="ready_receipt_path",
        ),
        GraphCapabilityRow(
            method_id="autoresearch_probability_dag_prompt_consumer",
            implementation_sites=(
                "src/ztare/validator/autoresearch_loop.py",
                "src/ztare/validator/dag_steering_context.py",
                "src/ztare/validator/probability_dag_carrier.py",
            ),
            required_markers=(
                "compute_dag_steering_context",
                "probability_dag_context",
                "latest_probability_dag.json",
                "dag_steering_log.jsonl",
                "render_probability_dag_vulnerability_prompt",
                "hysteresis_bumped",
            ),
            standard_framework_equivalent="DAG scheduling and dependency-analysis pattern",
            ztare_specific_layer=(
                "in-loop prompt steering, hysteresis, and damage-signal emission over the probability DAG"
            ),
            decision_receipt_path="steering log plus graph_carriers[] trace receipt",
            release_wording_allowed=(
                "single probability-DAG prompt consumer backed by shared parser/scorer/receipt helpers"
            ),
            status="ready_receipt_path",
            notes=(
                "autoresearch_loop.py renders one probability_dag_context prompt block via "
                "the import-safe dag_steering_context.compute_dag_steering_context(); "
                "probability_dag_carrier.py owns the parser, urgency scorer, "
                "vulnerable-assumption renderer, and trace receipt."
            ),
        ),
        GraphCapabilityRow(
            method_id="graph_action_card_lowering",
            implementation_sites=(
                "src/ztare/research_director/primitive_operator_cards.py",
                "src/ztare/research_director/pattern_action_contract.py",
            ),
            required_markers=(
                "OP-GDC-01",
                "graph_diagnostic_carrier",
                "selected_action_card_or_gate",
                "operator_card_catalog_entries",
                "build_operator_card_atlas",
                "route_operator_cards_semantic",
                "operator_card_routes",
            ),
            standard_framework_equivalent="no graph-library equivalent; orchestration layer",
            ztare_specific_layer="lowers graph diagnostics into action cards, gates, artifact slots, or non-use",
            decision_receipt_path="pattern action contract graph_carrier_artifact",
            release_wording_allowed="graph-to-action-card decision-receipt protocol",
            status="ready_receipt_path",
            notes=(
                "Card instances now export atlas-ready rows and route through an "
                "optional semantic card atlas when present. The deterministic "
                "move-card router remains the fallback; the atlas is not built "
                "by default. Pattern-action contracts expose route provenance "
                "as semantic_atlas or lexical_fallback."
            ),
        ),
        GraphCapabilityRow(
            method_id="graph_carrier_rd_action_consumer",
            implementation_sites=(
                "src/ztare/research_director/graph_carrier_actions.py",
                "src/ztare/reports/autoresearch_trace.py",
            ),
            required_markers=(
                "graph_carrier_action_rows",
                "validate_graph_carrier_summary",
                "out_of_loop_evidence_recovery",
                "in_loop_focus_receipt",
                "graph_rd_actions",
                "OP-GDC-01",
                "operator_card_routes",
                "operator_card_ids",
            ),
            standard_framework_equivalent="no graph-library equivalent; RD read-model layer",
            ztare_specific_layer=(
                "turns compact, validated graph summaries into in-loop versus out-of-loop advisory actions with graph-card route provenance"
            ),
            decision_receipt_path="autoresearch trace graph_rd_actions[]",
            release_wording_allowed="RD graph-record consumer for advisory prep and recovery actions",
            status="ready_receipt_path",
        ),
    )


def _read_site(repo: Path, site: str) -> str:
    path = repo / site
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _markers_found(repo: Path, row: GraphCapabilityRow) -> tuple[str, ...]:
    texts = [_read_site(repo, site) for site in row.implementation_sites]
    found: list[str] = []
    for marker in row.required_markers:
        if any(marker in text for text in texts):
            found.append(marker)
    return tuple(found)


def _rel(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _operator_card_atlas_summary(repo: Path) -> dict:
    atlas_path = repo / _rel(REPO, OPERATOR_CARD_ATLAS_PATH)
    manifest_path = repo / _rel(REPO, OPERATOR_CARD_ATLAS_MANIFEST_PATH)
    summary = operator_card_atlas_freshness(
        atlas_path=atlas_path,
        manifest_path=manifest_path,
    )
    return {
        **summary,
        "atlas_path": _rel(repo, atlas_path),
        "manifest_path": _rel(repo, manifest_path),
    }


def build_graph_capability_audit(repo: Path | str = REPO) -> dict:
    """Return the graph capability audit as a pure data object."""
    repo_path = Path(repo)
    rows: list[GraphCapabilityRow] = []
    for row in _rows():
        found = _markers_found(repo_path, row)
        rows.append(
            GraphCapabilityRow(
                **{
                    **asdict(row),
                    "markers_found": found,
                    "present": len(found) == len(row.required_markers),
                }
            )
        )

    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1

    ready_receipt_paths = [
        row.method_id for row in rows
        if row.present and row.status == "ready_receipt_path"
    ]
    recombination_rows = [
        row.method_id for row in rows
        if row.present and row.status in {"ztare_recombination_layer", "ready_receipt_path"}
    ]
    standard_rows = [
        row.method_id for row in rows
        if row.present and row.status == "standard_algorithm_with_ztare_adapter"
    ]
    missing_rows = [row.method_id for row in rows if not row.present]
    operator_card_atlas = _operator_card_atlas_summary(repo_path)
    card_router_semantic_status = (
        "semantic_atlas_available; graph-card routes may use semantic_atlas with lexical backfill"
        if operator_card_atlas.get("semantic_deployed")
        else (
            "lexical_fallback_current; build and evaluate the operator-card atlas "
            "before describing graph-card selection as semantic routing"
        )
    )

    verdict = {
        "not_framework_replacement": True,
        "strongest_supported_claim": (
            "ZTARE has a graph diagnostic and decision-receipt layer over "
            "research artifacts; standard algorithms remain library-backed."
        ),
        "release_boundary": (
            "Do not claim novelty for min-cut, dominators, PageRank, HITS, "
            "centrality, communities, k-core, shortest paths, or link prediction. "
            "Claim the extraction, conditioning, disagreement, perturbation, "
            "action-card lowering, and decision-receipt layer where present."
        ),
        "needs_before_stronger_claim": (
            "add one benchmark if learned graph prediction is promoted; wire a "
            "ledger/trajectory overlay before claiming graph salience predicts "
            "belief updates"
        ),
        "card_router_semantic_status": card_router_semantic_status,
    }

    return {
        "schema": "ztare-graph-capability-audit-v1",
        "summary": {
            "row_count": len(rows),
            "present_count": sum(1 for row in rows if row.present),
            "missing_count": len(missing_rows),
            "status_counts": counts,
            "standard_algorithm_rows": standard_rows,
            "recombination_rows": recombination_rows,
            "ready_receipt_paths": ready_receipt_paths,
            "missing_rows": missing_rows,
            "operator_card_atlas_status": operator_card_atlas["status"],
            "operator_card_routing_mode": operator_card_atlas["routing_mode"],
        },
        "verdict": verdict,
        "operator_card_atlas": operator_card_atlas,
        "rows": [asdict(row) for row in rows],
    }


def render_markdown(report: dict) -> str:
    """Render a compact markdown report for CLI users."""
    summary = report["summary"]
    lines = [
        "# Graph Capability Audit",
        "",
        f"Rows present: {summary['present_count']}/{summary['row_count']}",
        f"Operator-card atlas: {summary['operator_card_atlas_status']} ({summary['operator_card_routing_mode']})",
        "",
        "Verdict: " + report["verdict"]["strongest_supported_claim"],
        "",
        "| Method | Status | Present | Allowed wording |",
        "|---|---|---:|---|",
    ]
    for row in report["rows"]:
        lines.append(
            "| {method_id} | {status} | {present} | {release_wording_allowed} |".format(
                **row
            )
        )
    lines.extend([
        "",
        "Boundary: " + report["verdict"]["release_boundary"],
    ])
    return "\n".join(lines) + "\n"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = build_graph_capability_audit(args.repo)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
