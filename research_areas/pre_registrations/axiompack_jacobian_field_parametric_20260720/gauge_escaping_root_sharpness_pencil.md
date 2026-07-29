# Escaping-root shell sharpness

**Status:** proof pencil after finite coefficient orientation; before the
all-order derivation

## Eigenquestion

The finite-branch construction uses the unique reciprocal escaping root

\[
z=a(s)+b(s)z^2+c(s)Pz^3+d(s)Qz^4,
\]

where

\[
a=\frac{s}{2(s+2)},\quad
b=\frac{s+4}{2(s+2)},\quad
c=\frac{12}{(s-6)(s+2)},\quad
d=-\frac{s-4}{2(s+2)}.
\]

The existing construction proves only

\[
\deg_f[s^n]z\le 2n-2,\qquad
\deg_f(P,Q)=(4,6).
\]

Is this bound sharp at every order, and is the sharp shell intrinsic to any
formal contact that removes the escaping fourth sheet?

## Top-shell mechanism

Put

\[
x=s^2P,\qquad y=s^3Q,\qquad z=sZ(x,y)+
\text{higher Rees valuation}.
\]

The lowest-Rees part of the fixed-point equation is

\[
\boxed{Z=\frac14-xZ^3+yZ^4.}
\]

Thus the coefficient of \(P^iQ^j\) in \([s^n]z\) on the sharp shell
\(4i+6j=2n-2\) is \([x^iy^j]Z\).

For odd \(n=2k+1\), the monomial \(P^k\) is governed by

\[
Z_0=\frac14-xZ_0^3.
\]

For even \(n=2k\), the monomial \(P^{k-2}Q\) is governed by

\[
\left.\partial_yZ\right|_{y=0}
=\frac{Z_0^4}{1+3xZ_0^2}.
\]

The finite orientation through order thirteen shows nonzero coefficients
in both families.  The all-order task is to derive their exact
Fuss--Catalan forms and prove nonvanishing without extrapolating that
prefix.

## Candidate theorem

For every \(n\ge3\),

\[
\boxed{\deg_f[s^n]z=2n-2.}
\]

More precisely, the \(P^{(n-1)/2}\) coefficient is nonzero for odd \(n\),
and the \(P^{(n-4)/2}Q\) coefficient is nonzero for even \(n\ge4\).

## Symmetric-contact bridge

Sharpness of the canonical root factorization is not yet a lower bound for
all contacts.  The required bridge must show that the escaping rank-one
factor is invariant under the pair of coefficientwise-polynomial formal
automorphisms in

\[
H_s\circ F_s=F_0\circ\Psi_s.
\]

The target and source maps may redistribute the shell.  The desired
consequence is only

\[
\max\{\deg_f[s^n](H_s-\mathrm{id}),
       \deg[s^n](\Psi_s-\mathrm{id})\}
\ge 2n-O(1)
\]

along an infinite subsequence.  Do not infer this from the canonical
factorization alone.

## Kill conditions

The shell theorem is killed if either displayed coefficient family
vanishes at some order or if higher-Rees terms can contribute at the same
filtration.  The minimax bridge is killed by a contact whose two sides both
have asymptotic slope below two, or by an exact conjugacy showing that the
reciprocal-root shell is coordinate-dependent.
