"""Post-run thesis synthesizer (GP-193, 2026-05-02).

Mechanizes the cross-iter recombination pattern that the agent was
performing by hand at debrief time on gp168 v3 run-2 (F1-F4 findings)
and gp169 v3 (calibration-veto + ERP + Trigger Table protocol).
Per AGENTS.md mechanization guide: recurring valuable hand-procedures
become deterministic primitives.

Reference seam:
  research_areas/private/seams/protocol/GP-193_post_run_thesis_synthesizer_seam.md

How it works (narrow scope, opt-in to promotion):

1. Reads all iter records from projects/<slug>/history/.
2. Detects complementary clusters via verified_axiom ↔ weakest_point
   matching (deterministic heuristic + optional LLM fallback).
3. Composes candidate combined theses by inserting complementary
   verified_axioms into the highest-scored cluster member.
4. Scores each candidate via the existing judge invoker.
5. Promotes a candidate to thesis.md ONLY if it beats the per-iter
   champion by ≥ margin_threshold (default 5).
6. Always logs to workspace/post_run_synthesis_attempts.jsonl.

Opt-out: set `enable_post_run_thesis_synthesis: false` in the rubric
to disable synthesis for any project.

Quality controls:
  - iter-0 seed theses are excluded by default. They describe the
    starting bifurcation and are almost never a valid theorem component.
  - low-score records far below the run champion are excluded by
    default. They remain available in the audit/debrief artifacts, but
    are not automatically blended into a promotion candidate.
  - oversized transitive clusters are trimmed to the strongest records.
    The pair detector is intentionally cheap; this prevents generic
    vocabulary overlap from collapsing a whole run into one noisy
    appendix candidate.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# Shared primitive — single source of truth for iter extraction
# (per GP-193 seam Architecture-Coherence debate, Option A).
from src.ztare.synthesis.iter_extraction import (
    IterRecord,
    read_iter_records,
    detect_complementary_pairs,
    cluster_pairs_to_groups,
)

log = logging.getLogger(__name__)


def _filter_records_for_synthesis(
    records: list[IterRecord],
    rubric_data: dict,
) -> list[IterRecord]:
    """Apply conservative quality controls before pair clustering.

    Post-run synthesis is allowed to be opportunistic, but it should not
    spend judge calls blending seed prompts and heavily defeated theses
    into a candidate whose top theorem body is still the old champion.
    The dropped records are not deleted; they remain in submissions and
    debriefs for human interpretation.
    """
    if not records:
        return []

    include_iter0 = bool(rubric_data.get(
        "post_run_synthesis_include_iter0", False))
    max_score_gap = int(rubric_data.get(
        "post_run_synthesis_max_score_gap", 25))
    explicit_floor = rubric_data.get("post_run_synthesis_min_score")

    champion_score = max(r.score for r in records)
    if explicit_floor is None:
        score_floor = max(1, champion_score - max_score_gap)
    else:
        score_floor = int(explicit_floor)

    kept: list[IterRecord] = []
    dropped: list[tuple[int, int, str]] = []
    for rec in records:
        if rec.iter_index == 0 and not include_iter0:
            dropped.append((rec.iter_index, rec.score, "iter0_seed"))
            continue
        if rec.score < score_floor:
            dropped.append((rec.iter_index, rec.score, "below_score_floor"))
            continue
        kept.append(rec)

    if dropped:
        log.info(
            "post-run synthesis: filtered records before clustering: %s "
            "(score_floor=%s, include_iter0=%s)",
            dropped, score_floor, include_iter0,
        )
    return kept


def _trim_cluster_to_quality_cap(
    cluster: set[int],
    records_by_iter: dict[int, IterRecord],
    rubric_data: dict,
) -> set[int]:
    """Keep transitive clusters small enough to remain interpretable."""
    max_cluster_size = int(rubric_data.get(
        "post_run_synthesis_max_cluster_size", 4))
    if max_cluster_size <= 0 or len(cluster) <= max_cluster_size:
        return set(cluster)

    ranked = sorted(
        (records_by_iter[i] for i in cluster),
        key=lambda r: (-r.score, r.iter_index),
    )
    trimmed = {r.iter_index for r in ranked[:max_cluster_size]}
    log.info(
        "post-run synthesis: trimmed broad cluster %s -> %s",
        sorted(cluster), sorted(trimmed),
    )
    return trimmed


@dataclass
class SynthesisAttempt:
    """One attempted synthesis (whether promoted or not)."""
    cluster_iter_indices: list[int]
    base_iter_index: int
    base_score: int
    candidate_score: Optional[int] = None
    margin: Optional[int] = None
    promoted: bool = False
    candidate_path: Optional[Path] = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "cluster_iter_indices": self.cluster_iter_indices,
            "base_iter_index": self.base_iter_index,
            "base_score": self.base_score,
            "candidate_score": self.candidate_score,
            "margin": self.margin,
            "promoted": self.promoted,
            "candidate_path": str(self.candidate_path) if self.candidate_path else None,
            "reason": self.reason,
        }


def compose_candidate_thesis(cluster: set[int],
                              records_by_iter: dict[int, IterRecord]
                              ) -> tuple[Path, IterRecord]:
    """Compose a candidate combined thesis from a cluster.

    Strategy:
      1. Pick highest-scored iter as base.
      2. For each other iter in the cluster, append a SYNTHESIS
         section with the verified_axioms that complement the base's
         weakest_point.
      3. Synthesis markers are explicit and auditable.

    Returns: (candidate_path, base_record).
    """
    cluster_records = sorted(
        [records_by_iter[i] for i in cluster],
        key=lambda r: r.score, reverse=True,
    )
    base = cluster_records[0]
    others = cluster_records[1:]

    base_text = base.thesis_md_path.read_text(encoding="utf-8")
    parts = [base_text.rstrip(), ""]
    parts.append("---")
    parts.append("")
    parts.append("## POST-RUN SYNTHESIS APPENDIX (GP-193)")
    parts.append("")
    parts.append(
        f"Base: iter-{base.iter_index} (score {base.score}). "
        f"Synthesized with {len(others)} complementary iter(s) "
        f"detected via verified-axiom ↔ weakest-point overlap."
    )
    parts.append("")

    for other in others:
        parts.append(f"### From iter-{other.iter_index} (score {other.score})")
        parts.append("")
        parts.append(
            f"<!-- SYNTHESIS: addresses base weakest_point: "
            f"{base.weakest_point[:200]}... -->"
        )
        parts.append("")
        if other.verified_axioms:
            # Detect whether axioms are short discrete claims or
            # the fallback (full thesis text). Full-text payloads
            # become a path-pointer + score; short discrete axioms
            # get inlined as bullets.
            ax_total_chars = sum(len(a) for a in other.verified_axioms)
            if ax_total_chars > 2000 or len(other.verified_axioms) == 1:
                # Fallback case — full thesis text. Don't inline (would
                # bloat the candidate); reference instead and excerpt
                # the structural-content sections.
                parts.append(
                    f"**Complementary content from iter-{other.iter_index}** "
                    f"(full thesis at `{other.thesis_md_path.name}`):"
                )
                parts.append("")
                # Excerpt: take any section headers present (## or ###)
                # from the other thesis as a structural map
                first_text = other.verified_axioms[0]
                import re as _re
                headers = _re.findall(r"^(#{2,4} .+)$", first_text, _re.MULTILINE)
                if headers:
                    parts.append("Structural sections this iter contributes:")
                    for h in headers[:15]:
                        parts.append(f"- {h.lstrip('#').strip()}")
                    parts.append("")
                # Plus a short excerpt of the first ~600 chars
                excerpt = first_text[:600].rstrip() + "..."
                parts.append("Opening excerpt:")
                parts.append("```")
                parts.append(excerpt)
                parts.append("```")
                parts.append("")
            else:
                parts.append("**Complementary verified axioms:**")
                for ax in other.verified_axioms:
                    parts.append(f"- {ax}")
                parts.append("")
        else:
            parts.append("*(no verified_axioms or thesis-text available)*")
            parts.append("")

    parts.append("---")
    parts.append("")
    parts.append(
        "**Audit trail:** original per-iter theses preserved in "
        "history/ at the timestamps above. Synthesis composed by "
        "src/ztare/synthesis/post_run_thesis_synthesizer.py per "
        "GP-193 spec."
    )

    workspace = base.thesis_md_path.parent.parent / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    cluster_label = "_".join(str(i) for i in sorted(cluster))
    candidate_path = workspace / f"synthesis_candidate_{cluster_label}.md"
    candidate_path.write_text("\n".join(parts), encoding="utf-8")

    # Also write a companion test_model.py from the base iter's submission
    # so the synthesis judge_invoker can run the correct falsification suite.
    # Search order: (1) sibling .py next to thesis_md_path, (2) submissions/
    # dir matched by iter index pattern (iter_NNN_*.py), (3) skip silently.
    base_py = base.thesis_md_path.with_suffix(".py")
    if not base_py.exists():
        submissions_dir = workspace / "submissions"
        if submissions_dir.is_dir():
            pattern = f"iter_{base.iter_index:03d}_*.py"
            matches = sorted(submissions_dir.glob(pattern), reverse=True)
            if matches:
                base_py = matches[0]
    if base_py.exists():
        companion_py = workspace / f"synthesis_candidate_{cluster_label}.py"
        companion_py.write_text(base_py.read_text(encoding="utf-8"), encoding="utf-8")
        log.info("post-run synthesis: wrote companion test_model at %s", companion_py)

    return candidate_path, base


def run_post_run_synthesis(*,
                           project_dir: Path,
                           rubric_data: dict,
                           judge_invoker: Optional[Callable[[Path], int]] = None,
                           margin_threshold: int = 5,
                           max_synthesis_attempts: int = 3,
                           ) -> list[SynthesisAttempt]:
    """End-of-run hook: try to synthesize a better-than-champion
    combined thesis. See module docstring + GP-193 seam.

    Args:
        project_dir: projects/<slug>/
        rubric_data: parsed rubric JSON
        judge_invoker: callable(candidate_path) → score; if None,
            synthesis attempts are recorded but never promoted (dry run)
        margin_threshold: candidate_score must beat champion by this
        max_synthesis_attempts: cap on judge calls (cost control)

    Returns: list of SynthesisAttempt records.
    """
    attempts: list[SynthesisAttempt] = []
    workspace = project_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    if not bool(rubric_data.get("enable_post_run_thesis_synthesis", True)):
        log.info("post-run synthesis disabled by rubric flag")
        _write_attempts_log(workspace, attempts, note="disabled_by_rubric")
        return attempts

    # Always supplement from submissions/ so non-promoted iters (e.g., a
    # score-88 iter-4 that lost to a score-92 champion) are available for
    # synthesis. The default min_records_before_supplement=2 guard was
    # designed for sparse-history loops; synthesis always wants the full set.
    records = read_iter_records(project_dir, min_records_before_supplement=999)
    # Filter score-0 iters — they carry no structural content worth merging.
    records = [r for r in records if r.score > 0]
    records = _filter_records_for_synthesis(records, rubric_data)
    if len(records) < 2:
        log.info("post-run synthesis: <2 scored iters available, nothing to compose")
        _write_attempts_log(workspace, attempts,
                            note="less_than_two_quality_scored_iters")
        return attempts

    records_by_iter = {r.iter_index: r for r in records}
    pairs = detect_complementary_pairs(records)
    if not pairs:
        log.info("post-run synthesis: no complementary pairs detected")
        _write_attempts_log(workspace, attempts, note="no_pairs_detected")
        return attempts

    clusters = [
        _trim_cluster_to_quality_cap(c, records_by_iter, rubric_data)
        for c in cluster_pairs_to_groups(pairs)
    ]
    clusters = [c for c in clusters if len(c) >= 2]
    if not clusters:
        log.info("post-run synthesis: pairs found but no clusters formed")
        _write_attempts_log(workspace, attempts, note="no_clusters")
        return attempts

    # Order clusters by max score in cluster (try strongest first)
    clusters_ordered = sorted(
        clusters,
        key=lambda c: max(records_by_iter[i].score for i in c),
        reverse=True,
    )
    clusters_to_try = clusters_ordered[:max_synthesis_attempts]
    log.info("post-run synthesis: %d clusters detected, trying top %d",
             len(clusters), len(clusters_to_try))

    overall_champion_score = max(r.score for r in records)

    for cluster in clusters_to_try:
        candidate_path, base = compose_candidate_thesis(cluster, records_by_iter)
        attempt = SynthesisAttempt(
            cluster_iter_indices=sorted(cluster),
            base_iter_index=base.iter_index,
            base_score=base.score,
            candidate_path=candidate_path,
        )
        if judge_invoker is None:
            attempt.reason = "no_judge_invoker_dry_run"
            attempts.append(attempt)
            continue
        try:
            candidate_score = int(judge_invoker(candidate_path))
            attempt.candidate_score = candidate_score
            attempt.margin = candidate_score - overall_champion_score
            if attempt.margin >= margin_threshold:
                attempt.promoted = True
                attempt.reason = f"promoted: margin {attempt.margin} >= {margin_threshold}"
                _promote_synthesis(project_dir, candidate_path, attempt)
                # Stop after first promotion — apparatus does not
                # synthesize-on-top-of-synthesis in v1.
                attempts.append(attempt)
                break
            else:
                attempt.reason = f"not_promoted: margin {attempt.margin} < {margin_threshold}"
        except Exception as exc:
            attempt.reason = f"judge_error: {exc}"
            log.warning("post-run synth judge failed for cluster %s: %s",
                        cluster, exc)
        attempts.append(attempt)

    _write_attempts_log(workspace, attempts, note="completed")
    return attempts


def _promote_synthesis(project_dir: Path,
                       candidate_path: Path,
                       attempt: SynthesisAttempt) -> None:
    """Copy candidate to thesis.md, append to history/, update
    transitions.jsonl."""
    import shutil
    from datetime import datetime, timezone

    # 1. Replace thesis.md
    thesis_path = project_dir / "thesis.md"
    if thesis_path.exists():
        backup = project_dir / "thesis_pre_synthesis_backup.md"
        shutil.copy(thesis_path, backup)
    shutil.copy(candidate_path, thesis_path)

    # 2. Append to history/
    cluster_label = "_".join(str(i) for i in attempt.cluster_iter_indices)
    history_path = (
        project_dir / "history"
        / f"post_run_synthesis_iters_{cluster_label}_score_{attempt.candidate_score}.md"
    )
    history_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(candidate_path, history_path)

    # 3. Update transitions.jsonl
    try:
        transitions_path = project_dir.parent.parent / "ztare_workspace" / "transitions.jsonl"
        if not transitions_path.parent.exists():
            transitions_path = project_dir / "transitions.jsonl"
        transitions_path.parent.mkdir(parents=True, exist_ok=True)
        with transitions_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "event": "post_run_synthesis_promoted",
                "project_slug": project_dir.name,
                "cluster_iter_indices": attempt.cluster_iter_indices,
                "base_iter_index": attempt.base_iter_index,
                "candidate_score": attempt.candidate_score,
                "base_score": attempt.base_score,
                "margin": attempt.margin,
                "candidate_path": str(candidate_path),
                "thesis_path": str(thesis_path),
                "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }) + "\n")
    except Exception as exc:
        log.warning("post-run synth transitions write failed: %s", exc)

    log.info("post-run synthesis PROMOTED: cluster=%s score=%s margin=%s",
             attempt.cluster_iter_indices, attempt.candidate_score, attempt.margin)


def _write_attempts_log(workspace: Path,
                         attempts: list[SynthesisAttempt],
                         note: str = "") -> None:
    """Append all attempts to a per-run jsonl audit trail."""
    log_path = workspace / "post_run_synthesis_attempts.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "timestamp_utc": ts,
            "note": note,
            "attempts_count": len(attempts),
            "attempts": [a.to_dict() for a in attempts],
        }) + "\n")
