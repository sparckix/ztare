"""GP-102 Reflexive Primitive Discovery Audit.

Periodic diagnostic that scans cross-project telemetry for structural
paralysis -- the "Groundhog Day" signature where the same gate fails with
similar residual across K+ iterations after all recovery primitives have
fired.

Uses Deming's SPC discriminator (common-cause vs special-cause variation)
to prevent false-positive audits on genuinely hard substrates.

Output: a seam draft at n=0 for principal review. No code is written.
No primitive is automatically promoted. The LLM's role is Inception --
applying existing ZTARE legs to the diagnosed stuck layer. Diagnosis
(Components 1-3) is deterministic; creativity (Component 4) is LLM.

Design constraints (from GP-102 seam):
1. No false-positive audits on difficult substrates (variance discriminator)
2. Artisan-mode compatible -- no GP-070 orchestrator required
3. Zero new infrastructure -- uses iteration_telemetry.jsonl,
   structural_memory.json, latent_distance.jsonl, git log
4. Output is a seam, not code. Principal disposes.
5. Must not re-propose existing primitives (reads catalog first)
6. Fail-silent on missing telemetry

Usage:
  python -m src.ztare.validator.reflexive_audit \\
      --projects-dir projects/ \\
      --primitives-catalog research_areas/private/philosophy/reflexive_engineering_primitives.md \\
      [--since 2026-04-01] \\
      [--K 5] \\
      [--stagnation-threshold 3] \\
      [--output-dir research_areas/private/seams/reflexive/]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from src.ztare.common.llm_runtime import LLMRuntime, PRODUCTION_CALL_RETRIES
from src.ztare.common.paths import REPO_ROOT, PROJECTS_DIR

_RUNTIME = LLMRuntime()
_COMMITTEE_MODEL = os.environ.get("ZTARE_REFLEXIVE_AUDIT_MODEL", "gemini-2.5-flash")

_DEFAULT_SEAM_OUTPUT_DIR = REPO_ROOT / "research_areas" / "private" / "seams" / "reflexive"
_DEFAULT_PRIMITIVES_CATALOG = (
    REPO_ROOT / "research_areas" / "private" / "philosophy" / "reflexive_engineering_primitives.md"
)
_AUDIT_REPORT_FILENAME = "reflexive_audit_report.json"

# Gate name fragments that map to stuck layers (deterministic classification).
_GATE_TO_LAYER: dict[str, str] = {
    "farther_tail":     "Grammar / Tail Law",
    "parsimony":        "Review Layer (Complexity Penalty)",
    "extrapolation":    "Gate Architecture (Holdout Boundary)",
    "evidence_fit":     "Fit Engine / Primitive Library",
    "uniqueness_gap":   "Review Layer (Identifiability)",
    "naming_import":    "Grammar / Vocabulary",
    "composition":      "Component D / Composition Loop",
    "holdout":          "Holdout Gate",
}


# ---------------------------------------------------------------------------
# Component 1: Data structures
# ---------------------------------------------------------------------------

@dataclass
class ProjectTelemetrySummary:
    """Per-project telemetry summary for the discriminator."""
    project_id: str
    workspace_path: Path
    stagnation_count: int
    best_score: int
    score_trajectory: list[int]           # last K scores (oldest → newest)
    gate_failure_history: list[dict]      # last K iteration records with failed_gate_ids
    families_exhausted: int               # from structural_memory.json
    families_total: int
    recovery_exhausted: bool              # proxy for "Component D / GP-087 had chances"
    latest_champion_expression: str | None
    latent_distance_trend: float | None   # slope of last-K latent distances; None if absent


class AuditVerdict(Enum):
    MACHINERY_BROKEN = "machinery_broken"               # trigger audit — same gate failing, stagnating
    SCIENCE_IS_HARD  = "science_is_hard"                # all clear — diverse gate failures, hard substrate
    AMBIGUOUS        = "ambiguous"                      # report, don't flag
    INSUFFICIENT_DATA = "insufficient_data"             # skip — too few iterations or too early
    GOODHARTED_SPECIFICATION = "goodharted_specification"  # GP-105: high score, wrong question


@dataclass
class FailureDiagnosis:
    """Deterministic (no LLM) failure classification."""
    failure_mode: str              # "primitive_exhaustion" | "persistent_stagnation" | "gate_ceiling"
    stuck_layer: str               # "Grammar / Tail Law" | "Gate Architecture" | etc.
    dominant_failing_gate: str     # gate that fails most often (or "" if none)
    evidence: dict[str, Any]       # raw telemetry fields supporting this diagnosis


@dataclass
class SeamProposal:
    """What the inception committee produced."""
    primitive_name: str            # proposed name
    ztare_leg: str                 # "Invert" | "Compress" | "Adversarial Disagreement"
    stuck_layer: str
    proposal_text: str             # full seam-body draft from LLM
    committee_model: str
    target_sandbox: str = ""       # project_id of the stagnated sandbox that motivated this proposal
                                   # (retroactive falsification: principal must re-run this sandbox
                                   # with the new primitive; if stagnation is not reduced,
                                   # the primitive is reverted as false-positive bureaucracy)


@dataclass
class ArtisanActivitySummary:
    """Git-derived artisan activity signals."""
    friction_commit_count: int     # commits with "fix", "revert", "workaround" in message
    layer_churn: dict[str, int]    # path_prefix → commit_count since last audit
    high_churn_layers: list[str]   # layers with churn > 2x median


@dataclass
class ProjectAuditResult:
    project_id: str
    verdict: AuditVerdict
    diagnosis: FailureDiagnosis | None
    proposal: SeamProposal | None
    seam_path: Path | None
    evidence_summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    audit_timestamp_utc: str
    projects_scanned: int
    projects_flagged: int
    results: list[ProjectAuditResult] = field(default_factory=list)
    artisan_activity: ArtisanActivitySummary | None = None


# ---------------------------------------------------------------------------
# A2 helper: count total science iterations across all projects
# ---------------------------------------------------------------------------

def _count_total_science_iterations(projects_dir: Path) -> int:
    """Count total science iterations across all projects for the A2 meta-budget guard.

    Reads iteration_telemetry.jsonl from each project workspace (non-empty lines = 1 iter).
    Returns 0 if no telemetry found.
    """
    total = 0
    if not projects_dir.exists():
        return total
    for p in projects_dir.iterdir():
        if not p.is_dir():
            continue
        tel = p / "workspace" / "iteration_telemetry.jsonl"
        if tel.exists():
            try:
                total += sum(1 for line in tel.read_text().splitlines() if line.strip())
            except Exception:
                pass
    return total


# ---------------------------------------------------------------------------
# Component 1: gather_telemetry — Cross-Project Scanner
# ---------------------------------------------------------------------------

def gather_telemetry(
    projects_dir: Path,
    *,
    K: int = 5,
    stagnation_threshold: int = 3,
) -> list[ProjectTelemetrySummary]:
    """Scan all project workspaces for stagnation signals.

    For each project with a workspace/:
    1. Read iteration_telemetry.jsonl for stagnation_count, score, gate data
    2. Read structural_memory.json for family exhaustion depth
    3. Read latent_distance.jsonl for trend
    4. Return ProjectTelemetrySummary per project

    Fail-silent: projects missing required artifacts are skipped.
    """
    summaries: list[ProjectTelemetrySummary] = []
    if not projects_dir.is_dir():
        return summaries

    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        project_id = project_dir.name
        workspace = project_dir / "workspace"
        if not workspace.is_dir():
            continue

        telemetry_path = workspace / "iteration_telemetry.jsonl"
        if not telemetry_path.exists():
            continue

        try:
            summary = _parse_project_telemetry(
                project_id, workspace, telemetry_path, K=K,
                stagnation_threshold=stagnation_threshold,
            )
            if summary is not None:
                summaries.append(summary)
        except Exception:
            pass  # fail-silent per constraint 6

    return summaries


def _parse_project_telemetry(
    project_id: str,
    workspace: Path,
    telemetry_path: Path,
    *,
    K: int,
    stagnation_threshold: int,
) -> ProjectTelemetrySummary | None:
    """Parse a single project's telemetry. Returns None if insufficient data."""
    raw_lines = telemetry_path.read_text(encoding="utf-8").splitlines()
    iteration_records: list[dict] = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Only include iteration records from the most recent run
        if rec.get("record_type") == "iteration":
            iteration_records.append(rec)

    if not iteration_records:
        return None

    # Use only the most recent run's iterations (detect run boundary by run_id)
    if iteration_records:
        latest_run_id = iteration_records[-1].get("run_id")
        run_records = [r for r in iteration_records if r.get("run_id") == latest_run_id]
    else:
        run_records = iteration_records

    if not run_records:
        return None

    last_K = run_records[-K:] if len(run_records) >= K else run_records[:]
    score_trajectory = [r.get("score", 0) for r in last_K]
    stagnation_count = run_records[-1].get("stagnation_count", 0)
    best_score_in_run = max((r.get("score", 0) for r in run_records), default=0)

    gate_failure_history = [
        {
            "iteration_index": r.get("iteration_index"),
            "score": r.get("score"),
            "failed_gate_ids": r.get("failed_gate_ids", []),
            "gate_failure_count": r.get("gate_failure_count", 0),
        }
        for r in last_K
    ]

    # Structural memory: family exhaustion
    # Schema: families is a list of dicts; exhaustion is proxied by
    # composition_primitive_count > 0 (Component D has fired) + stagnation.
    families_exhausted = 0
    families_total = 0
    composition_primitive_count = 0
    sm_path = workspace / "structural_memory.json"
    if sm_path.exists():
        try:
            sm = json.loads(sm_path.read_text(encoding="utf-8"))
            families = sm.get("families", [])
            if isinstance(families, list):
                families_total = len(families)
                # No explicit "exhausted" flag — use distinct family count as proxy.
                # Families seen only once = candidates exhausted in one attempt.
                families_exhausted = sum(
                    1 for f in families
                    if isinstance(f, dict) and f.get("seen_count", 1) <= 1
                )
            elif isinstance(families, dict):
                families_total = len(families)
                families_exhausted = sum(
                    1 for v in families.values()
                    if isinstance(v, dict) and v.get("exhausted", False)
                )
            composition_primitive_count = sm.get("composition_primitive_count", 0)
        except Exception:
            pass

    # Champion expression from fit_result.json
    latest_champion_expression: str | None = None
    fit_result_path = workspace / "fit_result.json"
    if fit_result_path.exists():
        try:
            fr = json.loads(fit_result_path.read_text(encoding="utf-8"))
            latest_champion_expression = fr.get("expression")
        except Exception:
            pass

    # Latent distance trend (slope of last K)
    latent_distance_trend: float | None = None
    ld_path = workspace / "latent_distance.jsonl"
    if ld_path.exists():
        try:
            ld_lines = ld_path.read_text(encoding="utf-8").splitlines()
            ld_values: list[float] = []
            for line in ld_lines[-K:]:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                v = rec.get("latent_distance") or rec.get("distance")
                if isinstance(v, (int, float)):
                    ld_values.append(float(v))
            if len(ld_values) >= 2:
                # Simple linear slope (last point minus first, normalized)
                latent_distance_trend = (ld_values[-1] - ld_values[0]) / max(1, len(ld_values) - 1)
        except Exception:
            pass

    # recovery_exhausted proxy:
    # Component D has fired (composition_primitive_count > 0) AND still stagnating.
    # This is the observable "all recovery mechanisms have had an opportunity to fire"
    # condition without needing an explicit exhausted flag per family.
    # Fallback: if no composition data, fall back to family-level exhaustion ratio.
    if composition_primitive_count > 0:
        recovery_exhausted = stagnation_count >= stagnation_threshold
    else:
        # Component D hasn't fired yet — use family-level proxy
        recovery_exhausted = (
            families_total > 0
            and families_exhausted >= max(1, families_total // 2)
            and stagnation_count >= stagnation_threshold
        )

    return ProjectTelemetrySummary(
        project_id=project_id,
        workspace_path=workspace,
        stagnation_count=stagnation_count,
        best_score=best_score_in_run,
        score_trajectory=score_trajectory,
        gate_failure_history=gate_failure_history,
        families_exhausted=families_exhausted,
        families_total=families_total,
        recovery_exhausted=recovery_exhausted,
        latest_champion_expression=latest_champion_expression,
        latent_distance_trend=latent_distance_trend,
    )


# ---------------------------------------------------------------------------
# Component 2: discriminate — Variance-of-Failure Classifier
# ---------------------------------------------------------------------------

def discriminate(
    summary: ProjectTelemetrySummary,
    *,
    K: int = 5,
) -> AuditVerdict:
    """Apply Deming SPC discriminator: common-cause vs special-cause variation.

    Returns MACHINERY_BROKEN, SCIENCE_IS_HARD, AMBIGUOUS, or INSUFFICIENT_DATA.

    Logic:
    1. stagnation_count < 3 → INSUFFICIENT_DATA (too early)
    2. not recovery_exhausted → INSUFFICIENT_DATA (recovery primitives haven't fired)
    3. Extract gate failures from last K iterations of gate_failure_history
    4. Compute gate_failure_variance:
       - 1 gate fails in >80% of iterations → LOW_VARIANCE → MACHINERY_BROKEN
       - 3+ distinct gates, no single gate >50% → HIGH_VARIANCE → SCIENCE_IS_HARD
       - Otherwise → AMBIGUOUS
    5. Latent distance confirmation (optional):
       - Flat latent trend + low gate variance → confirms MACHINERY_BROKEN
    """
    if summary.stagnation_count < 3:
        return AuditVerdict.INSUFFICIENT_DATA

    # A project that has already scored 100 is not structurally broken.
    if summary.best_score >= 100:
        return AuditVerdict.INSUFFICIENT_DATA

    if not summary.recovery_exhausted:
        return AuditVerdict.INSUFFICIENT_DATA

    history = summary.gate_failure_history
    if not history:
        return AuditVerdict.INSUFFICIENT_DATA

    # Count gate failures across last K iterations
    gate_failure_counts: dict[str, int] = {}
    n_iters_with_any_failure = 0
    for rec in history:
        failed = rec.get("failed_gate_ids", [])
        if failed:
            n_iters_with_any_failure += 1
            for gate in failed:
                gate_failure_counts[gate] = gate_failure_counts.get(gate, 0) + 1

    n_iters = len(history)
    if n_iters_with_any_failure == 0:
        # No gate failures at all — stagnation is from qualitative scoring only.
        # Before flagging MACHINERY_BROKEN, check latent distance: if the system
        # is still exploring (nonzero latent motion), it may be SCIENCE_IS_HARD,
        # not a structural wall. Only flag as MACHINERY_BROKEN if latent motion
        # is flat (trend near zero) — confirming the search is genuinely stuck.
        ld_trend = summary.latent_distance_trend
        if ld_trend is not None and abs(ld_trend) > 0.05:
            # Active latent exploration + qualitative plateau = hard substrate
            return AuditVerdict.SCIENCE_IS_HARD
        return AuditVerdict.MACHINERY_BROKEN

    distinct_gates = len(gate_failure_counts)
    dominant_gate = max(gate_failure_counts, key=gate_failure_counts.get)
    dominant_rate = gate_failure_counts[dominant_gate] / n_iters

    if dominant_rate >= 0.8:
        # Low variance: same gate dominates → structural wall
        return AuditVerdict.MACHINERY_BROKEN
    elif distinct_gates >= 3 and dominant_rate <= 0.5:
        # High variance: diverse failures → genuinely hard substrate
        return AuditVerdict.SCIENCE_IS_HARD
    else:
        return AuditVerdict.AMBIGUOUS


# ---------------------------------------------------------------------------
# Component 3: classify_failure_mode — Deterministic Diagnosis (NO LLM)
# ---------------------------------------------------------------------------

def classify_failure_mode(
    summary: ProjectTelemetrySummary,
) -> FailureDiagnosis:
    """Deterministic classifier: maps telemetry to typed failure mode.

    No LLM call. Diagnosis is math, not judgment. (Compress principle:
    if the answer is deterministic, don't route it through a stochastic system.)
    """
    # Determine dominant failing gate
    gate_failure_counts: dict[str, int] = {}
    for rec in summary.gate_failure_history:
        for gate in rec.get("failed_gate_ids", []):
            gate_failure_counts[gate] = gate_failure_counts.get(gate, 0) + 1

    dominant_gate = ""
    if gate_failure_counts:
        dominant_gate = max(gate_failure_counts, key=gate_failure_counts.get)

    # Map gate name to stuck layer
    stuck_layer = "Unknown Layer"
    for fragment, layer in _GATE_TO_LAYER.items():
        if fragment in dominant_gate:
            stuck_layer = layer
            break

    # Determine failure mode
    if summary.recovery_exhausted:
        failure_mode = "primitive_exhaustion"
        if not gate_failure_counts:
            # Qualitative stagnation with no hard gate failures — grammar ceiling variant
            failure_mode = "qualitative_ceiling"
            stuck_layer = "Review Layer (Qualitative Scoring)"
    elif gate_failure_counts:
        failure_mode = "persistent_stagnation"
        # Refine stuck_layer from dominant gate if recovery not exhausted
    else:
        failure_mode = "persistent_stagnation"
        stuck_layer = "Unknown — no gate failures logged"

    evidence = {
        "stagnation_count": summary.stagnation_count,
        "best_score": summary.best_score,
        "score_trajectory": summary.score_trajectory,
        "families_exhausted": summary.families_exhausted,
        "families_total": summary.families_total,
        "gate_failure_counts": gate_failure_counts,
        "dominant_failing_gate": dominant_gate,
        "latent_distance_trend": summary.latent_distance_trend,
        "latest_champion_expression": summary.latest_champion_expression,
    }

    return FailureDiagnosis(
        failure_mode=failure_mode,
        stuck_layer=stuck_layer,
        dominant_failing_gate=dominant_gate,
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# Component 4: inception_committee — LLM Proposes the Cure (NOT the Diagnosis)
# ---------------------------------------------------------------------------

_INCEPTION_PROMPT_TEMPLATE = """\
You are a ZTARE process engineer running a reflexive audit.

The deterministic SPC monitor has declared MACHINERY_BROKEN for project: {project_id}

## Deterministic Diagnosis (final — do not re-diagnose)

Failure Mode: {failure_mode}
Stuck Layer: {stuck_layer}
Dominant Failing Gate: {dominant_failing_gate}

Evidence:
- Stagnation count: {stagnation_count}
- Best score achieved: {best_score}
- Score trajectory (last K): {score_trajectory}
- Family exhaustion: {families_exhausted} / {families_total}
- Dominant gate failures: {gate_failure_counts}
- Latent distance trend: {latent_distance_trend}
- Champion expression: {champion_expression}

## Existing Reflexive Primitives (do NOT re-propose these)

{primitives_catalog}

## Your Task: INCEPTION

Do not diagnose. The diagnosis is final.

Your task is Inception: apply the ZTARE Three Legs (Invert, Compress, Adversarial\
 Disagreement) reflexively to the identified stuck layer and propose ONE new\
 Reflexive Engineering Primitive that would prevent this failure mode.

ZTARE Three Legs:
- Invert (Leg 1): Ask "what would kill this?" before asking "does this work?" Apply\
 this to the stuck layer — what assumption in the layer should be inverted?
- Compress (Leg 2): Prefer the form with fewer free parameters that still captures\
 the essential structure. Apply to the layer — what is the minimal representation\
 that exposes the wall without the noise?
- Adversarial Disagreement (Leg 3): The review layer must include perspectives that\
 genuinely disagree. Apply to the layer — what adversarial reviewer is missing?

If existing primitives already cover this failure mode, say so explicitly and return\
 "NO_NEW_PRIMITIVE" as the primitive name.

## Meta-Parsimony Constraint (One-In, One-Out)

If you propose a new primitive, you MUST also identify either:
(a) An existing primitive in the catalog that this new one supersedes or renders\
 obsolete — name it explicitly, or
(b) A mathematical justification for why the overall system complexity must increase\
 (i.e., why this failure mode cannot be handled by combining existing primitives).

If you cannot satisfy either (a) or (b), return "NO_NEW_PRIMITIVE".

## Output format (required)

PRIMITIVE_NAME: <short descriptive name>
ZTARE_LEG: <Invert | Compress | Adversarial Disagreement>
TARGET_LAYER: <the stuck layer this primitive addresses>
EIGENQUESTION: <the single question this primitive answers for the operator>
PROBLEM_STATEMENT: <2-3 sentences: what failure this prevents and why the existing\
 primitives don't cover it>
PROPOSED_PRIMITIVE: <3-5 sentences: what the primitive is, how it works, what ZTARE\
 leg it applies and how>
TELEMETRY_EVIDENCE: <1-2 sentences: which specific telemetry signals motivated this\
 proposal>
DEBATE_OPENING: <1 sentence the adversarial reviewer should use to challenge this\
 proposal>
"""


def inception_committee(
    diagnosis: FailureDiagnosis,
    project_id: str,
    primitives_catalog_path: Path,
) -> SeamProposal | None:
    """Route the deterministic diagnosis to the inception committee.

    The LLM DOES NOT diagnose. Diagnosis is final (Component 3).
    The LLM applies ZTARE legs to the stuck layer and proposes a new primitive.

    Returns None if the committee concludes existing primitives cover the failure.
    """
    primitives_text = ""
    if primitives_catalog_path.exists():
        try:
            primitives_text = primitives_catalog_path.read_text(encoding="utf-8")
        except Exception:
            primitives_text = "(catalog unreadable)"
    else:
        primitives_text = "(catalog not found)"

    prompt = _INCEPTION_PROMPT_TEMPLATE.format(
        project_id=project_id,
        failure_mode=diagnosis.failure_mode,
        stuck_layer=diagnosis.stuck_layer,
        dominant_failing_gate=diagnosis.dominant_failing_gate or "(none logged)",
        stagnation_count=diagnosis.evidence.get("stagnation_count", "?"),
        best_score=diagnosis.evidence.get("best_score", "?"),
        score_trajectory=diagnosis.evidence.get("score_trajectory", []),
        families_exhausted=diagnosis.evidence.get("families_exhausted", "?"),
        families_total=diagnosis.evidence.get("families_total", "?"),
        gate_failure_counts=diagnosis.evidence.get("gate_failure_counts", {}),
        latent_distance_trend=diagnosis.evidence.get("latent_distance_trend", "N/A"),
        champion_expression=str(diagnosis.evidence.get("latest_champion_expression", ""))[:200],
        primitives_catalog=primitives_text[:4000],  # cap to avoid context overflow
    )

    try:
        response = _RUNTIME.call_text(
            prompt,
            model_id=_COMMITTEE_MODEL,
            retries=3,
            timeout_seconds=120,
            request_label="GP-102 inception committee",
            progress_printer=print,
            transient_wait_seconds=10,
            timeout_wait_seconds=10,
        )
        raw = response.text or ""
    except Exception as exc:
        print(f"    >> GP-102: inception committee failed: {exc}")
        return None

    # Parse the structured output
    def _extract(key: str) -> str:
        prefix = f"{key}:"
        for line in raw.splitlines():
            if line.strip().upper().startswith(key.upper() + ":"):
                return line.split(":", 1)[1].strip()
        return ""

    primitive_name = _extract("PRIMITIVE_NAME")
    if not primitive_name or primitive_name.upper() == "NO_NEW_PRIMITIVE":
        print(f"    >> GP-102: committee found no new primitive needed for {project_id}")
        return None

    ztare_leg = _extract("ZTARE_LEG")

    return SeamProposal(
        primitive_name=primitive_name,
        ztare_leg=ztare_leg,
        stuck_layer=diagnosis.stuck_layer,
        proposal_text=raw,
        committee_model=_COMMITTEE_MODEL,
        target_sandbox=project_id,  # retroactive falsification target
    )


# ---------------------------------------------------------------------------
# Component 5: propose_seam — Seam Draft Output
# ---------------------------------------------------------------------------

def propose_seam(
    proposal: SeamProposal,
    diagnosis: FailureDiagnosis,
    project_id: str,
    output_dir: Path,
) -> Path | None:
    """Draft a seam at n=0 for principal review.

    Does NOT promote. Principal must review before the seam enters active work.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    safe_name = proposal.primitive_name.replace(" ", "_").replace("/", "-").lower()
    filename = f"reflexive_audit_{today}_{project_id}_{safe_name}.md"
    seam_path = output_dir / filename

    evidence = diagnosis.evidence
    seam_content = f"""\
# Reflexive Audit Seam: {proposal.primitive_name}

## Status

Open — opened {today}, proposed by `reflexive_primitive_audit` (GP-102)

**Principal action required:** Review and decide: promote to active work, hold, or discard.

---

## Eigenquestion

What new Reflexive Engineering Primitive would prevent the structural paralysis
observed in project `{project_id}` from recurring silently in future projects?

---

## Problem Statement

Project `{project_id}` entered MACHINERY_BROKEN state.

- Failure Mode: `{diagnosis.failure_mode}`
- Stuck Layer: `{diagnosis.stuck_layer}`
- Dominant Failing Gate: `{diagnosis.dominant_failing_gate or "(none logged)"}`
- Stagnation Count: {evidence.get("stagnation_count", "?")}
- Best Score: {evidence.get("best_score", "?")}
- Score Trajectory: {evidence.get("score_trajectory", [])}
- Family Exhaustion: {evidence.get("families_exhausted", "?")}/{evidence.get("families_total", "?")}

The diagnostic ran after all known recovery mechanisms (Component D / GP-087) had
opportunities to fire. The engine was structurally paralyzed, not epistemically
frustrated by a hard substrate.

---

## Proposed Primitive

**Name:** {proposal.primitive_name}
**ZTARE Leg Applied:** {proposal.ztare_leg}
**Target Layer:** {proposal.stuck_layer}

Full inception committee output:

---

{proposal.proposal_text}

---

## Telemetry Evidence

```json
{json.dumps(evidence, indent=2, default=str)[:1500]}
```

---

## Retroactive Falsification Gate (Required Before Promotion)

**Target sandbox:** `{proposal.target_sandbox}`

Before this seam can be raised to `status: active`, the principal MUST:
1. Re-run the target sandbox above with the proposed primitive in effect
2. Confirm that the stagnation is reduced (new run breaks out of the {evidence.get("stagnation_count", "?")} stagnation)
3. Record the new best score and gate failure profile in Turn 2 of the Debate Log below

If the sandbox does NOT break the stagnation, this primitive is reverted as\
 false-positive bureaucracy. No exceptions.

---

## Debate Log

### Turn 1 — reflexive_primitive_audit (automated, {today})

SENTINEL_DECISION: hold

Automated seam. Principal must review before promoting. The inception committee
(model: `{proposal.committee_model}`) proposed the primitive above, but the
creative judgment of whether this primitive is real, useful, and distinct from
existing catalog entries belongs to the principal.

Pre-promotion checklist:
- [ ] Does this primitive address a failure class not covered by existing catalog?
- [ ] Is the ZTARE leg applied correctly (reflexive inward application)?
- [ ] Meta-parsimony: is an existing primitive deprecated or superseded? (if not, justify complexity increase)
- [ ] Retroactive falsification: target sandbox re-run completed, stagnation reduced?
- [ ] Is the telemetry evidence reproducible (not a one-off run artifact)?
"""

    seam_path.write_text(seam_content, encoding="utf-8")
    print(f"    >> GP-102: seam drafted → {seam_path.relative_to(REPO_ROOT)}")
    return seam_path


# ---------------------------------------------------------------------------
# Component 6: artisan_git_scan — Manual Activity Telemetry
# ---------------------------------------------------------------------------

_LAYER_PATH_PREFIXES: dict[str, str] = {
    "src/ztare/validator/": "Validator",
    "src/ztare/personas/": "Personas",
    "src/ztare/common/": "Common",
    "config/": "Config",
    "rubrics/": "Rubrics",
    "research_areas/private/seams/": "Seams",
    "research_areas/private/specs/": "Specs",
    "supervisor/": "Supervisor",
}

_FRICTION_KEYWORDS = ("fix", "revert", "workaround", "hack", "broken", "patch", "wrong")


def artisan_git_scan(
    repo_dir: Path,
    since: str | None,
) -> ArtisanActivitySummary:
    """Read git log to detect artisan-mode layer activity.

    Extracts commit message friction signals and file-change frequency per layer.
    Commit message patterns are HEURISTIC — use file-change frequency as primary signal.
    """
    cmd = ["git", "-C", str(repo_dir), "log", "--name-only", "--pretty=format:COMMIT:%s"]
    if since:
        cmd += [f"--since={since}"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
        raw = result.stdout
    except Exception:
        return ArtisanActivitySummary(
            friction_commit_count=0,
            layer_churn={},
            high_churn_layers=[],
        )

    friction_count = 0
    layer_churn: dict[str, int] = {v: 0 for v in _LAYER_PATH_PREFIXES.values()}
    layer_churn["Other"] = 0

    current_message = ""
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("COMMIT:"):
            current_message = line[7:].lower()
            if any(kw in current_message for kw in _FRICTION_KEYWORDS):
                friction_count += 1
        elif line:
            # It's a changed file path
            matched = False
            for prefix, layer_name in _LAYER_PATH_PREFIXES.items():
                if line.startswith(prefix):
                    layer_churn[layer_name] = layer_churn.get(layer_name, 0) + 1
                    matched = True
                    break
            if not matched:
                layer_churn["Other"] += 1

    # Identify high-churn layers (>2x median)
    churn_values = list(layer_churn.values())
    if churn_values:
        median = sorted(churn_values)[len(churn_values) // 2]
        threshold = max(2, 2 * median)
        high_churn = [layer for layer, count in layer_churn.items() if count > threshold]
    else:
        high_churn = []

    return ArtisanActivitySummary(
        friction_commit_count=friction_count,
        layer_churn=layer_churn,
        high_churn_layers=high_churn,
    )


# ---------------------------------------------------------------------------
# Wiring: Main Entry Point
# ---------------------------------------------------------------------------

def run_reflexive_audit(
    projects_dir: Path,
    repo_dir: Path,
    primitives_catalog_path: Path,
    output_dir: Path,
    *,
    last_audit_date: str | None = None,
    K: int = 5,
    stagnation_threshold: int = 3,
    skip_llm: bool = False,
    science_token_budget: int = 0,
    meta_budget_ratio: int = 20,
) -> AuditReport:
    """Main entry point. Can be called by GP-070 cron or manually in artisan mode.

    Pipeline:
    1. gather_telemetry across all projects (Component 1)
    2. discriminate each project via SPC (Component 2)
    3. classify_failure_mode deterministically for MACHINERY_BROKEN projects (Component 3)
    4. artisan_git_scan for manual activity signals (Component 6)
    5. inception_committee for diagnosed gaps — LLM proposes primitive (Component 4)
    6. propose_seam for committee outputs (Component 5)
    7. Return AuditReport

    Key principle: diagnosis is deterministic (steps 1-3).
    LLM is reserved for inception (step 5) — the creative act of proposing
    which ZTARE leg to apply reflexively to the stuck layer.

    Meta-budget guard (Preventative 2):
    If science_token_budget is provided, the inception committee (LLM call) only
    fires if science_token_budget >= meta_budget_ratio * (estimated audit tokens).
    Default ratio is 20:1 (science:audit). Pass science_token_budget=0 to auto-compute
    from disk (counts total science iterations × estimated tokens/iter).
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"\n>> GP-102 Reflexive Audit — {timestamp}")
    print(f"   projects_dir:       {projects_dir}")
    print(f"   primitives_catalog: {primitives_catalog_path}")
    print(f"   output_dir:         {output_dir}")
    print(f"   K={K}, stagnation_threshold={stagnation_threshold}")
    print()

    # A2: Auto-compute science budget from disk when caller doesn't provide it.
    # Prevents the guard from being silently bypassed when science_token_budget=0 (default).
    if science_token_budget == 0:
        total_iters = _count_total_science_iterations(projects_dir)
        # Rough estimate: ~8K tokens per science iteration (prompt + response)
        science_token_budget = total_iters * 8000
        print(f"   A2 meta-budget: auto-computed {total_iters} iters × 8K = {science_token_budget:,} tokens")

    # Step 1: Gather telemetry
    summaries = gather_telemetry(projects_dir, K=K, stagnation_threshold=stagnation_threshold)
    print(f"   Scanned {len(summaries)} projects with workspace telemetry")

    # Step 4: Artisan git scan (runs independently, used as corroborating signal)
    artisan_activity = artisan_git_scan(repo_dir, since=last_audit_date)
    print(f"   Git scan: {artisan_activity.friction_commit_count} friction commits, "
          f"high-churn layers: {artisan_activity.high_churn_layers or ['none']}")

    results: list[ProjectAuditResult] = []
    flagged = 0

    for summary in summaries:
        # Step 2: Discriminate
        verdict = discriminate(summary, K=K)
        print(f"   [{summary.project_id}] stagnation={summary.stagnation_count}, "
              f"score={summary.best_score}, verdict={verdict.value}")

        if verdict != AuditVerdict.MACHINERY_BROKEN:
            results.append(ProjectAuditResult(
                project_id=summary.project_id,
                verdict=verdict,
                diagnosis=None,
                proposal=None,
                seam_path=None,
                evidence_summary={"stagnation_count": summary.stagnation_count,
                                  "best_score": summary.best_score},
            ))
            continue

        flagged += 1

        # Step 3: Classify failure mode (deterministic, no LLM)
        diagnosis = classify_failure_mode(summary)
        print(f"     Failure mode: {diagnosis.failure_mode}, stuck: {diagnosis.stuck_layer}")

        # Step 5: Inception committee (LLM proposes primitive)
        # Meta-budget guard: only fire LLM if science has consumed enough tokens.
        # Ratio 20:1 prevents the audit from consuming more than 1/20 of science budget.
        proposal: SeamProposal | None = None
        _budget_ok = (
            science_token_budget >= meta_budget_ratio * 4000  # ~4K tokens per audit call
        )
        if not skip_llm and _budget_ok:
            proposal = inception_committee(diagnosis, summary.project_id, primitives_catalog_path)
        elif not skip_llm and not _budget_ok:
            print(
                f"     >> GP-102: meta-budget guard — science_token_budget={science_token_budget} "
                f"< {meta_budget_ratio}x audit cost; inception committee skipped"
            )
        else:
            print("     >> skip_llm=True: inception committee skipped")

        # Step 6: Propose seam
        seam_path: Path | None = None
        if proposal is not None:
            seam_path = propose_seam(proposal, diagnosis, summary.project_id, output_dir)

        results.append(ProjectAuditResult(
            project_id=summary.project_id,
            verdict=verdict,
            diagnosis=diagnosis,
            proposal=proposal,
            seam_path=seam_path,
            evidence_summary=diagnosis.evidence,
        ))

    report = AuditReport(
        audit_timestamp_utc=timestamp,
        projects_scanned=len(summaries),
        projects_flagged=flagged,
        results=results,
        artisan_activity=artisan_activity,
    )

    # Write audit report to output dir
    _write_audit_report(report, output_dir)

    print(f"\n>> GP-102 Audit complete: {flagged}/{len(summaries)} projects flagged")
    return report


def _write_audit_report(report: AuditReport, output_dir: Path) -> None:
    """Persist the audit report as JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / _AUDIT_REPORT_FILENAME
    payload = {
        "audit_timestamp_utc": report.audit_timestamp_utc,
        "projects_scanned": report.projects_scanned,
        "projects_flagged": report.projects_flagged,
        "results": [
            {
                "project_id": r.project_id,
                "verdict": r.verdict.value,
                "failure_mode": r.diagnosis.failure_mode if r.diagnosis else None,
                "stuck_layer": r.diagnosis.stuck_layer if r.diagnosis else None,
                "primitive_proposed": r.proposal.primitive_name if r.proposal else None,
                "seam_path": str(r.seam_path) if r.seam_path else None,
                "evidence_summary": r.evidence_summary,
            }
            for r in report.results
        ],
        "artisan_activity": {
            "friction_commit_count": report.artisan_activity.friction_commit_count,
            "high_churn_layers": report.artisan_activity.high_churn_layers,
            "layer_churn": report.artisan_activity.layer_churn,
        } if report.artisan_activity else None,
    }
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"   Audit report written → {report_path.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(
        description="GP-102 Reflexive Primitive Discovery Audit"
    )
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=PROJECTS_DIR,
        help="Root directory containing project folders (default: projects/)",
    )
    parser.add_argument(
        "--primitives-catalog",
        type=Path,
        default=_DEFAULT_PRIMITIVES_CATALOG,
        help="Path to reflexive_engineering_primitives.md",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_SEAM_OUTPUT_DIR,
        help="Directory for seam drafts and audit report",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="ISO date — limit git scan to commits since this date (e.g. 2026-04-01)",
    )
    parser.add_argument(
        "--K",
        type=int,
        default=5,
        help="Number of iterations to include in gate failure history (default: 5)",
    )
    parser.add_argument(
        "--stagnation-threshold",
        type=int,
        default=3,
        help="Minimum stagnation_count before audit fires (default: 3)",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Run deterministic stages only — skip inception committee (testing / dry-run)",
    )
    args = parser.parse_args()

    run_reflexive_audit(
        projects_dir=args.projects_dir,
        repo_dir=REPO_ROOT,
        primitives_catalog_path=args.primitives_catalog,
        output_dir=args.output_dir,
        last_audit_date=args.since,
        K=args.K,
        stagnation_threshold=args.stagnation_threshold,
        skip_llm=args.skip_llm,
    )


if __name__ == "__main__":
    _main()
