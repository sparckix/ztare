---
description: "Curated claim cards linking ZTARE public claims to evidence sources, commands, non-claims, and next falsifiers."
---
# Claim Cards

> **Up:** [Evidence Atlas](README.md)

Each card below is a reviewer route through existing evidence. The cards are
curated for breadth and inspectability, not because they exhaust the repo.

## Card 1: Evaluator Hardening And Self-Certification Failures

**Claim.** ZTARE-style deterministic gates and mined adversarial precedent can
reduce self-certifying evaluator failures on the benchmark families tested.

**Evidence level.** L4, controlled benchmark evidence on bounded families.

**Primary sources.**

- [Benchmark evidence](../../benchmarks/benchmark_evidence.md)
- [Constraint-memory benchmark](../../benchmarks/constraint_memory/README.md)
- [Cheating catalog](../cheating_catalog.md)
- [Cognitive Camouflage paper](../../papers/cognitive-camouflage/draft.md)
- [Adversarial Precedent Memory paper](../../papers/adversarial-precedent-memory/draft.md)

**Runnable anchors.**

```bash
make benchmark-evidence
make demo
```

**Non-claims.** Not a global SOTA claim. Not evidence that ZTARE is the best
general-purpose reasoning system. Not evidence that null-returning gates are
sufficient for discovery.

**Next falsifier.** Freeze a larger public claim-packet suite with ordinary LLM
review, rubric-only review, deterministic gates, and gates-plus-precedent as
separate conditions.

## Card 2: Public Claim Register And Project Claim Summaries

**Claim.** The repository has a public claim register that separates claims,
non-claims, evidence pointers, retest tags, and next falsifiers across rowdy
scientific and methodology campaigns.

**Evidence level.** L3 as claim-governance infrastructure; individual claims
vary from L1 to L4.

**Primary sources.**

- [Public claim register](../public_claim_register.md)
- Per-project `projects/*/public/CLAIM_SUMMARY.md`
- [Experiment track record](../../research_areas/EXPERIMENT_TRACK_RECORD.md)

**Runnable anchor.**

```bash
find projects -path '*/public/CLAIM_SUMMARY.md' | sort
```

**Non-claims.** A linked claim summary is not external validation. Some
project claims remain original-run-only, apparatus-internal, or explicitly
demoted.

**Next falsifier.** Add machine-readable claim-card rows and a validator that
fails when a public claim lacks evidence pointer, non-claim, status, and next
falsifier fields.

## Card 3: Agentic Engineering Patterns

**Claim.** The repo has a portable pattern catalog for LLM-mediated pipelines:
stub replay, pre-flight assertion batteries, canonical hashing, provenance
telemetry, forecast-pool control, result-bound success claims, structural
contract gating, and related orchestration patterns.

**Evidence level.** Mixed L1-L3 today. Some patterns have implementation
anchors and tests; others are documented design patterns awaiting stronger
ablation evidence.

**Primary sources.**

- [Agentic engineering patterns](../concepts/agentic_engineering_patterns.md)
- [Primitive classification criteria](../concepts/primitive_classification_criteria.md)
- [Scripts README](../../scripts/README.md)
- [Tests tree](../../tests/)

**Runnable anchors.**

```bash
make smoke-public
python scripts/public/control/org_runtime_smoke.py --role research_director --member-id codex --agent-cli codex --agent-adapter auto
```

The second command checks the role preflight and daemon dry-run path; see
[org runtime smoke](../../scripts/public/control/org_runtime_smoke.py).

**Non-claims.** The pattern catalog is not itself evidence that each pattern
improves outcomes. Improvement claims require per-pattern evidence rows.

**Next falsifier.** For each pattern, add a minimum evidence row: motivating
failure, implementation artifact, validator or test, observed prevented
failure, and demotion criterion.

## Card 4: Reflexive Primitives

**Claim.** ZTARE has a small registry of self-referential primitives: the
apparatus using its own infrastructure or epistemic rules to govern its own
growth.

**Evidence level.** L1-L3 for registered primitives; RP-003 and RP-004 are new
and explicitly calibration-seed stage.

**Primary sources.**

- [Reflexive primitive registry](../../src/ztare/reflexive_primitives/INDEX.md)
- [Reflexive engineering](../concepts/reflexive_engineering.md)
- [Capability evidence contract seam](../../research_areas/seams/apparatus/instrumentation/GP-247_capability_evidence_contract_seam.md)
- [Capability evidence contract ledger](../../analytics/public/ledgers/capability_evidence_contracts/cec_ledger.jsonl)
- [Self-report epistemology critic](../../scripts/public/control/self_report_epistemology_critic.py)

**Runnable anchor.**

```bash
python scripts/public/control/self_report_epistemology_critic.py
```

**Non-claims.** A reflexive primitive being elegant is not evidence that it is
causally useful. The registry itself marks falsifiers and demotion criteria.

**Next falsifier.** Resolve at least five Capability Evidence Contract bets and
test whether CEC fields predict realized capability yield better than prior
operator belief.

## Card 5: Forecast Pool And Action Intelligence

**Claim.** The apparatus has a forecast-pool and action-intelligence layer for
sealed forecasts, scored outcomes, decision-use logging, calibration surfaces,
and action-impact rows.

**Evidence level.** L1-L3; selected smoke tests pass, while full calibration
strength depends on resolved and scored contract history.

**Primary sources.**

- [Forecast pool implementation](../../scripts/public/control/forecast/pool.py)
- [Action intelligence implementation](../../scripts/public/control/action_intelligence.py)
- [Operations intelligence surface](../../src/ztare/reports/operations_intelligence.py)
- Forecast artifacts under `analytics/public/forecast_pool/`

**Runnable anchors.**

```bash
python scripts/public/control/forecast/pool.py smoke
make smoke-public
```

**Non-claims.** Forecast artifacts are not research truth. They are calibration
and routing evidence unless tied to objective outcomes and decision-use rows.

**Next falsifier.** Publish a calibration report with enough resolved
contracts to estimate per-agent calibration and decision-use lift with
confidence intervals.

## Card 6: LeanMill Governance And Formal-Audit Discipline

**Claim.** LeanMill is a station-factory and audit substrate for Lean proof
work, with leak-tight benchmarking, matched negative controls, proof-governance
distinctions, and explicit mechanism-vs-moat separation.

**Evidence level.** L3-L4 for governance discipline and no-lift benchmark;
not L5 and not a theorem-prover leaderboard claim.

**Primary sources.**

- [LeanMill architecture](../concepts/leanmill_architecture.md)
- [APN audit summary](../../analytics/public/queries/lane_b_apn_audit_summary.md)
- [APN audit receipts](../../analytics/public/queries/lane_b_apn_audit_receipts.json)
- [Public claim register, F103](../public_claim_register.md)

**Runnable anchors.**

```bash
lake build
```

Use Lean-specific review commands from the LeanMill docs for targeted proofs;
do not treat a whole-repo build as a proof-value claim.

**Non-claims.** LeanMill currently has no public miniF2F number and no claim
that planner memory beats public static tools on natural Mathlib rows. Internal
review docs exist in the repository, but this card treats the public claim
register, public analytics receipts, architecture doc, and runnable Lean build
as the external-review anchors.

**Next falsifier.** Submit or externally review at least one audit-clean proof
artifact, and run a public calibration benchmark against named baselines.

## Card 7: Navier-Stokes Residual Localization

**Claim.** The NS campaign has produced proof infrastructure, residual
localization, route demotions, and typed scaffolding that are public as an
atlas of what has and has not survived.

**Evidence level.** L2-L3; selected Lean artifacts are L1-L2 formal source,
but the campaign is not a theorem closure.

**Primary sources.**

- [Public claim register, Navier-Stokes Track B](../public_claim_register.md#navier-stokes-track-b)
- [NS public journey/status](../../projects/ns_millennium_hunt/public/JOURNEY.md)
- [NS public graph](../../projects/ns_millennium_hunt/public/index.html)
- [Lean proof tree](../../ztare_proofs/)
- [NS residual manifest](../../projects/ns_millennium_hunt/workspace/ns_residual_manifest.md)

**Runnable anchor.**

```bash
lake build
```

**Non-claims.** No Clay proof. No unconditional regularity proof. No blow-up
construction. No claim that typed wrappers close analytic PDE obligations.

**Next falsifier.** Route only through named residual frontiers with explicit
target axiom, amnesia check, tool-depth loop, and formal/source receipts.

## Card 8: GP-245 LLM Forecasting Calibration Program

**Claim.** The forecasting program measured many forecasting-channel,
herding, abstention, judge-loop, and bias-inheritance findings across a
multi-family LLM panel, with a power-aware verdict resolver and explicit
retractions.

**Evidence level.** L2-L4 internally, depending on finding; not
second-lab-replicated.

**Primary sources.**

- [Public claim register, GP-245](../public_claim_register.md#gp-245-forecast-calibration-program-llm-forecasting-channels--operationalization)
- [Research log](../../projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/research_log.md)
- [Forecast pool scorer](../../scripts/public/control/forecast/pool.py)
- [Working paper draft](../../papers/llm-forecast-calibration-cross-corpus/draft.md)

**Runnable anchors.**

```bash
python scripts/public/control/forecast/pool.py calibrate
python scripts/public/control/forecast/pool.py smoke
```

If a command name changes, defer to `python scripts/public/control/forecast/pool.py --help`.

**Non-claims.** Does not claim LLMs cannot forecast. Does not claim
reproducibility-grade external methodology. Does not solve contamination or
author-selection leakage.

**Next falsifier.** Second-lab submission or clean external corpus replication
with model cutoffs strictly before resolution dates.

## Card 9: Evaluation-Design Case Studies

**Claim.** The repo contains small, reproducible case studies showing common
evaluation failures: rank-deficient bootstrap, evidence-grid
underdetermination, and evidence-enrichment saturation.

**Evidence level.** L4 for small model-free reproducers.

**Primary sources.**

- [Case-study index](../../papers/case_studies/README.md)
- [Benchmark evidence](../../benchmarks/benchmark_evidence.md)

**Runnable anchor.**

```bash
make demo
```

**Non-claims.** These are not exhaustive failure modes and do not benchmark
the current full apparatus.

**Next falsifier.** Add only case studies with one-minute reproducers and
clear expected output.

## Card 10: Cross-Substrate Methodology

**Claim.** Across campaigns, ZTARE's strongest integrative claim is not that
it solved each domain, but that the same discipline repeatedly demoted
overclaims, preserved nulls, and surfaced next falsifiers.

**Evidence level.** L3 methodology claim; individual domains vary.

**Primary sources.**

- [Cross-substrate methodology in the public claim register](../public_claim_register.md#cross-substrate-methodology)
- [Multi-substrate validation](../multi_substrate_validation.md)
- [Experiment track record](../../research_areas/EXPERIMENT_TRACK_RECORD.md)
- [Public claim register](../public_claim_register.md)

**Runnable anchors.**

```bash
make smoke-public
make benchmark-evidence
```

**Non-claims.** Does not prove the current meta-architecture is independently
replicated or generally superior across research domains.

**Next falsifier.** Re-run a frozen current-system benchmark over claim
packets with external baselines and independently assigned labels.
