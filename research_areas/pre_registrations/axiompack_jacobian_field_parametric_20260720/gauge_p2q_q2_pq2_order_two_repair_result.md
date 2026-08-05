# Order-two \(PQ^2\) repair: exact rate \(7/2\)

## Result

The cone-compatible target connection

\[
K_s^{[2]}
=K_s
-\frac{s}{168}P^2Q
+\frac{325s}{1344}Q^2
-\frac{s^2}{5376}PQ^2
\]

has

\[
\boxed{
\text{source logarithmic rate}
=\text{symmetric logarithmic rate}
=\frac72.
}
\]

In particular, the unrestricted symmetric tail statistic satisfies

\[
\boxed{\sigma_{\rm ct}\le\frac72}.
\]

## Newton upper bound

The \(PQ^2\) term is the minimum cone monomial whose seed radial weight is
eight.  Its coefficient cancels the cost-three velocity
\(-u^8z^8/14336\) left by the exceptional order-one prefix.

The complete source Hamiltonian degree profile at costs one through six is

\[
(-\infty,10,14,18,20,22).
\]

All later inputs have degree at most twenty-two.  The additive grading

\[
G_{7/2}=2(a+b)-7q-8
\]

is nonpositive, with unique zero-grade logarithmic generator

\[
X=\frac{137}{4128768}u^9z^9
\quad\text{at cost four}.
\]

Therefore

\[
\deg\Omega_q^{\rm src}\le\frac72q+4.
\]

The target connection remains in the slope-one Hamiltonian envelope, so the
source controls the symmetric maximum.

## Closed lower ray

The closed grade-\(-12\) orbit is

\[
E_k=u^{17+8k}z^{16+6k},
\qquad q_k=10+4k,
\]

with adjoint multiplier

\[
[X,E_k]
=\frac{137(2k+1)}{458752}E_{k+1}.
\]

After this multiplier is removed, the logarithmic response is

\[
D(x)
=D_0\frac{x}{e^x-1}
\int_0^1w(t)e^{xt}\,dt,
\]

where

\[
D_0=\frac{18769}{202035261603840},
\qquad
w(t)=10t^2+\frac{50}{3}t-\frac{80}{3}t^{3/2}.
\]

The weight is nonnegative on \([0,1]\), has total mass one, and has moments

\[
\int_0^1t^kw(t)\,dt
=\frac{10(2k+9)}
{3(k+2)(k+3)(2k+5)}.
\]

Thus

\[
\frac{k!D_k}{D_0}
=\int_0^1w(t)B_k(t)\,dt.
\]

Every nonconstant cosine coefficient of \(w\) is negative.  The Fourier
series of the even Bernoulli polynomials then gives

\[
\operatorname{sign}D_{2m}=(-1)^m
\qquad(m\ge1).
\]

The corresponding source derivation degree is

\[
\frac72q_{2m}-5,
\]

which proves the matching lower rate.

## Verification and boundary

The exact replay
[`gauge_p2q_q2_pq2_order_two_repair.py`](gauge_p2q_q2_pq2_order_two_repair.py)
reconstructs the complete connection, proves the uniform Newton bound,
performs the right-`dexp` round trip, and checks the closed response through
logarithmic order ninety.  The accompanying
[`pencil`](gauge_p2q_q2_pq2_order_two_repair_pencil.md) gives the all-order
moment and Fourier-sign proof.

This is one coefficientwise-finite staircase prefix.  A parameter-order-three
cone coefficient can cancel its cost-four radial generator, so the result is
an upper bound rather than a universal minimax lower bound.
