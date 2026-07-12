# GP-251 attempt 3 — source-bound interpretation

Recorded 2026-07-10 after the frozen result, boundary checks, and governed
recheck. This is retrospective interpretation, not part of the preregistered
selection signal.

## Frozen result

- premise: `x = x ◇ ((x ◇ y) ◇ x)`;
- target: `x = x ◇ (x ◇ x)`;
- endogenous baseline: `leanmill.direct_equational_deduction.v2`;
- residual identification bits: `0.67665929`;
- fixed-size countermodels: none at carrier sizes four or five;
- Lean: proved with two instantiations of the premise;
- causal replay: full premise arm passed; empty and leave-one-out arms failed;
- governed status: `proved_attributed`;
- boundary result SHA-256:
  `2cbd85247d1234c431f7758a4e84f503986693428f930c47fc4bfe0c0466e6dc`;
- matched-attribution receipt:
  `c72149432780c2f18c32dea825e3c95e23069755acc997ac717eeeec39ed62cc`;
- governance-recheck receipt:
  `d7533964677d06e4d61c3a37e192e122c52305be1fc1e5e498b297b38275ac40`.

## External identification

The official Equational Theories Project equation list identifies the premise
as Equation 101 and the target as Equation 8. The project studies the 4,694
single magma equations of order at most four and publishes their implication
graph:

- <https://github.com/teorth/equational_theories>
- <https://github.com/teorth/equational_theories/blob/main/data/equations.txt>
- <https://teorth.github.io/equational_theories/implications/>
- <https://teorth.github.io/equational_theories/dashboard/>

The downloaded graph cell `(101, 8)` has status code 7. The explorer's
published decoder labels code 7 `IMPLICIT_PROOF_TRUE`: the implication follows
from the reflexive-transitive closure of explicit Lean-checked edges. The
project dashboard now reports the full single-equation implication graph
complete.

Therefore attempt 3 is a rediscovery of a catalogued implication, not a new
mathematical result. It is stronger than the earlier one-rewrite control: the
cheap v2 baseline did not explain it and the governed Lean boundary needed two
premise instantiations. It still does not test the requested two-law interaction
because `pack_arity: 2` had been interpreted only as a maximum and allowed a
singleton freeze.

## Consequence for the next campaign

1. Bind `navigator_contract.presentation_size` to
   `{minimum: 2, maximum: 2}` when the direction asks for two-law interaction.
2. Keep the anonymous navigator scored against the endogenous cheap-deduction
   baseline; do not reveal equation numbers or literature labels upstream.
3. After freeze, subtract any available external known-implication closure as a
   second, source-bound novelty coordinate before expensive interpretation or
   publication claims.
4. Treat the Equational Theories Project's completed single-law graph as a
   control/knowledge baseline. A two-law presentation can still be interesting
   when its target is not implied by either premise alone and the conjunction
   survives larger-model, SMT, and Lean attribution checks.
