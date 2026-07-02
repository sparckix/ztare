# Shamir threshold secret sharing: reconstruction from t shares AND perfect secrecy from t − 1

Adi Shamir's 1979 scheme is the foundational construction of information-theoretic cryptography: split a secret
into `n` shares so that (a) any `t` shares REBUILD it exactly (reconstruction / the threshold), and (b) any `t − 1`
shares reveal NOTHING — not "nothing feasible to compute", but nothing at all, unconditionally (PERFECT SECRECY).
The two guarantees ride on ONE object: a polynomial of degree below `t` over a field, evaluated at distinct
points; the secret is its value at `0`, and the other coefficients are the randomness. Reconstruction is that
`t` points pin a degree-`< t` polynomial; secrecy is the SAME pinning read the other way — `t − 1` points leave
the value at `0` completely free, one polynomial per candidate secret.

The distinctive machine-checked output is the TWO-SIDED threshold from a single mechanism: `t` suffices and
`t − 1` is worthless, and the second half is stated honestly. Perfect secrecy is NOT "the secret is not
determined" (a weak negative) and NOT "there exists a consistent polynomial" (trivially the real one) — it is
that EVERY candidate secret is consistent with EXACTLY ONE degree-`< t` polynomial matching the `t − 1` observed
shares, i.e. secrets and consistent polynomials correspond ONE-TO-ONE, so the observation cannot prefer any
secret over another. This secret-sharing vocabulary is not in Mathlib (cryptolib has ElGamal, ArkLib has SNARKs;
Shamir is absent) — it is a NEW domain (information-theoretic cryptography), not a math result with a Lean proof
already. Theory-building: establish the scheme's vocabulary, probe the polynomial/interpolation API with the warm
checker and Loogle, and decompose however the kernel teaches. A non-closure is an honest gap, never a fake
closure and never a silent weakening (no `t − 1 → t` retreat, no single-secret secrecy, no lucky-node-set
reconstruction).

## Domain
formalization-nonmath

## Theory file
shamir_secret_sharing.lean

The bespoke vocabulary Mathlib lacks — establish each once, over a field of shares, and never "prove" a
definition:

- **Field of shares / secret** — a field `F` (the scheme's finite field; the reconstruction and secrecy
  correspondences are field-general, so do not assume more structure than the claim needs). The secret is an
  element of `F`. Non-degeneracy needs at least two secrets (`F` nontrivial).
- **Threshold** — a natural number `t` (`1 ≤ t`), the number of shares required.
- **Sharing polynomial for a secret `s`** — a polynomial over `F` of degree below `t` whose value at `0` is `s`.
  (Node `0` encodes the secret; the remaining coefficients are the dealer's randomness.)
- **Node / share** — a participant is a DISTINCT, NONZERO point of `F`; that participant's share is the sharing
  polynomial evaluated there. Node `0` is reserved for the secret, so no share is ever trivially the secret.
- **Consistency with observed shares** — a polynomial is consistent with a given set of (node, value) shares when
  it evaluates to each value at each node.

## Target
Over a field `F` with a threshold `t` (`1 ≤ t`), DEFINE the sharing polynomial, the shares, reconstruction, and
consistency, and prove all three:

1. **Reconstruction (correctness).** For ANY secret `s`, ANY sharing polynomial `P` for `s` (degree `< t`,
   `P(0) = s`), and ANY set of `t` DISTINCT nodes, the shares at those nodes DETERMINE `P` uniquely: any
   polynomial `Q` of degree `< t` that agrees with `P` at all `t` nodes equals `P`. Hence the secret `s = P(0)`
   is recovered EXACTLY from any `t` shares. This must be the universally-quantified uniqueness statement (any
   `t` distinct nodes, any degree-`< t` agreeing polynomial), proved through low-degree uniqueness — not assumed,
   and not restricted to one convenient node set.

2. **Perfect secrecy (the load-bearing security leg).** Fix ANY `t − 1` distinct nonzero nodes and ANY observed
   values on them. Then for EVERY candidate secret `w ∈ F` there is EXACTLY ONE sharing polynomial of degree
   `< t` with value `w` at `0` that is consistent with those `t − 1` shares. Consequently the map
   `w ↦ (its unique consistent sharing polynomial)` is a BIJECTION between the secrets `F` and the degree-`< t`
   polynomials consistent with the `t − 1` shares: every secret is consistent with the observation equally, so
   the `t − 1` shares carry ZERO information about the secret. This must be the `∀ w, ∃!`-consistent-polynomial
   (equivalently, the bijection) statement.

3. **Tightness (the threshold is exactly `t`).** With `F` nontrivial (at least two secrets) and `1 ≤ t`:
   from `t − 1` shares the secret is GENUINELY undetermined — there exist two degree-`< t` sharing polynomials
   consistent with the SAME `t − 1` shares whose secrets (`value at 0`) DIFFER. Together with (1), `t` shares
   suffice and `t − 1` do not: the threshold is tight, not an artifact of a weak statement.

**GUARDS — MANDATORY, DO NOT WEAKEN.**
- **Perfect secrecy is `∀ w ∈ F, ∃!` consistent degree-`< t` polynomial (a bijection secrets ≃ consistent
  polynomials), NOT a weaker reading.** Forbidden: "the secret is not uniquely determined" (a negative that does
  not establish uniform consistency), and "there exists a consistent polynomial" (trivially the true sharing
  polynomial). The content is that EVERY secret is EQUALLY consistent.
- **Reconstruction is universally quantified over the `t`-node set** and recovers `P` (hence `s = P(0)`) EXACTLY
  via low-degree uniqueness — prove the uniqueness, do not assume it; do not restrict to a fixed lucky node set.
- **Nodes are DISTINCT and NONZERO, with `0` reserved for the secret** (`0` is not a share node), so a share is
  never trivially the secret. The counts are exact: `t − 1` in secrecy, `t` in reconstruction.
- **`F` is a genuine field with at least two secrets (nontrivial).** Do not collapse to a one-element field
  (secrecy vacuous) or otherwise trivialize the secret space.
- **`degree < t` is the scheme's definition, not a tunable.** Do not weaken to `degree ≤ t`, nor pin a fixed
  small degree; keep `t` a general natural number with `1 ≤ t`.

## Idea
(Advisory planner context — a tractability steer, NOT a formalization or decomposition mandate; the apparatus
probes the library itself.) Both legs are the SAME fact about low-degree polynomials over a field: a polynomial of
degree `< t` is pinned uniquely by its values at `t` distinct points. Reconstruction is that fact read forward —
`t` points determine the degree-`< t` polynomial, hence its value at `0`. Perfect secrecy is the same fact applied
to the `t` points `{0, x₁, …, x_{t-1}}`: fixing the value at `0` to a candidate secret `w` and the values at the
`t − 1` observed nodes yields exactly one degree-`< t` polynomial, so secrets and consistent polynomials line up
one-to-one. State reconstruction's uniqueness as its own rung; secrecy's existence (an interpolating polynomial
through the `t` points) plus the same low-degree uniqueness give the bijection; tightness reads off two distinct
secrets. Keep `t` an explicit natural number and the nodes explicit distinct field elements.
