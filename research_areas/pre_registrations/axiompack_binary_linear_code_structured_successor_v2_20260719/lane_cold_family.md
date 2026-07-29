---
description: "PATTERN-014 cold mathematical orientation for finite structured binary-code families."
---

# Cold family lane for binary `[50,20,14]`

Date: 2026-07-19

Lane: `PATTERN-014 / theory-building cold shot`

Status: mathematical orientation only. This lane selects and implements no
campaign family.

## Boundary recovered from the controls

The predecessor supplied three exact controls: the quasicyclic
`[50,20,13]` code, its even `[51,20,14]` parity extension \(D\), and a
rank-20 distance-12 perturbation. Its six campaign-qualified proposals had
distances `12,12,12,10,11,12`. Thus the live residual is construction-family
identity, not another matrix proposal. A null below is only a result about the
byte-frozen family; discovery, exact verification, kernel ratification, and
priority remain separate statuses.

The following families are finite before any target query. In each case the
authoring organ must emit the family bytes and the independent reviewer must
accept the identity, extent, quotient, and lowering before enumeration.

## Ranked families

### 1. High-transition one-generator \(2\)-quasicyclic graph family

This is the most informative cold candidate because it changes the module
presentation rather than perturbing the published five-block seed.

Let

\[
R=\mathbf F_2[x]/(x^{25}-1),\qquad g=1+x^5.
\]

For a phase tuple \(\phi=(\phi_0,\ldots,\phi_4)\in(\mathbf Z/5)^5\), set

\[
a_\phi(x)=\sum_{r=0}^4
\left(x^{r+5\phi_r}+x^{r+5(\phi_r+2)}\right)\in R.
\]

The code is the graph

\[
C_\phi=\{(g f,\,g f a_\phi): f\in\mathbf F_2[x],\ \deg f<20\}
\subseteq\mathbf F_2^{25}\times\mathbf F_2^{25}.
\]

- **Finite domain.** Start with all \(5^5=3125\) phase tuples and quotient by
  \(a\mapsto x^t a\), \(t\in\mathbf Z/25\), which is a cyclic permutation of
  the second 25-coordinate block. Take the lexicographically least 25-bit
  support mask in each orbit. The action is free: a nonzero multiple-of-five
  shift cannot stabilize a two-point subset of a five-cycle, and invariance
  under any other shift would imply such invariance after taking its fifth
  power. Hence the canonical domain has exactly \(3125/25=125\) members.
- **Lowering.** Emit the \(20\times50\) binary matrix whose row \(i\),
  \(0\le i<20\), is the coefficient vector of
  \((x^i g,\,x^i g a_\phi)\) modulo \(x^{25}-1\). The first 25-coordinate
  block proves rank 20: multiplication by \(g\) is injective on polynomials of
  degree below 20. Each generator row has weight \(2+20=22\), since the chosen
  two separated points in every five-cycle give four transitions under
  multiplication by \(1+x^5\). Moreover the fixed message
  \(f=1+x^{10}\) gives first-block weight 4 and second-block weight 10:
  on each five-cycle,
  \((1+y+y^2+y^3)(1+y^2)=y+y^4\) modulo \(y^5-1\). Thus every
  member has an explicit weight-14 word. The family is tuned to the target
  boundary, and exact success is precisely the absence of any smaller word.
- **Information value.** A rejection exposes cancellation among cyclic-module
  shifts after the one-row obstruction has been designed away. The low-weight
  messages partition the next move into a richer multiplier grammar versus a
  different module ideal. A survivor directly supplies the target matrix.
- **Decisive kill.** Kill the family only after all 125 canonical parameters
  lower deterministically and each exact replay supplies a nonzero message of
  weight at most 13. A uniform algebraic bound producing such a message for
  every phase tuple is an even stronger family kill. Reject the family at
  review time if a certified coordinate-equivalence audit collapses all 125
  members to one code.

### 2. Pair-fold descendants of the reviewed `[51,20,14]` code

Write the 51 coordinates of \(D\) as five quasicyclic blocks
\(B_0,\ldots,B_4\cong\mathbf Z/10\) plus the parity coordinate \(\infty\).
The known simultaneous block shift \(\sigma\) has order 10 and fixes
\(\infty\).

- **Finite domain.** Use unordered coordinate pairs modulo \(\langle
  \sigma\rangle\). A canonical domain consists of: five pairs
  \(\{\infty,(b,0)\}\); 25 within-block pairs indexed by
  \(b\in\{0,\ldots,4\}\) and cyclic separation
  \(\delta\in\{1,\ldots,5\}\); and 100 cross-block pairs indexed by
  \(b<c\) and relative offset \(\delta\in\mathbf Z/10\). Its exact
  cardinality is \(5+25+100=130\). These representatives cover all
  \(\binom{51}{2}=1275\) pairs under the certified shift.
- **Lowering.** For a pair \(\{p,q\}\), replace generator columns
  \(d_p,d_q\) by the single column \(d_p+d_q\), retain the other 49 columns,
  and put the sum column in a fixed canonical position. This is the linear
  fold \((z_p,z_q)\mapsto z_p+z_q\). Its kernel on the ambient space is
  spanned by the weight-two vector \(e_p+e_q\), so its restriction to \(D\)
  is injective and every lowered matrix has rank 20.
- **Information value.** Because \(D\) is even, a fold lowers a word's weight
  by exactly two only when both selected coordinates lie in its support.
  Therefore the descendant has distance 14 exactly when no weight-14 support
  of \(D\) contains the chosen pair; otherwise the supplied minimum word
  becomes a weight-12 counterexample. The run measures the complete
  two-shadow of the minimum-support geometry and can solve the target in the
  same pass.
- **Decisive kill.** Kill all 130 members by giving, for every pair orbit, a
  weight-14 word of \(D\) containing that pair; its folded image is the exact
  low-weight witness. The quotient must be checked against the carried
  quasicyclic shift. Further equivalences may remove duplicate work but may
  not delete a shift orbit without a bound equivalence witness.

### 3. Symmetry-quotiented punctures of the reviewed extension

This is the cheapest control family and the least informative of the three.

- **Finite domain.** Under the same certified order-10 shift, the 51
  coordinates have six orbits. Use the six canonical punctures
  \(\infty,(0,0),(1,0),\ldots,(4,0)\).
- **Lowering.** Delete the selected column from the carried generator of
  \(D\). Rank remains 20 because a rank drop would give \(D\) a word supported
  on the deleted coordinate, contradicting distance 14.
- **Information value.** The puncture at \(\infty\) reconstructs the known
  distance-13 control. Each other orbit asks whether the minimum words omit an
  entire coordinate orbit, in which case that puncture has distance 14.
- **Decisive kill.** For every one of the six coordinate orbits, exhibit a
  weight-14 word of \(D\) that is nonzero on the representative; puncturing it
  gives a weight-13 counterexample. Admit this as a campaign family only if a
  pre-enumeration invariant certifies at least two inequivalent punctured
  descendants. If all six are one equivalence class, retain one as a control
  and reject the family as tautological.

## Explicit exclusions

- Reject \(UGP\) families obtained only by row-basis changes
  \(U\in\mathrm{GL}_{20}(2)\) and coordinate permutations \(P\). They are one
  code-equivalence orbit, regardless of the apparent parameter count.
- Reject cyclic shifts, block rotations, or polynomial-unit multiples of one
  seed unless they are quotiented before enumeration and the remaining family
  contains more than one certified equivalence class.
- Reject Hamming balls of arbitrary bit toggles around any prior generator,
  random systematic matrices, and a list of hand-authored rows relabelled as a
  grammar. Those repeat the predecessor's raw-matrix channel. A polynomial
  mask is not sufficient structure when its only semantics is which matrix
  bits to flip.
- Reject sampled subdomains and any family whose canonical cardinality exceeds
  the frozen execution budget without a new pre-registration.

## Recommendation without selection

If AxiomPack independently authors one of these families, rank the
high-transition \(2\)-quasicyclic graph family first: it has a compact exact
domain, automatic rank, an intentionally removed one-row obstruction, and a
failure geometry that points to the next multiplier or module identity. Rank
the pair-fold family second for its exceptionally sharp minimum-support
incidence test, and the puncture family third as a cheap derived-code control.
This cold lane does not choose the host campaign's family and supplies no
matrix, polynomial instance, Lean artifact, or executable lowerer.
