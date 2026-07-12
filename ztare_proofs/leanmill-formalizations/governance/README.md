# Governance — machine-checked formalizations

Kernel-verified Lean 4 + Mathlib formalizations of corporate-governance and voting-procedure logic, produced
end-to-end by [LeanMill](../../../docs/concepts/leanmill_architecture.md) from natural-language blueprints
(through the faithfulness firewall: each statement compiles, is non-trivial, and is round-trip faithful to the NL;
each proof is independently kernel-ratified with an axiom audit). Every file is self-contained (`import Mathlib`)
and carries a GENERATED provenance header (outcome, axioms, real elapsed, phases, reuse) emitted by
`promote_campaign_artifact.py` — not hand-authored.

A governance rule is a **procedure** institutions run on — a charter's adoption logic, not a preference-aggregation
theorem — so this domain sits apart from the social-choice results (Arrow, Gibbard–Satterthwaite, median voter)
elsewhere in the library. As in `Compliance`, the value is a faithful formalization of contested institutional
intent, not proof depth: the numbers live in a bylaw, but the litigated question is the *basis* on which they are
measured.

## Contents

### `CorporateGovernanceQuorumSupermajority.lean` — quorum, supermajority, and the basis abstentions count on
`corporate_governance_present_basis_two_gate_and_basis_divergence`. A shareholder or board action is adopted only
if two gates clear — a **quorum** (enough voting power present) and a **supermajority** (enough of the base votes
in favour). The contested, non-mathematical question is the *basis*: is the supermajority measured against shares
**present** or against votes actually **cast**? The two readings agree until someone abstains, and then they
diverge — an abstention swells the "present" base while leaving the "cast" base untouched. Real charter fights turn
on exactly this. The theorem has two parts, proved over an ordered field of real-valued tallies (`q`, `s`
parametric, no fixed decidable carrier):

1. **Two-gate adoption.** On the present basis, an action is adopted exactly when both the quorum gate and the
   present-basis supermajority gate clear, and failing either alone defeats it.
2. **The basis is load-bearing.** There is a tally that meets quorum and clears the supermajority on the *cast*
   basis yet fails it on the *present* basis — so the same votes adopt under one reading of the charter and defeat
   under the other, and the divergence is driven entirely by a **strictly positive abstention**.

Four supporting lemmas are established and cited: adoption is monotone in support (converting against/abstain power
into for-power, present base fixed, cannot un-adopt); the present and cast bases coincide when abstain-power is
zero; the explicit basis-divergence witness; and the supermajority threshold is sharp (exactly the `s`-fraction of
the present base is adopted, strictly below is not). Axiom-clean `[propext, Classical.choice, Quot.sound]`.

### Definitions

The guarantee is only as meaningful as these definitions — read them to check the faithfulness boundary. Tallies
and thresholds live over an ordered field `K`; `q` (quorum) and `s` (supermajority) are parametric, with no fixed
decidable carrier. Every gate is cross-multiplied, so there is no division and no nonzero-denominator side
condition, and the thresholds stay exact.

- `presentPower t := t.forPower + t.againstPower + t.abstainPower` — shares *present* (abstentions included).
- `castPower t := t.forPower + t.againstPower` — shares *cast* (abstentions excluded).
- `CharterFraction x := 0 < x ∧ x ≤ 1` — a quorum or supermajority fraction.
- `QuorumMet q t := q * t.totalPower ≤ presentPower t` — the quorum gate.
- `SupermajorityPresent s t := s * presentPower t ≤ t.forPower` — supermajority on the *present* base; an abstention swells the denominator and tells against the motion.
- `SupermajorityCast s t := s * castPower t ≤ t.forPower` — supermajority on the *cast* base; an abstention is neutral.
- `AdoptedPresent q s t := QuorumMet q t ∧ SupermajorityPresent s t` — the charter's adoption rule on the present basis.

The two supermajority readings coincide when `abstainPower = 0` and diverge exactly when it is strictly positive —
the divergence the main theorem certifies.
