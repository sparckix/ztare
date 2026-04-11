"""GP-029 first slice — passive latent-distance observability.

Answers the question the score trace can't: **did the mutator actually
move this iteration, semantically?** Score is a scalar projection and
stagnation counts are loop-control signals; neither distinguishes
"orbiting one basin" from "traversing distinct but still-wrong basins"
from "frozen." GP-029 Turn 1–3 walked through why that matters.

Design (per GP-029 Recommendation + Codex Turn 2):

- **Deterministic only.** Jaccard over failure-family sets, attack-
  surface node sets, and named-primitive sets, plus a normalized
  stdlib string-similarity distance over thesis.md. No embeddings, no
  LLM/API calls — adding one would create a new experimental surface
  pre-Planck-Phase-2, which Codex Turn 2 explicitly ruled out.
- **Passive.** Reads workspace files only. Writes to its own
  ``workspace/latent_distance.jsonl``. **Never read by score path,
  mutation path, or loop control.** Pure observability.
- **Per-project opt-in by construction** — if the autoresearch hook
  is called with a project whose workspace lacks the expected files,
  the record is written with ``"status": "no_prior_iter"`` or
  ``"status": "source_files_missing"`` and no classifier fires.

Schema of one appended line (mirrors GP-029 Option B, first-slice
vocabulary from Codex Turn 2)::

    {"iteration_index": 7,
     "timestamp": "2026-04-11T...",
     "score": 58,
     "score_delta": 3,
     "signature": {"failure_families": [...], "attack_surface": [...],
                   "named_primitives": [...], "thesis_fingerprint": "sha256:..."},
     "distances": {"jaccard_failure_families": 0.31,
                   "jaccard_attack_surface": 0.52,
                   "jaccard_named_primitives": 0.18,
                   "thesis_text_distance": 0.47},
     "motion_class": "semantic_move_without_score_change",
     "status": "ok"}

The motion classifier vocabulary is exactly the five labels from
Codex GP-029 Turn 2, and the thresholds below are intentionally
conservative — this is slice 1, meant to calibrate against live
data, not to produce final buckets.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.ztare.validator.set_distance import jaccard_distance


LATENT_DISTANCE_FILENAME = "latent_distance.jsonl"
"""Artifact name under ``<project_dir>/workspace/``. Append-only JSONL
so tail-reading is cheap and the file is never rewritten."""


# Classifier thresholds — slice 1, deliberately conservative. Calibrate
# after ≥ 2 live runs of trace data, per GP-029 Dependencies section.
_FREEZE_EPS = 0.02
_ORBITING_SET_MAX = 0.15
_STRUCTURAL_SET_MIN = 0.40
_SCORE_DELTA_SIGNIFICANT = 5


@dataclass(frozen=True)
class IterSignature:
    """Three set-based features + thesis fingerprint + raw thesis text.

    Raw text is held so the consumer can compute string distance
    against the next iteration without re-reading the previous
    ``thesis.md``. Fingerprint is hex-sha256 for quick equality check.
    """

    failure_families: tuple[str, ...]
    attack_surface: tuple[str, ...]
    named_primitives: tuple[str, ...]
    thesis_text: str
    thesis_fingerprint: str

    def to_public_dict(self) -> dict[str, Any]:
        """Serializable form without the raw text (too large for JSONL)."""
        return {
            "failure_families": list(self.failure_families),
            "attack_surface": list(self.attack_surface),
            "named_primitives": list(self.named_primitives),
            "thesis_fingerprint": self.thesis_fingerprint,
        }


@dataclass(frozen=True)
class LatentDistanceRecord:
    """One iter-over-iter distance record, written as one JSONL line."""

    iteration_index: int
    timestamp: str
    score: int | None
    score_delta: int | None
    signature: IterSignature
    distances: dict[str, float] = field(default_factory=dict)
    motion_class: str = ""
    status: str = "ok"


# ---------------------------------------------------------------------------
# Signature extraction
# ---------------------------------------------------------------------------


def _safe_list_of_str(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _thesis_fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def extract_iter_signature_from_paths(
    *,
    latest_eval_results_path: Path,
    thesis_path: Path,
) -> IterSignature | None:
    """Build an ``IterSignature`` by reading two workspace files.

    Returns ``None`` when either file is missing or malformed — the
    caller's contract is that this is an observability feature, and a
    missing source file must not break the loop. The caller writes a
    ``source_files_missing`` status record instead.
    """

    if not latest_eval_results_path.exists() or not thesis_path.exists():
        return None
    try:
        eval_data = json.loads(latest_eval_results_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    try:
        thesis_text = thesis_path.read_text(encoding="utf-8")
    except OSError:
        return None

    score_contract = eval_data.get("score_contract")
    if not isinstance(score_contract, dict):
        score_contract = {}

    failure_families = _safe_list_of_str(
        score_contract.get("derived_constraint_failure_families")
    )
    gap_types = _safe_list_of_str(score_contract.get("evidence_gap_types"))
    failure_family_set = tuple(sorted(set(failure_families + gap_types)))

    # Attack surface: DAG node IDs paired with their labels. Falling back
    # to top-level ``probability_dag`` because that's what gets written
    # to ``latest_eval_results.json`` each iter.
    dag = eval_data.get("probability_dag") or {}
    nodes = dag.get("nodes") if isinstance(dag, dict) else None
    attack_surface_items: list[str] = []
    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id", "")).strip()
            label = str(node.get("label", "")).strip()
            if node_id or label:
                attack_surface_items.append(f"{node_id}:{label}" if node_id else label)
    attack_surface_set = tuple(sorted(set(attack_surface_items)))

    # Named primitives: the union of the two "what is the thesis
    # committing to" string lists the score contract already emits.
    primitive_items = _safe_list_of_str(
        score_contract.get("derived_constraint_targets")
    ) + _safe_list_of_str(score_contract.get("evidence_gap_targets"))
    named_primitive_set = tuple(sorted(set(primitive_items)))

    return IterSignature(
        failure_families=failure_family_set,
        attack_surface=attack_surface_set,
        named_primitives=named_primitive_set,
        thesis_text=thesis_text,
        thesis_fingerprint=_thesis_fingerprint(thesis_text),
    )


# ---------------------------------------------------------------------------
# Distance + classification
# ---------------------------------------------------------------------------


def compute_distances(
    prev: IterSignature,
    curr: IterSignature,
) -> dict[str, float]:
    """Four scalar distances between two iter signatures.

    - Three Jaccard distances over the set-valued features
    - One normalized stdlib text-similarity distance over thesis.md
      via ``difflib.SequenceMatcher.ratio()``. Not Levenshtein, but
      deterministic, stdlib-only, and sufficient for freeze detection
      and coarse paraphrase detection at the slice-1 granularity.
    """

    thesis_similarity = difflib.SequenceMatcher(
        a=prev.thesis_text,
        b=curr.thesis_text,
        autojunk=False,
    ).ratio()
    return {
        "jaccard_failure_families": jaccard_distance(
            set(prev.failure_families), set(curr.failure_families)
        ),
        "jaccard_attack_surface": jaccard_distance(
            set(prev.attack_surface), set(curr.attack_surface)
        ),
        "jaccard_named_primitives": jaccard_distance(
            set(prev.named_primitives), set(curr.named_primitives)
        ),
        "thesis_text_distance": 1.0 - thesis_similarity,
    }


def classify_motion(
    distances: dict[str, float],
    score_delta: int | None,
) -> str:
    """Return one of the five slice-1 motion labels (Codex Turn 2).

    Vocabulary:

    - ``freeze``: near-zero everywhere. Mutator is repeating itself.
    - ``orbiting``: low set deltas, moderate-or-higher thesis text
      churn. Mutator is rephrasing inside one basin.
    - ``structural_move``: high Jaccard on at least one set axis.
      Mutator is swapping structural content (primitives, attack
      surface, or failure families changed materially).
    - ``score_only_change``: low motion with non-trivial score delta.
      Suggests the score moved without the thesis moving — either
      noise or judge-softening (GP-030-adjacent).
    - ``semantic_move_without_score_change``: motion present, score
      flat. The case GP-029 was built to name.
    """

    text = distances.get("thesis_text_distance", 0.0)
    max_set = max(
        distances.get("jaccard_failure_families", 0.0),
        distances.get("jaccard_attack_surface", 0.0),
        distances.get("jaccard_named_primitives", 0.0),
    )
    score_moved = (
        score_delta is not None and abs(int(score_delta)) >= _SCORE_DELTA_SIGNIFICANT
    )

    if text < _FREEZE_EPS and max_set < _FREEZE_EPS:
        return "freeze"
    if max_set >= _STRUCTURAL_SET_MIN:
        return "structural_move"
    if max_set < _ORBITING_SET_MAX and text >= _FREEZE_EPS and not score_moved:
        return "orbiting"
    if max_set < _ORBITING_SET_MAX and text < _ORBITING_SET_MAX and score_moved:
        return "score_only_change"
    if not score_moved:
        return "semantic_move_without_score_change"
    return "structural_move"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _read_last_jsonl_record(path: Path) -> dict[str, Any] | None:
    """Return the last parseable JSONL record in ``path``, or ``None``.

    Append-only JSONL means the last line is the previous iter. We
    don't tail-seek — these files are tiny (one short record per iter)
    — but we do tolerate trailing blank lines and malformed earlier
    lines so a corrupt mid-file entry doesn't poison the next record.
    """

    if not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _reconstruct_signature_from_record(record: dict[str, Any]) -> IterSignature | None:
    """Best-effort signature reconstruction from a persisted JSONL record.

    The persisted record intentionally does not include the raw
    ``thesis_text`` (too large), so reconstructed signatures can be
    used for set-valued Jaccard but **not** for the text-distance
    metric. Caller falls back to reading the prior thesis.md from
    disk if it needs raw text — but for GP-029's first slice we write
    the text distance against the fingerprint difference: a
    fingerprint mismatch implies the thesis text moved, and we store
    the text distance only when we have both raw texts in memory.
    """

    sig_data = record.get("signature")
    if not isinstance(sig_data, dict):
        return None
    return IterSignature(
        failure_families=tuple(_safe_list_of_str(sig_data.get("failure_families"))),
        attack_surface=tuple(_safe_list_of_str(sig_data.get("attack_surface"))),
        named_primitives=tuple(_safe_list_of_str(sig_data.get("named_primitives"))),
        thesis_text="",  # not persisted — set-distance only
        thesis_fingerprint=str(sig_data.get("thesis_fingerprint", "")),
    )


def record_latent_distance(
    *,
    project_dir: Path,
    iteration_index: int,
    score: int | None,
) -> LatentDistanceRecord:
    """End-of-iter hook. Safe to call from the autoresearch loop.

    Reads ``<project_dir>/latest_eval_results.json`` and
    ``<project_dir>/current_iteration.md`` to build the current
    signature. ``current_iteration.md`` holds the candidate this iter
    *just evaluated*, regardless of whether it was admitted as the new
    best — so this captures motion through rejected candidates too,
    which is the whole point (the score trace can't see rejected
    moves, but GP-029 should). Reads the last record of
    ``<project_dir>/workspace/latent_distance.jsonl`` to get the prior
    signature (if any). Appends the new record.

    Returns the record that was written. The caller can ignore the
    return value — this function never raises on missing/malformed
    input files; it writes a status-annotated record instead.
    """

    workspace_dir = project_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = workspace_dir / LATENT_DISTANCE_FILENAME

    timestamp = datetime.now().isoformat()

    curr = extract_iter_signature_from_paths(
        latest_eval_results_path=project_dir / "latest_eval_results.json",
        thesis_path=project_dir / "current_iteration.md",
    )

    prev_record = _read_last_jsonl_record(artifact_path)
    prev_score = None
    if isinstance(prev_record, dict):
        prev_score = prev_record.get("score")
        if not isinstance(prev_score, int):
            prev_score = None
    score_delta: int | None
    if score is None or prev_score is None:
        score_delta = None
    else:
        score_delta = score - prev_score

    if curr is None:
        record = LatentDistanceRecord(
            iteration_index=iteration_index,
            timestamp=timestamp,
            score=score,
            score_delta=score_delta,
            signature=IterSignature(
                failure_families=(),
                attack_surface=(),
                named_primitives=(),
                thesis_text="",
                thesis_fingerprint="",
            ),
            distances={},
            motion_class="",
            status="source_files_missing",
        )
        _append_record(artifact_path, record)
        return record

    prev_sig = _reconstruct_signature_from_record(prev_record) if prev_record else None
    if prev_sig is None:
        record = LatentDistanceRecord(
            iteration_index=iteration_index,
            timestamp=timestamp,
            score=score,
            score_delta=score_delta,
            signature=curr,
            distances={},
            motion_class="",
            status="no_prior_iter",
        )
        _append_record(artifact_path, record)
        return record

    distances = compute_distances(prev_sig, curr)
    # Fingerprint-based text-distance override: the reconstructed prev
    # signature has no raw text, so compute_distances produced a text
    # distance against an empty string (1.0). Replace with a coarse
    # fingerprint-equality proxy: 0.0 if fingerprints match, 1.0 if they
    # don't. Slice 2 can upgrade to real text distance by re-reading the
    # prior thesis snapshot from history if needed.
    if not prev_sig.thesis_text:
        distances["thesis_text_distance"] = (
            0.0 if prev_sig.thesis_fingerprint == curr.thesis_fingerprint else 1.0
        )

    motion_class = classify_motion(distances, score_delta)
    record = LatentDistanceRecord(
        iteration_index=iteration_index,
        timestamp=timestamp,
        score=score,
        score_delta=score_delta,
        signature=curr,
        distances=distances,
        motion_class=motion_class,
        status="ok",
    )
    _append_record(artifact_path, record)
    return record


def _append_record(path: Path, record: LatentDistanceRecord) -> None:
    """Append one serialized record line. Defensive against I/O errors —
    an observability writer must never break the main loop."""

    payload = {
        "iteration_index": record.iteration_index,
        "timestamp": record.timestamp,
        "score": record.score,
        "score_delta": record.score_delta,
        "signature": record.signature.to_public_dict(),
        "distances": record.distances,
        "motion_class": record.motion_class,
        "status": record.status,
    }
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except OSError:
        # Deliberate: observability writer must be fail-silent.
        # The record is lost for this iter but the loop continues.
        pass
