# Coupled-Julia common-equilibrium saturation

## Eigenquestion

After filtered Darboux rigidity forces a persistent irreducible factor to
have only `F`-weight zero, what exact algebraic statement removes that
factor without assuming that the two polynomial generators are coprime?

## Coefficient-separation theorem

Let `K` be a field, let `p,q ∈ K[Y]`, and let `v ∈ K[F]` be nonzero and
tangent to order at least two:

\[
v_1=0,\qquad d=\deg v\ge 2.
\]

For nonzero scalars `c,L ∈ K`, form the coupled relation as a polynomial
in the visible variable `F` with coefficients in `K[Y]`:

\[
R(F,Y)=c\,p(Y)v(F)-L\,Fq(Y).
\]

Then every `a ∈ K[Y]` satisfies

\[
\boxed{\quad C(a)\mid R\quad\Longleftrightarrow\quad
       a\mid p\ \text{and}\ a\mid q.\quad}
\]

Here `C : K[Y] → K[Y][F]` is the constant-polynomial embedding.  No
irreducibility or squarefreeness hypothesis on `a` is needed.

The forward implication uses two separated coefficients:

\[
[F^1]R=-Lq(Y),\qquad
[F^d]R=cv_d p(Y).
\]

Both scalar multipliers are units.  The reverse implication is immediate
term by term.  Replacing `a` by `a^m` gives the multiplicity statement

\[
v_{C(h)}(R)=\min\{v_h(p),v_h(q)\}
\]

for every irreducible `h ∈ K[Y]`.

## Full saturation, not universal-factor cancellation

Let `g = gcd(p,q)`, with `p=gp₀` and `q=gq₀`.  The theorem gives

\[
R=C(g)R_0,
\qquad
R_0=c\,p_0(Y)v(F)-L\,Fq_0(Y).
\]

Every `F`-independent divisor of `R₀` divides both `p₀` and `q₀`,
so it is a unit.  This is the needed consequence after the filtered Darboux
dichotomy: saturation must use the complete common-equilibrium gcd, including
all multiplicities, rather than only the universal `Y^2` factor.

For the coupled-Julia relation before saturation, `v=q`.  After hidden gcd
division, `v` remains the original visible polynomial while the hidden
factor becomes `q₀`.  Keeping these as separate arguments is essential;
silently replacing `v(F)` by `q₀(F)` would prove a theorem about a different
relation.

The exact downstream adapter chain is therefore:

1. finite multiplicity descent produces a persistent Darboux prime dividing
   the saturated initial relation;
2. filtered weight rigidity and one-weight contraction put the
   `F`-independent branch in the form `C(a)`, up to association;
3. the coefficient-separation theorem gives `a ∣ p₀` and `a ∣ q₀`;
4. coprimality of `p₀,q₀` makes `a`, hence `C(a)` and the associated prime,
   a unit, contradicting primality.

This closes the algebraic `F`-independent branch.  The separate
`F`-dependent/endpoint-variable branch and the construction of the finite
derivative prefix remain outside this lemma.

The adversary

\[
p=Y^2(Y-1),\qquad q=Y^2(Y-1)(Y-2)
\]

has the persistent content `Y^2(Y-1)`.  It disproves naive coprimality and
universal-`Y^2`-only cancellation, but it satisfies the boxed theorem.
Likewise

\[
p=Y^3(Y-1)^2,\qquad q=Y^2(Y-1)^5(Y-2)
\]

has relation content `Y^2(Y-1)^2`, exhibiting the minimum-multiplicity
law.

## Exceptional charts and tangent cancellation

For a common equilibrium `r` over an algebraic extension, translate
`Y=r+T`.  If

\[
m_r=\min\{\operatorname{ord}_r p,\operatorname{ord}_r q\},
\]

then the translated gcd is `T^m_r` times a unit.  On a selected
nonconstant tangent branch `T=η(u)`, where

\[
\eta(0)=0,\qquad \eta'(0)\in K^\times,
\]

`FormalTangentSubstitutionInjectivity` implies that every nonzero translated
polynomial remains nonzero after substitution.  Hence the full gcd value may
be canceled in the power-series domain even when it has positive `u`-order;
it need not be a unit.

The only chart on which a common-equilibrium factor evaluates to zero is the
constant chart `η=0`.  Both generators vanish there, so both autonomous
flows fix the point.  Such a chart cannot supply the selected invertible
tangent endpoint.  Thus the chart partition is:

1. nonroot chart: the gcd value is already a unit;
2. nonconstant root chart: the gcd value has positive order but is nonzero
   and cancels in the domain;
3. constant root chart: stationary and excluded by the selected tangent
   endpoint condition.

Repeated and non-rational roots require no separate factor argument: powers
and scalar extension commute with the divisibility theorem, while translated
tangent injectivity handles each local chart.

## Kill conditions

1. If the outer generator has a linear term, the `F^1` row mixes `p` and
   `q`; the coefficient-separation theorem above is unavailable.
2. A zero generator or zero coefficient multiplier destroys one of the two
   isolating rows and must remain excluded by the flow data.
3. Canceling only `Y^2` is invalid when the generators have another common
   factor.
4. Squarefree gcd language loses repeated-equilibrium multiplicities.
5. Tangent substitution proves nonvanishing, not invertibility.  Cancellation
   uses the power-series domain.
6. A constant equilibrium chart cannot be discarded without the selected
   nonconstant/invertible-tangent endpoint premise.

## Intended formal surface

The smallest reusable kernel is a coefficient-ring theorem over
`K[Y][F]`:

```text
C a ∣ coupledRelation p visibleOuter q ↔ a ∣ p ∧ a ∣ q
```

under `visibleOuter.coeff 1 = 0` and
`2 ≤ visibleOuter.natDegree`.  Its proof should use
`Polynomial.C_dvd_iff_dvd_coeff` at indices `1` and
`visibleOuter.natDegree`.
The same theorem applied to `a ^ m` owns multiplicities.  The existing
`FormalTangentSubstitutionInjectivity` module owns nonzero substitution and
cancellation; it should be consumed rather than duplicated.

This kernel removes `F`-independent persistent primes after full gcd
saturation.  It does not prove that the derivative-prefix ideal is proper or
unit, construct the selected continuation, or show that the remaining
finite prolongation ideal becomes the unit ideal.

## Outcome

`FormalCoupledJuliaCommonEquilibriumSaturation` now proves the boxed
equivalence directly in `K[Y][F]`, with separate visible-outer and
hidden-outer inputs, together with its arbitrary-power form.  An `IsCoprime`
corollary says that every visible-constant divisor of the fully saturated
relation is a unit.  The module also binds such a divisor to the existing
tangent-germ cancellation theorem.  Focused compilation and the named module
build pass.  The axiom audit reports only `propext`, `Classical.choice`, and
`Quot.sound`.

An exact adversarial replay with

\[
p=Y^3(Y-1)^2,\qquad q=Y^2(Y-1)^5(Y-2)
\]

returns coefficient content `Y^2(Y-1)^2`, and content one after division
by that full gcd.  This confirms that the kernel retains multiplicity and
that the extra `Y-1` equilibrium cannot be omitted.
