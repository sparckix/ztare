# Mixed-orientation Magnus audit of the moving cone prefix

## Why the two factors use different signs

The infinitesimal contact equation is

\[
\partial_sF_s=X_s\circ F_s+dF_sV_s.
\]

Writing

\[
F_s=A_s\circ F_0\circ\psi_s
\]

gives

\[
A'_s=X_s\circ A_s,\qquad
\psi'_s=D\psi_s\,V_s.
\]

Thus the target factor has matrix analogue \(A'=XA\), while the source
factor has matrix analogue \(\psi'=\psi V\).  For
\(A=\exp\Omega_{\rm tar}\), inverse `dexp` therefore has first Bernoulli
coefficient \(-1/2\).  For
\(\psi=\exp\Omega_{\rm src}\), it has \(+1/2\).  Equivalently, the target
forward `dexp` uses

\[
\sum_{k\ge0}\frac{\operatorname{ad}_\Omega^k}{(k+1)!},
\]

and the source forward `dexp` uses

\[
\sum_{k\ge0}\frac{(-1)^k\operatorname{ad}_\Omega^k}{(k+1)!}.
\]

Both exact forward round trips pass through order seven.  Using the same
orientation on both sides preserves the degree profiles below but reverses
the first orientation-sensitive source shells.

## Exact degree profiles

For the selected cone connection from the natural-weight replay, the
instantaneous source velocity degrees at \(j=0,\ldots,6\) are

\[
(5,5,7,9,11,13,14).
\]

After converting \(V_j,K_j\) to ordinary coefficients by division by
\(j!\), the actual source precomposition logarithm has component degrees
at logarithmic orders \(1,\ldots,7\)

\[
\boxed{(5,5,9,11,14,18,22)}.
\]

The target logarithmic Hamiltonian degrees are

\[
\boxed{(2,3,3,3,4,4,5)},
\]

and the corresponding Hamiltonian-vector-field degrees are

\[
(1,2,2,2,3,3,4).
\]

The maximum target cusp weights are exactly

\[
(6,7,8,9,10,11,12).
\]

The target logarithm remains cone-valued, as required by Poisson closure.

## Exact source top shells

Use adapted coordinates

\[
V=v,\qquad G=t-\frac32v.
\]

The source top shells for the correct precomposition orientation are

\[
\begin{aligned}
\operatorname{top}\Omega^{\rm src}_1
  &=
  \left(\frac14V^4G,-\frac14V^3G^2\right),\\
\operatorname{top}\Omega^{\rm src}_2
  &=
  \left(
    \frac{V^3G(-200G+83V)}{2240},
    \frac{V^2G^2(120G-83V)}{2240}
  \right),\\
\operatorname{top}\Omega^{\rm src}_3
  &=
  \left(\frac1{112}V^6G^3,-\frac1{112}V^5G^4\right),\\
\operatorname{top}\Omega^{\rm src}_4
  &=
  \left(
    \frac{115}{24576}V^7G^4,
    -\frac{115}{24576}V^6G^5
  \right),\\
\operatorname{top}\Omega^{\rm src}_5
  &=
  \left(
    \frac7{276480}V^{10}G^4,
    -\frac1{27648}V^9G^5
  \right),\\
\operatorname{top}\Omega^{\rm src}_6
  &=
  \left(
    -\frac1{184320}V^{13}G^5,
    \frac{13}{1474560}V^{12}G^6
  \right),\\
\operatorname{top}\Omega^{\rm src}_7
  &=
  \left(
    -\frac1{1376256}V^{16}G^6,
    \frac1{774144}V^{15}G^7
  \right).
\end{aligned}
\]

In particular, with

\[
W_m=(V^mG^{m-3},-V^{m-1}G^{m-2}),
\]

the first orientation-sensitive shells are

\[
\operatorname{top}\Omega^{\rm src}_3=\frac1{112}W_6,
\qquad
\operatorname{top}\Omega^{\rm src}_4=\frac{115}{24576}W_7.
\]

## Exact coefficient hashes

The hashes below cover complete expanded coefficients, not only their top
shells.

| order | source component SHA-256 |
|---:|---|
| 1 | `034fff9ca41b20a249400675d9f3483dd15edac639dce4a6ad2b4c9d52011e08`, `a4be5928595278764fa8ca7ee21d56ad8a69f40540fd8c3a645a2957dc4072bc` |
| 2 | `42cc9cc1f5e1a0c037008c52386c9bc287a0e14e4c044484278569401eefaeab`, `6c4e3a4d1de3d35ae769bc3750df50587ae328e588d4b4f82a27b15555f3e257` |
| 3 | `6777efb4c0e057db2a975ad40c88ad2ebfab65c156b3f697628cdc3a03fbb1e2`, `f2ff818b6b29f2fdf04ca5b9182b9f3cb11d48bc8f963891ae6ded8c87450e95` |
| 4 | `882aadd08afba69fa8da5a860a0af0890e100c6d2e5c5e4098248441e2d7f34f`, `34a05beccd1a58df3aef20c72eee54708175bf5f87bdd03d1956cbf38a2216e8` |
| 5 | `86b5357dc26d3afc05173ec2df9e757528b2fbd8c447c0c7d4c907e148f7997d`, `61a354bb42996b0efc39e680ff6e219627c9ae515e0766d6f3d582d544bd39d0` |
| 6 | `7045407993b8f634a8a26808025bf7a475437b1b28e18df76b4c04b72507e554`, `b39559ef87ea1a98cbb5ec6ce32b483313443fef4fe78ac77c91dc9470d0b766` |
| 7 | `e7b6059f5c0b974ab782172f21dd965948a4cb407bec120a62fccc7a2a6851d1`, `06dbaf56bcf337455ecf276ad7f2582c5537c77d22231bc34f12c8bc1f80dfbe` |

## Interpretation

The source logarithm grows substantially faster than the instantaneous
minimum-cap sequence in this selected connection.  In particular,
\(\deg\Omega^{\rm src}_7=22\) although \(\deg V_6=14\).  This kills the
inference from the finite velocity profile to a slope-two logarithmic law.

It does not establish an asymptotic lower bound.  Later affine choices can
feed the same top shells, and the exact source-only connection has velocity
degree eleven.  The finite result identifies a nontrivial Magnus mechanism
that a successful minimax normalization must cancel; it does not show that
the mechanism survives every cone-compatible contact.
