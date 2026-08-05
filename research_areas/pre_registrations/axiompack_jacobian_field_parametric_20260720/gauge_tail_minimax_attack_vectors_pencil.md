# Tail minimax attack vectors

**Status:** active pencil map for the unrestricted symmetric logarithmic
contact statistic

## Eigenquestion

For coefficientwise-polynomial formal contacts

\[
H_s\circ F_s=F_0\circ\Psi_s,
\]

determine

\[
\sigma_{\rm ct}
=
\inf\limsup_{n\to\infty}
\frac{\max\{e(Y_n),e(X_{K_n})\}}{n}.
\]

The all-prefix source statistic is already exactly two.  The tail statistic
can discard a finite prefix and charges target degree as well, so that result
does not determine \(\sigma_{\rm ct}\).

## Vector A: fixed-rational cusp cascade

The finite-prefix stabilizer calculation gives

\[
\Omega(\tau,\mu)
=
\log\!\left(e^{-\tau X_C}e^{\tau X_{C+\mu B}}\right).
\]

Every coefficient is nonzero over \(\mathbb Q(\mu)\), with exact ordinary
slope \(1/2\).  A prescribed rational amplitude is still open because
different powers of \(\mu\) can cancel.

The diagonal identity

\[
C+\mu B
=4(1-\mu/144)P^3+27(1-\mu/108)Q^2
\]

gives a stronger attack.  If

\[
\mu=\frac{432(r^5-1)}{4r^5-3},
\]

then

\[
C+\mu B=\kappa\,C(rP,r^{-1}Q),
\qquad
\kappa=\frac{1-\mu/144}{r^3}.
\]

For rational \(r\), both \(\mu\) and \(\kappa\) are rational.  The first test
is \(r=2\), giving

\[
\mu=\frac{13392}{125},
\qquad
\kappa=\frac4{125}.
\]

The attack succeeds if the top ordinary coefficient of every
\(\tau^n\)-Hamiltonian is nonzero at this amplitude and admits an all-order
recurrence, sign rule, or valuation proof.

It is killed if an exact coefficient vanishes, if the top coefficient is
not sufficient to detect the Hamiltonian, or if the observed finite prefix
has no recurrence-level explanation.

**Current disposition.**  The specialization \(\mu=144\) gives
\(C+144B=-9Q^2\).  The exact shell algebra

\[
H_{r,s}=P^{2r-s+1}Q^{s-r+1}
\]

reduces the critical coefficients to a two-index recurrence and extends the
nonzero fixed-amplitude prefix through order forty-one.  The even coefficient
is \(9(k+2)\) times its preceding odd coefficient at every order.  The
remaining odd recurrence is triangular but not scalar: a Wick rotation
removes the Bernoulli sign alternation, while an explicit mixed-shell
counterexample shows that the full positive coefficient cone is not
invariant.

Exact symbolic coefficients now sharpen the correlated cone.  All boundary
polynomials through index twenty-one, and every Wick-rotated odd shell
through logarithmic order forty-one, are coefficientwise nonnegative.  At
the fixed amplitude, the higher weighted profiles have simple negative
zeros and strictly interlace through the same order.  Boundary parts of the
actual even adjoints at depths \(2,4,6,8\) and the first profile Wronskian
are also nonnegative through that cap.  Raw Magnus contributions are not
termwise positive, so Vector A remains open at preservation of this
proper-position/even-adjoint correlation rather than at a generic
coefficient cone.

## Vector B: coefficientwise-finite staircase

The completed canonical target normalizer has infinitely many transverse
weights in its coefficient of \(s\), so it is excluded from
\(\mathbb Q[P,Q][[s]]\).  A valid alternative must distribute target
weights over increasing parameter orders while retaining polynomial source
coefficients.

Represent the support by points

\[
(n,m)
=
(\text{parameter order},\text{transverse layer}).
\]

Coefficientwise polynomiality says every row \(n\) is finite.  The canonical
normalizer occupies infinitely many points in row \(1\); the source-only
contact occupies finitely many points in every row but its Magnus logarithm
has slope two.

The attack succeeds with either:

1. a recursive locally finite staircase whose source and target logarithmic
   excesses both have slope below two; or
2. a scheduling inequality showing that every locally finite staircase
   must reproduce an infinite subsequence of the source or target critical
   shell.

It is killed by a repeated same-order target tail, a source lift failure, an
uncontrolled BCH word, or an inequality that bounds only a finite prefix.

**Current disposition.**  \(s\)-adic causality excludes delaying the
infinitely supported canonical first row: the mismatch is already visible
modulo \(s^2\).  The canonical row's size-three \(3/2\)-Jordan realization
also does not arise as an adjoint module of the complete cap-seven
first-order contact fiber.  That fiber is not adjoint-invariant, and positive
source filtration makes any finite-support graded adjoint action nilpotent.
A distinct coupled recursion is still possible; it must begin with a
polynomial first row and cannot be interpreted as a reindexing of the
completed canonical normalizer.

The complete moving-cone staircase now gives a sharper finite stress test.
Carrying all fourteen lower affine directions into instantaneous order seven,
source caps \(14,15,16\) have exact rational inconsistency functionals, while
cap \(17\) has a rational solution replaying all 692 equations.  For one
selected solution the source logarithmic degrees through order eight are

\[
(5,5,9,11,14,18,22,26).
\]

The new top shell is transverse to \(VG=0\), so the earlier tangent
\(W_m\)-ideal is not the complete leading mechanism.  This finite jump rules
out the cap-fifteen continuation but does not exclude a different locally
finite schedule.

The first transverse source-log seed is now complete-affine rather than
selected.  Across all six minimum-cap affine prefixes through instantaneous
order four,

\[
\operatorname{top}_{14}\Omega^{\rm src}_5
=\frac7{276480}Z_5,
\qquad
Z_m=D_{3m-5,m-1},
\]

and no affine parameter enters the two nonzero coefficients.  The exact
monomial Lie law gives

\[
\operatorname{ad}_{W_4}^{\,k}Z_5
=\frac{k+7}{7}(2k+1)!!Z_{5+k}.
\]

This supplies a nonvanishing slope-four Lie-word ray.  Vector B is not
settled until its coefficient is shown to survive every later compatible
choice, or until cancelling it is shown to force an equal-or-larger target
or source logarithmic shell.

The next exact affine carries strengthen coefficient survival through two
more orders:

\[
\operatorname{top}_{18}\Omega^{\rm src}_6
=-\frac1{184320}Z_6,
\qquad
\operatorname{top}_{22}\Omega^{\rm src}_7
=-\frac1{1376256}Z_7
\]

identically across the complete ten- and fourteen-dimensional affine
families.  The corresponding dexp identity is not a one-generator
transport: bracket depths zero through four contribute already at order
six.  The live all-order task is therefore a finite-prefix projected
recurrence for the whole defect-\(-2\) module, followed by a proof that new
compatible controls cannot enter its extremal quotient cheaply.

The exact cap-seventeen kernel has dimension twenty-one and extends all
fourteen lower affine parameters.  Its new source directions have degree at
most seventeen and therefore cannot enter the degree-twenty-six log shell.
Consequently

\[
\operatorname{top}_{26}\Omega^{\rm src}_8
=\frac5{14155776}Z_8
\]

is the fourth successive complete-affine invariant shell.  This rules out a
finite escape anywhere in the minimum-cap prefixes through instantaneous
order seven; it still does not rule out a more expensive earlier prefix or
a later symmetric source/target cancellation.

The excess-\(-6\) quotient can be replayed much farther under the explicit
condition that projected velocity inputs vanish from derivative order three
onward.  Its \(Z_m\) coefficients are independent of the complete order-two
affine parameter and nonzero through \(m=41\), with sign
\((-1)^{\lfloor m/2\rfloor}\).  Exact agreement with the full Magnus replay
holds through order eight.  Constant-coefficient, low-degree rational-ratio,
bounded polynomial-coefficient, product-form, and rational-generating-
function guesses all fail on the extended prefix.  Thus the quotient is a
strong finite obstruction but does not yet supply its own all-order
nonvanishing proof.

The exact normalized global control gives an independent locally finite
schedule:

\[
K_s=a(s)P^3+b(s)PQ-\frac14Q^2.
\]

Its source velocity vanishes at the distinguished fiber and has uniformly
bounded spatial degree.  The apparent source-log ray of degrees
\((22,24,26)\) at orders six through eight does not continue with slope two.
The complete order-nine Hamiltonian replay gives

\[
\operatorname{top}\Omega_9^{\rm src}
=X_{-\frac{23}{42278584320}v^{20}z^{17}},
\qquad z=2+2t-3v,
\]

of derivation degree \(34\).  The target log reaches only degree eight
through order fifteen, so the source controls the checked symmetric maximum.
This exact control is therefore not a bounded-log escape.

A closed source grading sharpens the failure.  For \(v^az^b\) at cost \(q\),
put

\[
(I,J)=(a-3q-1,b-2q-3).
\]

All velocity grades are nonpositive, the order-two radial field is the
unique zero grade, and all instantaneous Hamiltonian exponents are at most
nine.  The rectangle down to \((-6,-3)\) is therefore an exact quotient.
Its coefficient at order \(6+2r\) is

\[
\frac1{2^{20}}
\left(-\frac3{128}\right)^r
(2r-1)!!
\frac{12B_{r+2}}{(r+2)!}
\]

on \(v^{13+6r}z^{12+4r}\).  Translation to \(u=1+v\) reduces the quotient
to eighteen instantaneous monomials and derives the complete terminal
forward-`dexp` equation

\[
2[D+f(D+xD')]+\frac1{1536}(1-f)=\frac7{3072},
\qquad
f=\frac{1-e^{-x}}x.
\]

Its unique formal solution is the displayed Bernoulli divided difference.
Thus the subsequence \(r=2m\) has nonzero source degree \(5n-8\) at every
\(n=6+4m\).  This rules out the normalized global schedule as a bounded-log
escape.  It remains a one-connection theorem rather than a minimax
conclusion.

The first earlier-coefficient counterattack exposes two different transfer
mechanisms.  The perturbation

\[
K_s-\frac{s}{56}Q^3
\]

cancels the rate-five source generator and removes its first rate-seven
source face in the complete closed quotients.  It introduces alternating
target cubics \(P^3,Q^3\), however.  Their exact word

\[
W_m=P^{3m}Q^3,\qquad
\operatorname{ad}_{Q^3}\operatorname{ad}_{P^3}^{\,2}W_m
=162(3m+4)W_{m+1}
\]

has candidate target rate \(3/4\), and the complete left-Magnus replay has
nonzero \(W_m\)-coefficients through logarithmic order forty-two.  An
all-order target coefficient proof is still missing.

The source side now decides the candidate.  In the closed excess
\(G=a+b-7q-4\), the first tested rate-seven module has zero response, but
the next module \(G=-13\) has the exact coefficient

\[
\frac{27}{12845056}
\frac{B_{k+2}}{(k+2)!}
\prod_{j=0}^{k-1}\frac{9(2j+1)}{896}
\]

on \(\operatorname{ad}_{u^9z^9/896}^{\,k}(u^{17}z^{16})\).
At even \(k=2m\), this gives a nonzero source shell at \(n=6+4m\) of
derivation degree

\[
\boxed{7n-12}.
\]

Thus the \(Q^3\) direction is an all-order source obstruction, not a
minimax construction.

The target-central alternative is decisive.  With

\[
H_0=-P^3/36-Q^2/4,\qquad
K_s^{\rm cent}=K_s-\frac9{28}sH_0^2,
\]

the target perturbation commutes with the seed and cancels the old source
generator.  Its full source pullback creates the unique radial term

\[
A=-\frac9{458752}u^{12}z^{12}
\]

in a second closed quotient.  A finite negative-grade core changes the
first terminal iterate by \(-12/37\); every later outer bracket is forced
to use \(A\).  The universal response has coefficients
\(B_{k+1}/(2(k+1)!)\), so odd depths give a nonzero source subsequence at
\(n=6+4m\) of exact derivation degree

\[
\boxed{10n-18}.
\]

This excludes the seed-central cancellation at all orders.  It also shows
that canceling one extremal ray can increase the source rate; it does not
yet impose that tradeoff on every locally finite staircase.

The minimum seed-Newton-weight cancellation is more competitive:

\[
K_s-\frac{s}{168}P^2Q.
\]

It cancels the rate-five generator without introducing a higher seed face.
The complete instantaneous source support has nonpositive grading

\[
G_4=a+b-4q-4,
\]

which proves the all-order upper bound

\[
\deg\Omega_n^{\rm src}\le4n+4.
\]

The first persistent quotient is \(G_4=-7\), nonzero at every checked order
through thirty-six.  Its two zero-grade radial generators commute, and
removing them leaves a finite core through cost eleven.  A scalar boundary
projection fails at adjoint depth three because a neighboring orbit feeds
back.

The triangular lattice grading

\[
h=q-(a-b)
\]

resolves that coupling.  The \(h=4\) boundary terminates, and the \(h=5\)
boundary is closed under the cost-two radial adjoint.  Its normalized
right-`dexp` solution is

\[
D(x)=
-\frac{221}{26208}
+\frac{23}{1950}x
+\frac{13}{1872}\frac{x}{e^x-1}.
\]

Even-Bernoulli nonvanishing gives a source ray at
\(n=2+4m\), \(m\ge1\), of exact derivation degree

\[
\boxed{4n-6}.
\]

Thus the \(P^2Q\) connection has exact symmetric logarithmic rate four.
It proves a minimax upper bound of four.  The lower minimax bound remains
open because the calculation classifies this connection rather than every
point of the full cancellation hyperplane.

The remaining low-weight order-one freedom has now been tested at its unique
radial exception.  In

\[
-\frac1{168}P^2Q+\alpha PQ+\beta Q^2,
\]

the cost-two radial generator vanishes only at
\(\beta=325/1344\), while the cost-three generator
\(-u^8z^8/43008\) is independent of \(\alpha,\beta\).
At \(\alpha=0\), the exact terminal quotient has orbit

\[
q=2+3k,\qquad (a,b)=(1+7k,4+5k).
\]

Its dominant quadratic response satisfies

\[
27(2m)!D_{2m}^{\rm dom}\equiv1\pmod3,
\]

and every other marker sector vanishes after the same scaling modulo three.
Hence this exceptional connection also has exact symmetric rate four.  This
closes the cheapest \(Q^2\) counterattack, but a later coefficient can still
cancel the cost-three radial generator.  The minimum cone monomial capable
of doing so is \(PQ^2\) at parameter order two.

That repair now gives the first strict improvement below four:

\[
K_s^{[2]}
=K_s-\frac{s}{168}P^2Q
+\frac{325s}{1344}Q^2
-\frac{s^2}{5376}PQ^2.
\]

Its exact Newton grading is

\[
G_{7/2}=2(a+b)-7q-8,
\]

with unique zero-grade generator \(137u^9z^9/4128768\) at logarithmic
cost four.  The grade-\(-12\) terminal response is a positive-weight
Bernoulli-polynomial average.  Its even coefficients have sign
\((-1)^m\), giving source derivation degree \(7n/2-5\) on
\(n=10+8m\).  Thus this connection has exact symmetric rate \(7/2\), and

\[
\sigma_{\rm ct}\le\frac72.
\]

The next forced cone cancellation is
\(137s^3Q^3/129024\), which removes the cost-four radial velocity.  Its
complete Newton polygon drops to \(10/3\), but it exposes a lower-order
freedom that a one-generator repair misses.

Solving every radial weight in each parameter row gives a different
construction.  The seed radial symbols of the cone monomials are diagonal
by weight.  A target-lift audit excludes the bare \(Q\) monomial, so the
admissible represented weights are

\[
\{w:w\ge5\}.
\]

The first five row dimensions are \((3,4,5,6,7)\), while their exact source
Hamiltonian degrees are

\[
(8,10,12,14,16)
\]

at costs two through six.  In the two-layer chart

\[
P_s=A_s(r)+a_sz,\qquad Q_s=B_s(r)+b_srz,
\]

the moving tangency

\[
(A_s',B_s')=L_s(r)(a_s,b_sr)
\]

forces the first-normal layer to follow the radial solve.  Every higher
normal factor lowers radial degree by two.  The resulting all-order
triangular induction gives

\[
\deg H_q^{\rm src}\le2q+4,\qquad
\deg Y_q\le2q+1,
\]

with target rate at most one.  Therefore

\[
\boxed{\sigma_{\rm ct}\le2}.
\]

The omitted \(Q\) column was the unique cone monomial whose pullback had
\(z\)-order below three.  On the corrected rows every source Hamiltonian
defines a polynomial density-\(z^2\) field, and both side-typed Magnus
round trips pass.

The lower bound remains open because the first unused cone-kernel direction
\(Q^2C\) starts exactly on the growing \(z^2\) layer at cost seven.  The
corrected replay shows that velocity-first cancellation leaves a BCH
degree-\(18\) shell.  A logarithm-first solve reduces order seven to degree
\(16\), but through target order ten an uncancellable negative-normal
quotient has degrees \(19,21,23\) at orders \(8,9,10\).  Both oriented
round trips pass, so one \(C\)-layer retains rate two.  The live escape is
a finite high-degree \(C\)-prefix whose delayed Magnus action changes that
quotient.  The first such test, \(\lambda Q^2C\) in row one, is negative:
it leaves the quotient unchanged through the first window and creates
nonzero self-cascade coefficients
\(33\lambda^2/16384\) and
\(-1377\lambda^3/9175040\) at source degrees \(33,42\).

That self-cascade is now closed at all orders.  In the leading-amplitude
prefix grading, a three-state positive core and a periodic seed cokernel
reduce the complete terminal quotient to

\[
2xfE'+(2+3f)E=H,
\qquad
f=\frac{1-e^{-x}}x.
\]

Its regular solution is \(E=xJ/(e^x-1)\).  An exact growth majorant and
rational interval certificate give

\[
\operatorname{Im}J(2\pi i)>\frac1{200}.
\]

Thus \(E\) has a nonremovable pole and infinitely many nonzero
coefficients.  The row-one \(Q^2C\) prefix produces terminal Hamiltonians

\[
u^{12+7n}z^{16+7n}
\]

at infinitely many costs \(5+2n\), with limiting spatial rate seven.
The smallest delayed one-\(C\) escape is therefore excluded.  The live
counterattack initially narrowed to equal-weight discriminant cancellation,
arbitrary finite one-\(C\) prefixes, and higher \(C\)-adic powers.

The next monomial shows why cusp weight alone cannot organize that attack.
For \(Q^4C\), the entire prefix-dependent cost-three logarithmic row is
removed by the current normalizer.  A deeper quotient has zero-grade letter
\(-9u^{14}z^{16}/1024\) at cost two and terminal velocity
\(5u^{14}z^{17}/1024\) at cost four.  Its exact response is

\[
\phi_3(x)
=\frac{x}{e^x-1}\int_0^1t^3e^{t^2x}\,dt.
\]

The positive-depth coefficients are
\(B_{k+1}/(2(k+1)!)\), and the orbit multiplier is
\(9(7-13k)/512\).  Every odd depth survives, so \(Q^4C\) produces a
source ray of limiting spatial rate thirteen.  The monomial is excluded,
but only after moving to the first covariant target derivative that leaves
the cone.  That cone-exit depth, not raw weight, is the next classification
parameter.

For the complete pure-\(Q\) family this target parameter is now exact.
If \(G_b=Q^bC\), then

\[
\operatorname{ad}_{H_0}^nG_b
\]

remains cone-valued precisely for
\(n<\lfloor b/2\rfloor\).  At depth \(\lfloor b/2\rfloor\), the unique
all-\(P^3\) branch

\[
\frac{4(b)_n}{12^n}P^{3+2n}Q^{b-n}
\]

has negative cone margin \(2b-3-4n\).  The target runway is therefore
finite for every pure-\(Q\) one-\(C\) prefix.  What remains is the uniform
source transfer at the exit depth and the extension from monomials to
mixed discriminant-leading classes.

The first depth-three source check shows that this transfer is not indexed
by target exit depth alone.  Although \(Q^6C\) remains target-cone-valued
through two covariant derivatives, the canonical one-\(C\) staircase
already has the prefix-dependent cost-four velocity

\[
\frac{29}{65536}u^{20}z^{23}.
\]

The richer covariant continuation does not remove it.  Solving
\(G'+\{K,G\}=0\) gives cone-valued \(G_1,G_2\), followed by the exact
outside-cone part

\[
-\frac5{108}P^9Q^3+\frac5{432}P^8Q^3
\]

in \(G_3\).  Inserting all of \(G_1,G_2\) leaves the displayed cost-four
velocity unchanged, gives no cost-six terminal velocity, and produces

\[
[u^{39}z^{42}]\Omega^{\rm src}_6
=\frac{435}{2147483648}.
\]

The terminal orbit multiplier is \(9(10-19k)/8192\), and the cost-four
response has coefficients \(B_{k+1}/(2(k+1)!)\) at positive depth.
Every odd depth survives, giving a \(Q^6C\) source ray of limiting rate
nineteen.  The coupled cokernel is therefore the operative invariant.

The uniform source transfer is now exact.  For every \(b\ge6\), symbolic
generalized-binomial reduction of the covariantly completed source
quotient gives

\[
[u^{3b+2}z^{3b+5}]V_4
=\frac{(-1)^b(9b+4)}{2^{2b+5}}.
\]

The competing normal-order-two coefficient vanishes identically.  The
same formula holds in the separately checked \(b=4,5\) cases.  The
zero-grade adjoint multiplier has no integral zero, and the odd
Bernoulli response gives limiting rate \(3b+1\).  Thus every
\(Q^bC\), \(b\ge4\), is excluded.

The missing immediate-exit exponent \(b=3\) has a deceptive leading
cancellation: its logarithm terminates through cost nine in the window
\(\Gamma\ge(-8,-8)\).  The next grade \((-16,-12)\) has a
control-independent three-state cokernel recurrence.  After orbit
division its response satisfies

\[
2xfE'+(2+3f)E=H,
\qquad
E=\frac{xJ}{e^x-1},
\]

with

\[
|H_n|\le\frac{130(n+2)^4}{(n+2)!},
\qquad
\operatorname{Im}J(2\pi i)>\frac1{4000}.
\]

It therefore has infinitely many nonzero rows and limiting rate ten.
Together with the earlier \(Q^2C\) theorem, this completes every
pure-\(Q\) one-\(C\) monomial.  The live one-\(C\) frontier is
cancellation among mixed leading terms; higher \(C\)-adic powers remain
separate.

That mixed frontier is now resolved.  Reduction modulo
\(D=4P^3+27Q^2\) leaves \(P^aQ^b\), \(a\in\{0,1,2\}\).  The stable
mixed classes have a nonpolynomial \(\phi_2\) ray; the exceptional
\(PQ^2C,PQ^3C\) classes have control-independent lower recurrences of
rates nine and twelve.  At positive \(D\)-adic depth, depth one has its
own nonzero symbolic transfer, while every \(d\ge2\) has

\[
[u^\sigma z^{\sigma+4}]\Omega_3
=
\left(-\frac34\right)^a
\left(-\frac14\right)^b
\left(\frac{27}{8}\right)^d
\frac3{64}\binom d2,
\qquad
\sigma=2a+3b+5d+1.
\]

Four current columns fall below this terminal quotient and the fifth
has a forced higher pivot.  The adjoint multiplier has no integral
zero, and the same \(\phi_2\) pole certificate gives infinite support.
Thus every nonzero finite one-\(C\) prefix is excluded.  The remaining
finite-prefix frontier is the higher contact filtration
\(C^m,\ m\ge2\).

The stable higher-contact frontier has an exact obstruction.  In the fixed
chart \(r=uz\),

\[
\operatorname{Res}_r(P-P_0,Q-Q_0)=\frac C{64},
\qquad
C(P_0,Q_0)=z^2\cdot\text{unit},
\]

so

\[
\nu_z(H(P_0,Q_0))=2\nu_C(H).
\]

After complete current normalization, the stable
\(P^aQ^bD^dC^m\) cost-four terminal is

\[
\begin{aligned}
[u^Sz^{S+2m+1}]V_4
={}&
\left(-\frac34\right)^a
\left(-\frac14\right)^b
\left(\frac{27}{8}\right)^d
\left(-\frac9{16}\right)^{m-1}\\
&\times\frac{6a+9b+15d+4m}{32},
\end{aligned}
\]

with \(S=2a+3b+5d+2m\).  The preregistered \(18d\) target-weight
prediction fails; the correct \(15d\) records the source radial
valuation five of \(D\).

The odd terminal is independent of every polynomial current column.
Its adjoint multiplier is

\[
2(S-m)k-S,
\]

whose only algebraic zero lies in \((0,1)\), and the right-Magnus
response is \(\phi_3\).  Every odd depth survives.

The four boundary slack classes require a separate transition graph.
For \(d\ge1\) all twelve residue states have a nonzero odd corner.  At
\(d=0\), only

\[
(a,\ell)\in
\{(0,0),(0,1),(0,2),(0,3),(1,0)\}
\]

have a primary even terminal.  The preregistered full-row audit
falsifies the first proposed leader and replaces it with the
state-dependent key

\[
(r,n)=(S+\delta_{a,\ell},2m),
\]

where the five offsets are \(2,1,1,1,2\) in the displayed state order.
Parity-wise polynomial certificates through a fifth held-out contact
depth give nonzero factored amplitudes of degree at most three.  The
corrected adjoint multiplier

\[
2m\delta_{a,\ell}+2k(S-m)
\]

is positive at every nonnegative depth.  The corrected transition graph
has no exceptional-\(d=0\) return.

At maximum invariant contact depth \(M\), a depth-\(k\) cancellation
requires contact \(M+(M-1)k\).  This exceeds a finite prefix for
\(M>1,k\ge1\); a depth-zero cancellation, and every \(M=1\)
cancellation, exits to an odd-terminal class.  The odd transfer is
injective on the first nonzero radial symbol, and exact combined-prefix
matrices through \(C^3\) have source rank equal to target rank after
polynomial identities are removed.

Thus finite polynomial higher-contact prefixes are excluded.  Vector B
is narrowed to an infinite coefficientwise-finite \(C\)-adic schedule,
and the unrestricted matching lower bound for \(\sigma_{\rm ct}\)
remains open.

The local-finiteness counterattack removes that schedule for
continuations of the normalized radial background.  A robust odd
terminal can only be canceled by accepting a strictly higher same-order
source pivot; an exceptional terminal either survives or has a first
cancellation that enters the robust case.  The limiting source
Hamiltonian rate is uniformly at least \(11/2\).  What remains is an
arbitrary replacement of the contact-zero backbone with a coupled
higher-contact recursion, not a delayed \(C\)-adic repair of the
normalized one.

## Vector C: finite-dimensional orbit test

The family coefficients are rational in \(s\), and the reciprocal escaping
root can be flattened to \(s/(s+4)\) by an identity-normalized generator
change.  This raises a direct countermodel test: perhaps \(F_s\) is contained,
after rational reparameterization, in a finite-dimensional algebraic
source/target orbit whose logarithm has bounded spatial degree.

The attack searches for a constant or finite-dimensional Lie-algebra-valued
connection after exact source/target gauge, rather than fitting finite jets.

It succeeds only with an exact orbit identity or a bracket-closed connection
and a proved integration statement.  It is killed by an associated-graded
class outside every proposed finite-dimensional orbit, or by bracket growth
that survives the complete target image.

**Current disposition.**  Vector C is closed for every finite-dimensional
polynomial source/target Lie algebra.  Generic function-field degree excludes
algebraic polynomial orbits, and the reciprocal-root translation has an
explicit unbounded coefficient family.  The selected low-weight connections
have source rays \(18+8j\) or \(24+10j\).

The complete target classification is stronger.  Every finite-dimensional
polynomial Hamiltonian algebra containing the normalized cusp seed is
abelian and contained in \(\mathbb Q[H_0]\).  Its only finite-Lie divisor
profile is the known affine one.  Powers \(H_0^k\), \(k\ge2\), start in
normal layer \(3k-3\), leaving the first two source jets unchanged through
layer two.  Spectral projectors in those jets isolate layer-one \(z^4\) and
\(z^3\) generators and give the all-order source ray

\[
\operatorname{gr}\!
\left(\operatorname{ad}_{E_4}^{\,j}[E_4,E_3]\right)
=c_jD_{z^{6+3j}}^{(2+j)},
\qquad
\deg=8+4j,
\]

with

\[
\frac{c_{j+1}}{c_j}
=-\frac{7(j+6)(2j+1)}{64(j+5)}\ne0.
\]

This obstruction is coefficient-Lie algebraic, so it also covers
finite-dimensional formal flows whose generic-time maps are nonpolynomial.
It does not cover the infinite-dimensional coefficientwise-finite
staircases of Vector B.

## Consolidation rule

Finite prefixes are orientation evidence only.  A promoted conclusion about
\(\sigma_{\rm ct}\) requires an all-order construction or an infinite
gauge-independent obstruction.  The completed canonical recurrence and the
second transverse quotient are inputs to these attacks; neither is promoted
alone to the minimax conclusion.
