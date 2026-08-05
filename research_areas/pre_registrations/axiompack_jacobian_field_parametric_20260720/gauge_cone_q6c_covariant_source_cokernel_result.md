# Covariant source cokernel of the \(Q^6C\) prefix

## Result

Transport the row-one target prefix

\[
\lambda Q^6C
\]

under the complete controlled target background

\[
K_s=
\frac{96(s^2-12s+16)}
{(s-6)^3(s-4)^2(s+4)^2}P^3
+\frac{2s}{(s-4)(s+4)}PQ
-\frac14Q^2.
\]

If \(G'_s+\{K_s,G_s\}=0\) and \(G_0=Q^6C\), then \(G_1\) and
\(G_2\) lie in the target cone.  The first exit is \(G_3\), whose
outside-cone part is exactly

\[
-\frac5{108}P^9Q^3+\frac5{432}P^8Q^3.
\]

Insert the complete admissible continuation \(G_1,G_2\) into the
logarithm-first radial and one-\(C\) source normalizer.  It does not
remove the earlier source class.  In the grading

\[
\Gamma(a,b;q)=(2a-19q-2,\ 2b-19q-6),
\]

the retained terminal input is

\[
V_{\rm term}
=\frac{29\lambda}{65536}u^{20}z^{23}
\]

at cost four and grade \((-38,-36)\).  The cost-six instantaneous
terminal input is zero, while the complete source logarithm has

\[
[u^{39}z^{42}]\Omega^{\rm src}_6
=\frac{435\lambda^2}{2147483648}.
\]

Thus the class is a source-transport cokernel invisible to target-cone
membership through the admissible runway.

## Leading-amplitude response

The unique zero-grade logarithmic letter is

\[
A=-\frac{9\lambda}{16384}u^{20}z^{22}.
\]

For

\[
E_k=u^{20+19k}z^{23+19k},
\]

the density-\(z^2\) Hamiltonian bracket is

\[
[A/\lambda,E_k]
=\frac{9(10-19k)}{8192}E_{k+1}.
\]

No multiplier vanishes at an integral depth.  The terminal
right-Magnus response is

\[
\phi_3(x)
=\frac{x}{e^x-1}\int_0^1t^3e^{t^2x}\,dt,
\]

with constant coefficient \(1/4\) and, for \(k\ge1\),

\[
[x^k]\phi_3(x)=\frac{B_{k+1}}{2(k+1)!}.
\]

Every odd depth \(k=2m+1\) is nonzero.  The corresponding
leading-amplitude Hamiltonians occur at costs \(6+4m\), with exponents

\[
(39+38m,\ 42+38m),
\]

so this quotient has limiting spatial rate nineteen.

## Verification and boundary

The replay is
[`gauge_cone_q6c_covariant_source_cokernel.py`](gauge_cone_q6c_covariant_source_cokernel.py).
Its fast path derives the covariant target coefficients and the exact
all-order response.  The `--verify-full-projection` path reruns the full
source normalizer through cost six and checks the four displayed
instantaneous and logarithmic assertions.

This closes the pure \(Q^6C\) counterattack.  It does not yet give a
uniform theorem for every \(Q^bC\), mixed one-\(C\) prefixes, or powers
\(C^m\) with \(m\ge2\).
