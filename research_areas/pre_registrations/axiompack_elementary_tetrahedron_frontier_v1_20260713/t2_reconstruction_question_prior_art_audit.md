# T2 reconstruction question: prior-art and forward-citation audit

Date: 2026-07-15

## Verdict (corrected 2026-07-17)

The AxiomPack finalist-one witness gives a kernel-checked negative answer to a
printed question, and the independent convention audit still passes. A broad
priority claim for the counterexample or negative answer is now excluded.

The first audit searched forward citations, reconstruction terminology, and
the displayed identity. Target-conditioned consequence replay found the missed
route: known associative-ring tetrahedron maps already fail the published
reconstruction after its extraction definitions are applied. Igonin proves
that, on any associative ring,

\[
(X,Y,Z)\longmapsto(X,Y+XMZ,Z)
\]

is a tetrahedron map. With `M=1`, basepoint zero, and identity unary map, its
extracted operations reconstruct `Y`, while the original middle coordinate is
`Y+XZ`. The two disagree whenever `XZ` is nonzero. The scalar family
`(x,(y-xz)/k,z)` is also explicit in the earlier tetrahedron-map literature.

These sources do not appear to state the consequence for Question 9.12/9.69,
but the consequence is immediate. Remaining priority candidates are narrower:
the exact extraction-fiber characterization, the associativity-plus-centroid
iff for the enlarged affine family, and its additive-conjugacy criterion.
None has a confirmed priority verdict. The pointed two-element classification
and minimality statement is excluded by Sadykov's complete two-color catalogue.

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

This paragraph is limited to works citing Bardakov et al. It does not exclude
older construction families that predate the printed question; those are the
source of the consequence-replay correction below.

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

### Consequence-replay correction

The terminology search was insufficient because the relevant earlier sources
do not use Bardakov's later extraction vocabulary. Directly replaying the
target predicate against their examples changes the result:

- S. Igonin,
  [Set-theoretical solutions to the Zamolodchikov tetrahedron equation on
  associative rings and Liouville integrability](https://arxiv.org/abs/2203.05552),
  Theorem 1, gives `(X,Y,Z) -> (X,Y+XMZ,Z)` on associative rings.
- S. Konstantinou-Rizos,
  [Birational solutions to the set-theoretical 4-simplex
  equation](https://arxiv.org/abs/2211.16338), equation (17), records the
  scalar tetrahedron map `(x,y,z) -> (x,(y-xz)/k,z)` and traces it to the
  Kashaev--Korepanov--Sergeev lane.
- R. M. Sadykov,
  [Set-theoretical solutions of the tetrahedron equation](https://arxiv.org/abs/1504.03314),
  gives a complete two-color catalogue containing the identity, `y+xz`, and
  its color-complement presentation. The campaign's pointed Boolean dichotomy
  is a filtered corollary of that catalogue.

Both yield reconstruction failures by elementary substitution into the later
extraction formulas. Future literature audits for construction/reconstruction
questions must run retrieved example families through the target predicate,
in addition to coordinate fingerprints and terminology searches.

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

Supported after kernel replay and the corrected audit:

- an explicit three-element kernel witness discovered independently by the
  AxiomPack campaign;
- a valid negative answer to preprint Question 9.12 / published Question 9.69,
  without a priority claim;
- a raw no-go theorem for reconstruction in the middle-injective finalist-one
  subclass;
- the exact orbit-label obstruction inside the orbit-action representation;
- the diagnosis that known associative-ring examples already imply the same
  negative answer under consequence replay.

The independent definition map and convention result are recorded in
`t2_reconstruction_convention_audit.md`.

Not supported by this audit:

- novelty of differential modes or their orbit decomposition;
- classification of all elementary 2-solutions or all T2-groupoids;
- a claim that no unrelated T2-groupoid presentation can generate the same
  ternary operation;
- priority for the counterexample or broad negative answer;
- priority for the narrower extraction-fiber, affine-iff, or
  additive-conjugacy statements without author or subject-expert review;
- priority for the pointed two-point classification or minimality statement.
