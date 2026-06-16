---
description: "Public claim register for the ZTARE campaigns: what survived, what did not, and where the evidence lives."
---

# Public Claim Register

Last refreshed: 2026-06-12

This is the public claim register for the ZTARE campaigns:
Navier-Stokes, consciousness-ascription governance, modified gravity, neural
scaling / mechanistic audits, experimental mathematics, vocabulary-escape
calibration, empirical curve-fit recoveries, sealed apparatus calibrations,
apparatus self-audits, methodology and apparatus-hardening papers, and
evaluation-design case studies.

This is not a leaderboard, not a marketing page, and not a proof of general
scientific authority. A claim appears here only if the repository can state
what survived, what did not survive, where the evidence lives, and what the
next falsifier or source-design step is.

The register is intentionally prose-first. Tables make these claims look more
settled and more commensurable than they are.

This is the canonical public entry point for these campaigns. The
[70-day journey](sprint_70day_journey.md), raw experiment track record, and
project folders are evidence/provenance layers; they are not the source of
current public claim status. If a campaign is not summarized here, treat it as
private, historical, or not yet public-claim-ready.

## Scope Discipline

ZTARE is a falsification-native research system. It has produced bounded
scientific and governance results across several difficult substrates and
preserves the demotions of its own wrong causal stories alongside the
positive results. That is the scope of the public claim, no wider.

The repository should not claim that Navier-Stokes is solved, consciousness is
solved, modified gravity or dark matter is adjudicated, neural scaling laws are
universal, the current meta-architecture has been independently replicated, or
a non-expert principal plus LLMs replaces domain experts.

Public evidence also means intentionally public evidence. Many live project
surfaces are private or ignored working areas. Those may guide the operator,
but they are not public support until their relevant source packet, claim,
non-claim, and next falsifier are moved into a public document.

## Confidence and Retest Discipline

Each claim below carries an explicit **retest tag**. A result that was
produced once under a specific apparatus is not the same kind of evidence as
a result that survived re-execution under a different mutator, a different
tool, an enlarged dataset, or a revised apparatus version. The tags make
that distinction legible rather than hiding it inside the prose.

The tags are deliberately narrow:

- **Original-run only (n=1).** Single sealed sandbox or single experimental
  run. The result is on the public record but has not been re-executed under
  a different mutator, larger data, or a later apparatus version.
- **Cross-mutator replicated.** The same result was obtained from at least
  two distinct mutator families (e.g., Gemini + Claude, or Claude + GPT-4o).
- **Cross-tool replicated.** An independent symbolic-regression tool (e.g.,
  PySR) arrived at the same form or coefficient on the same substrate.
- **Enlarged-data confirmed.** Re-run on a substantially expanded evidence
  range or term count still passes the same gates.
- **Successor-run partial demotion.** A successor sandbox on the same axis
  did not reproduce the original outcome; the demotion is recorded next to
  the original claim.
- **Negative result on retest.** An earlier positive claim was killed by a
  later run; the demotion is the durable evidence.
- **Diagnostic finding (no recovery to retest).** The claim is a structural
  diagnosis (e.g., a depth-1 composition ceiling, a within-class feature
  collapse). The diagnosis is the artifact; there is nothing to "retest" in
  the recovery sense.
- **Methodology / framework claim.** Not a recovery; an architectural
  property of the apparatus, held across multiple substrates.
- **Apparatus-internal verdict only.** A sealed result under the
  apparatus's own judge layer, not yet adjudicated externally.
- **Not yet retested under current apparatus version.** Honestly absent;
  the claim is on the historical record but the current apparatus has not
  been pointed back at it.

The general posture: a single sealed run is real evidence, but it is the
*weakest* defensible category, and the register should say so out loud
rather than letting prose-volume substitute for replication.

**Self-report epistemology caveat (2026-05-31).** The [GP-166](../research_areas/seams/mission/meta/GP-166_self_enacted_procedural_compliance_seam.md) noise-profile
critic was turned inward on the apparatus's own metric series (the same critic
that refuses to trust a substrate fit until it measures the residual's
statistics). Two results the reader should hold: (1) the per-iteration
champion-score series (n=2000) is **non-i.i.d. — autocorrelated and
non-Gaussian** — so any aggregate "the score improved" statement inherits
momentum/drift and is not a sequence of independent samples; treat score
*trends*, not levels, with that caveat. (2) The reflexive metric history
(`p0_metrics_history.jsonl`) currently holds **one snapshot**, so the
"recursive gain plateaued" reading rests on too few points to validate as a
series. These are disclosed, not asserted past; the critic lives at
[`scripts/public/control/self_report_epistemology_critic.py`](../scripts/public/control/self_report_epistemology_critic.py).

## Navier-Stokes Track B

**Public claim.** The Navier-Stokes campaign has produced a deep
proof-infrastructure and residual-localization result. The public record
contains sorry-free Lean scaffolding, Unified Categorical Compactness
wall-certificates, residual-void atoms, proof-search routes, demotion logs,
and a public journey that distinguishes typed scaffolding from analytic PDE
closure.

The strongest public claim is precision-localization: several candidate routes
were formalized, audited, and demoted or bounded, leaving named residual
frontiers rather than a monolithic vague "Navier-Stokes attempt."

**Status.** Active hard-problem campaign. Proof infrastructure and bounded
negative/progress results. Not a theorem closure.

**Proof-state checkpoint.** As of 2026-05-22, the live proof-search routes
are: cycle-resupply bridge (sealed at 97), low/high operator-norm bridge
(95), residual defect-packet certificate (91), resupply pincer (93),
square-law exhaust bridge (93), alien-invariant bridge (93). The demoted
or bounded routes are: 0-degree, parabolic slaving, anisotropy collapse,
gain/tax tether (open failure mode documented at low internal score), and
coherent-stretch-depletion (typed scaffolding stands, analytic-half
unpaid). Several null-profile and pressure-channel taxonomy routes are
staged but not yet scored. The reader should treat the checkpoint as a
snapshot of *where the proof-search apparatus is currently spending
effort*, not as a list of theorem-closures.

**Retest tag.** *Successor-run partial demotion (multiple).* Across the
campaign, several candidate routes were positively scored at one point and
later demoted or bounded by their successor runs. The demotions are
recorded next to the original artifacts. The proof-search scaffolding
itself is *not yet retested under a current apparatus version* that closes
analytic-half obligations.

**Current public status checkpoint.** As of 2026-05-27, the NS corpus is best
published as a residual-characterization and route-demotion atlas, not as a
clean proof corpus. The measured footprint is 445 direct `ns*.lean` files,
253,667 raw Lean lines, 8,810 atlas graph declarations, 1,974 closed theorem
rows, 568 exclusion theorem rows, 878 open obligation rows, 365 stripped
`axiom` rows, 382 stripped `opaque` rows, 27 stripped `sorry` rows, and 0
stripped `admit` rows. The large assumption-bearing interface surface remains
visible: 9,670 `Prop` fields, 1,408 `_proof` fields, and 416 evidence/source
fields.

**Evidence pointers.** [NS public journey/status](../projects/ns_millennium_hunt/public/JOURNEY.md);
[NS public graph](../projects/ns_millennium_hunt/public/index.html);
[Lean proof tree](../ztare_proofs/); [experiment track record](../research_areas/EXPERIMENT_TRACK_RECORD.md);
[70-day journey](sprint_70day_journey.md); NS sibling projects under
[projects/](../projects/) with `ns_*` and `ns_proofsearch_*` prefixes.

**TICK668 evidence update (2026-05-23).** A recent pressure/C7 route produced a five-direction trace-free tensor recovery certificate. The underlying finite-dimensional algebra should be treated as standard symmetric trace-free tensor reconstruction / tensor-tomography mathematics, not as an invented mathematical theorem. The project-specific claim is narrower: the algebra was used as an executable anti-laundering contract inside the PDE workbench. It repaired the single-scalar cancellation confuser, then the `pec_k` owner-preimage gate exposed the missing receipt instead of allowing pointwise recovery to be confused with selected-prefix summability. The current gate therefore rejects the route unless the five frame samples carry a cofinal owner-prefix receipt.

Evidence pointers for this update: `projects/ns_millennium_hunt/workspace/queries/tick668_route1_annular_output_identity_depth_pencil.md`; `projects/ns_millennium_hunt/workspace/queries/tick668_tracefree_tensor_frame_tomography.json`; `projects/ns_millennium_hunt/workspace/queries/tick668_five_frame_owner_fiber_prefix_witness.json`; `projects/ns_millennium_hunt/workspace/queries/tick668_five_frame_nonadaptive_currency_mismatch_witness.json`; `projects/ns_millennium_hunt/workspace/queries/pde_workbench/tick668/20260523T_five_frame_false_positive_gate/20260523T192329Z_angular_pressure_tomography_selected_packet_morphology_pointwise_tomography_without_cofinal_owner_prefix_budget/pack.md`; Lean boundary `FiveFrameTomographyOwnerFiberPrefixOverflowConfuser` / `no_TraceFreeVariationC7CofinalOwnerPrefixBudget_of_fiveFrameOwnerFiberPrefixOverflow` in `ztare_proofs/ZtareProofs/ns_tick668_pressure_cutoff_carrier_identity.lean`.

**Non-claims.** No Clay proof. No unconditional regularity proof. No blow-up
construction. No claim that proof stubs, typed wrappers, or conditional
carriers close analytic PDE obligations.

**Next falsifier or source-design step.** Route only through named residual
targets: non-taxonomic PDE estimates, analytic-half closures after typed audit
gaps, independently attested proof-search gates, or source-designed falsifiers.
Do not spend more cycles on already-demoted 0-degree or parabolic-slaving
reduction ticks unless they carry a new falsifiable obligation.

**Readiness.** Public, but requires careful framing. The journey is usable;
the claim surface still needs readers to understand "scaffold sorry-free modulo
named axioms" as bounded infrastructure, not closure.

## LeanMill: Governed Proof Search And Autoformalization

Last updated: 2026-06-16.

**Public claim.** LeanMill is a governance layer for machine-generated formal
work: LLM agents propose proofs, decompositions, and formalizations; a
deterministic stack (kernel re-compile, axiom allowlist audit,
statement-integrity diff against the original, matched negative controls)
decides what earns credit. The claim is the governance, not the prover: the
harness has repeatedly caught its own agents producing compiling-but-altered
"closures" and rejected them at solve time, with receipts in the closure
certificate ledger (`analytics/public/queries/adhoc_closure_certificates.jsonl`,
`outcome=rejected_governance`, `statement_altered_confirmed`).

**What survived.** Witness-transport closed 12/12 on a controlled corpus
(Pell / factoring / Diophantine) where the native cascade closed 0/12 — a
matched A/B, the one move with measured lift. The faithfulness firewall
(round-trip judges + SMT boundary checks) runs on non-mathematical substrates
(healthcare-privacy, aviation, export-control, DeFi policy text) and caught
meaning-altering formalizations that passed a human review battery. On the
Lam–Litt 1.1.1 order-1 program (open mathematics; no closure claimed),
kernel-ratified sub-lemma certificates — each with a statement hash and a
recompilable `.lean` artifact — accumulate across governed runs and are cited
by later runs instead of re-derived.

**Measured this round (2026-06-16).** (1) *Benchmark* — miniF2F-test, governed,
compiled warm against v4.30 Mathlib. A **depth-bounded N=23** random admissible
sample closed **10/23 = 43% (Wilson 95% 26–63%)**; an earlier **N=9
unbounded-depth pilot** landed **6/9 = 67%**. The larger bounded sample is the
more reliable estimate (the small-N pilot was optimistic) and a **conservative
floor** — the depth-1 cost cap timed 5 problems out (budget-cut, not clean
failures). The two use different budget regimes (not apples-to-apples; CIs
overlap), and the bare arm was off so the JSON `apparatus_lift` field is a
cosmetic artifact, **not** a real lift. The matched bare-vs-LeanMill apparatus-lift
A/B is built but **not yet published** (deferred on cost — the bare arm runs
~13 min/problem); **no apparatus-lift rate is claimed.** (2) *Soundness, adversarial* — a
governance red-team rejects **5/5** smuggled-unsoundness attacks
(`sorry`/`admit`/`native_decide`→`ofReduceBool`/false-axiom) and admits genuine
proofs; re-runnable (`governance_redteam.py`). (3) *Non-math firewall vs. a
steelmanned LLM judge*, 7 compliance domains: firewall **14/14**, judge
**13/14** — the edge is **precision + the certificate**, *not* catch-rate.
(4) *Certified faithfulness — opinion vs. certificate, at scale.* `certify_policy_faithfulness`
returns a typed 3-verdict **artifact** (CERTIFIED_EQUIVALENT / REFUTED with a
re-verifiable distinguishing input / OUT_OF_FRAGMENT), composing z3 + Gröbner +
the Lean kernel (no reimplemented decision procedure). On an **N=18** policy
corpus across 8 compliance domains the engine *decides* all 18 and agrees with
the z3 ground truth — but since the engine **is** z3, that agreement is a
**consistency check, NOT an accuracy claim** (it is not measured against an
independent oracle). The non-tautological signals: every verdict is a checkable
artifact, and vs the **independent** judge oracle the result is a **kept null** —
the N=5 witness gap (engine 3/3 vs judge 2/3) **did not replicate** (at N=18 the
judge matched it, 18/18 + 9/9). No measured accuracy edge; the differentiator is
the soundness *guarantee* (a re-runnable certificate vs an unguaranteed opinion). (5) *Transport-to-decidability router* —
`decidability_router.py` routes an obligation to the theory where it is
decidable; **decidable-fraction lift = +3** (portfolio 5/7 = 71% vs single best
theory 2/7 = 29%) on a mixed math+policy seed with honest OUT_OF_FRAGMENT rows.
(6) *Transport-laundering soundness* — the red-team now catches a wrong Gröbner
cofactor / false witness / asserted analogy by kernel re-verification: **8/8
rejected, 0 false-positive**, genuine transport passes — "alien" exploration is
safe by construction. (7) *Cloud/IAM policy refinement* — `certify_policy_refinement` (the SMT
policy-permissiveness check, as a faithfulness verdict) on 9 access-policy cases. Again the engine *is*
z3, so "9/9 vs z3 ground truth" is a **consistency check, not an accuracy claim**; the real signal is the
**artifact** — **5/5** over-grants (privilege escalations) caught with a concrete, **re-verifiable**
escalation request. Honest edge vs the mature SMT-policy-verification line is the *intent→formal
translation* firewall + domain-generality + independent governance, **not** out-verifying their domain grammars. Receipts:
`results/{certified_faithfulness_demo,certify_policy_corpus_run,iam_refinement_run,decidability_router,governance_redteam}.md`;
reviewer packet `docs/evidence_atlas/packets/transport_to_decidability.md`.

**What did not survive, kept on the record.** The non-math *catch-rate* edge is
a measured **null** across all three launder classes (structural, SMT-boundary,
and a purpose-built must-search class): a frontier judge reasons through the
same launders, so we claim no catch-rate edge — only precision + verifiability.
The diverse judge-diversity panel showed a **null** false-reject lift against an
already-strong single judge. Early "apparatus gives no lift"
nulls were dead-instrument artifacts (probes never parsed): the thesis was
untested, not refuted. The abduce and reflection moves are subsumed by native
automation at low degree; their lift claims were withdrawn and the nulls kept.
A run-forensics pass found that closures ratified before 2026-06-12 carry
hollow certificates (the checker verified in memory and persisted no probe);
fixed, pre-fix rows retained and labeled, and integrity-unverified closures no
longer earn credit.

**Next falsifiers.** The differential re-verification stage (a proof that also
closes its negated conclusion is rejected as vacuous-context) awaits its live
contradictory-hypothesis positive control. The Gröbner / SOS transport edges
now have a controlled A/B (both arms kernel-verified, baseline = full local
native incl. `subst_vars`): they close **2 degree-≥3 goals** (`a+b+c=0 ⊢
a³+b³+c³=3abc`; `(x²−1)²≥0`) the native cascade cannot. `polyrith` — the
historical Gröbner competitor — is **decommissioned** in current Mathlib (its
external service is dead), so the edge fills that gap locally with an auditable
cert; the lift is not a polyrith or baseline-weakness artifact.

**Readiness.** Public. The honest frame: an open problem decomposed under
governance with certified partial progress and the cheating receipts kept —
not a solved problem, not a benchmark claim.

## Consciousness-Ascription Governance

**Public claim.** The consciousness work produced a governance and
identification result, not a consciousness theory. AID-MCVP states that a
low-concern verdict on a substrate of unknown consciousness is forbidden unless
the target property is identifiable through intervention access, independent
replication, an invertible predicate bridge, and adversarial completeness.

The useful result is a veto protocol for low-concern verdicts under
non-identification.

**Status.** Scope-limited governance result with formal-adjacent follow-on
work.

**Retest tag.** *Original-run only (n=1) for the protocol itself; methodology
/ framework claim for the veto structure.* The veto protocol's formal
properties have been argued; an external replication of the protocol against
a new substrate of unknown consciousness has not been performed.

**Evidence pointers.** [multi-substrate validation](multi_substrate_validation.md);
the formal-adjacent follow-on artifact —
[`projects/gp211_paper8_lean_proofs/public/CLAIM_SUMMARY.md`](../projects/gp211_paper8_lean_proofs/public/CLAIM_SUMMARY.md)
(descent invariance under categorical equivalence, sharpening the
verdict-transport requirement for the consciousness-ascription
governance work). The wider consciousness-track sub-projects
(`gp169_consciousness_ascription_audit`, `gp210_consciousness_theory`,
`gp212_consciousness_omega_audit`) are private working areas without
per-project public summaries; the public-claim contribution is the
veto protocol itself (above) plus the gp211 sharpening.

**Non-claims.** Does not solve consciousness. Does not classify any current AI
system as conscious or not conscious. Does not prove a sufficiency direction
for a consciousness theory. Does not make a finite stressor suite complete by
assertion.

**Next falsifier or source-design step.** Stress the certificate on adjacent
governance domains, separate necessary non-identification results from
sufficiency claims, and keep alien-substrate/no-citation reframes active
whenever qualitative substrates risk corpus-gradient recapitulation.

**Readiness.** Public with narrow framing. The main risk is readers mistaking
the governance veto for a theory of consciousness.

## Modified Gravity / AQUAL / RAR

**Public claim.** The gravity campaign produced a substrate-bounded null and a
numerical-methods instrument audit. The row-wise RAR campaign across SPARC,
cluster, and wide-binary data did not unify regimes under the tested form
families; the structural diagnosis is within-class feature collapse at
cross-class joints. The 3D AQUAL-style sandbox found that diffuse UDG-like
sources can show large representation-sensitive fourfold susceptibility while
compact controls remain nearly flat.

The strongest public result is diagnostic: this substrate and this class of
multiplicative-EFE / per-galaxy-free-`gext` tests have poor
constraint-to-degree-of-freedom structure and can generate curve-fit handles.
The v3 substrate enrichment (real per-cluster masses, real per-binary radii)
is in flight and not yet a public claim.

**Status.** Bounded null plus instrument-audit result.

**Retest tag.** *Mixed.*
- Within-class feature collapse diagnosis: *diagnostic finding* — the
  collapse is structural to the v2 aggregated public dataset, not a search
  failure. The R26 G-CROSS-CLASS-FEATURE-SUPPORT gate now names it
  explicitly.
- 5-parameter PMOND v5 / 9-UDG kinematics fit: *original-run only (n=1)*;
  not re-executed under a revised gate stack.
- 3D AQUAL fourfold-susceptibility finding: *original-run only* under one
  numerical scheme; representation-invariance has not been verified.

### Internal scale-dependence candidate (`gp163d_unified_accel`)

A six-parameter density-radius susceptibility form, pre-committed to
**Hypothesis S (scale-dependence)** with anti-patterns AP-1 (false fit on
absent data) and AP-2 (hidden universality) explicitly forbidden by the
project charter and respected by the form, passes the apparatus's holdout
(class A withheld, MRE 0.275) and farther-tail (84 class-B + 12 class-C
unseen rows, MRE 0.275 against a threshold of 0.50) gates under an
apparatus-internal score of 100. Class B and C predictions are determined
by smooth functions of continuous features (`radius_log10`,
`rho_local_log10`, NaN-safe disk/gas terms on class A only) — no free
class-conditional parameter is introduced for the unseen classes.

**Retest tag.** *Apparatus-internal verdict only; original-run only (n=1);
not externally reviewed.*

**Why this is not promoted to a public unified-acceleration claim.**

- MRE < 0.50 is a loose threshold for a physics-grade claim; "agreement
  within a factor of 1.5" passes the gate, but it is not law-grade
  discrimination.
- The unseen-class sample is small (84 + 12 rows).
- The form has six free parameters with sigmoid saturations; that is
  flexible relative to the unseen evidence.
- The disk/gas features that distinguish class A are NaN on B and C, so
  the class-B/C prediction effectively rides on one continuous feature
  (`rho_local_log10`).
- The judge layer is LLM-based; the apparatus's own probability DAG sits at
  0.78, not 1.0. The "score 100" is the rubric verdict, not the
  probability the law is right.
- The supporting Lagrangian-derivability is sketched, not derived.
- The thesis's own self-flagged catastrophic mode is precisely that an
  enriched future substrate could expose a class-separating cause the
  current features do not capture.

**What is real here.** The pre-commit discipline was real, the anti-patterns
were explicitly named and respected, and a non-trivial farther-tail margin
was cleared on unseen classes under a smooth feature-conditioned form. The
result is recorded as an apparatus-internal candidate. It is not yet a public
physics claim.

**Next falsifier or source-design step.** An enriched v4 substrate that
exposes one new candidate class-separating feature (e.g., a cluster
gas-mass-profile slope or a wide-binary perihelion observable),
independently chosen; or an external physicist's re-evaluation against an
alternative phenomenological form with the same parameter count.

**Evidence pointers.** [multi-substrate validation](multi_substrate_validation.md);
[70-day journey](sprint_70day_journey.md). The internal scale-dependence
candidate has a public summary at
[`projects/gp163d_unified_accel/public/CLAIM_SUMMARY.md`](../projects/gp163d_unified_accel/public/CLAIM_SUMMARY.md).
The other gp163-family sub-projects (`gp163_accel_interpolation`,
`gp163d_DM`, `gp163d_MG`, `gp163d_susceptibility_regime_law`,
`gp163d_alien_invariant_bridge`, `gp163d_admsr_attack_and_cleanroom_bridge`,
`gp163d_science_promotion_bridge`) are private working areas without
their own public summaries; the per-arm findings are recorded in the
internal seam ledger, not on the public surface.

**Non-claims.** Does not adjudicate MOND versus dark matter. Does not claim
MOND fails on clusters. Does not claim a physical AQUAL orientation law. Does
not claim the fourfold phase is representation-invariant. Does not treat
fitted `gext` boundary-pinning as an environment estimate. *Does not* claim
the `gp163d_unified_accel` apparatus-internal score-100 result is a
unified-acceleration law.

**Next falsifier or source-design step (campaign-level).** Either define a
representation-invariant diffuse susceptibility observable that survives
adversarial boundary and stencil changes, or leave the sandbox result as a
numerical-methods instrumentation finding. Future modified-gravity campaigns
should prefer higher constraint-to-DoF tests such as strong lensing,
wide-binary acceleration, or GW170817-style scalar/EFE bounds.

**Readiness.** Public as a demotion and diagnostic story plus an
apparatus-internal scale-dependence candidate. Not ready as a positive
physics claim.

## Neural Scaling And Mechanistic Audits

**Public claim.** The neural work produced bounded findings and several clean
negative results. Mechanistic audits identify BOS mean-pooling as a source of
low-rank illusion in hidden-state analysis. Scaling-law work found an OLMo2
7B/13B gauge-removed trajectory morphology regularity, but stronger promotion
paths failed: optimizer-control phase-flow anti-transferred to production
telemetry, exact OLMo2 1B closed the slope-anchor path negatively, and
same-packet eval-state rescues failed under persistence and observability
baselines.

The useful public claim is source-admissibility discipline: some neural
regularities survive as bounded morphology; several attractive law readings do
not.

**Status.** Bounded empirical result plus source-design program.

**Retest tag.** *Mixed.*
- BOS mean-pooling as a source of low-rank illusion: *original-run only (n=1)*
  on the specific hidden-state slices probed; the *mechanism* is recorded,
  the *generality across architectures and training stages* is not retested.
- OLMo2 7B/13B trajectory morphology regularity: *original-run only (n=1)*;
  it survived its initial gates, but the *promotion path* was demoted (see
  below).
- OLMo2 1B slope-anchor: *negative result on retest.* Demotion durable.
- Optimizer-control phase-flow: *negative result on retest.* Anti-transfers
  from toy grids to production telemetry.
- Same-packet eval-state rescues: *negative result on retest.* Failed under
  persistence and observability baselines.

**Closed null at apparatus level.** The `neural_hunt` campaign closed
hypotheses H-01 through H-12 as negative under contemporary OLMo2
raw-train-loss data. The GPU checkpoint-eval packet (H-16 onwards) is staged
but not yet executed. The honest framing is that the *failed* law candidates
are the durable evidence here.

**Evidence pointers.** The substantive evidence for the closed-
negative campaign is consolidated in the Neural Hunt public summary:
[`projects/neural_hunt/public/CLAIM_SUMMARY.md`](../projects/neural_hunt/public/CLAIM_SUMMARY.md).
The summary catalogues H-01 through H-12, the demoted hypotheses, and
the first gate on any future neural work. Companion context:
[multi-substrate validation](multi_substrate_validation.md) and the
[70-day journey](sprint_70day_journey.md). The earlier `gp154_*`
per-project links cited in prior drafts are *not* public evidence
anchors — the substantive evidence lives in the consolidated
neural-hunt audit, not in per-project sealed sandboxes.

**Non-claims.** Does not claim a universal neural scaling law. Does not claim
endpoint-free OLMo2 1B validation. Does not claim optimizer-control telemetry
transfers from toy grids to production training. Does not promote public
aggregate eval movement into per-instance law evidence.

**Next falsifier or source-design step.** Use sealed per-instance checkpoint
eval packets with aggregate metrics plus per-instance prediction/logprob rows.
Task selection from public aggregates must be treated as targeting, not law
evidence, until earlier and mid-stage checkpoint windows outside the selector
window survive.

**Readiness.** Public as bounded empirical/source-admissibility work. Not ready
as universal scaling theory.

## Asymptotic-Law Sandbox Recoveries (Per-Substrate)

**Public claim.** Under a sealed apparatus (deterministic holdout +
farther-tail gates, template-enumeration compression, observable rotation,
fixed grammar/exponent grid), the engine recovered the leading asymptotic
structure of several integer sequences presented as unlabeled observables,
and *correctly returned null* on substrates where no closed-form
compression exists. Across the substrates tested, the apparatus-internal
false-positive rate was zero on incompressible targets. An independent
symbolic-regression tool (PySR) arrived at the same Lucky-number density
coefficient on the substrate it was run against. None of the
asymptotic-form recoveries here is a discovery claim against an unknown
target; each is a *blinded recovery against an answer the engine was not
shown* — i.e., a calibration class of result, not a discovery class.

**Status.** A set of sealed per-substrate sandbox recoveries plus named
incompressible-substrate nulls. Each substrate stands on its own sealed
sandbox; the per-substrate public surface is the project's
`public/CLAIM_SUMMARY.md`, not a synthesized paper.

**Per-substrate outcomes (each backed by a public summary in the
project's `public/` slice).**

- **Meinardus partitions into squares (OEIS A001156).** Topology
  identified — the fit converged on the Meinardus-predicted `n^(1/3)`
  exponent within 0.5% under cold variable names. The composite
  rational form clears the visible-window gates (max residual < 0.02);
  the absolute-residual gate at large `n` is conservative on a
  large-scale observable, normalized relative residual is 0.16%.
  Apparatus-internal score 85. Public summary:
  [`projects/oeis_a001156/public/CLAIM_SUMMARY.md`](../projects/oeis_a001156/public/CLAIM_SUMMARY.md).
  *Retest tag: original-run only (n=1); topology correct, absolute-
  residual gate conservative.*

- **Hardy-Ramanujan derivative (OEIS A002865).** Canonical sealed
  result is the dynamic-programming recurrence recovery in
  `gp077_a002865_01` at apparatus-internal score 96: the
  empirical-asymptotic-fitting axiom was retired, the analytic
  Hardy-Ramanujan-Rademacher k=1 constants
  (`K = π√(2/3) ≈ 2.565`, `M = 1/(2π√2) ≈ 0.113`) were enforced as
  rigid, and exact integer values were produced by the
  `p(n) − p(n−1)` recurrence. This is the canonical INS-015 instance
  of judge-demotion-then-recovery discipline. Public summary:
  [`projects/gp077_a002865_01/public/CLAIM_SUMMARY.md`](../projects/gp077_a002865_01/public/CLAIM_SUMMARY.md).
  A weaker direct-fitting variant exists in `oeis_a002865` (score 54);
  the contrast between the two records the effect of enforcing the
  analytic constants instead of fitting them. Details in
  [`projects/oeis_a002865/public/CLAIM_SUMMARY.md`](../projects/oeis_a002865/public/CLAIM_SUMMARY.md).
  *Retest tag: original-run only (n=1) per variant.*

- **Lucky-number density (OEIS A000959).** Three sealed variants on
  the public record: the original lower-`n` run
  (`oeis_a000959`, score 29 — incomplete), the enlarged-data run
  (`oeis_a000959_500k`, score 77 — strongest, structural log-leading
  form identified, partial closure), and a Newton-step validation
  attempt (`oeis_a000959_newton`, score 12 — *negative result*,
  Newton-step path falsified). The log-leading topology is consistent
  with the conjectured Prime-Number-Theorem analog for lucky numbers;
  numerical closure on the leading coefficient is not in the public
  record on these projects. Cross-tool PySR baseline data exists in
  private working material and is not part of the current public
  record. Public summaries:
  [`projects/oeis_a000959/public/`](../projects/oeis_a000959/public/CLAIM_SUMMARY.md),
  [`projects/oeis_a000959_500k/public/`](../projects/oeis_a000959_500k/public/CLAIM_SUMMARY.md),
  [`projects/oeis_a000959_newton/public/`](../projects/oeis_a000959_newton/public/CLAIM_SUMMARY.md).
  *Retest tag: enlarged-data confirmed (500k vs base); Newton-step
  variant demoted as a durable negative result.*

- **Ulam numbers (OEIS A002858).** The sealed direct-ratio blind run
  is a *null result*: `gp088_oeis_a002858`, score 0 — no closed-form
  law for `U(n)/n` proposed against the gate battery. The reciprocal
  observable-rotation finding referenced in earlier internal
  write-ups is held privately and is not part of the current public
  record. Public summary:
  [`projects/gp088_oeis_a002858/public/CLAIM_SUMMARY.md`](../projects/gp088_oeis_a002858/public/CLAIM_SUMMARY.md).
  *Retest tag: original-run only (n=1); null result by protocol.*

- **Prime partitions (OEIS A000607).** Sealed bare-sequence run is a
  *null result*: `gp088_oeis_a000607`, score 0 — no closed-form law
  proposed against the gate battery without the compositional-
  template layer. The Vaughan `√(n/ln n)` compositional finding
  referenced in earlier internal write-ups is held privately and is
  not part of the current public record. Public summary:
  [`projects/gp088_oeis_a000607/public/CLAIM_SUMMARY.md`](../projects/gp088_oeis_a000607/public/CLAIM_SUMMARY.md).
  *Retest tag: original-run only (n=1); null result by protocol.*

- **Partitions into distinct parts (OEIS A000009).** Partial
  structural identification: the framework `p₁·√n + p₂·(log n)^γ + p₃`
  with `0 < γ < 1` was identified and differentiated from the integer-
  log rival, but final parameters did not finalize cleanly.
  Apparatus-internal score 67. Public summary:
  [`projects/oeis_a000009/public/CLAIM_SUMMARY.md`](../projects/oeis_a000009/public/CLAIM_SUMMARY.md).
  *Retest tag: original-run only (n=1); framework identified, closure
  pending.*

**Held privately (not in current public record).** Several results
that appeared in earlier internal write-ups do not have sealed
sandbox projects with public summaries and are therefore *not part of
the public claim surface*: the Hardy-Ramanujan partition recovery
(A000041) including the PSLQ identification of the leading
`π√(2/3)`; the Ulam reciprocal observable-rotation finding (the
`n/U(n)` compression and the spectral-period discrepancy vs.
Steinerberger 2017); the Vaughan compositional-template recovery
(`√(n/ln n)`); the incompressible-substrate nulls on Mertens, prime
gaps, and the three further blinded substrates S1–S3; the PySR
cross-tool baseline on those five substrates; and the sopfr (A001414)
grammar-vs-space ceiling diagnosis. To enter the public record, each
of these would need its own sealed project under `projects/` with a
`public/CLAIM_SUMMARY.md`.

**Evidence pointers.** The public evidence for each per-substrate
recovery is the project's own `public/CLAIM_SUMMARY.md` — the working
directory of each OEIS sandbox is private, but each public summary
records the recovered form, the gate verdicts, the retest tag, and the
honest framing for that one substrate. The substrate-specific summaries:

- A001156 (Meinardus partitions into squares):
  [`projects/oeis_a001156/public/CLAIM_SUMMARY.md`](../projects/oeis_a001156/public/CLAIM_SUMMARY.md).
- A002865 (Hardy-Ramanujan derivative) — secondary DP-recurrence
  recovery, score 96, canonical INS-015 instance:
  [`projects/gp077_a002865_01/public/CLAIM_SUMMARY.md`](../projects/gp077_a002865_01/public/CLAIM_SUMMARY.md).
- Remaining per-substrate summaries (A000959 Lucky, A002858 Ulam,
  A000607 Vaughan prime partitions, A000041 Hardy-Ramanujan partition,
  A001414 sopfr grammar-vs-space ceiling, and the incompressible
  nulls Mertens / prime gaps / S1-S3) are being authored. Until each
  lands, the per-substrate retest tags above stand on the project's
  internal artifacts, not on a public summary.

The cross-tool result — PySR independently arriving at `a = 1.204` on
Lucky numbers vs. ZTARE's `a = 1.200` — should appear in the
per-substrate Lucky-number summary once it is written; the comparison
data is held privately.

Related public artifacts (the case-study reproducers, not OEIS
recoveries): [`papers/case_studies/`](../papers/case_studies/)
(rank-deficient bootstrap, evidence-grid underdetermination, evidence
enrichment saturation) and
[`benchmarks/benchmark_evidence.md`](../benchmarks/benchmark_evidence.md).

**Non-claims.** Does not claim discovery of new number-theoretic laws. Does
not claim ZTARE search dominates all symbolic-regression methods. Does not
benchmark the current general-purpose reasoning / scientific validation system.
The unknown-substrate hit rate remains explicitly bounded.

**Next falsifier or source-design step.** Add more blinded substrates,
especially category-switch targets where the expression grammar admits the
answer but the mutator does not naturally enter the right mathematical
category. Re-run the Lucky-number and Hardy-Ramanujan recoveries under the
current apparatus version to convert the n=1 evidence into n=2.

**Readiness.** Public as a draft and methodology note; per-substrate outcomes
public with the retest tags above. Not yet a finished paper-grade claim
surface.

## Vocabulary-Escape Calibration (Planck Sandbox)

**Public claim.** Under the sealed nine-gate decomposed apparatus
(charter-committed gate battery, sealed farther-tail holdout, exact-fitter
audit, post-identifiability reparameterization, hardening seam R1–R6), a
general-purpose LLM mutator converged from a naive monotonic power-law seed
onto an operator-authored non-elementary transcendental ground-truth functional
form

  `I(φ, ψ) = A · φᵖ / (exp((γ·φ/ψ)^q) − 1) + offset`

with `A = 0.95, p = 2.30, γ = 0.72, q = 1.30, offset = 0.06`, in
≤10 iterations. All nine deterministic gates pass at machine precision
(hidden global residual 5.95×10⁻⁶ against threshold 0.05; farther-tail global
residual 3.27×10⁻⁶ against threshold 0.01; terminal-value residuals ~7.2×10⁻⁷
against threshold 5×10⁻³).

The recovered functional form is the Planck / Bose-Einstein geometric-series
occupancy shape `x / (exp(x^q) − 1)`, which is not in the mutator's typical
regression-toolbox repertoire. The mutator was forced into it by the
hidden-gate residual landscape under the apparatus.

**Status.** Sealed sandbox calibration result. The honest category for this
result is *vocabulary-escape recovery of an operator-committed non-elementary
target under a sealed apparatus.*

**What this is not.** Not a demonstration of open-ended scientific discovery.
The ground-truth form and coefficients were authored by the operator before
the mutator ran. The mutator solved a very difficult curve-fitting problem
under extreme external constraint and recovered the exact hidden form; it did
not derive a physical law from first principles against an unknown target.
The result proves the cage is strong enough to force vocabulary escape *when
the operator knows the answer*. It does not prove the cage is strong enough
to force convergence on a correct form when the operator does not.

**Retest tag.** *Successor-run partial demotion (axis-specific).* The frozen
sandbox_06 result is the calibration baseline. Successor sandboxes on the
*eml-only vocabulary axis* (sandbox_07, sandbox_08) closed at score 0 under
the standard vocabulary — establishing that the convergence does not
trivially generalize when the mutator's vocabulary is restricted.
Sandbox_08 post-mortem identified a feature-bag completeness gap.
Sandbox_09 was scaffolded as a clean blind re-run on the eml-only axis with
a live negative-space extractor. The frozen sandbox_06 result itself stands,
with the explicit caveat that its successor-axis runs have not reproduced
the convergence under restricted vocabularies. The continuous-residual
unfalsifiability finding (INS-011) was confirmed twice across sandbox_09 v2
and sandbox_10.

**Evidence pointers.** Public summary with gate verdicts, recovered form,
and SHA-256-fingerprinted file manifest:
[`projects/gp023_planck_sandbox_06/public/CLAIM_SUMMARY.md`](../projects/gp023_planck_sandbox_06/public/CLAIM_SUMMARY.md).
The working directory and `_frozen_reference/` material (thesis, generator
`raw/generate_curve_v3.py`, hardening seam, `latest_eval_results.json`)
are private; the public summary's fingerprints make every cited artifact
verifiable for any reader granted local access. Successor runs
(`projects/gp023_planck_sandbox_07/`, `_08/`, `_09/`, `_10/`) are also
private; their negative outcomes on the eml-only vocabulary axis are
summarized under *Retest tag* above.

**Non-claims.** Not a discovery of a physical Planck law. Not a claim that
the same convergence holds under arbitrary mutator vocabularies. Not a claim
that vocabulary escape is a general property of the mutator; it is a
property of *this* apparatus under sealed sandbox_06 conditions.

**Next falsifier or source-design step.** Promote vocabulary-escape recovery
from sandbox_06 (operator-authored target) to a blinded-oracle successor
(unknown target, operator-oracle coupling removed). That experiment is the
H-SP2-04 thread.

**Readiness.** Public as a calibration result with the explicit "operator
knew the answer" caveat. Not ready as a discovery claim.

## Polymer Stress-Relaxation Blind Fit

**Public claim.** Presented with 22 visible points plus 4 hidden tail points
of a monotonic scalar dataset (no domain labels), the engine recovered

  `G(t) = A · t^(−B) · exp(−C·t)`,  with  `A = 0.006598, B = 0.4328, C = 0.754`,

under deterministic gates: normalized RMSE < 10% on the full point set,
tail-point residual at t = 2.12 within ±10%, and a named structurally
strongest rival (log-quadratic exponential
`exp(−a·log(t/t₀) − b·[log(t/t₀)]²)`) fails the same tail-point test by
> 50%. The fit holds the asymptotic wall gate as well.

The source dataset is the stress-relaxation curve of a noncatenated
polystyrene ring polymer melt (molecular weight 198 kDa), reported as the
blue curve in figure 1 of the source paper. The source paper's Eqn. 1 gives
the *a priori theoretical expectation* (not a fit) for this regime, and the
engine's blind three-parameter recovery is close to that theoretical
expectation. The operator did not name the substrate or the source paper to
the engine.

**Status.** A blind recovery of a known physical form on a single dataset,
with external validation by the source paper's a priori theory.

**Retest tag.** *Original-run only (n=1) under cold variable names; the
external comparison to the source paper's Eqn. 1 is a theory-vs-fit
agreement, not an independent re-run of the engine.* The engine has not been
pointed at additional stress-relaxation datasets (other molecular weights,
other ring-polymer melts, other relaxation regimes) under the same gates.

**What this is not.** Not a discovery of new polymer-melt physics. Not an
adjudication between the source paper's theoretical derivation and rival
empirical fits. Not a claim that the same engine recovers ring-polymer
forms in regimes outside the t-range tested. The reported parameters are
single-fit values; uncertainty quantification beyond the gate thresholds
was not reported.

**Evidence pointers.** Public summary with parameters, gate verdicts, and
the discriminator-test framing:
[`projects/gp096_sandbox_20/public/CLAIM_SUMMARY.md`](../projects/gp096_sandbox_20/public/CLAIM_SUMMARY.md).
The working directory (`projects/gp096_sandbox_20/`) is private; the
source paper is named in the project's narrative but is *not republished
here* and is identified only via the operator's external comparison.
This work was developed in collaboration with an external scientist;
attribution is held pending source-paper context being released alongside.

**Non-claims.** Does not claim the recovered parameters match the source
paper's theoretical values exactly; only that the form and the rough
parameter regime line up. Does not generalize beyond the single dataset.

**Next falsifier or source-design step.** Either republish the dataset and
the source paper's Eqn. 1 alongside the fit so a reader can verify the
agreement directly, or run the same blind protocol on a second
ring-polymer-melt dataset (different MW, different regime) and report the
form recovered. Both are real falsifier moves; the first is cheaper.

**Readiness.** Public as a single bounded blind-fit result with explicit
n=1 status. Not ready as a polymer-physics claim.

## Sealed Apparatus Calibrations And Curve-Fit Sandboxes

These are sealed, per-substrate calibrations and curve-fit recoveries that
support the campaign claims above. Each is *original-run only (n=1)* unless
noted; together they document the apparatus's behavior across a range of
operator-authored or literature-sourced targets. Project directories under
`projects/gp*` and `projects/oeis_*` are private working areas; the public
evidence is the per-project thesis and the champion-eval verdict.

- **`gp023_crucial_01` — Wien-class structural discovery at low cost.**
  Score 97/100, sealed champion. A cheap-tier mutator under the validated
  cage identified the Wien exponential family for an
  operator-authored Planck-adjacent target; total spend ~$1.01.
  *Retest tag: original-run only (n=1); farther-tail gate pending and
  expected to fail on the non-Wien asymptotic, per project notes.*
  The recorded finding is that the selection pressure came from the
  apparatus gates, not from the model: a cheap-tier mutator reached the
  Wien family under the gate stack. This is not a derivation of a physical
  law.

- **`gp023_crucial_02`, `gp023_crucial_03` — Planck-shape calibration
  cohort.** Score 88/88 each. Multi-regime structure confirmed across
  sweeps; supporting calibration runs for the Planck-shape vocabulary-escape
  thread.
  *Retest tag: original-run only (n=1) each.*

- **`gp077_a002865_01` — partition recurrence (A002865) recovery under
  dynamic-programming mode.** Score 96. The judge correctly scored an
  early overclaim at 70 (demanding derivation), the mutator regressed to 57
  on continued overclaim, and the judge reverted on the corrected
  derivation. The canonical instance of judge-correctly-demoted-then-
  recovered discipline (INS-015).
  *Retest tag: original-run only (n=1); the apparatus-discipline behavior
  is the reusable artifact, not the recurrence itself.*

- **`gp080_01`, `gp080_02` — underdetermination-boundary empirical
  instance.** Scores 98 and 94. The rational form
  `x₂ / (p₀·x₁ + p₁ + p₂/x₁)` passes holdout; the judge independently
  named exponential-exclusion at score 94 without ground-truth access.
  Post-close farther-tail evaluation confirmed structural-class mismatch
  with the true bi-exponential ground truth. The canonical INS-018
  instance: a holdout hard-gate is *insufficient* — farther-tail
  discrimination is necessary to detect underdetermination.
  *Retest tag: original-run only (n=1) for the recovery; post-hoc
  farther-tail demotion sealed. `gp080_03` is in-flight and not yet a
  claim.*

- **`gp069_sandbox_12` — modular-arithmetic quadratic-congruence
  recovery.** Score 83. `y = (3x² + 5x + 7) mod 13` recovered;
  second-difference discriminator isolates the form from a linear rival.
  *Retest tag: original-run only (n=1); vocabulary-boundary check
  (INS-012).*

- **`gp072_sandbox_14` — chirp-signal recovery.** Score 94.
  `f(x) = A·sin(B·x²)` with monotonically compressed oscillation frequency;
  zero-crossing gaps discriminate chirp from harmonic rival.
  *Retest tag: original-run only (n=1).*

- **`gp061_sandbox_11_01` — two-variable threshold model.** Score 95.
  Piecewise non-differentiable structure `V = max(baseline, slope·(t − t_c(R)))`
  with control-delayed Heaviside threshold. Holdout passes; farther-tail
  asymptotic verified.
  *Retest tag: original-run only (n=1).*

- **`gp096_kww_sandbox_17` — stretched-exponential (KWW) blind recovery.**
  Score 98 across all seven gates at machine precision (hidden global
  residual 10⁻⁶; farther-tail at 4× the visible t-range also at 10⁻⁶).
  Recovered form `a·exp(−b·t^c) + d` with `a = 2.810, b = 0.396,
  c = 0.630, d = 0.470`; structural equivalence to the operator-authored
  KWW ground truth confirmed (`b = 1/τ^β` match to 0.0002%). The score
  plateau at 98 corresponds to a Prony-series objection that is
  mathematically a correct unfalsifiable ceiling, not a gap.
  *Retest tag: original-run only (n=1) under cold variable names;
  operator-authored ground truth so this is a calibration win.* Public
  summary:
  [`projects/gp096_kww_sandbox_17/public/CLAIM_SUMMARY.md`](../projects/gp096_kww_sandbox_17/public/CLAIM_SUMMARY.md).

- **`gp096_langevin_sandbox_16` — depth-1 composition ceiling diagnosis.**
  Score 75. The true Langevin form `coth(B·u) − 1/(B·u)` requires a
  depth-2 composition (ratio of sums inside an exponential) that depth-1
  templates cannot express. The apparatus correctly identified that
  depth-1 cannot reach the true form; H-GP103 (compositional hypothesis
  generator + trigger-guard fix) is the remedy.
  *Retest tag: diagnostic finding (no recovery to retest).*

- **`gp096_sandbox_18`, `gp096_sandbox_18_gagorder` — DFDO topology-induction
  gap.** Score 95 on each, on a two-regime Duffing-plus-power-law substrate.
  The recovered form passes the hard gates but is a *functional surrogate*
  in the wrong structural class — the minimum gate-passing form is a
  two-regime additive composite `a·exp(−b·u^p) + C·(1+d·u)^{-3.70}` that
  the apparatus never proposed. Trigger-guard bug confirmed (H-GP103).
  *Retest tag: diagnostic finding.*

**Public summaries.** Each sealed calibration above has a one-page
public summary at `projects/<name>/public/CLAIM_SUMMARY.md`:
[`gp023_crucial_01`](../projects/gp023_crucial_01/public/CLAIM_SUMMARY.md),
[`gp023_crucial_02`](../projects/gp023_crucial_02/public/CLAIM_SUMMARY.md),
[`gp023_crucial_03`](../projects/gp023_crucial_03/public/CLAIM_SUMMARY.md),
[`gp077_a002865_01`](../projects/gp077_a002865_01/public/CLAIM_SUMMARY.md),
[`gp080_01`](../projects/gp080_01/public/CLAIM_SUMMARY.md),
[`gp080_02`](../projects/gp080_02/public/CLAIM_SUMMARY.md),
[`gp069_sandbox_12`](../projects/gp069_sandbox_12/public/CLAIM_SUMMARY.md),
[`gp072_sandbox_14`](../projects/gp072_sandbox_14/public/CLAIM_SUMMARY.md),
[`gp061_sandbox_11_01`](../projects/gp061_sandbox_11_01/public/CLAIM_SUMMARY.md),
[`gp096_kww_sandbox_17`](../projects/gp096_kww_sandbox_17/public/CLAIM_SUMMARY.md),
[`gp096_langevin_sandbox_16`](../projects/gp096_langevin_sandbox_16/public/CLAIM_SUMMARY.md),
[`gp096_sandbox_18`](../projects/gp096_sandbox_18/public/CLAIM_SUMMARY.md).

## Apparatus Self-Audits

These projects are apparatus-internal hardening and self-audit work. Each
records a structural property of the apparatus (a failure mode caught, a
gate proven necessary, a ceiling diagnosed), not a substrate finding. The
durable evidence is the catalogued failure mode plus the apparatus change
that closed it.

Each project below has a public summary at
`projects/<name>/public/CLAIM_SUMMARY.md` (the working directory is
private; the summary records the claim, score, and retest tag).

- **`gp145_saw_mu_square` and `gp145b_saw_narrow_null` —
  self-avoiding-walk constant μ_sq, rigorous null.** Run-1 null at
  apparatus-internal score 56 with PSLQ on `Δ₁` (dim ≤ 5, height
  H ≤ 10⁸) under an empirical `κ̂` bound and the
  Bailey-Ferguson 1992 deterministic-recovery guarantee. Run-2
  (`gp145b`) narrows scope to `Δ₀_small` with a *provable* `κ̂` margin
  at 450 bits; the null persists at score 48. The G2 PSLQ-falsity gate
  held across all runs (no false positive). Recorded as **INS-053**.
  *Retest tag: cross-scope confirmed.*
  Summaries:
  [parent](../projects/gp145_saw_mu_square/public/CLAIM_SUMMARY.md),
  [narrow-scope sibling](../projects/gp145b_saw_narrow_null/public/CLAIM_SUMMARY.md).

- **`gp146_arnold_cat_map_validation` — Arnold cat-map
  self-validation.** Score 92. Apparatus pointed at a known chaotic
  map (`λ₁ = log((3 + √5)/2)`) and asked to close the discovery +
  Lean-verification loop against the analytic answer; loop closed.
  Recorded as **INS-047**.
  *Retest tag: original-run only (n=1); calibration against a known
  result.*
  Summary:
  [`projects/gp146_arnold_cat_map_validation/public/CLAIM_SUMMARY.md`](../projects/gp146_arnold_cat_map_validation/public/CLAIM_SUMMARY.md).

- **`gp147_gate_discovery_validation` — file-level guardrail gates at
  the Phase-D / E¹ bridge.** Score 88. Six new structural-admissibility
  gates (H1–H8 hazard coverage) added to the `make discover` pipeline,
  on the hypothesis that every still-wrong claim-artifact will violate
  at least one hazard before external submission.
  *Retest tag: original-run only (n=1); apparatus hardening claim.*
  Summary:
  [`projects/gp147_gate_discovery_validation/public/CLAIM_SUMMARY.md`](../projects/gp147_gate_discovery_validation/public/CLAIM_SUMMARY.md).

- **`gp150_epistemic_boundary_audit` — subordinated Brownian semigroup
  truncation audit.** Score 71. Identifies that the apparatus's
  advertised *continuous-mixture* implementation is in fact a
  finite-table approximation and bounds the truncation error envelope.
  Recorded as **INS-024**.
  *Retest tag: original-run only (n=1); epistemic-scope audit.*
  Summary:
  [`projects/gp150_epistemic_boundary_audit/public/CLAIM_SUMMARY.md`](../projects/gp150_epistemic_boundary_audit/public/CLAIM_SUMMARY.md).

- **`gp152_framer_architecture_audit` and `gp153_framer_spec_critique`
  — Framer-language audit.** Scores 91 each. Verifies that a bounded,
  symmetry-filtered, MDL-driven pre-solver phase reduces description
  length under named scope, and audits the v1.1 spec for residual
  under-determination. Recorded as **INS-031** and **INS-032**.
  *Retest tag: original-run only (n=1) per sibling.*
  Summaries:
  [architecture audit](../projects/gp152_framer_architecture_audit/public/CLAIM_SUMMARY.md),
  [spec critique](../projects/gp153_framer_spec_critique/public/CLAIM_SUMMARY.md).

- **`gp156_apparatus_hardening_review` — foundational five-layer
  hardening review.** Score 97. The driving instance is a *fail-open*
  fit-primitive failure: a misspelled feature key in `PARAMETRIC_FORM`
  is silently swallowed by the optimization stack, which converges to
  arbitrary parameters and writes a valid-looking result. The review
  extends the pattern to five layers (pre-commit verifier, gate
  harness, judge isolation, rubric calibration, fit-primitive
  contract) and catalogues **INS-001 through INS-006**, the
  fractal-Goodhart-at-every-layer findings that underwrite
  [`docs/concepts/goodhart_at_every_layer.md`](concepts/goodhart_at_every_layer.md).
  *Retest tag: methodology / framework claim; the foundational
  apparatus-hardening artifact.*
  Summary:
  [`projects/gp156_apparatus_hardening_review/public/CLAIM_SUMMARY.md`](../projects/gp156_apparatus_hardening_review/public/CLAIM_SUMMARY.md).

- **`gp158_v5_cage_orchestrator_audit` — six v5.0 orchestrator design
  defects.** Score 82. Each defect is anchored to a *line range* in
  the internal v5 super-architecture map (e.g., DEFECT #1 is the
  REACHABILITY GAP in `cage.dispatch.can_handle` at lines 313–325).
  Recorded as **INS-043**.
  *Retest tag: original-run only (n=1); apparatus / framework claim.*
  Summary:
  [`projects/gp158_v5_cage_orchestrator_audit/public/CLAIM_SUMMARY.md`](../projects/gp158_v5_cage_orchestrator_audit/public/CLAIM_SUMMARY.md).

- **`gp159_retrieval_trap` — named failure mode (over-parametrized
  collapse).** Score 90. When visible data is generated by
  `y = a/(x + b)` with non-standard constants, the apparatus's
  three-parameter generalization `y = a/(x+b)^c` returns `c = 1.0000`
  deterministically (no residual improvement to allocate); the rival
  three-parameter monotones with `1/x` tails and `K_law ≤ 3` collapse
  to the same form. Sealed structural-uniqueness claim. Recorded
  adjacent to INS-006.
  *Retest tag: diagnostic finding.*
  Summary:
  [`projects/gp159_retrieval_trap/public/CLAIM_SUMMARY.md`](../projects/gp159_retrieval_trap/public/CLAIM_SUMMARY.md).

- **`gp160_asymptotic_wall` — grammar-ceiling diagnosis.** Score 82.
  Additional compute does not break a structural ceiling imposed by
  the expression grammar; only grammar expansion enables structural-
  class transitions. The companion finding (the space ceiling on the
  sopfr substrate, where the grammar admits the answer but the
  mutator searches in the wrong mathematical category) bounds the
  apparatus from the other side. Recorded as **INS-020 / INS-021**.
  *Retest tag: diagnostic finding.*
  Summary:
  [`projects/gp160_asymptotic_wall/public/CLAIM_SUMMARY.md`](../projects/gp160_asymptotic_wall/public/CLAIM_SUMMARY.md).

- **`gp161_mdl_anti_goodhart` — Goodhart immunity at the selection
  layer.** Score 81. MDL/BIC parsimony pressure does not force the
  apparatus to retreat to a structurally inconsistent simpler form
  (the canonical instance: an exponential envelope paired with a
  log-chirp phase that is *mathematically inconsistent* even though
  it fits visible data; the apparatus correctly re-derives the
  consistent envelope rather than accepting the parsimony-preferred
  one). Recorded as **INS-028**.
  *Retest tag: original-run only (n=1); methodology / framework claim
  for selection-layer Goodhart immunity.*
  Summary:
  [`projects/gp161_mdl_anti_goodhart/public/CLAIM_SUMMARY.md`](../projects/gp161_mdl_anti_goodhart/public/CLAIM_SUMMARY.md).

- **[GP-233](../research_areas/seams/apparatus/instrumentation/GP-233_research_yield_decomposition_seam.md) — research-yield decomposition with zero-false-ratify
  governance gate.** A seam contract decomposes scientific yield into
  named factors (candidate supply, eligibility rate,
  verification-compile rate, residual-or-closure rate, decision impact,
  per wall-time or cost) rather than a single scalar. The governance
  gate (`gp233_adversary_yield_decomp.py`) four-way classifies Lean
  proof rows — genuine novel closure, single-lemma rejected,
  consequence-exposure axiom-dependent (not genuine), prover-self-gap —
  under a `#print axioms` kernel guard that trusts only
  `{propext, Classical.choice, Quot.sound}`. The controlling invariant
  is *zero false ratification*. An independent adversarial review of
  the kernel-axioms guard is in flight; until it clears, the bundle's
  genuine counts carry that caveat. Evidence ledger at
  `analytics/public/ledgers/research_yield_decomposition/`; seam at
  `research_areas/seams/apparatus/instrumentation/GP-233_research_yield_decomposition_seam.md`.
  *Retest tag: methodology / framework claim; kernel-axioms guard under
  independent adversarial review.*

## Methodology And Apparatus-Hardening Papers

These are paper-stage tracks that argue properties of the apparatus
itself, not findings on substrates. They are first-class public artifacts
and are listed here so a reader who lands on this register sees them.

- **Specification Gaming in LLM-Generated Code / Cognitive Camouflage.**
  Published on SSRN (6512960). Documents the original nine
  specification-gaming strategies across at least six evaluation
  domains; the live public gaming catalog extends that paper-level
  taxonomy with later mined cross-substrate vectors and gate status.
  Cross-mutator replication (Gemini, Claude, GPT-4o) shows that gaming
  is *mutator-family-specific*: Gemini and Claude exhibit strategic
  gaming under adversarial pressure, while GPT-4o oscillates and never
  sustains convergence. Suite Omission is treated as an emerging
  cross-mutator pattern rather than one of the original nine. A
  four-condition judge-failure benchmark (baseline soft judge →
  deterministic gates → gates + primitives → crux-first) shows holistic
  LLM judging is fooled by Suite Omission while adversarial execution
  catches it.
  *Public artifact:* `papers/cognitive-camouflage/draft.md` and the
  SSRN preprint.
  *Retest tag: cross-mutator replicated* on the gaming-detection axis.

- **Adversarial Precedent Memory (evaluator hardening).** Published on
  SSRN (6525598). Argues that deterministic gates plus an adversarial
  precedent library let an evaluator catch specification-gaming
  strategies that holistic LLM review misses. Four central claims in
  the Introduction; the paper is the primary reference for the
  zero-trust adversarial evaluator architecture used throughout the
  rest of the repository.
  *Public artifact:* `adversarial-precedent-memory/paper2.md`,
  `adversarial-precedent-memory/main.pdf`.
  *Retest tag: methodology / framework claim* — the paper itself is
  the durable evidence; the gating architecture it argues for is
  reused across the campaigns above.

- **Contract-Governed Hardening.** Working paper at
  `contract-governed-hardening/main.pdf`. Argues for apparatus
  hardening through explicit contract specification (fit-primitive,
  gate, rubric contracts) rather than soft narrative review.
  Complements the adversarial-precedent-memory paper.
  *Retest tag: methodology / framework claim.*

- **Adversarial Substrate Prober.** Working paper draft at
  `adversarial-substrate-prober/draft.md` (~v0.1, April 2026). Argues
  the substrate-prober framing: LLM-driven symbolic regression that
  *diagnoses* what data can and cannot answer, rather than claiming a
  positive law. Includes the within-class feature-collapse finding on
  the v2 RAR substrate that triggered the v3 substrate enrichment now
  in flight under the Modified Gravity campaign.
  *Retest tag: original-run only (n=1) for the v2 feature-collapse
  diagnosis; v3 substrate retest in flight.* Not yet a published paper.

- **Epistemic Generation as Mechanization Placement.** Working paper
  at `papers/epistemic-generation/draft.md`. Operationalizes Gowers's
  theory-builder / problem-solver distinction inside an operated
  research corpus: a TB vocabulary covers TB arcs at 58.1% and PS arcs
  at 20.7%; a PS vocabulary covers PS arcs at 65.9% and TB arcs at
  19.1%; a same-culture random split produces only a 3.0 pp gap, so
  the split is real *inside this operated corpus* but not an objective
  taxonomy of all mathematical research. A subsequent eight-subfield
  re-mining produces a layered structural language (six shared-core,
  eight broadly shared, four peripheral operations) with partial
  out-of-distribution transfer (57.9% on a business held-out set,
  75.2% on four sparse 2026 specialist papers, but 12.5% on a
  post-cutoff PDE stress test under adversarial scoring).

  *Agent-facing primitive screens — honest negatives.* Passive
  primitive prose is inert as an agent prompt under the tested
  designs: catalogue dumps, single-primitive prompts, route-then-solve
  prompts, and pairwise route-answer probes do not improve
  Humanity's-Last-Exam exact-answer performance, native route choice,
  external operator transfer, or downstream execution. Placebo-
  structured routing absorbs much of the apparent benefit; generic
  "pause and structure" effects cannot be counted as primitive
  effects.

  *Surviving positives — three replicated findings, narrowly framed.*
  (a) **Compact operator-card scaffolding on hard external source
  packets.** Under no-hidden-gold pairwise judging, compact primitive
  operator cards beat no-card free-text artifacts ~23-4 across 27
  paired comparisons on hard external source packets, and beat
  shuffled-semantics placebo cards ~17-9. (b) **Typed
  evidence-carrier contracts as an artifact-transfer mechanism.** On
  an artifact-only consumer task (consumer sees only the producer's
  artifact, never the original source facts), typed evidence-contract
  artifacts reach 24/24 audit-intent recovery on a fresh external
  corpus, versus 20/24 for generic-careful artifacts and 17/24 for
  matched placebo contracts; the result survives a cross-model
  rejudge under a different model family (typed > generic 12-4,
  typed > placebo 13-2-1). The earlier preference signal was 16-0
  vs. original drafts, generic revision, and placebo each on a
  same-family text judge. (c) **Mechanism narrowing — the active
  carrier is source-bound action-constraint content, not typed-field
  names and not primitive labels.** On a controlled mechanism probe,
  artifact-only consumer payment goes 71% (source-only) → 86%
  (schema slot-names only) → 100% (delabeled constraint values) →
  100% (full typed fields). Typed schemas are useful placement /
  scaffold; they are not independently validated as causal primitives
  in this setting.

  *Operational implication.* The strongest current claim is *not*
  that primitives improve agent answers in general — that framing is
  too blunt. It is the narrower placement claim: primitive language
  becomes an executable research operator when (1) the correct
  operator is supplied (wrong operators *actively misroute* the
  evidence path), and (2) the operator is rendered as a
  source-bound, action-constraint-carrying contract rather than as
  passive prose. Recognition / routing is the bottleneck — direct
  primitive-label classifiers and full-menu disambiguators do not
  reliably route; evidence-matrix ranking + top-2 pairwise contrast
  helps but is not sufficient.

  *Catalogue-status update (2026-05-23).* Subsequent semantic
  reliability tests show that the fine primitive catalogue should not
  be read as a strict mutually exclusive taxonomy. On the 118-move
  corpus, fine op identity has moderate agreement (Cohen kappa 0.578);
  the full/partial/none level axis is weak (kappa 0.121); and the
  top-1/top-2 gap mostly measures diffuse catalogue fuzziness rather
  than a solved routing capability. Merging the two largest confusion
  pairs (`core_02/core_03`, `cand_g/core_01`) improves kappa only to
  0.640, while broader automatic merging over-collapses the language.
  The more reliable machine-facing layer is the four obligation
  classes: `construct`, `transfer`, `bound`, and `decompose` (plus
  rare `other`), which lift agreement to kappa 0.741 on the same
  corpus. Operationally, route and receipt-check at that coarse
  obligation layer, allow multi-label cases, and treat fine primitives
  as human retrieval handles, checklist prompts, and nearest-confuser
  guards.

  *Patterns and anti-patterns are a separate surface.* The pattern
  catalogue is not the same object as the primitive catalogue: patterns
  choose a research-control policy, anti-patterns name failure guards,
  and the orchestration menu routes situations to a policy chain. The
  current pattern audit finds 31 distinct pattern entries, but many were
  unused or lacked quantified tests before later wiring repairs. A
  separate routing audit over five coarse problem classes reached kappa
  0.846, while the first receipt-transfer test for RD patterns failed
  and was later judged under-designed. The conservative claim is that
  coarse routing and explicit action contracts are promising operating
  surfaces; fine pattern and anti-pattern labels should co-fire as
  guards and evidence slots, not be treated as exclusive classes.

  *Methodological note (strange-loop).* The receipt-deployment-form
  question — does rendering an RD pattern as a receipt-style contract
  outperform a label — produced four consecutive *failed measurements*
  on synthetic corpora, every one biased against receipts for a
  design/measurement reason (judge-preference for free prose,
  action-text undercounting of receipt arms, fictional-substrate
  flooring). The assisting agent erred three times on this question
  while itself lacking a receipt-style discipline (pre-commit confound
  check, falsifier-of-own-claim check). That is weak evidence *for*
  structured discipline and a warning to apply it to the apparatus's
  own conclusions; the receipt-form question itself is *unresolved
  and deferred to a live A/B*, not refuted.

  *Reasoning-compiler update (2026-05-24).* Subsequent H31-H55
  experiments narrow the agent-facing result further. The useful unit is an
  executable contract field that binds source facts to an action:
  residual/evidence carrier, nearest confuser, action program, deterministic
  gate, and later outcome trace. A primitive, pattern, anti-pattern, or menu
  label does not carry the claim by itself. Free-form compilation is unsafe;
  checked typed lowering and invariant gates are required. Wrong contracts
  actively misroute action. Boundary-card and PDE/RD tests show the same
  discipline: validate the typed work unit or repair trace, not prose that
  merely says the work was done. Production uplift remains
  unproven because existing production-like traces had zero complete
  orchestration-shadow rows. Public summary:
  [`public/CLAIM_SUMMARY.md`](../public/CLAIM_SUMMARY.md).

  *Retest tag: mixed.* The TB/PS split, structural language, and
  partial OOD transfer are original-run only inside the operated
  corpus. The agent-facing-primitive *negatives* are honest negatives
  with cross-design replication. The compact-card and typed-contract
  *positives* are cross-design and (for typed contracts) cross-model
  preserved; they have *not* yet been shown under cross-family human
  consumers, and the typed-vs-generic margin is statistically
  underpowered at current N. The paper's overall claim remains a
  placement theory, not a solver-uplift or universal-cognition
  claim.

## Evaluation-Design Case Studies

**Public claim.** The restored case studies provide three small reproducible
examples of evaluation checks passing while missing their intended question:
bootstrap-under-noise can miss rank deficiency, a holdout grid can fail to
discriminate structural class, and evidence enrichment can outrun the
discriminator it was meant to strengthen.

**Status.** Public reproducible methodology cases.

**Retest tag.** *Methodology / framework claim.* Each case ships a small
reproducer script; the case is the demonstration, not a generalization
claim.

**Evidence pointers.** [case-study index](../papers/case_studies/README.md);
[rank-deficient bootstrap note](../papers/case_studies/rank_deficient_bootstrap.md);
[rank-deficient reproducer](../papers/case_studies/rank_deficient_reproducer.py);
[evidence-grid underdetermination note](../papers/case_studies/evidence_grid_underdetermination.md);
[evidence-grid reproducer](../papers/case_studies/evidence_grid_underdetermination_reproducer.py);
[evidence-enrichment saturation note](../papers/case_studies/evidence_enrichment_saturation.md);
[evidence-enrichment reproducer](../papers/case_studies/evidence_enrichment_saturation_reproducer.py);
[docs summary](concepts/evaluation_failure_cases.md).

**Non-claims.** Does not claim these are exhaustive failure modes. Does not
claim all holdouts, bootstraps, or enrichment steps are bad. The claim is about
form-vs-intent mismatch in evaluation design.

**Next falsifier or source-design step.** Add only small, runnable cases where
the old check, the miss, and the better check can be demonstrated in under a
minute.

**Readiness.** Public and reusable.

## Cross-Substrate Methodology

**Public claim.** Across the campaigns, the strongest integrative claim
is methodological: the same operating discipline surfaced bounded positives,
clean negatives, and self-demotions across structurally different substrates.

The discipline includes pre-registration, falsification probes, gauge audits,
multi-model cold-shot diversity, corpus-gradient suppression, source-readiness
checks, explicit non-claims, and documented self-demotion.

**Status.** Methodology claim, not a domain-solution claim.

**Retest tag.** *Methodology / framework claim.* The discipline has held
across NS, consciousness, gravity, neural, and experimental-math substrates.
What has *not* yet been done is a re-run of the *current* meta-architecture
against a non-NS substrate where the same self-demotion, catch, forecast,
and source-readiness discipline must hold end-to-end under one apparatus
version. That re-validation is on the roadmap and is named.

**Evidence pointers.** [multi-substrate validation](multi_substrate_validation.md);
[70-day journey](sprint_70day_journey.md); [priority roadmap](../priority_roadmap.md);
[experiment track record](../research_areas/EXPERIMENT_TRACK_RECORD.md);
[insights ledger](../research_areas/insights_ledger.md);
[evaluation failure cases](concepts/evaluation_failure_cases.md).

**Non-claims.** Does not prove the current NS-era meta-architecture has already
been revalidated across all non-NS substrates. Does not prove the apparatus
replaces domain experts. Does not prove that a second principal or different
apparatus stack would reproduce the same outputs.

**Next falsifier or source-design step.** Re-run the current
meta-architecture on at least one non-NS substrate and require the same
self-demotion, catch, forecast, and source-readiness discipline to hold.

**Readiness.** Public as a thesis with explicit single-operator and
single-apparatus limitations.

## [GP-245](../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md) Forecast Calibration Program (LLM Forecasting Channels + Operationalization)

**Public claim.** The GP-245 program (a forecaster-skill / multi-channel calibration subsystem of the ZTARE repo) measured 104 documented findings (F1–F104, with F31 reserved) on subscription-class LLM forecasting across a 5-family panel (claude-opus-4.7, codex-gpt-5.5, codex-gpt-5.4-mini, deepseek-chat, gemini-2.5-flash) over apparatus-internal and external ForecastBench corpora. The strongest empirical contributions:

1. **Tail-insurance-premium as a verbalized second-moment channel that predicts per-row Brier** (F8 ρ=+0.36 on v4 N=100; F10 ρ=+0.41 on existing pool n=590; F20 cross-corpus on v10 with |ρ|=0.47; F32 fourth replication on v16 gp225 corpus with pooled ρ=+0.32 and **all three agents same-sign for the first time**). The verbal-confidence comparison (F20) scoped down by F32 to corpus-and-agent-dependent rather than universal: which channel is strongest readout depends on agent family and corpus character, while the per-family vconf sign-flip on `codex_55` reproduces. Specific instrument distinct from Tian-style generic verbal confidence.

2. **LLM herding under explicit exposure is robust to behavioral remediation** (F15 N=239 triples, ~74% herding rate, ~7% shift on a 0–1 scale, 6/6 directional pairs same sign; F33 N=240 confirms slope(shift|prior_gap) = +0.745 under skeptical-framing instruction vs +0.754 baseline, statistically indistinguishable). The non-independence Schoenegger 2024 flagged is measured, *and* the cheapest light-touch remediation (instruct the receiver to be skeptical) fails cleanly. Together with F19/F22 (rationale-exchange null), this establishes that on the protocols tested, independence must be enforced architecturally by a sealed pool — no behavioral patch substitutes for it.

3. **Premium-as-abstention rescues a failed threshold-shift wiring** (F25 negative → F28 +22 utility lift on symmetric-loss regime). Same signal, different wiring → opposite operational outcome.

4. **Closed-loop super-judge re-decision on worried cases improves Brier** (F30 N=44, judge Brier 0.21 vs original 0.35, Δ=−0.14; +11 utility lift on asymmetric-favor-yes vs abstention). Pure-LLM autonomy without humans-in-the-loop, on cases the original agent flagged worried.

5. **Failure-mode atlas surface** documented in the [GP-245](../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md) research log and current forecasting paper draft: F12 (LLMs predict Lean-proof completability worse than constant baseline), F19/F22 (rationale-only transfer null on single-shot binary forecasting; adversarial framing rescues worst-case anchoring only), F24 (meta-classifier OOD failure remediated), with F23 reconciliation distinguishing where debate-style mechanisms work (code/seam) vs fail (binary forecasting).

**Status.** Methodology + empirical-instrument claims, mostly apparatus-internal-verdict-only. Code/data at `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/` and sibling directories; reproducible scorer at `scripts/public/control/forecast/pool.py` (extended with F8/F10 second-moment-Spearman per F9 v2 landed this session). Full per-finding strength + retest-tag table in `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/research_log.md`.

**Retest tags.** Per F-finding (subset):
- F3 (codex-CLI hang root cause + fix): *Methodology / framework claim* (one-line, empirically verified)
- F8 (tail-premium predicts Brier): *Cross-mutator replicated* (claude + 2 codex variants same sign across v3 + v4); *apparatus-internal verdict only* on the specific instrument
- F10 (decomposed channels predict Brier on pool): *Enlarged-data confirmed* (n=590, different corpus from F8)
- F15 (herding magnitude): *Original-run only (n=239 triples)*; phenomenon documented in arXiv:2505.21588 but specific binary-forecast measurement is ours
- F17 (per-agent heterogeneous memory-injection rescue): *Original-run only*; behavioral finding likely novel
- F18+F24 (meta-classifier + OOD remediation): *Methodology / framework claim* with documented OOD failure mode
- F20 (tail-premium vs verbal-confidence comparison): *Cross-corpus replication on apparatus*; scoped by F32 to corpus-and-agent-dependent ordering, per-agent codex_55 sign-flip reproduces
- F28 (premium-as-abstention rescue): *Original-run only*; operationalization-specific
- F30 (closed-loop judge): *Original-run only*; pure-LLM autonomy with regime-dependent utility
- F32 (tail-premium fourth replication; first all-agent-same-sign; scopes F20 channel-ordering): *Original-run-only on apparatus-internal gp225 corpus*; N=30 per agent, Spearman SE≈±0.18
- F33 (skeptical-framing does not reduce herding): *Original-run-only on apparatus-external + apparatus-internal NS contracts*; clean Δ-vs-v5-baseline null, 6/6 pairs slope +0.65 to +0.86, vindicates architectural-only fix for ensemble independence
- F35 (signed directional tail beats unsigned magnitude; magnitude on top is noise): *Original-run-only on v21 cross-domain corpus N=270*; C2 split (downside_worry + upside_surprise) Brier=0.1917 beats C1 magnitude-only 0.2017 and C3 combined 0.1998; per-agent picture disagrees (claude favors C3, codex_5.5 favors C1, codex_5.4-mini favors C2) — corpus-level finding does not dictate per-agent channel composition
- F36 (per-agent inverted-vs-direction-correct premium-correctness coupling): *Original-run-only on v21 N=270, 164 premium-rowed calls*; claude has inverted gap (+10, pays more when right) vs codex variants direction-correct (5.5 gap −4, 5.4-mini gap −19); aggregate signal direction depends on per-agent sample-size balance — implies F8/F10/F20/F32 population correlation is the average of opposite within-family signals. Operational consequence shipped: forecast pool now records `agent_family` on every emission; per-agent sign rules in `org/calibration/per_agent_premium_sign.yaml` so downstream consumers do not bake the rule into emitter code.
- F37 (signed-tail elicitation cancels claude's per-agent premium-tone confound; tone-vs-content mechanism unified): *Original-run-only on v22b N=90, 85 parsed*; F36's per-agent sign-flip replicates under inverted question framing (claude +5 inverted, codex_55 −5 / codex_54mini −17 direction-correct), AND signed-split elicitation flips claude's sign to direction-correct (−5) AND lowers claude/mini Brier by ~0.05/~0.05. Mechanism: magnitude measures epistemic tone for tone-tuned models; signed-split forces contract-specific commitment. Implies the F8/F10/F20/F32 lineage's "premium predicts Brier" was a tone-vs-content confound, not a clean second-moment signal — signed-split is the cleaner channel.
- F95 (gemini retest at N=42 public-domain disambiguates corpus-vs-prompt for the F42 "inversion" claim): *Original-run only*; ρ(worry, Brier) = +0.110 on the v21-style C1 worry-only prompt, gemini-2.5-flash via API; at N=42 the Fisher-z detectable |ρ| at 80% power is ≥0.43, so the CI excludes the original "inverted" direction (ρ<−0.30) — *h0_kept* against the inversion. The deployed YAML sign-rule retraction for gemini stands; positive-direction signal at this N is *inconclusive_underpowered*.
- F96 (v28a refill on +100 public-domain contracts; partial success due to codex subscription parse-failure mode): *Original-run only on the schema-OK subset*; claude / gemini / deepseek returned 100/100 schema-OK each, extending public-domain N from 42 → 142 for those three families. codex_55 / codex_mini returned 0/100 schema-OK each because of a `default_codex_model` kwarg bug in the dispatcher (now fixed and re-firing). The codex-subscription schema-fail pattern was previously documented under v28-stake; this is its second occurrence and the root cause is the same kwarg-vs-environment confusion in `run_subscription_agent_with_recovery`, not model behavior.
- F97 (deployable composed-routing recipe at N=142 beats naive ensembles but does not beat best-single at p<0.05): *Original-run only / methodology claim*; routed_v1 = mean-of-5 panel forecast + four universal shrinkage rules (confident-NO discount, NO-bias upward shift on the middle band, horizon-to-cutoff shrinkage, source-difficulty shrinkage) achieves pooled Brier 0.2416 on N=142 vs median-of-5 0.2937 (paired-permutation p=0.0003) vs mean-of-5 0.2701 (p=0.017) vs best-single (Claude on this corpus) 0.2543 (Δ=−0.0127, p=0.48). routed_v2 = routed_v1 + per-family channel weighting from the bid-ask + worry + b_mid + b_width channels adds nothing on top of routed_v1 at N=142 (Δ=+0.0140 vs routed_v1, p=0.069), consistent with F61's LOO result that only one of five families has a generalizable multi-channel decomposition. Halawi-class headline (routed recipe beats best-single at p<0.05) is NOT yet licensed at this N; the codex schema-fail in F96 is the most actionable next move — when codex lands at N=142, the best-single anchor shifts and the comparison repaints.
- F99 (composed routing at N=142 with full codex coverage — F97 superseded): *Original-run only*; codex re-fire landed 500/500 schema-OK after kwarg fix. routed_v1 holds Brier 0.2320; routed_v1 vs best-single Δ=−0.0223 (was −0.0127 at F97), p=0.18 (was 0.48). routed_v1 vs median-of-5 Δ=−0.040 at p=0.0013, vs mean-of-5 Δ=−0.029 at p=0.0069 — routed-beats-aggregation hardens to p<0.01. routed_v1 also beats routed_v2 at p=0.04 (universal rules > per-channel rules). Verdict: deployable headline against aggregation baselines; *inconclusive_underpowered* against best-single at the program's Δ≥0.05 detection bar.
- F100 (confident-NO discount as a STANDALONE per-family rule beats raw at p<0.05 on every panel member): *Original-run only / deployment claim*; on N=142 the rule `if p_raw<0.10: p = p_raw + (0.65 - p_raw) * 0.5` improves per-family Brier for claude (Δ=−0.030, p=0.016), codex_55 (Δ=−0.021, p=0.030), codex_mini (Δ=−0.026, p=0.015), deepseek (Δ=−0.052, **p=0.0008**), gemini (Δ=−0.033, p=0.008). Discounted-claude (Brier 0.2240) is at parity-or-better than the four-rule routed_v1 (0.2320). Deployed as the `confident_no_discount` post-forecast adjustment in `org/calibration/per_agent_prompt_policy.yaml`. Cross-corpus replication on a non-public-domain pool remains the next falsifier.
- F101 (Halawi 2024 dataset structurally contaminated for the 2025+ LLM generation): *Original analytic*; the released forecasting dataset (`YuehHanChen/forecasting`, N=1754 binary-resolved across Polymarket / Metaculus / Manifold / GJOpen / CSET) has resolve-year histogram 2021:1 / 2022:147 / 2023:1470 / 2024:136 / 2025+:**0**. Every current panel member's knowledge cutoff postdates every resolution. Any 2025-generation replication using this corpus measures memorization, not skill. A 30-call probe returned raw Brier 0.13 with perfect bin-calibration at p<0.10 (empirical YES rate = 0.07 = exactly what claude said) — the memorization signature. The deployable check before any cross-corpus replication is one filter: `resolve_date > max(panel_cutoff)`. That filter empties this dataset for the current generation. Written into the working paper §"Implications".
- F102 (novel-bias smokes split — LLMs ESCAPE loss-frame asymmetry but INHERIT status-quo / endowment bias; probability weighting near-linear): *Original-run only / preliminary*; 5-family × n=30 paired same-contract two-framing smokes on v28a public-domain pool. (A) Loss-frame invariance |p_success − (1 − p_failure)|: mean gap 0.035 (claude) to 0.148 (gemini) — all below human reference range 0.15–0.30; LLMs symmetric on loss-framing. (F) Status-quo / endowment |p_currently − p_fresh|: 0.084 (gemini) to **0.440 (codex_55, median 0.500 — half flip sign)**; large effects on framing-grounded prompts; LLMs reproduce the human bias. (B) Probability weighting (8 anchors): claude near-linear; full panel curve fit pending. The split is informative: framings grounded in UTILITY (loss as disutility) don't transfer; framings grounded in TEXT (current state) do. Cross-corpus n=42 firing on diversified corpus_v26 (Metaculus + FRED) at the moment of writing.
- F103 (Lane B canonical L1+L2+L3 audit of 8 published AlphaProof Nexus AICollaborator bare-Mathlib proofs, after 4 corrected rounds): *Original-run; methodology claim plus per-target verdicts*; with the helper-vs-top-level distinction enforced (audit code consolidated 2026-05-29), forced sidecar enabled at v4.27 for non-drift compile_failed, and process-group kill discipline on lake subprocesses (orphan-lake leak fix 2026-05-29), the corrected verdict over the 8 top-level published theorems is: **8/8 compile kernel-clean at the pinned v4.27 toolchain** (L1: no `sorry`/`admit`; L2: only allowlisted kernel axioms {propext, Classical.choice, Quot.sound}), and **all 8 are top-level L3-clean** — no headline theorem is a vacuous restatement of a library lemma. The two substantive caveats are **(a) toolchain-pinning** — 5/8 fail native v4.30 compile (P5's native run hit a harness `audit_invocation_failed`, an infra bug, not a falsification) — and **(b) library-composition**: the proofs assemble existing Mathlib lemmas, i.e. limited novel-math content (normal for formalization). 7/8 also carry **helper-level** `gold_name_verbatim` flags (P1 excepted), but these are **advisory**: a helper lemma citing a Mathlib lemma by name is normal library use and near-vacuous as a quality signal when auditing a finished foreign proof. Two earlier framings are both **retracted**: the "laundering caught / 7–8 of 8 clean closures" framing (an auditor Bug-4 conflated helper-blocker passes into "clean") overstated quality, and the interim "1 unqualified-clean + 7 carry blockers" framing overstated a defect by giving helper-level L3 weight it does not carry. We do **NOT** claim DeepMind published anything fake. We do claim the strict L1+L2 stack at the pinned toolchain — with L3 top-level as the only discriminating laundering signal and L3 helper-level demoted to advisory — is the publishable audit discipline; per-target receipts live in `analytics/public/queries/lane_b_apn_audit_receipts.json` and the consolidated table in `analytics/public/queries/lane_b_apn_audit_summary.md`.
- F104 (Frequency-Inheritance Hypothesis with 3-axis ESCAPE / INHERIT / MIMIC taxonomy, pre-registered ≥8/10 cell-classification bar): *Original-run; inductive theory plus pre-registered confirmatory smoke*; inducted from F100-F102 that LLM bias inheritance partitions by elicitation surface × bias-mechanism class × alignment overlay. Pre-classified 10 biases into the 3 cells; claude-subscription confirmatory at n=15 per arm. **Result: 8 of 10 cells classified correctly** at the pre-registered bar (random-cell baseline 3.3/10). Confirmed: A/B/G ESCAPE; C/E/H/J INHERIT; F MIMIC. Two informative misses both predicted MIMIC: D sunk-cost (gap 0.021) and I in-group (gap 0.017), both fully suppressed on subscription-RLHF claude — consistent with alignment damping stronger than the frame anticipated and refining MIMIC predicate to "systemic motivational + heavy case-study representation + survives alignment damping." Cross-panel n=15 D-and-I over codex/deepseek/gemini fired 2026-05-29 to distinguish "alignment damping" from "framework wrong"; result pending. Receipts: `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/freq_inheritance_smoke_n15_calls.jsonl` + `freq_inheritance_DI_panel_smoke_n15_calls.jsonl`.

**Evidence pointers.** [research log with all F-findings through F104](../projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/research_log.md); [findings completeness ledger](../projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/findings_completeness_ledger.md); [yield-formula calibration analytic](../projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/yield_formula_calibration_analytic.md); [LLM forecast calibration paper draft](../papers/llm-forecast-calibration-cross-corpus/draft.md); [GP-245 project methodology](../projects/llm_forecasting_calibration_program/public/METHODOLOGY.md); [GP-245 seam](../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md).

**Non-claims.** Does NOT claim LLMs cannot forecast in general (positive findings outnumber negatives in the same program). Does NOT claim three independent model families (trio is 1 claude + 2 codex variants — codex errors are correlated; strongest external claim is "consistent across this trio"). Does NOT claim reproducibility-grade methodology (internal-audit-grade with documented external-extension path; zero second-lab submissions to date). Does NOT solve corpus contamination, author-level GT-selection leakage, or estimate API token cost. Does NOT claim novel mechanisms — most are extensions or scoped replications of mechanisms in arXiv:2603.25052 (multi-channel readout), arXiv:2604.01457 (overconfidence circuits), arXiv:2509.25532 (suggestibility), arXiv:2505.21588 (multi-agent herd behavior), Schoenegger 2024 (independent-aggregation ensembles), and Tian 2023 (verbalized confidence). Novelty is in **specific instruments and operationalizations** (F8 tail-premium token, F17 per-agent heterogeneity, F20 channel comparison, F28 abstention-vs-threshold wiring, F30 closed-loop judge), not new mechanisms.

**Next falsifier or source-design step.**
- F8/F10/F20 cross-family replication (Gemini / open-weights / reasoning-class) on contamination-clean external corpus.
- F28/F30 replication under non-synthetic cost structures (operator-measured costs, not assumed regimes).
- F12 natural-distribution Lean replication (v7.2 pilot built but not yet completed; current stratified-corpus result could collapse).
- Independent second-lab submission to [GP-245](../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md)-CalBench (zero submissions to date; testbed claim depends on this).

**Readiness.** Public as a multi-finding portfolio with explicit strength + retest tags per F-ID. Methodology findings (F3, F4, F9) are high-strength; empirical findings (F8, F10, F15, F17, F20, F28, F30, F32, F33) are apparatus-internal-grade with documented external-extension path. Earlier standalone draft paths were retired; the live public surfaces are the GP-245 project docs and the LLM forecast calibration paper draft. Per-project public surface: [`projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md`](../projects/llm_forecasting_calibration_program/public/CLAIM_SUMMARY.md).
