# Moving-family admissibility of the minimum-section Lie cone

**Status:** preregistered; exact replay extended through instantaneous order
six with complete affine carry

## Eigenquestion

Let

\[
\mathfrak c
=\operatorname{span}_{\mathbb Q}
\{X^aY^b:b\ge1,\ a\le2b\},
\qquad X=-P/3,\quad Y=-Q/2.
\]

The minimum cusp section generates a Poisson Lie subalgebra inside
\(\mathfrak c\), with sharp ordinary-degree/cusp-weight rate \(3/7\).
Can the instantaneous target Hamiltonian in the full normalized moving
contact be chosen coefficientwise in \(\mathfrak c\), while the paired
source field remains polynomial and satisfies the declared source lift and
weighted-area conditions?

The first-order target Hamiltonian used in the canonical gauge contains a
bare \(X^3\) term and therefore lies outside \(\mathfrak c\).  The seed
stabilizer quotient shows that target representatives may be shifted by
\(C=X^3-Y^2\) together with a source response.  The discriminating question
is whether that shift can place the **complete moving connection** in
\(\mathfrak c\), rather than only its seed restriction.

## Exact finite test

At each instantaneous parameter order, solve

\[
\partial_sF_s=X_{K_s}(F_s)+dF_sV_s
\]

coefficientwise with:

1. \(K_j\) in the complete target lift window;
2. every monomial of \(K_j(X,Y)\) satisfying \(b\ge1\) and \(a\le2b\),
   apart from an irrelevant additive constant;
3. \(V_j\) polynomial, weighted-divergence-free, and in the strict source
   lift category;
4. all lower-order transport terms retained exactly.

Run the same exact linear system without the cone restriction as a positive
control.  Compare ranks, minimum source degree, target support, and the
first inconsistent order if one occurs.

## Attack vectors and counterattacks

1. **Seed representative shift.**  Replace the canonical weight-six
   Hamiltonian by its minimum \(Y^2\) representative and solve for the
   paired source stabilizer response.

   **Counterattack:** the strict source scalar obstruction
   \(\omega(a,b)=2[r^2]a+3[r^3]b\) may block this particular shift even
   when the campaign polar witness had \(\omega=0\).

2. **Recursive cone solve.**  Carry the cone constraint through the exact
   instantaneous recurrence, not through an independently refitted equation
   at each order.

   **Counterattack:** a low-order pass can hide a later transverse
   incompatibility.  Record it only as a prefix result until an all-order
   module recurrence is proved.

3. **Magnus closure.**  If every instantaneous coefficient lies in
   \(\mathfrak c\), its target Magnus logarithm also lies there because
   \(\mathfrak c\) is a Lie subalgebra.

   **Counterattack:** coefficientwise polynomiality still requires finite
   target support at each parameter order; a target-adic infinite tail is
   inadmissible.

4. **Source-side cost.**  A target cone construction is useful for the
   symmetric statistic only if the paired source logarithm has a compatible
   asymptotic degree bound.

   **Counterattack:** a cone-constrained target solve may simply transfer
   all growth to the source.

## Success and kill conditions

- **Finite success:** every exact available moving order admits a recursive
  cone-constrained solution, with no higher source-degree cost than the
  declared comparison window.
- **Finite kill:** one exact order has full-system rank equal to augmented
  rank but cone-system rank below augmented rank.
- **All-order success:** an explicit filtered module recurrence produces
  cone-valued \(K_s\), polynomial \(V_s\), coefficientwise finite support,
  and logarithmic degree bounds on both sides.
- **Campaign boundary:** a finite pass or failure is scientifically useful
  but does not alone determine \(\sigma_{\rm ct}\).

## Intended verification surface

Reuse the existing complete instantaneous contact solver and its target/source
lift bases.  Add a substrate-independent target-support predicate rather
than a Jacobian-specific solver branch.  The output must expose the removed
monomials and exact rank delta so the result is auditable.

## Exact finite result

The initial cone-constrained replay exists through family derivative order
four.  The later natural-weight, complete-affine extension through
instantaneous order six is recorded in
[`gauge_moving_sections_extended_result.md`](gauge_moving_sections_extended_result.md).

The replay is
[`gauge_moving_lie_cone_admissibility.py`](gauge_moving_lie_cone_admissibility.py).
It reuses `_family_jets`, `_hamiltonian_field_window`, `_monomials`,
`_coefficient_system`, and `_particular_solution`.  The only new operation
is a general kernel construction that restricts a polynomial span by a
monomial-support predicate.  In particular, it does not discard individual
\(C\)-normal basis elements: it retains every linear combination whose
forbidden monomials cancel.

Write the derivative-normalized instantaneous coefficients as

\[
K_s=\sum_{j\geq0}\frac{s^j}{j!}K_j,\qquad
V_s=\sum_{j\geq0}\frac{s^j}{j!}V_j.
\]

The exact constrained solution is

\[
\begin{aligned}
K_0={}&-\frac18PQ-\frac1{16}Q^2,\\
K_1={}&\frac1{224}P^2Q-\frac{401}{6720}PQ
        +\frac{167}{2688}Q^2,\\
K_2={}&-\frac{17}{1792}P^2Q+\frac{29}{3584}PQ^2
        +\frac{29}{24192}PQ-\frac{3091}{71680}Q^2,\\
K_3={}&\frac{927}{71680}P^2Q-\frac5{112}PQ^2
        -\frac5{756}PQ+\frac{507}{28672}Q^3
        +\frac{169}{43008}Q^2.
\end{aligned}
\]

Every nonconstant monomial satisfies \(b\geq1\) and \(a\leq2b\).
In the normalized \(X,Y\) coordinates, their maximum cusp weights are

\[
6,\ 7,\ 8,\ 9,
\]

at instantaneous orders \(0,1,2,3\), respectively.  Thus this finite prefix
has exactly the natural bound

\[
\operatorname{wt}K_j\leq j+6.
\]

The ordinary target degrees are

\[
(2,3,3,3).
\]

### First representative shift

Let

\[
H_{\mathrm{base}}=-\frac14Q^2-\frac1{36}P^3,\qquad
K_*=-\frac{4P^3-18PQ+27Q^2}{12}.
\]

Then the cone representative is obtained by the exact moving stabilizer
shift

\[
K_0=H_{\mathrm{base}}-\frac1{12}K_*.
\]

The \(P^3\) coefficient cancels, while the paired source response is
polynomial of component degree five and satisfies the strict lift and
weighted-area equations.

### Initial broad-window rank certificates (superseded by affine replay)

These were the target windows in the initial order-three implementation.
The natural-weight and complete-affine certificates through order six are
the authoritative comparison in
[`gauge_moving_sections_extended_result.md`](gauge_moving_sections_extended_result.md).
The initial target windows were held fixed while testing source caps.  They are the
complete \(C\)-normal component windows \((8,10),(8,10),(10,12),(12,14)\).
After target lift and cone restriction, their target dimensions are
\(3,3,4,5\).

| \(j\) | first source cap | matrix | rank | augmented rank | nullity | previous-cap rank/augmented rank |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 5 | \(134\times42\) | 42 | 42 | 0 | \(30/31\) at cap 4 |
| 1 | 5 | \(134\times42\) | 42 | 42 | 0 | \(30/31\) at cap 4 |
| 2 | 7 | \(197\times73\) | 72 | 72 | 1 | \(57/58\) at cap 6 |
| 3 | 9 | \(272\times112\) | 110 | 110 | 2 | \(91/92\) at cap 8 |

The selected source fields have component-degree profile

\[
\boxed{(5,5,7,9)}.
\]

Every component is polynomial, every strict source lift check passes, and

\[
\partial_v(\gamma^2V_{j,v})
+\partial_t(\gamma^2V_{j,t})=0
\]

at each order.  Direct coefficient extraction replays

\[
\partial_sF_s=X_{K_s}(F_s)+dF_sV_s
\]

through \(s^3\), so all lower target and source transport is present.

At order two the constrained system has a one-dimensional homogeneous
direction with target Hamiltonian \(-PQ\) and source component degrees
\((7,7)\).  Carrying this parameter symbolically into order three does not
lower the cap: the joint cap-eight system has rank \(91\) and augmented
rank \(92\), while cap nine is consistent.  The complete later replay
carries the full joint nullspace, rather than interpreting the zero value
of one selected particular solution as uniqueness.

### Unrestricted positive control

Removing only the cone condition, while retaining the same target lift,
source lift, weighted-area equation, lower transport, and complete target
windows, gives:

| \(j\) | first source cap | matrix | rank | augmented rank | nullity |
|---:|---:|---:|---:|---:|---:|
| 0 | 0 | \(87\times4\) | 4 | 4 | 0 |
| 1 | 5 | \(135\times43\) | 42 | 42 | 1 |
| 2 | 5 | \(161\times45\) | 44 | 44 | 1 |
| 3 | 6 | \(216\times62\) | 61 | 61 | 1 |

Its source profile is

\[
(0,5,5,6),
\]

recovering the previously audited instantaneous positive controls.

## Interpretation and boundary

The finite target-side test succeeds: the moving family does not force a
bare \(X^3\) term back into the instantaneous Hamiltonian through the
available order, and its target coefficients occupy the sharp
minimum-section cone with the natural weight window.

The source-side counterattack is active.  The constrained source cost is
strictly higher than the unrestricted control at orders two and three.
Consequently this prefix supports the conditional \(3/7\) Magnus envelope
on the target, but gives no symmetric-statistic improvement by itself.

This is a finite prefix theorem.  It does not prove an all-order
cone-valued recurrence, an asymptotic bound for the paired source logarithm,
or the value of \(\sigma_{\rm ct}\).
