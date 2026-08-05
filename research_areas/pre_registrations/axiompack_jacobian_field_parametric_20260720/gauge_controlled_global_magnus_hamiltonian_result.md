# Exact global-control Hamiltonian Magnus replay

## Exact chart and conventions

Put

\[
z=2+2t-3v.
\]

The preserved source density becomes \(z^2\).  A source Hamiltonian \(H\)
therefore represents the vector field

\[
X_H=
\left(
\frac{H_z}{z^2},
-\frac{H_v}{z^2}
\right),
\]

and the exact polynomial bracket is

\[
\{v^az^b,v^Az^B\}_{z^2}
=(bA-aB)v^{a+A-1}z^{b+B-3}.
\]

The source equation is

\[
\partial_s\psi_s=D\psi_sV_s,
\]

so its instantaneous velocity is right-placed.  The target equation is
left-placed.  The replay uses these two placements separately and applies
the matching forward `dexp` on both sides.

## Order-nine correction

For the exact target Hamiltonian

\[
K_s=a(s)P^3+b(s)PQ-\frac14Q^2,
\]

the source logarithm has derivation degrees

\[
-\infty,11,13,15,17,22,24,26,34
\]

through orders one to nine.  The top order-nine Hamiltonian is

\[
\boxed{
-\frac{23}{42278584320}v^{20}z^{17}.
}
\]

The proposed continuation \(v^{n+7}z^{n+6}\) would have given derivation
degree \(28\) at order nine.  Its order-nine coefficient is instead the
subleading nonzero value

\[
-\frac{844253}{47563407360}.
\]

Thus the earlier orders-six-to-eight slope-two pattern is exactly
falsified at its first preregistered kill order.

## Symmetric target check

The target Magnus logarithm was replayed through order 15.  Its derivation
degrees are

\[
2,2,2,2,3,3,4,4,5,5,6,6,7,7,8.
\]

The source already dominates the symmetric maximum at order nine.  This
does not remove the need for an all-order source analysis, but it rules out
a hidden target cost in the checked window.

## All-order bigraded theorem

For a source Hamiltonian monomial \(v^az^b\) at cost \(q\), define

\[
I=a-3q-1,\qquad J=b-2q-3.
\]

The bracket adds these grades.  All exact velocity grades lie in the
nonpositive quadrant, and

\[
-\frac3{448}(vz)^7
\]

at parameter cost two is the unique zero-grade velocity letter.  Moreover,
the all-parameter source Hamiltonian has \(a,b\leq9\).  Hence the rectangle
down to \((-6,-3)\) is closed and receives no instantaneous term of cost at
least six.

The translation

\[
u=1+v
\]

preserves polynomial degree and turns the complete grade-zero logarithm into

\[
A=-\frac3{896}(uz)^7.
\]

In the translated southwest quotient the instantaneous connection has only
eighteen monomials, at parameter costs two, three, and four.  Away from
terminal grade \((-6,-3)\), its logarithm is exactly

\[
\Omega_{\rm poly}(s)=s^2L_2+s^3L_3+s^4L_4.
\]

The decisive bracket relations are

\[
\begin{aligned}
[L_2,L_3]&=-\frac7{32768}u^{10}z^{10},\\
[L_2,L_4]&=-\frac1{131072}u^{13}z^{12},\\
[L_3,L_4]&=0
\end{aligned}
\]

in the quotient.  The first two brackets already have terminal grade.
Every nonzero outer bracket after either core must therefore use the sole
zero-grade term \(A\).

For the even terminal sector, set

\[
E_0=u^7z^8,\qquad E_{k+1}=[A,E_k].
\]

The monomial bracket gives

\[
E_k=
\left(-\frac3{128}\right)^k
\prod_{j=0}^{k-1}(2j-1)\,
u^{7+6k}z^{8+4k},
\]

and none of these orbit multipliers vanishes.

Write

\[
T_{\rm even}
=\sum_{k\ge0}s^{4+2k}d_kE_k,
\qquad
D(x)=\sum_{k\ge0}d_kx^k.
\]

The even forcing from \(\Omega_{\rm poly}\) is the single core
\(2[L_2,L_4]\) followed by arbitrary \(A\)-adjoints:

\[
F(x)=\frac1{1536}
\left(1-\frac{1-e^{-x}}x\right).
\]

For a right-placed source velocity, exact forward `dexp` on the terminal
module gives

\[
2\left[D+f(D+xD')\right]+F=\frac7{3072},
\qquad
f(x)=\frac{1-e^{-x}}x.
\]

The coefficient multiplying \(d_k\) in the \(x^k\) equation is
\(2(k+2)\), so the formal solution is unique in characteristic zero.
Direct symbolic substitution gives

\[
\boxed{
D(x)=\frac7{12288}
+\frac1{2048x}
\left(
\frac{x}{e^x-1}-1+\frac{x}{2}
\right).
}
\]

Consequently

\[
d_0=\frac7{12288},
\qquad
d_k=\frac{B_{k+1}}{2048(k+1)!}\quad(k\ge1).
\]

Equivalently, the coefficient at order \(6+2r\) on

\[
u^{13+6r}z^{12+4r}
\]

is

\[
\boxed{
c_r=
\frac1{2^{20}}
\left(-\frac3{128}\right)^r
(2r-1)!!
\frac{12B_{r+2}}{(r+2)!}.
}
\]

An independent exact quotient replay matches this identity through order
81.  Its first nonzero terms at orders \(6,10,14,18\) are

\[
\frac1{1048576},\quad
-\frac9{343597383680},\quad
\frac{27}{2251799813685248},\quad
-\frac{24057}{1475739525896764129280}.
\]

At \(r=2m\), the nonzero subsequence has order \(n=6+4m\), Hamiltonian
exponents

\[
(3n-5,2n),
\]

and source derivation degree \(5n-8\).

The elementary positive-convolution recurrence already used for the
exceptional-divisor theorem proves \(B_{2m+2}\ne0\).  The new Lean arithmetic
endpoint checks that nonvanishing transfers through the complete radial
adjoint multiplier, verifies the degree formula, and proves that these
degrees exceed every fixed natural cap.

The symbolic replay is
[`gauge_controlled_global_magnus_all_order.py`](gauge_controlled_global_magnus_all_order.py).
The arithmetic endpoint is
[`AxiomPackJacobianGlobalControlMagnusEscapeArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianGlobalControlMagnusEscapeArithmetic.lean).

## Order-three perturbation rigidity

The Bernoulli tail is multiplied by the scalar

\[
\Delta=H+2N=\frac1{1024},
\]

where \(H\) is the direct cost-four terminal velocity and \(N\) is the
normalized \(2[L_2,L_4]\) seed.  This scalar cannot be changed by adding an
arbitrary polynomial coefficient \(s^3M(P,Q)\) to the target Hamiltonian.

Indeed, in the translated seed chart,

\[
dP_0\wedge dQ_0=-\frac{z^2}{8}\,du\wedge dz,
\]

so the source Hamiltonian perturbation is \(8M(P_0,Q_0)\).  The defect
functional reads only nine coefficients with \(z\)-exponent at most eleven.
The seed orders

\[
\operatorname{ord}_z(P_0^aQ_0^b)=a+2b
\]

reduce an arbitrary polynomial to 42 possible monomials, and the exact
functional vanishes on every one.  The replay is
[`gauge_global_ray_defect_perturbation.py`](gauge_global_ray_defect_perturbation.py).

## Order-one cancellation dispositions

Two exact order-one directions cancel the rate-five generator, but neither
produces a bounded logarithm.

The noncentral perturbation

\[
K_s-\frac{s}{56}Q^3
\]

has a closed source excess-\(-13\) module.  Its right-Magnus response is

\[
\frac{27}{12845056}
\frac{B_{k+2}}{(k+2)!}
\prod_{j=0}^{k-1}\frac{9(2j+1)}{896}.
\]

At even depth \(k=2m\), this gives a nonzero source derivation of degree
\(7n-12\) at every \(n=6+4m\).  The exact theorem is recorded in
[`gauge_q3_source_excess_modules_result.md`](gauge_q3_source_excess_modules_result.md).

The seed-central perturbation

\[
K_s-\frac9{28}sH_0^2,
\qquad
H_0=-P^3/36-Q^2/4,
\]

creates a different closed source quotient.  Its nonzero subsequence has
derivation degree \(10n-18\) at the same orders \(n=6+4m\).  The exact
theorem is recorded in
[`gauge_seed_central_magnus_transfer_result.md`](gauge_seed_central_magnus_transfer_result.md).

The lower-Newton-weight perturbation

\[
K_s-\frac{s}{168}P^2Q
\]

also cancels the original generator.  Its complete source Newton support
gives the all-order upper bound
\(\deg\Omega_n^{\rm src}\le4n+4\).  The triangular \(h=5\) boundary has
normalized response

\[
-\frac{221}{26208}
+\frac{23}{1950}x
+\frac{13}{1872}\frac{x}{e^x-1}.
\]

Its even Bernoulli coefficients give a nonzero subsequence of exact source
derivation degree \(4n-6\) at \(n=2+4m\).  Thus this connection has exact
symmetric logarithmic rate four, proving a minimax upper bound of four.
The theorem and its remaining universal boundary are recorded in
[`gauge_p2q_order_one_cancellation_result.md`](gauge_p2q_order_one_cancellation_result.md).

## Boundary

This proves unbounded source logarithmic degree for the displayed exact
global connection, with a nonzero subsequence of derivation degree \(5n-8\).
It also proves rigidity under arbitrary polynomial changes to this
connection's order-three target coefficient and excludes two exact
order-one cancellations by transferred source rays.  It does not prove a
rate-four lower bound after minimizing over all cone-compatible gauges:
another order-one polynomial or later coefficient can alter the quotient.
A different coefficientwise-finite staircase could still have a smaller
symmetric tail rate.
