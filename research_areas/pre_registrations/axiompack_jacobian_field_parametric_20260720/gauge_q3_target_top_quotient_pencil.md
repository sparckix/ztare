# Alternating-cubic target top quotient

## Claim boundary

This pencil studies the target logarithm of the single cancellation

\[
K_s^{\rm new}=K_s-\frac{s}{56}Q^3.
\]

It can decide whether its extremal \(P^3/Q^3\) quotient has an all-order
nonzero ray.  It does not classify other order-one cancellations or the
full coupled minimax problem.

## Exact quotient

For a target Hamiltonian monomial \(P^aQ^b\) at parameter cost \(q\), put

\[
E=4a+5b-3q-9.
\]

Every instantaneous target term has \(E\le0\).  The only zero-grade terms
are

\[
\alpha A,\qquad \beta sC,\qquad
A=P^3,\quad C=Q^3,
\]

at costs one and two, with

\[
\alpha=-\frac1{36},\qquad
\beta=-\frac1{56}.
\]

Thus the zero-grade target logarithm is the universal left-Magnus series
for velocity \(\alpha A+\beta sC\).

For counts \(x,y\ge0\), define

\[
E_{x,y}
=P^{\,2x-y+1}Q^{\,2y-x+1}
\]

when both exponents are nonnegative.  The two generators are
\(A=E_{1,0}\), \(C=E_{0,1}\), and direct calculation gives

\[
[E_{x,y},E_{w,u}]
=3(yw-xu+y-x+w-u)E_{x+w,y+u}.
\]

Consequently every admissible count bidegree is at most one-dimensional.
The distinguished ray is

\[
W_m=E_{2m,m+1}=P^{3m}Q^3
\]

at logarithmic order \(4m+2\).  Its coefficient factors as

\[
\alpha^{2m}\beta^{m+1}c_m
\]

for a universal rational number \(c_m\).

## Eigenquestion

Is \(c_m\ne0\) for every \(m\ge0\)?

The exact Lie word

\[
\operatorname{ad}_{C}\operatorname{ad}_{A}^{\,2}W_m
=162(3m+4)W_{m+1}
\]

shows that the ray exists in the Lie algebra.  It does not show that its
left-Magnus coefficient survives the sum over all words of the same counts.

## Discriminating test

1. Replay the equation-typed left-Magnus recursion directly in the
   one-dimensional count bidegrees.
2. Remove the forced amplitude
   \(\alpha^{2m}\beta^{m+1}\).
3. Search the exact \(c_m\) sequence for a scalar rational recurrence,
   a holonomic recurrence, or a generating differential equation.
4. Reserve a held-out suffix beyond the discovery range.
5. If a recurrence is found, derive it from the count algebra and prove
   that its multiplier or positive convolution cannot vanish.

## Kill and success conditions

The ray claim is killed by one exact zero.  A finite nonzero prefix does not
settle the eigenquestion.  Success requires an all-order identity with a
nonvanishing proof; a guessed recurrence that only fits the discovery
window is recorded as finite evidence.

If the ray survives, the target Hamiltonian degree is \(3m+3\), the target
derivation degree is \(3m+2\), and the limiting rate along
\(n=4m+2\) is \(3/4\).

## Exact finite outcome

The count-algebra replay is
[`gauge_q3_target_top_quotient.py`](gauge_q3_target_top_quotient.py).
It verifies nonzero universal coefficients through \(m=16\), or
logarithmic order \(66\).  The first values are

\[
\frac12,\quad
\frac9{10},\quad
-\frac{9963}{5600},\quad
-\frac{11845380303}{56056000},\quad
\frac{9134180037909}{15247232000}.
\]

A discovery window of twelve terms and five held-out terms rejects every
homogeneous polynomial-coefficient recurrence of order at most four and
coefficient degree at most three.  The signs also cease to follow the first
apparent two-by-two pattern.

This is a finite negative result about a cheap recurrence class, not an
all-order target theorem.  The companion source excess calculation now
excludes the \(Q^3\) cancellation independently, so no target extrapolation
is used in the candidate disposition.
