"""Research Director tick-start primitive discoverability surface.

The architecture index is the source of truth. This module turns that flat
index into a small, problem-aware briefing so a cold RD session can see
available CAS, PDE, graph, Lagrangian, and cognitive primitives before it
starts free-recalling tools.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
ARCH_INDEX = REPO / "analytics" / "public" / "index" / "architecture_index.jsonl"
GRAPH_PATH = REPO / "src" / "ztare" / "architecture_index" / "graph.yaml"
OUT_PATH = REPO / "analytics" / "public" / "queries" / "rd_tick_primitive_surface.json"

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
    "lagrangian_path_b",
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
    "lagrangian_path_b": [
        "lagrangian",
        "lagrangian_path_b",
        "variational_principle",
        "noether_check",
        "physics_substrate",
        "path_b",
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
    terms = query_terms or DEFAULT_QUERY_TERMS
    exclusions = excluded_terms or []
    rows, warnings = _load_rows()
    graph_bonus, graph_warnings = _load_graph_bonus()
    warnings.extend(graph_warnings)
    hits: list[PrimitiveHit] = []
    for row in rows:
        if exclusions and _matches(row, exclusions):
            continue
        score, matched, buckets = _score(row, terms)
        if not matched and not buckets:
            continue
        bonus = graph_bonus.get(str(row.get("id", "")), 0.0)
        score += bonus
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

    return PrimitiveTickSurface(
        query_terms=terms,
        total_index_rows=len(rows),
        top_hits=hits[:top_n],
        buckets=bucketed,
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
        "  top primitives for this tick:",
    ]
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
