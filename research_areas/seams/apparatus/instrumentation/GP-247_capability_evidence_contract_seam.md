# GP-247 Capability Evidence Contract Seam

> **Seam metadata** · `seam_id:` GP-247 · `track:` apparatus/instrumentation · `status:` `v1-open` — opened 2026-05-31 · `last_updated:` 2026-05-31
> **Cross-links (superset / consumes):** generalizes the yield-decomposition logic from research *lanes* to *capabilities* — reads the bottleneck binding from [[GP-233_research_yield_decomposition_seam]] (general lane yield) and [[GP-246_governed_dag_proof_search_seam]] (lean-closure yield `closed_or_exact_gap@budget`); consumes the six metric families of [[GP-244_research_operations_intelligence_cockpit_seam]]; enforced by the master-discriminator (exogenous-carrier-or-nothing).

## Eigenquestion

When the apparatus is pointed at itself and proposes a new internal capability to build, can we decide *which* capability is worth building **without** the decision becoming a self-scored sophistication ladder?

## Provenance: a scalar ranker was designed, cold-pre-flighted, and KILLED

The first design was a scalar **Capability Exploration Priority** formula
`CEP = (EIY × CA × TR) / (C × (1+GR))` (expected-insight-yield × constraint-alignment ×
transfer / cost × Goodhart-risk). A cold cross-provider adversarial pre-flight killed it,
and the kill is correct and load-bearing:

- **CEP is a sophistication ladder in disguise.** EIY, CA, TR, GR are all judgment slots the
  capability author can launder taste into. GR (the Goodhart-risk discount) is itself
  Goodhartable. The formula is a recursive self-audit ranker: "this creates structural info,
  this hits the bottleneck, this transfers, trust me the evidence is exogenous enough" — same
  failure class as a rubric, cleaner spreadsheet. (Lived precedent: the self-narrated-
  sophistication-ladder and recursive-over-architecting failures this repo has repeatedly hit.)
- **CA-as-multiplicative-gate is the highest-leverage gaming surface**, not a virtue: it pays
  every proposer to narrate "my capability relieves *the* bottleneck," and bottleneck identity
  is itself contestable.
- **Constructed failure the formula gets wrong:** a "Meta-Goodhart Risk Auditor" scores high on
  CEP (high EIY/CA/TR, low GR because it *claims* to audit Goodhart) but must NOT be built —
  its evidence is authored by the same apparatus it audits (a prestige machine). Inversely, a
  boring single-stage hidden-test harness scores LOW on CEP (low EIY, narrow TR) but SHOULD be
  built, because it pins an exogenous carrier that makes all later evidence non-self-scored.

**Verdict: do NOT build a scalar capability ranker. No formula until enough ex-post calibration
exists to prove the factors predict good capability choices.**

## The object instead: Capability Evidence Contract (CEC)

A capability is not *scored*; it is made **rankable only if it can post a carrier-bound
preflight contract**. Each field must be backed by an evidence source fixed *before* the
capability is evaluated, with at least one **exogenous** carrier (kernel / hidden test /
downstream decision the apparatus cannot narrate around). No qualifying carrier ⇒ the
capability is **not rankable by CEC** (it can still be built on operator conviction, but it
does not get an apparatus-blessed priority).

```yaml
capability_evidence_contract:
  capability_id: <slug>
  bottleneck_stage_targeted:        # PINNED to a frozen yield-decomposition snapshot,
    decomposition_ref: <GP-233 lane snapshot | GP-246 lean-closure snapshot>   # not a fresh estimate
    snapshot_hash: <sha256 of the frozen decomposition>
    declared_causal_path: "changes <measured stage> by <observable mechanism>"  # absent ⇒ stage=unclassified, NOT a soft score
  exogenous_carrier:                # the one non-negotiable field
    kind: kernel | hidden_test | downstream_decision | matched_negative_control
    where: <path / gate / ledger that will fire>
    why_unfakeable: "the proposer cannot choose this evidence distribution"
  kill_criterion: "this capability is abandoned if <observable> after <budget>"
  downstream_decision_changed: "<the concrete decision this would change>"
  cost_ceiling: { wall_time: , usd: , agent_attention: }
  reuse_surface: <substrate-agnostic primitive it becomes | one-off>
```

Comparison is a **review table over the contracts**, not a sorted scalar. The operator (or a
cold cross-provider panel) reads the table; CEC's job is to make off-constraint, no-exogenous-
carrier, no-kill-criterion proposals *visibly* non-rankable, not to rank them numerically.

## Why this is the link to the yield decomposition (operator's framing)

The `bottleneck_stage_targeted` field binds every capability to a **frozen** snapshot of an
existing yield decomposition — GP-233 for research lanes, GP-246's `closed_or_exact_gap@budget`
for lean closures. CEC is the *superset*: it generalizes "where is the bottleneck → what is the
next lever" from a single lane to the capability portfolio, while refusing to let the bottleneck
binding be re-narrated per proposal. Freezing the snapshot + requiring a declared causal path is
exactly what stops CA-gaming.

## Invariants (HARD)
- No CEC field may be scored by the same agent that proposes the capability without an exogenous
  carrier backing it. Carrier-or-nothing.
- `bottleneck_stage_targeted` resolves against a frozen decomposition hash; a live re-estimate is
  rejected.
- No scalar priority number is emitted until a ledger of ≥N resolved capability bets shows the
  contract fields predict realized yield (the calibration the cold pre-flight demanded).

## First two capability bets to run under CEC (the calibration seed)
1. **Newton-gate ablation** (reflexive idea #1): is a "engaged" primitive *Newton-alive* (did its
   firing causally lift a held-out yield it did not touch) or only Kepler-alive (it merely ran)?
   Exogenous carrier = held-out closure-rate delta vs a no-primitive control. Bottleneck stage =
   `verification`/`closure` on the lean-closure decomposition.
2. **Self-report epistemology critic** (reflexive idea #3, BUILT 2026-05-31,
   `scripts/public/control/self_report_epistemology_critic.py`): GP-166 noise-profile turned on
   the apparatus's own metric series. Exogenous carrier = the Durbin-Watson / Breusch-Pagan
   statistic of the series (objective). Already found: trajectory-score series is non-i.i.d.
   (autocorrelated + non-Gaussian); catch ledger is an 11-day ratification burst; insight-density
   has no series (1 snapshot). These two bets' realized yield is the seed calibration data.

## Done-definition
- v1 BUILD: the CEC schema + a review-table renderer; the two seed bets posted as CEC contracts.
- SCIENCE: after ≥N resolved bets, test whether the contract fields predict realized capability
  yield; only then consider promoting CEC from a contract to a (calibrated, exogenously-anchored)
  ranker — never before.
