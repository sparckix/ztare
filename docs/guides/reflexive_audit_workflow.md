# Reflexive Audit Workflow

**Canonical for:** GP-102 reflexive primitive discovery audit — how to run it, interpret it, and act on it.
**Companion doc:** `docs/concepts/reflexive_engineering.md` — the primitives catalog this audit extends.
**Implementation:** `src/ztare/composition/reflexive_audit.py`

---

## Purpose

Every reflexive engineering primitive in the catalog was discovered the same way: the principal observed a failure, recognized it as infrastructure (not science), and incepted a fix. The engine discovered none of them.

The reflexive audit mechanizes the *detection* half of that pattern. It cannot invent a new primitive — the creative act of applying a ZTARE leg to a stuck layer requires judgment. But it can reliably detect when a project has hit a structural wall that no existing recovery mechanism addresses, and draft a first seam for principal review.

**The key distinction the audit makes:** Is the project stagnating because the *science is hard* (a genuinely difficult substrate with high-variance failures across many gates) or because the *machinery is broken* (the same gate failing with similar residual across K+ iterations — the Groundhog Day signature)?

The audit only flags the second case. Flagging the first would generate false-positive "process improvement" seams on every difficult project.

---

## When to Run

Run the audit when:
- You sense the engine is stuck and want a cross-project diagnostic
- You have completed a batch of goals and want a periodic Kaizen review
- A specific project has been stagnating and you want to check if it is machinery or science

The design is Kaizen-style: **periodic and scheduled, not event-driven.** Event-driven detection requires knowing the shape of the failure signal in advance — but a *new* primitive addresses a failure class you haven't seen before, so you can't pre-specify its trigger.

In artisan mode (GP-070 orchestrator not running), trigger manually. In orchestrator mode, wire as a goal with `trigger: cron` and `frequency: every_5_goals`.

---

## What It Inspects

The audit reads three telemetry sources per project:

| Source | What it extracts |
|--------|-----------------|
| `workspace/iteration_telemetry.jsonl` | Stagnation count, score trajectory, failed gate IDs per iteration |
| `workspace/structural_memory.json` | Expression family exhaustion depth, composition primitive count |
| `workspace/latent_distance.jsonl` | Latent motion trend (optional — confirms SCIENCE_IS_HARD when high) |

Plus a repo-level source:

| Source | What it extracts |
|--------|-----------------|
| `git log` | File-change frequency per layer (artisan activity proxy) |

**Fail-silent:** projects missing any of these artifacts are skipped, not crashed.

---

## The Discriminator: Deming SPC

The core logic is W. Edwards Deming's Statistical Process Control distinction between **common-cause** and **special-cause** variation:

| Signature | Gate failure variance | Latent motion | Diagnosis | Action |
|-----------|----------------------|---------------|-----------|--------|
| Same gate fails >80% of iterations | **Low** (special-cause) | Flat | `MACHINERY_BROKEN` | Trigger audit |
| Failures rotate across 3+ gates | **High** (common-cause) | High | `SCIENCE_IS_HARD` | All clear |
| Ambiguous | Neither threshold | Mixed | `AMBIGUOUS` | Report, don't flag |
| Too few iterations | — | — | `INSUFFICIENT_DATA` | Skip |

**Deming's key insight applied here:** Intervening on common-cause variation (the engine exploring a hard substrate) makes things worse — it generates spurious process-improvement seams on projects that are simply in difficult territory. Only zero-variance stagnation (special-cause) is actionable.

**Gate 2 — recovery exhausted:** Before flagging MACHINERY_BROKEN, the discriminator checks that recovery mechanisms have had opportunities to fire. Proxy: `families_exhausted == families_total` AND `stagnation_count > threshold`. If recovery is not yet exhausted, the verdict is `INSUFFICIENT_DATA` — the engine may still be working.

---

## Running It

**Dry-run (no LLM, deterministic stages only):**
```bash
python -m src.ztare.composition.reflexive_audit \
    --projects-dir projects/ \
    --primitives-catalog research_areas/private/philosophy/reflexive_engineering_primitives.md \
    --skip-llm
```
Use this first. It scans all projects, runs the discriminator, and classifies failure modes — all in seconds with no API cost. No seams are drafted.

**Full run (LLM inception committee fires for flagged projects):**
```bash
python -m src.ztare.composition.reflexive_audit \
    --projects-dir projects/ \
    --primitives-catalog research_areas/private/philosophy/reflexive_engineering_primitives.md \
    --science-token-budget 5000000
```
The `--science-token-budget` tells the meta-budget guard "we have spent this many science tokens." The inception committee (LLM call) only fires if the science budget is at least 20× the estimated audit cost (~4K tokens per call). This prevents the audit from dominating token spend when little science has run. If omitted, the guard auto-computes from disk by counting past iteration records.

**All CLI options:**

| Flag | Default | Purpose |
|------|---------|---------|
| `--projects-dir` | `projects/` | Root directory of project folders |
| `--primitives-catalog` | `research_areas/private/philosophy/reflexive_engineering_primitives.md` | Catalog read before inception to avoid re-proposals |
| `--output-dir` | `research_areas/private/seams/reflexive/` | Where seam drafts and audit report land |
| `--since` | (all history) | ISO date — limit git scan to commits since this date |
| `--K` | `5` | Iterations of gate history to check |
| `--stagnation-threshold` | `3` | Minimum stagnation_count before audit fires |
| `--skip-llm` | off | Run deterministic stages only — no inception committee |
| `--science-token-budget` | auto-computed | Override for the meta-budget guard |

---

## Reading the Audit Report

The audit writes `research_areas/private/seams/reflexive/reflexive_audit_report.json` after each run. Key fields per project:

```json
{
  "project_id": "gp023_planck_sandbox_05",
  "verdict": "machinery_broken",
  "failure_mode": "primitive_exhaustion",
  "stuck_layer": "Grammar / Tail Law",
  "primitive_proposed": null,
  "evidence_summary": {
    "stagnation_count": 9,
    "best_score": 50,
    "dominant_failing_gate": "farther_tail_global_residual",
    "families_exhausted": 8,
    "families_total": 9
  }
}
```

**Verdict taxonomy:**

| Verdict | Meaning |
|---------|---------|
| `machinery_broken` | Structural wall — same gate failing, recovery exhausted. Audit this project. |
| `science_is_hard` | Diverse failures, high latent motion. Engine is searching a hard substrate. No action. |
| `ambiguous` | Neither threshold met. Noted in the report, not flagged for action. |
| `insufficient_data` | Too few iterations, or recovery not yet exhausted, or project already converged. Skip. |

**Failure mode taxonomy (for `machinery_broken` projects):**

| Failure mode | What it means |
|--------------|---------------|
| `primitive_exhaustion` | All expression families exhausted AND stagnation persists. Component D has run out of topology to try. |
| `persistent_stagnation` | Stagnation persists but recovery is not fully exhausted — a dominant gate is failing but Component D hasn't fired yet. |
| `qualitative_ceiling` | Stagnation with no hard gate failures logged. The review layer is scoring the same candidates similarly without improvement. |

---

## Acting on a MACHINERY_BROKEN Flag

**Step 1: Read the evidence summary.** Look at `dominant_failing_gate`, `stuck_layer`, and `score_trajectory`. Is the diagnosis plausible? Does the stuck layer match what you know about this project?

**Step 2: Check the primitives catalog.** Is an existing primitive already designed for this failure mode? If yes, the question is why it hasn't fired — that's a wiring issue, not a new primitive gap.

**Step 3 (if LLM run): Review the seam draft.** The inception committee writes a seam to `research_areas/private/seams/reflexive/` with `SENTINEL_DECISION: hold`. This means the seam cannot be promoted without explicit principal action. Check:
- [ ] Does the proposed primitive address a failure class not covered by the existing catalog?
- [ ] Is the ZTARE leg applied correctly (reflexive inward application)?
- [ ] Meta-parsimony: does the proposal identify an existing primitive it supersedes, or justify why complexity must increase? If neither, it should be `NO_NEW_PRIMITIVE`.
- [ ] Is the telemetry evidence reproducible (not a one-off run artifact)?

**Step 4: Retroactive falsification gate (mandatory before promotion).** Every seam draft includes a `target_sandbox` field — the project_id of the stagnated sandbox that motivated the proposal. Before raising the seam from `hold` to `active`, re-run that sandbox with the proposed primitive in effect and record the result in Turn 2 of the Debate Log. If the sandbox does not break the stagnation, the primitive is reverted as false-positive bureaucracy.

---

## Structural Safeguards Against Self-Perpetuating Audit

The audit is designed against the "self-licking ice cream cone" failure mode — where the meta-auditor becomes a permanent bureaucracy that generates its own workload rather than serving the science. Four structural preventatives:

**P1 — Meta-parsimony (one-in, one-out):** The inception committee prompt requires the LLM to either identify an existing primitive it supersedes, or provide a mathematical justification for complexity increase. If neither is satisfied, the LLM must return `NO_NEW_PRIMITIVE`. No new primitive may be added without a corresponding simplification or a hard justification.

**P2 — 20:1 meta-budget ratio:** The inception committee (LLM call) only fires if the science token budget is at least 20× the audit's estimated cost. This prevents the audit from consuming more than 5% of total token budget. Auto-computed from disk when not explicitly set.

**P3 — Retroactive falsification gate:** Every seam draft includes a mandatory target sandbox. The primitive is not promoted until the principal re-runs that sandbox with the primitive in effect and observes reduced stagnation. A primitive that doesn't fix its motivating case is discarded.

**P4 — Hardware air-gap:** The audit can only write to `research_areas/private/seams/reflexive/`. It has no write path to the primitives catalog, the orchestrator configs, or any implementation. Manual copy-to-commit by the principal is the only promotion path.

---

## Tuning Parameters

| Parameter | Start value | Tune up if | Tune down if |
|-----------|-------------|-----------|--------------|
| `K` (gate history window) | 5 | False positives from short stagnation bursts | Missing real structural walls that need longer observation |
| `stagnation-threshold` | 3 | Too many flags on projects with brief plateaus | Missing persistent walls that start early |
| `meta-budget-ratio` | 20 | Audit runs are costly relative to science runs | Inception committee never fires because science budget is always too low |
| Frequency | Every 5 goals (or manual) | "All clear" reports feel wasteful | Structural walls slip through undetected |
