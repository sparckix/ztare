# Formal path lifting through a unit-Jacobian polynomial map

**Status:** pre-proof pencil for
`H-AXIOMPACK-JACOBIAN-ETALE-LIFT-20260720-12`

## Eigenquestion

Did the order-six computation detect a special cancellation of the weighted
lift, or did it repeatedly instantiate the formal inverse-function mechanism
available at every polynomial map with constant unit Jacobian?

## Candidate theorem

Let `k` be a characteristic-zero field, let

\[
F_0:k^m\longrightarrow k^m
\]

be polynomial with `det DF_0=c in k^*`, and let

\[
G_s=F_0+\sum_{n\ge1}s^nG_n
\]

be a vector of formal series with polynomial coefficients.  Then there is a
unique

\[
\psi_s=\operatorname{id}+\sum_{n\ge1}s^nY_n,
\qquad Y_n\in k[x_1,\ldots,x_m]^m,
\]

such that `F_0 o psi_s=G_s`.

At order `n`, subtract the contribution formed from `Y_1,...,Y_{n-1}`.
The remaining equation is

\[
DF_0\,Y_n=R_n.
\]

Since

\[
(DF_0)^{-1}=c^{-1}\operatorname{adj}(DF_0)
\]

has polynomial entries, `Y_n` is polynomial.  The same linear equation gives
uniqueness.  A series tangent to the identity has a compositional inverse
recursively, so `psi_s` is a formal source automorphism.

## Symmetry and volume

If a group action makes `F_0` and `G_s` equivariant, conjugating `psi_s` by
the action produces another solution; uniqueness should force equivariance.
If `det DF_0=det DG_s=c`, the formal chain rule gives

\[
c\,\det D\psi_s=c,
\]

and hence `det D psi_s=1`.  Thus coefficientwise polynomial,
volume-preserving equivariant contact is generic under these hypotheses.

For the current quotient calculation, the apparent `gamma^2` denominator is
the shadow of passing from the three-variable unit-Jacobian map to invariant
coordinates.  The full polynomial adjugate supplies the lift that quotient
inversion discovers by cancellation.

## Attack vectors and counterattacks

1. **Polynomial recursion.** Counterattack: exhibit an order where nonlinear
   substitution makes `R_n` nonpolynomial.  This should be impossible because
   `F_0` and every earlier `Y_j` are polynomial.
2. **Equivariance.** Counterattack: find nonuniqueness in the formal source
   solution.  The invertible `DF_0` coefficient equation should exclude it.
3. **Volume preservation.** Counterattack: track the target correction and
   check whether it has a coefficientwise-polynomial volume-preserving lift;
   otherwise the chain-rule conclusion does not apply to that gauge.
4. **Family-specific residue.** Counterattack: show the degree sequence depends
   on the chosen target gauge or source parameterization.  If so, its raw
   parity is not an invariant; the correct object is the minimal degree over
   allowed gauges.

## Exact kill conditions

- `det DF_0` is not a scalar unit in the full source coordinates;
- the normalized family or target flow lacks polynomial coefficients at some
  formal order;
- the chosen target Hamiltonian field has no equivariant polynomial lift;
- quotient coefficients fail to agree with the unique full-source lift;
- or the alleged degree law changes under an admissible gauge of lower degree.

## Intended formal surface

First formalize a finite-order ring-level recursion lemma or a compact
coefficient identity that exposes the adjugate mechanism.  Do not paste the
order-six tables into the kernel.  A separate family-specific theorem is
warranted only after degree growth is made gauge-invariant.
