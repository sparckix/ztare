# T2 reconstruction question: independent convention audit

Date: 2026-07-15

## Verdict

Pass.  The finite Lean counterexample uses the same operation orientation,
basepoint convention, unary inverse-slice map, extracted binary operations,
five T2-groupoid laws, and reconstruction term as published Question 9.69.
No coordinate or argument-order mismatch was found.

The public description should say **bijective elementary 2-solution**.  The
paper permits elementary set-theoretic solutions without requiring
bijectivity, whereas the formal predicate used here additionally requires the
elementary map to be bijective.  This is a stronger witness condition and does
not weaken the negative answer.

## Definition map

For the ternary operation `T`, the paper's elementary map

\[
R(x,y,z)=(x,T(x,y,z),z)
\]

is `elementaryMap T`.  The elementary type-2 simplex equation is the exact
`TetrahedronEquation` imported by the counterexample module.

For a basepoint `c` and unary map `brace`, the five assumptions of published
Proposition 9.68 are `ExtractionHypotheses T c brace`, in the published order:

\[
T(c,c,c)=c,
\quad \{T(c,x,c)\}=x,
\quad T(c,\{x\},c)=x,
\]

\[
T(\{x\},\{y\},c)=\{T(x,y,c)\},
\quad
T(c,\{x\},\{y\})=\{T(c,x,y)\}.
\]

The four extracted operations are represented without reorientation:

\[
x\star y=T(x,y,c),\qquad x\circ y=T(c,x,y),
\]

\[
x\mathbin{\lhd}y=T(c,\{x\},y),\qquad
x\mathbin{\rhd}y=T(x,\{y\},c).
\]

`T2GroupoidLaws` contains the five identities of Proposition 9.68
term-for-term.  The reconstruction asked about in Question 9.69 is

\[
x\mathbin{\rhd}(y\circ z)
=T(x,\{T(c,y,z)\},c),
\]

which is exactly `reconstructed T c brace x y z`.

## Witness checks

On `Fin 3`, the finalist-one operation is

\[
T(x,y,z)=
\begin{cases}
(0\;1)\cdot y,&x=2\text{ and }z\in\{0,1\},\\
y,&\text{otherwise}.
\end{cases}
\]

The kernel artifact verifies:

- the elementary type-2 simplex equation;
- bijectivity of `R` by proving that it is involutive;
- all five extraction assumptions for every basepoint with the identity unary
  map;
- all five extracted T2-groupoid laws;
- failure of reconstruction for every basepoint;
- uniqueness of the admissible unary map for this witness, so another choice
  of `brace` cannot repair reconstruction.

The finalist-one bridge identities are used only to shorten the proof of the
diagonal slice law.  They are separately checked on the finite operation and
are not assumptions in the terminal counterexample theorem.

## Audited artifacts

- `ztare_proofs/ZtareProofs/AxiomPackT2ReconstructionCounterexample.lean`
- `ztare_proofs/ZtareProofs/AxiomPackFinalistOneBridge.lean`
- published Proposition 9.68 and Question 9.69 in Bardakov et al.,
  *Set-Theoretical Solutions of Simplex Equations*
