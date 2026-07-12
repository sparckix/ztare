"""PDE subkernel adapter over LeanMill formal-feedback capabilities.

The PDE kernel owns estimate/currency/operator semantics. LeanMill owns formal
premise retrieval, compiler feedback, proof-loop exits, and proof-credit
boundaries. This module keeps that dependency one-way: PDE callers can request
formal surface context without importing LeanMill internals throughout the
workbench.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class PDEFormalFeedbackCard:
    schema: str
    target: str
    query: str
    formal_surface_status: str
    leanmill_services_used: list[str]
    premise_shelf: dict[str, Any]
    source_counts: dict[str, int]
    skip_reasons: list[str]
    compiler_feedback: dict[str, Any]
    recommended_next_leaf: str
    credit_boundary: str


def _source_counts(shelf: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for hit in shelf.get("hits") or []:
        if not isinstance(hit, dict):
            continue
        source = str(hit.get("source") or "unknown")
        counts[source] = counts.get(source, 0) + 1
    return dict(sorted(counts.items()))


def _status_from_inputs(
    *,
    statement: str,
    compile_result: dict[str, Any] | None,
    typed_exit: dict[str, Any] | None,
) -> str:
    if compile_result and compile_result.get("success") is True:
        return "lean_compile_passed"
    if typed_exit:
        residual = str(typed_exit.get("residual_class") or "")
        if residual == "theorem_or_pde_gap":
            return "formal_gap_reported"
        if str(typed_exit.get("typed_exit_kind") or "") == "unratified_closure_candidate":
            return "unratified_closure_candidate"
        return "leanmill_typed_exit_available"
    if statement.strip():
        return "lean_statement_candidate"
    return "informal_only"


def _next_leaf(status: str, source_counts: dict[str, int]) -> str:
    if status == "lean_compile_passed":
        return "FormalizationLeaf: route compiled artifact through governance/faithfulness checks"
    if status == "formal_gap_reported":
        return "FormalizationLeaf: promote missing lemma obligation from LeanMill typed exit"
    if source_counts:
        return "FormalizationLeaf: attempt Lean statement/proof using premise shelf, then record compiler feedback"
    return "TheoremRetrievalLeaf: retrieve formal premise candidates before Lean editing"


def build_pde_formal_feedback_card(
    *,
    target: str,
    statement: str = "",
    context: str = "",
    source: str = "",
    lean_root: str | Path | None = None,
    compile_result: dict[str, Any] | None = None,
    typed_exit: dict[str, Any] | None = None,
    embedder: Callable[[str], list[float] | None] | None = None,
    top_k_mathlib: int = 8,
    top_k_domain: int = 5,
    top_k_own: int = 4,
    threshold: float = 0.55,
) -> dict[str, Any]:
    """Build one PDE formal-feedback card from LeanMill services.

    The returned card is advisory. It never grants proof credit and never
    decides PDE estimate truth; it only exposes formal retrieval/feedback state
    to PDE leaf agents.
    """
    from ztare.leanmill.semantic_premise_shelf import (
        build_semantic_premise_shelf,
    )

    query = "\n".join(
        part for part in (str(target or ""), str(statement or ""), str(context or ""))
        if part.strip()
    )
    shelf = build_semantic_premise_shelf(
        query,
        top_k_mathlib=top_k_mathlib,
        top_k_ns=top_k_domain,
        top_k_own=top_k_own,
        threshold=threshold,
        include_ns=True,
        embedder=embedder,
        source=source,
        lean_root=lean_root,
    )
    counts = _source_counts(shelf)
    status = _status_from_inputs(
        statement=statement,
        compile_result=compile_result,
        typed_exit=typed_exit,
    )
    compiler_feedback = {
        "compile_result": compile_result or {},
        "typed_exit": typed_exit or {},
    }
    card = PDEFormalFeedbackCard(
        schema="pde-formal-feedback-card-v1",
        target=str(target or ""),
        query=query[:1000],
        formal_surface_status=status,
        leanmill_services_used=[
            "semantic_premise_shelf",
            "own_ledger_recall",
            "mathlib_semantic_neighbours",
            "domain_atlas_semantic_neighbours",
            "typed_exit_contract_if_supplied",
        ],
        premise_shelf=shelf,
        source_counts=counts,
        skip_reasons=[str(x) for x in shelf.get("skip_reasons") or []],
        compiler_feedback=compiler_feedback,
        recommended_next_leaf=_next_leaf(status, counts),
        credit_boundary=(
            "advisory_only_no_proof_credit; PDE truth requires estimate gates, "
            "theorem applicability, work-unit receipts, and Lean/governance checks"
        ),
    )
    return asdict(card)


def render_pde_formal_feedback_card(card: dict[str, Any], *, max_hits: int = 8) -> str:
    """Render a compact human-readable formal feedback card."""
    from ztare.leanmill.semantic_premise_shelf import (
        render_semantic_premise_shelf,
    )

    lines = [
        f"PDE formal feedback: {card.get('target', '')}",
        f"- status: `{card.get('formal_surface_status')}`",
        f"- next leaf: {card.get('recommended_next_leaf')}",
        f"- source counts: {card.get('source_counts', {})}",
        f"- credit boundary: {card.get('credit_boundary')}",
        "",
        render_semantic_premise_shelf(
            card.get("premise_shelf") if isinstance(card.get("premise_shelf"), dict) else {},
            max_hits=max_hits,
        ),
    ]
    return "\n".join(lines)
