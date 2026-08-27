# Formal residual coverage compiler result

**Date:** 2026-08-06
**Status:** v51 replay passed; root remains unratified

## Outcome

The active compiler now has one claim decomposition and one governed-support
registry. It replays 46 content-bound formal receipts. Forty-four DAG nodes
are covered bottom-up, eight inference rules are governed, and no enclosing
authority is issued.

The replay is
[`jacobian_critical_puiseux_formal_coverage.py`](jacobian_critical_puiseux_formal_coverage.py).
It preserves the established semantic certificates:

- single flow: `6c3a97ebae223d4c0dbf6762d1399d242ea951459d3e7ae44255be2575931926`;
- conditional two-flow obstruction: `190c7ff996246b663dc6ab94435aaea81fa8f8e4c009188badac06ec88bc963c`;
- adapter evidence: `bde0a8cd2e908b0795ad28e1838151691f20bda27170d699cdc1ccb6097e4151`;
- finite-equilibrium countermodel: `7858bb75adf8f7199b894d35a41b2a9211330a40cc534aee3acbe7aefbdc3210`;
- exact monodromy-residue adapter: `c27c46c0e1d4d83a93714ebe4fafe3dae4994320ceac592b2cfd273a5bce898d`.

The v51 identities are:

- decomposition: `7d2b7266c44cb9cddaac79ade0a822a3d356b7a0510b43a31df2d9e39fc0b4b6`;
- coverage certificate: `751972381243875f8daab5b5ccb5cfb42c1fc7831cd412b42728063d3bb05b02`;
- replay envelope: `457b902e4f5717877031b7e415877db20bad3fc1c422a22b66df8f8dbe3472d9`.

## Audit correction

The v32 graph understated and overstated different parts of the frontier.

First, exact governed supports for the complex single-flow obstruction and
complex Julia transport already existed but were omitted in favor of narrower
real-only parents. They are active in v34.

Second, the old finite/infinity branch split was false. The exact local
countermodel composes two finite equilibrium transitions with exponents
`3/2` and `2/3` to

```text
u + (77/12) u^2 + (376/81) u^(5/2) + O(u^3),
```

with no lower `u^(3/2)` shell. Finite Julia valuation classification now
separates regular-to-regular from equilibrium-to-equilibrium branches; it does
not identify every finite branch with an ordinary analytic germ.

## General prime-reduction kernel

[`FormalRationalRootModPrime.lean`](../../../ztare_proofs/ZtareProofs/FormalRationalRootModPrime.lean)
contains the substrate-neutral theorem
`rat_no_root_of_mod_prime_no_root`. For any integer polynomial and any
selected prime, it proves that:

1. survival of the leading coefficient modulo the prime; and
2. absence of roots of the reduced polynomial

exclude every rational root. The proof uses Mathlib's rational-root theorem,
canonical numerator/denominator scaling, and exact transport through
`Polynomial.scaleRoots`.

The Jacobian specialization is
[`FormalCriticalResidueIrrationality.lean`](../../../ztare_proofs/ZtareProofs/FormalCriticalResidueIrrationality.lean).
It defines the exact degree-seven eliminant, checks its reduction over
`ZMod 17` with kernel reduction, and proves every real root irrational.
The terminal theorem has:

- governed record: `b9ac4e8a487f757cde1870bbe795b92b122a502d288802bdd8731490b15a9cf7`;
- kernel-parity record: `30c0849fb14a8f082d8bb06c02a04ac5f54ecd373ceb82b178b8b9cd13918523`;
- content-bound receipt: `56e8457b58314944ac3ef2021891b2ca6f95841a88453786b5e90fe3b966db27`;
- formal proposition identity: `dfa6af3d7d46e67d15fe0186231f969e67616e167750768ce084639981550e0f`.

The previously governed
`FormalComplexMonodromyNonTorsion.complex_monodromy_non_torsion_terminal_certificate`
then proves that an irrational real residue gives
`exp(2*pi*i*rho)` infinite multiplicative order. Its content-bound receipt is
`a72e9f7832783458aa3e4df5bd52d3057d00e3e3ba08103b54bd8800fda5adbd`.

## Exact pole-to-monodromy binding

[`FormalCriticalMonodromyResidueBinding.lean`](../../../ztare_proofs/ZtareProofs/FormalCriticalMonodromyResidueBinding.lean)
constructs a real root of the exact pole polynomial in
`[-2/5, -3/10]`. Exact Bezout identities prove that the pole is simple and
the numerator does not cancel there. A complete degree-49 polynomial
factorization then places the logarithmic residue on the governed degree-seven
eliminant. The prime-reduction kernel proves that residue irrational, and the
complex-exponential kernel proves every positive monodromy power nontrivial.

The terminal theorem has:

- governed record: `25727111271dbc731e3d0c4cdc9688e64bad8a97d28daffa2895d29896b501a7`;
- kernel-parity record: `ca9c9294f633b66ee242df6e67e17b520a092b36c05ef3f6d54bc8e7bb6c3fa5`;
- content-bound receipt: `c78401d1f0a722b0c9a4d7499b7a9f12565a7bba0b90a8784d8b8ef443676ef2`;
- formal proposition identity: `4852ab2a062108f67917052bba456842ced24c13915bf979b2b606159b543a36`.

At v35 this governed infinite monodromy only for the displayed rational
differential; equality with the original critical connection was still a
separate leaf.  The v36 result below discharges that equality.

## Exact connection rationalization

[`FormalCriticalConnectionRationalization.lean`](../../../ztare_proofs/ZtareProofs/FormalCriticalConnectionRationalization.lean)
now discharges that equality in the rational-function field `RatFunc ℝ`. It
formalizes the two algebraic source-connection rows, proves the conic sheet
identity, checks the analytic derivative of the uniformizing coordinate,
normalizes the pulled-back velocity and radial denominator, and proves the
result is exactly the numerator and pole polynomial used by the governed
residue theorem. No exceptional-point premise or supplied simplification is
accepted.

The terminal theorem has:

- governed record: `dbc90efc8066be9b0897f097a114dd2c276c8431c8cd990b3a175e5f1e0517ac`;
- kernel-parity record: `42b941559cc67669a5795dbd9a5910b7131b8918598ec9bc2ee96978eb197cb3`;
- content-bound receipt: `ff3dacb701f8fc0bf97db0770ae54a88641fdc9f320968659ccfba9a7716c4c7`;
- formal proposition identity: `ed2eecd909969d52b6ff8fe08815363e52c877e9500117c38756bdc03fb92d32`.

Coverage v36 therefore had no remaining local arithmetic or rationalization
leaf in the monodromy branch. Its scalar endpoint-orbit assembly was the next
semantic inference.

## Exact logarithmic-loop realization

[`FormalAnalyticLogarithmicLoop.lean`](../../../ztare_proofs/ZtareProofs/FormalAnalyticLogarithmicLoop.lean)
defines a reusable circle-continuation carrier for a coefficient decomposed
as a logarithmic pole plus a regular term. It constructs the exponential
continuation path, proves the pulled-back scalar ODE, computes every repeated-
loop endpoint, and proves endpoint injectivity from non-torsion of the
multiplier. The terminal certificate has governed record
`1869287e878cffd4bac6db000609b64ae3a2f79a4c1a99d55ad80bb1c46d3d0f`
and kernel-parity record
`347bfcc2f43198054c42ac4a179559709dcd93c1fc2d5aa0af35c0f1ad336047`.

[`FormalCriticalHolonomyLoop.lean`](../../../ztare_proofs/ZtareProofs/FormalCriticalHolonomyLoop.lean)
specializes that kernel to the exact critical differential. It performs both
polynomial divisions needed to remove the selected simple pole, proves the
reduced denominator nonzero at the pole, constructs a local analytic
primitive, and derives an injective local endpoint orbit for every nonzero
initial value on the circle. It also retains the exact equality with the
original critical connection differential.

The specialization has:

- governed record: `54198f8b2fe5854ec115f6195de2383b17816cdb257a24d1294d7b3b47f24c33`;
- kernel-parity record: `37f39e4884122371bec62c696aacd28619425e98a8912213b6a5896fc3d8c3b7`;
- content-bound receipt: `5cc3011d1ab52aee73ad217317c387e1de695a9888c4c5b0e7cd4f057cda0a72`;
- formal proposition identity: `20e168e4af317b9103fd06fcfcf3292ad0195dd1d8e51d6ffc871953a789c230`.

Coverage v37 therefore pays
`critical_scalar_holonomy_infinite_monodromy` as a governed connection-
holonomy inference. Transporting a chosen two-flow factorization from its
germ basepoint to this loop is deliberately owned by the separate factor-loop
transfer leaf.

## v38 finite-route correction

The tentative finite-equilibrium shortcut fails. The exact negative-control
replay
[`gauge_polynomial_flow_finite_monodromy_countermodels.py`](../axiompack_jacobian_field_parametric_20260720/gauge_polynomial_flow_finite_monodromy_countermodels.py)
has certificate
`013cafdb99d8de33106059b9a6afe6475991a5e095221166c4a52549d19ec22a`.
For `y'=y^3`, it verifies two finite non-equilibrium time-one sheets and the
Julia identity exactly. For `y'=y^2(1-y)`, the Abel coordinate reduces the
selected time-one relation to `w*exp(w)=1`; its Lambert-W branches give
infinitely many finite regular sheets. Seventeen distinct branches are
sampled, while the classical all-branch fact remains outside formal
authority.

Coverage v38 therefore replaces
`two_flow_finite_equilibrium_chain_exclusion` with
`two_flow_finite_coupled_monodromy_exclusion`. The loop-transfer leaf must
retain the two Julia rows and their eliminated relation

```text
p(G) q(F) = F' p(x) q(G).
```

This prevents the compiler from turning finiteness into a root-set premise.
The count of open nodes is unchanged, but their mathematical content is now
strictly broader.

## Division-free coupled-Julia kernel

[`FormalCoupledJuliaElimination.lean`](../../../ztare_proofs/ZtareProofs/FormalCoupledJuliaElimination.lean)
now owns the algebraic consequence of the two Julia rows. Over any
commutative ring it constructs

```text
R(Y) = q(F) p(Y) - A F p(x) q(Y)
```

and proves `R(G)=0` from the inner Julia row, outer Julia row, and `F'=AF`.
It assumes no generator value nonzero and performs no quotient operation.

The terminal theorem has:

- governed record: `9a0b93843527fc75cb9c0121b79d9c89f726f2de29caaf341485bc56610785c2`;
- kernel-parity record: `12eb5debcb68f59547c9a0c41954dbedd1b1a186785610b6044264ca48b19e32`;
- content-bound receipt: `2453126559905d5f8b469193075b5d99f67b6964842edc421710e352acfd4945`.

Coverage v39 makes this the governed inference for
`two_flow_factorization_loop_continuation_transfer`. That node is now blocked
only by `two_flow_selected_factorization_continuation_carrier`, which must
construct the analytic lifts and Julia rows from an arbitrary selected
factorization.

## v40 finite-prolongation refinement

Five further governed terminals now isolate the algebraic mechanism needed
to exclude the complete finite lifted branch:

1. `FormalAnalyticPolynomialControlledTrajectory` constructs and locally
   uniquely determines `y'=c(z)p(y)` through every finite complex state;
2. `FormalCoupledJuliaDifferentialProlongation` derives the zero-th coupled
   relation and its first division-free total prolongation from analytic Julia
   rows;
3. `FormalPolynomialVectorFieldMultiplicity` proves that iteration of
   `D_p(Q)=pQ'` lowers root multiplicity exactly by one away from `p=0`;
4. `FormalPolynomialVectorFieldTriangularProlongation` proves that, at the
   multiplicity-selected order, every higher coefficient jet disappears and
   the surviving value is `jet(0) D_p^m Q(y)`; and
5. `FormalPolynomialVectorFieldFiniteProlongationEscape` bounds that escape
   order by `degree Q`.

These terminals do not identify the abstract triangular family with the
actual normalized coupled-Julia tower. Coverage v40 tentatively represented
the remaining bridge as unconditional endpoint elimination. The v41
negative control below falsifies that promotion; the five governed terminals
remain valid.

## v41 projection-fallacy correction

The exact replay
[`gauge_coupled_julia_projection_fallacy.py`](../axiompack_jacobian_field_parametric_20260720/gauge_coupled_julia_projection_fallacy.py)
has certificate
`9693925138efb8db07be2afee0d65d7aba8d5b3d5864bfa976ad510eeea5b90e`.
For the saturated ideal generated by `FY-1` and `ZY-1`, its fiber over
`F=0` is empty, while its elimination ideal in `C[F]` is zero and every
`F!=0` has the finite solution `Y=1/F`. Thus empty special fiber does not
produce a nonzero endpoint polynomial.

The coupled monomial normal form shows both boundary mechanisms. After
saturation, exponents `(r,s)=(2,3)` give `Y=F^2`, which approaches the
equilibrium locus, while `(r,s)=(3,2)` give `Y=1/F`, which approaches hidden
infinity. Both components project densely.

Coverage v41 therefore replaces unconditional endpoint elimination by the
correct alternative:

1. the saturated differential ideal contains a nonzero endpoint eliminant;
   or
2. it has an irreducible component dominating the endpoint line.

The second alternative must be normalized over `F=0` and routed to an
equilibrium boundary, infinity-cross carrier, or proportional component.
The adapter does not assume that classification. The v41 combined adapter
digest is
`bde0a8cd2e908b0795ad28e1838151691f20bda27170d699cdc1ccb6097e4151`.

## v42 invariant-divisor specialization kernel

[`FormalDifferentialPolynomialInvariantSpecialization.lean`](../../../ztare_proofs/ZtareProofs/FormalDifferentialPolynomialInvariantSpecialization.lean)
constructs the polynomial total derivation
`P ↦ d_coeff(P) + v P'` over an arbitrary commutative ring. It proves
functorial compatibility under coefficient maps and derives that compatibility
for every iterate. Its nested-polynomial specialization at `F=0` follows from
the derived condition that the visible velocity vanishes on that divisor.

The terminal has:

- governed record: `ac5df55300c07830f6fe1695cb3cb2bd178e9c104d05c27596efeebd8f2c69b4`;
- kernel-parity record: `acee04551c6b44a2a8ece9393c2ea5574cfa0dda5127bc87abe01e76a0703a49`;
- content-bound receipt: `c87bc1088d9a7820c05c1c631ff472e289fda2989850f6a14fb604ee933dc4fc`.

Coverage v42 makes this a governed child of the actual-specialization node.
The concrete relation normalization remains a semantic leaf, and the exact
iterated-Leibniz identification remains in the parent semantic inference.

## v43 all-order concrete normalization

[`FormalDerivationIteratedLeibniz.lean`](../../../ztare_proofs/ZtareProofs/FormalDerivationIteratedLeibniz.lean)
proves the binomial product law for every iterate of an arbitrary derivation
of a commutative ring. Its governed record is
`b8942ecd8796511053655f85b068a5ab8394e3350630e5008d2d637f1f16cdbc`,
kernel-parity record is
`e2cc754610595297d71ed9a2b313d412db85cce98bd83f657befaf079229c8e2`,
and content-bound receipt is
`407a5a98863a3f98771b69758ed130e7dd9290209cddc5298073b226602583b2`.

[`FormalCoupledJuliaAllOrderSpecialization.lean`](../../../ztare_proofs/ZtareProofs/FormalCoupledJuliaAllOrderSpecialization.lean)
constructs `qTail` from the two tangent coefficient vanishings, proves the
exact relation binding and visible factorization, computes the special fiber
`-a0*q`, and derives every triangular prolongation by combining invariant
specialization with iterated Leibniz. Its governed record is
`455ad189d87c9b11c1b6b2203557d7d82afca44b7757134d0eae6a40ccbefa0b`,
kernel-parity record is
`a1c70be8cd61dedc73bd62e00cbb16171868c52775fee575e5b989f9a885e8c0`,
and content-bound receipt is
`9990d58da6603873f424a06afee542ad8f2635fb4c73f84cca3229dd3727da06`.

The actual-specialization inference is therefore governed. Its remaining
semantic child contains only finite instantiation facts and the necessary
regular/equilibrium branch split; it no longer contains an all-order
recurrence.

## v44 analytic Kummer lift

[`FormalAnalyticKummerLift.lean`](../../../ztare_proofs/ZtareProofs/FormalAnalyticKummerLift.lean)
classifies an analytic local automorphism lifting a positive-power scaling.
From `lifted(t)^e = lambda*t^e`, fixed zero, nonzero derivative, `e > 0`,
and `lambda != 0`, it constructs `mu != 0`, proves `mu^e = lambda`, and
derives the germ equality `lifted(t) = mu*t`.

The proof derives analytic order one, factors out the ramification parameter,
cancels only on the punctured germ, restores the center by continuity, and
uses the geometric-sum factor to rule out local switching among roots. The
terminal has:

- governed record: `b2c0303e108228cdabb399f493680c942e5309fec8b68dc0ff3d08ef380c1a53`;
- closure source: `e1b7bdc6f2d5d743e483f56cdafa94372c9247d61bdd0fa8e998efc22723ae83`;
- kernel-parity record: `d2b34c49d719d6ef6f9131dba952363ae75f11c929a68a568b68b2a0afb5f712`;
- content-bound receipt: `28a3c3f934810f093e2fc0fbbd8231095e23e40d56919ba43ad3354dc4f04552`.

Coverage v44 makes this a governed child of dominant-component routing. The
remaining semantic leaf must construct the finite normalization, the lifted
analytic automorphism with its exact power identity, and the compatible
boundary overlaps. It no longer owes local Kummer classification.

## v45 separated-polynomial branch valuation

[`FormalSeparatedPolynomialBranchValuation.lean`](../../../ztare_proofs/ZtareProofs/FormalSeparatedPolynomialBranchValuation.lean)
classifies the local boundary of every supplied normalized meromorphic branch
of the separated relation

```text
c(t) p(Y(t)) = a0 q(Y(t)).
```

The coefficient germ `c` may have any positive exact order; no quadratic-tail
unit is assumed. In the finite case `Y=beta+z`, the theorem first derives
`a0 != 0`, then proves

```text
ord(c) = ord(z) * (mult_q(beta) - mult_p(beta)),
```

so `mult_p(beta) < mult_q(beta)` and `q(beta)=0`. In the pole case it derives
the same scalar nonvanishing and

```text
ord(c) = poleOrder(Y) * (degree(p) - degree(q)),
```

so `degree(q) < degree(p)`. The desired balances are conclusions, not carrier
fields. The narrower first draft was rejected before ratification because its
unit-tail premise excluded outer generators of tangency order greater than
two.

The strengthened terminal has:

- governed record: `e95beaa9fd0fad531eff65148617cdd474cc79f385e8d08dda9273389dcd431a`;
- closure source: `c24d3a16744aba2153bf3d92cc9b4197267caac38c481e21fceeb350606502aa`;
- kernel-parity record: `7b2009b293eb040c03a6cc75964cda070fc5218d60b335d26b3ad8db6fea0161`;
- content-bound receipt: `e5e299636988d347285de47fa53d50ad0b58669e4a7e7721109b5cc9a3ee67f7`.

Coverage v45 makes this a governed child of dominant-component routing. The
remaining carrier leaf must construct the normalized meromorphic branch and
its exact separated relation and preserve overlap with the selected global
factor. It no longer owes the finite/pole valuation classification or scalar
nonvanishing.

## v46 scalar-free all-order specialization

[`FormalCoupledJuliaAllOrderSpecializationUnconditional.lean`](../../../ztare_proofs/ZtareProofs/FormalCoupledJuliaAllOrderSpecializationUnconditional.lean)
removes an unnecessary regular-branch condition from the all-order algebra.
For arbitrary `a0`, including zero, it constructs the tangent tail, exact
normalized relation, visible factorization, special fiber, invariant visible
divisor, and every triangular prolongation. It invokes the constructive helper
lemmas directly and does not consume the older terminal with its nonzero
premise.

The terminal has:

- governed record: `1fd61139d56282c44089c43943960ba28990fe7c4ca626718d4bf17e92139b26`;
- closure source: `65604fab8860aae7aced4ecfcb5116033c87ec9bfa90d5329de0d9bea6a6ab43`;
- kernel-parity record: `b2936474b087d8b9dc57f3cd90c40b3496bbac5da6a70884fb1b01d3bf24cdab`;
- content-bound receipt: `a31da2183e7d0dc6be267051697204e6ab36f943fb7f7f83f28d078a13a61d6b`.

Coverage v46 replaces the prior inference support with this stronger theorem,
so the support count is unchanged. The actual-normalized-relation leaf owes
the differential-field embedding, tangent coefficients, coefficient
constancy, and exact scalar binding, but no scalar-nonzero premise.

## v47 analytic-algebraic boundary trichotomy

[`FormalAnalyticAlgebraicBranchBoundary.lean`](../../../ztare_proofs/ZtareProofs/FormalAnalyticAlgebraicBranchBoundary.lean)
starts from a selected degree-bounded analytic polynomial root whose family is
exactly `visible(t)*p(Y)-scalar*q(Y)`. It derives hidden meromorphicity and
constructs an exhaustive local alternative:

1. a locally constant finite branch, which forces a root of `p` or `q`;
2. a nonconstant finite analytic branch with a constructed positive natural
   order and `FiniteSeparatedRelationCarrier`;
3. a pole with a constructed positive natural pole order, analytic reciprocal
   chart, and `PoleSeparatedRelationCarrier`.

The finite and pole results include the governed multiplicity/degree balances
and exact punctured-germ overlap with the selected input branch. No hidden
meromorphicity, hidden order, extension, reciprocal chart, or boundary class
is input data.

The terminal has:

- governed record: `2dba25c7e49e10d69fd7079b255909a3b14949f1cd161c08032898e5354960d9`;
- closure source: `a35d6a6525b784b09b004f92773220252dabd37c283b1d53a431542a9d450639`;
- kernel-parity record: `3043417fdff95b2e5a81e7e0069cb3a69525651ea49eb162ab4f6bc0d2ef2f77`;
- content-bound receipt: `e0972768c378472a259c30b7e8f0819df70802344dfba0e3fb17047e932479be`.

Coverage v47 makes this a governed child of dominant-component routing. The
remaining leaf must construct the finite normalization, lifted power identity,
selected single-valued analytic algebraic root of the separated family, and
original-factor overlap; it no longer assumes a meromorphic branch or its
boundary classification.

## v48 raw separated-branch assembly

[`FormalSeparatedAnalyticBranchAssembly.lean`](../../../ztare_proofs/ZtareProofs/FormalSeparatedAnalyticBranchAssembly.lean)
starts from the selected punctured analytic branch and the raw relation
`visible(t)*p(branch(t))=scalar*q(branch(t))`. It constructs the exact
degree-bounded analytic polynomial-root carrier required by v47. Coefficient
analyticity, the uniform degree bound, root membership, and an active
coefficient are all conclusions.

The activity proof retains both scalar cases. At scalar zero, positive finite
visible order and the leading coefficient of nonzero `p` supply activity. At
nonzero scalar, the proof derives `visible(center)=0` and activates the leading
coefficient of nonzero `q`. The constructed carrier keeps the original branch
and feeds the complete v47 trichotomy.

The terminal has:

- governed record: `c41ea283911e4d1c4dfe7e6abb8ebcd7cdd79e129ecb7ba626da94c1566d0757`;
- closure source: `604b10a725463e263ddece94b8a13bb3972dc749c0327a03a1bba24e9156eb1c`;
- kernel-parity record: `662f74a7a84338104eeb282f5dd89ae0cb49ee1ae87fd56f9cb0be455bc5046e`;
- content-bound receipt: `cfd0c2aa47ee55f71e52c2db9a82d964d9a9a387cd4286a84d2c959736b3e832`.

Coverage v48 has 43 governed supports and 41 bottom-up-covered nodes. The
dominant-component leaf now owes the finite ramified normalization, lifted
power identity, a selected punctured analytic branch satisfying the raw
separated relation, and original-factor overlap. It no longer owes a
degree-bounded polynomial family or an active coefficient witness.

## v49 finite-endpoint ODE continuation

[`FormalAnalyticFiniteEndpointODEContinuation.lean`](../../../ztare_proofs/ZtareProofs/FormalAnalyticFiniteEndpointODEContinuation.lean)
constructs an analytic extension of a punctured solution of
`y'=c(z)p(y)` from a finite endpoint limit. The extension has the prescribed
endpoint value, agrees with the original punctured branch, and satisfies the
same ODE on a full neighborhood. The proof works at equilibrium endpoints.

The terminal has:

- governed record: `59606a1a955c9c7de78db4abb65a374b4c485ca1984b199b18be661045fe67fa`;
- closure source: `9f267319c908cbc9d243d961b20e6bc7258f30d0c471a9142d692a2bb6d308d1`;
- kernel-parity record: `8f8831e7ad1882b9cfd797cc1ea255e943c3183eba7682befdb2b5b2bd933814`;
- content-bound receipt: `4a49afa18c8bd78e47cf080e3ffd8121bd3a1b44b851a97c156e5f2b4dffaff6`.

Coverage v49 has 44 governed supports and 42 bottom-up-covered nodes. The
selected-factor continuation proposition is now an internal semantic
inference. Its remaining leaf is maximal selected-path construction plus the
finite-limit versus reciprocal-infinity endpoint alternative.

## v50 bounded-derivative endpoint compactness

[`FormalBoundedDerivativeEndpointLimit.lean`](../../../ztare_proofs/ZtareProofs/FormalBoundedDerivativeEndpointLimit.lean)
is substrate-neutral. For a trajectory into any complete real normed space,
it derives a finite left-endpoint limit from differentiability and one uniform
derivative bound on a finite half-open interval. The proof constructs a
Lipschitz restriction by the mean-value theorem, maps the Cauchy
left-neighborhood filter through that uniformly continuous restriction, and
uses completeness to construct the limit.

The carrier contains no endpoint state, limit, Cauchy witness, compact-image
witness, bounded-trajectory premise, or convergent subsequence. The terminal
has:

- governed record: `9bcdf8d78a402b45c78d2570e29386625f4aa855e840d8e863b4c73661abb421`;
- closure source: `33cf4d0382765aceb2acfa1141da3a7f012d5b33888e0961a0f2291104924ef3`;
- kernel-parity record: `a087563bedaf4fccd761b5ea77be5940110c956dfb69e32df201542474f9842d`;
- content-bound receipt: `af1b0f0210f871aa32ff741e1baa5ce23d0ea186b5188d5925ad5357051e12ed`.

Coverage v50 has 45 governed supports and 43 bottom-up-covered nodes. The
maximal-path/escape proposition is now an internal semantic inference. Its
remaining child must construct the maximal selected lift and produce a
uniform terminal derivative bound or a compatible reciprocal-infinity escape
chart.

## v51 bounded controlled-polynomial endpoint compactness

[`FormalBoundedControlledPolynomialEndpoint.lean`](../../../ztare_proofs/ZtareProofs/FormalBoundedControlledPolynomialEndpoint.lean)
derives an explicit speed ceiling for a complex trajectory satisfying
`y'=driver*p(y)` from uniform bounds `D` on the driver and `R` on the state:

```text
D * sum i in p.support, nnnorm(p.coeff i) * R^i.
```

The same theorem constructs a finite left-endpoint limit by applying the v50
complete-space kernel. Its carrier contains no derivative bound, polynomial-
evaluation bound, endpoint state, endpoint limit, Lipschitz witness, or Cauchy
witness. Zero and constant polynomials are included.

The terminal has:

- governed record: `01b18c94801a24c0cbef421dda8c279e8168e14d94d9c751aee46daf6ed737db`;
- closure source: `b9cd249dd8ab50b0839c8dd6f7ec7daf2250f21e274e39e72eec91f3f31f29ed`;
- kernel-parity record: `213d59d16705027030b58194c5a62247db08ca0aee598fffbd2b4001981196e9`;
- content-bound receipt: `55bb145bb04cc6f05ed8b301054c1f44189da4f628cdd488f6a169ea2b47f1a5`.

Coverage v51 has 46 governed supports and 44 bottom-up-covered nodes. The
remaining continuation leaf now owes maximal selected lifts, the bounded
compact-loop driver, and a bounded-state versus reciprocal-infinity terminal
alternative. The analytic compactness chain after bounded state is governed.

## v52 norm escape and reciprocal endpoint

[`FormalNormEscapeReciprocalLimit.lean`](../../../ztare_proofs/ZtareProofs/FormalNormEscapeReciprocalLimit.lean)
constructs eventual nonvanishing and convergence of the reciprocal to zero
from norm escape along an arbitrary filter into an arbitrary nontrivially
normed field. It passed governed ratification and its matched
negated-conclusion control.

The terminal has:

- governed record: `67e0c54d559d3425a3156e43f04dd5cd41c91abc54b4daaee8460c8f93ea8af7`;
- closure source: `f64b30ed55d13ea88da8ff146b3d71b2ffe0e6569bb781e1c2ef2213e9fefbde`;
- kernel-parity record: `ec078158444523cebba177e996852ad36543fd1200a551cd59e5e004bce54475`;
- content-bound receipt: `4ce398507c2ed80e4f370afa548a06f742f87376a5ed8de61d3ad8d652acf934`.

Coverage v52 has 47 governed supports, 45 bottom-up-covered nodes, 39 directly
ratified nodes, five semantic leaves, and eleven semantic inferences. The
maximal continuation residual is split at the boundary between pathwise
escape and holomorphic compactification.

## v53 uniform-restart endpoint alternative

[`FormalUniformRestartEndpointEscape.lean`](../../../ztare_proofs/ZtareProofs/FormalUniformRestartEndpointEscape.lean)
constructs the finite-extension-or-norm-escape dichotomy from an abstract
solution predicate with restriction stability, uniqueness on open
preconnected overlaps, and restart time uniform on each bounded state ball.
Its no-extension corollary constructs norm escape. The carrier contains no
extension, escape, bounded-return point, or restart-agreement field.

The terminal has:

- governed record: `1c7573b2d50b3d7e3de72d9c0c9a2aa1dfb91c2ee67dfa782d179e93d1577391`;
- closure source: `a709f3189b17032155e5cbb3a9c0b32167850d7dc254446c4a589db45797119b`;
- kernel-parity record: `518bbfa31e9b38e284595e7d13c18ad67f82a79ef98b019707d44c6ccbb886b3`;
- content-bound receipt: `ca90dc44704eae98a224ba6c95fe69289c89b2cc241021c795f1b14e5fda1c07`.

Coverage v53 has 48 governed supports, 46 bottom-up-covered nodes, 40 directly
ratified nodes, five semantic leaves, and twelve semantic inferences. The
maximal-lift bounded-state-or-norm-escape proposition is now an internal
inference. Its construction child must supply the selected maximal lift,
restriction-stable local uniqueness, uniform bounded-ball restart,
controlled-polynomial bindings, and nonextendability. The decomposition,
coverage, and envelope digests are
`e7d52b4144ff91bfb5e4d95452e55434c6cb0aeeb8bb0905d355172434057a68`,
`d1f5da0d9c83ab6313e431bb955df6f20f193662115e1a3a83b1a5629e4e3a5b`,
and
`81c7b86f7a2d8ad278cc475676e24093b0c5a72b2187382e90ff73e88feba11f`.

## v54 controlled-polynomial uniform restart

[`FormalControlledPolynomialUniformRestart.lean`](../../../ztare_proofs/ZtareProofs/FormalControlledPolynomialUniformRestart.lean)
constructs, for every bounded complex state ball, one positive restart time
uniform over every real restart center and every initial state in the ball for
`y'=driver(t)*p(y)`. It derives the polynomial Lipschitz and field bounds from
the polynomial coefficients, continuous driver, and one global driver bound,
then invokes Picard--Lindelof. The returned solution has the exact initial
value and satisfies the ODE throughout an open symmetric interval. Zero,
constant, and equilibrium cases are included.

The terminal has:

- governed record: `39f57f7f8537e0dcfe07130160bb26c3f00f1685a74d29d6e7b4de5adfd62251`;
- closure source: `118729a48f83ef86ec0b93e7356d8d5d17718d05aa85f91e7861b7882ac10589`;
- kernel-parity record: `e6490bb04a535ae9466605d9a5e405a5a190860d62d165851e014aaa0543d6e2`;
- content-bound receipt: `eea30edabd7b12f683d878baf193f806cd4ba9db05d2be38c52941d11db68da9`.

Coverage v54 has 49 governed supports, 47 bottom-up-covered nodes, 41 directly
ratified nodes, five semantic leaves, and thirteen semantic inferences. The
uniform-restart proposition is now an internal inference. Its remaining
construction child must supply the selected maximal lift, bounded continuous
loop-driver adapter, restriction-stable overlap uniqueness,
controlled-polynomial bindings, and nonextendability. The decomposition,
coverage, and envelope digests are
`ef4b2f983cbedec1fe1e9118cb3417da52b9bee96ea7c6704172ac1937c8074c`,
`303cfc4e5457472f32bd861f61b718369572601ca84a62710c4b1675f871f209`,
and
`5c52de7d6dc484e67ab2a4e76ed0ccc5d5755702ec24b3ec90991b0ab11f1824`.

## v55 controlled-polynomial overlap uniqueness

[`FormalControlledPolynomialOverlapUniqueness.lean`](../../../ztare_proofs/ZtareProofs/FormalControlledPolynomialOverlapUniqueness.lean)
proves that two complex trajectories satisfying the same bounded-driver
polynomial ODE and agreeing at one anchor agree throughout their complete
preconnected real time domain. The theorem assumes no solution bound,
Lipschitz witness, analyticity, or uniqueness callback. For each target it
constructs a common compact state ball from the two trajectories, derives the
polynomial Lipschitz constant there, and applies forward or time-reversed
Gronwall uniqueness.

The terminal has:

- governed record: `9f35200f054a5351365e5b287f9868fd031343dc7eca98ba425527a8efc79da6`;
- closure source: `45a4e0d47b94c8e771f0f0ed7c3f687d26bbe6db1b4f3f2c3692f28c1d72ec11`;
- kernel-parity record: `24ca35b345f1888a1550e93df137e5296a526315def0e47f5ca6610e5b031750`;
- content-bound receipt: `419f63bac8ac57b8c6c1ba880f8d34709e372ff26bc7006f012210bbed8c68ed`.

Coverage v55 has 50 governed supports, 48 bottom-up-covered nodes, 42 directly
ratified nodes, five semantic leaves, and fourteen semantic inferences. The
bounded-driver/local-uniqueness proposition is now an internal inference. Its
construction child must supply only the selected maximal lift, globally
bounded continuous loop driver, nonextendability, and exact ODE/endpoint
bindings. The decomposition, coverage, and envelope digests are
`8ffd156ddfb7aab4d2f5473874e7bca8f3e043c5a097b44c7f80e351956f81e2`,
`54059de1736e66e22f86b806a882e7c56bca026d869889732a0b122890086eb9`,
and
`3f1a5d0ba59dfa61b35bb5bf45fbae5e4ff8ff82067705cb3aaa77d2058f1fd7`.

## Exact residual

Five adapter-semantic leaves remain:

1. `two_flow_actual_normalized_relation_hypotheses`: instantiate the selected
   factorization in a differential coefficient field, prove tangency and
   coefficient constancy, and bind `a0=A(x)p(x)`;
2. `two_flow_selected_dominant_component_normalization_lift_and_relation_carrier`:
   construct the finite ramified normalization over `F=0`, its lifted
   analytic monodromy and exact power identity, a selected single-valued
   punctured analytic branch satisfying the exact raw separated relation, and
   overlap with the selected global factor;
3. `two_flow_selected_maximal_lift_bounded_driver_carrier`:
   construct maximal selected lifts along every compact critical-loop
   iterate, derive the globally bounded continuous loop driver, retain the
   controlled-polynomial ODE and endpoint derivative bindings, and prove
   nonextendability at every finite maximal endpoint;
4. `two_flow_selected_nonfinite_cross_carrier_realization`: construct the
   governed ramified-cross carrier from every selected nonfinite factor branch;
5. `two_flow_selected_norm_escape_holomorphic_reciprocal_germ_upgrade`:
   upgrade the pathwise reciprocal-zero limit of the selected algebraic
   continuation to a holomorphic reciprocal germ, punctured nonvanishing, and
   compatible infinity-sheet entry.

Fourteen semantic inference propositions remain:

1. `critical_terminal_excluded`;
2. `two_flow_actual_prolongation_eliminant_or_dominant_component`;
3. `two_flow_finite_coupled_monodromy_exclusion`;
4. `two_flow_nonfinite_cross_carrier_exclusion`;
5. `two_flow_selected_dominant_component_normalization_and_routing`;
6. `two_flow_selected_factorization_continuation_carrier`;
7. `two_flow_selected_factorization_maximal_lift_bounded_speed_or_reciprocal_escape_carrier`;
8. `two_flow_selected_factorization_maximal_lift_bounded_state_or_norm_escape_carrier`;
9. `two_flow_selected_factorization_maximal_lift_bounded_state_or_reciprocal_escape_carrier`;
10. `two_flow_selected_factorization_maximal_path_or_escape_carrier`;
11. `two_flow_selected_maximal_lift_bounded_driver_local_uniqueness_carrier`;
12. `two_flow_selected_uniformly_restartable_maximal_lift_carrier`;
13. `two_flow_selected_route_evidence_exhaustion`;
14. `two_polynomial_flow_factorization_excluded`.

The connection rationalization, pole, eliminant binding, residue
irrationality, explicit differential monodromy, and the scalar endpoint orbit
are governed. Continuing an arbitrary two-flow factorization to that loop and
excluding its complete finite algebraic-monodromy branch is the principal
global obstruction.

```text
all_required_leaves_covered       = false
all_inference_rules_covered       = false
root_bottom_up_covered            = false
root_directly_ratified            = false
root_authority_promotion_eligible = false
formal_authority_issued           = false
```

## Boundary

This result covers the selected Puiseux series passage, complex single-flow
obstruction, finite Julia classification, local ramified-cross Abel
contradiction, proportional reduction, prime-reduction irrationality kernel,
the exact connection rationalization, the explicit rational differential's
pole-to-eliminant binding, its analytic infinite endpoint orbit, local
finite-state polynomial trajectories, first coupled differential
prolongation, exact multiplicity descent, triangular specialization, and
finite prolongation escape, plus all-order invariant-divisor specialization
for polynomial total derivations, the general iterated-Leibniz law, and the
concrete all-order coupled normalization, local Kummer classification of a
normalized lifted action, and exact separated-polynomial finite/pole
valuation, plus the local analytic-algebraic boundary trichotomy and raw
separated-branch assembly, finite-endpoint controlled-polynomial
continuation, bounded-derivative endpoint compactness, and explicit bounded
controlled-polynomial endpoint compactness, plus reciprocal convergence at
norm escape, the abstract uniform-restart endpoint alternative, and explicit
bounded-state uniform restart and complete overlap uniqueness for
controlled-polynomial fields. It does
not discharge every
selected-factor instantiation premise, classify a dominant invariant
component, exclude every
composition of two polynomial autonomous flows, or prove the candidate
minimax lower bound. The next exact moves are finite selected-factor
instantiation/equilibrium routing, construction of the normalized
dominant-component relation carrier, and the maximal selected-path/escape
theorem for factor-loop continuation with a bounded-state versus
norm-escape terminal alternative. That continuation step is now reduced to
constructing a maximal selected lift with a globally bounded continuous loop
driver, exact flow bindings, and nonextendability, followed by the
holomorphic reciprocal-germ upgrade.
