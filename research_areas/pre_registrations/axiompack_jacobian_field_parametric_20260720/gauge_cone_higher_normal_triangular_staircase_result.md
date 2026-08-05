# One-\(C\)-layer cone staircase retains slope two

## Result

The first cone direction in the seed cusp ideal,

\[
Q^2C,\qquad
C=4P^3-P^2-18PQ+27Q^2+4Q,
\]

does cancel the growing second-normal instantaneous shell.  It does not
lower the logarithmic tail rate below two.

This statement uses the corrected target-lift category: the bare
Hamiltonian \(Q\) is excluded from every radial row, every instantaneous
source Hamiltonian is divisible by \(z^3\), and both source and target
flows remain polynomial.

## Velocity-first coefficient

At target order six, the exact coefficient

\[
\boxed{-\frac{2945}{132120576}Q^2C}
\]

removes the \(r^8z^2\) velocity shell and lowers the instantaneous
Hamiltonian degree from \(18\) to \(16\).  The source Magnus logarithm
nevertheless has degree \(18\), with top shell

\[
\frac{1186929}{2014104780800}u^9z^9
+
\frac{232227}{1611283824640}u^8z^{10}.
\]

The first term is radial, so changing the \(Q^2C\) coefficient cannot
remove the complete shell.

## Logarithm-first coefficient

Choosing each ordinary cone row against the current source logarithm first,
then solving its representable second-normal shell, changes the order-six
coefficient to

\[
\boxed{-\frac{1210823}{64739082240}Q^2C}.
\]

This reduces logarithmic order seven to Hamiltonian degree \(16\).
The replay through target order ten gives logarithmic degrees

\[
\boxed{(16,16,20,20,21,26)}
\]

at target orders five through ten.  The two larger exceptional values are
the finite multiplier gaps \(w=7,10\).

Away from those gaps, a quotient below the seed cusp-normal cone becomes
the leading obstruction.  Its top Hamiltonian degrees at target orders
\(8,9,10\) are

\[
19,\ 21,\ 23=2n+3.
\]

At order nine, for example, the complete degree-\(21\) shell is supported
on

\[
u^{13}z^8,\quad u^{12}z^9,\quad u^{11}z^{10},
\quad u^{10}z^{11},\quad u^9z^{12},
\]

with nonzero exact rational coefficients.  Current radial target rows act
through normal order zero and current \(C\)-kernel rows begin in normal
order two, so the already-fixed current diagonals do not directly cancel
this negative-normal quotient.

## Boundary

The deterministic replay is
[`gauge_cone_radial_triangular_staircase.py`](gauge_cone_radial_triangular_staircase.py)
with `normalization_objective="logarithm"` and
`cancel_second_normal=True`.
The promoted target-order-ten prefix passes source/right and target/left
forward-`dexp` round trips.

The one-\(C\)-layer construction is therefore a finite negative for a
sub-two rate, while the corrected radial staircase still proves
\(\sigma_{\rm ct}\le2\).  This does not prove the matching lower bound:
earlier powers \(C^k\) can enter delayed Magnus brackets after the
density-\(z^2\) bracket lowers normal order, so an all-order \(C\)-adic
schedule remains unresolved.
