# GP-102 Reflexive Primitive Discovery Spec

## Status

Active — opened 2026-04-19

## Seam

`research_areas/private/seams/GP-102_reflexive_primitive_discovery_seam.md`

## Scope

- A periodic diagnostic that scans cross-project telemetry for structural paralysis
- A variance-of-failure discriminator that separates "machinery is broken" from "science is hard"
- A seam-drafting output that proposes new reflexive primitives for principal review
- Artisan-mode compatible: works without GP-070 orchestrator running

Does not cover:

- Automating primitive invention (creative act, principal or high-capability agent judgment)
- Automating primitive implementation (output is a seam, not code)
- Replacing principal judgment on whether a proposed primitive is real
- Building new telemetry infrastructure (uses existing artifacts + eval_history.jsonl)

## Decision

Build a periodic diagnostic goal (`reflexive_primitive_audit`) that scans cross-project telemetry for zero-variance stagnation — the "Groundhog Day" signature where the same gate fails with similar residual across K+ iterations after all recovery primitives have fired. Uses Deming's SPC discriminator (common-cause vs special-cause variation) to prevent false-positive audits on difficult substrates. Output is a seam at n=0 for principal review, not code or implementation.

## Problem

Every reflexive primitive in the catalog was discovered the same way: the principal observed a failure class, recognized it as an infrastructure problem (not a science problem), identified which ZTARE leg applies reflexively, and proposed the fix. The engine discovered none of them.

The primitives: Token-Optimized Self-Modeling, Inception Pattern, Hybrid Persona Router, Residual Isomorphism, Reflexive Orchestration — all principal-incepted. The pattern: principal frustration → inversion → new primitive. The frustration signal doesn't exist in any log file.

While the creative act of inventing a primitive can't be mechanized, the *detection* that one might be needed CAN be. When the engine exhausts all known recovery mechanisms and still doesn't improve in the same way (zero-variance stagnation), something structural is wrong.

## Why It Matters

Without this mechanism, primitive discovery scales linearly with principal attention. The principal must be watching a specific project at the moment it hits a structural wall, recognize the wall as process (not science), and inception the fix. Projects the principal isn't watching miss opportunities.

The cron audit doesn't replace the principal — it narrows the search space: "this project is structurally paralyzed, here's the failure trace, here's which layer is stuck." The creative move (which ZTARE leg to apply, what the new primitive should be) remains principal judgment.

## Constraints

1. **No false-positive audits on difficult substrates.** A project that stagnates because the ground truth is genuinely hard (noisy, chaotic, high-dimensional) must NOT trigger a process fix. The variance-of-failure discriminator is the defense.
2. **Artisan-mode compatible.** Must work when GP-070 is not running. Cannot assume `transitions.jsonl` or orchestrator-generated telemetry exists.
3. **Zero new infrastructure.** Uses existing telemetry artifacts (`iteration_telemetry.jsonl`, `structural_memory.json`, `eval_history.jsonl`, `git log`). No databases, dashboards, or aggregation services.
4. **Output is a seam, not code.** The audit proposes; the principal disposes. No automatic implementation, no automatic promotion.
5. **Must not re-propose existing primitives.** The audit reads the reflexive primitives catalog before diagnosing.
6. **Fail-silent on missing telemetry.** If a project lacks `eval_history.jsonl` or `structural_memory.json`, skip it — don't crash the audit.

## Options

### Option A — Event-driven signal detector

Fire when a compound failure signal exceeds a threshold.

**Pros:** Responsive — catches problems as they happen.

**Cons:** Requires knowing the shape of the failure signal in advance. By definition, a new primitive addresses a failure class you haven't seen before — you can't pre-specify its trigger. Chicken-and-egg.

**Verdict:** Rejected in seam Turn 1.

### Option B — Periodic cron goal (Kaizen)

Scheduled review every N goals or N hours. Not triggered by crisis — triggered by calendar.

**Pros:** Avoids the chicken-and-egg. Periodically asks "what's stuck?" without needing to know the shape of the stuckness. This is how Kaizen works — periodic, scheduled, not triggered by crisis. Safe to run unattended because the variance discriminator prevents false positives.

**Cons:** May waste tokens on "all clear" reports if frequency is too high. Tunable.

**Verdict:** Adopted.

### Option C — Principal-only (status quo)

All primitives discovered by principal inception. No mechanization.

**Pros:** Zero cost. High signal — the principal only notices things that matter.

**Cons:** Doesn't scale. Projects the principal isn't watching miss opportunities. Linear in principal attention.

**Verdict:** Baseline to beat, not a solution.

## Recommendation

Option B — periodic cron goal with variance-of-failure discriminator.

## Implementation Sketch

### Component 1: `gather_telemetry` — Cross-Project Scanner

```python
# src/ztare/validator/reflexive_audit.py

def gather_telemetry(projects_dir: Path) -> list[ProjectTelemetrySummary]:
    """Scan all project workspaces for stagnation signals.
    
    For each project with a workspace/:
    1. Read iteration_telemetry.jsonl → extract stagnation_count, score trajectory
    2. Read structural_memory.json → extract family exhaustion depth
    3. Read eval_history.jsonl → extract gate failure history (last K iterations)
    4. Return ProjectTelemetrySummary per project
    
    Skip projects missing required artifacts (fail-silent).
    """
```

**Output dataclass:**

```python
@dataclass
class ProjectTelemetrySummary:
    project_id: str
    workspace_path: Path
    stagnation_count: int
    best_score: int
    score_trajectory: list[int]          # last K scores
    gate_failure_history: list[dict]     # last K gate_verdicts from eval_history.jsonl
    families_exhausted: int              # from structural_memory.json
    families_total: int
    recovery_exhausted: bool             # True when families_exhausted == families_total
                                         # AND stagnation_count > composition_stagnation_threshold
                                         # (proxy: Component D and GP-087 have had opportunities to fire)
    latest_champion_expression: str | None
```

### Component 2: `discriminate` — Variance-of-Failure Classifier

```python
def discriminate(summary: ProjectTelemetrySummary, *, K: int = 5) -> AuditVerdict:
    """Apply Deming's SPC discriminator to a project's gate failure history.
    
    Returns MACHINERY_BROKEN, SCIENCE_IS_HARD, or INSUFFICIENT_DATA.
    
    Logic:
    1. If stagnation_count < 3: return INSUFFICIENT_DATA (too early to judge)
    2. If not recovery_exhausted: return INSUFFICIENT_DATA
       (recovery_exhausted is a proxy: all expression families in structural_memory
        are exhausted AND stagnation exceeds composition threshold — meaning Component D
        and GP-087 have had opportunities to fire. Not a direct "primitives fired" check,
        but computable from existing telemetry without new instrumentation.)
    3. Extract gate failures from last K iterations of eval_history.jsonl
    4. Compute gate_failure_variance:
       - Count distinct gates that failed across K iterations
       - If 1 gate fails in >80% of iterations → LOW_VARIANCE → MACHINERY_BROKEN
       - If 3+ distinct gates fail, no single gate >50% → HIGH_VARIANCE → SCIENCE_IS_HARD
       - Otherwise → AMBIGUOUS (report but don't flag)
    5. Optional: check latent_distance.jsonl trend
       - Flat latent distance + low gate variance → confirms MACHINERY_BROKEN
       - High latent motion + high gate variance → confirms SCIENCE_IS_HARD
    """
```

**Enum:**

```python
class AuditVerdict(Enum):
    MACHINERY_BROKEN = "machinery_broken"       # trigger audit
    SCIENCE_IS_HARD = "science_is_hard"         # all clear
    AMBIGUOUS = "ambiguous"                      # report, don't flag
    INSUFFICIENT_DATA = "insufficient_data"     # skip
```

### Component 3: `classify_failure_mode` — Deterministic Diagnosis (NO LLM)

```python
def classify_failure_mode(
    summary: ProjectTelemetrySummary,
    gate_failure_history: list[dict],
) -> FailureDiagnosis:
    """Deterministic classifier: maps telemetry to typified failure mode.
    
    NO LLM call. The diagnosis is math, not judgment.
    
    MVP failure modes (deterministic):
    - primitive_exhaustion: recovery_exhausted == True
      → stuck_layer = "Component D / Grammar"
    - persistent_stagnation: stagnation > N but recovery NOT exhausted
      → stuck_layer = inferred from dominant failing gate name
        (farther_tail_* → grammar/tail law, parsimony_* → review layer,
         extrapolation_* → gate architecture)
    
    Deferred failure modes (require visibility gaps to close):
    - gate_ceiling, persona_churn, parameter_collision, context_drift
    
    Why deterministic: asking an LLM to "diagnose" a state that is already
    computable wastes tokens and risks hallucinated diagnoses (e.g., blaming
    the prompt when the bottleneck is the grammar ceiling). Compress principle:
    if the answer is deterministic, don't route it through a stochastic system.
    """
```

**Output dataclass:**

```python
@dataclass
class FailureDiagnosis:
    failure_mode: str              # "primitive_exhaustion" | "persistent_stagnation"
    stuck_layer: str               # "Component D / Grammar" | "Gate Architecture" | etc.
    dominant_failing_gate: str     # the gate that fails most often
    evidence: dict                 # raw telemetry that supports this diagnosis
```

### Component 4: `inception_committee` — LLM Invents the Cure (NOT the Diagnosis)

```python
def inception_committee(
    diagnosis: FailureDiagnosis,
    primitives_catalog_path: Path,
) -> SeamProposal | None:
    """Route the deterministic diagnosis to a Process Committee for INCEPTION.
    
    The LLM does NOT diagnose. The diagnosis is final (Component 3).
    The LLM's sole task: apply ZTARE legs (Invert, Compress, Adversarial
    Disagreement) to the identified stuck layer and propose a new
    Reflexive Engineering Primitive that would prevent this failure mode.
    
    Prompt structure:
      "The deterministic SPC monitor has declared MACHINERY_BROKEN.
       Failure Mode: {failure_mode}
       Stuck Layer: {stuck_layer}
       Evidence: {gate_failure_history}
       Existing Primitives: {catalog contents}
       
       TASK: Do not diagnose. The diagnosis is final. Your task is
       Inception — apply ZTARE legs to this layer to draft a new
       primitive that prevents this failure mode."
    
    Committee reads the reflexive primitives catalog first to avoid
    re-proposing existing primitives.
    
    Returns None if committee concludes no new primitive is needed
    (existing primitives cover the failure mode).
    """
```

### Component 5: `propose_seam` — Output Drafting

```python
def propose_seam(
    proposal: SeamProposal,
    output_dir: Path,
) -> Path | None:
    """If a gap is identified, draft a seam at n=0.
    
    Output format: standard seam with:
    - ## Status: open — opened {date}, proposed by reflexive_primitive_audit
    - ## Eigenquestion: {from diagnosis}
    - ## Problem Statement: {from telemetry evidence}
    - ## Proposed Primitive: {layer, failure class, ZTARE leg}
    - ## Telemetry Evidence: {gate failure history, stagnation trace}
    - ## Debate Log: Turn 1 — reflexive_primitive_audit (automated)
    
    Returns path to drafted seam, or None if diagnosis is "all clear."
    Principal must review before promotion to active work.
    """
```

### Component 6: `artisan_git_scan` — Manual Activity Telemetry

```python
def artisan_git_scan(
    repo_dir: Path,
    since: str,  # ISO date of last audit
) -> ArtisanActivitySummary:
    """Read git log to detect artisan-mode layer activity.
    
    Extracts:
    - Which files changed (maps to layers via path prefixes)
    - Commit message patterns (friction signals: "fix", "revert", "workaround")
    - Change frequency per layer (high churn = possible friction)
    
    This is the artisan-mode substitute for transitions.jsonl.
    
    Caveat: commit message conventions are not enforced in this repo.
    Friction keywords ("fix", "revert", "workaround") are heuristic,
    not reliable. Use file-change frequency per layer as the primary
    signal; commit message patterns as secondary/corroborating only.
    """
```

### Wiring: Entry Point

```python
def run_reflexive_audit(
    projects_dir: Path,
    repo_dir: Path,
    primitives_catalog_path: Path,
    *,
    last_audit_date: str | None = None,
    K: int = 5,               # iterations of gate history to check
    stagnation_threshold: int = 3,
) -> AuditReport:
    """Main entry point. Can be called by GP-070 cron or manually in artisan mode.
    
    1. gather_telemetry across all projects
    2. discriminate each project (variance-of-failure SPC)
    3. classify_failure_mode for MACHINERY_BROKEN projects (deterministic, NO LLM)
    4. artisan_git_scan for manual activity signals (corroborating)
    5. inception_committee for diagnosed gaps (LLM invents cure, not diagnosis)
    6. propose_seam for committee outputs
    7. Write audit report to workspace
    
    Key design principle: diagnosis is deterministic (Components 1-3).
    LLM is reserved for inception (Component 5) — the creative act of
    proposing which ZTARE leg to apply reflexively to the stuck layer.
    """
```

### CLI Interface

```
python -m src.ztare.validator.reflexive_audit \
    --projects-dir projects/ \
    --primitives-catalog research_areas/private/philosophy/reflexive_engineering_primitives.md \
    [--since 2026-04-15]  \
    [--K 5]               \
    [--stagnation-threshold 3]
```

In GP-070 orchestrator mode, this is a goal config:

```yaml
name: reflexive_primitive_audit
trigger: cron
frequency: every_5_goals  # or manual in artisan mode
type: diagnostic
entry_point: src.ztare.validator.reflexive_audit:run_reflexive_audit
```

### File Layout

```
src/ztare/validator/reflexive_audit.py     — all 5 components in one file
                                             (~200-300 lines estimated)
```

No new dependencies. Uses existing: `json`, `pathlib`, `subprocess` (for git log), `dataclasses`, `enum`. Committee routing uses existing `src.ztare.personas.routing`.

**Estimated size:** ~400-500 lines. Components 1, 2, 4, 5 are plumbing (~200 lines). Component 3 (committee invocation) requires LLM prompt construction, response parsing, and retry logic (~200 lines, consistent with other LLM call scaffolding in this codebase).

## Open Questions

**Q1: What is the right K (iterations of gate history to check)?**

Start with K=5. If too sensitive (false positives from short stagnation runs), increase to K=8. If too insensitive (misses real structural walls), decrease to K=3. Tunable via CLI flag.

**Q2: Should the audit report persist across runs?**

Candidate: write audit reports to `research_areas/private/audit_reports/reflexive_audit_{date}.json`. This creates a longitudinal view of which layers have been flagged before. But this may be premature — start without persistence, add if the principal finds themselves asking "what did the last audit say?"

**Q3: How does the committee interact with the findings runner?**

The committee convened by GP-102 is a *process* committee, not a *science* committee. It could use the findings runner infrastructure (`supervisor_findings_runner.py`) with process-level failure families as input. Or it could be a standalone LLM call with the primitives catalog + telemetry as context. The findings runner route is heavier but provides debate logging for free. Standalone is simpler. Start standalone, migrate to findings runner if debate quality matters.
