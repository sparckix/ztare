# Target-control quotient of the exceptional-divisor connection

**Status:** exact pencil result; historical priority not assessed

## Eigenquestion

Does the Bernoulli--Witt degree cascade in the source-only connection survive
regular polynomial Hamiltonian target gauges?

For the normalized family \(F_s=(P_s,Q_s)\), write

\[
V_s^{(0)}=(dF_s)^{-1}\partial_sF_s.
\]

For a target Hamiltonian \(K_s(P,Q)\), with

\[
X_{K_s}=(\partial_QK_s,-\partial_PK_s),
\qquad
W_{K_s}=(dF_s)^{-1}(X_{K_s}\circ F_s),
\]

the source velocity in the corresponding contact decomposition is

\[
V_s^{K}=V_s^{(0)}-W_{K_s}.
\]

This sign is fixed directly by

\[
\partial_sF_s=X_{K_s}(F_s)+dF_sV_s^K.
\]

## Local normal form

Put

\[
g=\gamma=1-\frac32v+t,\qquad y=2v+3.
\]

Near \(g=0\), the exact family has

\[
P_s=gA_s(y)+O(g^2),\qquad
Q_s=g^2D_s(y)+O(g^3),
\]

where, with

\[
\begin{aligned}
L&=3s^2y-5s^2-48y,\\
M&=3sy-5s-12y+12,\\
N&=3s^2y-5s^2+8s-48y-48,
\end{aligned}
\]

one has

\[
A=-\frac{L}{48},\qquad
D=-\frac{MN}{16(s-6)^2(s-4)}.
\]

The leading Jacobian identity is especially rigid:

\[
AD'-2A'D=\frac12.
\]

This is the \(g^2\)-coefficient of the exact determinant identity
\(\det dF_s=-g^2\), after changing from \((v,t)\) to \((g,y)\).

## Complete Hamiltonian control image on \(g=0\)

The target lift ideals are

\[
\dot P\in(P,Q),\qquad \dot Q\in(Q,P^2).
\]

For an arbitrary polynomial Hamiltonian satisfying those ideals, write its
relevant low jets as

\[
K=\alpha PQ+\frac{\beta}{2}Q^2+\frac{\chi}{3}P^3+\cdots
\]

and use the normal weights

\[
\operatorname{wt}(P)=1,\qquad \operatorname{wt}(Q)=2.
\]

After substitution into \(F_s\), the lift ideals give

\[
\partial_QK(F_s)=\alpha gA+O(g^2)
\]

and

\[
-\partial_PK(F_s)
=g^2(-\alpha D-\chi A^2)+O(g^3).
\]

Thus only \(\alpha\) and \(\chi\) enter the equations determining the
divisor tangent field.  The \(Q^2\) coefficient and every other allowed
monomial occur beyond those two displayed leading terms.

Write a polynomial pullback near the divisor as

\[
W_K(g)=gr+O(g^2),\qquad W_K(y)=h+O(g).
\]

The two leading equations are

\[
Ar+A'h=\alpha A,
\]

and

\[
2Dr+D'h=-\alpha D-\chi A^2.
\]

Using \(AD'-2A'D=1/2\) gives the complete restriction formula

\[
\boxed{h=-6\alpha AD-2\chi A^3.}
\]

The \(Q^2\) coefficient and all the omitted jets vanish under restriction.
Conversely, the \(PQ\), \(P^3/3\), and \(Q^2/2\) target fields all have
polynomial pullbacks through the full \(F_s\), so the displayed image is
attained.

Define

\[
H_{11}=-6AD
  =-\frac{LMN}{128(s-6)^2(s-4)}
\]

and

\[
H_3=-2A^3=\frac{L^3}{55296}.
\]

Then the complete divisor control image is

\[
\mathcal C_s
=\operatorname{span}_{\mathbb Q(s)}
  \{H_{11}\partial_y,H_3\partial_y\}.
\]

The identity

\[
H_{11}
+\frac{432}{(s-6)^2(s^2-16)}H_3
=\frac{L}{2(s^2-16)}
\]

shows more transparently that

\[
\mathcal C_s
=\operatorname{span}_{\mathbb Q(s)}
  \{L\partial_y,L^3\partial_y\}.
\]

## Exact regular normal form

Let \(f_s(y)\partial_y\) be the restriction of the source-only connection.
Exact reduction gives

\[
f_s=a(s)H_{11}+b(s)H_3+c(s),
\]

where

\[
a(s)=\frac{2s}{s^2-16},
\]

\[
b(s)=
\frac{288(s^2-12s+16)}
{(s-6)^3(s^2-16)^2},
\]

and

\[
c(s)=\frac{160s}{3(s^2-16)^2}.
\]

All denominators are units in \(\mathbb Q[[s]]\).  Choose the instantaneous
target Hamiltonian

\[
\boxed{
K_s
=a(s)PQ+\frac{b(s)}3P^3-\frac14Q^2.
}
\]

At the special fiber,

\[
K_0=-\frac{P^3}{36}-\frac{Q^2}{4},
\]

so this is the fixed first-order target normalization

\[
X_{K_0}=(-Q/2,P^2/12).
\]

The \(Q^2\) pullback has zero divisor restriction.  Off the divisor it is
needed for the identity-normalized source condition

\[
V_0^K=0
\]

on the full affine source.

The resulting divisor connection is the translation field

\[
\boxed{
\left.V_s^K\right|_{g=0}
=\frac{160s}{3(s^2-16)^2}\partial_y.
}
\]

The three elementary pullbacks are polynomial in \((v,t)\), with only scalar
denominators:

| target Hamiltonian | source component degree | scalar denominator factors |
|---|---:|---|
| \(PQ\) | \(11\) | \((s-6)^6(s-4)\) |
| \(P^3/3\) | \(15\) | \((s-6)^6\) |
| \(Q^2/2\) | \(13\) | \((s-6)^8(s-4)^2\) |

Their pullbacks, and hence \(V_s^K\), satisfy

\[
U(0,0)=0,\qquad V(v,0)\in(v^2),
\]

\[
\partial_v(g^2U)+\partial_t(g^2V)=0,
\]

and

\[
\left.(V-\tfrac32U)\right|_{g=0}=0.
\]

The full \(V_s^K\) has spatial component degrees \((15,15)\) over
\(\mathbb Q(s)\) and is regular at \(s=0\).

## Integration and logarithm

Translations commute at all parameter values.  Therefore Magnus integration
on the divisor is exact:

\[
\int_0^s c(u)\,du
=-\frac{5s^2}{3(s^2-16)}
=\frac{5s^2}{3(16-s^2)}.
\]

In the source-flow convention with velocity \(V_s^K\),

\[
\left.\log\Psi_s\right|_{g=0}
=\frac{5s^2}{3(16-s^2)}\partial_y.
\]

Using the inverse source flow changes the sign and leaves the degree
unchanged.  Every coefficient of this logarithm has \(y\)-degree zero.

## Quotient residue

The source connection is not annihilated by target controls on the divisor.
Since \(L\) is nonconstant over \(\mathbb Q[[s]]\),

\[
c(s)[1]\ne0
\quad\text{in}\quad
\mathbb Q[[s]][y]/
\operatorname{span}\{L,L^3\}.
\]

Thus a target-control quotient class remains, but it has the abelian
translation representative \(c(s)\partial_y\).  It cannot supply an
unbounded polynomial-degree obstruction.

## Claim separation

1. **Source-only gauge.**  The proved even-order law
   \[
   \deg(Y_n|_{g=0})=2n-4
   \]
   remains valid for that declared gauge.

2. **Full polynomial contact.**  The regular Hamiltonian above changes the
   same divisor logarithm to degree zero at every order.  Therefore the
   source-only Bernoulli--Witt cascade cannot yield a gauge-independent
   logarithmic lower bound.

3. **Global source complexity.**  The constructed source velocity has degree
   fifteen off the divisor.  Its global Magnus logarithm has not been shown
   to lie in a bounded polynomial-degree Lie algebra.

4. **Symmetric source/target filtration.**  The instantaneous target field
   has degree at most two, but its logarithm need not.  The \(P^3\) and
   \(Q^2\) Hamiltonians generate increasing monomials under Poisson brackets,
   beginning with
   \[
   \{P^3/3,Q^2/2\}\ \propto\ P^2Q.
   \]
   The divisor reduction therefore does not decide the symmetric asymptotic
   contact complexity.

## Counterattacks

- **Gauge sign:** \(V^K=V^{(0)}-W_K\) is checked by the infinitesimal contact
  equation and by \(V_0^K=0\).
- **Flow orientation:** left/right or inverse-flow conventions only change
  the sign of the translation logarithm.
- **Hidden high target jets:** the \((1,2)\) normal weights prove that they
  vanish before restriction; this is stronger than a finite target cutoff.
- **Rational pullback masquerading as a control:** each of the three used
  pullbacks has no spatial denominator and satisfies the lift and weighted
  divergence identities.
- **Moving-divisor correction:** the final source field is tangent to
  \(g=0\); no normal motion is used.
- **Global overextension:** bounded divisor degree is not a bounded global or
  symmetric logarithm theorem.

## Verdict

The exceptional-divisor Bernoulli--Witt cascade is removable by an admissible
regular target gauge.  Its complete target-control quotient retains a
nonzero translation residue, whose logarithm is degree zero.  The next
gauge-independent discriminator must use off-divisor structure or charge
source and target logarithms symmetrically.
