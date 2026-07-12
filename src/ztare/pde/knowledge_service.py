"""PDE knowledge-service adapter over LeanMill and project theorem profiles.

This module is the PDE kernel's retrieval/context surface.  It deliberately
does not create a second proof cache, theorem bank, or failure memory:

* LeanMill owns proof cache, no-good/failure memory, and premise shelf recall.
* PDE owns theorem-profile applicability and estimate/currency gate context.
* Project apps own substrate theorem profiles and hostile packets.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from ztare.pde.applicability_cards import applicability_card_retrieval
from ztare.pde.formal_feedback import build_pde_formal_feedback_card


@dataclass(frozen=True)
class PDELeanMillMemorySummary:
    schema: str
    statement_supplied: bool
    proof_cache: dict[str, Any]
    no_good_store: dict[str, Any]
    skip_reasons: list[str]


@dataclass(frozen=True)
class PDEKnowledgeContext:
    schema: str
    target: str
    query: str
    service_boundaries: dict[str, list[str]]
    theorem_profile_cards: list[dict[str, Any]]
    formal_feedback: dict[str, Any] | None
    leanmill_memory: dict[str, Any]
    recommended_leaf_sequence: list[str]
    credit_boundary: str


def _readonly_proof_cache_summary(
    *,
    statement: str,
    path: str | Path | None,
) -> tuple[dict[str, Any], str | None]:
    if not path:
        return {"enabled": False, "hit": False, "stats": {}}, "proof cache path not supplied"
    try:
        from ztare.leanmill.solver.proof_cache import ProofCache

        cache = ProofCache(path)
        return {
            "enabled": True,
            "path": str(path),
            "hit": bool(statement and cache.has(statement)),
            "stats": cache.stats(),
        }, None
    except Exception as exc:  # noqa: BLE001 - advisory service must fail open
        return {
            "enabled": False,
            "path": str(path),
            "hit": False,
            "stats": {},
            "error": f"{type(exc).__name__}: {exc}",
        }, "proof cache unavailable"


def _readonly_no_good_summary(
    *,
    statement: str,
    path: str | Path | None,
    max_matches: int = 4,
) -> tuple[dict[str, Any], str | None]:
    if not path:
        return {"enabled": False, "matches": [], "stats": {}}, "no-good store path not supplied"
    try:
        from ztare.leanmill.solver.no_good_store import NoGoodStore

        store = NoGoodStore(path)
        matches = store.matches(statement) if statement else []
        return {
            "enabled": True,
            "path": str(path),
            "matches": matches[:max(0, max_matches)],
            "n_matches": len(matches),
            "stats": store.stats(),
            "prompt_block_available": bool(matches),
        }, None
    except Exception as exc:  # noqa: BLE001 - advisory service must fail open
        return {
            "enabled": False,
            "path": str(path),
            "matches": [],
            "stats": {},
            "error": f"{type(exc).__name__}: {exc}",
        }, "no-good store unavailable"


def build_leanmill_memory_summary(
    *,
    statement: str = "",
    proof_cache_path: str | Path | None = None,
    no_good_store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return read-only LeanMill proof/failure-memory context for PDE leaves."""
    skip_reasons: list[str] = []
    proof_cache, proof_skip = _readonly_proof_cache_summary(
        statement=statement,
        path=proof_cache_path,
    )
    no_good_store, no_good_skip = _readonly_no_good_summary(
        statement=statement,
        path=no_good_store_path,
    )
    if proof_skip:
        skip_reasons.append(proof_skip)
    if no_good_skip:
        skip_reasons.append(no_good_skip)
    if not statement.strip():
        skip_reasons.append("lean statement not supplied")
    return asdict(PDELeanMillMemorySummary(
        schema="pde-leanmill-memory-summary-v1",
        statement_supplied=bool(statement.strip()),
        proof_cache=proof_cache,
        no_good_store=no_good_store,
        skip_reasons=skip_reasons,
    ))


def _recommended_leaf_sequence(
    *,
    cards: list[dict[str, Any]],
    formal_feedback: dict[str, Any] | None,
    memory: dict[str, Any],
) -> list[str]:
    sequence: list[str] = []
    no_good = memory.get("no_good_store") if isinstance(memory.get("no_good_store"), dict) else {}
    proof_cache = memory.get("proof_cache") if isinstance(memory.get("proof_cache"), dict) else {}
    if no_good.get("n_matches"):
        sequence.append("FailureMemoryLeaf: inspect confirmed LeanMill no-good witnesses first")
    if proof_cache.get("hit"):
        sequence.append("FormalizationLeaf: attempt verified proof-cache reuse under current scope")
    if cards:
        sequence.append("TheoremRetrievalLeaf: run field-level theorem applicability and confuser checks")
    if formal_feedback:
        sequence.append(str(formal_feedback.get("recommended_next_leaf") or "FormalizationLeaf"))
    if not sequence:
        sequence.append("NormalizeLeaf: identify PDE currency, carrier, endpoint, and hostile packet")
    return sequence


def build_pde_knowledge_context(
    *,
    target: str,
    query: str = "",
    theorem_db: dict[str, dict[str, Any]] | None = None,
    available: dict[str, Any] | None = None,
    source_profile: str = "unknown",
    statement: str = "",
    context: str = "",
    source: str = "",
    lean_root: str | Path | None = None,
    proof_cache_path: str | Path | None = None,
    no_good_store_path: str | Path | None = None,
    embedder: Callable[[str], list[float] | None] | None = None,
    top_k_cards: int = 8,
    top_k_mathlib: int = 0,
    top_k_domain: int = 0,
    top_k_own: int = 0,
    threshold: float = 0.55,
) -> dict[str, Any]:
    """Build one retrieval/failure-memory context for a PDE leaf agent.

    The context is advisory.  It routes work; it never grants proof or estimate
    credit.
    """
    q = query or target
    cards = applicability_card_retrieval(
        theorem_db or {},
        query=q,
        available=available or {},
        source_profile=source_profile,
        top_k=top_k_cards,
    ) if theorem_db else []
    formal_feedback = None
    if top_k_mathlib > 0 or top_k_domain > 0 or top_k_own > 0 or source or lean_root:
        formal_feedback = build_pde_formal_feedback_card(
            target=target,
            statement=statement,
            context=context or q,
            source=source,
            lean_root=lean_root,
            embedder=embedder,
            top_k_mathlib=top_k_mathlib,
            top_k_domain=top_k_domain,
            top_k_own=top_k_own,
            threshold=threshold,
        )
    memory = build_leanmill_memory_summary(
        statement=statement,
        proof_cache_path=proof_cache_path,
        no_good_store_path=no_good_store_path,
    )
    return asdict(PDEKnowledgeContext(
        schema="pde-knowledge-context-v1",
        target=str(target or ""),
        query=str(q or ""),
        service_boundaries={
            "pde_kernel": [
                "theorem applicability cards",
                "estimate/currency/operator gate routing",
                "leaf work-order context",
            ],
            "leanmill_service": [
                "semantic premise shelf",
                "verified proof cache",
                "confirmed no-good/failure memory",
                "compiler and typed-exit feedback",
            ],
            "project_app": [
                "theorem profiles",
                "hostile packets",
                "formal-surface records",
            ],
        },
        theorem_profile_cards=cards,
        formal_feedback=formal_feedback,
        leanmill_memory=memory,
        recommended_leaf_sequence=_recommended_leaf_sequence(
            cards=cards,
            formal_feedback=formal_feedback,
            memory=memory,
        ),
        credit_boundary=(
            "advisory_retrieval_only; PDE estimate credit still requires "
            "gate receipts, theorem applicability, hostile-packet survival, "
            "work-unit validation, and Lean/governance where formalized"
        ),
    ))
