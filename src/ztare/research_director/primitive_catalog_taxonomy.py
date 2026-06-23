"""Generated-catalog taxonomy and health checks for primitive surfacing.

The architecture index remains the source catalog. This module provides derived
metadata over that catalog: one source category (where the capability lives) and
one semantic family (what research move it serves). The rows do not need to be
hand-reorganized to get a navigable family graph.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[3]
ARCH_INDEX = REPO / "analytics" / "public" / "index" / "architecture_index.jsonl"
ATLAS_PATH = REPO / "analytics" / "public" / "index" / "primitive_atlas_embeddings.json"
INDEX_MD = REPO / "src" / "ztare" / "architecture_index" / "INDEX.md"


SOURCE_CATEGORY_BY_PREFIX: tuple[tuple[str, str], ...] = (
    ("src/ztare/experiment_stats", "statistical"),
    ("src/ztare/motion", "set-distance/metric"),
    ("src/ztare/validator/core", "validation/scoring"),
    ("src/ztare/validator", "validator"),
    ("src/ztare/leanmill/solver", "proof-search"),
    ("src/ztare/leanmill", "leanmill"),
    ("src/ztare/formal", "formal"),
    ("src/ztare/fit", "fit/regime"),
    ("src/ztare/framer", "framing"),
    ("src/ztare/reports", "report"),
    ("src/ztare/research_director", "research-operator"),
    ("src/ztare/orchestrator", "orchestrator"),
    ("src/ztare/gates", "gate"),
    ("src/ztare/common", "common-infra"),
    ("src/ztare/product_exports", "export/judgment"),
    ("scripts/public/validators", "validator-script"),
    ("scripts/public/control/leanmill", "leanmill-script"),
    ("scripts/public/control", "control-script"),
    ("scripts/mining", "mining"),
    ("org/patterns", "pattern"),
    ("org/anti-patterns", "anti-pattern"),
    ("research_areas/seams", "seam"),
    ("projects/", "substrate-project"),
    ("ztare_proofs/", "formal-artifact"),
)


EXACT_PATH_RENAMES: dict[str, str] = {
    "src/ztare/research_director/ns_graph_tick.py": "projects/ns_millennium_hunt/scripts/ns_graph_tick.py",
    "scripts/projects/ns/CAS_W6_verification.py": "projects/ns_millennium_hunt/scripts/CAS_W6_verification.py",
    "scripts/projects/ns/CAS_atom8_verification.py": "projects/ns_millennium_hunt/scripts/CAS_atom8_verification.py",
    "scripts/projects/ns/ns_residual_void_audit.py": "projects/ns_millennium_hunt/scripts/ns_residual_void_audit.py",
    "scripts/public/control/v33_consequence_exposure_gate.py": "src/ztare/gates/v33_consequence_exposure_gate.py",
    "scripts/public/projects/ns/ns_scientific_amnesia_precheck.py": "projects/ns_millennium_hunt/scripts/ns_scientific_amnesia_precheck.py",
    "src/ztare/orchestrator/briefing_providers/path_b_promotion_floor.py": "src/ztare/orchestrator/briefing_providers/variational_promotion_floor.py",
}


SEMANTIC_FAMILIES: dict[str, str] = {
    "research_move_operator": "RD-facing operators that select questions, residuals, portfolios, routes, or research moves.",
    "evidence_governance_gate": "Deterministic gates, validators, audits, and claim/admission controls.",
    "proof_formalization_worker": "Lean/formal proof-state, theorem, solver, or source-binding capabilities.",
    "model_fit_structure_probe": "Fit, regime, statistics, metric, distance, and structural-fingerprint probes.",
    "orchestration_briefing_provider": "Prompt assembly, briefing providers, committee/composition, and loop-routing helpers.",
    "mining_operations_intelligence": "Mining, dashboard, reflexive telemetry, ROI, and operations-intelligence capabilities.",
    "pattern_memory": "Patterns, anti-patterns, meta-patterns, and reflexive working-memory artifacts.",
    "substrate_workbench": "Substrate-specific workbench artifacts or domain-local scripts.",
    "infrastructure_utility": "Reusable common infrastructure or glue with cross-cutting operational value.",
}


ADVISORY_NOTE = (
    "Semantic families are deterministic catalog metadata. Embeddings and "
    "subscription agents may propose related-capability edges, but promotion "
    "into the taxonomy should be a reviewed rule or curated mapping."
)


@dataclass(frozen=True)
class ClassifiedCatalogRow:
    id: str
    path: str
    kind: str
    source_category: str
    semantic_family: str
    semantic_family_reason: str


@dataclass(frozen=True)
class CatalogParentNode:
    family_id: str
    family_label: str
    purpose: str
    child_count: int
    matched_terms: tuple[str, ...]
    source_categories: tuple[str, ...]
    example_ids: tuple[str, ...]


@dataclass(frozen=True)
class CatalogHealth:
    ok: bool
    catalog_path: str
    row_count: int
    source_categories: dict[str, int]
    semantic_families: dict[str, int]
    duplicate_ids: dict[str, int]
    duplicate_signatures: dict[str, int]
    exact_duplicate_rows: int
    missing_paths: tuple[str, ...]
    stale_outputs: tuple[str, ...]
    warnings: tuple[str, ...]

    def summary(self) -> str:
        status = "ok" if self.ok else "needs_attention"
        return (
            f"CATALOG_HEALTH status={status} rows={self.row_count} "
            f"families={len(self.semantic_families)} duplicate_ids={len(self.duplicate_ids)} "
            f"duplicate_signatures={len(self.duplicate_signatures)} missing_paths={len(self.missing_paths)}"
        )


def source_category_for_path(path: str) -> str:
    for prefix, category in SOURCE_CATEGORY_BY_PREFIX:
        if (path or "").startswith(prefix):
            return category
    return "other"


def normalize_catalog_path(path: str, *, repo: Path = REPO) -> str:
    """Resolve known moved catalog paths to their current repo locations.

    This is intentionally deterministic. It repairs broad relocations such as
    `scripts/mining/` -> `scripts/public/mining/` without asking an LLM to guess.
    Rows that only resolve to an archive still resolve to an existing file, leaving
    retirement/debt review to impact and health reporting.
    """
    if not path:
        return path
    if (repo / path).exists():
        return path
    exact = EXACT_PATH_RENAMES.get(path)
    if exact and (repo / exact).exists():
        return exact
    if path.startswith("scripts/mining/"):
        name = Path(path).name
        candidates = (
            f"scripts/public/mining/{name}",
            f"scripts/public/mining/research_mode/{name}",
            f"scripts/public/_archive/mining_vestigial_20260523/{name}",
        )
        for candidate in candidates:
            if (repo / candidate).exists():
                return candidate
    if path.startswith("scripts/public/projects/ns/"):
        candidate = f"projects/ns_millennium_hunt/scripts/{Path(path).name}"
        if (repo / candidate).exists():
            return candidate
    if path.startswith("scripts/projects/ns/"):
        candidate = f"projects/ns_millennium_hunt/scripts/{Path(path).name}"
        if (repo / candidate).exists():
            return candidate
    return path


def _text(row: dict[str, Any]) -> str:
    parts: list[str] = [
        str(row.get("id") or ""),
        str(row.get("path") or ""),
        str(row.get("kind") or ""),
        str(row.get("description") or ""),
    ]
    for key in ("applicability", "dependencies"):
        value = row.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).lower()


def semantic_family_for_row(row: dict[str, Any]) -> tuple[str, str]:
    """Return exactly one semantic family for an architecture-index row."""
    kind = str(row.get("kind") or "").lower()
    path = str(row.get("path") or "")
    source_category = source_category_for_path(path)
    text = _text(row)

    if kind in {"pattern", "anti-pattern", "meta-pattern", "reflexive_primitive"}:
        return "pattern_memory", f"kind={kind}"
    if source_category in {"leanmill", "proof-search", "formal", "formal-artifact", "leanmill-script"}:
        return "proof_formalization_worker", f"source_category={source_category}"
    if kind in {"gate", "validator"} or source_category in {"gate", "validator", "validation/scoring", "validator-script"}:
        return "evidence_governance_gate", f"kind/source={kind}/{source_category}"
    if source_category in {"fit/regime", "framing", "set-distance/metric", "statistical"}:
        return "model_fit_structure_probe", f"source_category={source_category}"
    if kind == "orchestrator" or source_category == "orchestrator":
        return "orchestration_briefing_provider", f"kind/source={kind}/{source_category}"
    if (
        kind == "mining"
        or source_category in {"mining", "report"}
        or "dashboard" in text
        or "telemetry" in text
    ):
        return "mining_operations_intelligence", f"kind/source/text={kind}/{source_category}"
    if source_category in {"substrate-project"} or path.startswith("projects/") or path.startswith("scripts/projects/"):
        return "substrate_workbench", f"source_category={source_category}"
    if source_category in {"research-operator"} or "eigenquestion" in text or "research director" in text:
        return "research_move_operator", f"source_category={source_category}"
    if source_category in {"common-infra", "control-script", "export/judgment", "seam"}:
        return "infrastructure_utility", f"source_category={source_category}"
    return "infrastructure_utility", "fallback"


def classify_row(row: dict[str, Any]) -> ClassifiedCatalogRow:
    family, reason = semantic_family_for_row(row)
    return ClassifiedCatalogRow(
        id=str(row.get("id") or ""),
        path=str(row.get("path") or ""),
        kind=str(row.get("kind") or ""),
        source_category=source_category_for_path(str(row.get("path") or "")),
        semantic_family=family,
        semantic_family_reason=reason,
    )


def load_rows(path: Path = ARCH_INDEX) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def enrich_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["path"] = normalize_catalog_path(str(out.get("path") or ""))
    classified = classify_row(out)
    out["source_category"] = classified.source_category
    out["semantic_family"] = classified.semantic_family
    out["semantic_family_reason"] = classified.semantic_family_reason
    return out


def catalog_parent_nodes(
    rows: Iterable[dict[str, Any]],
    query_terms: Iterable[str] = (),
    *,
    examples_per_family: int = 8,
) -> tuple[CatalogParentNode, ...]:
    query = tuple(str(term).lower() for term in query_terms if str(term).strip())
    grouped: dict[str, list[tuple[ClassifiedCatalogRow, dict[str, Any]]]] = defaultdict(list)
    for row in rows:
        classified = classify_row(row)
        grouped[classified.semantic_family].append((classified, row))

    def impact(row: dict[str, Any]) -> float:
        try:
            return float(row.get("impact_factor_expost") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def query_weight(term: str) -> int:
        if len(term) < 4:
            return 0
        if " " in term or "_" in term:
            return 4
        if len(term) >= 10:
            return 3
        if len(term) >= 6:
            return 2
        return 1

    def example_sort_key(item: tuple[ClassifiedCatalogRow, dict[str, Any]]) -> tuple[float, float, str]:
        child, raw = item
        row_text = _text(raw)
        child_id = child.id.lower()
        child_id_words = child_id.replace("-", " ").replace("_", " ")
        score = 0
        for term in query:
            weight = query_weight(term)
            if not weight:
                continue
            if term in row_text:
                score += weight
            term_id = term.replace(" ", "-").replace("_", "-")
            if term in child_id_words or term_id in child_id:
                score += weight + 2
        return (-float(score), -impact(raw), child.id)

    nodes: list[CatalogParentNode] = []
    for family_id, children_with_rows in grouped.items():
        children = [child for child, _ in children_with_rows]
        purpose = SEMANTIC_FAMILIES.get(family_id, "")
        haystack = " ".join(
            [
                family_id,
                purpose,
                " ".join(child.id for child in children),
                " ".join(child.path for child in children),
            ]
        ).lower()
        matched = tuple(term for term in query if term in haystack)
        examples = tuple(
            child.id
            for child, _ in sorted(children_with_rows, key=example_sort_key)[:examples_per_family]
        )
        source_categories = tuple(sorted({child.source_category for child in children}))
        nodes.append(
            CatalogParentNode(
                family_id=family_id,
                family_label=family_id.replace("_", " ").title(),
                purpose=purpose,
                child_count=len(children),
                matched_terms=matched,
                source_categories=source_categories,
                example_ids=examples,
            )
        )
    return tuple(sorted(nodes, key=lambda node: (-len(node.matched_terms), -node.child_count, node.family_id)))


def catalog_health(
    *,
    catalog_path: Path = ARCH_INDEX,
    atlas_path: Path = ATLAS_PATH,
    rendered_index_path: Path = INDEX_MD,
) -> CatalogHealth:
    rows = load_rows(catalog_path)
    ids = [str(row.get("id") or "") for row in rows]
    signatures = [str(row.get("signature") or "") for row in rows if row.get("signature")]
    duplicate_ids = {key: count for key, count in Counter(ids).items() if key and count > 1}
    duplicate_signatures = {key: count for key, count in Counter(signatures).items() if key and count > 1}
    exact_duplicate_rows = sum(count - 1 for count in Counter(json.dumps(row, sort_keys=True) for row in rows).values() if count > 1)

    missing_paths = tuple(
        sorted({
            str(row.get("path") or "")
            for row in rows
            if row.get("path")
            and not (REPO / normalize_catalog_path(str(row.get("path")))).exists()
        })
    )
    classified = [classify_row(row) for row in rows]
    source_categories = dict(Counter(row.source_category for row in classified))
    semantic_families = dict(Counter(row.semantic_family for row in classified))

    stale_outputs: list[str] = []
    if catalog_path.exists():
        catalog_mtime = catalog_path.stat().st_mtime
        for label, path in (("atlas", atlas_path), ("rendered_index", rendered_index_path)):
            if not path.exists():
                stale_outputs.append(f"{label}:missing")
            elif catalog_mtime > path.stat().st_mtime + 1.0:
                stale_outputs.append(f"{label}:older_than_catalog")

    warnings: list[str] = []
    if duplicate_ids:
        warnings.append(f"{len(duplicate_ids)} duplicate ids")
    if duplicate_signatures:
        warnings.append(f"{len(duplicate_signatures)} duplicate signatures")
    if exact_duplicate_rows:
        warnings.append(f"{exact_duplicate_rows} exact duplicate rows")
    if missing_paths:
        warnings.append(f"{len(missing_paths)} missing paths")
    if stale_outputs:
        warnings.append("stale outputs: " + ", ".join(stale_outputs))
    if not rows:
        warnings.append("catalog empty or missing")

    return CatalogHealth(
        ok=not warnings,
        catalog_path=str(catalog_path),
        row_count=len(rows),
        source_categories=dict(sorted(source_categories.items())),
        semantic_families=dict(sorted(semantic_families.items())),
        duplicate_ids=dict(sorted(duplicate_ids.items())),
        duplicate_signatures=dict(sorted(duplicate_signatures.items())),
        exact_duplicate_rows=exact_duplicate_rows,
        missing_paths=missing_paths[:20],
        stale_outputs=tuple(stale_outputs),
        warnings=tuple(warnings),
    )


def render_health_text(health: CatalogHealth) -> str:
    lines = [health.summary()]
    lines.append("semantic families:")
    for family, count in health.semantic_families.items():
        lines.append(f"  {family}: {count}")
    lines.append("source categories:")
    for category, count in health.source_categories.items():
        lines.append(f"  {category}: {count}")
    for warning in health.warnings:
        lines.append(f"WARNING: {warning}")
    for path in health.missing_paths[:10]:
        lines.append(f"MISSING_PATH: {path}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument("--parents", action="store_true", help="Emit semantic parent nodes.")
    parser.add_argument("--query", action="append", default=[], help="Query term for parent-node matching.")
    args = parser.parse_args(argv)

    if args.parents:
        rows = load_rows()
        nodes = catalog_parent_nodes(rows, args.query)
        payload = [asdict(node) for node in nodes]
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for node in nodes:
                matched = ", ".join(node.matched_terms) or "no query match"
                print(f"{node.family_id}: {node.child_count} rows ({matched})")
        return 0

    health = catalog_health()
    if args.json:
        print(json.dumps(asdict(health), indent=2, sort_keys=True))
    else:
        print(render_health_text(health))
    return 0 if health.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
