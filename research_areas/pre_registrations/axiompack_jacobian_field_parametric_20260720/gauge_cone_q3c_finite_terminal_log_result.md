# Finite terminal-log candidate from \(Q^3C\)

## Reversal of the obstruction

The immediate-exit prefix \(Q^3C\) has a nonzero complete cost-three
source logarithm.  In the slope-ten grading its terminal part begins

\[
\Omega_{\rm term}
=\frac{9\lambda}{256}s^2u^{11}z^{13}
-\frac{27\lambda}{2048}s^3u^{12}z^{14}.
\]

The first attempt treated the cost-three row as a lone velocity input
and predicted an infinite inverse-`dexp` response.  The next exact row
falsifies that model.  The staircase supplies

\[
\operatorname{term}V_5
=\frac{243\lambda^2}{524288}u^{22}z^{24},
\]

which cancels the predicted cost-five logarithm.

## Finite-log model

Put

\[
E_k=u^{12+10k}z^{14+10k}.
\]

The zero-grade letter acts by

\[
\operatorname{ad}_{A}E_k
=\frac{9(1+10k)}{128}E_{k+1}.
\]

If the terminal logarithm is exactly the two displayed rows, its
right-forward-`dexp` response is

\[
\psi_2(x)=2+\frac{1-e^{-x}}x.
\]

The constant coefficient is three and, for \(k\ge1\),

\[
[x^k]\psi_2(x)=\frac{(-1)^k}{(k+1)!}.
\]

The full projected staircase agrees at four consecutive terminal rows:

\[
\begin{array}{c|c|c}
\text{cost} & \operatorname{term}V & \operatorname{term}\Omega\\
\hline
3 & -81\lambda u^{12}z^{14}/2048
  & -27\lambda u^{12}z^{14}/2048\\
5 & 243\lambda^2u^{22}z^{24}/524288 & 0\\
7 & -8019\lambda^3u^{32}z^{34}/67108864 & 0\\
9 & 1515591\lambda^4u^{42}z^{44}/34359738368 & 0.
\end{array}
\]

Thus the leading terminal quotient currently supports a finite
logarithm rather than an escape obstruction.

## Entire leading grade window

The cancellation is not confined to the terminal monomial.  In the
componentwise window

\[
\Gamma\ge(-8,-8),
\]

the complete prefix-dependent logarithm through cost nine is supported
only at costs two and three.  Its cost-two Hamiltonian is

\[
\begin{aligned}
\Omega_2/\lambda={}&
\frac3{32}u^7z^9-\frac{135}{256}u^7z^{10}
+\frac{51}{256}u^7z^{11}
-\frac{57}{256}u^8z^{10}\\
&+\frac{57}{128}u^8z^{11}
+\frac{67}{256}u^9z^{11}
-\frac{35}{256}u^9z^{12}\\
&-\frac{39}{256}u^{10}z^{12}
+\frac9{256}u^{11}z^{13},
\end{aligned}
\]

and

\[
\Omega_3/\lambda=-\frac{27}{2048}u^{12}z^{14}.
\]

Forward `dexp` of these two rows reproduces every prefix-dependent
velocity coefficient retained in the window.  The nonzero rows after
cost three lie only on the displayed terminal orbit.

## Verification and boundary

The replay is
[`gauge_cone_q3c_finite_terminal_log.py`](gauge_cone_q3c_finite_terminal_log.py).
Its fast path computes the all-order forward-`dexp` image and checks the
inverse round trip.  The `--verify-full-projection` path reruns the
normalized connection through cost nine and compares every retained
prefix-dependent row, not only the terminal orbit.

The equality between that actual connection and the finite-log model is
verified through cost nine in this window.  It does not extend to the
next additive layer.  At grade \((-16,-12)\), the logarithm has an
all-order nonterminating ray proved in
[`gauge_cone_q3c_lower_terminal_recurrence_result.md`](gauge_cone_q3c_lower_terminal_recurrence_result.md).
Thus this artifact records the finite leading cancellation that delayed
the obstruction; it is not a finite-prefix escape.
