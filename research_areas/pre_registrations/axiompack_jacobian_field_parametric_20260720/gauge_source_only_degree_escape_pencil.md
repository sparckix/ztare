# Source-only degree escape from the exceptional divisor

**Status:** theorem candidate; independently audited, algebraic endpoints
kernel-ratified, full leading-term and jet bridge formalization pending

## Eigenquestion

For a compatible formal contact

\[
H_s\circ F_s=F_0\circ\Psi_s,\qquad \det DH_s=1,
\]

must the spatial degrees of the source coefficients of \(\Psi_s\) be
unbounded even when no degree bound is imposed on the target gauge \(H_s\)?

The contact is identity-normalized:

\[
H_0=\operatorname{id},\qquad \Psi_0=\operatorname{id}.
\]

The claim is killed by any of:

- failure of the weighted source-volume identity without a target-degree
  bound;
- a bounded source map not algebraizing over \(K=\mathbb Q((s))\);
- failure of the equivariant source-map ideals to force the exceptional
  scaling to one;
- a nonzero first-order isotropy inside the fixed-\(\gamma\) shear subgroup;
- or a missing fixed-\(\gamma\) direction in the all-degree second-jet
  obstruction.

## Bounded source degree forces a fixed-exceptional shear

Assume only that all coefficients of \(\Psi_s-\operatorname{id}\) have
spatial degree at most one fixed \(D\).  Finite monomial support assembles
them into

\[
\Psi_K\in K[v,t]^2.
\]

The chain rule uses no target-degree hypothesis.  Since
\(\det DH_s=1\) coefficientwise and

\[
\det DF_s=\det DF_0=-\gamma^2,\qquad
\gamma=1-\frac32v+t,
\]

it gives

\[
\gamma(\Psi_K)^2\det D\Psi_K=\gamma^2.
\]

The UFD and dominance argument from the joint obstruction yields, after the
affine conjugation \((x,y)=(\gamma,v)\),

\[
\Psi_K(x,y)=(cx,c^{-3}y+p(x)),
\qquad c\in K^\times,\quad p\in K[x].
\]

Write the original-coordinate differences as

\[
\begin{aligned}
U&=v'-v=(c^{-3}-1)y+p(x),\\
V&=t'-t=(c-1)x+\frac32(c^{-3}-1)y+\frac32p(x).
\end{aligned}
\]

The equivariant source-map lift ideals are

\[
U\in(v,t),\qquad V\in(t,v^2).
\]

Evaluating the first at \(v=t=0\) gives \(p(1)=0\).  Evaluating the second
there then gives \(c=1\).  Finally, setting \(t=0\) and taking the coefficient
of \(v\) gives \(p'(1)=0\).  Hence

\[
\boxed{\Psi_K(\gamma,v)=(\gamma,v+p(\gamma)),
\qquad (\gamma-1)^2\mid p(\gamma).}
\]

Equality over \(K\) is equality of the original formal coefficient tower, so
the formal source contact lies in the fixed-\(\gamma\) shear subgroup.  This
subgroup is additive: its logarithm and every parameter jet have the form

\[
f(\gamma)\left(\partial_v+\frac32\partial_t\right).
\]

## First-order isotropy is trivial in the fixed-\(\gamma\) subgroup

The normalized family tangent is already the target Hamiltonian response

\[
\dot F_0=X_H(F_0),\qquad
H=-\frac14Q^2-\frac1{36}P^3.
\]

Another first-order decomposition could differ only by an isotropy pair

\[
X_K(F_0)+f(\gamma)D_\gamma F_0=0,
\qquad
D_\gamma=\partial_v+\frac32\partial_t.
\]

In the inverse coordinate \(w\), target-base terms have zero \(w,w^2\)
remainder modulo

\[
w^3-w^2+Pw-Q.
\]

For a leading shear term \(\gamma^n\), \(n\ge1\), the associated-graded
remainders at \(P=0\) have exponents \(2n+3\) and \(2n+4\) modulo
\(w^3-Q\).  They cannot both be divisible by three.  Descending in \(n\)
therefore eliminates every positive-degree coefficient of \(f\).

For constant \(f\), the first source component has remainder

\[
2(6Pw+P-9Q-2w),
\]

whose \(w\)-coefficient \(12P-4\) is nonzero.  Thus \(f=0\), and dominance
of \(F_0\) makes the target vector field difference zero as well.  The
first-order source shear is forced to vanish.

## The second jet excludes the remaining contact

With the first source jet zero, the composition-correct second residual is

\[
\mathcal R=
\left(
\ddot P+\frac1{24}P_0^2,\,
\ddot Q+\frac1{12}P_0Q_0
\right).
\]

Every parameter-dependent target correction contributes an arbitrary
polynomial Hamiltonian field \(X_K(F_0)\); every second source correction in
the forced subgroup contributes \(f(\gamma)D_\gamma F_0\).

The all-degree fixed-\(\gamma\) certificate eliminates positive-degree
\(f\) by the same associated-graded descent.  For constant \(f\), the
\(w^2\)-coefficient in the first residual remainder is

\[
\frac{10-21P}{24},
\]

while the constant source response has no \(w^2\)-term.  It cannot vanish
identically.  Therefore the second-order contact equation has no solution
in this subgroup.

Combining the forced subgroup with that obstruction gives the candidate
theorem

\[
\boxed{
\text{every compatible Hamiltonian contact has source coefficients of
unbounded spatial degree.}
}
\]

This is stronger than joint target/source escape and does not require a
uniform target-degree hypothesis.

## Scope

The degree tower here is the coefficient tower of the assembled source
coordinate map \(\Psi_s\).  The conclusion does not by itself give a
quantitative lower rate.  It also does not immediately imply that the
degrees of the logarithmic generators \(Y_n\) are unbounded: exponentiating
a uniformly degree-bounded sequence of generators can create higher-degree
composition words.  That logarithmic minimax question remains the next
filtered problem.

The map lift ideals used above follow coefficientwise from the declared
source group because \((v,t)\) and \((t,v^2)\) are preserved by its
derivations, compositions, inverses, and formal flows.

## Formal surface and remaining checks

The existing kernel artifacts already certify:

- the exceptional-square factorization and bivariate reduction;
- the normalized first Hamiltonian tangent;
- the modulo-cubic remainder identities;
- the associated-graded consecutive-exponent obstruction;
- and the constant second-jet witness.

The new kernel surface should additionally bind:

1. the two source-map lift ideals to \(c=1\), \(p(1)=p'(1)=0\);
2. the constant fixed-\(\gamma\) first-order isotropy obstruction;
3. the descent from a polynomial \(f\) to its leading monomial;
4. and the implication from a bounded formal source tower to the
   fixed-\(\gamma\) subgroup.

Historical priority remains separate from validity.

## Audit and current kernel boundary

An independent audit attempted the unrestricted-target counterattack and
found no counterexample.  It checked:

- inheritance of the map ideals from the logarithmic source group;
- absence of Laurent-coefficient cancellation in \(p(\gamma)\);
- the arbitrary-polynomial leading-term descent for first-order isotropy;
- the general second-order expansion of an area-preserving target path;
- and invariance of the obstruction under reversing the contact convention.

The compiled endpoint is
[`AxiomPackJacobianSourceDegreeEscape.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianSourceDegreeEscape.lean).
Provider-free LeanMill ratification of
`source_degree_escape_terminal_certificate` closed with:

- zero provider calls;
- closure-record SHA-256
  `e9400b37a1df59a178c0a51b4c04fc3b8a7800d998e185b42f711cf8a4ac3523`;
- kernel-parity SHA-256
  `69229f1784eecccaf3f2abd6484efdcb4c33ad6222ecc16a937715a2dca840ee`;
- governed closure SHA-256
  `2f50f8425a3f20e4e0b233c07acdb76f8cc9ae4ca98d7d3c5b9ca1aee2db9cc1`;
- matched negated-conclusion control and axiom allowlist passed.

That carried target binds the generic-field square factorization, lift-ideal
scalar endpoint, arbitrary-polynomial leading-degree descent, first-order
isotropy elimination, second-jet exclusion, and componentwise second-order
path reduction.  The remaining non-kernel bridge is the ambient formal-series
and admissible-group setup that sends a bounded normalized contact to these
exact algebraic hypotheses.  The mathematical audit regards the displayed
source-only theorem as valid at the stated admissible boundary.
