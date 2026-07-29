---
description: "Pencil-first contract for the bounded AxiomPack successor on the binary [50,20,14] table cell."
---

# Binary `[50,20,14]` structured successor: experiment contract

Date: 2026-07-19

Tick: `tick-axiompack-blc-structured-20260719`

Forecast contract:
`axiompack-blc-50-20-14-structured-successor-micro-20260719`

## Frozen claim boundary

The current Grassl table entry remains

\[
13 \le d_2(50,20) \le 14.
\]

The campaign tests the existence side by seeking a binary generator matrix
\(G\in\mathbf F_2^{20\times 50}\) satisfying

\[
\operatorname{rank}_{\mathbf F_2}(G)=20,
\qquad
\min_{0\ne u\in\mathbf F_2^{20}}\operatorname{wt}(uG)\ge14.
\]

Failure in one declared construction family is only a family-scoped null. It
does not improve the global upper bound or prove that `[50,20,14]` is
impossible. A candidate matrix is only a discovery candidate until exact
verification and current-policy LeanMill ratification both pass. Priority is a
separate literature question.

## Eigenquestion and falsifiable hypothesis

**Eigenquestion.** Can the AxiomPack loop replace its failed raw-matrix search
with one campaign-authored, finite, explicitly enumerable construction family
whose members lower deterministically to binary generator matrices?

**Hypothesis H-BLC-STRUCT-1.** Given the published `[50,20,13]` quasicyclic
control, its `[51,20,14]` parity extension, the six preserved failed matrices,
and the exact verifier, the campaign will either:

1. author a finite structured family containing a rank-20 `[50,20,>=14]`
   member; or
2. author and freeze a finite family whose complete enumeration can be
   replayed, reject every member with exact rank or low-weight evidence, and
   name a typed successor representation selected by those failures.

Raw matrices outside a frozen family, an unexecutable family description, a
sample of a larger family, or a host-authored construction do not satisfy the
hypothesis.

## Input at the mathematical frontier

The target input is the unresolved one-unit gap in the binary linear-code
table, together with the exact construction data for the current lower-bound
code and its parity extension. The 2026-07-19 source replay found the table
unchanged. The previous campaign's six exact rejections have distances
`12,12,12,10,11,12`; they are recurrence evidence against unconstrained matrix
proposals, not evidence about the structured family chosen here.

## Attack vectors and counterattacks

The campaign—not the host—must choose exactly one first family. Its admissible
orientation space includes, but is not restricted to:

- a finite quasicyclic/circulant-block grammar;
- a finite derived-code neighborhood of reviewed nearby codes;
- a finite Construction-X/XX composition grammar;
- a finite symmetry-reduced augmentation family.

For any choice, the campaign must state the parameter domain, lowering map,
symmetry quotient (if used), and cardinality before the first target query.

The counterattacks are fixed:

- **tautological orbit:** kill a family consisting only of equivalent copies
  of one seed unless equivalence reduction is itself the claimed result;
- **sample laundering:** kill any claim of exhaustion when the materialized
  instances are a sample of the declared parameter domain;
- **rank laundering:** reject rank below 20 with a dependent-row witness;
- **distance laundering:** reject distance below 14 with an explicit nonzero
  message and codeword;
- **host invention:** reject a family whose defining parameters or generator
  rows were supplied by deterministic host code rather than a campaign organ;
- **global overreach:** quarantine any inference from a family null to global
  nonexistence;
- **certificate conflation:** keep exact finite verification distinct from
  kernel ratification.

## Candidate theorem or obstruction

Positive candidate:

> There exists a binary linear `[50,20,14]` code, witnessed by the emitted
> generator matrix and its exact rank/distance certificate.

Negative family statement:

> No member of the byte-frozen campaign-authored family \(\mathcal F\) is a
> binary `[50,20,14]` code.

The negative statement is meaningful only with a replayable proof that every
parameter tuple in \(\mathcal F\) was lowered and checked.

## Proof and verification skeleton

1. A campaign organ authors a data-only family specification.
2. An independent organ reviews the specification for finite extent,
   nontriviality, provenance, and target relevance.
3. The host validates the schema, canonical parameter domain, deterministic
   lowering, and complete enumeration count.
4. `binary_linear_code.v1` checks every lowered matrix. Every rejection stores
   either a rank witness or a low-weight message/codeword.
5. If a target survives, replay all \(2^{20}-1\) nonzero messages and submit a
   separately bound construction artifact to LeanMill.
6. If the family is exhausted, bind the family digest, coverage receipt, all
   rejection digests, and the campaign-authored next representation. Record a
   family-scoped null only.

## Kill conditions and stop rule

Stop this split when one of the following occurs:

- a target witness passes exact verification and current-policy ratification;
- one frozen family is completely enumerated and disposed with a typed next
  representation;
- the campaign cannot make its chosen family executable within 480 minutes;
- a source replay changes the table cell or invalidates a frozen control;
- the provider or boundary budget is exhausted.

The last three are unsuccessful outcomes, preserved for diagnosis.

## Recurrence and capability-amnesia check

The semantic primitive precheck on 2026-07-19 surfaced the generic
`validate_explored_classes` and adversarial anti-laundering machinery; it did
not surface a binary-code family enumerator. The nearest recurrence is the
previous raw-matrix campaign. This run differs on the representation axis:
the family is authored and frozen before enumeration. No new primitive is
promoted unless the live route proves the absence of a reusable typed finite-
family consumer.

## Intended formal surface

No Lean file is authored before a mathematical artifact exists. A positive
witness should lower to a theorem over a concrete `20 x 50` bit matrix with a
rank certificate and a complete minimum-distance certificate. A negative
result should formalize only the finite family enumeration and per-member
rejections; it must not quantify over all binary `[50,20]` codes.
