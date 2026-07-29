# Source coordinate degree escape for the normalized Jacobian deformation

**Status:** independently audited theorem candidate with provider-free
kernel ratification of its algebraic spine; historical priority unconfirmed

## Statement

Let \(F_s\) be the normalized degree-\(3\)-to-\(4\) Jacobian-counterexample
deformation and \(F_0\) its special fiber.  Consider an identity-normalized
admissible equivariant formal contact

\[
H_s\circ F_s=F_0\circ\Psi_s,\qquad
\det DH_s=1,\qquad H_0=\Psi_0=\operatorname{id}.
\]

Then the coefficient maps of the source coordinate series
\(\Psi_s-\operatorname{id}\) cannot all have spatial degree bounded by one
fixed constant.

No degree restriction is placed on \(H_s\).

## Mechanism

Assume a source bound.  The finite spatial support algebraizes
\(\Psi_s\) over \(K=\mathbb Q((s))\).  The exact quotient Jacobians

\[
\det DF_s=\det DF_0=-\gamma^2,\qquad
\gamma=1-\frac32v+t
\]

and the contact chain rule give

\[
\gamma(\Psi_K)^2\det D\Psi_K=\gamma^2.
\]

In \(K[v,t]\), unique factorization and dominance force

\[
\gamma\circ\Psi_K=c\gamma,\qquad
\det D\Psi_K=c^{-2}.
\]

After the affine conjugation \((x,y)=(\gamma,v)\),

\[
\Psi_K(x,y)=(cx,c^{-3}y+p(x)).
\]

The two equivariant source-map ideals evaluate to

\[
p(1)=0,\qquad c=1,\qquad p'(1)=0.
\]

Thus the entire source contact is a fixed-\(\gamma\) shear:

\[
\Psi_s(\gamma,v)=(\gamma,v+p_s(\gamma)).
\]

The inverse-cubic chart

\[
w^3-w^2+Pw-Q=0
\]

then supplies the obstruction.  At first order, a leading shear monomial
\(\gamma^n\) has associated-graded nonbase exponents \(2n+3\) and \(2n+4\);
they cannot both be multiples of three.  Descent removes every
positive-degree shear term.  The constant term is removed by the nonzero
\(w\)-coefficient \(12P-4\), so the first source jet vanishes.

At second order the normalized residual allows every parameter-dependent
Hamiltonian target correction and every fixed-\(\gamma\) source shear.  The
same leading-term descent removes positive source degree.  A constant shear
has no \(w^2\)-term in the first component, while the residual has

\[
\frac{10-21P}{24}\ne0.
\]

The second contact equation is therefore impossible.

## Verification

The independent audit checked the volume identity, ideal inheritance,
Laurent-to-formal coefficient descent, first-order isotropy, general
second-order target-path expansion, and both contact orientations.

The deterministic inverse-cubic replay
[`equivariant_hamiltonian_jet_escape.py`](equivariant_hamiltonian_jet_escape.py)
passes and exposes the exact remainders.

The Lean source
[`AxiomPackJacobianSourceDegreeEscape.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianSourceDegreeEscape.lean)
contains:

- generic-field bivariate exceptional-square factorization;
- the lift-ideal scaling endpoint;
- arbitrary-polynomial leading-degree descent;
- first-order fixed-\(\gamma\) isotropy elimination;
- all-degree second-jet exclusion;
- and the second-order path reduction.

Provider-free LeanMill ratification of
`source_degree_escape_terminal_certificate` used zero provider calls and
closed with:

- closure-record SHA-256
  `e9400b37a1df59a178c0a51b4c04fc3b8a7800d998e185b42f711cf8a4ac3523`;
- kernel-parity SHA-256
  `69229f1784eecccaf3f2abd6484efdcb4c33ad6222ecc16a937715a2dca840ee`;
- governed closure SHA-256
  `2f50f8425a3f20e4e0b233c07acdb76f8cc9ae4ca98d7d3c5b9ca1aee2db9cc1`;
- matched negated-conclusion control and axiom allowlist passed.

The ambient formal-series/group bridge remains a mathematical argument in
the pencil rather than one monolithic Mathlib formalization.

## Scope and priority

The conclusion concerns coefficient degrees of the assembled source
coordinate map.  It gives no quantitative lower rate and does not settle the
uniform-degree problem for logarithmic generators \(Y_n\), since
exponentiation can increase map degree through repeated compositions.

The closest current sources own the counterexample, the quotient square
Jacobian, the inverse cubic, the branch at infinity, and capped local
deformation calculations.  The inspected primary records do not state this
source-only all-order degree obstruction.  This supports a narrow frontier
candidate classification; historical priority still requires external
confirmation.
