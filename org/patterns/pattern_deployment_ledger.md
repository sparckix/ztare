---
id: PATTERN-013
name: pattern_deployment_ledger
version: 1
status: active
minted_at: 2026-05-09
triggers:
  lexical: [pattern monoculture, recency bias, deployment ledger, blind spot, underused pattern]
  structural: [repeated_pattern_dispatch, campaign_summary_pending, operator_monoculture_concern]
  problem_classes: [apparatus_self_audit, too_complex_direct_attack]
minted_reason: |
  Operator caught recency-bias in orchestration menu twice in same session
  (2026-05-09): "i'm not sure ur orchestration menu is top notch — it
  seems to me that u are recency bias and even if i tell i have to keep
  telling you... if it is the case then we need to find a structural
  solution." First-order patterns (PATTERN-001..012) describe HOW to
  deploy a tactic; this second-order pattern describes how to AUDIT the
  RD's own deployment distribution and flag monoculture / recency bias
  before the operator has to.

  Empirical justification at minting time: of the ~17 dispatches
  captured in `analytics/public/telemetry/agent_telemetry.jsonl` for the 2026-05-08/09
  NS Track B session, ~12 were PATTERN-001 (typed-companion / friction-
  debate) and 0 were PATTERN-009 (independent_cas_verification). The
  Lerner-2026 W6 port unfaithfulness catch (C-2026-05-09-59) was
  surfaced by an EXTERNAL prover (operator-relayed GPT-5.5), exactly
  because PATTERN-009 was not being deployed by the RD.
falsifiable_test: |
  Over N>=10 logged monoculture_flag=true events, ignored flags must retroactively
  predict a missed catch: in >=60% of cases where the RD ignored a monoculture flag
  and continued the dominant pattern, the next dispatch must have failed to surface
  a defect that a later off-pattern dispatch then caught. If ignored monoculture
  flags predict missed catches in <60% of cases, the diversity metric is not
  central and demotes — this quantifies the pattern's own existing
  (unquantified) falsifiable-asymmetry note.
  metric_source: pattern_deployment_diversity.json (monoculture_flag history)
  joined to the catch ledger for the catch immediately following each ignored-flag
  dispatch.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-013 — Pattern-Deployment Ledger

## What this pattern does

A **second-order ledger** tracking the Research Director's pattern-
deployment distribution itself. Every agent dispatch logs the primary
pattern + secondary patterns + substrate + eigenquestion-or-not into
`analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl`. A scoring script computes
rolling-window diversity metrics and flags **monoculture** (any single
pattern > 50% of last K=10 dispatches) or **structural-blind-spots**
(any pattern with utilization < 5% over last K=20 dispatches).

This is the structural fix for **recency bias in pattern selection**.
First-order patterns (PATTERN-001..012) tell you HOW to deploy each
tactic; PATTERN-013 tells you to NOTICE WHEN your own deployment is
clustering and to CORRECT before the operator has to.

## When to deploy

**Always-on**: every agent dispatch by the RD or any orchestrator
should log a ledger row. The cost is one JSONL append per dispatch
(~milliseconds). The yield is structural defense against monoculture.

**Audit cadence**: the diversity scorer should run

  1. Before any campaign-summary write-up.
  2. When the RD is about to dispatch the K-th identical-primary-pattern
     in a row (K=3 default trigger).
  3. On operator command ("are you in monoculture?").

## Schema (`analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl`)

```json
{
  "dispatch_id": "<uuid>",
  "dispatched_at": "<iso8601>",
  "task_id": "<harness task_id if known, else null>",
  "substrate": "<NS-Track-B | gravity | meta-architecture | ...>",
  "primary_pattern": "PATTERN-XXX",
  "secondary_patterns": ["PATTERN-YYY", ...],
  "eigenquestion_shape": true | false,
  "audit_or_construct": "audit" | "construct" | "scope" | "calibrate",
  "external_or_internal": "internal" | "external_via_operator",
  "outcome_bucket_pre_registered": "<event_1 | ... | event_N>",
  "outcome_bucket_realized": "<event_1 | ... | event_N | null>",
  "notes": "<short>"
}
```

`eigenquestion_shape: true` if the dispatch prompt is a single
falsifiable proposition of the form "is X a faithful encoding of Y;
specify divergences in standard form" — the form GPT-5.5 has been
demolishing claims with. `false` if the prompt is multi-page
constructive scoping.

`audit_or_construct` partitions dispatches into the four operating
modes. `audit` and `calibrate` are yield-bearing for falsification;
`construct` and `scope` are yield-bearing for production. Healthy
distribution should have all four > 10% over a campaign window.

`external_or_internal`: cross-family external-prover dispatches
(via operator-relayed GPT-5.5 / GPT-4.1 / o1) get tagged
`external_via_operator`. PATTERN-009 deployments default to
`external_via_operator`.

## Diversity metrics (`scripts/public/analytics_shared/score_pattern_deployment_diversity.py`)

The scoring script reports:

| Metric | Definition | Healthy band |
|---|---|---|
| `monoculture_flag` | max pattern share over last K=10 | < 0.50 |
| `structural_blind_spots` | patterns with < 0.05 share over last K=20 | < 3 |
| `audit_share` | audit + calibrate share | 0.20–0.50 |
| `external_share` | external_via_operator share | ≥ 0.10 |
| `eigenquestion_share` | eigenquestion_shape=true share | ≥ 0.20 |

Out-of-band metrics emit a flag in the ledger summary; at K=3
consecutive monoculture flags the script emits a HARD KILL signal
that should block further dispatch until a corrective dispatch fires.

## Self-application (this is fractal — the ledger audits itself)

PATTERN-013 itself is subject to monoculture. If `scripts/public/score_
pattern_deployment_diversity.py` is the only audit ever applied,
the audit becomes the next anti-pattern. So this pattern's audit
cadence should itself be subject to operator review at campaign
boundaries.

## Catches that triggered minting

* **Operator catch (2026-05-09 evening)**: explicit pushback on
  recency bias in the orchestration menu. RD acknowledged but did not
  ship structural fix until operator authorized.
* **C-2026-05-09-59 (Lerner-port unfaithfulness)**: external GPT-5.5
  caught what 17 internal Claude dispatches missed; root cause was
  PATTERN-009 utilization = 0% over the campaign window. PATTERN-013
  would have flagged this before the operator had to.

## Falsifiable-asymmetry test (per PATTERN-005)

If the ledger fires `monoculture_flag = true` and the RD ignores it
and the next dispatch fails to surface a defect that a different-
pattern dispatch would have surfaced — that's the falsification.
Ledger correctness is empirically tested by whether ignored monoculture
flags retroactively predict missed catches.
