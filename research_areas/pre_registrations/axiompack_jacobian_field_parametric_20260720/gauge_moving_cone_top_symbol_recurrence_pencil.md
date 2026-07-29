# Associated-graded recurrence for the moving cone source shell

**Status:** preregistered before symbolic top-shell extraction

## Eigenquestion

The exact cone-valued moving-contact solutions currently have minimum
source-component degrees

\[
(5,5,7,9,11)
\]

at instantaneous orders \(j=0,\ldots,4\).  At \(j=2,3,4\), the system with
source cap \(2j+2\) is inconsistent by one rank.  Is this the finite shadow
of one associated-graded source obstruction forcing

\[
\deg V_j\ge 2j+3\qquad (j\ge2)?
\]

## Candidate mechanism

Use source coordinates

\[
V=v,\qquad G=t-\frac32v,\qquad \gamma=1+G.
\]

For each instantaneous order:

1. take the top homogeneous shell of the residual contact equation;
2. retain the complete cone-valued target window, rather than a selected
   representative;
3. compute the associated-graded image of strict, weighted-area-preserving
   source fields of degree at most \(2j+2\);
4. quotient by the associated-graded target image;
5. identify the dual functional that survives.

The finite solutions indicate a two-dimensional top source shell spanned by

\[
U_m=
\left(\frac{m+2}{2}V^mG^{m-1},
      -\frac m2V^{m-1}G^m\right),
\qquad
W_m=
\left(V^mG^{m-3},-V^{m-1}G^{m-2}\right).
\]

This span is orientation only.  A recurrence must be derived from the
contact equation or its dual module; fitting the displayed coefficients is
disallowed.

## Attack vectors and kill conditions

1. **Shifted cokernel.**  Normalize the nonzero left-kernel evaluation at
   caps \(6,8,10\) for \(j=2,3,4\) using semantic row labels.

   **Kill:** the supports do not agree after the predicted order shift, or
   an enlarged complete target window removes the evaluation.

2. **Top-shell operator.**  Derive the source associated-graded map in
   \((V,G)\) coordinates and compute its image on a general homogeneous
   strict weighted-area field.

   **Kill:** lower shells feed the proposed top quotient, so no triangular
   associated-graded reduction exists.

3. **Moving residual recurrence.**  Extract the highest homogeneous part of
   the exact family derivative and all lower-order transport terms.

   **Kill:** the surviving dual evaluation vanishes at some symbolic order
   or depends on unconstrained lower affine parameters.

4. **Instantaneous-to-logarithmic transfer.**  Only after an instantaneous
   lower bound is proved, check whether lower-order commutators can cancel
   its top source shell in the source Magnus logarithm.

   **Kill:** the logarithmic triangular map has an independent contribution
   in the same degree that cancels the instantaneous obstruction.

## Success criterion

An exact symbolic formula for the dual evaluation, nonzero for every
\(j\ge2\), plus a triangular filtration argument proving
\(\deg V_j\ge2j+3\).  A claim about the symmetric contact-complexity
statistic additionally requires the logarithmic transfer in item 4.

## Intended verification surface

The mathematical derivation comes first.  Exact symbolic replay should then
instantiate several orders and compare semantic cokernel supports.  LeanMill
should receive only the finite-dimensional arithmetic or recurrence spine
that can be stated without importing an unformalized power-series category.

## First symbolic extraction: the proposed recurrence changes category

Put \(r=VG\).  The top homogeneous seed map is

\[
\overline P=-3r^2,\qquad \overline Q=-2r^3.
\]

For a weighted-area-preserving source field \(Z=(A,B)\), its top action on
the seed depends only on

\[
dr(Z)=GA+VB.
\]

The displayed source-shell vectors satisfy

\[
dr(U_m)=r^m,\qquad dr(W_m)=0.
\]

Thus \(U_{j+2}\) supplies the transverse top source direction at component
degree \(2j+3\); \(W_{j+3}\) is tangent to the top cusp and is determined by
the next seed shell.  This explains the observed two-dimensional top source
span without fitting its coefficients.

The decisive counterattack is on the target side.  At cusp weight \(w\),
the cone monomials are

\[
\mathcal E_w=
\{(a,b)\in\mathbb N^2:2a+3b=w,\ b\ge1,\ a\le2b\}.
\]

For \(h_{a,b}=X^aY^b\), the Hamiltonian field restricted to
\((X,Y)=(r^2,r^3)\) has top coefficient vector

\[
J_w(a,b)=\left(-\frac b2,\frac a3\right)
\]

against \((r^{w-3},r^{w-2})\).  Two distinct solutions of
\(2a+3b=w\) differ by \((3,-2)\).  Consequently

\[
\det\!\begin{pmatrix}
-b/2 & -(b-2)/2\\
a/3 & (a+3)/3
\end{pmatrix}
=-\frac{2a+3b}{6}
=-\frac w6\ne0.
\]

Therefore:

\[
\operatorname{rank}J_w=
\begin{cases}
1,&|\mathcal E_w|=1,\\
2,&|\mathcal E_w|\ge2.
\end{cases}
\]

The exact cone counts begin

\[
\begin{array}{c|rrrrrrrrrrr}
w&6&7&8&9&10&11&12&13&14&15&16\\ \hline
|\mathcal E_w|&1&1&1&1&1&1&2&1&2&2&1.
\end{array}
\]

Moreover \(|\mathcal E_w|\ge2\) for every \(w\ge17\).  A six-residue proof
chooses the two adjacent solutions listed below, with \(w=6k+\rho\):

\[
\begin{array}{c|c|c|c}
\rho&(a,b)&(a+3,b-2)&\text{first admissible }w\\ \hline
0&(0,2k)&(3,2k-2)&12\\
1&(2,2k-1)&(5,2k-3)&19\\
2&(1,2k)&(4,2k-2)&14\\
3&(0,2k+1)&(3,2k-1)&15\\
4&(2,2k)&(5,2k-2)&22\\
5&(1,2k+1)&(4,2k-1)&17.
\end{array}
\]

For the consecutive range \(17\le w\le22\), each residue is already at or
above its row threshold; adding six preserves both cone inequalities.

### Consequence for the finite cokernels

The codimension-one failures through \(j=4\) occur at top weights
\(w=j+6\le10\), exactly where the cone has a single target symbol.  The same
mechanism predicts a one-line top quotient at \(w=11,13,16\), but it cannot
produce an all-order lower bound: at \(w=12,14,15\) and every \(w\ge17\),
the cone target symbols already span both top cusp directions.

Hence the candidate statement

\[
\deg V_j\ge2j+3\quad\text{for every }j\ge2
\]

is rejected at the associated-graded level.  The finite pattern was a
low-weight Apéry phenomenon.

### New theorem candidate

The replacement mechanism is eventual target-symbol surjectivity:

\[
J_w(\mathfrak c_w)=
\mathbb Q\,r^{w-3}\oplus\mathbb Q\,r^{w-2}
\qquad(w\ge17).
\]

If the complete moving contact equation is triangular for the corresponding
filtration, every high-weight residual can be removed by a cone-valued
target Hamiltonian, leaving source corrections only in the finite exceptional
weights

\[
\{6,7,8,9,10,11,13,16\}.
\]

### First exact phase-transition check

The complete-affine moving replay now reaches weight twelve.  Its two cone
symbols lower the first consistent source cap from the extrapolated fifteen
to fourteen.  The comparison parity section, with one weight-twelve symbol,
remains inconsistent at cap fourteen and first passes at fifteen.  Exact
ranks and primitive duals are in
[`gauge_moving_sections_extended_result.md`](gauge_moving_sections_extended_result.md).

This confirms the predicted failure of the low-weight one-line recurrence
at its first multiplicity jump.  It does not yet prove the triangular
all-order lifting statement in the preceding paragraph.

That triangular lift is now the main gate.  It could replace the apparent
source slope two by a bounded exceptional source correction.  The symbol
rank theorem alone does not establish that lift or a value of the symmetric
contact statistic.

## Kernel verification

The arithmetic carrier is
[`AxiomPackJacobianConeSymbolSurjectivityArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianConeSymbolSurjectivityArithmetic.lean).
It proves:

- adjacent fixed-weight solutions have equal cusp weight;
- their exponent determinant is exactly minus that weight;
- every weight \(w\ge17\) has two cone solutions with nonzero determinant.

The targeted Lean build passes.  Provider-free LeanMill ratification used
zero provider calls and closed
`AxiomPackJacobianConeSymbolSurjectivityArithmetic.cone_symbol_surjectivity_arithmetic_terminal_certificate`
with:

- governed closure SHA-256
  `4838e2e0301ffd0554b06688963a9ad5d5c97c1a0025d7098ce1eaa336539053`;
- closure-record SHA-256
  `a2b2a9bba57f4bc0ff97260df27846a22850fe47f0b70061c1a20ff6b4ce8634`;
- kernel-parity SHA-256
  `416ff837e0d1bee1ba6f860078fcae3ff674692cb01b6dcdc97226c4ee1f54e7`;
- matched negated-conclusion control, target identity, statement integrity,
  governance, and axiom allowlist all passed.

The governed closure is
[`AxiomPackJacobianConeSymbolSurjectivityArithmetic.cone_symbol_surjectivity_arithmetic_terminal_certificate_4838e2e0301f.lean`](../../../ztare_proofs/closures/AxiomPackJacobianConeSymbolSurjectivityArithmetic.cone_symbol_surjectivity_arithmetic_terminal_certificate_4838e2e0301f.lean).
