"""GP-212 — Gate-Package Recommender.

Reads `docs/concepts/problem_class_taxonomy.md`, classifies a charter into a
problem class via embedding-based cosine similarity over class definitions,
and recommends a gate package. Advisory only — never auto-applies.

Companion seam: `research_areas/private/seams/engine/GP-212_meta_solver_kernel_seam.md`
Companion spec: `research_areas/private/specs/active/engine/GP-212_meta_solver_kernel_spec.md`

Phase A (this module): scaffolds the interface. The classification body is
`NotImplementedError` until Phase 2 mining completes and the taxonomy hit-rate
fields are populated. Phase C will replace the body with embedding-based
classification.

Discipline:
  - Deterministic on (charter_text, taxonomy_path). No LLM judgment in the
    classifier; embedding cosine similarity only. Cross-LLM block from GP-151
    forbids LLM-derived problem-class labels at routing time.
  - Operator-confirmable only. Caller (rubric_mode_resolver) surfaces the
    Recommendation and waits for explicit `--accept-recommender` flag before
    applying.
  - Novel-substrate detection: when classifier confidence < novel threshold,
    return `novel=True` and refuse to suggest. Operator hand-tunes.
  - Embedding model is operator-tunable via env var `META_SOLVER_EMBED_MODEL`.

Risks and mitigations are documented in the companion seam §4 and spec §6.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Default thresholds. Operator may override via environment for experimentation.
DEFAULT_MATCH_THRESHOLD = float(os.environ.get("META_SOLVER_MATCH_THRESHOLD", "0.65"))
DEFAULT_NOVEL_THRESHOLD = float(os.environ.get("META_SOLVER_NOVEL_THRESHOLD", "0.45"))

DEFAULT_TAXONOMY_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "concepts" / "problem_class_taxonomy.md"
)

DEFAULT_EMBED_MODEL = os.environ.get("META_SOLVER_EMBED_MODEL", "gemini-embedding-001")

DEFAULT_OVERRIDE_LOG = (
    Path(__file__).resolve().parents[3] / "analytics" / "meta_solver_overrides.jsonl"
)


@dataclass(frozen=True)
class Recommendation:
    """Output of the gate-package recommender.

    Attributes:
        problem_class: Snake-case class name, or None when novel-substrate
            detection fires.
        confidence: One of {"high", "medium", "low", "novel"}. Mapping:
            high   - charter strongly matches one class AND that class has
                     mining N >= 20 (taxonomy stability == populated_stable)
            medium - strong match but mining N < 20
            low    - weak match (novel_threshold <= score < match_threshold)
            novel  - score < novel_threshold; recommender refuses to suggest
        rubric_mode: Suggested rubric_mode (newton / kepler / calibration), or
            None when novel.
        gate_flags: Suggested rubric flag overrides. Empty when novel.
        anti_pattern_inject_mode: One of {"off", "hardkill", "ceilingbreaker",
            "both"}. Defaults to "off" when novel.
        rationale: One-paragraph explanation citing taxonomy + mining sources.
            Required to be non-empty in all non-novel paths. Cites taxonomy
            entry by name and mining query path when applicable.
        novel_substrate: True iff confidence == "novel".
        secondary_class: Optional second class when composition mode fires
            (top-2 classes both above match threshold and together cover the
            charter's structural language).
    """

    problem_class: Optional[str]
    confidence: str
    rubric_mode: Optional[str]
    gate_flags: dict
    anti_pattern_inject_mode: str
    rationale: str
    novel_substrate: bool
    secondary_class: Optional[str] = None
    match_score: float = 0.0
    secondary_match_score: float = 0.0
    taxonomy_version: str = ""
    classifier_metadata: dict = field(default_factory=dict)


class TaxonomyNotPopulated(RuntimeError):
    """Raised when the taxonomy is in scaffold state (Phase A) and the
    recommender is asked to do live classification.

    Phase A scaffold returns this so callers fail loudly rather than silently
    routing on unvalidated data. Phase C replaces this with real classifier
    output.
    """


def load_taxonomy(taxonomy_path: Path = DEFAULT_TAXONOMY_PATH) -> dict[str, Any]:
    """Read and parse the problem-class taxonomy.

    Returns a dict keyed by class name. Each value contains the class's
    definition text plus structured metadata (default_rubric_mode,
    recommended_gates, anti_pattern_emphasis, N, stability).

    Phase A: returns the parsed structure but does not enrich with mining
    hit-rate data. Phase B populates hit rates after the next mining run.
    """
    if not taxonomy_path.is_file():
        raise FileNotFoundError(
            f"Problem-class taxonomy not found at {taxonomy_path}. "
            f"See GP-212 spec §2.1 for required format."
        )
    text = taxonomy_path.read_text(encoding="utf-8")
    # Lightweight section parser. The taxonomy uses level-3 headers
    # (### 2.X class_name) per the canonical format.
    classes: dict[str, dict[str, Any]] = {}
    current_class: Optional[str] = None
    current_definition: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("### 2."):
            # Flush previous class.
            if current_class is not None:
                classes[current_class] = {
                    "definition_text": "\n".join(current_definition).strip(),
                }
            # Parse new class name. Header form: "### 2.N class_name".
            parts = stripped.split(maxsplit=2)
            if len(parts) >= 3:
                current_class = parts[2].strip()
                current_definition = []
            else:
                current_class = None
                current_definition = []
        elif current_class is not None:
            current_definition.append(line)
    if current_class is not None:
        classes[current_class] = {
            "definition_text": "\n".join(current_definition).strip(),
        }
    return classes


def classify_problem_class(
    charter_text: str,
    taxonomy: dict[str, Any],
) -> tuple[Optional[str], float]:
    """Embedding-based cosine similarity classifier.

    Returns (best_match_class_name, similarity_score). When the score is below
    the novel threshold, returns (None, score).

    Phase A: NotImplementedError. The classifier body lands in Phase C, after
    Phase 2 mining produces the per-class hit rates that the recommender's
    confidence levels depend on.

    The implementation MUST be deterministic on (charter_text, taxonomy) for a
    fixed embedding model. No LLM judgment.
    """
    raise NotImplementedError(
        "GP-212 Phase A scaffold. Classification body lands in Phase C. "
        "See spec §2.2 and rollout plan §4 for sequencing. Until Phase 2 "
        "mining populates per-class hit rates, calling this function is a "
        "kernel-discipline violation."
    )


def recommend_gate_package(
    charter_text: str,
    taxonomy_path: Path = DEFAULT_TAXONOMY_PATH,
) -> Recommendation:
    """Read the taxonomy, classify the charter, return a Recommendation.

    NEVER auto-applies. The caller (e.g., rubric_mode_resolver) surfaces the
    Recommendation to the operator and waits for `--accept-recommender` before
    mutating any rubric.

    Phase A: raises TaxonomyNotPopulated. The recommender is wired but
    intentionally inert until Phase 2 mining populates hit rates and Phase C
    implements the classifier.

    Args:
        charter_text: Full text of `project_charter.md` for the substrate.
        taxonomy_path: Path to `problem_class_taxonomy.md`. Defaults to the
            canonical location.

    Returns:
        A Recommendation. When confidence == "novel", `problem_class` is None,
        `gate_flags` is empty, and the operator must hand-tune.

    Raises:
        FileNotFoundError: taxonomy file missing.
        TaxonomyNotPopulated: Phase A scaffold; mining hit rates not yet
            populated.
    """
    taxonomy = load_taxonomy(taxonomy_path)
    raise TaxonomyNotPopulated(
        "GP-212 Phase A — taxonomy is scaffolded with class definitions but "
        "per-class hit rates from mining are not yet populated. The "
        "recommender refuses to produce live recommendations until Phase 2 "
        "mining completes. See spec §4 (rollout plan) for sequencing. "
        f"Taxonomy parsed: {len(taxonomy)} classes."
    )


def log_operator_override(
    project_slug: str,
    recommendation: Recommendation,
    operator_action: str,
    operator_modifications: Optional[dict] = None,
    operator_rationale: str = "",
    log_path: Path = DEFAULT_OVERRIDE_LOG,
) -> None:
    """Append an entry to the operator-override log.

    The log is mining input for future taxonomy refinement. Per seam §4.2,
    every operator override is signal — it tells the recommender where its
    suggestions are wrong.

    Args:
        project_slug: Project name being authored.
        recommendation: The Recommendation that was produced.
        operator_action: One of {"rejected", "modified", "ignored", "accepted"}.
        operator_modifications: When `operator_action == "modified"`, the
            deltas the operator applied vs the recommendation.
        operator_rationale: Free text from the operator. Optional.
        log_path: Override-log destination. Defaults to
            `analytics/public/meta_solver_overrides.jsonl`.
    """
    import json
    from datetime import datetime, timezone

    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "project": project_slug,
        "recommended": {
            "problem_class": recommendation.problem_class,
            "confidence": recommendation.confidence,
            "rubric_mode": recommendation.rubric_mode,
            "gate_flags": recommendation.gate_flags,
            "anti_pattern_inject_mode": recommendation.anti_pattern_inject_mode,
            "rationale": recommendation.rationale,
            "novel_substrate": recommendation.novel_substrate,
            "secondary_class": recommendation.secondary_class,
            "match_score": recommendation.match_score,
            "taxonomy_version": recommendation.taxonomy_version,
        },
        "operator_action": operator_action,
        "operator_modifications": operator_modifications or {},
        "operator_rationale": operator_rationale,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
