# Exceptional-divisor Magnus escape in the source-only gauge

**Status:** source-only all-order theorem with exact replay through order
eleven; its use as a full-gauge lower bound is exactly refuted

## Statement

Let \(V_s\) be the regular source-only connection for the normalized
Jacobian-counterexample deformation:

\[
\partial_sF_s=dF_sV_s.
\]

Let \(\Psi_s\) be its formal source flow and

\[
\Omega_s=\log\Psi_s=\sum_{n\ge1}s^nY_n.
\]

On the invariant exceptional divisor

\[
\gamma=1-\frac32v+t=0,
\]

the even logarithmic coefficients satisfy

\[
\boxed{
\deg_v\!\left(Y_n|_{\gamma=0}\right)=2n-4
\quad\text{for every even }n\ge4.
}
\]

Consequently the polynomial degrees of the full \(Y_n\) are unbounded in
this source-only gauge.

## Witt reduction

Put \(y=2v+3\).  The restricted connection is cubic at every parameter
order.  Its first three coefficient fields are

\[
A=\frac{y^3}{6}\partial_y,\qquad
B=\frac{7y^3-9y+10}{48}\partial_y,\qquad
C=\frac{y^2(8y+15)}{288}\partial_y.
\]

For the Witt basis \(e_j=y^{j+1}\partial_y\),

\[
[e_i,e_j]=(j-i)e_{i+j}.
\]

The top surviving part of
\(\operatorname{ad}_A^kB\) comes from the \(e_{-1}\) term of \(B\), while
the matching part of \(\operatorname{ad}_A^{k-1}C\) comes from the \(e_1\)
term of \(C\).  For every \(k\ge2\),

\[
\deg\operatorname{ad}_A^kB=2k
\]

and

\[
\operatorname{ad}_A^{k-1}C
=-\frac12\operatorname{ad}_A^kB
+\text{terms of lower Witt index}.
\]

The leading coefficient recurrence is nonzero:

\[
r_{k+1}=\frac16(2k-3)r_k
\qquad(k\ge2),
\]

with \(r_2\ne0\).

## Magnus coefficient

Linearizing the Magnus logarithm around the constant field \(A\), let
\(\phi_j(x)\) be the universal response to \(s^jV_j\).  Direct integration
and the inverse differential of the exponential give

\[
\phi_j(x)=
\frac{xe^x}{e^x-1}
\int_0^1u^je^{-ux}\,du.
\]

The two top Witt chains combine as

\[
\phi_1(x)-\frac{x}{2}\phi_2(x)
=\frac{x}{2(e^x-1)}.
\]

At \(k=n-2\), with \(n\ge4\) even, its coefficient is

\[
\frac{B_k}{2k!}\ne0.
\]

The required nonvanishing has an elementary recurrence proof.  Put

\[
\frac{x}{2}\coth\frac{x}{2}
=1+\sum_{m\ge1}c_mx^{2m}.
\]

The differential equation

\[
xh'=h-h^2+\frac{x^2}{4}
\]

gives \(c_1=1/12\) and, for \(m\ge2\),

\[
(2m+1)c_m
=-\sum_{i=1}^{m-1}c_ic_{m-i}.
\]

Writing \(c_m=(-1)^{m-1}a_m\) yields

\[
a_1=\frac1{12},\qquad
a_m=\frac{\sum_{i=1}^{m-1}a_ia_{m-i}}{2m+1}>0.
\]

Thus every \(c_m\), and therefore every displayed even Magnus coefficient,
is nonzero without importing an analytic zeta-value formula.

No other Magnus word reaches the same Witt index.  If a word contains \(r\)
positive-order fields with parameter indices \(j_\ell\) and Witt indices
\(q_\ell\le2\), its total Witt index is

\[
2k+\sum_\ell q_\ell,
\]

while its parameter order is

\[
n=k+r+\sum_\ell j_\ell.
\]

The candidate index \(2n-5\) can occur only from
\((j,q)=(1,-1)\) or \((2,1)\).  Those are exactly the displayed \(B\) and
\(C\) chains.  With at least two positive-order fields the sole apparent
equality case would require an \(e_1\) term in \(B\), but \(B\) has none.
Every nonlinear word is therefore lower.

## Verification

[`gauge_source_connection_divisor_magnus.py`](gauge_source_connection_divisor_magnus.py)
checks:

- invariance of \(\gamma=0\);
- cubic degree and regularity of every tested velocity coefficient;
- the displayed Witt fields;
- the iterated-bracket degree and leading-coefficient recurrence;
- the \(-1/2\) top-chain ratio;
- the Bernoulli coefficients through bracket depth eight;
- and the complete Magnus recursion through order eleven in both
  left- and right-flow conventions.

The replayed even divisor degrees are

\[
\deg(Y_4,Y_6,Y_8,Y_{10})=(4,8,12,16)
\]

in both conventions.

The Lean source
[`AxiomPackJacobianDivisorMagnusEscape.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianDivisorMagnusEscape.lean)
proves positivity of the convolution recurrence, nonvanishing of the Witt
chain, nonvanishing of their product at every even order, and the degree
arithmetic.  Provider-free LeanMill ratification of
`divisor_magnus_escape_terminal_certificate` used zero provider calls and
closed with:

- closure-record SHA-256
  `ee6e6aa15db3d3fad1cf40eb93c1a3947c51e4069fe3b56bdcbc9282633048e7`;
- kernel-parity SHA-256
  `b6e85f9945162b24411659e302b60c03e4550a67502d04bdd9865365e603de34`;
- governed closure
  [`AxiomPackJacobianDivisorMagnusEscape.divisor_magnus_escape_terminal_certificate_22c765cc99d9.lean`](../../../ztare_proofs/closures/AxiomPackJacobianDivisorMagnusEscape.divisor_magnus_escape_terminal_certificate_22c765cc99d9.lean).

Compilation, the matched negated-conclusion control, statement integrity,
and the axiom allowlist all passed.

## Full-gauge disposition

The Bernoulli–Witt cascade is removable by one regular admissible target
control.  Let

\[
K_s=a(s)P^3,\qquad
a(s)=
-\frac{192(s^2-3s-8)}
{(s-6)^3(s-4)^2(s+4)^2}.
\]

Its Hamiltonian field is

\[
X_{K_s}=(0,-3a(s)P^2),
\]

so it satisfies the full target lift ideals.  The coefficient is regular at
the distinguished fiber and \(a(0)=-1/36\), the \(P^3\) part of the
normalized first target Hamiltonian.

Subtracting its polynomial source pullback from the source-only connection
gives, on \(\gamma=0\),

\[
\boxed{
\overline V^{\,\mathrm{controlled}}_s
=
\frac{
s\bigl(9s^2y-15s^2-144y+160\bigr)
}{
3(s-4)^2(s+4)^2
}\partial_y .
}
\]

This field is affine in \(y\) for every \(s\).  The affine fields

\[
\mathfrak{aff}_1
=\operatorname{span}\{\partial_y,y\partial_y\}
\]

are closed under Lie bracket.  Hence every Magnus coefficient of the
controlled divisor connection remains affine.  Exact replay through order
eleven verifies this in both left- and right-flow conventions.  The full
source pullback is polynomial, satisfies both source lift ideals, is tangent
to \(\gamma=0\), and has zero divergence for the weighted density
\(\gamma^2\,dv\wedge dt\).

This is a decisive negative for the proposed gauge-independent divisor
mechanism: the unbounded source-only logarithmic shells disappear in an
allowed regular Hamiltonian gauge.

The complete lowest-weight target image sharpens the normal form further.
With

\[
\begin{aligned}
\widetilde a(s)
&=\frac{96(s^2-12s+16)}
{(s-6)^3(s-4)^2(s+4)^2},\\
b(s)&=\frac{2s}{(s-4)(s+4)}
\end{aligned}
\]

and

\[
\widetilde K_s=\widetilde a(s)P^3+b(s)PQ,
\]

the controlled divisor connection is the constant field

\[
\boxed{
\left.\widetilde V_s\right|_{\gamma=0}
=
\frac{160s}{3(s-4)^2(s+4)^2}\partial_y.
}
\]

Both coefficients are regular at zero, with
\((\widetilde a(0),b(0))=(-1/36,0)\).  The target field satisfies

\[
\dot P=b(s)P,\qquad
\dot Q=-3\widetilde a(s)P^2-b(s)Q,
\]

so the target lift ideals are explicit.  The divisor logarithm now lies in
the abelian translation algebra \(\mathbb Q\partial_y\).

This is also the complete lowest-weight action.  Give \(P,Q\) exceptional
weights \(1,2\).  The target lift ideals exclude the Hamiltonian monomials
\(P,Q,P^2\).  Every remaining monomial of weight at least four has source
pullback vanishing on \(\gamma=0\), because

\[
P_s=\gamma\,p_s(y)+O(\gamma^2),\qquad
Q_s=\gamma^2q_s(y)+O(\gamma^3),\qquad
\det D_{(y,\gamma)}F_s=-\frac{\gamma^2}{2}.
\]

Only the weight-three monomials \(P^3\) and \(PQ\) act nontrivially on the
divisor.  They are exactly the two controls used above.

Adding the divisor-invisible Hamiltonian \(-Q^2/4\) gives

\[
K_s^{\mathrm{norm}}
=\widetilde a(s)P^3+b(s)PQ-\frac14Q^2.
\]

At \(s=0\) this is exactly
\(-P^3/36-Q^2/4\), the campaign's fixed first target Hamiltonian.  The
corresponding global source connection vanishes at \(s=0\), while its
divisor restriction remains the same translation field.  The cancellation
therefore survives the normalized first-order slice; it is not obtained by
changing the first source jet.

## Scope

This result identifies an infinite Bernoulli–Witt cascade in a canonical
source-only connection and simultaneously proves that this cascade cannot
establish a gauge-minimized logarithmic lower bound.  The remaining campaign
residual is global: whether compatible contacts can keep the complete source
logarithm in a fixed polynomial-degree space, not merely its restriction to
the exceptional divisor.
