---
description: "PATTERN-002 adversarial preflight of the finite-family successor route."
---

# Structured-family adversarial lane

Date: 2026-07-19

Lane: `PATTERN-002 / adversarial_kill`

Scope: the pre-registered binary `[50,20,14]` successor and the current
LeanMill/AxiomPack working-tree runtime. This lane inspected the campaign and
runtime without changing source code.

## Judgment

**NO-GO for a scientific family-exhaustion launch on the current executable
surface.** The run may proceed only as an explicitly labelled capability-gap
first fire, where the admissible terminal outcome is a typed unavailable
receipt. It cannot currently earn the negative-family result promised by the
experiment contract.

Two independent gaps determine the judgment:

1. The registered binary task consumes one explicit generator matrix. There
   is no executable family identity, parameter-domain freeze, lowering join,
   member-coverage receipt, or family-exhaustion adjudicator.
2. A positive `[50,20,14]` candidate needs `2^20 - 1` nonzero-message checks,
   while the current kernel-certificate producer refuses any artifact above
   `2^14 - 1`. Exact host verification can discover a candidate, but the
   campaign's ratification success branch is unavailable under the present
   certificate capability.

The campaign's mathematical claim boundary is well stated. Its advertised
execution route is ahead of the runtime.

## Evidence from the current runtime

### The construction boundary is singleton-valued

- `binary_linear_code.v1` exposes exactly one theory-task capability, described
  as verification of "one explicit binary generator matrix"
  (`src/ztare/leanmill/adapters/binary_linear_code.py:707`).
- Its public witness schema has only the concrete matrix fields
  `schema`, `field_order`, `length`, `dimension`,
  `coordinate_convention`, and `rows_hex`
  (`src/ztare/leanmill/adapters/binary_linear_code.py:47`).
- The witness-constructor output must contain one `artifact` satisfying that
  exact schema (`src/ztare/leanmill/witness_construction_boundary.py:599`).
- Boundary execution normalizes and verifies that single artifact twice for
  determinism (`src/ztare/leanmill/witness_construction_boundary.py:1270`).

The durable candidate memory is useful but insufficient for exhaustion. It is
keyed by source-artifact and normalized-artifact digests and retains exact
outcomes (`src/ztare/leanmill/frontier_campaign_runner.py:1305`). It has no
family digest, parameter identity, expected domain, lowering receipt,
pre-outcome family review, or expected-versus-observed coverage join. A series
of remembered matrices therefore remains a series of candidates.

### Existing adjacent machinery does not close this gap

- `quasicyclic_generator_matrix` is a deterministic substrate helper
  (`src/ztare/leanmill/adapters/binary_linear_code.py:1130`), but it is absent
  from the adapter's registered `CAPABILITIES`. The campaign cannot invoke it
  as a typed family lowerer. Calling it from a one-off host loop would also
  leave family authorship and coverage unbound.
- The alpha/gamma generative-representation surface consumes `FiniteModel`
  batches over theory signatures. Its own countermodel finder returns
  `unknown` after a reviewed batch has no countermodel because generator
  exhaustiveness is not host-certified
  (`src/ztare/leanmill/generative_representation.py:315`). It is not a generic
  constructive-witness family consumer.
- AdapterForge currently admits only `leanmill.object_coordinates.v1` and
  `leanmill.materialized_generative_representation.v1`
  (`src/ztare/leanmill/adapter_forge.py:266`). The campaign statement that
  AdapterForge may return a reviewed finite-family materialization has no
  matching output interface.

### Positive ratification is also unavailable

The host verifier can replay all `2^20 - 1` messages. The current formal
certificate path caps its compiled exhaustive range at `2^14 - 1`
(`src/ztare/leanmill/adapters/binary_linear_code.py:29`) and raises
`binary_kernel_certificate_message_bound_exceeded` for larger inputs
(`src/ztare/leanmill/adapters/binary_linear_code.py:920`). Thus these statuses
must remain distinct:

1. concrete matrix authored;
2. exact predicate verification passed;
3. construction artifact ratified by the current kernel policy;
4. priority/novelty reviewed against current primary sources.

At `[50,20,14]`, status 2 is executable and status 3 is not yet executable.

## False-exhaustion and authorship threats

| Threat | Current protection | Remaining failure |
|---|---|---|
| Sample renamed as family | Prose forbids it | No expected-domain/observed-domain equality check |
| Repeated concrete matrices renamed as enumeration | Artifact outcome memory prevents exact repeats | Memory has no parameter or family identity |
| Post-outcome family choice | Campaign says freeze first | No byte/digest ordering relation between family review and first verification |
| Host-selected mathematics | Concrete witness carries witness-constructor authorship | No family-spec authorship type; a custom host loop could select masks or neighbors |
| Symmetry quotient omits cases | Prose requires a check | No quotient map, fiber coverage, or reviewer-bound omission test |
| Duplicate parameters collapse after normalization | Normalizer is deterministic | No parameter-to-normalized-artifact multiplicity join |
| Verifier unavailable counted as rejection | Singleton boundary types unavailability | No family aggregate that requires every member to be rejected rather than unavailable |
| Navigation/budget exhaustion read as mathematical exhaustion | Campaign's claim boundary forbids global overreach | No typed family status prevents later prose from conflating the two |
| Deterministic verification read as ratification | Campaign separates them | Positive certificate is known unavailable at dimension 20 |
| Family null read as priority-novel mathematics | Campaign separates novelty | No post-freeze source-review status is bound to a negative family theorem |

The existing source control and the published quasicyclic seed are admissible
inputs. They become host-authored mathematics only if deterministic code uses
them to choose the new family, parameters, or composition. A generic host
interpreter may lower bytes chosen by the campaign.

## Smallest substrate-invariant consumer contract

Add one common boundary object rather than a binary-code family subsystem:

`leanmill.reviewed_finite_construction_family.v1`

It should consume the existing adapter's witness interface and carry:

1. `family_id`, `family_spec_sha256`, and campaign-role authorship receipt;
2. a canonical finite parameter domain, exact declared cardinality, and a
   digest of the ordered parameter IDs;
3. either:
   - an explicit, data-only ordered relation
     `parameter -> witness_artifact`, which is the smallest safe first fire; or
   - a reviewed registered lowering descriptor invoked twice per parameter;
4. symmetry policy (`none` by default), with any quotient carrying a reviewer-
   bound map and coverage obligation;
5. an independent review bound to the family bytes **before** target outcomes,
   accepting mathematical identity, finite extent, nontriviality, and the
   claimed lowering semantics;
6. the frozen target witness interface, so substrate-specific normalization
   and verification remain adapter-owned.

The generic executor should emit
`leanmill.finite_construction_family_execution.v1` with:

- exact expected/observed parameter-ID equality;
- one parameter-to-source-to-normalized artifact join per member;
- duplicate multiplicities retained even when verification is memoized;
- per-member status in `{verified, rejected, unavailable}` with evidence refs;
- an aggregate status in `{witness_found, exhausted, unavailable}`;
- `exhausted` only when every expected parameter is present and every member is
  rejected by a complete verifier receipt;
- a family-scoped claim string bound to the frozen family digest;
- no authority over global nonexistence, kernel ratification, or novelty.

The typed next representation belongs to a later navigation response consuming
the aggregate. It may be required for the campaign's information-yield stop,
but it must not participate in the proof that the family was exhausted.

This contract applies to codes, finite algebras, graph constructions, protocol
machines, or any substrate whose adapter already supplies a strict artifact
schema, normalizer, and verifier. Family vocabulary and lowering parameters
stay in data and adapter capabilities. The common kernel owns only identity,
coverage, provenance, deterministic joins, and the closed outcome algebra.

## Mandatory kill tests

The launch changes to GO only after all tests below pass.

1. **Schema substitution.** Submit a family object to the singleton witness
   interface. It must return a typed missing-capability outcome; it must never
   degrade to a sequence of unbound concrete candidates.
2. **One-member omission.** Declare `N` canonical parameters and materialize
   `N-1`. The aggregate must be `unavailable`, never `exhausted`.
3. **Undeclared member injection.** Add one artifact with no declared parameter.
   Coverage must fail.
4. **Duplicate lowering.** Map several distinct parameters to one normalized
   artifact. Verification may be reused, while the coverage receipt must retain
   every parameter and its multiplicity.
5. **Post-outcome mutation.** Change the family domain, lowering relation, or
   quotient after one member outcome exists. Digest/order binding must reject
   the aggregate.
6. **Authorship crossing.** Replace the campaign-role family authorship with a
   host-produced row or unbound agent call. Admission must fail.
7. **Nondeterministic lowering.** Two lowerings of one parameter differ.
   Execution must be `unavailable` and produce no member credit.
8. **Incomplete verifier.** Any member reports message-budget or capability
   unavailability. The family cannot be exhausted.
9. **Quotient omission.** Remove one declared quotient fiber or provide a
   quotient without a bound review/coverage receipt. Admission must fail.
10. **Tautological orbit.** Every member normalizes to the seed. The reviewer
    must reject family nontriviality unless equivalence reduction is the
    preregistered claim.
11. **Status separation.** A host-verified `[50,20,14]` candidate with the
    current certificate bound must end as `discovered_pending_ratification`,
    not ratified.
12. **Claim-scope mutation.** Reword an exhausted-family result as global
    `[50,20,14]` nonexistence or as a priority claim. Validation must quarantine
    the changed claim.

## GO conditions

The scientific run is GO when:

- the generic family input, independent review, execution aggregate, and kill
  tests exist;
- the campaign-authored family cardinality fits the frozen member/boundary
  budget before enumeration begins;
- family review is content-bound and precedes target evaluation;
- the positive branch explicitly permits
  `discovered_pending_ratification`, or a separate dimension-20 kernel
  certificate capability has passed its own controls;
- result reporting has separate discovery, deterministic verification,
  ratification, and novelty fields.

Until then, launching the current campaign can still measure whether the
autonomous loop identifies and routes the capability gap. Such a run is an
apparatus result and cannot close the mathematical family claim.
