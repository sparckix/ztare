"""Audit move-card routing on a fixed paraphrase set.

The graph capability audit answers whether graph/card routing artifacts are
wired. This report answers a narrower question: do compact move cards route
recognizable task phrasings to the intended card without adding another local
phrase table in callers?
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
import re

from ztare.research_director.primitive_operator_cards import (
    OPERATOR_CARD_ATLAS_PATH,
    OperatorCard,
    operator_card_atlas_freshness,
    route_operator_cards,
    route_operator_cards_semantic,
)


@dataclass(frozen=True)
class RouterAuditCase:
    case_id: str
    expected_card_id: str
    prompt: str
    confuser_card_ids: tuple[str, ...] = ()


CASES: tuple[RouterAuditCase, ...] = (
    RouterAuditCase(
        case_id="evidence_carrier_proxy_update",
        expected_card_id="OP-ECR-01",
        prompt=(
            "An indirect assay proxy measurement is being used as an evidence "
            "carrier for a claim update; require receipt and falsifier."
        ),
    ),
    RouterAuditCase(
        case_id="hard_residual_research_contract",
        expected_card_id="OP-HRD-01",
        prompt=(
            "Hard mathematical residual at a proof frontier; require pencil "
            "artifact, kill condition, tool pass, and verification gate."
        ),
    ),
    RouterAuditCase(
        case_id="pde_estimate_carrier",
        expected_card_id="OP-PDE-01",
        prompt="area ns pde estimate Duhamel carrier with vorticity dimensional endpoint check.",
    ),
    RouterAuditCase(
        case_id="branch_coverage_gate",
        expected_card_id="OP-BCG-01",
        prompt=(
            "The conclusion depends on case split coverage across regimes and "
            "thresholds; every branch needs a receipt before aggregation."
        ),
    ),
    RouterAuditCase(
        case_id="analogy_transfer_audit",
        expected_card_id="OP-XFT-01",
        prompt=(
            "Use an analogy and source-target isomorphism to transfer a "
            "representation while preserving the invariant."
        ),
    ),
    RouterAuditCase(
        case_id="surplus_loss_projection",
        expected_card_id="OP-SLP-01",
        prompt=(
            "Lift to an ambient high-dimensional lattice with entropy surplus, "
            "loss budget, quotient projection, injective multiplicity, and target-size bound."
        ),
    ),
    RouterAuditCase(
        case_id="portable_estimate_receipt",
        expected_card_id="OP-PER-01",
        prompt=(
            "Use pec_a auxiliary object and pec_e hostile witness as a portable "
            "estimate receipt; fill selected receipt family and nearest confuser."
        ),
    ),
    RouterAuditCase(
        case_id="local_global_assembly",
        expected_card_id="OP-LGA-01",
        prompt=(
            "Local modules and patches are valid individually but need global "
            "assembly, interface compatibility, and gluing receipts."
        ),
    ),
    RouterAuditCase(
        case_id="claim_boundary_mutation",
        expected_card_id="OP-CBM-01",
        prompt=(
            "The proposal overclaims; narrow the claim boundary to an answer "
            "object, success criterion, missing evidence, and pass-fail boundary."
        ),
    ),
    RouterAuditCase(
        case_id="reflexive_mining_instrument",
        expected_card_id="OP-RMI-01",
        prompt=(
            "Reflexive mining of primitive ROI and operations intelligence "
            "should inspect portfolio attention and in-loop share before roadmap decision."
        ),
        confuser_card_ids=("OP-AWR-01",),
    ),
    RouterAuditCase(
        case_id="graph_diagnostic_carrier",
        expected_card_id="OP-GDC-01",
        prompt=(
            "A context graph over source claims uses min-cut, PageRank, graph "
            "disagreement, and a decision receipt to select the next artifact."
        ),
        confuser_card_ids=("OP-XFT-01", "OP-ECR-01"),
    ),
    RouterAuditCase(
        case_id="meta_language_edge_carrier",
        expected_card_id="OP-MME-01",
        prompt=(
            "mm_02 quotient surface and mm_03 live residual should compile an "
            "evidence-path graph into a residual-to-check causal edge."
        ),
        confuser_card_ids=("OP-GDC-01",),
    ),
    RouterAuditCase(
        case_id="autoresearch_workbench_routing",
        expected_card_id="OP-AWR-01",
        prompt=(
            "A bounded claim with stable evaluator, rubric surface, and artifact "
            "surface needs autoresearch workbench routing: invoke in-loop or stay out-of-loop."
        ),
        confuser_card_ids=("OP-RMI-01",),
    ),
)


def _route_mode(cards: list[OperatorCard]) -> str:
    if any(
        str(term).startswith("semantic:")
        for card in cards
        for term in getattr(card, "matched_terms", ())
    ):
        return "semantic_atlas"
    return "lexical_fallback"


def _safe_error(exc: BaseException) -> str:
    """Compact provider/runtime errors without leaking credentials."""
    text = str(exc).strip().replace("\n", " ")
    text = re.sub(r"(AIza[0-9A-Za-z_\-]{20,}|sk-[0-9A-Za-z_\-]{12,}|xai-[0-9A-Za-z_\-]{12,})", "[redacted]", text)
    if len(text) > 240:
        text = text[:237] + "..."
    return f"{exc.__class__.__name__}: {text}"


def _case_result(
    case: RouterAuditCase,
    *,
    top_n: int,
    semantic_live: bool,
) -> dict:
    semantic_error: str | None = None
    if semantic_live:
        try:
            cards = route_operator_cards_semantic(
                context=case.prompt,
                top_n=top_n,
                raise_on_semantic_error=True,
            )
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            semantic_error = _safe_error(exc)
            cards = route_operator_cards(context=case.prompt, top_n=top_n)
    else:
        cards = route_operator_cards(context=case.prompt, top_n=top_n)
    top_ids = [card.card_id for card in cards]
    primary_card_id = top_ids[0] if top_ids else None
    expected_rank = top_ids.index(case.expected_card_id) + 1 if case.expected_card_id in top_ids else None
    if semantic_error:
        route_mode = "semantic_error_lexical_fallback"
    else:
        route_mode = _route_mode(cards) if semantic_live else "deterministic_lexical"
    return {
        **asdict(case),
        "primary_card_id": primary_card_id,
        "top_card_ids": top_ids,
        "expected_rank": expected_rank,
        "expected_primary": primary_card_id == case.expected_card_id,
        "expected_in_top_n": expected_rank is not None,
        "route_mode": route_mode,
        "matched_terms": {
            card.card_id: list(card.matched_terms)
            for card in cards
            if card.card_id in {case.expected_card_id, primary_card_id, *case.confuser_card_ids}
        },
        "semantic_error": semantic_error,
    }


def build_operator_card_router_audit(*, semantic_live: bool = False, top_n: int = 3) -> dict:
    """Return the move-card router audit as a pure data object."""
    top_n = max(1, int(top_n))
    atlas_contract = operator_card_atlas_freshness()
    results = [
        _case_result(case, top_n=top_n, semantic_live=semantic_live)
        for case in CASES
    ]
    primary_failures = [
        row["case_id"]
        for row in results
        if not row["expected_primary"]
    ]
    top_n_failures = [
        row["case_id"]
        for row in results
        if not row["expected_in_top_n"]
    ]
    semantic_route_count = sum(1 for row in results if row["route_mode"] == "semantic_atlas")
    semantic_error_count = sum(1 for row in results if row.get("semantic_error"))
    semantic_exercised = bool(semantic_live) and semantic_route_count > 0 and semantic_error_count == 0
    atlas_ok = (not OPERATOR_CARD_ATLAS_PATH.exists()) or bool(atlas_contract.get("fresh"))
    summary = {
        "case_count": len(results),
        "top_n": top_n,
        "mode": "semantic_live" if semantic_live else "deterministic_lexical",
        "semantic_requested": bool(semantic_live),
        "semantic_atlas_exists": OPERATOR_CARD_ATLAS_PATH.exists(),
        "semantic_atlas_status": atlas_contract["status"],
        "semantic_atlas_fresh": bool(atlas_contract["fresh"]),
        "semantic_atlas_expected_count": atlas_contract["expected_count"],
        "semantic_atlas_embedding_count": atlas_contract.get("embedding_count", 0),
        "semantic_atlas_next_command": atlas_contract.get("next_command"),
        "semantic_audit_next_command": "make move-card-router-audit SEMANTIC=1 STRICT=1",
        "semantic_exercised": semantic_exercised,
        "primary_pass_count": len(results) - len(primary_failures),
        "top_n_pass_count": len(results) - len(top_n_failures),
        "primary_failures": primary_failures,
        "top_n_failures": top_n_failures,
        "semantic_route_count": semantic_route_count,
        "semantic_error_count": semantic_error_count,
        "lexical_or_fallback_count": len(results) - semantic_route_count,
        "ok": (
            (not primary_failures and atlas_ok)
            if not semantic_live
            else (
                bool(atlas_contract["fresh"])
                and not top_n_failures
                and semantic_exercised
                and semantic_error_count == 0
            )
        ),
    }
    return {
        "schema": "ztare-move-card-router-audit-v1",
        "summary": summary,
        "semantic_atlas_contract": atlas_contract,
        "cases": results,
        "verdict": {
            "deterministic_router_is_baseline": True,
            "semantic_router_is_advisory": True,
            "release_boundary": (
                "Passing this audit means the fixed paraphrase set routes to the intended cards; "
                "it is not evidence that the move-card taxonomy is complete."
            ),
            "needs_before_stronger_claim": (
                "miss logging, held-out paraphrases, nearest-confuser expectations, and "
                "evidence that routed cards change downstream artifacts or checks"
            ),
        },
    }


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Operator-Card Router Audit",
        "",
        f"Mode: `{summary['mode']}`",
        f"Cases: {summary['case_count']}",
        f"Primary pass: {summary['primary_pass_count']}/{summary['case_count']}",
        f"Top-{summary['top_n']} pass: {summary['top_n_pass_count']}/{summary['case_count']}",
        f"Semantic routes: {summary['semantic_route_count']}/{summary['case_count']}",
        f"Semantic exercised: {summary['semantic_exercised']}",
        f"Semantic atlas: `{summary['semantic_atlas_status']}`",
        f"Semantic live check: `{summary['semantic_audit_next_command']}`",
        "",
        "| Case | Expected | Primary | Rank | Route |",
        "|---|---|---|---:|---|",
    ]
    for row in report["cases"]:
        lines.append(
            f"| {row['case_id']} | {row['expected_card_id']} | "
            f"{row['primary_card_id'] or '-'} | {row['expected_rank'] or '-'} | "
            f"{row['route_mode']} |"
        )
    lines.extend(
        [
            "",
            f"Verdict: {'PASS' if summary['ok'] else 'ATTENTION'}",
            "",
            "Boundary: "
            + report["verdict"]["release_boundary"],
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--semantic-live", action="store_true")
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-misses", type=Path)
    args = parser.parse_args(argv)

    report = build_operator_card_router_audit(
        semantic_live=args.semantic_live,
        top_n=args.top_n,
    )
    if args.write_misses:
        misses = [
            row
            for row in report["cases"]
            if not row["expected_primary"]
            or (args.semantic_live and not row["expected_in_top_n"])
        ]
        args.write_misses.parent.mkdir(parents=True, exist_ok=True)
        args.write_misses.write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in misses) + ("\n" if misses else ""),
            encoding="utf-8",
        )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_markdown(report))

    return 0 if (report["summary"]["ok"] or not args.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
