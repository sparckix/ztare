---
description: "Disposition and replay status for the 2026-07-17 Fable review of LeanMill and AxiomPack."
---

# Fable LeanMill + AxiomPack Review Disposition

Updated: 2026-07-19

## Claim boundary

This document records which review findings have executable repairs, which
have only fixture evidence, and which remain open. It is not a release tag or
a mathematical novelty certificate. Files remain in a dirty working tree;
deployment identity is pending until the principal chooses a commit boundary.

The source review is `claude_leanmill_axiompack_review/`. An independent
read-only replay classified the twenty work orders after the current repairs.

## Disposition

| ID | Review work order | Status | Current evidence | Required next action |
|---:|---|---|---|---|
| 1 | One axiom-audit chokepoint | fixed | Consequence reconsideration and formal-task admission require positive axiom evidence; omission probes fail closed | Preserve in broad release suite |
| 2 | Withhold ratification after governance crash | fixed | The outer boundary reruns governance on the exact carried artifact, requires explicit availability from every authority receipt, replaces root validation with the completed 14-authority state, and maps any finalizer fault to typed unavailability | Preserve in broad release suite |
| 3 | Repair two live loop breakers | fixed | Receipted reject-all and `prediction_formula_id` regressions pass | None beyond release replay |
| 4 | Tracked deployment identity for `first_order_baseline.py` | deployment-declared; commit pending | The module and the full current AxiomPack runtime delta are in the VPS sync identity; the updater now rejects changed runtime files omitted from that identity | Include the untracked module at the selected commit boundary and test from a clean checkout |
| 5 | Remove `FalseRender` pollution | fixed | Live stores are clean; injected-solver writes are guarded | Keep dated backup excluded from consumers |
| 6 | Disposition supersession | fixed | Reopen replay removes only the superseded same-lineage stop from the active projection | Exercise once in a forward campaign |
| 7 | Self-play through the certificate chokepoint | code fixed, experiment blocked | Strict governed-closure validation exists and the canonical corpus is now strict; the frozen E1 scale gate failed before self-play | Grow a new strict corpus through normal governed closures; do not restore legacy rows |
| 8 | Nontriviality check | fixed | Elaboration, cheap-tactic compilation, and nondegenerate-instance probing fail closed | Preserve matched negative controls |
| 9 | Family holdout | fixed | The terminal strict split contains 127 training proofs and 62 evaluation proofs; its content-bound receipt reports zero shared definitions and zero cross-split near duplicates | Preserve the split and leakage receipt in the release candidate |
| 10 | Disable expensive routes in direct fallback | fixed | Both route flags are scoped off and restored | None beyond release replay |
| 11 | Blind 197-seed self-play and starvation remeasurement | blocked before run | Finalization produced 189 distinct strict proof pairs (127 train, 62 eval); the frozen 197-row gate blocked E1 with zero provider calls | Accumulate at least eight new governed, deduplicated proof rows, then re-evaluate the frozen gate |
| 12 | One closure finalizer | fixed in working tree | Root producers converge on `solver/closed_artifact.py`; combined regression suite passed | Include new module at commit boundary; retain attempt/toolchain identity work under item 15 |
| 13 | End-to-end timing | fixed | Campaign launch stamps ownership; consumers compute launch-to-close wall time | Confirm once on a forward closure |
| 14 | Corpus provenance and dependency repair | fixed | The exact frozen 197-row corpus replay admitted 187 and quarantined 10 under the completed policy; two independently launched successor rows also closed, all with zero provider calls. The final strict corpus contains 189 proof pairs after deduplication | Grow only through new governed closures; do not backfill E1 with quarantined rows |
| 15 | Receipt identity | fixed for new closures | The terminal process-level replay binds launch input, worker source, job/source/run, full target signatures, toolchain, closure/parity pairing, and the 14-authority roster. Repeated finalization reproduced the same receipts | Preserve the terminal self-check and external-worker identity receipts |
| 16 | Deletion and decomposition | partial | The disconnected `void_self_play.py` and duplicate `src/src/` files are deleted after consumer checks. Documented or experimental consumers still own the other questioned modules; the two monolith decompositions remain deferred | Migrate those consumers before deletion; extract only at state/authority boundaries |
| 17 | Fixed-size SMT screening | fixed | A production size-5 screen ran four exact queries, replayed all three countermodels, preserved one bounded UNSAT, and assigned no theorem credit | Preserve the receipt and its independent replay in release evidence |
| 18 | Live pack-promotion transition | fixed and first-fired | A de-anchored model-authored pack passed candidate birth, exact semantic screen, shadow A/B, conditional lowering, signature validation, and independent replay | Keep the earlier anchored rehearsal invalidated; use the promoted pack only within its recorded theorem-campaign scope |
| 19 | Checked interpretation seam | fixed as controlled first fire | Typed operation images, total maps, finite attack, noncollapse, and Lean obligations pass on the opposite-semigroup control | Next credit requires independently authored source and target theories |
| 20 | E4/E1 and morphism discovery | partial | A de-anchored E4 first fire completed with independent theory authors, a checked interpretation, compute-matched two-row cohorts, and strict carried-proof ratification; both arms scored 0 strict hits | Repeat E4 on broader structure-bearing interpretations; keep E1 behind the strict-corpus gate |

## Item 18 forward evidence

The valid first fire is
`outputs/axiom_pack_live_promotion_first_fire_deanchored_20260718/`.
The earlier rehearsal is explicitly marked as prompt-contaminated and earns no
credit.

The de-anchored proposer independently authored

\[
\forall x\,y,\qquad (xy)x=xy.
\]

The nine-task shadow comparison solved zero tasks in the baseline arm and one
in the treatment arm, with one attributable improvement and zero regressions.
The baseline has an exact finite countermodel; the treatment proof compiles in
Lean; full/empty/leave-one-out ablation makes the new axiom indispensable; and
the conditional-lowering and ratification signatures verify. The independent
replay reports all eighteen checks true.

Primary machine-readable records:

- `outputs/axiom_pack_live_promotion_first_fire_deanchored_20260718/first_fire_summary.json`
- `outputs/axiom_pack_live_promotion_first_fire_deanchored_20260718/independent_replay.json`
- `outputs/axiom_pack_live_promotion_first_fire_deanchored_20260718/noncalibration_promotion/axiom_pack_promotion_transition.e2748ddee72a0f7e.json`

This establishes the candidate-law lifecycle. The selected law is familiar
algebra and carries no priority claim.

## Item 17 production screen

The provider-free fixed-size run is
`outputs/axiompack_release_fixed_size_screen_20260718/`. It scheduled four
uniform carrier-size-five queries. Three returned SAT with concrete models;
all three models were replayed against the base axioms, selected premises, and
negated target. One query returned UNSAT at size five. No query returned
UNKNOWN, and the aggregate explicitly sets `proof_credit_eligible=false` and
`theorem_campaign_admissible=false`. The result therefore records bounded
finite evidence only.

Primary machine-readable records:

- `outputs/axiompack_release_fixed_size_screen_20260718/receipt.json`
- `outputs/axiompack_release_fixed_size_screen_20260718/summary.json`

## Item 20 E4 first fire

The E4 run is
`outputs/axiompack_e4_deanchored_first_fire_20260718/`. Two independent model
authors produced the source involution

\[
u(u(x))=x
\]

and the target laws

\[
n(n(x))=x,\qquad b(n(x),n(y))=b(x,y).
\]

A third agent proposed the signature interpretation

\[
A\mapsto U,\qquad u(x)\mapsto n(n(x)).
\]

It is syntactically nonidentity and nonconstant on the checked target model,
and it passed totality, typing, exhaustive carrier-size-at-most-two
preservation, noncollapse, and governed Lean obligations. It is nevertheless a
weak feasibility witness: the target involution law reduces its operation image
to the identity. It does not establish faithful, full, or useful transport.

The transported and de-novo arms each received one model call, two proposals,
equal prompt bytes, the same model and effort, identical finite gates, and the
same Lean adjudication path. One of two transported proposals and both de-novo
proposals reached target adjudication. All three proofs used a strict subset of
the frozen target premises, so the preregistered `proved_attributed` hit count
was zero in both arms. The observed resolution rates were 1/2 transported and
2/2 control. This moves item 20 from open to partial as an executable E4
feasibility result; it supplies no transport advantage, novelty, priority, or
training evidence, and E1 remains unrun.

The first attempt also caught a data-boundary mismatch: the prompt requested a
compact three-field operation image while the parser required a schema tag.
The experiment-local adapter now canonicalizes that exact compact form. Four
carried proofs were then replayed provider-free through the ratification-only
door. Each content-addressed certificate binds its goal hash to the
source-aware matched-control target-signature hash.

Primary machine-readable records:

- `outputs/axiompack_e4_deanchored_first_fire_20260718/preregistration.json`
- `outputs/axiompack_e4_deanchored_first_fire_20260718/result.json`
- `outputs/axiompack_e4_deanchored_first_fire_20260718/item20_disposition.json`
- `outputs/axiompack_e4_deanchored_first_fire_20260718/replay_receipt.json`
- `outputs/axiompack_e4_deanchored_first_fire_20260718/verify_e4.py`

## Items 9, 14, and 15 terminal replay

The current-policy replay is
`outputs/axiompack_item14_final_policy_replay_20260719/`. Its launch contract
freezes 197 input rows at SHA-256
`02b326574aa6c91a95cf97313c18b970193ce00d3d65e43d56250d91819f9671`.
The provider-free replay admitted 187 rows and quarantined 10: four failed
compilation, three used banned axioms, and three failed governance. Two
process-isolated successor rows then closed under the same policy. Final
deduplication selected 189 strict proof pairs.

The family holdout contains 127 training proofs and 62 evaluation proofs. Its
receipt reports zero shared definitions and zero cross-split near duplicates.
E1 did not start because the frozen scale gate requires 197 strict proof pairs;
the blocker was minted before any provider call. Quarantined rows were not
relabeled to reach the threshold.

The terminal audit preserved five superseded failures before the accepted
process-level route:

1. a freeze-time empty-directory fact was incorrectly reused as a later fact;
2. `failed_compile` was omitted from the final authority outcome algebra;
3. a predecessor launch was accepted after its finalizer bytes were replaced;
4. the nested ratifier acquired duplicate bootstrap ownership;
5. the parent finalizer remained `__main__`, so its execution identity differed
   from the frozen harness identity.

The accepted route launches `external_holdout_ratifier.py` as a separate
worker, binds its source digest, and reproduces the same terminal receipts on
repeated finalization. Principal receipts are:

- replay summary: `2d90aab1950b04495632d8759b04b314a77e0ec0252947864cc98b350bd0815b`;
- final validation: `e93d9be3c05a773b5281e88ec34cdf535c2baf9562b2a60c40eacb8c08a98ff9`;
- terminal finalizer supersession: `fcee2ec1fe402127732d574ec5b55466f58b5dc6293091d7ee0a5ac3eac61f56`;
- terminal self-check: `2865f964a1cbc5933504a3108bed108dc554eb4f30f76e20d8845058a5ad22cb`;
- E1 blocker: `04f9659baa37b31b2be29eef12adf628e50eb295e68675714286e5d375f15f06`.

## Finite verifier boundary

The authority surface is finite and domain-neutral. Lean checks the
elaborated proof against the frozen environment; the common ratification path
binds target identity, source, axiom provenance, matched controls, and content
hashes. A registered theory adapter may lower domain semantics and produce a
candidate certificate. It cannot set the governance verdict, alter the axiom
policy, or award closure credit.

The policy module freezes three nested sets in code: six executable
anti-laundering organs, eleven target-governance authorities, and fourteen
final-ratification authorities. Their final roster digest is
`dfe23b3412b575d0868979eed73087257baee696fab06cf07fce18bf6f2bdd82`.
Required-organ errors, deep-probe timeouts, canonical re-elaboration faults,
diagnostic disablement, Cage fallback failure, and unresolved target selectors
all return typed governance unavailability. Solver, falsifier, and
closed-artifact consumers require the common completed-state predicate;
unavailability preserves the candidate for retry and cannot become closure or
falsification credit. Every target-aware organ uses the same qualified theorem
identity: signature checks see its signature, proof checks see its declaration,
contextual checks see only the source prefix through it, and deep probes replace
only its named proof.

The 54-line roster module is the policy nucleus, not the whole trusted
computing base. The carried-artifact ratifier, closure finalizer, authority
implementations, Lean executable, and frozen environment still mediate the
verdict and require audit. Candidate generators, campaign schedulers,
literature retrieval, adapters, and evidence renderers remain outside that
base: they may propose bytes and receipts but cannot enlarge the roster or set
an authority disposition. The five preserved terminal failures above are why
the implementation boundary still needs process isolation and tamper replay
even though the policy list is small.

The exact published binary `[51,20,14]` control exposed a certificate-capacity
limit without changing that boundary. Bit-vector normalization plus Lean's
fast generated checker closed the distance-14 proposition and rejected the
distance-15 strengthening with an explicit weight-14 word. The positive proof
depends on a generated native-check axiom outside the current allowlist, so it
is excluded from ratification. The axiom-clean generic LRAT importer passes on
a small control, and the frozen large proof was confirmed compatible with the
exact regenerated 7,392-variable, 18,008-clause CNF. Its 532,290-action
explicit replay exceeded the 500-second observation envelope without a
diagnostic. The large formal task therefore remains typed unavailable.

The next admissible capability is a generic chunked kernel-pure LRAT
elaboration path or a structure-aware algebraic certificate with explicit
reflection linkage. Neither option grants binary-code vocabulary or verdict
authority to the common verifier. Detailed hashes and measurements are in
`outputs/axiompack_release_forward_ratification_20260718/kernel_boundary_audit_post_item14.json`.

## Release gate

The final local regression slices pass: 131/131 filename-matched AxiomPack tests and
183/183 broader LeanMill tests. All fourteen AxiomPack Lean modules build, and
their finite certificates contain no `native_decide`; the 49-point cycle-set
law is checked by exhaustive kernel reduction. Its top-level certificate also
closed through the current 14-authority carried-artifact ratifier with matched
control and zero provider calls (certificate record `920f4db4…`, parity record
`240341b7…`). The terminal corpus finalizer and its tamper suite pass after the
external process replay.

The current AxiomPack runtime delta is declared in
`deploy/vps_sync_files.txt`. `deploy/vps_update.sh` now rejects any changed
LeanMill script, Python module, or AxiomPack proof file omitted from that
working-tree deployment identity and refuses to overlay it on a remote checkout
with a different base commit. Shell syntax and the local declaration preflight
pass; a networked dry run still requires the operator's VPS connection profile.

Two release conditions remain outside the repaired AxiomPack surface:

1. the repository is still a dirty, partly untracked working tree, so no
   clean-checkout release identity or tag exists; the ratification toolchain
   receipt also records local changes in the Mathlib and Batteries package
   checkouts, bound by their exact status/diff hashes;
2. a full repository `lake build` reaches an unrelated modified Navier--Stokes
   target and fails there, although the complete AxiomPack target set builds.

E1 remains intentionally blocked at 189/197 strict proof pairs. Items 11 and
20 and mathematical priority remain incomplete; none is promoted by the
apparatus repairs above.
