# LeanMill formalizations

Curated, **machine-checked Lean 4 + Mathlib** formalizations produced end-to-end by
[**LeanMill**](../../docs/concepts/leanmill_architecture.md) — a governed proof-search environment that runs a
`formalize → solve → govern → self-learn` pipeline over frontier-model agent leaves. Each result here is the
harness's output unit: a **typed, governed exit** — a kernel-verified closure with an explicit assumption/axiom
account — not agent activity.

These are the *trustworthy-by-construction* artifacts: produced from a natural-language blueprint, gated by a
**faithfulness firewall** before any proof is attempted (the statement must compile, be non-trivial, and round-trip
faithful to the NL), and every closure re-verified by an **anti-laundering governance kernel the leaf cannot
influence**. Each `.lean` file is self-contained (`import Mathlib`) and carries a GENERATED provenance header
(outcome, axioms, real elapsed, phases, reuse) emitted by `promote_campaign_artifact.py` — never hand-authored.

## Layout

| Folder | What | Contents |
|---|---|---|
| [`finance/`](./finance/) | Asset pricing, market microstructure, capital structure | FTAP (easy direction); constant-product AMM temporal + no-arbitrage invariants; no round-trip arbitrage at any reachable AMM state; corporate APR + pari-passu waterfalls |
| [`strategy/`](./strategy/) | Game theory / monotone comparative statics | Topkis (supermodular) and ordinal/single-crossing comparative statics |
| [`distributed_systems/`](./distributed_systems/) | Fault tolerance / quorum systems / consensus | Byzantine quorum intersection: safe + available threshold quorums exist iff `n ≥ 3f + 1` (the `n > 3f` bound), with the intersection→correct-node lemma and a tight witness (blueprint co-located) |
| [`cryptography/`](./cryptography/) | Cryptography / information-theoretic security | Shamir `(t, n)` threshold secret sharing: reconstruction from any `t` shares, perfect secrecy (`∃!` interpolant) from any `t − 1`, and tightness at the boundary — on the banked low-degree-uniqueness / root-count rungs |
| [`blueprints/`](./blueprints/) | The natural-language inputs | One `*_blueprint.md` per theorem family — the operator-authored NL the apparatus formalized from (the *only* human input) |

Each code folder has its own README with a per-theorem summary.

## Trust model

- **Autoformalized, not hand-written.** The blueprint is the human input; the apparatus produces the Lean
  *statements* (through the faithfulness firewall) and the *proofs*.
- **Kernel-ratified.** Every filed theorem is an independently ratified closure with a matched-negative-control
  receipt and a passing governance kernel (anti-laundering + statement-integrity + axiom audit).
- **Axiom-clean.** `#print axioms` (in each file) reports only the standard Mathlib axioms — `propext`,
  `Classical.choice`, `Quot.sound` — and **no `sorryAx`**. Every proof is sorry-free.
- **Compounding.** Later targets *cite* earlier banked rungs rather than re-deriving them
  (e.g. `amm_no_cyclic_arbitrage` stands on the banked `constant_product_amm` theory) — a deliberate demonstration
  that the library *is* the environment.

## Time accounting (real elapsed wall)

Provenance headers report **`campaign span`** = the real elapsed wall (last − first attempt).
**`cost-to-closure total`** is the summed *active-solve* time only — smaller, because it omits formalization,
Mathlib imports, warm-env builds, and inter-attempt gaps. For a milestone worked across several re-runs, the
`milestone` line reports the combined real span across the campaign family (and which run proved vs reused vs
closed), so a cheap reuse-run's time is never mistaken for the proving cost.

## Verify it yourself

From a Lean project with Mathlib on the toolchain:

```
lake env lean finance/<file>.lean      # or strategy/<file>.lean
```

It should elaborate with no errors and print the axiom audit (standard axioms only).

## See also

- [LeanMill architecture](../../docs/concepts/leanmill_architecture.md) — how the harness produces these.
- [LeanMill positioning](../../docs/concepts/leanmill_positioning.md) — what it's for and why the untrusted-claim regime.
