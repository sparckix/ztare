"""Research Director tick-start primitive discoverability surface.

The architecture index is the source of truth. This module turns that flat
index into a small, problem-aware briefing so a cold RD session can see
available CAS, PDE, graph, Lagrangian, and cognitive primitives before it
starts free-recalling tools.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
ARCH_INDEX = REPO / "analytics" / "public" / "index" / "architecture_index.jsonl"
GRAPH_PATH = REPO / "src" / "ztare" / "architecture_index" / "graph.yaml"
OUT_PATH = REPO / "analytics" / "public" / "queries" / "rd_tick_primitive_surface.json"

_QUERY_STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "and",
    "another",
    "before",
    "being",
    "between",
    "could",
    "current",
    "does",
    "for",
    "from",
    "has",
    "have",
    "into",
    "itself",
    "little",
    "more",
    "need",
    "needs",
    "next",
    "only",
    "same",
    "several",
    "should",
    "show",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "what",
    "when",
    "where",
    "whether",
    "with",
    "would",
}


def expand_query_terms(query_terms: list[str] | tuple[str, ...]) -> list[str]:
    """Expand natural RD task text into stable lexical retrieval terms.

    The semantic atlas can consume full prose, but catalog/worker parent-node
    ranking also uses deterministic substring matches. This keeps natural
    operator/RD brief text usable without replacing the semantic retrieval path.
    """
    out: list[str] = []

    def add(term: str) -> None:
        norm = term.strip().lower()
        if not norm or norm in _QUERY_STOPWORDS:
            return
        if norm not in out:
            out.append(norm)

    for raw in query_terms:
        text = str(raw or "").strip()
        if not text:
            continue
        lower = text.lower()
        add(lower)
        if "_" in lower:
            add(lower.replace("_", " "))
        if " " in lower:
            add(lower.replace(" ", "_"))
        tokens = [
            token
            for token in re.findall(r"[a-zA-Z0-9_]+", lower)
            if len(token) >= 3 and token not in _QUERY_STOPWORDS
        ]
        for token in tokens:
            add(token)
            if "_" in token:
                add(token.replace("_", " "))
        for left, right in zip(tokens, tokens[1:]):
            phrase = f"{left} {right}"
            add(phrase)
            add(phrase.replace(" ", "_"))
    return out


DEFAULT_QUERY_TERMS = [
    "NS_track_b",
    "PDE_estimate",
    "harmonic_analysis",
    "lean_substrate",
    "proof_compile_check",
    "pre_lean_preflight",
    "dimensional_check",
    "endpoint_check",
    "CAS_verification",
    "sympy",
    "variational_lagrangian",
    "variational_principle",
    "inversion",
    "anti_anchoring",
    "framer",
    "stagnation",
    "cold_start",
    "graph_mining",
        "closure_attempt",
        "typed_endpoint",
        "gowers_first",
        "formalization_sequence",
        "theorem_surface",
    "carrier_observable",
    "source_selection",
    "nonadaptive",
    "no_post_hoc",
    "stopping_time",
    "same_carrier",
    "fresh_capacity",
    "no_reuse",
    "packing",
    "injection",
        "bundle",
        "bundling",
    "bundle_discriminator_stack",
    "gate_compression",
    "discriminator_stack",
    "artifact_to_gate",
    "lane_compression",
    "pull_forward",
    "meta_darwin",
    "darwin_idea_killer",
    "kill_agent",
    "excitement_trigger",
    "promotion_gate",
    "strong_signal",
    "null_form",
    "signed_cancellation",
    "positive_source_square",
    "symbol_audit",
]

SCOPE_QUERY_TERMS = {
    "neural_hunt": [
        "neural_hunt",
        "scaling",
        "scaling_law",
        "checkpoint",
        "eval",
        "validation",
        "source_packet",
        "source_admissibility",
        "leakage",
        "observability",
        "signal",
        "noise",
        "baseline",
        "residual",
        "residual_void",
        "negative_space",
        "negative_result",
        "response_mode",
        "mode_flow",
        "state_variable",
        "law_gate",
        "falsifiability_check",
        "data_diagnostic",
        "pre_fit_briefing",
        "champion_scope",
        "extrapolation_warning",
        "graph",
        "graph_mining",
        "capability_index",
        "substrate_audit",
        "anti_anchoring",
        "de_anchor",
        "inversion",
        "bundle",
        "gate_compression",
        "discriminator_stack",
        "lane_compression",
        "pull_forward",
        "meta_darwin",
        "darwin_idea_killer",
        "kill_agent",
        "excitement_trigger",
        "promotion_gate",
        "strong_signal",
    ],
    "ns": [
        "NS_track_b",
        "PDE_estimate",
        "harmonic_analysis",
        "lean_substrate",
        "proof_compile_check",
        "pre_lean_preflight",
        "dimensional_check",
        "endpoint_check",
        "CAS_verification",
        "sympy",
        "graph_mining",
        "closure_attempt",
        "typed_endpoint",
        "gowers_first",
        "formalization_sequence",
        "theorem_surface",
        "carrier_observable",
        "source_selection",
        "nonadaptive",
        "no_post_hoc",
        "stopping_time",
        "same_carrier",
        "fresh_capacity",
        "no_reuse",
        "packing",
        "injection",
        "single_spend",
        "phase_space",
        "packet_ownership",
        "owner_map",
        "owner_preimage",
        "event_prefix_budget",
        "bounded_multiplicity",
        "null_form",
        "signed_cancellation",
        "positive_source_square",
        "symbol_audit",
    ],
}

SCOPE_EXCLUDED_TERMS = {
    "neural_hunt": [
        "NS_track_b",
        "PDE_estimate",
        "harmonic_analysis",
        "lean_substrate",
        "proof_compile_check",
        "CAS_verification",
        "sympy",
        "typed_endpoint",
        "critical_increment",
    ],
}

BUCKET_TERMS = {
    "pde_ns_lean": [
        "PDE_estimate",
        "NS_track_b",
        "harmonic_analysis",
        "lean_substrate",
        "pre_lean_preflight",
        "endpoint_check",
        "limit_passage",
        "threshold_dichotomy",
        "gowers_first",
        "formalization_sequence",
        "theorem_surface",
        "carrier_observable",
        "source_selection",
        "nonadaptive",
        "no_post_hoc",
        "stopping_time",
        "fresh_capacity",
        "same_carrier",
        "no_reuse",
        "packing",
        "injection",
        "single_spend",
        "phase_space",
        "packet_ownership",
        "owner_map",
        "owner_preimage",
        "event_prefix_budget",
        "bounded_multiplicity",
        "null_form",
        "signed_cancellation",
        "positive_source_square",
        "symbol_audit",
    ],
    "sympy_cas": [
        "sympy",
        "CAS",
        "CAS_verification",
        "symbolic_check",
        "inequality_verification",
        "dimensional_check",
        "endpoint_check",
    ],
    "graph_mining": [
        "graph",
        "graph_mining",
        "closure_attempt",
        "reference_audit",
        "capability_index",
        "typed_endpoint",
        "leverage_audit",
    ],
    "variational_lagrangian": [
        "lagrangian",
        "lagrangian_derivation",
        "variational_principle",
        "noether_check",
        "physics_substrate",
        "action_principle",
    ],
    "cognitive_reframe": [
        "inversion",
        "anti_anchoring",
        "de_anchor",
        "reframe",
        "framer",
        "cold_start",
        "analogy",
        "stagnation",
        "skeptic_cycle",
        "cross_domain_transfer",
    ],
    "negative_to_object": [
        "negative_result",
        "negative_space",
        "residual",
        "residual_void",
        "state_variable",
        "response_mode",
        "mode_flow",
        "de_anchor",
        "reframe",
    ],
    "orchestration_compression": [
        "bundle",
        "bundling",
        "bundle_discriminator_stack",
        "gate_compression",
        "discriminator_stack",
        "artifact_to_gate",
        "lane_compression",
        "pull_forward",
        "staged_runner",
        "meta_darwin",
        "darwin_idea_killer",
        "kill_agent",
        "excitement_trigger",
        "promotion_gate",
        "strong_signal",
    ],
}

PREFERRED_KINDS = {
    "gate",
    "mining",
    "op",
    "orchestrator",
    "pattern",
    "primitive",
    "reflexive_primitive",
    "script",
    "validator",
}


def query_terms_for_scope(scope: str | None) -> list[str]:
    if not scope:
        return DEFAULT_QUERY_TERMS
    norm = "".join(ch.lower() if ch.isalnum() else "_" for ch in scope).strip("_")
    for key, terms in SCOPE_QUERY_TERMS.items():
        if key in norm:
            return terms
    return DEFAULT_QUERY_TERMS


def excluded_terms_for_scope(scope: str | None) -> list[str]:
    if not scope:
        return []
    norm = "".join(ch.lower() if ch.isalnum() else "_" for ch in scope).strip("_")
    for key, terms in SCOPE_EXCLUDED_TERMS.items():
        if key in norm:
            return terms
    return []


@dataclass(frozen=True)
class PrimitiveHit:
    id: str
    path: str
    kind: str
    score: float
    impact_factor_expost: float
    last_used: str
    matched_terms: list[str] = field(default_factory=list)
    buckets: list[str] = field(default_factory=list)
    description: str = ""
    why: str = ""


@dataclass
class PrimitiveTickSurface:
    query_terms: list[str]
    total_index_rows: int
    top_hits: list[PrimitiveHit]
    buckets: dict[str, list[PrimitiveHit]]
    parent_nodes: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.top_hits) and not any(w.startswith("ERROR:") for w in self.warnings)


def _load_rows(path: Path = ARCH_INDEX) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    if not path.exists():
        return rows, [f"ERROR: architecture index missing: {path}"]
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            warnings.append(f"malformed architecture index row {lineno}: {exc}")
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows, warnings


def _load_graph_bonus(path: Path = GRAPH_PATH) -> tuple[dict[str, float], list[str]]:
    if not path.exists():
        return {}, []
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}, ["graph bonus unavailable: pyyaml not installed"]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return {}, [f"graph bonus unavailable: {exc}"]
    bonuses: dict[str, float] = {}
    for edge in data.get("edges", []):
        if not isinstance(edge, dict):
            continue
        capability = edge.get("capability")
        if not isinstance(capability, str):
            continue
        bonus = 0.0
        surfaced = edge.get("surfaced_catch") or []
        discharges = edge.get("discharges_seam") or []
        advances = edge.get("advances_okr") or []
        operates = edge.get("operates_on_gp") or []
        composes = edge.get("composes_with") or []
        if isinstance(surfaced, list):
            bonus += min(len(surfaced), 3) * 1.0
        if isinstance(discharges, list) and discharges:
            bonus += 1.0
        if isinstance(advances, list) and advances:
            bonus += 0.5
        if isinstance(operates, list) and operates:
            bonus += 0.5
        if isinstance(composes, list):
            bonus += min(len(composes), 4) * 0.25
        if bonus > 0:
            bonuses[capability] = bonus
    return bonuses, []


def _haystack(row: dict[str, Any]) -> str:
    parts = [
        row.get("id", ""),
        row.get("path", ""),
        row.get("kind", ""),
        row.get("description", ""),
    ]
    for key in ("applicability", "dependencies"):
        value = row.get(key, [])
        if isinstance(value, list):
            parts.extend(str(v) for v in value)
        else:
            parts.append(str(value))
    return " ".join(str(p) for p in parts).lower()


def _matches(row: dict[str, Any], terms: list[str]) -> list[str]:
    hay = _haystack(row)
    return [term for term in terms if term.lower() in hay]


def _buckets(row: dict[str, Any]) -> list[str]:
    hits = []
    for bucket, terms in BUCKET_TERMS.items():
        if _matches(row, terms):
            hits.append(bucket)
    return hits


def _impact(row: dict[str, Any]) -> float:
    try:
        return float(row.get("impact_factor_expost", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _recency_bonus(last_used: str) -> float:
    if not last_used or last_used == "never":
        return 0.0
    try:
        used = date.fromisoformat(last_used)
    except ValueError:
        return 0.0
    days = (date.today() - used).days
    if days <= 14:
        return 3.0
    if days <= 30:
        return 1.5
    return 0.0


def _score(row: dict[str, Any], query_terms: list[str]) -> tuple[float, list[str], list[str]]:
    matched = _matches(row, query_terms)
    buckets = _buckets(row)
    kind = str(row.get("kind", "")).lower()
    score = 10.0 * _impact(row)
    score += 8.0 * len(matched)
    score += 6.0 * len(buckets)
    if kind in PREFERRED_KINDS:
        score += 4.0
    score += _recency_bonus(str(row.get("last_used", "")))
    return score, matched, buckets


def build_primitive_tick_surface(
    *,
    query_terms: list[str] | None = None,
    excluded_terms: list[str] | None = None,
    top_n: int = 12,
    per_bucket: int = 4,
) -> PrimitiveTickSurface:
    terms = expand_query_terms(query_terms or DEFAULT_QUERY_TERMS)
    exclusions = excluded_terms or []
    rows, warnings = _load_rows()
    graph_bonus, graph_warnings = _load_graph_bonus()
    warnings.extend(graph_warnings)
    try:
        from src.ztare.research_director.primitive_amnesia import atlas_freshness_status
        atlas_status = atlas_freshness_status()
        if not atlas_status.ok:
            warnings.append("primitive atlas stale: " + "; ".join(atlas_status.warnings[:3]))
    except Exception as exc:
        warnings.append(f"primitive atlas freshness check unavailable: {type(exc).__name__}: {str(exc)[:120]}")
    # ONE retrieval engine (2026-06-01): rank via the SEMANTIC atlas
    # (`primitive_amnesia`, vocabulary-invariant; measure current recall with
    # `python -m ztare.research_director.primitive_amnesia --eval`) using the
    # scope terms as the query — instead of this module's old lexical `_score`. The
    # lexical `_matches` is kept ONLY for bucketing/display + the skip filter, not for
    # ranking. Falls back to lexical ranking when no atlas/embedder is available.
    sem_scores: dict[str, float] = {}
    try:
        from src.ztare.research_director.primitive_amnesia import precheck as _amnesia_precheck
        q = " ".join(terms)
        for h in _amnesia_precheck(q, top_k=max(len(rows), 1)):
            sem_scores[str(h.get("name") or h.get("signature"))] = float(h.get("score") or 0.0)
    except Exception:
        sem_scores = {}
    hits: list[PrimitiveHit] = []
    for row in rows:
        if exclusions and _matches(row, exclusions):
            continue
        lex_score, matched, buckets = _score(row, terms)
        sem = sem_scores.get(str(row.get("id", "")), 0.0)
        if sem <= 0 and not matched and not buckets:
            continue
        bonus = graph_bonus.get(str(row.get("id", "")), 0.0)
        # Semantic relevance DOMINATES (to milli-cosine precision); impact/graph/lexical
        # only break ties WITHIN the same relevance band. This keeps high-graph-bonus
        # primitives from drowning the actually-relevant ones (parameter-free, no magic
        # weight). Lexical fallback when no atlas/embedder.
        priors = bonus + lex_score + _impact(row) * 0.1
        score = (round(sem, 3) * 1000 + priors) if sem_scores else (lex_score + bonus)
        desc = str(row.get("description", "") or "")
        why_parts = []
        if matched:
            why_parts.append("matched " + ", ".join(matched[:5]))
        if buckets:
            why_parts.append("bucket " + ", ".join(buckets))
        if _impact(row):
            why_parts.append(f"impact {_impact(row):g}")
        if bonus > 0:
            why_parts.append(f"graph_bonus {bonus:g}")
        hits.append(
            PrimitiveHit(
                id=str(row.get("id", "UNKNOWN")),
                path=str(row.get("path", "")),
                kind=str(row.get("kind", "")),
                score=round(score, 2),
                impact_factor_expost=_impact(row),
                last_used=str(row.get("last_used", "unknown")),
                matched_terms=matched,
                buckets=buckets,
                description=desc[:220],
                why="; ".join(why_parts),
            )
        )
    hits.sort(key=lambda h: (-h.score, h.id))

    bucketed: dict[str, list[PrimitiveHit]] = {}
    for bucket in BUCKET_TERMS:
        bucket_hits = [hit for hit in hits if bucket in hit.buckets]
        bucketed[bucket] = bucket_hits[:per_bucket]

    parent_node_payloads: list[dict[str, Any]] = []
    try:
        from src.ztare.research_director.primitive_catalog_taxonomy import catalog_parent_nodes
        from src.ztare.research_director.primitive_family_registry import parent_nodes

        parent_node_payloads = [
            {**asdict(node), "scope": "catalog"}
            for node in catalog_parent_nodes(rows, terms)
        ]
        parent_node_payloads.extend(
            {**asdict(node), "scope": "llm_mediated"}
            for node in parent_nodes(terms)
        )
    except Exception as exc:
        warnings.append(f"primitive parent nodes unavailable: {type(exc).__name__}: {str(exc)[:120]}")

    return PrimitiveTickSurface(
        query_terms=terms,
        total_index_rows=len(rows),
        top_hits=hits[:top_n],
        buckets=bucketed,
        parent_nodes=parent_node_payloads,
        warnings=warnings,
    )


def write_primitive_tick_surface(
    path: Path = OUT_PATH,
    *,
    query_terms: list[str] | None = None,
    excluded_terms: list[str] | None = None,
    top_n: int = 12,
    per_bucket: int = 4,
) -> PrimitiveTickSurface:
    surface = build_primitive_tick_surface(
        query_terms=query_terms,
        excluded_terms=excluded_terms,
        top_n=top_n,
        per_bucket=per_bucket,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": surface.ok,
        "query_terms": surface.query_terms,
        "total_index_rows": surface.total_index_rows,
        "top_hits": [asdict(hit) for hit in surface.top_hits],
        "buckets": {
            name: [asdict(hit) for hit in hits]
            for name, hits in surface.buckets.items()
        },
        "parent_nodes": surface.parent_nodes,
        "warnings": surface.warnings,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return surface


def render_text(surface: PrimitiveTickSurface) -> str:
    lines = [
        f"  primitive_surface_ok = {surface.ok}",
        f"  architecture index rows scanned: {surface.total_index_rows}",
        "  evidence discipline:",
        "    primitive hits are recall/checklist candidates, not solver evidence;",
        "    select a small candidate set, name the nearest confuser, then",
        "    use the chosen hit only by converting it into action-constraint receipt fields,",
        "    infer the action target from source facts rather than task/check-menu wording,",
        "    a gate, artifact, falsifier, repair rule, or explicit why_not.",
        "  catalog parent nodes:",
    ]
    catalog_nodes = [node for node in surface.parent_nodes if node.get("scope") == "catalog"]
    worker_nodes = [node for node in surface.parent_nodes if node.get("scope") == "llm_mediated"]
    for node in catalog_nodes[:4]:
        matched_terms = node.get("matched_terms", [])
        if isinstance(matched_terms, (list, tuple)):
            matched = ", ".join(str(term) for term in matched_terms[:5]) or "no query match"
        else:
            matched = "no query match"
        lines.append(
            f"    - {node.get('family_id')} ({node.get('child_count')} children): {matched}"
        )
        purpose = str(node.get("purpose") or "")
        if purpose:
            lines.append(f"      {purpose}")
        examples = node.get("child_primitives", [])
        if not isinstance(examples, (list, tuple)) or not examples:
            examples = node.get("example_ids", [])
        if isinstance(examples, (list, tuple)) and examples:
            lines.append("      examples: " + ", ".join(str(item) for item in examples[:5]))
    lines.append("  worker family nodes:")
    for node in worker_nodes[:4]:
        matched_terms = node.get("matched_terms", [])
        if isinstance(matched_terms, (list, tuple)):
            matched = ", ".join(str(term) for term in matched_terms[:5]) or "no query match"
        else:
            matched = "no query match"
        lines.append(
            f"    - {node.get('family_id')} ({node.get('child_count')} children): {matched}"
        )
        purpose = str(node.get("purpose") or "")
        if purpose:
            lines.append(f"      {purpose}")
        examples = node.get("child_primitives", [])
        if isinstance(examples, (list, tuple)) and examples:
            lines.append("      examples: " + ", ".join(str(item) for item in examples[:5]))
    lines.append("  top primitives for this tick:")
    for hit in surface.top_hits[:10]:
        lines.append(f"    - {hit.id} [{hit.kind}] score={hit.score:g}")
        lines.append(f"      {hit.path}")
        if hit.why:
            lines.append(f"      {hit.why}")
    lines.append("  bucket coverage:")
    for bucket, hits in surface.buckets.items():
        rendered = ", ".join(hit.id for hit in hits[:3]) or "(none)"
        lines.append(f"    - {bucket}: {rendered}")
    for warning in surface.warnings:
        lines.append(f"  WARNING: {warning}")
    return "\n".join(lines)
