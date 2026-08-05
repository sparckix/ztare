# Exceptional \(P^2Q+Q^2\) rate-four theorem

## Result

Consider the low-weight order-one target family

\[
M_{\alpha,\beta}
=-\frac1{168}P^2Q+\alpha PQ+\beta Q^2.
\]

Its cost-two radial source velocity is

\[
\left(-\frac{325}{2688}+\frac{\beta}{2}\right)u^6z^6.
\]

It vanishes only at

\[
\beta_*=\frac{325}{1344}.
\]

At cost three the degree-sixteen radial velocity

\[
-\frac1{14336}u^8z^8
\]

is independent of \(\alpha,\beta\).  Thus the exceptional choice
\(\alpha=0,\beta=\beta_*\) removes the first radial generator but retains

\[
B=-\frac1{43008}u^8z^8
\]

in the right-Magnus logarithm.

For this exceptional connection,

\[
\boxed{
\text{source logarithmic rate}
=\text{symmetric logarithmic rate}
=4.
}
\]

## Terminal orbit

The additive grading

\[
(I,J)=(3a-7q-3,\ 3b-5q-9)
\]

is nonpositive on the complete instantaneous source connection, and \(B\)
is its unique zero-grade generator.  The terminal grade
\((-14,-7)\) has orbit

\[
E_k=u^{1+7k}z^{4+5k},
\qquad q_k=2+3k,
\]

with normalized adjoint multiplier

\[
E_{k+1}=-\frac{2k-3}{5376}E_k.
\]

Every nonzero coefficient on this orbit has source derivation degree

\[
4q_k-6.
\]

## All-order noncancellation

Scaling every negative-grade input by a marker decomposes the terminal
coefficient into linear, quadratic, and cubic sectors.  Among the two
quadratic grade pairs, the pair

\[
(-8,-4)+(-6,-3)=(-14,-7)
\]

has the closed response

\[
D^{\rm dom}(x)=\frac{x}{e^x-1}R(x),
\]

where

\[
k![x^k]R(x)
=-\frac{174k^2-k-164}
{2016(k+1)(3k+2)}.
\]

For positive even \(k\), coefficient extraction and
von Staudt--Clausen give

\[
\boxed{
27k!D_k^{\rm dom}\equiv1\pmod3.
}
\]

The linear sector, the other quadratic pair, and the cubic sector all
satisfy

\[
k!D_k^{\rm other}\in3^{-2}\mathbf Z_{(3)}.
\]

After multiplication by \(27\), those sectors vanish modulo three.
Therefore the complete terminal coefficient obeys

\[
27(2m)!D_{2m}\equiv1\pmod3
\qquad(m\ge1),
\]

and is nonzero at every positive even depth.

## Verification and boundary

The exact replay
[`gauge_p2q_q2_rate_four_dichotomy.py`](gauge_p2q_q2_rate_four_dichotomy.py)
checks the complete exceptional connection through logarithmic order sixty,
the marker decomposition, both quadratic grade-pair replays, the closed
dominant response, and the finite \(3\)-adic separation.  The accompanying
[`pencil`](gauge_p2q_q2_rate_four_dichotomy_pencil.md) gives the all-order
coefficient extraction and localized arithmetic argument.

This theorem classifies the exceptional point in the declared low-weight
order-one plane.  Later target coefficients can alter the cost-three radial
generator, so it does not establish an unrestricted minimax lower bound.
