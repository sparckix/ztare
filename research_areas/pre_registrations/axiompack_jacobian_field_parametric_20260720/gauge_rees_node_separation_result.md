# Rees-boundary node separation

**Status:** exact diagonal-boundary theorem and conditional
instantaneous-velocity theorem; deterministic replay and targeted Lean
compilation passed; unrestricted logarithmic limsup remains open

## Boundary identity

Set

\[
s=\tau\varepsilon^2,\qquad
(v,t)=\left(\frac V\varepsilon,\frac T\varepsilon\right),
\]

and multiply the two normalized target components by
\(\varepsilon^4,\varepsilon^6\).  The exact special fiber factors through

\[
r=V\left(T-\frac32V\right)
\]

as

\[
\boxed{
f_\tau(r)=
\left(
\tau r^3-3r^2,\,
\frac34\tau r^4-2r^3
\right).
}
\]

This is derived from the full normalized family, including its rational
normalizing factors; it is not an extrapolation from the inverse quartic.

## Exceptional set

The derivatives are

\[
p_\tau'=3r(\tau r-2),\qquad
q_\tau'=3r^2(\tau r-2)=r\,p_\tau'.
\]

The normalization therefore ramifies at \(r=0\) and \(r=2/\tau\).  At each
point,

\[
\det(f_\tau'',f_\tau''')=72,
\]

so both singularities are ordinary cusps.

There is also an ordinary node.  Its two normalization points are

\[
r_\pm=\frac{1\pm\sqrt3}{\tau},
\]

and

\[
\boxed{
f_\tau(r_+)=f_\tau(r_-)
=\left(-\frac2{\tau^2},\frac1{\tau^3}\right).
}
\]

Their tangent slopes are \(r_+\ne r_-\).

The implicit boundary equation is

\[
\begin{aligned}
0={}&27\tau^2P^4+64P^3+24\tau P^2Q
+192\tau^2PQ^2\\
&-64\tau^3Q^3+432Q^2.
\end{aligned}
\]

At \(\tau=0\) this reduces to the unibranch seed cusp
\(4P^3+27Q^2=0\).  The deformation has concentrated its degree jump into a
second cusp and a node on the Rees boundary.

## Hamiltonian normal class

Suppose the complete source Rees action is regular.  Since \(f_\tau\)
factors through \(r\), its source contribution is tangent to the
parameterized curve.  Thus an instantaneous boundary contact has

\[
\partial_\tau f_\tau
=X_{K_\tau}(f_\tau)+a_\tau(r)f_\tau'(r),
\qquad
X_K=(K_Q,-K_P).
\]

Taking the determinant with \(f_\tau'\) removes the arbitrary
source-tangent coefficient.  Since

\[
\det(f_\tau',X_K(f_\tau))
=-\frac d{dr}K_\tau(f_\tau(r)),
\]

and

\[
\det(f_\tau',\partial_\tau f_\tau)
=-\frac34r^5(\tau r-2),
\]

every solution must satisfy

\[
K_\tau(f_\tau(r))
=-\frac14r^6+\frac{3\tau}{28}r^7+c(\tau).
\]

The required restriction separates the node branches:

\[
\boxed{
K_\tau(f_\tau(r_+))-K_\tau(f_\tau(r_-))
=\frac{72\sqrt3}{7\tau^6}\ne0.
}
\]

But a target function that can be evaluated at the node receives the same
pair \((-2\tau^{-2},\tau^{-3})\) on both branches.  It cannot have two
different values there.

## Conditional Rees consequence

For

\[
K_\tau=\sum k_{n,i,j}\tau^nP^iQ^j,
\]

the moving-node valuation is

\[
\nu_{\rm node}(\tau^nP^iQ^j)=n-2i-3j.
\]

If, for some \(\delta>0,C\),

\[
4i+6j\le(2-\delta)n+C
\]

on the complete support, then

\[
\nu_{\rm node}\ge\frac{\delta n-C}{2}.
\]

The node substitution is consequently a well-defined generalized Laurent
series, contradicting the separation above.  Hence, under the
regular-source specialization hypothesis, an instantaneous target
Hamiltonian solving this boundary problem must reach weighted slope two:

\[
\limsup_n
\frac{\max(4i+6j)}n\ge2.
\]

The elementary inequality
\(2i+3j\le3(i+j)\) gives the corresponding ordinary target-degree lower
rate \(1/3\) for this conditional instantaneous velocity.

## Uniform coefficient-map corollary

There is a complementary map-level statement.  Give a contact coefficient
the shifted excess

\[
\begin{aligned}
D_n=\max\{&
\deg(\Psi_{n,v})-1,\deg(\Psi_{n,t})-1,\\
&\deg_f(H_{n,P})-4,\deg_f(H_{n,Q})-6\}.
\end{aligned}
\]

If \(D_n\le2n\) at every order and \(2n-D_n\to+\infty\), the conjugated
contact maps have polynomial special fibers.  The target special fiber has
Jacobian one, hence is étale.  It cannot send the two local branches of the
nodal boundary curve into the unibranch seed cusp.  Therefore every contact
obeys the exact dichotomy

\[
\boxed{
\exists n:\ D_n>2n,
\quad\text{or}\quad
D_n\ge2n-O(1)\ \text{for infinitely many }n.
}
\]

This is a lower theorem for the global triangular Rees class.  Its first
arm may occur at one finite order, so the dichotomy alone does not bound a
tail-only limsup.

## Killed stronger inference

A contact logarithm with a low-degree tail need not have a low-degree
instantaneous velocity.  A finite noncommuting prefix can generate
infinitely many critical terms through `dexp`; iterated polynomial
Hamiltonian Witt brackets give explicit examples.  The
[polar-prefix audit](gauge_rees_node_polar_prefix_audit.md) also shows that
regular source tangency cannot be inferred from coefficientwise
polynomiality.  The apparent second-layer normal term cancels after the
forced cascade coefficient is included.  At the six vanishing Jacobian
layers, however, the exact regular source-only connection becomes a
pole-six cascade.  It has weighted divergence zero and spans the full
boundary motion.  Its principal part agrees with the adjugate witness; its
subleading terms repair that witness's divergence.

Accordingly, the node theorem does not yet prove
\(\sigma_{\rm ct}\ge1/3\), and it does not prove
\(\sigma_{\rm ct}=2\).  The remaining bridge is a contact-specific
polar-prefix normalization theorem that controls the logarithm of the
source-only flow.  The alternative assertion that every admissible prefix
cascade misses the node class is false.

## Verification

The exact replay
[`gauge_rees_node_separation.py`](gauge_rees_node_separation.py)
checks the full-family Rees limit, implicit equation, both cusps, the node,
normal determinant, Hamiltonian primitive, branch separation, the Rees
degree conversion, and the exact pole-six source-only contact.  It verifies
the scaled contact identity, weighted divergence, polar principal part, and
agreement with the adjugate witness.  Its SHA-256 is
`f4e5697e604f3d9c31b351754117e6a482fef297839611f020878326c5c7dbc0`.

The Lean source
[`AxiomPackJacobianReesNodeSeparation.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianReesNodeSeparation.lean)
checks the cusp Wronskians, the two scaled node images, the nonzero
Hamiltonian separation over \(\mathbb R\), and both degree inequalities.
The targeted Lake build passes.  Its terminal target is
`AxiomPackJacobianReesNodeSeparation.rees_node_separation_arithmetic_terminal_certificate`.
Provider-free LeanMill governance used zero provider calls and closed with:

- closure-record SHA-256
  `e51048696a9454875d0ed5348db5d60204116649d6a5f26c76713d77d78a16f2`;
- kernel-parity SHA-256
  `c014efa2577ab6ce098c9405b2135a5c922be1e3156341eb50029a374f9ba27c`;
- governed closure SHA-256
  `22f211961cfb01d3fca68c99cd5d693ccb2dfc7dcceadaa47d2cb63dc5956830`;
- matched negated-conclusion control, target identity, statement integrity,
  and axiom allowlist passed.

The governed closure is
[`AxiomPackJacobianReesNodeSeparation.rees_node_separation_arithmetic_terminal_certificate_22f211961cfb.lean`](../../../ztare_proofs/closures/AxiomPackJacobianReesNodeSeparation.rees_node_separation_arithmetic_terminal_certificate_22f211961cfb.lean).

Historical priority for this Rees-boundary contact-complexity statement has
not yet been established.
