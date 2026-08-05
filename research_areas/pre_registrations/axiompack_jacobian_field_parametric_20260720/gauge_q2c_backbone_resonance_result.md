# Contact-zero (Q^2C) resonance and its first positive-contact counterattack

**Status:** exact associated-grade and coupled finite-prefix result;
unrestricted symmetric tail minimax remains open; historical priority
unassessed

## Contact-zero associated grade

The lift-compatible target algebra is

\[
\mathbb Q+(P^3,PQ,Q^2).
\]

Contact zero means its associated grade modulo the cusp equation (C).
That quotient has one canonical symbol in every cusp weight (w\ge5):
(P^{w/2}) for even (w), and (P^{(w-3)/2}Q) for odd (w).  In the fixed
source chart,

\[
P_0=-\frac z4(3u^2z-4u-2),\qquad
Q_0=-\frac{uz^2}4(u^2z-u-1),\qquad
\det dF_0=-\frac{z^2}{8}.
\]

The paired source Hamiltonian is exactly

\[
h_H=8H(P_0,Q_0).
\]

A canonical weight-(w) symbol has nonzero leader (c_wu^wz^w), with all
source exponents componentwise at most (w).  For the (Q^2C) product
filtration

\[
G(a,b;j)=(2a-7j-2,2b-7j-6),
\]

every componentwise-nonpositive contact-zero letter is strictly negative in
the second component.  It cannot reach the zero-grade terminal action.

[`gauge_q2c_contact_zero_product_grade.py`](gauge_q2c_contact_zero_product_grade.py)
checks the exact pullback, product-grade additivity, training and held-out
windows, and a matched zero-grade control.  The all-weight conclusion uses
the support inequality rather than finite-cap stabilization.

## Movability of the first named terminal

Add a row-one weight-six backbone \(\beta P^3\).  At cost five and amplitude
(lambda^2), the coefficient of (u^{12}z^{16}) is

\[
\frac{3(563076\beta+283)}{16384}.
\]

Thus

\[
\beta=-\frac{283}{563076}
\]

cancels that named coordinate.  It leaves

\[
-\frac{893997}{512524288}u^{20}z^{20},
\]

which is outside the three current (C)-seed columns in that restricted
window.  This establishes movability of the representative and selects a
quotient calculation.

If a diagonal contact-zero leader (c_wu^wz^w) occurs at cost (j), its
orbit under (A=-9u^8z^{10}/64) is

\[
\operatorname{ad}_A^k(c_wu^wz^w)
=c_w\left(-\frac9{64}\right)^k2^k
\prod_{i=0}^{k-1}(w+7i)u^{w+7k}z^{w+7k}.
\]

The right-forward-`dexp` scalar is

\[
\frac{(-1)^k(j-2)}{(k+1)!},
\]

so cost two is the unique resonance.

## Cost-two contact-zero resonance

In the contact-zero associated grade, the unique weights-five-through-twelve
combination canceling every difference-two source monomial has coefficients

\[
\left(
\frac1{135},-\frac1{810},-\frac{11}{270},\frac{13}{1620},
\frac{13}{135},-\frac1{54},-\frac1{12},\frac2{135}
\right).
\]

The old zero-grade (A)-engine disappears.  On the region

\[
b-a\ge3,\qquad a+b\ge12,
\]

the class of (L_2) remains nonzero modulo every contact-zero associated-
grade symbol.  The exact annihilator has fourteen coordinates and pairs to
one.  It reads (z)-exponents at most twelve; canonical weights at least 25
are divisible by (z^{13}).  Weight caps 24 and 32 give the same functional.

## Static positive-contact preimage

The full lift algebra also contains positive powers of (C).  Including
those directions in the same finite compiler window cancels the entire
(L_2), not only its high-transverse projection.  The exact preimage is

\[
\boxed{
L_2
=8\left(\frac12Q^2C\right)(P_0,Q_0)}.
\]

Equivalently, the five monomial decomposition is

\[
\frac12Q^2C
=-\frac12P^2Q^2+2P^3Q^2+2Q^3-9PQ^3+\frac{27}{2}Q^4.
\]

Adding (-Q^2C/2) to the target logarithm cancels (L_2) exactly at that fixed
cost.  This direction has positive (C)-adic valuation, so it does not alter
the contact-zero associated-grade statement.

If the lower-row change is omitted, the cost-three Hamiltonian (L_3)
survives the span of every same-cost lift-compatible target monomial.  The
exact witness reads only (z)-exponents seven through nine.  This is a useful
static negative control, but it is not the coupled post-repair quotient.

The delayed (Q^2C) connection coefficient is the target velocity
\(sQ^2C\), whose target logarithm is exactly \(s^2Q^2C/2\).  The proposed
\(-s^2Q^2C/2\) repair has forward-`dexp` velocity \(-sQ^2C\).  The two
velocities cancel identically.  Therefore the complete coupled source and
target connections return to the no-prefix background, and (L_3) disappears
with (L_2).  The deterministic all-order identity and finite full-replay
stress are in
[`gauge_q2c_repair_identity.py`](gauge_q2c_repair_identity.py).

The deterministic certificate is
[`gauge_q2c_backbone_resonance.py`](gauge_q2c_backbone_resonance.py).

## Boundary and next residual

The contact-zero associated-grade quotient survives its complete polynomial
backbone.  The static target preimage does not move the same delayed prefix's
obstruction to cost three; it removes that prefix from the connection.
Neither statement determines the tail statistic.

The next residual is the least nonzero positive-contact coefficient over an
arbitrary moving contact-zero backbone.  Its own negative target logarithm
cannot be counted as an independent later control: choosing it simply makes
that coefficient zero and shifts the least-contact index.  A matching lower
bound must be uniform under this shift and under fixed-amplitude collisions.
