# BRIDGE-2 — Substrate-retirement detector — spec v0

**Parent seam:** `GP-213_operator_role_mechanization_seam.md` §3.2.
**Companion findings:** `GP-149_mining_findings_and_interventions_seam.md` (stagnation-vs-pre-climb-plateau pattern).
**Status:** v0 spec written 2026-05-04.
**Dependency:** trajectory archive (built); no LLM call required for the v0 decision rule.

## 1. What this builds

A new module `src/ztare/director/retirement_detector.py` and a CLI entrypoint `python -m ztare.director.detect_retirement_candidates`. The detector reads telemetry from the trajectory archive, applies a deterministic decision rule, and outputs a list of substrates that meet retirement criteria — with an explicit "but maybe a productive plateau" guard that surfaces the GP-149 §2.2 finding.

Operator-confirmed only in v0. No auto-retirement.

## 2. Decision rule (proposed in seam, refined here)

A substrate is flagged for retirement when **all three** of the following hold:

1. `stagnation_count >= 5` (5 consecutive iterations with no score improvement)
2. `last_5_iter_score_variance < 5` (the score has flatlined, not just paused)
3. `cost_per_finding_30d > median_cost_per_finding_all_time * 2` (return on compute has degraded)

A substrate is flagged as **likely productive plateau, do NOT retire yet** when **either** of the following holds:

- `pivot_history_30d` shows ≥ 1 successful pivot in the last 30 days (per GP-149 §2.2: pivots work for some classes)
- The substrate's predicted class is `tail_generalization` or `exhaustiveness_proof` (mining showed both classes have late-stage climbs after long plateaus)

The two checks are AND-gated: a substrate is recommended for retirement only if rule (1)–(3) fire AND no plateau-guard fires.

## 3. Inputs

Read-only:

- `analytics/public/ledgers/trajectory/trajectory_archive_enriched.jsonl` — per-iteration score, cost, pivot events, substrate class
- `EXPERIMENT_TRACK_RECORD.md` — currently-active substrates list
- `analytics/public/operator_overrides.jsonl` — past operator retirement decisions (for v1 calibration)

No LLM call in v0. Pure aggregation + decision rule.

## 4. Output

A markdown file dropped into `ztare_workspace/inbox/retirement_candidates/{timestamp}.md`:

```markdown
# Retirement candidates — {timestamp}

## Recommended for retirement

### {substrate_name}
- Stagnation count: {N}
- Last-5-iter score variance: {V}
- Cost per finding (last 30d): {C} (median all-time: {M})
- Plateau guards triggered: NONE
- **Recommendation:** retire.
- **Rationale:** {1-paragraph synthesis citing the three rule firings}

## Flagged but plateau-guarded (do NOT retire)

### {substrate_name}
- Stagnation count: {N}
- Last-5-iter score variance: {V}
- Cost per finding (last 30d): {C} (median all-time: {M})
- **Plateau guard:** {pivot_history_30d=1 successful pivot 12 days ago | substrate_class=tail_generalization}
- **Recommendation:** keep running; revisit in 7 days.

## All other substrates: not flagged.

---
**Detector metadata:**
- Run timestamp: ...
- Trajectory archive snapshot: ...
- Decision rule version: v0 (per GP-213 §3.2 + GP-149 §2.2)
```

## 5. CLI

```
python -m ztare.director.detect_retirement_candidates \
    [--substrate SUBSTRATE_NAME]   # filter to one substrate
    [--dry-run]                    # don't write to inbox; print to stdout
    [--threshold-stagnation N]     # override default 5
    [--threshold-variance V]       # override default 5
    [--threshold-cost-multiplier M]# override default 2.0
```

## 6. Anti-tautology guards

Less LLM-prone than BRIDGE-1, but still:

1. **No retirement of substrates < 10 iterations old.** Cold start exclusion; the decision rule needs enough history.
2. **No retirement of substrates with `paper_critical: true` flag in the F-row.** Operator marks substrates that produce paper-grade output; never auto-recommend retirement on those.
3. **Plateau-guard hard-codes the GP-149 §2.2 finding.** The decision rule will *underfire* on pivot-friendly classes by design. Operator can override with `--no-plateau-guard` if they explicitly want the raw rule.

## 7. Failure modes

- **Cost-per-finding metric depends on `findings` field in the archive.** If a substrate's findings are not yet recorded (mining lag), the metric is stale. Mitigation: the detector skips substrates whose archive's last entry is older than 7 days, with a warning.
- **Score variance over last 5 iterations may be < 5 because the substrate is genuinely converged on the right answer.** Mitigation: rule 3 (cost-per-finding) is the secondary check; converged substrates with cheap iterations stay below the cost threshold and are not flagged.
- **Operator's `paper_critical` flag is not yet a stable field.** Mitigation: v0 reads the flag if present, defaults to false otherwise; v1 makes it required for any substrate that has produced > 1 finding.

## 8. Out of scope (v0)

- LLM-narrative reasoning over telemetry. Pure decision rule in v0.
- Cross-substrate retirement (e.g. "retire X because Y produces strictly better results"). Per-substrate only in v0.
- Auto-archive of retired substrates. Operator runs the existing archive script after confirming retirement.

## 9. Acceptance criteria

The spec is shipped when:

- Module compiles; CLI runs on the current archive end-to-end.
- Three unit tests cover: (a) substrate flagged correctly when all three rules fire, (b) plateau guard correctly blocks retirement when a pivot succeeded recently, (c) `paper_critical` flag correctly blocks retirement.
- One real run produces a non-empty inbox file; operator reads it and either confirms a retirement or surfaces a false positive.
- F-row entry added to `EXPERIMENT_TRACK_RECORD.md`.

## 10. Calibration v1 (out of scope for v0, on roadmap)

Once the detector has a few months of operator-confirmation data in `analytics/public/operator_overrides.jsonl`, a v1 refresh will:

- Compare the rule's recommendations against operator's actual retirement decisions
- Compute precision (% of recommended-retired substrates that the operator actually retired)
- Compute recall (% of actually-retired substrates that the rule flagged)
- Tune the thresholds (stagnation, variance, cost-multiplier) to maximize a chosen F-beta score
- Add new plateau-guard cases as new substrate classes emerge

This is the BRIDGE-2 v1 spec (deferred until operator override data accumulates).

---

*v0 spec written 2026-05-04 in auto mode. Refresh after first 30 days of operator-confirmation data.*
