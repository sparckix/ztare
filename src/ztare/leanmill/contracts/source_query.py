"""Typed source-query contract for LeanMill source qualification.

This is the source-search boundary, not proof governance. It accepts
bounded declaration references and theorem-shape search requests, rejects
process text, and emits enough telemetry for recovery and prompt repair.
Lean/name-resolution and proof-state checks remain downstream gates.

Phase A migration (2026-05-23): canonical home moved here from
``scripts/public/control/leanmill/source_query_contract.py``. That script
keeps a shim re-export so existing imports keep working.
"""
from __future__ import annotations

import json  # noqa: F401  (preserved for symmetry with prior module surface)
import re
from typing import Any


PROCESS_FRAGMENTS = {
    "source_to_intake",
    "source-to-intake",
    "source_safety_status",
    "row_context_ready",
    "target-context-ready",
    "candidate generation",
    "request source code",
    "needed to advance",
    "source artifact",
    "source proof",
    "source safety",
    "intake rows",
    "valid_source_candidates",
    "proof_credit",
    "governance_gate",
    "leanmill",
    "negative_control",
    "negative control",
    "shape adapter",
    "direct apply",
    "kernel goal",
    "probe with",
    "scoreboard",
    "station",
    "receipt",
    "exclusion_count",
}

GENERIC_TOKENS = {
    "and", "the", "for", "with", "source", "candidate", "family", "planner",
    "repair", "valid", "safe", "rows", "row", "intake", "proof", "search",
    "query", "find", "needed", "advance", "route", "check", "control",
}

LEAN_SYMBOLS = {"≤", "≥", "↔", "∑", "∫", "∀", "∃", "→", "⊢", "∈", "=", "<", ">"}
LEAN_SHAPE_TOKENS = {
    "tendsto", "summable", "hassum", "lintegral", "integral", "convolution",
    "spectrum", "rayleigh", "cauchy", "causeq", "cusp", "qparam", "ennreal",
    "nnreal", "norm", "coercion", "iff", "linearindependent", "gram",
    "posdef", "zpow", "filter", "measure", "periodic", "differentiable",
    "continuous", "measurable", "hasderiv", "covering", "tsum", "series",
}

DECL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)+$")
LEAN_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*$")
DECL_IN_STATEMENT_RE = re.compile(r"\b(?:theorem|lemma|def)\s+([A-Za-z_][A-Za-z0-9_'.]*)")


def _compact(text: Any) -> str:
    return " ".join(str(text or "").split())


def _tokens(text: str) -> set[str]:
    return {
        t.lower()
        for t in re.findall(r"[A-Za-z][A-Za-z0-9_']+|[≤≥↔∑∫∀∃→⊢∈=<>]", text)
        if len(t) >= 1
    }


def _decl_name(text: str) -> str:
    q = _compact(text)
    match = DECL_IN_STATEMENT_RE.search(q)
    if match:
        return match.group(1)
    return q if DECL_RE.match(q) or LEAN_IDENT_RE.match(q) else ""


def _lean_identifier_decl(text: str) -> bool:
    q = _compact(text)
    if not LEAN_IDENT_RE.match(q):
        return False
    lower = q.lower()
    if lower in GENERIC_TOKENS or lower in PROCESS_FRAGMENTS:
        return False
    return "_" in q or any(ch.isupper() for ch in q) or "'" in q


def _infer_kind(query: str, obj: dict[str, Any] | None = None) -> str:
    if obj and str(obj.get("kind") or ""):
        return str(obj.get("kind"))
    if any(sym in query for sym in LEAN_SYMBOLS) or DECL_IN_STATEMENT_RE.search(query):
        return "theorem_shape"
    if _decl_name(query):
        return "declaration_ref"
    return "semantic_search"


def _first_nonempty(*values: Any) -> Any:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
        if value not in (None, "", [], {}):
            return value
    return ""


def _raw_query_value(obj: dict[str, Any], item: Any) -> Any:
    raw = obj.get("query")
    if isinstance(raw, dict):
        return _first_nonempty(
            raw.get("decl_name"),
            raw.get("query"),
            raw.get("statement"),
            raw.get("theorem_shape"),
            raw.get("text"),
        )
    return _first_nonempty(raw, obj.get("decl_name"), obj.get("statement"), obj.get("theorem_shape"), item)


def normalize_query_contract(item: Any, *, family: str = "") -> dict[str, Any]:
    """Return a normalized query contract.

    Accepted input:
    - string: legacy source query, normalized into a typed contract.
    - object: {kind, query|decl_name|statement, rationale?, required_shape?}.
    """
    obj = item if isinstance(item, dict) else {}
    raw = _raw_query_value(obj, item)
    query = _compact(raw)[:500]
    kind = _infer_kind(query, obj)
    return {
        "schema": "leanmill-source-query-contract-v1",
        "kind": kind,
        "query": query,
        "decl_name": _decl_name(query),
        "family": family,
        "rationale": _compact(obj.get("rationale") or "")[:300],
        "required_shape": obj.get("required_shape") if isinstance(obj.get("required_shape"), dict) else {},
    }


def compact_query_item(item: Any) -> Any:
    """Return a bounded typed query item, preserving structured query objects."""
    if isinstance(item, dict):
        out: dict[str, Any] = {}
        for key in ("schema", "kind", "query", "decl_name", "statement", "theorem_shape", "rationale", "required_shape"):
            if key not in item:
                continue
            value = item.get(key)
            out[key] = _compact(value)[:500] if isinstance(value, str) else value
        contract = normalize_query_contract(out, family="")
        text = str(contract.get("query") or "").strip()
        return out if text else None
    text = _compact(item)[:500]
    return text if text else None


def query_identity(item: Any) -> str:
    contract = normalize_query_contract(item, family="")
    return str(contract.get("decl_name") or contract.get("query") or "").strip()


def source_queries_from_proposal(obj: dict[str, Any], *, allow_hypothesis_fallback: bool = False) -> list[Any]:
    raw = obj.get("source_query") or obj.get("source_queries") or obj.get("queries") or []
    if isinstance(raw, str):
        raw = [raw]
    queries: list[Any] = []
    if isinstance(raw, list):
        for item in raw:
            query = compact_query_item(item)
            if query:
                queries.append(query)
    if allow_hypothesis_fallback and not queries:
        for key in ("hypothesis", "formal_statement", "gap_statement"):
            query = compact_query_item(obj.get(key))
            if query:
                queries.append(query)
                break
    out: list[Any] = []
    seen: set[str] = set()
    for query in queries:
        ident = query_identity(query)
        if ident and ident not in seen:
            seen.add(ident)
            out.append(query)
    return out[:8]


def query_quality(item: Any, family: str = "") -> dict[str, Any]:
    contract = normalize_query_contract(item, family=family)
    query = contract["query"]
    lower = query.lower()
    failures: list[str] = []
    early_decl = _decl_name(query)
    if len(query) < 8 and not _lean_identifier_decl(early_decl):
        failures.append("too_short")
    if len(query) > 260 and contract["kind"] != "theorem_shape":
        failures.append("too_long")
    bad = sorted(frag for frag in PROCESS_FRAGMENTS if frag in lower)
    if bad:
        failures.append("process_or_control_language:" + ",".join(bad))

    toks = _tokens(query)
    decl = contract["decl_name"]
    dotted_decl = bool(decl and DECL_RE.match(decl))
    lean_identifier_decl = bool(decl and _lean_identifier_decl(decl))
    symbol_count = sum(1 for s in LEAN_SYMBOLS if s in query)
    lean_shape_hits = sorted(t for t in toks if t in LEAN_SHAPE_TOKENS)
    camel_or_namespaced = [
        t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_'.]*", query)
        if "." in t or "_" in t or any(ch.isupper() for ch in t)
    ]
    structural_signal_count = (
        (1 if dotted_decl else 0)
        + min(2, symbol_count)
        + min(3, len(lean_shape_hits))
        + min(2, len(camel_or_namespaced))
    )

    kind = contract["kind"]
    if kind == "declaration_ref":
        if not (dotted_decl or lean_identifier_decl):
            failures.append("declaration_ref_requires_lean_decl_name")
    elif kind == "theorem_shape":
        if structural_signal_count < 3:
            failures.append("theorem_shape_requires_structural_lean_signals")
    elif kind == "semantic_search":
        meaningful = [t for t in toks if t not in GENERIC_TOKENS and t not in LEAN_SYMBOLS]
        if structural_signal_count < 2 or len(meaningful) < 3:
            failures.append("semantic_search_requires_math_structure")
    else:
        failures.append("invalid_query_kind")

    return {
        "query": query,
        "normalized_query": decl or query,
        "query_kind": kind,
        "accepted": not failures,
        "failures": failures,
        "decl_name": decl,
        "lean_identifier_decl": lean_identifier_decl,
        "lean_shape_hits": lean_shape_hits,
        "structural_signal_count": structural_signal_count,
        "contract": contract,
    }


def queries_pass_gate(queries: list[Any], family: str = "") -> tuple[bool, list[dict[str, Any]]]:
    quality = [query_quality(q, family) for q in queries if _compact(q)]
    return (bool(quality) and all(q["accepted"] for q in quality), quality)


def accepted_queries(query_quality_items: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for item in query_quality_items:
        if not isinstance(item, dict) or not bool(item.get("accepted")):
            continue
        query = str(item.get("normalized_query") or item.get("query") or "").strip()
        if query and query not in out:
            out.append(query)
    return out


__all__ = [
    "PROCESS_FRAGMENTS",
    "GENERIC_TOKENS",
    "LEAN_SYMBOLS",
    "LEAN_SHAPE_TOKENS",
    "DECL_RE",
    "LEAN_IDENT_RE",
    "DECL_IN_STATEMENT_RE",
    "normalize_query_contract",
    "compact_query_item",
    "query_identity",
    "source_queries_from_proposal",
    "query_quality",
    "queries_pass_gate",
    "accepted_queries",
]


def _self_test() -> int:
    assert query_quality("source_to_intake_receipt.exact_target_exclusion_count = 0", "fam")["accepted"] is False
    assert query_quality("Matrix.PosDef.gram", "gram_posdef_linear_independent_planner")["accepted"]
    assert query_quality({"kind": "declaration_ref", "decl_name": "HasSum"}, "lpnorm_hasSum_packaging_planner")["accepted"]
    assert query_quality({"kind": "declaration_ref", "query": {"decl_name": "NNReal.tsum_coe"}}, "ennreal_tsum_condensation_planner")["accepted"]
    assert query_quality({"kind": "theorem_shape", "query": {"statement": "lemma tendsto_norm_exp {x : ℝ} : Tendsto (fun n : ℕ => ‖Real.exp x‖) atTop atTop"}}, "qparam_tendsto_norm_exp_planner")["accepted"]
    assert query_quality({"kind": "declaration_ref", "decl_name": "tsum_eq"}, "lpnorm_hasSum_packaging_planner")["accepted"]
    nested = source_queries_from_proposal({
        "source_query": [
            {"kind": "declaration_ref", "query": {"decl_name": "ENNReal.coe_tsum"}},
            {"kind": "declaration_ref", "query": {"decl_name": "ENNReal.coe_tsum"}},
            {"kind": "declaration_ref", "query": {"decl_name": "Filter.Tendsto.comp"}},
        ],
    })
    assert [query_identity(q) for q in nested] == ["ENNReal.coe_tsum", "Filter.Tendsto.comp"]
    assert not query_quality({"kind": "declaration_ref", "decl_name": "proof"}, "fam")["accepted"]
    assert query_quality("theorem sum_Ioc_inv_sq_le_sub {k n : ℕ} : ∑ i ∈ Ioc k n, (↑i ^ 2)⁻¹ ≤ (↑k)⁻¹ - (↑n)⁻¹", "interval_alignment_planner")["accepted"]
    assert not query_quality("shape adapter construction for retrying direct apply", "source_action_shape_planner")["accepted"]
    ok, quality = queries_pass_gate(["ENNReal.coe_tsum", "ENNReal.le_tsum"], "ennreal_tsum_condensation_planner")
    assert ok and accepted_queries(quality) == ["ENNReal.coe_tsum", "ENNReal.le_tsum"]
    print("ztare.leanmill.contracts.source_query self-test PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())
