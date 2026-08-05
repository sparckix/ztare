# The \(P^2Q+Q^2\) rate-four tradeoff

## Claim boundary

This pencil studies the low-weight order-one target family

\[
M_{\alpha,\beta}
=-\frac1{168}P^2Q+\alpha PQ+\beta Q^2.
\]

The \(P^2Q\) coefficient is the one forced by cancellation of the original
degree-fourteen source face.  The calculation below proves an instantaneous
radial-generator dichotomy and an all-order rate-four theorem at its
exceptional point.  It does not cover higher-weight order-one or later-order
target coefficients.

## Eigenquestion

Can the remaining \(Q^2\) freedom cancel the cost-two slope-four radial
generator without creating another slope-four generator?

## Instantaneous dichotomy

The source Hamiltonian perturbation is

\[
8sM_{\alpha,\beta}(P_s,Q_s).
\]

After the degree-fourteen cancellation, the complete cost-two degree-twelve
face is

\[
\left(-\frac{325}{2688}+\frac{\beta}{2}\right)u^6z^6.
\]

Thus the cost-two logarithmic radial generator

\[
A_\beta
=\left(-\frac{325}{5376}+\frac{\beta}{4}\right)u^6z^6
\]

vanishes only at

\[
\boxed{\beta_*=\frac{325}{1344}}.
\]

At cost three, the degree-sixteen face is independent of both
\(\alpha\) and \(\beta\):

\[
-\frac1{14336}u^8z^8.
\]

Consequently the logarithm always contains

\[
\boxed{B=-\frac1{43008}u^8z^8}
\]

at cost three.  The \(PQ\) and \(Q^2\) moving pullbacks reach only degrees
twelve and fourteen at that cost, respectively, so they cannot change
\(B\).

The source Newton envelope remains

\[
\deg H_q\le4q+4
\]

throughout this low-weight plane.  The target envelope remains
\(\deg K_q\le q+2\).  Hence every connection in the plane has symmetric
logarithmic upper rate at most four.

## Exceptional \(A=0\) connection

Set \(\alpha=0\), \(\beta=\beta_*\).  Then \(A=0\) and \(B\ne0\).
The anisotropic additive grading fixed by \(B\) is

\[
(I,J)=(3a-7q-3,\ 3b-5q-9).
\]

Every instantaneous term has \(I,J\le0\), and \(B\) is the unique
zero-grade term.  The first persistent terminal bidegree is

\[
(I,J)=(-14,-7).
\]

It lies on the single \(B\)-orbit

\[
E_k
=u^{1+7k}z^{4+5k},
\qquad
q_k=2+3k.
\]

The adjoint recurrence is

\[
E_{k+1}
=-\frac{2k-3}{5376}E_k.
\]

Every nonzero coefficient on this orbit has Hamiltonian degree
\(5+12k\), hence source derivation degree

\[
2+12k=4q_k-6.
\]

The exact projected right-Magnus replay is nonzero at every depth
\(0\le k\le19\), through logarithmic order \(59\).

## Three-module \(3\)-adic reduction

Scale every nonzero-grade instantaneous term by a marker \(\lambda\), while
leaving \(B\) fixed.  Since the target bidegree has second coordinate
\(-7\) and every nonzero input grade has second coordinate at most \(-2\),
its logarithmic coefficient is a polynomial

\[
D_k(\lambda)
=\lambda D_k^{(1)}
+\lambda^2D_k^{(2)}
+\lambda^3D_k^{(3)}.
\]

Exact interpolation at \(\lambda=-1,1,2\) gives, for every checked even
\(k\ge2\),

\[
\begin{aligned}
v_3(k!D_k^{(1)})&=-2,\\
v_3(k!D_k^{(2)})&=-3,\\
v_3(k!D_k^{(3)})&\ge-1.
\end{aligned}
\]

Thus the quadratic part is the unique \(3\)-adic minimum and

\[
v_3(k!D_k)=-3.
\]

More precisely,

\[
\boxed{27k!D_k^{(2)}\equiv1\pmod3}
\]

at all checked even depths.

Only two unordered grade pairs can contribute quadratically:

\[
\begin{aligned}
(-10,-5)+(-4,-2)&=(-14,-7),\\
(-8,-4)+(-6,-3)&=(-14,-7).
\end{aligned}
\]

The first pair has strictly larger \(3\)-adic valuation.  The second pair
alone has valuation \(-3\) at every checked even depth.  Its instantaneous
fields are

\[
\begin{array}{c|c|c}
\text{grade}&\text{cost and monomial}&\text{coefficient}\\ \hline
(-8,-4)&(2,u^3z^5)&-1/112\\
(-8,-4)&(5,u^{10}z^{10})&-1/28672\\
(-6,-3)&(3,u^6z^7)&1/5376.
\end{array}
\]

The last field has the same parameter profile as \(B\).  This reduces the
all-order problem to a three-module semidirect calculation with one radial
shift, rather than the complete moving connection.

## Closed dominant-pair response

Normalize the \(B\)-orbits so that the adjoint action is the unilateral
shift.  If

\[
C(x)=\frac{x}{e^x-1}
=\sum_{n\ge0}B_n\frac{x^n}{n!},
\qquad B_1=-\frac12,
\]

then the contribution \(D_k^{\rm dom}\) of the second grade pair has
generating series

\[
D^{\rm dom}(x)=C(x)R(x),
\]

where \(r_0=0\) and

\[
\boxed{
k!r_k
=-\frac{174k^2-k-164}
{2016(k+1)(3k+2)}
}
\qquad(k\ge1).
\]

The useful partial fraction is

\[
k!r_k
=-\frac{29}{1008}
+\frac{43}{336(3k+2)}
+\frac{11}{2016(k+1)}.
\]

Equivalently,

\[
\begin{aligned}
R(x)
={}&-\frac{29}{1008}(e^x-1)\\
&+\frac{43}{336}\int_0^1
t\bigl(e^{xt^3}-1\bigr)\,dt\\
&+\frac{11}{2016}\frac{e^x-1-x}{x}.
\end{aligned}
\]

For positive even \(k\), put

\[
S_k=\sum_{j=1}^k
\binom{k}{j}\frac{B_{k-j}}{3j+2}.
\]

Since \(C(x)(e^x-1)=x\), coefficient extraction gives

\[
\boxed{
27k!D_k^{\rm dom}
=\frac{387}{112}S_k-\frac{33}{224}B_k.
}
\]

Now work in the localization \(\mathbf Z_{(3)}\).  The
von Staudt--Clausen theorem gives

\[
B_n\in3^{-1}\mathbf Z_{(3)}
\]

for every \(n\), and, for positive even \(k\),

\[
3B_k\equiv-1\pmod{3\mathbf Z_{(3)}}.
\]

Every \(3j+2\) is a 3-adic unit, so
\(S_k\in3^{-1}\mathbf Z_{(3)}\).  The first term in the boxed expression is
therefore divisible by three, whereas

\[
-\frac{33}{224}B_k
=-\frac{11}{224}(3B_k)
\equiv1\pmod3.
\]

Consequently

\[
\boxed{
27(2m)!D_{2m}^{\rm dom}\equiv1\pmod3
}
\qquad(m\ge1).
\]

This proves nonvanishing of the dominant quadratic contribution at every
positive even orbit depth.

## Separation from the other marker sectors

There is one linear target module, the two displayed quadratic grade pairs,
and one cubic grade triple,

\[
(-6,-3)+(-4,-2)+(-4,-2)=(-14,-7).
\]

No fourth marker can occur because every nonzero instantaneous grade has
second coordinate at most \(-2\).

The divided-power semidirect recursion has the following 3-local bounds:

\[
\begin{array}{c|c}
\text{sector}&
k!\times\text{normalized coefficient}\\ \hline
\text{linear}&3^{-2}\mathbf Z_{(3)}\\
(-10,-5)+(-4,-2)&3^{-2}\mathbf Z_{(3)}\\
\text{cubic}&3^{-2}\mathbf Z_{(3)}.
\end{array}
\]

Here each application of \(C(\operatorname{ad}_B)\) costs at most one
factor of three.  The first quadratic bracket supplies three factors of
three, exactly offsetting the two input denominators; its simplex
denominators have costs congruent to one or two modulo three.  In the cubic
sector, the two normalized brackets supply six factors, the three inputs
cost five, and the cost-three generator is absorbed into the common
order-three radial flow.  The remaining quadratic conversion uses at most
two Bernoulli operators.  These facts give the displayed bounds.

Multiplication by \(27\) sends all three sectors into
\(3\mathbf Z_{(3)}\).  The dominant-pair congruence therefore survives in
the complete coefficient:

\[
\boxed{
27(2m)!D_{2m}\equiv1\pmod3
}
\qquad(m\ge1).
\]

Thus every even orbit depth is nonzero.  At order \(q=2+6m\), its source
derivation degree is \(4q-6\).  Together with the Newton upper bound, the
exceptional connection has

\[
\boxed{
\text{source logarithmic rate}
=\text{symmetric logarithmic rate}
=4.
}

## Boundary

This classifies only the low-weight order-one exceptional connection.  A
later target coefficient can alter the cost-three logarithm, so the
unrestricted staircase minimax remains a separate question.

The deterministic replay is
[`gauge_p2q_q2_rate_four_dichotomy.py`](gauge_p2q_q2_rate_four_dichotomy.py).
