# Critical normalization-node separator

## Exact finite-velocity theorem

Put

\[
\widehat P=x^2P_{\rm crit}(x,0)=\frac{x^2(x-6)}8,
\qquad
\widehat Q=x^3Q_{\rm crit}(x,0)=\frac{x^3(3x-16)}{64}.
\]

The two normalization points

\[
x_\pm=2\pm2\sqrt3
\]

have the common image

\[
(\widehat P(x_\pm),\widehat Q(x_\pm))=(-2,1).
\]

A target monomial \(P^aQ^b\) of cusp weight \(w=2a+3b\), placed in its
critical row \(j=w-6\), satisfies

\[
x^jP_{\rm crit}(x,0)^aQ_{\rm crit}(x,0)^b
=x^{-6}\widehat P(x)^a\widehat Q(x)^b.
\]

Therefore \(x^6\) times every finite critical target velocity restriction is
a polynomial in \((\widehat P,\widehat Q)\), so it has equal values at
\(x_+\) and \(x_-\).

The required normalized radial primitive instead is

\[
G(x)=\frac{x^7(56x^2-441x+864)}{1032192},
\]

and direct evaluation gives

\[
G(x_\pm)=\frac{2239}{252}\pm\frac{36\sqrt3}{7},
\qquad
G(x_+)-G(x_-)=\frac{72\sqrt3}{7}\ne0.
\]

Hence no finite critical target velocity cancels the radial source demand.
The companion replay
[gauge_pure_contact_zero_critical_node_separator.py](gauge_pure_contact_zero_critical_node_separator.py)
also compiles the average/separator quotient with the Filtered Obstruction
Compiler.

## Boundary

This is stronger than the single-column delay calculation at the velocity
level: it handles every finite linear combination at once.  It does not
settle finite logarithms, because a finite target logarithm may have an
infinite forward-dexp velocity.  The unrestricted induction still requires
the two-sided finite-log orbit theorem.
