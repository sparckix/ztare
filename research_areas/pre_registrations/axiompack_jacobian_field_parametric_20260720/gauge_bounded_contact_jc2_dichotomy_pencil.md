# Bounded contact versus the plane Jacobian conjecture

**Status:** valid weaker reduction; degree arithmetic independently audited
and kernel-ratified, superseded for this family by the exceptional-divisor
obstruction

## Eigenquestion

Could the normalized degree-four deformation admit a single compatible
Hamiltonian contact whose source and target coefficients all lie in fixed
spatial-degree stages?

The proposed reduction is killed if uniform coefficient degree does not
algebraize both formal maps over \(\mathbb Q((s))\), if either quotient map
is not generically finite, or if generic degrees fail to multiply in the
contact square.

## Uniform degree algebraizes the formal maps

Suppose

\[
H_s\circ F_s=F_0\circ\Psi_s
\]

is one compatible formal contact over \(\mathbb Q[[s]]\), with

\[
\det DH_s=1,
\]

and suppose every coefficient of \(H_s\) and \(\Psi_s\) has ordinary
spatial degree at most one fixed \(D\).

There are only finitely many monomials of degree at most \(D\). Their scalar
coefficient series therefore assemble into polynomial maps

\[
H_K,\Psi_K
\]

over \(K=\mathbb Q((s))\). The formal contact identity becomes a polynomial
identity over \(K\).

The target map \(H_K:\mathbb A^2\to\mathbb A^2\) has determinant one, hence
is dominant and generically finite. The source map is also dominant: its
weighted volume identity

\[
\gamma(\Psi_K)^2\det D\Psi_K=\gamma^2
\]

shows that its Jacobian is not identically zero.

## The degree square

The special quotient seed has generic degree three, while the generic
deformed quotient map has degree four. Put

\[
h=\deg H_K,\qquad m=\deg\Psi_K.
\]

Generic degree is multiplicative under composition, so the contact square
gives

\[
4h=3m.
\]

Since \(\gcd(3,4)=1\), \(3\mid h\). In particular,

\[
h\ge3.
\]

Thus \(H_K\) is a noninvertible polynomial map of the affine plane with
constant nonzero Jacobian: a counterexample to the two-variable Jacobian
conjecture.

The coefficients of \(H_K\) generate a finitely generated characteristic-zero
subfield \(E\subset\mathbb Q((s))\).  Such a field embeds in \(\mathbb C\).
After base change, étaleness and the rank of the generic finite map persist,
so the counterexample descends to the usual complex formulation of
\(\mathrm{JC}_2\).

## Dichotomy

The reduction gives:

\[
\boxed{
\text{a uniformly bounded compatible Hamiltonian contact}
\Longrightarrow \neg\mathrm{JC}_2.
}
\]

Equivalently, conditional on the two-variable Jacobian conjecture, every
compatible Hamiltonian contact for this deformation has unbounded spatial
coefficient degree.

Combined with the root-cover construction, the present envelope is

\[
\text{under }\mathrm{JC}_2:\qquad
\sup_n\deg[s^n]\Psi_s=\infty,
\qquad
\deg[s^n]\Psi_s\le2n+1
\]

for one explicit compatible contact.

## Precision boundary

This statement concerns one compatible all-order contact. A bounded sequence
of independently optimized finite-prefix minima does not by itself select a
compatible bounded tower.

The implication is one-way. A plane Keller counterexample would remove this
obstruction but would not automatically construct a bounded contact for the
normalized deformation.

The recent counterexample settles the Jacobian conjecture in dimensions at
least three; the plane case remains open. Therefore this reduction attaches
the bounded-contact question to a current open frontier rather than resolving
the plane conjecture.

For this particular family, the later exceptional-divisor argument is
stronger.  The identity

\[
\gamma(\Psi_K)^2\det D\Psi_K=\gamma^2
\]

forces \(\Psi_K\) to be a triangular automorphism, so \(m=1\) and the degree
square becomes \(4h=3\), an unconditional contradiction.  The present
\(\mathrm{JC}_2\) route remains useful as a fallback pattern for families
without a single preserved exceptional divisor.

## Validity tasks

The quotient identities and degree orientation passed independent audit.
`AxiomPackJacobianBoundedContactDichotomy.lean` checks the arithmetic
consequence \(4h=3m\Rightarrow3\mid h\) and \(h\ne1\). Provider-free
LeanMill ratification closed
`bounded_contact_jc2_degree_certificate` with closure-record SHA-256
`315060b27033ea8b5faadeaf09ca68793470bf173826b941d86ad416dbe9c63e`
and kernel-parity SHA-256
`78cbe945f066e0a73f7b4e29ecdd41cc46f3c4faaec8c70e18ac5322b0b97eab`.
