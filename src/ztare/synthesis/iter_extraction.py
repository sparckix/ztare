"""Shared iter-extraction primitive for synthesis flows (GP-193).

Single source of truth for "read projects/<slug>/history/ and produce
typed IterRecord list." Consumed by:

  - src/ztare/synthesis/post_run_thesis_synthesizer.py (end-of-loop
    deterministic complementary-cluster detection + thesis promotion)
  - src/ztare/synthesis/synthesize.py (report-stage history
    summarization — Option B in the GP-193 seam, future work)

Why extract: per the GP-193 seam Architecture-Coherence debate, both
flows currently read history/ independently; if either drifts the
other will need patching. This module makes the history-read
contract single-source.

Reference seam:
  research_areas/private/seams/protocol/GP-193_post_run_thesis_synthesizer_seam.md
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# workspace/submissions/ filename: iter_NNN_TIMESTAMP.md
SUBMISSIONS_FILE_RE = re.compile(r"^iter_(?P<iter>\d{3})_(?P<ts>[\dT.+Z]+)\.md$")

log = logging.getLogger(__name__)

# Match the canonical history filename pattern emitted by autoresearch_loop
HISTORY_FILE_RE = re.compile(
    r"^(?P<runid>\d+)_iter(?P<iter>\d+)_score_(?P<score>\d+)_(?P<slug>.+)\.md$"
)
META_SUFFIX = "_meta.json"


@dataclass
class IterRecord:
    """Per-iteration content extracted from the run history.

    All fields except iter_index, score, and thesis_md_path may be
    empty strings or empty lists if the meta/DAG sidecar is missing
    or unparseable. Callers should treat empty fields as missing
    data, not as absence of content.

    DAG nodes (added 2026-05-02 evening per operator flag):
    `*_dag.json` per iter carries the judge's structural model of the
    thesis — nodes are labeled load-bearing claims (id, label),
    edges are inferential relations with weights. This is RICHER than
    parsing thesis text because the judge has already identified what
    is load-bearing. Complementarity detection prefers DAG node
    labels when present.
    """
    iter_index: int
    score: int
    thesis_md_path: Path
    meta_path: Path
    verified_axioms: list[str] = field(default_factory=list)
    weakest_point: str = ""
    debate_summary: str = ""
    dim_scores: dict[str, float] = field(default_factory=dict)
    runid: str = ""
    dag_nodes: list[dict] = field(default_factory=list)
    dag_edges: list[dict] = field(default_factory=list)

    def is_meta_loaded(self) -> bool:
        """True iff the meta sidecar was present and parsed."""
        return bool(self.weakest_point or self.verified_axioms
                    or self.debate_summary or self.dim_scores)

    def dag_node_labels(self) -> list[str]:
        """Convenience: extract node labels from DAG. Empty list if no
        DAG was loaded. These ARE the load-bearing primitives the
        judge identified — better signal than thesis-text fallback."""
        return [str(n.get("label", "")).strip()
                for n in self.dag_nodes if n.get("label")]


def _read_submissions_supplement(
    project_dir: Path,
    latest_runid: str,
    existing_iter_indices: set[int],
) -> list[IterRecord]:
    """Supplement history/ records with workspace/submissions/ when history
    is sparse for the latest run (e.g. only 1 promoted iter).

    workspace/submissions/ holds ALL submitted iters (including non-promoted
    ones below the champion). eval_history.jsonl carries scores and
    weakest_points. This lets the synthesizer see, e.g., an iter-3 (score 87)
    that addressed the Meta-Judge gap even when it never made history/.

    Only reads iters NOT already in existing_iter_indices to avoid duplicates.
    Marks records with runid=latest_runid so run-filtering still applies.

    Deduplication: submissions/ has files from all runs (no runid in filename).
    We take only the MOST RECENT file per iter_idx (latest timestamp = latest
    run's submission). eval_history is read in JSONL order — the LAST entry
    per iter_idx is the most recent run's score.
    """
    supplements: list[IterRecord] = []
    ws = project_dir / "workspace"
    submissions_dir = ws / "submissions"
    if not submissions_dir.exists():
        return supplements

    # Build score + weakest_point from eval_history.jsonl.
    # We need entries from the CURRENT run only. Strategy: find the
    # timestamp of the champion history record (already in history/ for
    # latest_runid), then only accept eval_history entries timestamped
    # at or after it. This bounds cross-run contamination.
    champion_ts: Optional[str] = None
    history_dir = project_dir / "history"
    if history_dir.exists():
        for f in sorted(history_dir.glob("*.md")):
            m2 = HISTORY_FILE_RE.match(f.name)
            if m2 and m2.group("runid") == latest_runid:
                meta_p = f.with_name(f.stem + META_SUFFIX)
                if meta_p.exists():
                    try:
                        meta_data = json.loads(meta_p.read_text(encoding="utf-8"))
                        champion_ts = str(meta_data.get("timestamp") or "")
                    except Exception:
                        pass
                break

    score_map: dict[int, int] = {}
    weak_map: dict[int, str] = {}
    eh_path = ws / "eval_history.jsonl"
    if eh_path.exists():
        try:
            for line in eh_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    it = rec.get("iteration")
                    sc = rec.get("score")
                    wp = str(rec.get("weakest_point") or "")
                    ts = str(rec.get("timestamp") or "")
                    # If we have a champion timestamp, only accept entries
                    # from the same run (ts >= champion_ts). If no champion
                    # timestamp is available, fall back to last-wins.
                    if champion_ts and ts and ts < champion_ts:
                        continue
                    if isinstance(it, int) and isinstance(sc, (int, float)):
                        score_map[it] = int(sc)
                        weak_map[it] = wp
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as exc:
            log.warning("iter_extraction: eval_history read failed: %s", exc)

    # For each iter_idx, collect all matching submission files and take
    # only the most recent one (sorted by filename timestamp, descending).
    by_iter: dict[int, list[Path]] = {}
    for f in submissions_dir.glob("*.md"):
        m = SUBMISSIONS_FILE_RE.match(f.name)
        if not m:
            continue
        iter_idx = int(m.group("iter"))
        by_iter.setdefault(iter_idx, []).append(f)

    for iter_idx in sorted(by_iter):
        if iter_idx in existing_iter_indices:
            continue  # already loaded from history/
        score = score_map.get(iter_idx, 0)
        if score <= 0:
            continue  # scored 0 or unknown — not useful for synthesis
        # Pick the most recent submission file for this iter
        candidates = sorted(by_iter[iter_idx], key=lambda p: p.name, reverse=True)
        f = candidates[0]
        rec = IterRecord(
            iter_index=iter_idx,
            score=score,
            thesis_md_path=f,
            meta_path=f.with_suffix(".meta.json"),  # doesn't exist; graceful
            runid=latest_runid,
        )
        rec.weakest_point = weak_map.get(iter_idx, "")
        try:
            rec.verified_axioms = [f.read_text(encoding="utf-8")]
        except Exception as exc:
            log.warning("iter_extraction: submission read failed %s: %s", f, exc)
        supplements.append(rec)
        log.info(
            "iter_extraction: supplemented iter-%d (score %d) from submissions/",
            iter_idx, score,
        )
    return supplements


def read_iter_records(project_dir: Path,
                      runid: Optional[str] = None,
                      latest_run_only: bool = True,
                      supplement_submissions: bool = True,
                      min_records_before_supplement: int = 2,
                      ) -> list[IterRecord]:
    """Walk projects/<slug>/history/ and build IterRecord per iter.

    Skips files that don't match the canonical name pattern. Returns
    records sorted by iter_index ascending. Meta sidecar load failures
    are logged but non-fatal.

    Args:
        project_dir: projects/<slug>/
        runid: if set, only return records from this specific runid.
            Mutually exclusive with latest_run_only.
        latest_run_only: if True (default), filter to the most recent
            runid only. Cross-run synthesis is rarely meaningful — iters
            from different runs operate under potentially different
            charters/rubrics. Set False to allow cross-run synthesis.
        supplement_submissions: if True and the filtered history has fewer
            than min_records_before_supplement records, supplement with
            non-promoted iters from workspace/submissions/ (using
            eval_history.jsonl for scores/weakest_points). This is needed
            because history/ only saves promoted iters (new champions);
            a 3-iter run with a strong iter-1 champion may have 0 other
            history entries even though iter-2 and iter-3 are useful for
            synthesis.
        min_records_before_supplement: supplement only kicks in when the
            filtered history has fewer records than this threshold.

    Note on verified_axioms: per-iter meta sidecars (`*_meta.json`) do
    NOT carry verified_axioms — those live in `latest_eval_results.json`
    overwritten each iter. As a substitute signal, this loader reads
    the thesis .md content directly into `verified_axioms` (one entry
    = the full thesis text body). Downstream complementarity detection
    operates on that text. This is intentional: the thesis text IS
    what synthesis recombines, and it is more reliable than the
    judge-extracted `verified_axioms` field which is often empty.
    """
    history_dir = project_dir / "history"
    if not history_dir.exists():
        return []

    raw: list[IterRecord] = []
    for f in sorted(history_dir.glob("*.md")):
        m = HISTORY_FILE_RE.match(f.name)
        if not m:
            continue
        iter_idx = int(m.group("iter"))
        score = int(m.group("score"))
        rid = m.group("runid")
        meta_path = f.with_name(f.stem + META_SUFFIX)
        rec = IterRecord(
            iter_index=iter_idx,
            score=score,
            thesis_md_path=f,
            meta_path=meta_path,
            runid=rid,
        )
        # Meta sidecar (carries weakest_point, score, run_id)
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                rec.weakest_point = str(meta.get("weakest_point") or "")
                rec.debate_summary = str(meta.get("debate_summary") or "")
                rec.dim_scores = dict(meta.get("dim_scores") or {})
                # Some pipelines may write verified_axioms here; keep if so.
                axioms = meta.get("verified_axioms")
                if axioms:
                    rec.verified_axioms = list(axioms)
            except Exception as exc:
                log.warning("iter_extraction: meta read failed for %s: %s",
                            meta_path, exc)
        # DAG sidecar (judge's structural model of the thesis —
        # nodes are labeled load-bearing claims). This is RICHER than
        # thesis-text parsing because the judge has already identified
        # what is load-bearing. Preferred signal for complementarity
        # detection when present.
        dag_path = f.with_name(f.stem + "_dag.json")
        if dag_path.exists():
            try:
                dag = json.loads(dag_path.read_text(encoding="utf-8"))
                rec.dag_nodes = list(dag.get("nodes") or [])
                rec.dag_edges = list(dag.get("edges") or [])
            except Exception as exc:
                log.warning("iter_extraction: DAG read failed for %s: %s",
                            dag_path, exc)
        # Thesis text body (load-bearing fallback for verified_axioms)
        if not rec.verified_axioms and f.exists():
            try:
                rec.verified_axioms = [f.read_text(encoding="utf-8")]
            except Exception as exc:
                log.warning("iter_extraction: thesis read failed for %s: %s",
                            f, exc)
        raw.append(rec)

    # Run-filtering — default to most recent run only
    latest_runid: str = ""
    if runid is not None:
        records = [r for r in raw if r.runid == runid]
        latest_runid = runid
    elif latest_run_only and raw:
        latest_runid = max(r.runid for r in raw)
        records = [r for r in raw if r.runid == latest_runid]
    else:
        records = raw
        if raw:
            latest_runid = max(r.runid for r in raw)

    # Supplement with non-promoted submissions when history is sparse.
    # This covers the common case where iter-1 is the champion and
    # iters 2+ never make history/, leaving the synthesizer with < 2
    # records even though iter-2/3 are valuable for complementary synthesis.
    if (supplement_submissions
            and latest_runid
            and len(records) < min_records_before_supplement):
        existing_indices = {r.iter_index for r in records}
        extra = _read_submissions_supplement(
            project_dir, latest_runid, existing_indices
        )
        if extra:
            log.info(
                "iter_extraction: supplemented %d record(s) from "
                "workspace/submissions/ (history had %d for latest run)",
                len(extra), len(records),
            )
            records = records + extra

    records.sort(key=lambda r: (r.iter_index, r.runid))
    return records


def content_words(text: str, min_len: int = 4) -> set[str]:
    """Extract content-word lowercased tokens (>=min_len chars,
    alphanumeric). Used by deterministic complementarity heuristics
    that match verified_axioms against weakest_points by vocabulary
    overlap."""
    return set(re.findall(rf"[a-z][a-z0-9_-]{{{min_len-1},}}", (text or "").lower()))


def detect_complementary_pairs(records: list[IterRecord],
                                min_overlap: int = 3
                                ) -> list[tuple[int, int]]:
    """Find iter pairs (M, N) where iter-M's load-bearing claims
    close iter-N's weakest_point.

    Signal preference (richest first):
      1. DAG node labels (judge-identified load-bearing claims) —
         strongest signal because the judge has already extracted them
      2. verified_axioms field from meta sidecar (when populated)
      3. Thesis text fallback (full body — noisier but always available)

    Heuristic: M's claims close N's weakest_point if M's content
    words have >=min_overlap overlap with N's weakest_point content
    words. Symmetric (also checks N→M).

    Returns: list of (M, N) pairs where M's claims close N's W_b.
    Indices reference iter_index values, not list positions.
    """
    pairs: list[tuple[int, int]] = []
    for i, m_rec in enumerate(records):
        # Pick the strongest available claim signal for iter-M
        if m_rec.dag_node_labels():
            m_claim_text = " ".join(m_rec.dag_node_labels())
        elif m_rec.verified_axioms:
            m_claim_text = " ".join(m_rec.verified_axioms)
        else:
            continue
        m_words = content_words(m_claim_text)
        if not m_words:
            continue
        for j, n_rec in enumerate(records):
            if i == j:
                continue
            if not n_rec.weakest_point:
                continue
            n_weak_words = content_words(n_rec.weakest_point)
            if len(m_words & n_weak_words) >= min_overlap:
                pairs.append((m_rec.iter_index, n_rec.iter_index))
    return pairs


def cluster_pairs_to_groups(pairs: list[tuple[int, int]]
                             ) -> list[set[int]]:
    """Union-find: collapse complementary pairs into transitive
    clusters. (M,N) and (N,P) → cluster {M, N, P}. Returns clusters
    of size >= 2 only."""
    parent: dict[int, int] = {}

    def find(x: int) -> int:
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    nodes: set[int] = set()
    for a, b in pairs:
        nodes.add(a); nodes.add(b)
        parent.setdefault(a, a); parent.setdefault(b, b)
        union(a, b)

    groups: dict[int, set[int]] = {}
    for n in nodes:
        r = find(n)
        groups.setdefault(r, set()).add(n)
    return [g for g in groups.values() if len(g) >= 2]
