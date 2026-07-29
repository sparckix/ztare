# Exact degree of the cusp Hamiltonian cascade

**Eigenquestion.**  For

\[
C=4P^3+27Q^2,\qquad
B=\frac{P^3-C}{108},\qquad
D=X_C=54Q\partial_P-12P^2\partial_Q,
\]

does every iterate \(D^kB\) contain the unique monomial of maximal
ordinary degree allowed by its \((2,3)\)-weight?

The candidate formula is

\[
\deg(D^kB)=3+\left\lfloor\frac{k}{2}\right\rfloor .
\]

## Flow reduction

Let \((P(t),Q(t))\) be the \(D\)-flow from \((p,0)\).  Then

\[
\dot P=54Q,\qquad \dot Q=-12P^2,\qquad
\ddot P=-648P^2.
\]

Writing

\[
P(t)=p\,u(x),\qquad x=pt^2,\qquad
u(x)=\sum_{m\geq0}a_mx^m,\qquad a_0=1
\]

gives

\[
u'+2xu''=-324u^2.
\]

Coefficient comparison yields

\[
(m+1)(2m+1)a_{m+1}
=-324\sum_{i+j=m}a_i a_j. \tag{1}
\]

Put \(b_m=(-1)^ma_m\).  If \(b_i>0\) for \(i\leq m\), every term in
the convolution on the right of (1) has sign \((-1)^m\).  Hence
\(b_{m+1}>0\).  Since \(b_0=1\), induction proves

\[
(-1)^ma_m>0\qquad(m\geq0). \tag{2}
\]

Every summand of

\[
[x^m]u(x)^3=\sum_{i+j+\ell=m}a_i a_j a_\ell
\]

has the common sign \((-1)^m\).  The coefficient is therefore nonzero.

## Even iterates

Along the \(D\)-flow, \(C\) is constant and

\[
B=\frac{P^3-C}{108}.
\]

For \(m\geq1\),

\[
\frac{(D^{2m}B)(p,0)}{(2m)!}
=\frac{[x^m]u(x)^3}{108}p^{m+3}\ne0. \tag{3}
\]

The derivation \(D\) raises \((2,3)\)-weight by one, so \(D^{2m}B\)
has weight \(6+2m\).  Its unique monomial of maximal ordinary degree is
\(P^{m+3}\).  Equation (3) proves that this monomial occurs.  The case
\(m=0\) is direct from \(B=-(P^3+9Q^2)/36\).

## Odd iterates

Let \(H=D^{2m+1}B\).  It has weight \(7+2m\), whose unique
maximal-ordinary-degree monomial is \(P^{m+2}Q\).  On \(Q=0\),

\[
(DH)(P,0)=-12P^2(\partial_QH)(P,0). \tag{4}
\]

The left side is \(D^{2m+2}B(P,0)\), which is nonzero by the even case.
Thus the coefficient of \(P^{m+2}Q\) in \(H\) is nonzero.  Consequently

\[
\deg(D^{2m}B)=m+3,\qquad
\deg(D^{2m+1}B)=m+3,
\]

and the candidate formula follows for all \(k\).

## Kill conditions checked

- A zero coefficient in \(u^3\) would kill the even argument.  Equation
  (2) rules this out term-by-term over \(\mathbb Q\).
- A second monomial of the same maximal ordinary degree would make
  evaluation on \(Q=0\) insufficient.  Solving
  \(2a+3b=6+k\) shows the minimal admissible \(b\) is unique:
  \(b=0\) for even \(k\), \(b=1\) for odd \(k\).
- The odd transfer would fail if the next even iterate could be supplied by
  the \(54Q\partial_P\) term at \(Q=0\).  That term vanishes identically
  there, leaving exactly (4).
- Characteristic dividing \(12\), \(108\), \(324\), or the recurrence
  denominators is outside the argument.  The present campaign is over
  \(\mathbb Q\), so all divisions and cancellations are valid.

## Intended formal surface

The Lean carrier should certify only the arithmetic core:

1. positivity propagates through the sign-normalized quadratic recurrence;
2. the corresponding cubic convolution is positive and hence nonzero;
3. the even/odd indexing expressions both equal
   \(3+\lfloor k/2\rfloor\).

The identifications of this recurrence with the formal \(D\)-flow,
coefficient extraction with \(D^{2m}B\), weighted-homogeneous support, and
the odd-to-even polynomial relation remain mathematical arguments in this
audit.  Encoding those objects would require a separate formal-power-series
and multivariate-polynomial development and is not represented by the
arithmetic carrier.

## Provider-free LeanMill ratification

The arithmetic carrier is
[`AxiomPackJacobianCuspExactDegreeArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianCuspExactDegreeArithmetic.lean).
Its terminal target
`cusp_exact_degree_arithmetic_terminal_certificate` passed the
provider-free carried-theorem route with zero inference calls:

- recompilable source/closure SHA-256:
  `a4464055ea8e90bfdfd0a85de9670ce12c08a234c9f9d815acac01be55e40ff2`;
- proof SHA-256:
  `013acc1167ff02d648e2c65b23caa1f35299dba31eee8db8f58103dfdf3523d6`;
- identical posed/closed target-signature SHA-256:
  `f8d7d067c6f8895c9f274b93016d848d675ee33dc27b61396b965ca1c79874c1`;
- kernel-parity record SHA-256:
  `eda335d95ae2298c7651ae205e2d1296994c1da4fff5f2d6ab54655e8c5e2e57`;
- closure-certificate record SHA-256:
  `bef9566037c0d9324e614403f4b0c6fc60da74fe8ff09776535b998b1775dc3e`;
- governed closure:
  [`cusp_exact_degree_arithmetic_terminal_certificate_a4464055ea8e.lean`](../../../ztare_proofs/closures/AxiomPackJacobianCuspExactDegreeArithmetic.cusp_exact_degree_arithmetic_terminal_certificate_a4464055ea8e.lean).

Statement integrity, target identity, the matched negated-conclusion control,
and the axiom allowlist all passed.  This ratifies the arithmetic carrier
within the formal boundary declared above.
