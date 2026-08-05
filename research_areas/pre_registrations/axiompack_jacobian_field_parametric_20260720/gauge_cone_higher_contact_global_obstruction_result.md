# No finite higher-contact prefix escape

## Claim boundary

Every nonzero finite polynomial target prefix of positive \(C\)-adic contact
depth forces an unbounded source Magnus logarithm.  Combined with the complete
one-\(C\) classification, this excludes every nonzero finite cone-compatible
contact prefix.

The initially proposed uniform \(d=0\) leading row was false.  The conclusion
uses the corrected state-dependent offsets, five factored amplitudes, fifth-
depth heldouts, and corrected transition graph below.  An infinite
coefficientwise-finite \(C\)-adic schedule remains outside the result.  The
radial construction still supplies \(\sigma_{\rm ct}\le2\), while the
unrestricted matching lower bound remains open.

## Contact valuation

Put \(r=uz\).  The exact seed pullbacks are

\[
\begin{aligned}
P_0&=-\frac34r^2+r+\frac z2,\\
Q_0&=-\frac14r^3+\frac14r^2+\frac14rz,\\
C(P_0,Q_0)
&=\frac{z^2}{16}
  \left(-9r^2+12r+8z-4\right).
\end{aligned}
\]

At \(z=0\), elimination of \(r\) gives

\[
\operatorname{Res}_r(P-P_0,Q-Q_0)
=\frac1{64}
\left(4P^3-P^2-18PQ+27Q^2+4Q\right).
\]

Hence the kernel of the cusp-axis pullback is exactly \((C)\).  Since
\(C(P_0,Q_0)/z^2\) is a unit in \(\mathbb Q(r)[[z]]\),

\[
\boxed{\nu_z(H(P_0,Q_0))=2\nu_C(H)}.
\]

Equivalently,

\[
\phi^{-1}\bigl((z^{2m+2})\bigr)=(C^{m+1}).
\]

This supplies the affine-stable definition of contact depth.  In
particular, two complete current solves agreeing through normal order
\(2m\) also agree at normal order \(2m+1\).  Hidden expansions of
\(C^{m+1}\) into ordinary cone monomials begin at order \(2m+2\), so
they cannot change the odd row.

## Stable cost-four transfer

Let

\[
D=4P^3+27Q^2
\]

and use the \(D\)-adic monomial basis

\[
P^aQ^bD^dC^m.
\]

In the stable range

\[
2b\ge a+3d+3m+8,
\]

complete cost-three and cost-four current normalization gives the odd
terminal

\[
\boxed{
\begin{aligned}
[u^Sz^{S+2m+1}]V_4
={}&
\left(-\frac34\right)^a
\left(-\frac14\right)^b
\left(\frac{27}{8}\right)^d
\left(-\frac9{16}\right)^{m-1}\\
&\times
\frac{6a+9b+15d+4m}{32},
\end{aligned}}
\]

where

\[
S=2a+3b+5d+2m.
\]

The coefficient is nonzero.  The \(15d\) term corrects the preregistered
\(18d\) prediction: the transfer sees the source radial valuation five
of \(D\), after its weight-six leading cancellation.

The exact quadratic identity certificate uses fifteen unisolvent
\((a,b,d,m)\) rows.  Every quadratic and mixed coefficient vanishes, and
three independent held-outs agree with

\[
-\frac{6a+9b+15d+4m}{18}
\]

after division by the leading scale.

More invariantly, on a surviving normal-\(2m\) radial row \(r^Rz^{2m}\)
the first odd transfer is diagonal:

\[
\boxed{\mathcal T_m(r^Rz^{2m})
=-\frac{3R-2m}{18}r^Rz^{2m+1}.}
\]

Its eigenvalue cannot vanish for a nonconstant positive-contact source
symbol.

## Boundary rows and affine cancellation

At contact level \(j\), the complete leading current weights are

\[
S_0=\{w\ge5\},
\]

\[
S_{2k}=\{9k,9k+3\}\cup\{w\ge9k+5\},
\]

and

\[
S_{2k+1}
=\{9k+6,9k+8,9k+9\}\cup\{w\ge9k+11\}.
\]

Write the cone slack as

\[
\ell=2b-a-3d-3m.
\]

The stable odd formula extends directly through \(\ell\ge4\).  The
twelve boundary residues have

\[
a\in\{0,1,2\},\qquad \ell\in\{0,1,2,3\}.
\]

For every \(d\ge1\), exact quadratic certificates give a nonzero odd
corner with normalized coefficient

\[
-\frac{21a+57d+35m+9\ell}{36}.
\]

At \(d=0\), seven states retain that odd corner.  The exceptional set is

\[
\mathcal E
=\{(0,0),(0,1),(0,2),(0,3),(1,0)\}.
\]

Those five states have a primary even terminal and a nonresonant
\(\phi_2\) orbit.  A full-residual audit falsifies the initially proposed
uniform primary location.  The corrected radial offsets are

\[
\delta_{0,0}=2,\quad
\delta_{0,1}=\delta_{0,2}=\delta_{0,3}=1,\quad
\delta_{1,0}=2,
\]

so the primary key is \((S+\delta_{a,\ell},2m)\).  After division by the
common leading scale, its amplitude is

\[
\begin{array}{c|c}
(a,\ell)&\text{normalized amplitude}\\ \hline
(0,0)&m(81m-46)/256\\
(0,1)&(3m+1)(153m^2+114m+73)/256\\
(0,2)&(3m+2)(153m^2+192m+112)/256\\
(0,3)&3(m+1)(153m^2+270m+169)/256\\
(1,0)&-(m+1)(81m+127)/256.
\end{array}
\]

Every displayed primary is the unique northeast corner.  Four
same-parity depths determine each degree-at-most-three law and a fifth
depth agrees; none has a zero at an admissible positive \(m\).

The corrected adjoint multiplier is

\[
2m\delta_{a,\ell}+2k(S-m)>0
\qquad(k\ge0).
\]

A direct cancellation by
\(P^{a'}Q^{b'}D^{d'}C^{j_k}\) must satisfy

\[
7a'+19d'+3\ell'
=7a+3\ell+2\delta_{a,\ell}
 +k(7a+3\ell+11).
\]

The corrected residue graph has no edge from exceptional \(d=0\) back
into exceptional \(d=0\): every cancellation has \(d'>0\) or lands
outside \(\mathcal E\).

The corrected primary law closes finite affine combinations.  Each
polynomial target coefficient has invariant contact depth \(\nu_C\),
and a finite prefix has a maximum depth \(M\).  Cancellation at adjoint
depth \(k\) requires

\[
j_k=M+(M-1)k.
\]

For \(M>1\) and \(k\ge1\), this exceeds the prefix maximum.  For \(M=1\),
the depth is unchanged, but the transition exits \(\mathcal E\) and
meets the odd-corner obstruction.  A depth-zero cancellation also exits
immediately.

On a fixed contact and radial grade the odd transfer is scalar.
Equivalently, on the first nonzero axial multiplier coefficient it is
the Euler operator

\[
3r\frac d{dr}+4m,
\]

whose degree-\(w\) eigenvalue \(3w+4m\) is nonzero.  Equal-grade
cancellation therefore exposes the next nonzero radial symbol.  The
finite \(D\)-adic expansion must eventually reach a nonzero odd terminal
or an uncanceled boundary gap.

The same conclusion follows from complete source-factor support.  For
each of \(P_0,Q_0,D_0,C_0\), radial deficit \(t\) and extra normal order
\(h\) satisfy

\[
t\ge h\ge0.
\]

A current column containing the odd terminal therefore has a strictly
higher even-normal pivot unless its coefficient is zero.

As an adversarial finite-window check, the universal zero-start
normalizer was applied directly to combined prefixes through \(C^3\).
After exact target polynomial identities were removed, the target/source
rank pairs were

\[
(10,10),\qquad(25,25),\qquad(27,27)
\]

for the tested \(C^1,C^2,C^3\) rectangles.  Direct normalization of
mixed-contact linear combinations agreed with the corresponding column
sums.

## Magnus orbit

Write the cost-two zero letter as

\[
A_0r^Sz^{2m}
\]

and the odd cost-four terminal as

\[
B_0r^Sz^{2m+1}.
\]

For

\[
F_k
=r^{S+k(S-1)}
 z^{2m+1+2k(m-1)},
\]

the density-\(z^2\) Hamiltonian bracket gives

\[
[A_0r^Sz^{2m},F_k]
=A_0\bigl(2(S-m)k-S\bigr)F_{k+1}.
\]

The sole algebraic resonance is

\[
\frac{S}{2(S-m)}\in(0,1),
\]

so no integral adjoint factor vanishes.  The side-correct source response
is

\[
\phi_3(x)
=\frac{x}{e^x-1}\int_0^1t^3e^{t^2x}\,dt.
\]

After orbit division its positive-depth coefficients are

\[
\frac{B_{k+1}}{2(k+1)!}.
\]

Every odd depth survives.  For the displayed \(D\)-adic monomial the
limiting Hamiltonian rate is

\[
2a+3b+5d+3m-2.
\]

The first held-out higher-contact replay is \(Q^7C^2\).  It gives

\[
[u^{25}z^{30}]V_4=\frac{639}{8388608},
\qquad
[u^{49}z^{56}]V_6=0
\]

on the terminal ray, and

\[
[u^{49}z^{56}]\Omega_6
=\frac{431325}{70368744177664},
\]

exactly the bracket and \(\phi_3\) prediction.

## Replays

The certificates are:

- [`gauge_cone_higher_contact_discriminant_symbolic.py`](gauge_cone_higher_contact_discriminant_symbolic.py)
  for the four-variable transfer;
- [`gauge_cone_higher_contact_global_obstruction.py`](gauge_cone_higher_contact_global_obstruction.py)
  for contact valuation, current support, the orbit, and the response;
- [`gauge_cone_boundary_contact_classes.py`](gauge_cone_boundary_contact_classes.py)
  for the twelve slack residues, corrected exceptional amplitudes, and
  the finite-contact transition induction;
- [`gauge_cone_boundary_actual_leading.py`](gauge_cone_boundary_actual_leading.py)
  for assumption-free extraction of the five corrected leading rows;
- [`gauge_cone_boundary_cubic_heldout.py`](gauge_cone_boundary_cubic_heldout.py)
  for the three fifth-depth cubic heldouts;
- [`gauge_cone_higher_contact_combined_rank.py`](gauge_cone_higher_contact_combined_rank.py)
  for direct combined-prefix linearity and rank checks after removing
  exact target polynomial identities;
- [`gauge_cone_q7c2_covariant_source_cokernel.py`](gauge_cone_q7c2_covariant_source_cokernel.py)
  for the held-out full projected replay.
- [`AxiomPackJacobianFiniteContactPrefixArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianFiniteContactPrefixArithmetic.lean)
  for the seed identity, amplitude positivity, corrected nonresonance,
  maximum-contact inequality, and exceptional-transition exit arithmetic.

The corrected arithmetic endpoint passed carried-theorem governance, the
matched negated-conclusion control, the axiom allowlist, and kernel replay.
Its governed closure is
[`finite_contact_prefix_arithmetic_terminal_certificate_c69dbb468230.lean`](../../../ztare_proofs/closures/AxiomPackJacobianFiniteContactPrefixArithmetic.finite_contact_prefix_arithmetic_terminal_certificate_c69dbb468230.lean).
The closure-certificate record has SHA-256
`b87f811553ffc97095e63ea9c920379fc1c2828275934fc505616a9be4d4ef8a`,
and the kernel-parity record has SHA-256
`d9f9195833554b532970b6d81433eec01f9b926235f64495b456bf027eb6443f`.

The finite-prefix boundary is sharp.  The successor
[`gauge_positive_contact_locally_finite_obstruction_result.md`](gauge_positive_contact_locally_finite_obstruction_result.md)
also excludes locally finite positive-contact continuations of this
normalized background.  Replacing the contact-zero backbone remains
outside both results.

## Adversarial correction

The uniform \(d=0\) audit in
[`gauge_cone_boundary_contact_classes.py`](gauge_cone_boundary_contact_classes.py)
fails at its first exceptional full-residual row.  At

\[
(a,\ell,m,d)=(0,0,2,0)
\]

the proposed primary key \((14,4)\) is not the northeast leader: the complete
cost-four residual contains

\[
[r^{15}z^4]V_4=-\frac{2349}{524288}.
\]

This invalidated the first exceptional transition calculation and
temporarily reopened the finite-prefix argument.  The corrected audit
classifies the actual leader as
\((S+\delta_{a,\ell},2m)\), verifies all five factored amplitude laws at
a fifth same-parity contact depth, and recomputes both the bracket and
transition equations.  The corrected graph again has the five-state exit
property, now for the actual leading source quotient.
