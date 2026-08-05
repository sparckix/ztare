# Order-two cone repair after the \(P^2Q+Q^2\) exception

## Claim boundary

This pencil tests one later cone-compatible coefficient.  It does not assume
that canceling the exceptional cost-three radial face improves the
logarithmic rate, and it does not infer a minimax value from a finite
prefix.

## Eigenquestion

After the exceptional order-one choice

\[
K_s^{(1)}
=-\frac{s}{168}P^2Q
+\frac{325s}{1344}Q^2
\]

cancels the cost-two radial generator, can a polynomial cone coefficient at
order two cancel

\[
-\frac1{14336}u^8z^8
\]

without creating an equal-or-steeper source or target Newton face?

## Forced minimum cone monomial

At the seed,

\[
\operatorname{top}P_0=-\frac34u^2z^2,
\qquad
\operatorname{top}Q_0=-\frac14u^3z^3.
\]

A cone monomial \(P^aQ^b\), \(b\ge1\), has radial seed weight \(2a+3b\).
The minimum solution of

\[
2a+3b=8
\]

inside the cone is \((a,b)=(1,2)\).  Since

\[
\operatorname{top}(P_0Q_0^2)
=-\frac3{64}u^8z^8,
\]

and a target perturbation pulls back with the Hamiltonian factor eight, the
unique coefficient on this monomial that cancels the radial velocity is

\[
\boxed{
K_s^{(2)}
=-\frac{s^2}{5376}PQ^2.
}
\]

Its source Hamiltonian perturbation is

\[
-\frac{s^2}{672}P_sQ_s^2,
\]

whose seed top is \(+u^8z^8/14336\).

## Discriminating replay

Construct the complete source and target velocities for

\[
K_s^{\rm exc}
=K_s
-\frac{s}{168}P^2Q
+\frac{325s}{1344}Q^2
-\frac{s^2}{5376}PQ^2.
\]

The replay must:

1. verify exact contact and forward-`dexp` round trips on both sides;
2. certify disappearance of both radial logarithmic generators at costs two
   and three;
3. compute the complete source Newton polygon, not only its top total
   degree;
4. identify every additive zero-grade face and its first closed orbit;
5. carry any proposed terminal orbit beyond the fitted prefix and derive an
   all-order response equation before promoting a rate;
6. report the target logarithmic envelope for the added cubic.

## Exact Newton result

The complete instantaneous source Hamiltonian degrees at costs one through
six are

\[
(-\infty,10,14,18,20,22).
\]

The perturbation has uniform spatial degree twenty-two, so every later input
lies strictly below the leading face.  The additive integer grading

\[
G_{7/2}(u^az^b\text{ at cost }q)
=2(a+b)-7q-8
\]

is nonpositive on the complete connection.  Its unique zero-grade velocity
is

\[
\frac{137}{1032192}u^9z^9
\quad\text{at cost four},
\]

and the corresponding logarithmic generator is

\[
X=\frac{137}{4128768}u^9z^9.
\]

This proves the all-order upper bound

\[
\deg\Omega_q^{\rm src}\le\frac72q+4.
\]

The target additions have degree at most three and lie below this source
envelope.

## Closed terminal response

The first closed terminal grade is \(G_{7/2}=-12\).  Normalize its
\(X\)-orbit as

\[
E_k=u^{17+8k}z^{16+6k},
\qquad q_k=10+4k.
\]

The raw adjoint multiplier is

\[
[X,E_k]
=\frac{137(2k+1)}{458752}E_{k+1}.
\]

Write the normalized logarithmic coefficient as

\[
D(x)=\sum_{k\ge0}D_kx^k,
\qquad
D_0=\frac{18769}{202035261603840}.
\]

Exact elimination of the lower grades from the terminal forward-`dexp`
equation gives

\[
\boxed{
D(x)
=D_0\frac{x}{e^x-1}
\int_0^1w(t)e^{xt}\,dt,
}
\]

where

\[
w(t)
=10t^2+\frac{50}{3}t-\frac{80}{3}t^{3/2}
=\frac{10}{3}t(3\sqrt t-5)(\sqrt t-1).
\]

In particular \(w(t)\ge0\) on \([0,1]\) and
\(\int_0^1w(t)\,dt=1\).  Its moments are

\[
A_k
=\int_0^1t^kw(t)\,dt
=\frac{10(2k+9)}
{3(k+2)(k+3)(2k+5)}.
\]

If

\[
U_k=\frac{k!D_k}{D_0},
\]

then

\[
U_k=\int_0^1w(t)B_k(t)\,dt
\]

and the terminal `dexp` equation is equivalently the triangular recurrence

\[
\sum_{j=0}^{k-1}\binom{k}{j}U_j=kA_{k-1}.
\]

## All-order sign

For \(\ell\ge1\), put \(a=2\pi\ell\) and

\[
J_\ell=\int_0^1t^{-1/2}\cos(at)\,dt.
\]

Two integrations by parts give the exact cosine transform

\[
\int_0^1w(t)\cos(at)\,dt
=\frac{20}{a^2}(J_\ell-1).
\]

After \(t=y^2\),

\[
J_\ell
=\frac2{\sqrt\ell}F(\sqrt\ell),
\qquad
F(A)=\int_0^A\cos(2\pi z^2)\,dz.
\]

The Fresnel value \(F(\infty)=1/4\) and one tail integration by parts give

\[
F(A)\le\frac14+\frac1{2\pi A}
\quad(A\ge1).
\]

Hence

\[
J_\ell
\le\frac1{2\sqrt\ell}+\frac1{\pi\ell}
<1.
\]

Every nonconstant cosine coefficient of \(w\) is therefore strictly
negative.  The Fourier series

\[
B_{2m}(t)
=(-1)^{m+1}
\frac{2(2m)!}{(2\pi)^{2m}}
\sum_{\ell\ge1}
\frac{\cos(2\pi\ell t)}{\ell^{2m}}
\]

now yields

\[
\boxed{\operatorname{sign}U_{2m}=(-1)^m}
\qquad(m\ge1).
\]

Thus the terminal coefficient is nonzero at every positive even depth.
At \(n=10+8m\), its source derivation degree is

\[
\frac72n-5.
\]

Together with the Newton upper bound,

\[
\boxed{
\text{source logarithmic rate}
=\text{symmetric logarithmic rate}
=\frac72.
}

The replay
[`gauge_p2q_q2_pq2_order_two_repair.py`](gauge_p2q_q2_pq2_order_two_repair.py)
checks the complete instantaneous connection, the right-`dexp` round trip,
the terminal recurrence, and the closed response through logarithmic order
ninety.

## Boundary

This proves a second explicit minimax upper bound,
\(\sigma_{\rm ct}\le7/2\).  A parameter-order-three cone coefficient can
alter the cost-four radial generator, so the unrestricted lower bound
remains open.
