# Formal residual coverage compiler result

**Date:** 2026-08-02
**Status:** compiler and governed Puiseux refinement supported; final audits active

## Outcome

LeanMill now has a content-bound coverage compiler for broad claims.  It
replays a finite decomposition DAG, replays every offered theorem through the
governed ratification bridge, computes the bottom-up covered set, and emits the
exact leaf, inference, and direct-root residual.  It never emits a formal
evidence receipt.

A formal proposition identity binds four pieces of content:

1. qualified target identity;
2. normalized target-signature digest;
3. posed-source digest; and
4. Lean toolchain identity.

This stronger identity was required by the cross-context adversary.  Matching
signature text alone would allow another source to redefine a name used in the
statement while preserving its printed signature.

Root promotion eligibility requires all reachable leaves, all inference
rules, bottom-up root coverage, and a direct governed root theorem.  A direct
root receipt cannot bypass missing child or inference coverage.

## Jacobian critical-Puiseux instance

The executable replay is
[`jacobian_critical_puiseux_formal_coverage.py`](jacobian_critical_puiseux_formal_coverage.py).
It preserves the established single-flow and two-flow semantic digests:

- `6c3a97ebae223d4c0dbf6762d1399d242ea951459d3e7ae44255be2575931926`;
- `190c7ff996246b663dc6ab94435aaea81fa8f8e4c009188badac06ec88bc963c`.

Seven exact leaves now have governed formal support:

| Leaf | Governed record | Formal receipt |
|---|---|---|
| Critical coefficient arithmetic | `6caf168f5d071956f6f0d8a3567296c7984bcae13b3b682afb62381fa8c12699` | `dc3c205e70124f469a5fd5421873568c0dce822e4b4233fdddc0a3db55e0eeb0` |
| Julia coefficient cancellation | `a634915d075e94c0428889f33dc07ee73ee96270afd065d7cd2831dbc287dd6c` | `87382db51f823468f0c46d85d83d5bffdef24b0cf3fa372b6197ce066e63b9fb` |
| Two-flow exponent interval | `fe4c2bc04778c7e8a6b1dec1a64f16b619293ff87dfb224e9981ef121c87384f` | `a81b12695b53f9d367404b945e04bf6d378ff07311b1f33e6a7555049fdf648a` |
| Discriminant factorization | `3a53defd2a04afb350284a42f1b546555052016fd4278c22d2892b3967b88a27` | `3ded1d209f499225a8efbfc7b6ea06cc6c52847f16530f6a89a658f2f1b6bb23` |
| Radical numerator simple zero | `80013b6ea38fc8dd4c6065bc8a29b503b583509d5d8123b7f73c36e5d50e3883` | `4466cbbe4df7e108cb00538752061d43c612a9ff035a8e6c37b44394d04569a7` |
| Radical denominator nonzero | `200a02cc74d82fc9249d024167647df4b92ff10e18bacfb980c372e787364c1d` | `7805bfcdc3d7eab508aca839aee6fc157080b2c10c0952af42e9c3ff8ae03a07` |
| Radical quotient scale | `35dfc7a5250f950269181742170b3e6e404b7ffc63dede4a93eed64604cbb136` | `291a64cb3be111b370fe13d3176306e992e2d7bc786ad66f71ebd9b822f4a6b9` |

The resulting decomposition digest is
`f22950cd2bd08468fa3bfdd3331b7221632e5aa4a94dcd4795710a8bc0a914a6`.
The coverage certificate is
`c3926d743c36e9d84a316bf648e4b8599bd2e99c20d460eceff1627a3888cf4b`,
and its full replay envelope is
`d33b673d16b0097a84ff7ba9e6972983d6c0c9e5d68a3619f63f15927a6b02fe`.

## Exact residual

The three uncovered leaf propositions are:

1. passage from the governed leading scales through the selected square-root
   branch and logarithmic integration to the endpoint `u^(5/2)` series term;
2. Julia's all-order formal-flow identity for the selected holonomy; and
3. the exhaustive finite/infinity/proportional structural alternative for two
   polynomial flows.

Three semantic inference rules remain: selected-germ assembly, single-flow
exclusion, and terminal two-flow assembly.  The direct terminal theorem is
also unformalized.  Therefore:

```text
all_required_leaves_covered       = false
all_inference_rules_covered       = false
root_bottom_up_covered            = false
root_directly_ratified            = false
root_authority_promotion_eligible = false
formal_authority_issued           = false
```

The finite Julia recurrence check remains a stress test and does not count as
the all-order formal-flow leaf.

## Ratification boundary findings

The broad mechanism conjunction built in Lean but its governed transition
returned `rejected_mnc_inconclusive`; no record was created.  Its two narrow
mechanism theorems subsequently closed independently.

The aggregate germ-scale conjunction built in Lean and reached governance,
but returned `governance_unavailable`; again no record was created.  Four
narrow algebraic targets then closed independently.  The coverage DAG consumes
only those seven positive governed records, never the two rejected aggregate
attempts.

## Adversarial coverage

The focused suite rejects partial-root promotion, missing leaves, semantic
leaf or inference laundering, duplicate receipts, duplicate proposition
identities, extra supports, wrong authority, crossed governed replay, same
printed signatures from another target or posed source, cycles, unreachable
debt, graph-identity collisions, and certificate tampering.  The same compiler
also closes a complete alien valuation DAG without Puiseux vocabulary.

## Boundary

This campaign mechanizes what remains to formalize and adds seven governed
mechanism leaves.  It does not upgrade the critical Puiseux terminal, the pure
contact-zero branch, or the unrestricted minimax theorem to formal-kernel
authority.  Those scopes retain their established adapter/compiler authority
until the seven residual obligations above are discharged in exact Lean
statements and governed records.
