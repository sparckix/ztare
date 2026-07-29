# All-order slope-two contact from the inverse cubic

**Status:** independently audited all-order construction with exact replay
and provider-free kernel ratification of its algebraic spine; historical
priority unconfirmed

## Statement

For the normalized Jacobian-counterexample deformation \(F_s\), there is an
identity-normalized compatible formal contact

\[
H_s\circ F_s=F_0\circ\Psi_s,\qquad \det DH_s=1,
\]

whose assembled source coefficients satisfy

\[
\boxed{\deg [s^n](\Psi_s-\operatorname{id})\le 2n+1.}
\]

The target coefficients lie in the companion filtered windows

\[
\deg_f[s^n](H_P-P)\le2n+4,\qquad
\deg_f[s^n](H_Q-Q)\le2n+6.
\]

Together with the complete gauge-minimal second-jet obstruction, this closes
the BCH-stable all-prefix source invariant

\[
\rho_n(F_s;F_0)=
\inf_{\text{admissible contacts through }n}
\max_{1\le j\le n}\frac{\max(0,\deg Y_j-1)}j:
\]

\[
\boxed{\rho_n(F_s;F_0)=2\quad(n\ge2)},\qquad
\boxed{\sup_{n\ge2}\rho_n=2}.
\]

## Construction

The generic inverse equation has one root escaping at \(s=0\).  If \(z\) is
its reciprocal, exact factorization removes the invertible sheet:

\[
\frac zaR_s(W)=(1-zW)D_s(W).
\]

The finite cubic \(D_s\) is shifted to the seed cubic

\[
U^3-U^2+P'U-Q'=0.
\]

Differentiating the factorization at a finite root gives

\[
\gamma'=\gamma\theta,\qquad
\theta=\frac{2(z/a)}{(s+2)(1-zW)}.
\]

The reciprocal-root recursion yields

\[
\deg_f[s^n]z\le2n-2,
\]

which propagates to the uncorrected source bound \(2n+1\).

To impose \(\det DH_s=1\), use a trace-zero inverse-cubic root field
\[
f=a+bW+cW^2,\qquad 3a+b+(1-2P)c=0.
\]
Its target divergence is inverted by

\[
\mathcal A=
5+\left(2P-\frac23\right)\partial_P
 +\left(3Q-\frac P3\right)\partial_Q.
\]

The diagonal part of \(\mathcal A\) has nonzero eigenvalues on every
filtered monomial and the remainder strictly lowers the \((4,6)\)
filtration, so \(\mathcal A^{-1}\) is a finite filtration-preserving sum on
each polynomial.  The selected control also satisfies the source lift
ideals.

At parameter order \(n\), the determinant defect is canceled by paired
formal flows

\[
\exp(s^nZ_n),\qquad \exp(s^nY_n).
\]

Replacing these by bare maps
\(\operatorname{id}+s^nZ_n\) and
\(\operatorname{id}+s^nY_n\) leaves an order-\(2n\) contact error.  The
paired-flow recursion preserves both target filtration and source degree
\(2n+1\).

## Verification

Three deterministic replays pass:

- [`gauge_weierstrass_finite_branch.py`](gauge_weierstrass_finite_branch.py)
  checks the exact factorization through order nine and the filtered target
  normalization through order six;
- [`gauge_root_volume_rectifier.py`](gauge_root_volume_rectifier.py) checks
  40 complete filtered monomial cases through parameter order eight;
- [`gauge_filtered_cubic_volume_rectifier.py`](gauge_filtered_cubic_volume_rectifier.py)
  checks the divergence right inverse, first rectifier, lift boundary, and
  differentiated source formulas.

The independent audit checked the pullback identity, divergence signs,
target-group bounds, source composition envelope, weighted volume identity,
and paired-flow requirement.

The Lean source
[`AxiomPackJacobianRootVolumeRectifier.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianRootVolumeRectifier.lean)
contains the root, trace, divergence, filtered inverse, source lift, and
degree arithmetic endpoints.  Provider-free LeanMill ratification of
`root_volume_rectifier_certificate` used zero provider calls and closed with:

- closure-record SHA-256
  `8e4831cb1eebd985f71a097619e6c1e274d460e5f0b8cfbea27e8838db167751`;
- kernel-parity SHA-256
  `d236a65f33d7e0e78621fb17d34c320b0ae5174f931a30300f81a587cef101b6`;
- matched negated-conclusion control and axiom allowlist passed.

The infinite filtered-group induction remains in the mathematical argument
rather than a full formal-power-series library.

For the all-prefix corollary, the upper implication uses the same
substitution-word estimate for \(\log\Psi_s\).  With
\(\Delta=\Psi_s^*-\operatorname{id}\), a word of length \(r\) and total
parameter order \(n\) has degree at most

\[
\sum_i(2n_i+1)-(r-1)=2n+1.
\]

It follows coefficientwise from
\(\log(\Psi_s^*)=\sum_{r\ge1}(-1)^{r+1}\Delta^r/r\).
The preserved source lift ideals survive logarithm, and the logarithm of the
area-preserving target map is polynomial Hamiltonian.  We use
\(\deg0=-\infty\) and source excess \(e(0)=0\).

The lower implication is the independently kernel-checked second-jet dual
certificate in
[`AxiomPackJacobianGaugeMinimum.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianGaugeMinimum.lean).
A prefix slope below two would force \(\deg Y_1\le2\), hence \(Y_1=0\) by
the complete order-one fiber, and then \(\deg Y_2\le4\), contradicting that
certificate.  The degree-five witness shows the lower endpoint is sharp.

The complete low first-order fiber and the all-prefix arithmetic aggregation
are now carried by
[`AxiomPackJacobianAllPrefixContactComplexity.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianAllPrefixContactComplexity.lean).
Its displayed \(15\times15\) coefficient minor is injective, so the nine
liftable source columns and six Hamiltonian target columns have zero kernel.
Provider-free LeanMill ratification of
`all_prefix_contact_complexity_arithmetic_terminal_certificate` used zero
provider calls and closed with:

- closure-record SHA-256
  `7023c17fbb6d00c4b1723bf1a7057399e466d87322474f86cb9f6ae3448d4022`;
- kernel-parity SHA-256
  `065f305d012a7f94e69e439fd91ca2dfb4caa9617d5b802a9b5b4e063f675664`;
- identical posed/closed target-signature SHA-256
  `d050416d10ca86d6a25acc30189afa0c8120627e06904321edebd33351692231`;
- matched negated-conclusion control, statement integrity, target identity,
  and axiom allowlist all passed.

This ratifies the finite/algebraic spine of the equality.  The completed
formal-substitution group and the all-order rectifier induction remain the
explicit mathematical argument above rather than encoded objects in a
formal-power-series library.

## Scope

The all-prefix invariant charges source logarithmic generators while
requiring the target contact to remain polynomial Hamiltonian and
area-preserving.  It is now exact.  It is saturated at order two and
therefore does not measure what remains after an arbitrary finite prefix is
discarded.

The separate symmetric tail statistic

\[
\sigma_{\rm ct}=
\inf\limsup_{j\to\infty}
\frac{\max(\max(0,\deg Y_j-1),
           \max(0,\deg X_{K_j}-1))}{j}
\]

still has an unresolved prefix-normalization problem.  The Rees node/cusp
theorem controls one global triangular class, while the exact polar source
connection and cusp-stabilizer BCH cascade show why it cannot yet be promoted
to an unrestricted tail lower bound.

The successor audit has now isolated that problem more sharply.  At the seed
cusp, liftable target Hamiltonians fit into the exact normal sequence

\[
0\longrightarrow\mathbb Q+(C)
\longrightarrow
\mathbb Q\oplus(P^3,PQ,Q^2)
\longrightarrow r^3\mathbb Q[r]
\longrightarrow0.
\]

Thus every target-lift-compatible normal class transfers.  With the original
strict source lift ideals imposed, full paired completion has one low scalar
obstruction

\[
\omega(a,b)=2[r^2]a+3[r^3]b.
\]

The campaign's polar witness has \(\omega=0\).  Modulo the cusp stabilizer,
its remaining strict source tangent lies in the degree-five one-dimensional
abelian class.  The exact replay and proof are
[`gauge_full_prefix_stabilizer_quotient.py`](gauge_full_prefix_stabilizer_quotient.py)
and
[`gauge_full_prefix_stabilizer_quotient_pencil.md`](gauge_full_prefix_stabilizer_quotient_pencil.md).
Its arithmetic endpoints passed provider-free LeanMill ratification with
kernel-parity record SHA-256
`31204a6b6e3ce1e2f9139e2535c43c349afd9c7b0b34122568670d3b0a9d5efe`.
This eliminates the seed normal-image search as a route to a tail lower
bound; the residual is compatibility through moving transverse layers and
the BCH cost of the selected cusp stabilizers.

That BCH cost is already all-order in the generic amplitude.  For

\[
\Omega(\tau,\mu)
=\log\!\left(e^{-\tau X_C}e^{\tau X_{C+\mu B}}\right),
\]

every coefficient is nonzero over \(\mathbb Q(\mu)\), and

\[
\deg(\operatorname{ad}_C^kB)
=3+\left\lfloor\frac k2\right\rfloor.
\]

Hence the square-zero and generic-amplitude cascades have exact ordinary
derivation-excess slope \(1/2\).  A prescribed fixed rational amplitude and
the unrestricted minimax remain open.  The generic noncancellation
arithmetic passed provider-free LeanMill ratification with kernel-parity
record SHA-256
`988f9e6b047a48d72a8eeb7d6ecdb380d1e541c5d82a298bf608635ff28ae9df`.
The recurrence and exact-degree arithmetic passed the same route with
kernel-parity record SHA-256
`eda335d95ae2298c7651ae205e2d1296994c1da4fff5f2d6ab54655e8c5e2e57`.

The target-side successor now has an exact rank-one classification.  In
normalized cusp coordinates \(X=-P/3\), \(Y=-Q/2\), the unique graded
rank-one Poisson section of the restriction \(X\mapsto r^2\),
\(Y\mapsto r^3\) is

\[
t_m=
\begin{cases}
X^{m/2},&m\text{ even},\\
X^{(m-3)/2}Y,&m\text{ odd},
\end{cases}
\qquad
\deg t_m=\left\lfloor\frac m2\right\rfloor.
\]

The alternative weight-six line \(Y^2\) forces incompatible weight-twelve
lines \(X^3Y^2\) and \(Y^4\).  Taking associated graded extends the same
half-rate lower bound to every cusp-weight-triangular, nonhomogeneous
rank-one section.  The arithmetic classification passed provider-free
LeanMill ratification with kernel-parity record SHA-256
`8430de7d0047fb08198f59d26b90d46ccf7b7e8e86f3dbc1d609a1571cd2a569`.

Allowing the bracket-generated stabilizer directions changes the category.
The Lie algebra generated by the minimum-degree section is supported in the
sharp monomial cone

\[
b\ge1,\qquad a\le2b
\quad\text{for }X^aY^b.
\]

This cone is closed under every nonzero Poisson bracket, and

\[
\deg(X^aY^b)\le\frac37\operatorname{wt}(X^aY^b).
\]

The bound is attained at unbounded weights by
\(X^{2b}Y^b\), generated recursively from \(X^2Y\) and \(X^2Y^2\).
Thus the higher-rank closure has exact extremal cusp-weight rate \(3/7\),
while the rank-one split pays \(1/2\).  Whether the moving contact stays in
this cone or forces the bare stabilizer \(C=X^3-Y^2\) remains the active
tail-minimax question.  The cone closure, rate, and sharp-ray recurrence
passed provider-free LeanMill ratification with kernel-parity record
SHA-256
`09e0a47758a9e8388c92dd9e77a9f0f088d2ab35db61e68557130a080d33beb2`.

The paired seed transfer explains the remaining tradeoff.  A nonzero
minimum-section bracket defect of cusp weight \(w\) has the form

\[
\delta=\alpha DY^{(w-6)/3}.
\]

Retaining it on the target has Hamiltonian degree \(w/3+1\).  Moving the
same defect through the seed cusp produces the strict source mode
\(U_{w-4}\), whose minimal polynomial degree is

\[
\boxed{2w-9}.
\]

At the natural logarithmic relation \(w=N+5\), this is degree \(2N+1\)
and derivation excess \(2N\).  Thus the exact categories are: transfer
infinitely many defects off the target and pay source slope two; absorb them
into one target line per weight and pay the rank-one rate \(1/2\); or retain
independent stabilizer directions in the \(3/7\) higher-rank cone, whose
paired moving-family source cost is still unknown.  The transfer arithmetic
passed provider-free LeanMill ratification with kernel-parity record SHA-256
`b2be5bd241d39de2896518bc537ebdac308cd8083da0c78a606fd04b22c1771c`.
Whether the moving family excites an infinite sequence is still open.

### Moving-cone phase transition

The complete-affine moving replay now reaches instantaneous order six.  It
carries the full lower homogeneous solution space rather than freezing a
sequential pivot.  The minimum source caps are

\[
\begin{aligned}
\text{higher-rank cone:}&\quad(5,5,7,9,11,13,14),\\
\text{rank-one parity section:}&\quad(5,5,7,9,11,13,15).
\end{aligned}
\]

The first difference occurs at cusp weight twelve.  The cone has two
independent symbols \(Y^4\) and \(X^3Y^2\), while the parity section has one.
At order six, cone cap thirteen fails with rank/augmented rank \(212/213\)
and cap fourteen passes; parity cap fourteen fails with \(241/242\) and cap
fifteen passes.  This is the first exact moving-family instance where
higher-rank target language reduces paired source cost.

The arithmetic reason is now all-order at the cusp-symbol level.  If
\[
\mathcal E_w=\{(a,b):2a+3b=w,\ b\ge1,\ a\le2b\},
\]
two adjacent solutions have Hamiltonian-symbol determinant \(-w/6\).
Every \(w\ge17\) has two such solutions.  The terminal arithmetic theorem
passed provider-free LeanMill ratification with kernel-parity SHA-256
`416ff837e0d1bee1ba6f860078fcae3ff674692cb01b6dcdc97226c4ee1f54e7`.
This rejects the earlier finite extrapolation
\(\deg V_j=2j+3\): the cone already saves one degree at \(w=12\).

The order-six one-below-cap cokernels also have exact projective-polar
forms in the adapted chart \(V=v,\ G=t-\frac32v\):

\[
\lambda_{\rm cone}
=\frac{2}{8!\,9!}
\left(\partial_V-\frac32\partial_G\right)^8
\partial_G^8(\partial_V+11\partial_G),
\qquad
\lambda_{\rm parity}
=\frac1{(9!)^2}
\left(\partial_V-\frac32\partial_G\right)^9\partial_G^9.
\]

Their root multiplicities are respectively \((8,8,1)\) and \((9,9)\), and
their weighted-divergence boundary pullbacks are nonzero at source degrees
fourteen and fifteen.  This identifies the exact finite quotients
responsible for the saved degree.  It also kills a stronger extrapolation:
neither functional factors through the exceptional-line restriction or any
proper normal jet there.  The cone's third projective direction rules out a
pure cusp tangent/normal invariant.  The calculation is recorded in
[`gauge_j6_cokernel_geometry_pencil.md`](gauge_j6_cokernel_geometry_pencil.md).

### Higher-normal boundary

Cusp-symbol rank two sees only the Hamiltonian one-jet modulo
\((X^3-Y^2)^2\).  It does not imply a triangular lift for the complete
target module.  On the source line \(V=-1\), the seed satisfies

\[
F_0=(G+1,0),\qquad
\partial_VQ_0=(G+1)^2,\qquad
\partial_GQ_0=0.
\]

Every cone Hamiltonian has zero second field component on \(Q=0\).  For the
transverse tower \(C^k\), however, that component has degree \(3k-1\).
A source field of degree \(B\) reaches at most degree \(B+2\), so any
universal decomposition into cone target plus source response forces

\[
\boxed{B\ge3k-3}.
\]

Hence no uniform-source cone normal form exists for the complete target
module.  Its seed-line and arithmetic spine passed provider-free LeanMill
ratification with zero provider calls:

- governed closure SHA-256
  `2d11aa45708a9b2aae4f06ce4a14f2253cccbb93ba03e89c9a9a615812ed0580`;
- closure-record SHA-256
  `35f47f7e7745b7316861eb3e9a5a27a1c636837c2b143080d95935df5f7f411c`;
- kernel-parity SHA-256
  `026a3115b00cde080759b09bada9c3a4c6eb92b3b6fd066e17e63ec59c6d8b2d`.

The particular moving recurrence avoids this \(C\)-adic quotient through
the six solved orders and the order-seven residual lookahead.  Its restricted
line degrees are

\[
(2,2,3,3,4,4,5,5),
\]

so fixed source caps eleven and twenty-three pass throughout.  The observed
full-system cap failures therefore live in other filtered quotients.

The finite line profile now has an all-order envelope.  On \(V=-1\), with
\(u=G+1\), the closed family formulas imply

\[
P_s\in uR+s^2u^2R+s^4u^3R,\qquad
Q_s\in su^2R+s^3u^3R+s^5u^4R.
\]

For every solvable natural-weight cone recurrence this propagates to

\[
\deg (R_n)_Q|_\ell\le\left\lfloor\frac n2\right\rfloor+2.
\]

The top coefficient is not invariant.  The exact source-only connection
has fixed line degrees \((4,5)\), so it satisfies the stronger
\(\Lambda_4=0\) at every order.  Conversely, freezing the selected target
prefix \(K_0,\ldots,K_6\) gives an exact source completion of line degrees
\((14,15)\) and eventually violates \(\Lambda_{11}=0\).  Maintaining that
bound therefore requires active delayed target controls.  The proof is
[`gauge_moving_cone_line_filtration_pencil.md`](gauge_moving_cone_line_filtration_pencil.md).

The exceptional-divisor normal form supplies a different, positive
quotient.  After the divisor and first transverse layers are normalized,
the complete weight-five target image in layer two is
\(\operatorname{span}\{A,A^3,A^5\}\).  The seed-linearized augmented system
has rank-four witness determinant \(3875/768\), and the canonical
opposite-parity class begins

\[
\boxed{[s]R_2^{\rm even}(s,A)=\frac{31-45A^2}{96}\ne0.}
\]

Its arithmetic spine and parity-routing laws passed provider-free LeanMill
ratification with kernel-parity SHA-256
`1b8da5ad17a609a1bb0fb55df9d81573db2622db32850318dcab0d59383232b5`.
This is the first surviving transverse class after complete target
normalization at its layer.  Turning it into a tail theorem still requires
mixed-bracket propagation through every higher normal layer.

### Source logarithm and convention correction

For the selected complete-affine cone connection, the instantaneous source
profile
\[
(5,5,7,9,11,13,14)
\]
becomes the source-logarithm profile
\[
\boxed{(5,5,9,11,14,18,22)}
\]
through logarithmic order seven.  The target Hamiltonian logarithm has
degree profile \((2,3,3,3,4,4,5)\).

This replay exposed a reusable convention defect.  In
\(F_s=A_s\circ F_0\circ\psi_s\), the target equation is \(A'=XA\), while
the source equation is \(\psi'=D\psi\,V\).  Their inverse-`dexp`
first-bracket coefficients are respectively \(-1/2\) and \(+1/2\).
A shared equation-typed formal-Lie-series primitive now binds the side to
the displayed flow equation and verifies both forward round trips.  The
orientation correction leaves degree profiles unchanged and corrects
source shell coefficients.

These successor results narrow the tail problem without closing it.  The
remaining theorem must identify the other moving filtered quotients and
either construct a finite-dimensional source Lie normalization or prove a
prefix-independent nonzero Magnus class.

The inspected current sources contain the inverse relation, degree jump,
exceptional sheet, quotient square Jacobian, and capped deformation
calculations.  They do not state this filtered area-preserving rectifier or
the exact all-prefix minimax corollary. Historical priority therefore remains
externally unconfirmed.
