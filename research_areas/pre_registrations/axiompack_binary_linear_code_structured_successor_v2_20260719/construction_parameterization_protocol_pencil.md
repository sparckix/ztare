# Runtime-extensible construction protocol pencil

Date: 2026-07-20

Hypothesis: `H-AXIOMPACK-CONSTRUCTION-20260720-03`

## Eigenquestion

Can one campaign-local, data-only protocol support both finite construction
families and exact symbolic construction charts while preserving the existing
navigation, AdapterForge, verification, feedback, and ratification lifecycle?

## Governing objects

### Construction parameterization

- **Job:** name a finite or symbolic parameter carrier and the safe lowering
  required to materialize candidate data.
- **Author:** a cold campaign leaf, or AdapterForge acting on the leaf's frozen
  language request.
- **Lifecycle:** authored before target evaluation; immutable within one
  campaign context and epoch.
- **Authority:** proposal only. It cannot certify coverage, satisfiability,
  candidate correctness, or terminal success.
- **Equality:** content identity over the context, epoch, request, variable
  domains, constraint/lowering descriptors, and resource contract.

### Exact constraint problem

- **Job:** bind a parameterization to a canonical, bounded problem for one
  declared decidable fragment.
- **Owner:** a registered backend capability.  The common protocol owns only
  the backend capability identity, its content-bound contract reference, and
  bounded data-only problem bytes.  Coefficient carriers, canonical scalar
  encodings, relations, and exact arithmetic remain behind that capability.
- **Lifecycle:** derived from one immutable parameterization; changing a
  domain, equation, symmetry gauge, or backend fragment creates a new object.
- **Authority:** mathematical syntax only. Solver output does not acquire
  verifier or ratification authority.
- **Equality:** the backend-canonical problem bytes, capability-contract
  identity, and resource ceilings; the outer protocol compares only their
  frozen content identities.

### Construction execution

- **Job:** enumerate or solve within the declared fragment and emit candidate,
  exact rejection, exhausted-with-certificate, or typed-unavailable results.
- **Owner:** deterministic host execution of reviewed interpreters/backends.
- **Lifecycle:** one parameterization/problem/backend contract and one frozen
  budget allocation; crash replay resumes the same identity without another
  provider call.
- **Authority:** execution evidence only. Candidate satisfaction is decided by
  the registered adapter verifier; terminal credit remains downstream.
- **Equality:** parameterization/problem/backend/budget digests plus ordered
  candidate and residual receipts.

### Construction residual and revision

- **Residual job:** expose the exact failed constraint, verifier counterexample,
  or capability boundary without suggesting the mathematical revision.
- **Residual owner:** host verifier/interpreter.
- **Revision job:** select the next representation, variable domain, symmetry
  gauge, or backend request.
- **Revision owner:** a later campaign leaf consuming the residual receipt.
- **Lifecycle:** a revision is a new parameterization causally bound to its
  predecessor and residual; it cannot overwrite them.

## Existing categories to extend

The protocol should extend, not fork:

1. `witness_construction_boundary.py` for public predicate, adapter capability,
   exact candidate replay, and downstream task discharge;
2. `finite_construction_family.py` as the materialized finite special case;
3. `generative_representation.py` for data-only alpha/gamma and raw replay;
4. `TheoryLanguageExpansionRequest` and AdapterForge for cold authorship,
   quarantine, host conformance, and independent review;
5. the existing feedback-wave and later-leaf authorship receipts for revision;
6. construction-artifact ratification and LeanMill for terminal mathematical
   authority.

No substrate-specific branch belongs in `frontier_campaign_runner.py`. The
runner should dispatch by reviewed artifact identity and registered generic
consumer, as it already does for finite families and generative snapshots.

## Safe runtime extensibility

Runtime construction is extensible through canonical data and reviewed
operation vocabularies. A leaf may introduce new variables, finite domains,
exact polynomial constraints, template structure, symmetry declarations, and
backend requirements. AdapterForge may materialize those bytes in a
campaign-local workspace. The host may interpret only operations already
owned by the generic protocol or named by a registered adapter capability.

A request needing a new executable primitive yields a typed capability gap.
It may cause a reviewed library addition in a later release, but it cannot
authorize importing campaign-generated Python or mutating the live registry.
This is the boundary between dynamic mathematical language and dynamic code
execution.

### Field-neutral correction after adversarial review

The first conformance implementation used rational parameter sorts,
`Fraction` arithmetic, sparse rational polynomials, and two built-in backend
objects inside the common parameterization module.  That arrangement is not
the stable category: adding `GF(p)`, an extension field, a bit-vector solver,
or a proof-producing SAT backend would require editing the purported common
kernel.

The stable outer object instead carries

```text
backend_capability = (adapter_id, capability_id, contract_sha256)
backend_problem    = bounded canonical JSON owned by that capability
materializer       = bounded safe artifact template
resource_envelope  = common ceilings
```

The registered capability validates and canonicalizes `backend_problem`,
executes it, and returns the shared closed residual algebra: candidate,
rejected assignment, exhausted with the certificate required by its contract,
or typed unavailable.  The common layer checks identity, resource accounting,
candidate hashes, coverage, and joins; it does not interpret field elements or
ordered-field relations.  The present exact rational enumerator is therefore
a built-in backend conformance instance, not a universal coefficient model.
An alternate finite-field backend must be addable by registration and adapter
data alone, with no branch in the campaign runner or common protocol.

## Two conformance instances

### Binary code

Use finite Boolean parameters to select a bounded generator-family chart.
Materialization produces the existing generator-matrix witness schema. Exact
rank/distance replay produces the existing low-weight message residual. The
same parameterization protocol must be able to freeze a complete finite domain
and join every parameter to one execution receipt.

### Rational polynomial map

Use exact finite rational coefficient domains over a sparse ansatz. The
adapter lowers constant-Jacobian and equal-image conditions to canonical
rational polynomial constraints. Candidate materialization produces the
existing sparse polynomial-map witness schema. Exact determinant/collision
replay remains the final adapter check. A symbolic Gröbner backend may later
consume the same constraint identity; absence today must be typed
`backend_unavailable`, not emulated by sampling.

### Cross-field polynomial campaigns

"Across fields" is a family of exact target identities, not an implicit
change of scalar semantics. A polynomial construction capability advertises
the canonical field specifications it owns, for example `Q`, `GF(p)`, or a
finite extension `GF(p)[u]/(m(u))` with a checked irreducible modulus. The
field specification, characteristic, scalar codec, normalization contract,
and backend certificate policy are included in `backend_problem` and its
content digest. Changing any of them creates a sibling construction problem;
it cannot reuse a verdict from another field by equality.

The common lifecycle may schedule and join a product of these sibling
problems. Their registered capabilities can choose different exact engines:
finite enumeration or bit-vector/SAT over small finite fields, modular or
Groebner methods over larger exact fields, and rational reconstruction plus a
full exact replay over `Q`. All return the same outer residual algebra and all
candidate maps still pass the target adapter's determinant/collision
verifier.

Cross-field information requires a separate checked morphism. Reduction of
an integral or rational ansatz modulo a good prime can refute that ansatz or
rank coefficient choices, while lifting a modular candidate requires its
declared denominator, discriminant, and reconstruction obligations. A
collision or Jacobian identity in positive characteristic has no
characteristic-zero authority without that receipt. This makes broad modular
scouting useful without conflating the mathematical questions.

## Kill conditions

- an opaque `domain_payload` becomes the effective protocol;
- the host chooses the ansatz, coefficients, family, or revision;
- generated executable code is imported;
- a registry changes inside a campaign;
- solver `UNSAT` becomes exhaustion without a replayable certificate when the
  backend contract requires one;
- post-outcome artifacts masquerade as cold parameterizations;
- resource ceilings are advisory;
- a candidate bypasses adapter verification or construction ratification;
- finite and symbolic problems need different campaign state machines;
- the shared protocol merely renames the two existing one-off paths.

## Completion test

The architecture is not complete merely because both payloads validate. A
cold replay must demonstrate:

\[
\text{leaf request}
\to \text{AdapterForge parameterization}
\to \text{host review/execution}
\to \text{exact adapter residual}
\to \text{later leaf revision}
\to \text{candidate ratification or typed unresolved exit}.
\]

Both conformance instances must traverse this chain with provider-free crash
replay and no host-authored mathematical choice.
