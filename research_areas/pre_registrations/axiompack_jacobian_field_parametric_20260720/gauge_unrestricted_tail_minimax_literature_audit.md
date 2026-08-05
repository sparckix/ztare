# Literature audit: unrestricted Jacobian tail minimax

**Audit date:** 2026-08-02  
**Scope:** primary-source comparison for the normalized July 2026 map  
**Verdict:** narrow candidate result absent from the audited record; historical
priority not established

## Claim-by-claim comparison

| Local claim | Closest primary precedent | Overlap | Residual content and confidence |
|---|---|---|---|
| \(\nu_z(H(P_0,Q_0))=2\nu_C(H)\) | Shaska, [*Graded Keller maps and the Jacobian Conjecture*](https://arxiv.org/abs/2607.20210), proves an adjacent order-two quotient ramification statement; standard divisor/valuation theory supplies the general multiplicity rule. | The order-two geometry is shared.  The local certificate additionally identifies the cusp kernel and proves \(C(P_0,Q_0)=z^2u\) with \(u\) a unit for the selected normalization. | The exact normalized-family identity was not found.  Once the kernel and unit are established, its valuation step is standard.  Confidence: high on standard mechanism; medium-high on absence of the exact formula from the checked map papers. |
| Exact unrestricted symmetric logarithmic tail minimax \(\sigma_{\rm ct}=2\) | Magnus, *On the exponential solution of differential equations for a linear operator* (1954); Wright--Zhao, [*D-log and formal flow for analytic isomorphisms of n-space*](https://arxiv.org/abs/math/0209274); Domitrz--Rieger, [*Volume preserving subgroups of A and K and singularities in unimodular geometry*](https://arxiv.org/abs/0804.2596). | These sources own Magnus/D-log/formal-flow machinery or the surrounding volume-preserving source/target equivalence setting. | No checked source defines this symmetric source/target degree-rate statistic, optimizes it over the declared coefficientwise-polynomial gauges, or proves a matching value for this map.  Confidence: medium because the map literature is new and the terminology is local. |
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

The appropriate public formulation is therefore: **an exact all-order
minimax theorem for the declared gauge category, not found in the primary
sources audited as of 2026-08-02.**
