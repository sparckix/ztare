"""Scientific-amnesia precheck.

Before a Research Director tick commits to a branch, ask whether the current
frontier overlaps prior evidence rows, GP-233 observations, or code artifacts.
The primitive is deterministic and source-pointing: it surfaces exact rows and
declarations, not a free-form memory summary.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXPERIMENT_TRACK = REPO / "research_areas" / "EXPERIMENT_TRACK_RECORD.md"
GP233_LEDGER = (
    REPO
    / "analytics"
    / "public"
    / "ledgers"
    / "research_yield_decomposition"
    / "GP-233_EVIDENCE_LEDGER.md"
)
DEFAULT_OUTPUT_DIR = REPO / "analytics" / "public" / "queries" / "scientific_amnesia"

# Vocabulary-invariant overlap layer. The atlas is rebuilt by
# projects/ns_millennium_hunt/scripts/build_ns_atlas_embeddings.py and lives in
# the NS tenant. Other tenants may pass their own atlas via --semantic-atlas.
DEFAULT_SEMANTIC_ATLAS = REPO / "projects" / "ns_millennium_hunt" / "public" / "ns_atlas_embeddings.json"
DEFAULT_SEMANTIC_CORPUS = REPO / "projects" / "ns_millennium_hunt" / "public" / "ns_atlas_rag_corpus.json"
SEMANTIC_STATUS_DEFAULT = (
    "falsifier_surface",
    "open_obligation",
    "exclusion_theorem",
    "unclosed_proof_gap",
)
SEMANTIC_THRESHOLD_DEFAULT = 0.65
SEMANTIC_TOP_K_DEFAULT = 5

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


@dataclass(frozen=True)
class OverlapHit:
    source: str
    identifier: str
    path: str
    line: int | None
    score: float
    jaccard: float
    query_coverage: float
    matched_terms: list[str]
    text: str


@dataclass(frozen=True)
class SemanticHit:
    """Vocabulary-invariant atlas neighbour.

    Cosine-similarity hit against the obstruction atlas. Surfaces prior
    formalizations whose lexical surface diverged from the current query but
    whose underlying structure overlaps (e.g. ``CF_LP_LowReg`` vs
    ``critical_frequency_lower_bound`` — see calibration evidence below).
    """

    identifier: str
    status: str
    path: str
    cosine: float
    text: str
    obstruction_id: str | None = None
    layer: str | None = None


@dataclass(frozen=True)
class ScientificAmnesiaReport:
    generated_at: str
    substrate: str
    query: str
    query_tokens: list[str]
    overlap_detected: bool
    threshold: float
    sources_scanned: dict[str, int]
    top_hits: list[OverlapHit]
    output_path: str | None = None
    semantic_enabled: bool = True
    semantic_threshold: float = SEMANTIC_THRESHOLD_DEFAULT
    semantic_top_k: int = SEMANTIC_TOP_K_DEFAULT
    semantic_atlas_path: str | None = None
    semantic_corpus_size: int = 0
    semantic_filtered_size: int = 0
    semantic_overlap_detected: bool = False
    semantic_hits: list[SemanticHit] = field(default_factory=list)
    semantic_skip_reason: str | None = None


def _split_camel(text: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)


def tokenize(text: str) -> set[str]:
    text = _split_camel(text)
    parts = re.split(r"[^A-Za-z0-9]+", text.lower())
    return {p for p in parts if len(p) >= 3 and p not in STOPWORDS}


def _score(query_tokens: set[str], text: str) -> tuple[float, float, float, list[str]]:
    item_tokens = tokenize(text)
    if not query_tokens or not item_tokens:
        return 0.0, 0.0, 0.0, []
    matched = sorted(query_tokens & item_tokens)
    union = query_tokens | item_tokens
    jaccard = len(matched) / max(len(union), 1)
    coverage = len(matched) / max(len(query_tokens), 1)
    # Coverage matters more than raw Jaccard because evidence rows are longer
    # than branch labels. Keep Jaccard visible so false broad matches are auditable.
    score = (0.35 * jaccard) + (0.65 * coverage)
    return score, jaccard, coverage, matched


def _markdown_table_rows(path: Path, *, substrate: str = "") -> list[tuple[int, str, str]]:
    if not path.exists():
        return []
    rows: list[tuple[int, str, str]] = []
    needle = substrate.lower().strip()
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if "---" in stripped:
            continue
        if needle and needle not in stripped.lower():
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        identifier = next((c for c in cells if re.search(r"\b[EF]-|GP-\d+|PL-\d+", c)), cells[0] if cells else "")
        rows.append((lineno, identifier[:160], stripped))
    return rows


def _lean_declarations(paths: list[Path]) -> list[tuple[Path, int, str, str]]:
    decl_re = re.compile(
        r"^\s*(?:noncomputable\s+)?(?:private\s+)?"
        r"(?:def|theorem|lemma|structure|abbrev|opaque|axiom)\s+([A-Za-z0-9_'.]+)"
    )
    out: list[tuple[Path, int, str, str]] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for idx, line in enumerate(lines, 1):
            m = decl_re.match(line)
            if not m:
                continue
            name = m.group(1)
            window = " ".join(lines[max(0, idx - 3) : min(len(lines), idx + 4)])
            out.append((path, idx, name, window))
    return out


def derive_latest_query(*, substrate: str, max_chars: int = 600) -> str:
    """Use the newest matching evidence row as a default branch query."""
    rows = _markdown_table_rows(EXPERIMENT_TRACK, substrate=substrate)
    if not rows:
        return substrate
    _, _, row = rows[-1]
    return row[:max_chars]


_SEMANTIC_CACHE: dict[str, tuple[list[dict], list[list[float]]]] = {}


def _load_semantic_atlas(
    atlas_path: Path, corpus_path: Path
) -> tuple[list[dict], list[list[float]]]:
    """Load + cache atlas embeddings and matching corpus entries.

    Atlas shape: ``{"embeddings": [{"id": str, "embedding": [float,...]}, ...]}``.
    Corpus shape: ``{"entries": [{"id": str, ...}, ...]}``. Alignment is by
    ``id`` (not index) because the builder may shuffle or reselect.
    """
    key = str(atlas_path.resolve())
    cached = _SEMANTIC_CACHE.get(key)
    if cached is not None:
        return cached
    atlas_payload = json.loads(atlas_path.read_text(encoding="utf-8"))
    corpus_payload = json.loads(corpus_path.read_text(encoding="utf-8"))

    if isinstance(atlas_payload, dict):
        atlas_items = atlas_payload.get("embeddings", [])
    else:
        atlas_items = atlas_payload
    embeddings_by_id: dict[str, list[float]] = {}
    for item in atlas_items:
        if isinstance(item, dict) and "id" in item and "embedding" in item:
            embeddings_by_id[str(item["id"])] = item["embedding"]

    if isinstance(corpus_payload, dict):
        corpus_rows = corpus_payload.get("entries", [])
    else:
        corpus_rows = corpus_payload

    aligned_rows: list[dict] = []
    aligned_vecs: list[list[float]] = []
    for row in corpus_rows:
        if not isinstance(row, dict):
            continue
        row_id = row.get("id")
        if row_id is None:
            continue
        vec = embeddings_by_id.get(str(row_id))
        if vec is None:
            continue
        aligned_rows.append(row)
        aligned_vecs.append(vec)
    _SEMANTIC_CACHE[key] = (aligned_rows, aligned_vecs)
    return aligned_rows, aligned_vecs


def _embed_query_genai(query: str) -> list[float] | None:
    """Embed query via gemini-embedding-001. Returns None on missing deps/key."""
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai  # type: ignore[import-not-found]
        from google.genai import types  # type: ignore[import-not-found]
    except Exception:
        return None
    client = genai.Client(api_key=api_key)
    try:
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=query,
            config=types.EmbedContentConfig(output_dimensionality=384),
        )
    except Exception:
        return None
    embeddings = getattr(result, "embeddings", None)
    if not embeddings:
        return None
    first = embeddings[0]
    return list(getattr(first, "values", first))


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / ((na**0.5) * (nb**0.5))


def semantic_overlap_hits(
    query: str,
    *,
    atlas_path: Path = DEFAULT_SEMANTIC_ATLAS,
    corpus_path: Path = DEFAULT_SEMANTIC_CORPUS,
    top_k: int = SEMANTIC_TOP_K_DEFAULT,
    threshold: float = SEMANTIC_THRESHOLD_DEFAULT,
    status_filter: tuple[str, ...] = SEMANTIC_STATUS_DEFAULT,
    embedder=None,
) -> tuple[list[SemanticHit], int, int, str | None]:
    """Return semantic neighbours from the obstruction atlas.

    Returns ``(hits, corpus_size, filtered_size, skip_reason)``. ``skip_reason``
    is non-None when the layer degraded gracefully (missing atlas, no API key,
    embed failure, etc.) — callers should still report the absence of semantic
    coverage rather than crashing the tick.
    """
    if not atlas_path.exists():
        return [], 0, 0, f"atlas missing: {atlas_path}"
    if not corpus_path.exists():
        return [], 0, 0, f"corpus missing: {corpus_path}"
    rows, vecs = _load_semantic_atlas(atlas_path, corpus_path)
    if not rows:
        return [], 0, 0, "atlas empty after alignment"
    embed_fn = embedder or _embed_query_genai
    qvec = embed_fn(query)
    if qvec is None:
        return [], len(rows), 0, "query embedding unavailable (no GOOGLE_API_KEY or google.genai)"

    filtered_indices: list[int] = []
    status_set = {s.lower() for s in status_filter} if status_filter else None
    for idx, row in enumerate(rows):
        if status_set is None:
            filtered_indices.append(idx)
            continue
        status = str(row.get("status", "")).lower()
        if status in status_set:
            filtered_indices.append(idx)
    if not filtered_indices:
        return [], len(rows), 0, "no atlas entries match status_filter"

    scored: list[tuple[float, int]] = []
    for idx in filtered_indices:
        scored.append((_cosine(qvec, vecs[idx]), idx))
    scored.sort(reverse=True, key=lambda t: t[0])

    hits: list[SemanticHit] = []
    for cosine, idx in scored[:top_k]:
        if cosine < threshold:
            break
        row = rows[idx]
        text = str(row.get("text") or row.get("content") or row.get("summary") or "")
        identifier = str(row.get("name") or row.get("identifier") or row.get("id") or f"row_{idx}")
        path = str(row.get("path") or row.get("file") or row.get("source") or "")
        line = row.get("line")
        if isinstance(line, int) and line > 0:
            path = f"{path}:{line}"
        tags = row.get("tags") or []
        obstruction_id = None
        if isinstance(tags, list):
            for tag in tags:
                tag_s = str(tag)
                if tag_s.startswith("obstruction:") or tag_s.startswith("L1:") or tag_s.startswith("L2:") or tag_s.startswith("L3:"):
                    obstruction_id = tag_s
                    break
        hits.append(
            SemanticHit(
                identifier=identifier,
                status=str(row.get("status", "")),
                path=path,
                cosine=round(float(cosine), 4),
                text=text[:500],
                obstruction_id=obstruction_id,
                layer=str(row.get("kind")) if row.get("kind") else None,
            )
        )
    return hits, len(rows), len(filtered_indices), None


def run_scientific_amnesia_check(
    *,
    query: str | None = None,
    substrate: str = "",
    code_globs: list[str] | None = None,
    max_hits: int = 10,
    threshold: float = 0.22,
    output_path: Path | None = None,
    semantic_enabled: bool = True,
    semantic_atlas_path: Path | None = None,
    semantic_corpus_path: Path | None = None,
    semantic_threshold: float = SEMANTIC_THRESHOLD_DEFAULT,
    semantic_top_k: int = SEMANTIC_TOP_K_DEFAULT,
    semantic_status_filter: tuple[str, ...] = SEMANTIC_STATUS_DEFAULT,
) -> ScientificAmnesiaReport:
    substrate_label = substrate or "general"
    query_text = query or derive_latest_query(substrate=substrate_label)
    query_tokens = tokenize(query_text)
    hits: list[OverlapHit] = []
    scanned = {"experiment_rows": 0, "gp233_rows": 0, "code_declarations": 0}

    for path, source_key in ((EXPERIMENT_TRACK, "experiment_rows"), (GP233_LEDGER, "gp233_rows")):
        rows = _markdown_table_rows(path, substrate=substrate)
        scanned[source_key] = len(rows)
        for lineno, identifier, text in rows:
            score, jaccard, coverage, matched = _score(query_tokens, text)
            if not matched:
                continue
            hits.append(
                OverlapHit(
                    source=source_key,
                    identifier=identifier,
                    path=str(path.relative_to(REPO)),
                    line=lineno,
                    score=round(score, 4),
                    jaccard=round(jaccard, 4),
                    query_coverage=round(coverage, 4),
                    matched_terms=matched[:24],
                    text=text[:500],
                )
            )

    resolved_globs = code_globs or []
    code_paths: list[Path] = []
    for pattern in resolved_globs:
        code_paths.extend(sorted(REPO.glob(pattern)))
    decls = _lean_declarations(code_paths)
    scanned["code_declarations"] = len(decls)
    for path, lineno, name, text in decls:
        score, jaccard, coverage, matched = _score(query_tokens, f"{name} {text}")
        if not matched:
            continue
        hits.append(
            OverlapHit(
                source="code_declarations",
                identifier=name,
                path=str(path.relative_to(REPO)),
                line=lineno,
                score=round(score, 4),
                jaccard=round(jaccard, 4),
                query_coverage=round(coverage, 4),
                matched_terms=matched[:24],
                text=text[:500],
            )
        )

    hits.sort(key=lambda h: (h.score, h.query_coverage, h.jaccard), reverse=True)
    top_hits = hits[:max_hits]

    semantic_hits: list[SemanticHit] = []
    sem_corpus_size = 0
    sem_filtered_size = 0
    sem_skip_reason: str | None = None
    if semantic_enabled:
        atlas_path = semantic_atlas_path or DEFAULT_SEMANTIC_ATLAS
        corpus_path = semantic_corpus_path or DEFAULT_SEMANTIC_CORPUS
        semantic_hits, sem_corpus_size, sem_filtered_size, sem_skip_reason = semantic_overlap_hits(
            query_text,
            atlas_path=atlas_path,
            corpus_path=corpus_path,
            top_k=semantic_top_k,
            threshold=semantic_threshold,
            status_filter=semantic_status_filter,
        )
    semantic_overlap_detected = bool(semantic_hits)

    report = ScientificAmnesiaReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        substrate=substrate_label,
        query=query_text,
        query_tokens=sorted(query_tokens),
        overlap_detected=any(h.score >= threshold for h in top_hits),
        threshold=threshold,
        sources_scanned=scanned,
        top_hits=top_hits,
        output_path=None,
        semantic_enabled=semantic_enabled,
        semantic_threshold=semantic_threshold,
        semantic_top_k=semantic_top_k,
        semantic_atlas_path=(
            str((semantic_atlas_path or DEFAULT_SEMANTIC_ATLAS).resolve())
            if semantic_enabled
            else None
        ),
        semantic_corpus_size=sem_corpus_size,
        semantic_filtered_size=sem_filtered_size,
        semantic_overlap_detected=semantic_overlap_detected,
        semantic_hits=semantic_hits,
        semantic_skip_reason=sem_skip_reason,
    )

    if output_path is None:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", substrate_label.lower()).strip("_") or "general"
        output_path = DEFAULT_OUTPUT_DIR / f"{safe}_latest.json"
    elif not output_path.is_absolute():
        output_path = REPO / output_path
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    payload["output_path"] = str(output_path.relative_to(REPO))
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ScientificAmnesiaReport(
        **{**payload, "top_hits": top_hits, "semantic_hits": semantic_hits}
    )


def render_text(report: ScientificAmnesiaReport) -> str:
    lines = [
        f"  scientific_amnesia_ok = True",
        f"  substrate: {report.substrate}",
        f"  overlap_detected: {report.overlap_detected} (threshold={report.threshold})",
        f"  query tokens: {', '.join(report.query_tokens[:24])}",
        f"  sources scanned: {report.sources_scanned}",
    ]
    if report.output_path:
        lines.append(f"  artifact: {report.output_path}")
    if report.top_hits:
        lines.append("  top history/code overlaps:")
        for hit in report.top_hits[:8]:
            loc = f"{hit.path}:{hit.line}" if hit.line else hit.path
            lines.append(
                f"    - {hit.score:.4f} {hit.source} {hit.identifier} @ {loc}"
                f" | matched={','.join(hit.matched_terms[:10])}"
            )
    else:
        lines.append("  top history/code overlaps: none")

    if report.semantic_enabled:
        lines.append(
            f"  semantic (vocabulary-invariant): "
            f"corpus={report.semantic_corpus_size} filtered={report.semantic_filtered_size} "
            f"threshold={report.semantic_threshold} top_k={report.semantic_top_k}"
        )
        if report.semantic_skip_reason:
            lines.append(f"    skipped: {report.semantic_skip_reason}")
        elif report.semantic_hits:
            lines.append("    top semantic neighbours:")
            for hit in report.semantic_hits:
                loc = hit.path or "(no path)"
                tag = f" [{hit.layer}]" if hit.layer else ""
                lines.append(
                    f"    - cos={hit.cosine:.4f} {hit.status} {hit.identifier}{tag} @ {loc}"
                )
        else:
            lines.append("    top semantic neighbours: none above threshold")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scientific-amnesia history-overlap precheck")
    parser.add_argument("--query", default=None)
    parser.add_argument("--substrate", default="")
    parser.add_argument("--code-glob", action="append", default=[])
    parser.add_argument("--max-hits", type=int, default=10)
    parser.add_argument("--threshold", type=float, default=0.22)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--no-semantic",
        dest="semantic_enabled",
        action="store_false",
        default=True,
        help="Disable the vocabulary-invariant atlas layer (opt-in by default).",
    )
    parser.add_argument(
        "--semantic-atlas",
        type=Path,
        default=None,
        help="Override atlas embeddings JSON (defaults to NS atlas).",
    )
    parser.add_argument(
        "--semantic-corpus",
        type=Path,
        default=None,
        help="Override atlas corpus JSON (defaults to NS atlas corpus).",
    )
    parser.add_argument("--semantic-threshold", type=float, default=SEMANTIC_THRESHOLD_DEFAULT)
    parser.add_argument("--semantic-top-k", type=int, default=SEMANTIC_TOP_K_DEFAULT)
    parser.add_argument(
        "--semantic-status",
        action="append",
        default=None,
        help="Filter atlas entries by status (repeatable). Defaults to obstruction surfaces.",
    )
    args = parser.parse_args(argv)
    status_filter = tuple(args.semantic_status) if args.semantic_status else SEMANTIC_STATUS_DEFAULT
    report = run_scientific_amnesia_check(
        query=args.query,
        substrate=args.substrate,
        code_globs=args.code_glob,
        max_hits=args.max_hits,
        threshold=args.threshold,
        output_path=args.output,
        semantic_enabled=args.semantic_enabled,
        semantic_atlas_path=args.semantic_atlas,
        semantic_corpus_path=args.semantic_corpus,
        semantic_threshold=args.semantic_threshold,
        semantic_top_k=args.semantic_top_k,
        semantic_status_filter=status_filter,
    )
    print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
