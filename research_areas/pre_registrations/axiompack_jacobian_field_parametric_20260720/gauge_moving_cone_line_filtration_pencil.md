# All-order line filtration and the \(\Lambda_{11}\) boundary

**Status:** closed structural envelope; automatic \(\Lambda_{11}\)
invariance rejected; controlled continuation of the minimal prefix remains
open

## Closed-form family on the transverse line

Put

\[
u=G+1,\qquad G=t-\frac32V,\qquad \ell=\{V=-1\}.
\]

The normalized family restricts to

\[
\begin{aligned}
P_s|_\ell
={}&
\frac{u}{48(s-6)^2}
\Bigl[
s^4u^2
+(3s^4-12s^3-36s^2)u\\
&\hspace{42mm}
+2s^4-24s^3+120s^2-576s+1728
\Bigr],\\
Q_s|_\ell
={}&
-\frac{s u^2}{16(s-6)^4(s-4)}
\Bigl[
3s^4u^2
+(8s^4-32s^3-96s^2)u\\
&\hspace{42mm}
+4s^4-64s^3+528s^2-2880s+6912
\Bigr].
\end{aligned}
\]

All scalar denominators are units in \(\mathbb Q[[s]]\).  Therefore, with
\(R=\mathbb Q[[s]]\),

\[
\boxed{
\begin{aligned}
P_s|_\ell&\in uR+s^2u^2R+s^4u^3R,\\
Q_s|_\ell&\in su^2R+s^3u^3R+s^5u^4R.
\end{aligned}}
\]

The exact restricted Jacobian has the companion filtration

\[
\boxed{
\begin{aligned}
P_V|_\ell&\in uR+su^2R+s^3u^3R,\\
P_G|_\ell&\in R+s^2uR+s^4u^2R,\\
Q_V|_\ell&\in u^2R+s^2u^3R+s^4u^4R,\\
Q_G|_\ell&\in suR+s^3u^2R+s^5u^3R.
\end{aligned}}
\]

At the seed these specialize to

\[
dF_0|_\ell
=
\begin{pmatrix}
2u&1\\
u^2&0
\end{pmatrix},
\qquad
\det dF_0|_\ell=-u^2.
\]

These are properties of \(F_s\) itself.  They contain no choice of cone
Hamiltonian or carried source field.

## Natural-weight cone target bound

Let the instantaneous coefficient \(K_i\) contain a cone monomial
\(P^aQ^b\), where

\[
b\ge1,\qquad a\le2b,\qquad 2a+3b\le i+6.
\]

At total parameter order \(n\), put \(m=n-i\).

The second Hamiltonian component is proportional to
\(P^{a-1}Q^b\).  Its coefficient can be nonzero only for \(m\ge b\), and
the line filtration gives

\[
\deg_u[s^m](P^{a-1}Q^b)
\le
a-1+2b+\left\lfloor\frac{m-b}{2}\right\rfloor.
\]

Twice the right-hand side is at most

\[
2a+3b+m-2\le n+4.
\]

Hence every earlier natural-weight cone target contributes to the second
residual component within

\[
\boxed{\deg_u\le\left\lfloor\frac n2\right\rfloor+2.}
\]

Similarly, the first Hamiltonian component is proportional to
\(P^aQ^{b-1}\), and

\[
\deg_u[s^m](P^aQ^{b-1})
\le
a+2b-2
+\left\lfloor\frac{m-b+1}{2}\right\rfloor.
\]

The doubled bound is at most \(n+3\), giving

\[
\boxed{
\deg_u\le
\left\lfloor\frac{n+1}{2}\right\rfloor+1
}
\]

in the first residual component.

## Inductively preserved line module

Write a source coefficient on \(\ell\) in \((V,G)\) components as

\[
V_i|_\ell=(A_i(u),B_i(u)).
\]

Consider the line module

\[
\boxed{
\deg A_i\le\left\lfloor\frac i2\right\rfloor,
\qquad
\deg B_i\le
\left\lfloor\frac{i+1}{2}\right\rfloor+1.
}
\]

The four restricted-Jacobian inclusions above show that lower source
coefficients in this module contribute at order \(n\) within

\[
\begin{aligned}
\deg(R_n)_P|_\ell
&\le
\left\lfloor\frac{n+1}{2}\right\rfloor+1,\\
\deg(R_n)_Q|_\ell
&\le
\left\lfloor\frac n2\right\rfloor+2.
\end{aligned}
\]

For example, the \(Q_VA_i\) term has degree at most

\[
\left\lfloor\frac i2\right\rfloor
+2+\left\lfloor\frac{n-i}{2}\right\rfloor
\le
\left\lfloor\frac n2\right\rfloor+2,
\]

and the \(Q_GB_i\) term, which starts one parameter order later, has degree
at most

\[
\left\lfloor\frac{i+1}{2}\right\rfloor+1
+1+\left\lfloor\frac{n-i-1}{2}\right\rfloor
\le
\left\lfloor\frac n2\right\rfloor+2.
\]

The two \(P\)-component estimates follow from the same floor identities.
The family forcing itself obeys these bounds by the two closed-form
filtrations for \(P_s,Q_s\).

At the new order, a cone Hamiltonian has zero second component on \(Q=0\).
The second contact equation is therefore

\[
u^2A_n=(R_n)_Q|_\ell.
\]

Whenever a polynomial contact solution exists, divisibility by \(u^2\)
gives

\[
\deg A_n\le\left\lfloor\frac n2\right\rfloor.
\]

The first equation is

\[
2uA_n+B_n+K_{n,Q}(u,0)=(R_n)_P|_\ell.
\]

Here \(\deg K_{n,Q}(u,0)\le2\), with the sharper degree-one bound at
\(n=0\).  It follows that

\[
\deg B_n\le
\left\lfloor\frac{n+1}{2}\right\rfloor+1.
\]

Thus the displayed line module is preserved at every solvable order.
It proves the all-order structural envelope

\[
\boxed{
\deg (R_n)_Q|_\ell
\le
\left\lfloor\frac n2\right\rfloor+2.
}
\]

The exact finite sequence

\[
2,2,3,3,4,4,5,5
\]

is the sharp prefix of this envelope.  The envelope does not assert that
its top coefficient remains nonzero.

## Separating family geometry from the carried gauge

The family itself admits the exact source-only connection

\[
V_s^{\rm src}=(dF_s)^{-1}\partial_sF_s.
\]

On \(\ell\), its two components are rational functions with scalar
denominators regular at \(s=0\) and fixed \(u\)-degrees

\[
\boxed{
\deg_u(V_s^{\rm src})_V=4,\qquad
\deg_u(V_s^{\rm src})_G=5.
}
\]

Taking \(K_s=0\) gives an all-order natural-weight cone connection and
proves

\[
\Lambda_4=0
\]

for that connection.  Consequently the half-rate prefix is created by the
carried low-cap gauge choices.  It is not forced by \(F_s\).

## Exact freeze test for the selected order-six prefix

Let

\[
K_{\le6}(s)
=
\sum_{i=0}^6\frac{s^i}{i!}K_i
\]

be the selected base point of the complete-affine cone replay, and freeze
all later target coefficients to zero.  The exact all-order source
completion is

\[
V_s^{\rm freeze}
=
V_s^{\rm src}
-(dF_s)^{-1}X_{K_{\le6}(s)}(F_s).
\]

This is a polynomial source field with rational parameter coefficients.
Its restriction to \(\ell\) has scalar denominators and exact degrees

\[
\boxed{
\deg_u(V_s^{\rm freeze})_V=14,\qquad
\deg_u(V_s^{\rm freeze})_G=15.
}
\]

Direct Taylor comparison recovers all selected carried coefficients through
order six.  Their restricted degrees are

\[
\begin{aligned}
\deg(A_0,\ldots,A_6)&=(0,0,1,1,2,2,3),\\
\deg(B_0,\ldots,B_6)&=(1,2,2,3,3,4,4).
\end{aligned}
\]

The nonzero \(u^{14}\) coefficient has a scalar denominator regular at the
seed, so some finite Taylor coefficient contains \(u^{14}\).  At that
order the new second residual contains \(u^{16}\), and

\[
\boxed{\Lambda_{11}\ne0}
\]

for the frozen-target completion.  The all-order line envelope places any
such failure no earlier than order \(24\); the exact first order was not
needed for this discriminator.

## Verdict

\(\Lambda_{11}=0\) is achievable all-order: the source-only connection
already satisfies the stronger \(\Lambda_4=0\).

It is not an automatic invariant of the natural-weight cone language or of
the selected minimal prefix.  Freezing the verified target prefix produces
an exact continuation that eventually leaves \(\ker\Lambda_{11}\).
Maintaining \(\Lambda_{11}=0\) after that prefix would require active future
cone controls whose delayed effects cancel the high line shells.

The line calculation alone neither constructs those controls nor excludes
them.  It replaces the finite pattern by an all-order half-rate envelope
and identifies the precise control obligation.  No additional rank solve is
needed until a proposed recurrence for those delayed cone coefficients is
available.
