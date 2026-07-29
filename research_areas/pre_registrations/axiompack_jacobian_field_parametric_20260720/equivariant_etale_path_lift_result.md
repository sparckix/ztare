# Formal-etale explanation of the Jacobian jet calculations

**Status:** standard mechanism identified; coefficient step kernel-ratified

## Verdict

The order-six polynomial source contact is forced by the seed's constant unit
Jacobian.  It is a general formal-lifting mechanism rather than a special
cancellation theorem for the public weighted lift.

Let `F_0 : A^m -> A^m` be polynomial over a field `k`, with
`det DF_0=c in k*`, and let

\[
G_s=F_0+\sum_{n\ge1}s^nG_n
\]

have polynomial coefficients.  There is a unique compatible family

\[
\psi_N\in\operatorname{Aut}_{k[s]/(s^{N+1})}
  (\mathbb A^m_{k[s]/(s^{N+1})}),
\qquad \psi_N\equiv\operatorname{id}\pmod s,
\]

such that

\[
F_0\circ\psi_N=G_s\pmod{s^{N+1}}.
\]

Equivalently, there is a coefficientwise-polynomial `s`-adic source
automorphism.  This supplies no polynomial automorphism after specializing
`s` to a nonzero scalar.

## Two proofs of the mechanism

### Formal etaleness

Present the source coordinate ring over the target coordinate ring using the
relations `y_i-F_{0,i}(x)`.  Their relation Jacobian is `-DF_0`, whose
determinant is a unit.  The Jacobian presentation criterion makes `F_0`
etale.  The defining unique-lift property then lifts the identity sheet across
the successive square-zero parameter thickenings.  Uniqueness makes the lifts
compatible in `N` and equivariant whenever the input family is equivariant.

The relevant standard references are the Stacks Project
[Jacobian presentation criterion](https://stacks.math.columbia.edu/tag/03PA),
[formal-etale lifting definition](https://stacks.math.columbia.edu/tag/00UP),
and [functorial characterization](https://stacks.math.columbia.edu/tag/025K).

### Coefficient recursion

Assume `Y_1,...,Y_{n-1}` have been constructed.  At order `n`, all nonlinear
lower-order substitutions form a polynomial residual `R_n`; the new term
satisfies

\[
DF_0Y_n=R_n.
\]

Since

\[
(DF_0)^{-1}=c^{-1}\operatorname{adj}(DF_0)
\]

has polynomial entries, `Y_n` is polynomial and unique.  This is precisely
the cancellation that appeared as division by `gamma^2` after passing to
quotient coordinates.

## Target gauge check

The Hamiltonian quotient field used in the order-six replay has a polynomial
three-variable lift

\[
(\dot x,\dot y,\dot z)=
\left(0,-\frac{xz}{2},\frac{y^2}{12}\right).
\]

For `v=xy` and `t=x^2z`, it induces

\[
(\dot v,\dot t)=\left(-\frac t2,\frac{v^2}{12}\right)
\]

and its coordinate divergence is zero.  Its formal flow therefore has
polynomial coefficients and preserves volume at every parameter order.  The
target correction is optional: formal right-triviality already applies to
the original polynomial deformation.

For the source series, volume preservation follows from
`det D(F_0 o psi_s)=det DF_s` and the constant unit determinants.  The
order-six quotient replay's coefficientwise divergence checks are compatible
with this conclusion, but are not a standalone proof of it: determinant
cross-terms between coefficients begin at order four.

## Why global noninjectivity is compatible

Formal etaleness follows one chosen special-fiber sheet across nilpotent
thickenings.  It does not produce a global inverse of `F_0`.  The unique
source series may have unbounded degree, so it need not specialize to a
finite polynomial automorphism for `s != 0`.  This is compatible with the
public generic-degree jump from three to four and the extra inverse branch
entering from infinity.

The ind-group setting also warns against promoting tangent or formal-orbit
data to global group equality: Furter and Kraft exhibit strict closed
ind-subgroups with the same Lie algebra in
[On the geometry of the automorphism groups of affine varieties](https://arxiv.org/abs/1809.04175).

## Ratified formal surface

[`AxiomPackJacobianEtalePathLift.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianEtalePathLift.lean)
checks over an arbitrary commutative ring that a determinant-one matrix's
adjugate gives the unique solution of every coefficient equation.  It also
checks the quotient identities of the target lift.  Provider-free LeanMill
governance closed the terminal coefficient-step theorem with:

- zero provider calls;
- closure-record SHA-256
  `fa798849981b715b043444aa31a4f3a5bdf5582947d5ead957a7ee57cc5bef73`;
- parity-record SHA-256
  `db491301798204c8ba29bc0a6759f184d5a2645e9fc258306ba888e4129f511f`;
- governed closure
  [`AxiomPackJacobianEtalePathLift.etale_path_lift_step_certificate_26ec5db5d257.lean`](../../../ztare_proofs/closures/AxiomPackJacobianEtalePathLift.etale_path_lift_step_certificate_26ec5db5d257.lean).

The kernel theorem certifies the recursive algebraic step.  The standard
nilpotent-thickening induction is documented here rather than represented as
an order table.

The determinant-chain repair is also explicit in the same module: equal
nonzero outer and composite determinants force the intervening source
Jacobian to be one. Provider-free governance closed
`etale_path_lift_volume_certificate` with closure-record SHA-256
`034d7b7c801a1f92d83f2f1d5901f707b177de1820980dc50232011272125b8a`
and kernel-parity SHA-256
`d7df936b9060b54e404fd135d7061571e64bf25a98bc7362e6b2087b81809def`.

## Scientific residual

All-order removability is recovery.  The observed source degrees
`11,13,21,23,31` belong to one target gauge and may change under higher-order
target corrections.  A family-specific result now requires one of:

1. the minimum source/target degree required modulo `s^(N+1)`, optimized over
   the admissible equivariant volume-preserving gauge;
2. a proof that those minima are unbounded, hence the formal orbit arc is not
   algebraizable by a bounded-degree polynomial family; or
3. a sharp shell-support/cancellation invariant independent of gauge choice.

The generic-degree jump already forces qualitative unboundedness for the
unique source-only lift: a uniformly bounded source degree would give a
polynomial map over `k[[s]]`, hence over `k((s))`.  Its generic degree would
multiply with the seed degree, forcing `4=3m`, which is impossible.  The next
task is to state this argument with the exact algebraization hypothesis and
formalize its degree-multiplication step.  Extending the current recursion to
orders seven and eight would not distinguish the standard mechanism.
