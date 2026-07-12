# Corporate governance — quorum, supermajority, and the basis on which abstentions count

Opens a new institutional domain for the library: **corporate governance / voting procedure**. A shareholder or
board action is adopted only if two gates clear — a **quorum** (enough voting power is present) and a
**supermajority** (enough of the relevant base votes in favour). Both are contested, non-mathematical institutional
intent: the numbers live in a charter or bylaw, and the litigated question is almost never the arithmetic but the
**basis** — is the supermajority measured against shares *present*, or against shares actually *cast*? The two
readings agree until someone abstains, and then they diverge, because an abstention swells the "present" base while
leaving the "cast" base untouched. Real charter fights turn on exactly this. It is a governance *procedure* — a
mechanism institutions run on — not a preference-aggregation theorem, so it sits outside the social-choice results
(Arrow, Gibbard–Satterthwaite, median voter) that adjacent libraries already hold.

Assumption-accounting note: the results depend on (1) **nonnegativity and the accounting identity** — for-, against-,
and abstain-power are nonnegative and their sum (the power present) does not exceed the total voting power
outstanding; (2) the **quorum fraction** `q` and **supermajority fraction** `s`, each in `(0, 1]`, as the actual
charter constants; (3) the **basis** for the supermajority — shares present versus votes cast — which is the
load-bearing choice the whole result is about. Surface where each is used, and make the basis explicit rather than
implicit. Keep the tallies and thresholds over an ordered field of real-valued quantities; do **not** collapse to a
fixed decidable integer instance, and do **not** silently pick a basis in a way that hides the divergence a
non-degenerate abstention creates. A non-closure is an honest gap, never a fake closure.

## Domain
formalization-nonmath

## Theory file
corporate_governance_theory.lean

## Vocabulary (build these as definitions — do not prove them)
- **Tally**: nonnegative for-, against-, and abstain-power against a total voting power outstanding, with the power
  present (for + against + abstain) not exceeding the total.
- **Quorum met**: the power present is at least the quorum fraction `q` of the total voting power outstanding.
- **Supermajority on the present basis**: the for-power is at least the fraction `s` of the power *present* (for +
  against + abstain) — abstentions are in the denominator, so an abstention tells against the motion.
- **Supermajority on the cast basis**: the for-power is at least the fraction `s` of the power actually *cast* (for
  + against) — abstentions are excluded, so an abstention is neutral.
- **Adopted**: the charter's adoption rule — quorum met and the supermajority met on the charter's stated basis
  (model the present basis as the charter convention, with the cast basis available for the comparison below).

## Target
Consider an action put to a vote: nonnegative for-, against-, and abstain-power against a total voting power
outstanding, a quorum fraction `q` and a supermajority fraction `s` each between 0 and 1, under a charter that adopts
the action only when the power present meets the quorum and the for-power meets the supermajority on the shares
*present*. The claim has two parts. First, this adoption rule is a genuine two-gate conjunction: the action is adopted
exactly when both the quorum gate and the present-basis supermajority gate clear, and failing either one alone defeats
it. Second, the choice of basis is load-bearing, not cosmetic: there is a tally that meets the quorum and clears the
supermajority on the *cast* basis yet fails it on the *present* basis — so the same votes adopt the action under one
reading of the charter and defeat it under the other, and the divergence is driven entirely by a non-degenerate
abstention. Surface that the conclusion uses the accounting identity, the fraction ranges, and — for the divergence —
a strictly positive abstention.

## Lemmas
- Adoption is monotone in support: converting against- or abstain-power into for-power, holding the total and the
  power present fixed, cannot turn an adopted action into a defeated one.
- The present and cast bases coincide with no abstentions: when abstain-power is zero, the present-basis supermajority
  holds if and only if the cast-basis supermajority holds.
- The bases diverge with an abstention: there is a tally, meeting quorum, that clears the cast-basis supermajority but
  not the present-basis one — the same for- and against-power, made to differ only by a strictly positive abstention.
- The supermajority threshold is sharp: a tally whose for-power is exactly the fraction `s` of the present base (with
  quorum met) is adopted on the present basis, while any tally strictly below that fraction is not.

## Idea
Everything is linear arithmetic over an ordered field; the value is the faithful governance model and the certified
basis-divergence, not proof depth. Keep the gates cross-multiplied (`present ≥ q · total`, `for ≥ s · present`, `for ≥
s · (for + against)`) so no division or nonzero-denominator side condition is needed and the thresholds stay exact.
The two-gate structure is asserted directly in the TARGET (unfolding the conjunction, no standalone lemma needed —
it is definitional). Monotonicity is `linarith` on the increased for-term with the present base fixed. The no-abstention coincidence is immediate once abstain-power is
0 (present base = cast base). The divergence lemma is the interesting one and wants an explicit witness: choose a tally
where the for-power is exactly the `s`-fraction of the cast base but strictly below the `s`-fraction of the present
base — the abstention is what separates them (for a majority-quorum, two-thirds charter, for = 60, against = 30,
abstain = 10 out of 100 works: `60 ≥ (2/3)·90` holds, `60 ≥ (2/3)·100` fails); state it generally in `q, s` where the
theorem is general and instantiate only the witness. Keep `q` and `s` as parameters, model the present basis as the
charter rule, and do not fix a decidable integer carrier or drop the abstain component that makes the divergence real.
