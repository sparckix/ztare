# Moving-family admissibility of the parity Poisson section

**Status:** preregistered before the constrained moving-contact replay

## Eigenquestion

The unique graded rank-one cusp section is the Poisson subalgebra spanned by

\[
X^a\quad(a\ge3),\qquad
X^aY\quad(a\ge1),
\]

together with constants.  Its weight-\(m\) representative has ordinary
degree \(\lfloor m/2\rfloor\), and the algebra is closed under the Poisson
bracket.

Can the full normalized moving contact be solved coefficientwise with every
instantaneous target Hamiltonian in this parity algebra?  If so, what source
degree is forced, compared with:

- the unrestricted target control;
- the higher-rank cone \(b\ge1,\ a\le2b\)?

## Exact finite test

Reuse the moving-contact replay and replace only the target-support
predicate.  In normalized \(X,Y\) exponents, permit:

\[
(0,0),\qquad (a,0)\ (a\ge3),\qquad (a,1)\ (a\ge1).
\]

The general target lift conditions still exclude \(X,X^2,Y\).  At
instantaneous order \(j\), keep the natural cusp-weight window

\[
\operatorname{wt}K_j\le j+6
\]

and solve the exact recursive equation

\[
\partial_sF_s=X_{K_s}(F_s)+dF_sV_s
\]

with the same strict source lift and weighted-divergence conditions used in
the cone and unrestricted branches.

## Counterattacks

1. **Basis-vector filtering error:** restrict the complete polynomial span
   by the support predicate through a kernel calculation.  Do not discard
   \(C\)-normal basis vectors before allowing their forbidden monomials to
   cancel.

2. **Rank-one ambiguity:** the parity algebra has one monomial at each cusp
   weight, but a coefficient \(K_j\) may contain several weights.  The
   predicate must enforce the algebra above, not a single monomial per
   parameter order.

3. **Lower affine freedom:** carry every lower-order null direction into
   the next solve before declaring a minimum source cap.

4. **Finite extrapolation:** the implemented orders can compare categories
   and expose a recurrence candidate; they cannot establish an asymptotic
   source slope.

## Success and kill conditions

- **Finite success:** exact parity-valued solutions through every currently
  supported moving order, with complete rank and lower-affine controls.
- **Finite kill:** one exact moving order is inconsistent in the complete
  parity target window.
- **Comparative yield:** a source-cap profile that separates parity,
  higher-rank cone, and unrestricted controls.
- **All-order success:** a filtered recurrence proving parity-valued target
  integration, coefficientwise finite support, and a source logarithmic
  slope bound.

## Intended verification surface

The existing support-restriction operation should accept this predicate as
data.  No new solver branch or Jacobian-specific linear algebra is needed.

## Exact finite result

The shared complete-affine replay is
[`gauge_moving_section_affine_extension.py`](gauge_moving_section_affine_extension.py);
the rank and cokernel certificates are collected in
[`gauge_moving_sections_extended_result.md`](gauge_moving_sections_extended_result.md).

Through instantaneous order six, the exact parity source-cap profile is

\[
\boxed{(5,5,7,9,11,13,15)}.
\]

The complete affine dimensions after each order are

\[
(0,0,1,3,6,10,15).
\]

At order six, source cap fourteen is inconsistent:

\[
\operatorname{rank}M=241,\qquad
\operatorname{rank}[M\mid r]=242
\]

for the \(533\times255\) joint system carrying all ten lower directions.
Cap fifteen is the first consistent cap, with a \(569\times287\) matrix of
rank \(272\).

The comparison cone has two weight-twelve target symbols and passes at cap
fourteen.  Parity has only \(X^6\) at that weight and requires cap fifteen.
This exact one-degree separation survives complete lower affine carry.  It
is a finite language comparison, not an asymptotic source or logarithmic
degree theorem.
