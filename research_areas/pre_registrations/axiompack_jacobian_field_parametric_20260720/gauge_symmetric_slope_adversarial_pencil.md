# Adversarial symmetric contact slope

**Status:** pre-computation pencil

## Eigenquestion

For coefficientwise-polynomial formal contacts

\[
H_s\circ F_s=F_0\circ\Psi_s,
\]

is the symmetric logarithmic slope

\[
\sigma_{\rm ct}
=
\inf
\limsup_{n\to\infty}
\frac{
\max\{e(Y_n),e(X_{K_n})\}
}{n}
\]

forced to equal two, or can a noncanonical gauge redistribute the
escaping-root shell so that both sides have slope strictly below two?
Here \(e(D)=\deg D-1\).

The canonical root construction proves only
\(\sigma_{\rm ct}\le2\).  Its reciprocal root has the sharp filtered shell

\[
[s^{2k+1}]z\supset c_kP^k,\qquad c_k\ne0,
\]

whose pullback has source degree \(4k=2(2k+1)-2\).  Retained as a target
coefficient, however, \(P^k\) has ordinary degree \(k\).  Therefore this
shell costs asymptotic slope two on the source side and only one half on the
target side under the declared symmetric ordinary-degree statistic.  Any
lower-bound argument that simply identifies the escaping-root shell is
therefore incomplete.

## Candidate redistribution

At parameter order \(n\), retain target-exact top shells rather than applying
the canonical finite-root normalization greedily.  In the exceptional
coordinates, a weight-\(d=m+3\) target Hamiltonian has leading source image

\[
D_{-2dH(A,D)}^{(m)}.
\]

The image is one complete parity class in \(A\).  The first attack is to
test whether the top source shell of the root construction lies in that
class.  If it does, moving it to the target costs ordinary Hamiltonian
degree at most \(\lceil d/2\rceil\), while removing a source term whose
ordinary degree can be twice as large.

The counterattack is the opposite-parity residue.  Greedy removal can create
an infinite transverse chain at one fixed parameter order, which is
inadmissible in \(\mathbb Q[P,Q][[s]]\).  A valid redistribution must use
only finitely many target monomials in every coefficient of \(s\), leaving a
polynomial source representative.

## Three discriminators

1. **Diagonal finite-order search.**  Solve
   \[
   \partial_sF_s=X_s(F_s)+dF_sV_s
   \]
   coefficientwise with simultaneous bounds
   \[
   e(V_m)\le\lambda(m+1),\qquad
   e(X_m)\le\lambda(m+1)
   \]
   for rational candidates \(\lambda<2\).  Use the exhaustive \(C\)-normal
   target window and exact lift ideals.  A failed finite order is a
   lower-prefix obstruction for that \(\lambda\), not an asymptotic theorem.

2. **Top-shell quotient.**  Compute the associated-graded image of the
   canonical \(P^k\) and \(P^kQ\) root shells under admissible target
   Hamiltonians.  If both sharp families are target-exact with target
   ordinary degree \(o(2n)\), root sharpness cannot certify
   \(\sigma_{\rm ct}\ge2\).

3. **Polynomiality audit.**  Track the parameter valuation of every target
   correction.  A sequence of increasing target weights all carrying the
   same \(s^j\) coefficient belongs only to the target-adic completion and
   is excluded.  A slope-improving construction must have finite target
   support at each \(s\)-order.

## Success and kill conditions

A decisive slope-below-two result requires an all-order filtered contact, or
an exact recursive mechanism whose coefficientwise finiteness and BCH
closure are proved.

A lower bound of two requires a gauge-independent associated-graded class
that survives when source and target ordinary excess are charged together.
Canonical nonvanishing alone is insufficient.

The root-shell lower-bound lane is killed if its two sharp coefficient
families are target-exact at asymptotically cheaper ordinary degree.  A
particular slope-improving construction is killed by any nonpolynomial
pullback, lift-ideal failure, repeated same-order target tail, or
over-budget BCH word.

## Adversarial audit of the diagonal node obstruction

The diagonal specialization

\[
s=\tau\varepsilon^2,\qquad
(v,t)=(V,T)/\varepsilon
\]

has special fiber

\[
f_\tau(r)=
\left(\tau r^3-3r^2,\frac34\tau r^4-2r^3\right),
\qquad
r=V\left(T-\frac32V\right).
\]

For a source field whose rescaled limit exists, its image under the
special-fiber differential is a multiple of \(f_\tau'(r)\).  The determinant
with \(f_\tau'\) then removes the source term and forces

\[
K_\tau(f_\tau(r))
=-\frac14r^6+\frac{3\tau}{28}r^7+c(\tau).
\]

The two normalization points \(r_\pm=(1\pm\sqrt3)/\tau\) have the same
target image but the displayed right-hand side differs by
\(72\sqrt3/(7\tau^6)\).  This is a valid target-descent obstruction whenever
both the target Hamiltonian and the rescaled source action are defined on the
special fiber.

The main counterattack is a source field with negative
\(\varepsilon\)-valuation.  Write the scaled family as

\[
\widetilde F_\varepsilon
=f_\tau(r)+\varepsilon g_\tau(V,T)+O(\varepsilon^2)
\]

and a rescaled source field as

\[
\widetilde V_\varepsilon
=\varepsilon^{-1}U_{-1}+U_0+O(\varepsilon).
\]

If \(dr(U_{-1})=0\), the apparent pole in
\(d\widetilde F_\varepsilon\widetilde V_\varepsilon\) cancels, while
\(dg_\tau(U_{-1})\) can contribute a normal special-fiber motion.  A
limsup degree bound permits finitely many high-degree initial logarithmic
coefficients, hence permits finitely many negative Rees valuations.  The
node proof must either show that every such kernel cascade remains tangent,
or normalize the finite polar prefix without increasing the asymptotic
logarithmic slope.

The decisive audit is therefore:

1. compute \(g_\tau\) and the polynomial kernel generator of \(dr\);
2. evaluate
   \(\det(f_\tau',dg_\tau(U_{-1}))\) at the two node branches;
3. if it spans the node separation, the claimed conclusion for every
   limsup-bounded contact fails without a nonnegative-Rees hypothesis;
4. if it vanishes, continue through the first nonzero transverse layer and
   prove the vanishing is stable under all finite polar cascades.

Even if the weighted target lower bound survives, it implies only ordinary
Hamiltonian slope at least \(1/3\), since
\(4i+6j\le6(i+j)\).  It cannot by itself prove the symmetric ordinary slope
two.
