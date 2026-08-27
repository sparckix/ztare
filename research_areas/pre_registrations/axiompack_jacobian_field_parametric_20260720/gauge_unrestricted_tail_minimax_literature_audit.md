# Literature audit: unrestricted Jacobian tail minimax

**Audit date:** 2026-08-02  
**Scope:** primary-source comparison for the normalized July 2026 map  
**Verdict:** unconditional upper bound and conditional lower mechanism absent
from the audited record; the exact minimax equality is still open in this
campaign, and historical priority is not established

## Claim-by-claim comparison

| Local claim | Closest primary precedent | Overlap | Residual content and confidence |
|---|---|---|---|
| \(\nu_z(H(P_0,Q_0))=2\nu_C(H)\) | Shaska, [*Graded Keller maps and the Jacobian Conjecture*](https://arxiv.org/abs/2607.20210), proves an adjacent order-two quotient ramification statement; standard divisor/valuation theory supplies the general multiplicity rule. | The order-two geometry is shared.  The local certificate additionally identifies the cusp kernel and proves \(C(P_0,Q_0)=z^2u\) with \(u\) a unit for the selected normalization. | The exact normalized-family identity was not found.  Once the kernel and unit are established, its valuation step is standard.  Confidence: high on standard mechanism; medium-high on absence of the exact formula from the checked map papers. |
| Candidate unrestricted symmetric logarithmic tail minimax \(\sigma_{\rm ct}=2\) | Magnus, *On the exponential solution of differential equations for a linear operator* (1954); Wright--Zhao, [*D-log and formal flow for analytic isomorphisms of n-space*](https://arxiv.org/abs/math/0209274); Domitrz--Rieger, [*Volume preserving subgroups of A and K and singularities in unimodular geometry*](https://arxiv.org/abs/0804.2596). | These sources own Magnus/D-log/formal-flow machinery or the surrounding volume-preserving source/target equivalence setting. | The current campaign proves \(\sigma_{\rm ct}\le2\) and a conditional lower mechanism.  No checked source defines this symmetric source/target degree-rate statistic or optimizes it over the declared coefficientwise-polynomial gauges.  The matching lower bound still needs a schedule-level finite/infinite target-critical dichotomy, the finite Rees carrier, and a transfer-aware infinite branch for finite Lie data; finite Lie-module support does not imply a polynomial semidirect group-module coordinate.  Confidence: medium because the map literature is new and the terminology is local. |
| All-order Witt/tensor-density/Magnus obstruction to finite positive-Rees prefixes | Witt tensor-density modules and their cocycles are classical; a recent primary reference is Gao--Liu--Pei, [*1-cocycles of the Witt algebra with coefficients in tensor product of modules*](https://arxiv.org/abs/2406.12565).  Ribón, [*Embedding smooth and formal diffeomorphisms through the Jordan--Chevalley decomposition*](https://arxiv.org/abs/1107.3601), gives nearby formal-flow embeddability obstructions. | Tensor-density actions, resonance, formal logarithms, and Bernoulli transfers are established ingredients. | No checked source combines the split \(J=0\) target kernel, quadratic-field critical residual, four-resonance bound, semidirect transfer, and least-positive-contact induction for this map.  Confidence: medium.  The stand-alone finite-prefix wording must retain **positive \(C\)-adic contact**; the pure-contact-zero case enters only through its separate tensor induction and the global composition. |
| Relation to the announced \(\mathbb C^3\) counterexample | [*A Counterexample to the Jacobian Conjecture*](https://www.ulam.ai/research/jacobian.pdf) verifies the explicit constant-Jacobian map, its three-point fiber, inverse cubic, image, nonproperness set, and families.  [The July 21 state note](https://jacobianconjectures.com/jacobian/note/) and Shaska analyze further structure. | The map, counterexample, grading, quotient geometry, and global fiber facts are prior work. | The minimax result is a structural invariant of one normalized deformation under a declared gauge category.  It adds no second counterexample and does not alter the planar problem.  Confidence: high. |

## Term audit of the current map papers

The counterexample manuscript contains the global algebraic and geometric
analysis of the map but does not formulate Hamiltonian gauge deformation,
Magnus logarithms, cusp valuation, or the symmetric tail statistic.  Shaska
states the adjacent order-two quotient ramification but does not formulate
the logarithmic-tail optimization.  The state note describes capped
deformation and the planar Poisson master equation, not an all-order minimax
theorem.

## 2026-08-06 continuation and monodromy correction

The finite/infinity alternative used in the earlier compiler was not
exhaustive.  Exact local Julia series now exhibit two finite equilibrium
transitions whose composition has a nonzero linear term and first fractional
exponent (5/2).  A separate rationalized-residue calculation proves that the
critical scalar holonomy has an infinite-order monodromy multiplier, but the
transfer of those loop iterates through an arbitrary selected two-flow
factorization remains open.

The closest primary continuation source found in the added audit is
Françoise--Roytvarf--Yomdin,
[*Analytic continuation and fixed points of the Poincaré mapping for a
polynomial Abel equation*](https://arxiv.org/abs/math/0603534).  It confirms
that analytic continuation, singularities, and ramification of polynomial
ODE Poincaré maps form a substantive global problem and can have complicated
branching.  It does not state the autonomous one-variable factor-loop lift
needed here.  Wright--Zhao's D-log paper is formal-local and likewise does
not supply that lift.  The literature audit therefore supports the present
claim boundary; it does not close the residual.

## Remaining priority checks

Before a historical claim, a second specialist audit should cover:

1. Feigin--Fuchs/Ovsienko tensor-density extension and resonance literature,
   especially whether the four-resonance plus semidirect-orbit lemma is
   packaged in a more general form;
2. the Wright--Zhao citation tree on D-log polynomiality, polynomial flows,
   and locally nilpotent derivations;
3. Block/Witt subalgebra classification, including the full
   Arnaudova--Dimiev--Papaloucas--Tatarova line;
4. isochore right-left map-germ work by Domitrz and Rieger and logarithmic
   derivations of cusps following Saito; and
5. new July/August 2026 manuscripts or repository updates not yet indexed.

The appropriate public formulation is therefore: **an exact unconditional
rate-two upper construction and an all-order conditional obstruction for the
declared gauge category, with the schedule-level finite/infinite
target-critical carrier theorem still open; this package was not found in
the primary sources audited through 2026-08-06.**

## 2026-08-06 differential-prolongation comparison

The new saturated-prolongation route has clear classical neighbors, so its
broad algebraic ingredients should not be presented as new.

- Pereira's
  [*Vector fields, invariant varieties and linear systems*](https://aif.centre-mersenne.org/articles/10.5802/aif.1858/)
  studies invariant varieties through their interaction with linear systems
  and gives computational criteria and Darboux-type consequences.  This is
  the closest structural precedent for detecting a persistent algebraic
  component by iterated action of a vector field.
- Rueda's
  [*Differential elimination by differential specialization of Sylvester
  style matrices*](https://doi.org/10.1016/j.aam.2015.07.002)
  explicitly obtains algebraic polynomial systems by differentiation and
  then applies algebraic resultants to produce elements of a differential
  elimination ideal.  This owns the general differentiate-then-eliminate
  architecture.
- Kruff--Llibre--Pantazi--Walcher,
  [*Invariant algebraic surfaces of polynomial vector fields in dimension
  three*](https://arxiv.org/abs/1907.12536), treats polynomials satisfying
  `X_f(psi)=lambda*psi` as semi-invariants and emphasizes that their zero sets
  are precisely invariant hypersurfaces.  This supports the interpretation
  of an identically persistent common factor as an invariant component.

The campaign's exact contribution is narrower: for the coupled Julia
relation of this normalized map, restriction to the visible divisor exposes
the one-variable operator `D_p(Q)=pQ'`; a kernel-checked multiplicity argument
shows that the first `deg Q + 1` triangular prolongations cannot share a root
away from `p=0`, regardless of the higher source jets.  The degree-two/three
saturated resultants are nonzero exact examples.  No inspected source states
this map-specific reduction, its finite multiplicity bound in this carrier,
or the resulting tail-minimax implication.

The novelty verdict therefore remains cautious: differential resultants,
extactic/invariant-variety methods, and Darboux factors are established; the
coupled-Julia specialization and its use in this minimax problem are a
plausibly new narrow synthesis pending specialist review and completion of
the actual-tower and endpoint-elimination steps.
