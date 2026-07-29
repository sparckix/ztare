# Weierstrass volume correction and the source-degree shell

**Status:** exact target correction; exact source replay through order three;
the canonical correction fails the proposed source slope-two bound

## Eigenquestion

The finite cubic normalization gives a target map

\[
C_s(P,Q)=(P',Q')
\]

whose coefficients obey the shifted target filtration

\[
\deg_f [s^n]P'\le 2n+4,\qquad
\deg_f [s^n]Q'\le 2n+6,
\]

for \(\deg_f P=4,\deg_f Q=6\). Its determinant is not one:

\[
J_s=\det DC_s=1-\frac5{12}s+O(s^2).
\]

Does correcting this determinant preserve a source bound
\(\deg [s^n]S_s\le 2n+1\)?

The kill condition is one exact corrected source coefficient of degree
greater than \(2n+1\).

## Canonical target volume correction

Transport the Jacobian density to the image:

\[
\widehat J_s=J_s\circ C_s^{-1},\qquad
\rho_s=\widehat J_s^{-1}.
\]

Define the triangular liftable map

\[
R_s(Y_1,Y_2)=
\left(\int_0^{Y_1}\rho_s(u,Y_2)\,du,\;Y_2\right)
\]

and put

\[
H_s=R_s\circ C_s.
\]

Then, coefficientwise in \(\mathbb Q[P,Q][[s]]\),

\[
\det DH_s
=
(\rho_s\circ C_s)\det DC_s
=1.
\]

The integral has zero constant term in its first coordinate, while the
second coordinate is unchanged. Hence the quotient target lift ideals are
preserved. Formal inversion, composition, reciprocal, and integration also
preserve the shifted filtration:

\[
\deg_f[s^n](H_s)_1\le2n+4,\qquad
\deg_f[s^n](H_s)_2\le2n+6.
\]

The replay verifies these identities exactly through order three.

## Induced source lift

Let \(F_s\) be the normalized family and \(F_0\) its cubic seed. Define the
compatible source series by

\[
F_0\circ S_s=H_s\circ F_s,\qquad S_0=\operatorname{id}.
\]

At each order the coefficient equation is

\[
DF_0\,S_n=R_n.
\]

Although the quotient determinant is \(-\gamma^2\), exact cancellation
returns polynomial coefficients. Through order three they satisfy the source
lift ideals and

\[
\gamma(S_s)^2\det DS_s=\gamma^2.
\]

Thus the volume-corrected contact exists at these jets. Its ordinary source
degrees are:

| \(n\) | \(\deg V_n\) | \(\deg T_n\) | proposed \(2n+1\) |
|---:|---:|---:|---:|
| 1 | 7 | 7 | 3 |
| 2 | 13 | 13 | 5 |
| 3 | 19 | 19 | 7 |

The first row already kills source slope two for this canonical correction.
Target coefficient bounds cannot be transferred through the ramified
quotient inverse.

## Control: the uncorrected cubic normalization

The same source recursion was run for \(C_s\) before applying \(R_s\). It is
polynomial, remains in the source lift ideals, and has:

| \(n\) | \(\deg V_n\) | \(\deg T_n\) | \(\deg W_n\) |
|---:|---:|---:|---:|
| 1 | 3 | 3 | 4 |
| 2 | 3 | 5 | 6 |
| 3 | 5 | 7 | 8 |

Thus

\[
\max(\deg V_n,\deg T_n)\le2n+1,\qquad
\deg W_n\le2n+2
\]

through the replay depth. Its weighted Jacobian records the expected volume
defect:

\[
\gamma(S_s)^2\det DS_s
=
(J_s\circ F_s)\gamma^2.
\]

This control localizes the \(6n+1\) shell to the chosen volume correction,
not to the finite-cubic factorization.

## Leading mechanism

Put

\[
L=2t-3v,\qquad B=v^4L^2.
\]

Writing the second source coordinate as \(L_s=2T_s-3V_s\), the leading
homogeneous terms are

\[
\begin{array}{c|cc}
n &[s^n]V_s^{\rm top}&[s^n]L_s^{\rm top}\\ \hline
1&-\frac{15}{8}v^5L^2&
 \frac{15}{8}v^4L^3\\
2& \frac{675}{128}v^9L^4&
-\frac{225}{128}v^8L^5\\
3&-\frac{16875}{1024}v^{13}L^6&
 \frac{3375}{1024}v^{12}L^7 .
\end{array}
\]

These are exactly the first three coefficients of

\[
\Phi_s(v,L)=
\left(
v\left(1+\frac{15}{4}sB\right)^{-1/2},
L\left(1+\frac{15}{4}sB\right)^{1/2}
\right).
\]

This is the flow of

\[
X=\frac{15}{8}B\left(-v\partial_v+L\partial_L\right).
\]

It preserves \(vL\), which explains why large source terms can be invisible
to the highest cusp components

\[
P_0^{\rm top}=-\frac34(vL)^2,\qquad
Q_0^{\rm top}=-\frac14(vL)^3.
\]

The first high shell can also be derived without the order table. The
triangular correction begins

\[
R_s(P,Q)=\left(P+\frac5{12}sP,Q\right)+O(s^2).
\]

In \((W,\gamma)\) coordinates,

\[
P_0=\gamma+2W-3W^2,\qquad
Q_0=\gamma W+W^2-2W^3,
\]

and the Jacobian determinant is \(-\gamma\). Lifting the target vector
\((5P/12,0)\) gives

\[
\delta W=-\frac5{12}\frac{WP}{\gamma},\qquad
\delta\gamma=
\frac5{12}\frac{(\gamma+2W-6W^2)P}{\gamma}.
\]

Using

\[
\gamma^{\rm top}=\frac L2,\quad
W^{\rm top}=\frac{vL}{2},\quad
P_0^{\rm top}=-\frac34v^2L^2
\]

produces

\[
\delta\gamma^{\rm top}=\frac{15}{16}v^4L^3,\qquad
\delta v^{\rm top}=-\frac{15}{8}v^5L^2.
\]

This proves the degree-seven counter-shell at order one directly. No
truncation inference is needed for the failure of \(2n+1\).

The displayed flow predicts the sharp law

\[
\deg [s^n]V_s=\deg [s^n]T_s=6n+1
\]

for this gauge. Proving equality for every \(n\) requires a deficit argument
showing that lower pieces and higher primitive corrections cannot reach this
shell. The order-one shell is already decisive against \(2n+1\).

## Claim boundary

The Weierstrass factor proves formal finiteness of the three finite inverse
sheets, and its uncorrected source normalization exhibits slope two through
order three. The triangular density correction, followed by coefficientwise
source lifting, gives a volume-preserving liftable formal contact at every
constructed jet, but it destroys that source bound immediately.

This is gauge-specific. The divergence equation permits other corrections;
at first order one can choose the free Hamiltonian part to cancel the family
jet. Therefore this calculation does not exclude a different optimized
volume-preserving gauge with smaller source growth.

[`gauge_weierstrass_volume_contact.py`](gauge_weierstrass_volume_contact.py)
is the exact replay. It constructs \(C_s^{-1}\), \(\rho_s\), \(R_s\), \(H_s\),
the recursive source lift, the lift-ideal checks, the weighted Jacobian
identity, coefficient hashes, degrees, and leading homogeneous terms.
