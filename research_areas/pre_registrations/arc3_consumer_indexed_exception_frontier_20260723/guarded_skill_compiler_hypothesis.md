# H-GPSA-GUARDED-SKILL-COMPILER-20260727-46

## Identity

A compiled skill is a reusable generator of witnessed transition paths. Its
identity is the primitive operation word plus its evidence lineage. Its
current admissibility is a separate relation from opaque initiation keys to
witnessed effect/termination variants. A boundary or incompatible variant is a
typed side exit, never a synthetic successor.

The compiler owns selection and encoding. The predictive quotient owns state
equality. Reference execution owns consequences. The caller owns any
substrate-specific rendering or task meaning.

## Hypothesis

Given ordered traces of opaque source, operation, effect, successor, evidence,
and optional boundary tuples, a deterministic greedy description-length
compiler can:

1. find repeated operation words;
2. retain only words whose replacement saves more tokens than their dictionary
   definition costs;
3. reconstruct every ordinary witnessed operation exactly;
4. group successful occurrences into opaque effect/termination variants;
5. record the earliest explicit boundary encountered while attempting a
   retained word;
6. admit compiled execution only for initiation keys with successful,
   nonconflicting evidence;
7. return primitive fallback for unsafe or unseen starts.

## Discriminator

Use a generic corpus containing:

- several independent successful instances of one repeated operation motif;
- deterministic alternative paths that bounded graph enumeration can label but
  the corpus does not reuse enough to amortize;
- one attempted motif ending at an explicit boundary before completion;
- at least one unseen initiation key.

Run the compiler twice with reversed trace order. Compare exact primitive
reconstruction, description length, selected program identities, variant and
side-exit receipts, decisions at clean/unsafe/unseen starts, and selected
program count against bounded deterministic-path enumeration.

## Success and kill conditions

Success requires exact reconstruction, positive compression, a smaller retained
library, a multiply witnessed generator, earliest-step boundary localization,
compiled admission only on clean starts, primitive fallback on unsafe/unseen
starts, and order-invariant output.

Kill on any reconstruction loss, nonpositive compression, invented transition
content, missed boundary, unsafe admission, order sensitivity, no reduction
against path enumeration, or substrate nouns in the common API.

## Claim boundary

This fixture can establish the compiler's bounded contract only. Integration
with predictive quotient receipts and validation on the sealed ARC evidence are
separate experiments.
