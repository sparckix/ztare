# \(Q^3\)-cancellation source excess modules

## Claim boundary

This pencil studies the source logarithm for the exact order-one target
perturbation

\[
K_s^{\rm new}=K_s-\frac{s}{56}Q^3,
\qquad
\Delta V_s^{\rm src}=-\frac{s}{7}Q_s^3.
\]

It can exclude this connection if one closed source quotient has a
surviving all-order ray.  It cannot rule out a different earlier target
coefficient or a later coefficientwise cancellation.

## Grading

In the translated chart \(u=1+v\), \(z=2+2t-3v\), a Hamiltonian monomial
\(u^az^b\) at parameter cost \(q\) has slope-seven excess

\[
G=a+b-7q-4.
\]

For the density \(z^2\,du\wedge dz\), Hamiltonian brackets subtract four
from total degree.  Hence

\[
G([H_1,H_2])=G(H_1)+G(H_2).
\]

The perturbation creates the unique zero-excess logarithmic generator

\[
A_7=\frac1{896}u^9z^9
\]

at cost two.  Every fixed negative excess is therefore a module under
\(\operatorname{ad}_{A_7}\).

The first tested nonradial seed,

\[
B=\frac5{3584}u^8z^9
\]

lies at excess \(-8\).  Its raw radial orbit is nonzero, but the complete
finite core cancels its Magnus response.  This pencil begins with the next
negative excess rather than repeating that Lie-word test.

## Eigenquestion

What is the largest \(\gamma<0\) for which the complete excess-\(\gamma\)
source logarithm has a nonzero infinite
\(\operatorname{ad}_{A_7}\)-subsequence?

## Discriminating test

1. Reconstruct the exact rational source velocity and add
   \(-sQ_s^3/7\).
2. Prove a uniform spatial support box for its instantaneous Hamiltonians.
3. Enumerate every velocity term above a declared excess floor.  The
   support box must imply that no omitted later cost can re-enter.
4. Replay right-Magnus in the filtered quotient and identify the first
   surviving radial module.
5. Derive its finite forcing core and universal response.  A nonzero raw
   adjoint word is insufficient.
6. Reserve orders beyond the discovery prefix for exact replay.

## Success and kill conditions

A source obstruction succeeds only with a closed quotient, an all-order
response identity, and a nonvanishing subsequence.  It is killed if every
declared excess module has finite logarithmic support or zero response.

If all modules above the floor vanish but the floor is not exhaustive, the
result is a finite filtration advance.  It is not promoted to a source
upper bound.

## Outcome

The first surviving module is \(G=-13\).  The exact support box is

\[
a,b\le12
\]

for the perturbation Hamiltonian and \(a,b\le9\) for the base connection.
Thus every instantaneous Hamiltonian has total degree at most \(24\).
Costs \(q\ge6\) have

\[
G\le24-7q-4<-20,
\]

so the replay in \(G\ge-20\) has no omitted later velocity input.

The logarithm outside one \(G=-13\) orbit stops at cost five.  Put

\[
A=\frac1{896}u^9z^9,\qquad
E_0=u^{17}z^{16},\qquad E_{k+1}=[A,E_k].
\]

Then

\[
E_k=
\left(
\prod_{j=0}^{k-1}\frac{9(2j+1)}{896}
\right)
u^{17+8k}z^{16+6k}.
\]

The finite polynomial logarithm forces this module by

\[
F(x)
=-\frac{27}{12845056}
\frac{x-1+e^{-x}}{x^2}.
\]

For a terminal correction \(s^6D(x)E_0\), where
\(x=s^2\operatorname{ad}_A\), right-forward-`dexp` gives

\[
2D+f(4D+2xD')+F=0,
\qquad
f=\frac{1-e^{-x}}x.
\]

The coefficient of \(d_k\) is \(2(k+3)\), so the formal solution is unique.
It is

\[
D(x)
=\frac{27}{12845056x^2}
\left(
\frac{x}{e^x-1}-1+\frac x2
\right).
\]

Consequently the coefficient on \(E_k\) is

\[
\frac{27}{12845056}
\frac{B_{k+2}}{(k+2)!}.
\]

At \(k=2m\), positive even-Bernoulli nonvanishing gives a nonzero source
Hamiltonian

\[
u^{17+16m}z^{16+12m}
\]

at logarithmic order \(n=6+4m\).  Its derivation degree is

\[
(17+16m)+(16+12m)-3
=7n-12.
\]

Thus the \(Q^3\) cancellation is excluded at all orders by a rate-seven
source ray.  The exact reconstruction and independent replay through order
thirty-six are in
[`gauge_q3_source_excess_modules.py`](gauge_q3_source_excess_modules.py).
