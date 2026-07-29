# Filtered cusp Poisson sections: associated-graded eigenquestion

**Status:** preregistered before promotion of the graded uniqueness theorem

## Eigenquestion

Let \(W_{\le m}\mathbb Q[X,Y]\) be the cusp-weight filtration for

\[
\operatorname{wt}(X)=2,\qquad \operatorname{wt}(Y)=3,
\]

and let restriction be

\[
\operatorname{res}(K)=K(r^2,r^3).
\]

Suppose a linear section selects \(u_m\in W_{\le m}\) for every \(m\ge5\)
such that

\[
\operatorname{res}(u_m)=r^m
\]

and its span is closed under the planar Poisson bracket.  Must the top
weighted component of \(u_m\) be the parity representative

\[
t_m=
\begin{cases}
X^{m/2},&m\text{ even},\\
X^{(m-3)/2}Y,&m\text{ odd},
\end{cases}
\]

and hence force

\[
\deg u_m\ge\left\lfloor\frac m2\right\rfloor?
\]

This is the natural nonhomogeneous, triangular successor to the graded
rank-one theorem.  It does not allow representatives with cusp weight above
their target weight, nor does it allow extra stabilizer generators outside
the image of the section.

## Proposed mechanism

Write

\[
u_m=\bar u_m+u_m^{<m},
\]

where \(\bar u_m\) is homogeneous of cusp weight \(m\).  Restriction
preserves cusp weight.  Since

\[
\operatorname{res}(u_m)=r^m,
\]

the top component satisfies

\[
\operatorname{res}(\bar u_m)=r^m,
\]

while every lower component restricts to zero.

The Poisson bracket has filtered degree \(-5\):

\[
\{W_{\le m},W_{\le n}\}\subseteq W_{\le m+n-5}.
\]

If

\[
\{u_m,u_n\}=\sum_{k\ge5}c_k u_k,
\]

then restriction and the filtration bound should force \(c_k=0\) for
\(k>m+n-5\).  Taking weight \(m+n-5\) would therefore give

\[
\{\bar u_m,\bar u_n\}
=c_{m+n-5}\bar u_{m+n-5}.
\]

Thus the top components form a graded rank-one Poisson section.  The
graded uniqueness theorem would imply \(\bar u_m=t_m\).  Different cusp
weights have disjoint monomial support, so lower-weight terms cannot cancel
the ordinary-degree-\(\lfloor m/2\rfloor\) monomial in \(t_m\).

## Counterattacks

1. **High-index cancellation.**  Check that a finite combination of
   \(u_k\) with \(k>m+n-5\) cannot cancel its restriction while leaving a
   lower filtered polynomial.  Independence of the monomials \(r^k\) should
   exclude this.

2. **Top-bracket cancellation.**  When
   \(\{\bar u_m,\bar u_n\}=0\), no graded constraint is generated.  The
   graded theorem already permits zero brackets, so the reduction must use
   exactly its nonzero-bracket hypothesis and no stronger one.

3. **Degree cancellation.**  Verify that ordinary-degree terms from
   distinct cusp weights cannot be the same monomial.  A monomial has a
   unique cusp weight \(2a+3b\), so cross-weight cancellation is impossible.

4. **Category escape.**  A moving contact may use target Hamiltonians whose
   cusp weight exceeds the restriction weight, or a Poisson algebra with
   additional kernel directions.  Those cases are outside this theorem and
   remain active successor routes.

## Success and kill conditions

- **Success:** a complete associated-graded proof that every triangular
  filtered rank-one Poisson section has ordinary-degree rate at least
  \(1/2\), with equality achieved by the parity section.
- **Kill:** an explicit triangular section whose top components fail the
  graded closure rule, or a valid high-index cancellation omitted above.
- **Campaign boundary:** success excludes nonhomogeneous triangular
  rank-one cancellation.  It does not determine the moving symmetric
  contact invariant \(\sigma_{\rm ct}\).

## Intended verification surface

First prove the filtered-to-graded implication on paper.  Reuse the existing
graded arithmetic certificate for the classified top components.  Add a new
formal carrier only if it captures the filtration implication itself rather
than duplicating the exponent-pair classification.

## Settled theorem

The associated-graded reduction succeeds.

### Theorem

Let \(u_m\in W_{\le m}\mathbb Q[X,Y]\), \(m\ge5\), be a family with

\[
\operatorname{res}(u_m)=r^m.
\]

If

\[
\{u_m,u_n\}\in\operatorname{span}_{\mathbb Q}\{u_k:k\ge5\}
\]

for every \(m,n\ge5\), then the cusp-weight-\(m\) component of \(u_m\) is
exactly

\[
\operatorname{gr}_m(u_m)=
\begin{cases}
X^{m/2},&m\text{ even},\\
X^{(m-3)/2}Y,&m\text{ odd}.
\end{cases}
\]

Consequently

\[
\boxed{\deg u_m\ge\left\lfloor\frac m2\right\rfloor}
\]

for every \(m\ge5\).  Equality is attained by the parity section itself.

### Proof

Put \(w=m+n-5\).  The bracket filtration gives

\[
\{u_m,u_n\}\in W_{\le w}.
\]

Write its finite image expansion as

\[
\{u_m,u_n\}=\sum_{k\ge5}c_k u_k.
\]

After restriction, the right-hand side is

\[
\sum_{k\ge5}c_kr^k,
\]

whereas the left-hand side has cusp weight at most \(w\).  Linear
independence of the monomials \(r^k\) forces

\[
c_k=0\qquad(k>w).
\]

Taking the weight-\(w\) component now yields

\[
\{\operatorname{gr}_m(u_m),\operatorname{gr}_n(u_n)\}
=c_w\operatorname{gr}_w(u_w).
\]

No lower component contributes at weight \(w\), because the bracket lowers
the sum of cusp weights by exactly five.  Also,

\[
\operatorname{res}(\operatorname{gr}_m(u_m))=r^m,
\]

since restriction preserves cusp weight.  The top components therefore
form a graded rank-one Poisson section.

For completeness, the polynomial-to-monomial reduction is intrinsic.  The
weight-five component is \(XY\).  On monomials of a fixed cusp weight,

\[
\operatorname{ad}_{XY}(X^aY^b)
=\frac{b-a}{6}X^aY^b
\]

has simple spectrum: the simultaneous equations

\[
2a+3b=2c+3d,\qquad b-a=d-c
\]

imply \(a=c\) and \(b=d\).  Closure with the weight-five line forces each
top component to be one monomial, and its restriction fixes its coefficient
to one.  The graded classification then gives the displayed parity family.

Finally, monomials of distinct cusp weight are disjoint.  Hence no
lower-weight component of \(u_m\) can cancel the parity monomial in
\(\operatorname{gr}_m(u_m)\), including when another term has the same
ordinary degree.  This proves the degree bound.

### Updated boundary

The \(1/3\)-rate route is now excluded for both homogeneous and
nonhomogeneous **triangular rank-one** Poisson sections.  The remaining
escapes have a sharper form:

1. admit target Hamiltonians of cusp weight above the target restriction
   weight;
2. enlarge the Poisson algebra by independent \(C\)-stabilizer directions;
3. use positive transverse layers and the paired source action of the
   moving family.

The theorem does not exclude any of these three categories.
