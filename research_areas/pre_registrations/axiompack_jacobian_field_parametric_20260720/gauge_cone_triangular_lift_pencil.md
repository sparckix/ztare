# Higher-normal gate for a cone-valued moving connection

**Status:** pencil obstruction; the cusp-symbol rank theorem does not by
itself lift to the complete moving-contact module

## Eigenquestion

Let

\[
\mathfrak c
=
\mathbb Q\oplus
\operatorname{span}_{\mathbb Q}
\{X^aY^b:b\geq1,\ a\leq2b\},
\qquad X=-P/3,\quad Y=-Q/2.
\]

The kernel-ratified cusp-symbol theorem says that the Hamiltonian symbols
of \(\mathfrak c_w\) span both cusp directions for every weight \(w\geq17\).
Does this imply a coefficientwise finite triangular reduction of the
complete normalized moving-contact equation, with source corrections in
only finitely many spatial weights?

The answer separates into three claims:

1. literal existence of a cone-valued instantaneous connection;
2. a universal filtered reduction of every admissible target shell to the
   cone modulo a uniformly bounded source field;
3. a special reduction for the particular moving recurrence selected by
   the Jacobian family.

Claim 1 is already available and does not use cusp-symbol surjectivity.
Claim 2 is false.  Claim 3 remains a sharply defined higher-normal
recurrence question.

## Category correction: literal existence is already closed

The exact regular source-only connection satisfies

\[
\partial_sF_s=dF_s\,V_s,
\qquad
\deg_{v,t}V_s=11.
\]

Taking \(K_s=0\in\mathfrak c\) therefore gives an all-order cone-valued
instantaneous connection whose source velocity has bounded spatial support.
The same observation survives a prescribed fixed low cone Hamiltonian
whenever its full moving pullback is polynomial: subtract that pullback from
the source-only connection.

Consequently, “cone-valued target plus finitely many source spatial
weights” is too weak to advance the logarithmic contact problem.  A
bounded-degree velocity may generate unbounded Magnus coefficients.  A
useful successor statement must additionally fix the relevant low/polar
normal form or prove that the finite source module is closed in a
finite-degree Lie algebra.

## The rank-two theorem sees only the cusp one-jet

Put

\[
r=VG,\qquad
\overline P=-3r^2,\qquad
\overline Q=-2r^3.
\]

For \(H_{a,b}=X^aY^b\), \(2a+3b=w\), the restriction of its Hamiltonian
field to the top cusp has coefficient vector

\[
J_w(a,b)=\left(-\frac b2,\frac a3\right)
\]

against \((r^{w-3},r^{w-2})\).  Two adjacent monomials give determinant
\(-w/6\), so two cone monomials span this two-dimensional quotient.

Let

\[
D=X^3-Y^2.
\]

Equality of Hamiltonian one-jets on the cusp is equality modulo \(D^2\):
if a weighted-homogeneous polynomial \(H\) has
\(X_H|_{D=0}=0\), then both partial derivatives of \(H\) lie in \((D)\),
and weighted Euler first gives \(H\in(D)\).  Writing \(H=DL\) and reducing
its two derivatives modulo \(D\) gives
\(L D_X=L D_Y=0\) on the irreducible cusp.  Since \(D_X,D_Y\) are not both
zero at its generic point, \(L\in(D)\), hence \(H\in(D^2)\).  Thus \(J_w\)
is the quotient

\[
R_w\longrightarrow R_w/(D^2)_w
\]

seen through the Hamiltonian field.  It contains no information about the
higher normal layers \(D^m/D^{m+1}\), \(m\geq2\).

The first all-tail example occurs at weight \(17\).  The full weight space
has

\[
XY^5,\qquad X^4Y^3,\qquad X^7Y,
\]

while the cone contains only the first two.  The missing combination is

\[
\boxed{
X^7Y-2X^4Y^3+XY^5=XYD^2.
}
\]

Its cusp Hamiltonian symbol vanishes.  Under the exact seed map its two
components begin in source degrees \(26\) and \(28\):

\[
X_{XYD^2}(F_0)^{\rm top}
=
\left(-2r^{13},-2r^{14}\right).
\]

These are precisely the component degrees of cusp weight \(16\).  This
explains why the weight-17 missing two-jet can descend into the finite
exceptional weight \(16\); it does not prove that every higher-normal
direction descends to that finite set.

## Exact transverse tower missed by the cusp symbol

The complete target module has an independent transverse coordinate

\[
C
=4P^3-P^2-18PQ+27Q^2+4Q.
\]

At the seed,

\[
C(F_0)=\gamma^2(3P+\gamma-1),
\]

and in the \((V,G)\) top shell

\[
[C(F_0)]_{\deg 6}=-9G^4V^2.
\]

This is not a polynomial in \(r=VG\).  Powers of \(C\) therefore supply
higher-normal directions of unbounded degree that never enter the
two-dimensional cusp-symbol quotient.

There is a direct quotient which proves that no universal bounded-source
cone reduction exists.  On the source line

\[
\ell:\quad V=-1,
\]

the seed satisfies

\[
F_0|_\ell=(P,Q)=(G+1,0).
\]

Every nonconstant cone Hamiltonian is a sum of \(P^aQ^b\) with
\(b\geq1\) and \(a\leq2b\).  Hence, on \(Q=0\),

\[
\boxed{
X_K(P,0)=
\bigl(c_0+c_1P+c_2P^2,\ 0\bigr)
\quad(K\in\mathfrak c).
}
\]

Only terms with \(b=1\) contribute to \(K_Q(P,0)\), and the cone inequality
then gives \(a\leq2\); every term in \(-K_P(P,0)\) retains a factor \(Q\).

For \(k\geq2\), the Hamiltonian \(H_k=C^k\) satisfies the target lift
conditions.  Since

\[
C(P,0)=P^2(4P-1),
\]

its restriction is

\[
\begin{aligned}
(X_{H_k})_P(P,0)
&=
k[P^2(4P-1)]^{k-1}(4-18P),\\
(X_{H_k})_Q(P,0)
&=
-k[P^2(4P-1)]^{k-1}(12P^2-2P).
\end{aligned}
\]

The second component has degree \(3k-1\).  It cannot be changed by any
cone Hamiltonian on this line.

If a source field \(Z\) has component degree at most \(B\), then
the exact seed derivatives on this line are

\[
\left.\partial_VQ_0\right|_\ell=(G+1)^2,
\qquad
\left.\partial_GQ_0\right|_\ell=0.
\]

Hence \((dF_0Z)_Q|_\ell\) has degree at most \(B+2\).  Therefore a
decomposition

\[
X_{C^k}(F_0)
=X_{K^{\rm cone}}(F_0)+dF_0Z
\]

forces

\[
\boxed{B\geq3k-3.}
\]

The complete admissible target module consequently has no normal form
“cone target plus uniformly bounded source.”  The obstruction is a
\(C\)-adic transverse tower.  The ratified rank-two cusp arithmetic remains
valid.

In particular, the proposed exceptional cap \(B=23\) cannot absorb
\(C^k\) once \(k\geq9\).

## Conditional lifting lemma

The rank-two theorem would lift on a smaller moving residual module
\(\mathcal M\) if all of the following were proved:

1. **Two-dimensional graded pieces.**  For every \(w\geq17\),
   \[
   \operatorname{gr}_w\mathcal M
   =
   \mathbb Q r^{w-3}\oplus\mathbb Q r^{w-2}.
   \]
   In particular, no \(C\)-adic or higher-normal class may occur in this
   graded piece.

2. **Strict triangularity.**  Subtracting a cone lift of a graded class
   leaves \(\mathcal M_{<w}\).  Lower target weights and bounded source
   fields do not feed back into \(\operatorname{gr}_w\).

3. **Finite exceptional completion.**  At each rank-one weight
   \[
   E=\{6,7,8,9,10,11,13,16\},
   \]
   the cone symbol together with the strict weighted-volume source symbol
   \(U_{w-4}\) spans the two cusp directions.  Their determinant is a
   nonzero scalar multiple of
   \[
   2a+3b=w.
   \]
   Since \(U_m\) has component degree \(2m-1\), this exceptional package
   has the uniform source cap
   \[
   \max_{w\in E}\deg U_{w-4}=23.
   \]

4. **Moving stability.**  Parameter differentiation, substitution in
   \(F_s\), and every carried lower-order affine freedom preserve
   \(\mathcal M\).

5. **Coefficientwise termination.**  Each parameter coefficient begins at
   finite filtration weight, and every correction lowers that weight.
   This prevents an infinite target-adic tail in one coefficient.

Under these five hypotheses, descending induction cancels every weight
\(\geq17\) by a cone Hamiltonian and stops in the finite set \(E\), where
the source symbols complete the image.  This is the exact filtered-module
content needed by the proposed triangular lift.

The \(C^k\) calculation shows that hypothesis 1 fails for the complete
target-lift module.  It may still hold for a special submodule invariant
under the particular moving recurrence.

## Next discriminating computation

The next calculation should test moving stability, rather than enlarge a
generic rank table.

At instantaneous order \(n\), write the carried equation as

\[
\mathcal L_0(K_n,V_n)=R_n,
\qquad
\mathcal L_0(K,V)=X_K(F_0)+dF_0V.
\]

Restrict its second component to \(\ell\), with \(P=G+1,Q=0\), and project
above the declared bounded source degree:

\[
\Lambda_B(R_n)
=
\sum_{d>B+2}
[G^d]\,(R_n)_Q|_{V=-1}\,G^d.
\]

For a new cone coefficient \(K_n\), this projection is zero.  It is also
zero for every source coefficient of degree at most \(B\).  Thus

\[
\boxed{\Lambda_B(R_n)=0}
\]

is a necessary condition for a bounded-source cone recurrence.  It is
semantic, independent of row ordering and pivot choices, and it detects
the \(C\)-adic tower exhibited above.

The computation must carry the complete lower-order affine solution space.
A first nonzero \(\Lambda_B(R_n)\) is an exact obstruction.  Repeated
vanishing is only a prefix fact until one proves that the moving recurrence
preserves \(\ker\Lambda_B\) (and the analogous higher-normal quotients).

## Actual-family transverse-quotient replay

The replay
[`gauge_moving_cone_transverse_quotient.py`](gauge_moving_cone_transverse_quotient.py)
applies \(\Lambda_B\) to the complete affine cone family through solved
orders \(j=0,\ldots,6\) and to the order-seven residual lookahead.  It
carries every lower homogeneous prefix direction.

The restricted second-component residual degrees are

\[
(2,2,3,3,4,4,5,5).
\]

The smallest caps not excluded by this one quotient are

\[
(0,0,1,1,2,2,3,3).
\]

For \(j\ge2\), the leading restricted coefficient is nonzero and every
lower affine direction has smaller line degree, so the cap immediately
below this small quotient bound is excluded.  Conversely, the fixed caps
\(B=11\) and \(B=23\) pass at every tested order.  Every immediately
preceding cap rejected by the complete contact system also passes
\(\Lambda_B\).

Therefore the actual moving family avoids the universal \(C^k\) tower
through this prefix.  Its observed full-system source costs arise in other
quotients.  The exact tables and hashes are in
[`gauge_moving_cone_transverse_quotient_result.md`](gauge_moving_cone_transverse_quotient_result.md).

## Formal carrier and provider-free ratification

The seed-line identities, cone line cap, source lower-bound arithmetic, and
escape from every fixed cap are packaged in
[`AxiomPackJacobianConeTransverseTowerArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianConeTransverseTowerArithmetic.lean).
The targeted build passes.  Provider-free LeanMill ratification used zero
provider calls and closed
`AxiomPackJacobianConeTransverseTowerArithmetic.cone_transverse_tower_arithmetic_terminal_certificate`
with:

- governed closure SHA-256
  `2d11aa45708a9b2aae4f06ce4a14f2253cccbb93ba03e89c9a9a615812ed0580`;
- closure-record SHA-256
  `35f47f7e7745b7316861eb3e9a5a27a1c636837c2b143080d95935df5f7f411c`;
- kernel-parity SHA-256
  `026a3115b00cde080759b09bada9c3a4c6eb92b3b6fd066e17e63ec59c6d8b2d`.

The matched negated-conclusion control, target identity, statement
integrity, governance, and axiom allowlist all passed.  The governed closure
is
[`AxiomPackJacobianConeTransverseTowerArithmetic.cone_transverse_tower_arithmetic_terminal_certificate_2d11aa45708a.lean`](../../../ztare_proofs/closures/AxiomPackJacobianConeTransverseTowerArithmetic.cone_transverse_tower_arithmetic_terminal_certificate_2d11aa45708a.lean).

## Claim boundary

The ratified theorem remains a sharp statement about the cusp Hamiltonian
one-jet.  The complete moving-contact triangular lift is not established.
The current obstruction does not prove that the particular Jacobian family
necessarily excites the \(C\)-adic tower; it proves that such avoidance is
the missing theorem and cannot be inferred from symbol rank two.

Even a successful instantaneous bounded-source reduction would still need
a finite-dimensional source Lie-closure or a Magnus recurrence before it
would change the symmetric logarithmic statistic.
