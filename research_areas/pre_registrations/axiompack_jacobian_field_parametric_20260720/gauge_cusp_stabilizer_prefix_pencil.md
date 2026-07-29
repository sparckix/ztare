# Cusp stabilizers and the finite-prefix normalization cost

**Status:** exact pencil theorem with deterministic symbolic replay; the
generic-amplitude cascade is all-order, while the full polar-prefix quotient
for the moving family remains open

## Governing object

On the diagonal Rees boundary the seed curve is

\[
C(P,Q)=4P^3+27Q^2=0,\qquad
f_0(r)=(-3r^2,-2r^3).
\]

The relevant prefix is a polynomial Hamiltonian logarithm on the target,
together with its polynomial source lift through the seed map.  Equality is
contact equality, so a target field that preserves the seed presentation may
be moved to the source.  The cost of that move must be measured after BCH;
deleting finitely many displayed coefficients is not the same operation.

The eigenquestion is:

> Can every finite cusp-stabilizer prefix be removed without increasing the
> logarithmic tail slope, so that the Rees node-separation obstruction applies
> to the remaining contact?

The answer to that unrestricted normalization statement is negative.  A
finite stabilizer prefix can be moved, but the move can create an infinite
critical BCH tail.

## Polynomial Hamiltonian stabilizers

The logarithmic derivation module of the cusp has the usual free basis

\[
E=2P\partial_P+3Q\partial_Q,\qquad
D=X_C=54Q\partial_P-12P^2\partial_Q,
\]

with

\[
E(C)=6C,\qquad D(C)=0,\qquad
\det(E,D)=-6C.
\]

This is larger than the Hamiltonian stabilizer.  In particular,
\(\operatorname{div}E=5\), whereas \(\operatorname{div}D=0\).

Let \(X_K=(K_Q,-K_P)\).  It is tangent to the cusp precisely when

\[
\boxed{K=c+C L,\qquad c\in\mathbb Q,\quad L\in\mathbb Q[P,Q].}
\]

Indeed, \(X_C(f_0(r))=18r^2f_0'(r)\).  Tangency of \(X_K\) gives

\[
0=X_C(K)(f_0(r))
  =18r^2\frac d{dr}K(f_0(r)).
\]

Thus \(K(f_0(r))\) is constant.  The kernel of
\(\mathbb Q[P,Q]\to\mathbb Q[r]\), \(P\mapsto-3r^2\),
\(Q\mapsto-2r^3\), is the principal ideal \((C)\).  The converse follows
from

\[
X_{CL}=L X_C+C X_L.
\]

On the normalization, this stabilizer acts on a target potential
\(k(r)=K(f_0(r))\) by

\[
\delta_L k
=18r^2L(f_0(r))\,k'(r).
\]

No nonzero induced action \(\delta_L\) is locally nilpotent.  If
\(L(f_0(r))\ne0\) and its highest term is \(ar^d\), then the highest term of
\(\delta_L(r^m)\) is \(18ma\,r^{m+d+1}\), and iteration never vanishes in
characteristic zero.  Consequently a polar exponential of a cusp stabilizer
that acts nontrivially on the normalization has arbitrarily deep polar terms
unless it is removed together with its paired source action.  Stabilizers in
\((C^2)\), whose first action on the reduced cusp vanishes, require the
corresponding higher normal layer and are not classified by this argument.

## An exact BCH normalization cascade

Use the campaign's first normal Hamiltonian

\[
B=-\frac{P^3+9Q^2}{36},
\qquad B(f_0(r))=-\frac14r^6,
\]

and the minimal cusp stabilizer

\[
A=C.
\]

Both satisfy the target lift conditions.  Their pullbacks through the full
seed quotient map are polynomial, satisfy both source lift ideals, and
preserve the pulled-back area form.  Their source degrees are respectively
nine and seven.  Thus the calculation occurs inside the declared
infinitesimal contact category, rather than in an ambient target algebra
with no source lift.

Put

\[
H_k=\operatorname{ad}_A^k B
\]

for the Hamiltonian bracket convention corresponding to
\([X_A,X_B]=X_{\operatorname{ad}_A B}\).  Restriction to the cusp gives

\[
\boxed{
H_k(f_0(r))
=-\frac14\,18^k(6)^{\overline k}r^{6+k}\ne0,
}
\]

where \((6)^{\overline k}=6\cdot7\cdots(5+k)\).  Each \(H_k\) is weighted
homogeneous of degree \(6+k\) for
\(\operatorname{wt}(P,Q)=(2,3)\), equivalently degree \(12+2k\) for the
Rees target weights \((4,6)\).

Now work to first order in a square-zero normal amplitude \(\mu\).  Removing
the finite stabilizer from the one-coefficient logarithm gives

\[
G_{\tau,\mu}
=\exp(-\tau X_A)\exp\bigl(\tau X_{A+\mu B}\bigr).
\]

The exact linear-in-\(\mu\) BCH logarithm is

\[
\boxed{
[\mu]\log G_{\tau,\mu}
=\sum_{k\ge0}
\frac{(-1)^k\tau^{k+1}}{(k+1)!}X_{H_k}.
}
\]

This is the standard differential of the exponential:

\[
\exp(-X)\,d\exp_X(Y)
=\frac{1-e^{-\operatorname{ad}_X}}
       {\operatorname{ad}_X}Y.
\]

At order \(n=k+1\), the Hamiltonian weight is

\[
12+2k=2n+10.
\]

Hence every term lies on the critical target Rees face.  The original
logarithm has only one parameter coefficient and therefore zero tail; moving
the finite cusp stabilizer creates an infinite critical tail.

There is also an ordinary-degree consequence that does not require knowing
the exact monomial support.  A nonzero polynomial homogeneous of
\((2,3)\)-weight \(6+k\) has ordinary degree at least
\(\lceil(6+k)/3\rceil\).  Therefore the Hamiltonian derivation excess in
the displayed BCH tail has asymptotic slope at least

\[
\liminf_{k\to\infty}
\frac{\lceil(6+k)/3\rceil-2}{k+1}
=\frac13.
\]

Thus a proof of an unrestricted ordinary tail bound below \(1/3\) cannot
simply quotient finite cusp-stabilizer prefixes: the quotient operation can
itself pay the entire \(1/3\) rate.

## Generic nonlinear amplitude

The square-zero calculation also determines the cascade over the rational
function field, without discarding nonlinear normal insertions.  Write

\[
\Omega(\tau,\mu)
=\log\left(\exp(-\tau X_A)
           \exp(\tau X_{A+\mu B})\right)
=\sum_{n\geq1}\tau^n X_{\Omega_n(\mu)}.
\]

At each fixed order, the universal BCH formula makes
\(\Omega_n(\mu)\) a weighted-homogeneous polynomial in
\(\mathbb Q[\mu,P,Q]\).  Its linear coefficient is the differential of the
exponential computed above:

\[
\boxed{
[\mu]\Omega_n(\mu)
=\frac{(-1)^{n-1}}{n!}\operatorname{ad}_A^{\,n-1}B\ne0.
}
\]

Consequently \(\Omega_n(\mu)\) is a nonzero polynomial for every \(n\geq1\).
After base change to \(\mathbb Q(\mu)\), where \(\mu\) is an indeterminate
nonzero amplitude, no nonlinear term can cancel this coefficient:

\[
\boxed{\Omega_n(\mu)\ne0\quad\text{in }
\mathbb Q(\mu)[P,Q]\text{ for every }n\geq1.}
\]

Equivalently, every single amplitude
\(\lambda\) transcendental over \(\mathbb Q\) is simultaneously
nonexceptional at all orders: evaluation at \(\mu=\lambda\) cannot kill any
nonzero coefficient polynomial in \(\mathbb Q[\mu]\).

Every coefficient is still homogeneous of \((2,3)\)-weight \(n+5\), hence
lies on Rees weight \(2n+10\).  The ordinary Hamiltonian degree is at least
\(\lceil(n+5)/3\rceil\), so this fixed generic-amplitude logarithm has
ordinary derivation-excess liminf at least \(1/3\).

### Exact ordinary degree

The weight-only estimate can be sharpened to an equality.  Follow the
Hamiltonian flow of \(C\) from the point \((p,0)\):

\[
\dot P=54Q,\qquad \dot Q=-12P^2,\qquad
P(0)=p,\quad Q(0)=0.
\]

Write

\[
P(t)=p\,u(x),\qquad x=pt^2,\qquad
u(x)=\sum_{m\ge0}a_mx^m,\quad a_0=1.
\]

The equation \(\ddot P=-648P^2\) becomes

\[
u'+2xu''=-324u^2,
\]

and hence

\[
\boxed{
(m+1)(2m+1)a_{m+1}
=-324\sum_{i+j=m}a_i a_j.
}
\]

Induction gives

\[
(-1)^m a_m>0
\]

for every \(m\): after removing the common sign, the right-hand convolution
is a sum of positive rationals.  Every coefficient of \(u^3\) has the same
alternating sign and is therefore nonzero.

Since

\[
B=\frac{P^3-C}{108}
\]

and \(C\) is constant along its own flow, for every \(m\ge1\)

\[
\left(\operatorname{ad}_C^{2m}B\right)(p,0)
=\frac{(2m)!}{108}[x^m]u(x)^3\,p^{m+3}\ne0.
\]

Thus the maximal-ordinary-degree monomial \(P^{m+3}\) is present at every
even iterate.  For an odd iterate, weighted parity makes its unique possible
top monomial \(P^{m+2}Q\), and

\[
\left(\operatorname{ad}_C^{2m+2}B\right)(P,0)
=-12P^2
\left(\partial_Q\operatorname{ad}_C^{2m+1}B\right)(P,0).
\]

Nonvanishing of the next even iterate therefore forces the odd top
coefficient to be nonzero as well.  Including the directly checked
\(k=0,1\) cases gives

\[
\boxed{
\deg\left(\operatorname{ad}_C^kB\right)
=3+\left\lfloor\frac k2\right\rfloor
=\left\lfloor\frac{k+6}{2}\right\rfloor
\quad(k\ge0).
}
\]

At logarithmic order \(n=k+1\), the Hamiltonian vector-field excess is

\[
e\!\left(X_{\operatorname{ad}_C^kB}\right)
=\left\lfloor\frac{n+1}{2}\right\rfloor.
\]

The square-zero cascade therefore has exact ordinary slope \(1/2\).
Over \(\mathbb Q(\mu)\), the coefficient of the same top monomial is a
polynomial in \(\mu\) with the displayed nonzero linear term, so nonlinear
insertions cannot remove it.  The generic-amplitude cascade also has exact
ordinary slope \(1/2\).

This removes the nilpotent-amplitude limitation over the generic
characteristic-zero field.  Specialization to one prescribed
\(\mu\in\mathbb Q^\times\) remains a separate simultaneous-noncancellation
problem: a nonzero coefficient polynomial can vanish at an exceptional
rational amplitude.

The arithmetic spine is kernel-checked in
[`AxiomPackJacobianCuspStabilizerCascade.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianCuspStabilizerCascade.lean).
It certifies the nonzero rising-factor recurrence, the nonzero linear BCH
scalar at every order, and nonvanishing after adjoining an arbitrary
\(\mu^2\)-divisible nonlinear tail.  Provider-free LeanMill ratification
closed with zero inference calls:

- source/closure SHA-256:
  `8292a48abebc0629bd388f14e78d2004095e93e6cf9ab4442bb9c07b2b25e776`;
- kernel-parity record SHA-256:
  `988f9e6b047a48d72a8eeb7d6ecdb380d1e541c5d82a298bf608635ff28ae9df`;
- closure-certificate record SHA-256:
  `a4a6249206d139d76fe3fbd88b712ae0acd259f93f39bb8ebce34d163ba1b69d`;
- governed closure:
  [`generic_amplitude_cascade_arithmetic_terminal_certificate_8292a48abebc.lean`](../../../ztare_proofs/closures/AxiomPackJacobianCuspStabilizerCascade.generic_amplitude_cascade_arithmetic_terminal_certificate_8292a48abebc.lean).

The formal target is intentionally the arithmetic carrier.  The BCH
identification and the Hamiltonian restriction remain in the exact symbolic
replay and pencil theorem; the file does not construct the completed contact
group.

## Critical-face dexp and the node functional

Let a finite target logarithm lie on the critical face:

\[
\mathcal B_\tau(P,Q)
=\sum_n\tau^n B_n(P,Q),\qquad
\deg_{(2,3)}B_n=n+5.
\]

Under

\[
p=\tau^2P,\qquad q=\tau^3Q,
\]

it has the exact form

\[
\mathcal B_\tau(P,Q)=\tau^{-5}\,\overline B(p,q).
\]

At fixed \(P,Q\),

\[
\partial_\tau\mathcal B_\tau
=\tau^{-6}(\mathcal E-5)\overline B,
\qquad
\mathcal E=2p\partial_p+3q\partial_q.
\]

Because the Poisson bracket contributes the compensating factor \(\tau^5\),

\[
\boxed{
\operatorname{dexp}_{\mathcal B_\tau}
(\partial_\tau\mathcal B_\tau)
=\tau^{-6}
\operatorname{dexp}_{\overline B}
\bigl((\mathcal E-5)\overline B\bigr).
}
\]

If the right-hand dexp is evaluable at the scaled node
\((p,q)=(-2,1)\), it is a target function at one target point and is
therefore branch-equal.  A finite target prefix can defeat the
node-evaluability hypothesis by producing a nonterminating critical series;
it cannot be declared to equal the branch-separating class merely from its
seed-cusp restriction.

This corrects a tempting but invalid shortcut.  The iterates \(H_k(f_0(r))\)
have different values at the two normalization parameters after diagonal
substitution, but the full \(H_k\) must be evaluated on the nodal deformed
curve.  Both branches then have the identical target pair.  Dropping the
deformation terms before evaluation manufactures a false separation.

## The source-prefix counterexample and the remaining theorem

The target statement above does not annihilate polar source cascades.  The
regular source-only connection \(V_s\) already supplies an admissible
counterexample:

\[
\partial_sF_s=dF_sV_s,\qquad
\operatorname{div}(\gamma^2V_s)=0.
\]

Under the diagonal Rees scaling its source action has a pole of order six
and its principal action is exactly \(\partial_\tau f_\tau\).  It therefore
spans the node-separation class with no target Hamiltonian.  Any proposed
theorem saying that all admissible polar cascades miss the node class is
false.

The surviving bridge is a costed normalization theorem:

1. transfer every finite polar **normal** source class to a regular target
   Hamiltonian, beginning with \(B\);
2. classify the remaining cusp-stabilizer ambiguity;
3. prove the dichotomy that either the normalization preserves the declared
   subcritical tail, or its BCH cascade already pays the target lower rate.

The calculation above proves the second arm for the minimal Hamiltonian cusp
stabilizer to first order in the normal deformation amplitude.  Extending
that dichotomy to arbitrary finite source prefixes, with all nonlinear
normal terms and the full moving-family lift, is still required before
claiming an unrestricted lower bound for the campaign's logarithmic
minimax.

## Claim boundary

Established here:

- exact classification of polynomial Hamiltonian cusp stabilizers;
- absence of a nonzero locally nilpotent action on the cusp normalization;
- an admissible seed contact pair \(A=C\), \(B=-(P^3+9Q^2)/36\);
- a nonzero all-order BCH cascade after removing \(A\);
- a nonzero all-order nonlinear cascade over \(\mathbb Q(\mu)\);
- critical weighted slope and exact ordinary \(1/2\) rate for the
  square-zero component and for the generic-amplitude cascade;
- exact critical-face dexp scaling and branch equality whenever evaluation
  exists;
- the regular source-only connection as a counterexample to polar-cascade
  annihilation.

Not established:

- a prescribed fixed-rational-amplitude nonlinear BCH lower bound after
  cancellations among two or more normal insertions;
- removal of every finite source prefix;
- the unrestricted ordinary logarithmic minimax;
- historical priority.
