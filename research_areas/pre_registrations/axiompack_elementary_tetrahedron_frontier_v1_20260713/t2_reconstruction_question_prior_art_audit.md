# T2 reconstruction question: prior-art and forward-citation audit

Date: 2026-07-15

## Verdict

The AxiomPack finalist-one witness gives a kernel-checked negative answer to a
printed open question.  An independent convention audit found an exact match
between the source definitions and the Lean definitions.

The question appears as Question 9.12 in arXiv:2206.08906 and survives peer
review as Question 9.69 on page 55 of the 2024 Russian journal version.  A
bounded forward-citation and exact-identity search found no prior answer.  This
supports a frontier-novel candidate claim for the counterexample and the
negative answer.  It does not support novelty for the broader differential-mode
or orbit-action classification.

Database absence cannot establish global priority.  The source-definition gate
has passed; expert review remains the appropriate external priority check.

## Printed question

Bardakov et al. begin with an elementary 2-solution

\[
R(x,y,z)=(x,[x,y,z],z)
\]

and, under a basepoint `c` and unary inverse-slice map `{·}`, extract four
binary operations forming a second tetrahedral 4-groupoid.  They then ask
whether the solution reconstructed from those operations is always the
original one:

\[
[x,y,z]=x\mathbin{\mR}(y\mathbin{\mc}z).
\]

The displayed extracted operations make the right side

\[
[x,\{[c,y,z]\},c].
\]

The formal artifact uses this exact argument order and quantifier scope.

## Primary publication records

- V. G. Bardakov, B. B. Chuzinov, I. A. Emelyanenkov, M. E. Ivanov,
  T. A. Kozlovskaya, V. E. Leshkov,
  [Set-theoretical solutions of simplex equations](https://arxiv.org/abs/2206.08906),
  preprint Question 9.12.
- The peer-reviewed Russian version,
  [MathNet record and full text](https://www.mathnet.ru/eng/mt697),
  *Matematicheskie Trudy* 27(1), 2024, 5--72,
  [DOI 10.25205/1560-750X-2024-27-1-5-72](https://doi.org/10.25205/1560-750X-2024-27-1-5-72),
  published Question 9.69.
- English translation, *Siberian Advances in Mathematics* 34(1), 2024,
  1--40,
  [DOI 10.1134/S1055134424010012](https://doi.org/10.1134/S1055134424010012).

## Forward citations

MathNet and Crossref each expose three distinct forward citations as of the
audit date.  OpenAlex returns a fourth record only by duplicating the
Russian/English versions of one paper.  The merged Google Scholar cluster,
which joins six versions of the source paper, reports 17 citing records.  The
two result pages were inspected separately; after collapsing evident
Russian/English and bibliographic duplicates, roughly 15 substantive works
remain.  No inspected source states or resolves Question 9.12/9.69, uses its
reconstruction identity, or supplies an equivalent counterexample.

1. V. G. Bardakov, T. A. Kozlovskaya, D. V. Talalaev,
   [n-valued quandles and associated bialgebras](https://arxiv.org/abs/2312.12007),
   *Theoretical and Mathematical Physics* 220(1), 2024, 1080--1096,
   DOI 10.1134/S0040577924070031.  Full-source search contains no
   T2-groupoid, elementary-2, tetrahedron-reconstruction, or displayed-identity
   discussion.
2. A. Pourkia,
   [Unitary and entangling solutions to the parametric Yang--Baxter equation in all dimensions](https://doi.org/10.1016/j.physo.2025.100263),
   *Physics Open* 23, 2025, 100263.  The paper concerns matrix parametric
   Yang--Baxter solutions and does not discuss the reconstruction question.
3. A. Pourkia,
   [Novel unitary and entangling solutions to the parameter-dependent Yang--Baxter equation in all dimensions](https://doi.org/10.1007/s11128-025-05039-3),
   *Quantum Information Processing* 25(1), 2026.  Exact terminology and
   identity searches found no discussion of the reconstruction question.

None of the indexed forward citations proposes an answer.  The larger Scholar
trail is broader but mostly concerns other simplex constructions, quantum
gates, local Yang--Baxter correspondences, and adjacent n-ary structures; it
does not change that result.

## Broader exact-source search

Exact title, arXiv-identifier, terminology, and displayed-identity searches
also inspected retrieved full sources in the following nearby lanes:

- deformations through n-Lie algebra cohomology;
- Clifford-algebra solutions of Yang--Baxter, tetrahedron, and higher simplex
  equations;
- Majorana-fermion and unitary tetrahedron gates;
- formal-language constructions for quasicrystals;
- local Zamolodchikov tetrahedron equations;
- universal-algebra approaches to set-theoretic Yang--Baxter equations;
- local Yang--Baxter correspondences and Lax constructions.

Where Bardakov et al. appeared, it appeared bibliographically.  Searches for
`T_2-groupoid`, `second tetrahedral 4-groupoid`, `elementary 2-solution`, and
the reconstruction identity found no proposed answer.

## Mathematical result under audit

The `Fin 3` finalist-one operation satisfies the tetrahedron equation, has
bijective elementary map, satisfies every extraction hypothesis at every
basepoint with the identity unary map, and yields all five T2-groupoid laws.
Every admissible unary map is forced to be the identity, while reconstruction
fails for every basepoint.

The stronger raw theorem states that, in the middle-injective finalist-one
class, reconstruction through one basepoint is equivalent to
`T(x,y,z)=y`.  Thus every nonprojection member supplies a counterexample.  An
orbit-label theorem identifies the obstruction as failure of basepoint
factorization

\[
\kappa(A,B)=\kappa(A,C)\kappa(C,B)
\]

under diagonal identity and a faithful action.

## Claim boundary

Supported after kernel replay and this bounded audit:

- an explicit three-element counterexample;
- a negative answer to preprint Question 9.12 / published Question 9.69;
- a raw no-go theorem for reconstruction in the middle-injective finalist-one
  subclass;
- the exact orbit-label obstruction inside the orbit-action representation.

The independent definition map and convention result are recorded in
`t2_reconstruction_convention_audit.md`.

Not supported by this audit:

- novelty of differential modes or their orbit decomposition;
- classification of all elementary 2-solutions or all T2-groupoids;
- a claim that no unrelated T2-groupoid presentation can generate the same
  ternary operation;
- global priority without author or subject-expert review.
