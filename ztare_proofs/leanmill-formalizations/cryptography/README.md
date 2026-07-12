# Cryptography — machine-checked formalizations

Kernel-verified Lean 4 + Mathlib formalizations of cryptographic / information-theoretic-security results,
produced end-to-end by [LeanMill](../../../docs/concepts/leanmill_architecture.md) from natural-language
blueprints — gated by the faithfulness firewall (statement compiles, is non-trivial, round-trip faithful) and
independently kernel-ratified with a matched-negative-control receipt + axiom audit. Each file is self-contained
(`import Mathlib`) and carries a GENERATED provenance header from `promote_campaign_artifact.py` (not
hand-authored).

> **Time accounting.** Headers report **`campaign span`** = real elapsed — the true wall; **`cost-to-closure
> total`** = summed active-solve time only (smaller — omits formalization / imports / gaps). The `milestone`
> line reports the combined span across the campaign family (which run proved vs closed).

## Contents

### `ShamirSecretSharing.lean` — Shamir threshold secret sharing: reconstruction, perfect secrecy, tightness
`shamir_threshold_reconstruction_secrecy_tightness`. The information-theoretic security guarantee of Shamir's
`(t, n)` threshold scheme, reduced to the algebraic core — a degree-`< t` polynomial over a field is pinned
uniquely by its values at `t` distinct points — and read forward on three counts:

1. **Reconstruction (any `t` shares determine the secret).** For a sharing polynomial `P` of the secret `s`, any
   `t` distinct nonzero share nodes reconstruct `P`, and any degree-`< t` polynomial `Q` consistent with `P` on
   those nodes satisfies `Q = P` and `Q.eval 0 = s`. Proved through the low-degree uniqueness rung
   (`low_degree_unique_of_agree_on_injective_finset`) built on the root-count lemma `iso_lemma1` (a nonzero
   degree-`< |s|` polynomial cannot vanish on `s` distinct points).
2. **Perfect secrecy (any `t − 1` shares reveal nothing).** For every candidate secret `w`, there is exactly one
   degree-`< t` polynomial that fixes `P(0) = w` and matches the `t − 1` observed share values —
   `∀ w, ∃! P, IsSharingPolynomial t w P ∧ ConsistentOn nodes obs P`. Secrets and consistent polynomials are in
   bijection, so `t − 1` observations leave every secret equally possible.
3. **Tightness at the boundary.** At exactly `t − 1` observations, two distinct secrets each admit a consistent
   sharing polynomial (`TightAtObservation`) — the secrecy bound is not slack.

The threshold `t` is an explicit natural number; share nodes are the subtype of **nonzero** field elements, so
the secret point `0` is reserved definitionally (a share can never sit on it). `PerfectSecrecy` is the full
existence-and-uniqueness statement (`∃!`), not a cardinality proxy. `#print axioms` =
`[propext, Classical.choice, Quot.sound]` — no `sorry`, no custom axioms.

The public packaged theorem is the conjunction of the three named legs
(`…_conj1` reconstruction, `…_conj2` perfect secrecy, `…_conj3` tightness), each exposed as a citable
`Guarantee` definition for downstream assembly.

The natural-language input is
[`shamir_secret_sharing_blueprint.md`](../blueprints/shamir_secret_sharing_blueprint.md).

## Scope caveat (advisory, not a false closure)

The closure is kernel-clean and true, but it proves the **algebraic / combinatorial core** of Shamir's
security argument, not the full security-theoretic statement. Read the guarantees for exactly what they say:

- **What is proved.** The `∃!` bijection between candidate secrets and consistent degree-`< t` polynomials
  (secrecy), reconstruction from any `t` shares, and boundary tightness — over **any** field. This is the
  enabling lemma Shamir's own secrecy argument rests on.
- **What is *not* proved (deliberate scope).**
  1. **Measure-theoretic Shannon secrecy** (`P(secret ∣ shares) = P(secret)`). The bijection is the *capacity*
     for perfect secrecy; the probabilistic conclusion additionally needs **uniform sampling of the
     coefficients**, which needs a **finite** field (`Fintype F`) and a probability space. This development
     avoids `MeasureTheory` by choice, so `[Field F]` is correct for the bijection but does not encode the
     finiteness the *sampling* step requires.
  2. **Robustness to malicious shares.** The reconstruction guarantee assumes the `t` submitted shares are the
     dealer's genuine ones. This models **basic (honest-but-curious) Shamir**, not Verifiable Secret Sharing
     (Feldman/Pedersen), where a forged share is the threat.

So `PerfectSecrecy` here denotes the algebraic bijection, which reads as over-claiming the crypto-theoretic
property — the denotation is argued, not independently certified. The measure-theoretic wrap and a VSS
extension are the natural follow-on targets, not defects in this closure.

## Why "cryptography" (and what is NOT here)

This is the *information-theoretic* core of secret sharing: the polynomial-interpolation facts that make the
`(t, n)` scheme perfectly secure and correctly reconstructible, proved over a finite field with `Polynomial F`.
It is deliberately **not** a computational-hardness result (no adversary running time, no reduction), and not a
protocol/execution proof — it is the algebra the security argument rests on, stated so the reconstruction and
secrecy guarantees are kernel facts rather than prose. The compounding rungs (root count → low-degree uniqueness
→ reconstruction / secrecy) are banked and cited, not re-derived.

### Definitions

The vocabulary these theorems are stated over — read them to check the faithfulness boundary; each is documented at the top of its file.

**`ShamirSecretSharing.lean`**
- `IsThreshold (t : ℕ) : Prop` — The threshold is the natural number of shares required for reconstruction.
- `DegreeBelowThreshold [Semiring F] (t : ℕ) (P : F[X]) : Prop`
- `IsSharingPolynomial [Semiring F] (t : ℕ) (s : F) (P : F[X]) : Prop`
- `shareAt [Semiring F] (P : F[X]) (x : ShareNode F) : F`
- `Shares [Semiring F] (P : F[X]) : ShareNode F → F`
- `ConsistentOn [Semiring F] (nodes : Finset (ShareNode F)) (obs : ShareNode F → F)`
- `ReconstructsPolynomial [Semiring F] (t : ℕ) (nodes : Finset (ShareNode F))`
- `PerfectSecrecy [Semiring F] (t : ℕ) (nodes : Finset (ShareNode F))`
- `secretOf [Semiring F] (P : F[X]) : F`
