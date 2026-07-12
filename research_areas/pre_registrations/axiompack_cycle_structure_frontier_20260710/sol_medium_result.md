# Sol-medium cycle-structure AxiomPack result (2026-07-10)

## Frozen run

- Hetzner attempt:
  `/tmp/axiompack_cycle_structure_sol_20260710/attempt-522661ed21c748a7afac5e16a76b7c79`
- Campaign: `leanmill-campaign:eeff67c3149c3747507d6d7a1c41ade1f1de397b35fdd080effca2c3b32e0ddb`
- Final context: `478c61eea0e9cfd9ea0060578656f119a89dca27f4b9980be28915373e375dce`
- Packet: `sha256:925ef5141ef3c6a2422608e320f5403d32fddf89eba61178f05a5650ab83a196`
- Search surface: 88 canonical size-five structures, 2,640 accepted
  labeled structures, 211 formulas after one context epoch, 11 semantic
  formula profiles, and 15 generated theory nodes.
- Usage: ten Sol 5.6 medium navigator calls, one governed Sol proof call,
  four fixed-size SMT calls, one Isabelle attempt, and zero metered API spend.

The navigator exercised formula authorship once. It proposed associativity,
which the host typechecked and admitted into a new context epoch. Its truth
profile duplicated an existing size-five profile, so it earned no semantic
coordinate credit.

The seed chart then produced one frozen exact-two presentation:

1. `op2(op2(x)) = x`;
2. `op0(x, op1(y, z)) = z`.

The first ranked consequence was:

`op0(x, op0(x, y)) = y`.

## Boundary result

The first consequence received `proved_exact_two_synergy` under the frozen
campaign contract.

- Z3 exhausted carrier sizes six and seven without a countermodel. Receipts:
  `1ffc656d…` and `65411f6c…`.
- Isabelle accepted a `by metis` proof. Receipt: `da292220…`.
- LeanMill produced a proof through `solver_core.solve_adhoc`; the full arm
  compiled and the empty and both leave-one-out arms failed. Governed attempt:
  `7bb2a19e…`; attribution receipt: `37e9f51f…`.
- The exact size-five context supplies one host-replayed countermodel for each
  singleton premise. Logical-ablation receipt: `7fe893f6…`.
- A provider-free governance replay retained the attributed proof. Receipt:
  `b3233c83…`.
- Isabelle and Lean therefore agree on the implication, while the finite
  witnesses establish that neither candidate premise alone implies it.

The boundary result is `4d4f5012…`; completion is `396e7b17…`. A second ranked
target also survived size-six and size-seven SMT, but the single formal-peer
and Lean allowances were already spent, so its formal status remains
unresolved.

## Mathematical disposition

The proof exposes a standard one-permutation reduction. The second candidate
premise, together with the frozen rowwise-inverse equations, forces both
`op1(a, -)` and `op0(a, -)` to be independent of `a`. Write the common left
translation as a permutation `f`; then `op1` and the diagonal inverse `op2`
both encode `f⁻¹`. The first premise makes `f⁻¹` involutive, hence `f² = id`.
The ranked target is exactly that involution law written through `op0`.

At size five the three surviving structures are the three conjugacy types of
involutions. This is the permutation-solution slice of the cycle-set/Yang–Baxter
landscape. The implication is mathematically correct and causally attributed,
with a routine-reconstruction disposition. The campaign supports no theorem
novelty claim. The surrounding field remains an active source of open
enumeration and structure questions; see the
[2025 SAT enumeration paper](https://arxiv.org/abs/2501.14363) and
[Vendramin's survey](https://arxiv.org/abs/2311.07112).

## Contract outcome

The preregistered formula-authorship hypothesis failed at the decisive step.
Sol authored a typed formula, but it did not add a semantic profile. The frozen
winner used only seed formulas. Outcome class: proposed formula has an existing
finite profile, followed by a seed-chart recovery.

The implementation hypothesis passed: a semantics-rich, base-constrained
signature reached exact SMT enumeration, anonymous navigation, larger-carrier
checks, two formal kernels, singleton ablation, and governance replay through
the generic adapter with no family-specific runtime module.

## After-action review

The principal search defect was representational. The workbench could return a
separating model ID, but the cold leaf could not inspect an anonymous object
payload. The membrane correctly hid domain names and source labels, then also
hid the mathematical structures needed for coordinate invention. Formula
proposal therefore operated without contrastive examples.

A second host omission over-priced the selected presentation. Its second
premise forces the first argument of both binary operations to be inessential.
The signature-generic finite baseline now receipts inessential arguments and
conditions residual geometry on that reduction. Repricing lowers residual
identification from `1.5994142` to `0.98522814` bits. The remaining signal is
variation among involutions inside the already-reduced permutation slice, not
evidence of a new theory family.

The post-freeze Fable request never reached model inference. The common model
resolver mapped `fable` correctly, but a late caller override reset the runtime
to Codex; the provider rejected the unsupported pairing. The override now uses
the common provider/model route and has a regression test. The failed transport
consumed the campaign's final provider-call allowance, so no substitute review
was launched. Future campaigns use Sol medium for the first source review and
reserve Fable for a sparse second opinion.

The formal boundary took about sixteen minutes and completed normally. Sparse
stdout made the foreground SSH handle appear stalled. Owned leaf process
receipts were intact and no broad process signal was sent. Progress projection
now names the outstanding phase/action reservation. Provider accounting now
separates known pre-inference CLI rejections from model calls; old receipts
remain conservatively charged.

## Next discriminator

The next campaign should use contrastive language refinement:

1. partition substrate objects by their truth vector over the current formula
   language;
2. expose two anonymous same-stratum objects in one non-singleton class;
3. let the leaf author a typed coordinate intended to separate them;
4. host-evaluate the proposal on both objects;
5. admit a new context epoch only when the pair witnesses a previously absent
   semantic profile;
6. retain the existing description-cost, cross-stratum, proof, recovery, and
   novelty boundaries.

This is a substrate-neutral CEGAR refinement of the shared incidence context.
Finite algebra renders operation tables; evidence-induced substrates render
anonymous observations. It supplies agency with a discriminating example
without prescribing a human-named strategy or axiom family.

`research_isomorphism` remains a post-freeze follow-up. A verified mechanism
fingerprint may nominate destination substrates, but it should enter routine
use only after a matched test shows that transported destinations select more
informative experiments than cold destination choice.
