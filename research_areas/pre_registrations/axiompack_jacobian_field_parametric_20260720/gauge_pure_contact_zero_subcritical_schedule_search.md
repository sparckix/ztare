# Pure contact-zero subcritical schedule search

## Outcome

The higher-normal construction lane does not currently produce a schedule
with both logarithmic rates below two.  It does produce the exact quotient
that such a schedule must annihilate.

Let

\[
L=2-3r,
\qquad
C=4P^3-P^2-18PQ+27Q^2+4Q.
\]

At the base moving chart,

\[
P_0=-\frac34r^2+r+\frac12z,
\qquad
Q_0=-\frac14r^3+\frac14r^2+\frac14rz,
\]

and the cusp polynomial has the exact pullback

\[
\boxed{
C(P_0,Q_0)=-\frac{z^2}{16}\left(L^2-8z\right).
}
\]

For a source Hamiltonian coefficient

\[
H(r,z)=\sum_{j\ge0}z^jN_j(r),
\]

define its two-layer compatibility quotient by

\[
\boxed{
\Delta(H)=L^2N_3-LN_2'+2N_2.
}
\]

Every target correction with zero radial restriction is a multiple of
\(C\), and every such correction lies in the kernel of \(\Delta\).  Thus
normal order two and normal order three are not independent free rows.

The remaining all-index problem has been reduced to one scalar sequence:
prove that the leading coefficient of \(\Delta\) for the recursively
radial-normalized background is nonzero at infinitely many rows, uniformly
after an arbitrary finite rational prefix, or solve the recurrence that
makes it eventually zero.

## Exact kernel calculation

Write a radial-preserving correction as \(C(P,Q)G(P,Q)\).  If

\[
G(P_0,Q_0)=h(r)+zn(r)+O(z^2),
\]

the tangency identity gives

\[
h'=Ln.
\]

Using the displayed pullback of \(C\), the next two normal coefficients are

\[
N_2=-\frac{L^2}{16}h,
\qquad
N_3=\frac12h-\frac{L}{16}h'.
\]

Since \(L'=-3\), direct differentiation gives

\[
L^2N_3-LN_2'+2N_2=0.
\]

This holds for every polynomial \(G\), with no weight or parameter cutoff.
The cusp parametrization has principal kernel \((C)\), so it is the complete
same-row kernel after the radial coefficient has been fixed.

## Radial-to-normal diagonal

The quotient response of a nonzero radial leader is also explicit.  Let a
target cone polynomial have radial leader

\[
[r^w]K(P_0,Q_0)=c.
\]

Then

\[
\boxed{
[r^{w-4}]\Delta\bigl(K(P_0,Q_0)\bigr)
=\frac{w(w-2)(w-3)}9c.
}
\]

Indeed, on the highest radial face,

\[
P_0=-\frac34r^2
\left(1-\frac23\frac{z}{r^2}\right)+\text{lower},
\qquad
Q_0=-\frac14r^3
\left(1-\frac{z}{r^2}\right)+\text{lower}.
\]

Extracting the \(z^2\) and \(z^3\) binomial coefficients gives the boxed
factor.  It is nonzero at every permitted cone weight \(w\ge5\).  The
companion replay checks the formula across 79 monomial representatives; the
formula itself is the displayed binomial identity, not an inference from
that finite check.

This diagonal explains why cancelling the radial weight \(w=n+6\) creates a
compatibility class in radial degree \(n+2\).  A cancellation by \(C G\) can
move its representative between normal orders two and three, but cannot
change the class.

## Why the apparent higher-normal freedom does not decide the rate

Cone-compatible multiples of \(C\) become plentiful.  A multiplier
\(P^pQ^q\) keeps every term of \(CP^pQ^q\) in the cone when

\[
p+3\le2q.
\]

Every multiplier weight \(m\ge11\) has such a representative:

\[
p=
\begin{cases}
0,&m\equiv0\pmod3,\\
2,&m\equiv1\pmod3,\\
1,&m\equiv2\pmod3,
\end{cases}
\qquad
q=\frac{m-2p}{3}.
\]

Consequently the normal-two staircase can cancel every sufficiently high
radial monomial.  These corrections exclude bare \(Q\), remain
coefficientwise polynomial, and their pullbacks satisfy the source
divisibility requirement.  But their normal-three coefficients are already
fixed by \(\Delta=0\).  The freedom therefore does not erase the
compatibility quotient.

If a logarithmic row \(q=n+1\) has

\[
\deg_r\Delta=n+2,
\]

then every representative has either \(\deg_rN_2\ge n+2\) or
\(\deg_rN_3\ge n\).  The corresponding source vector-field degree is at
least

\[
2(n+2)-4=2n.
\]

Nonvanishing on an unbounded set of rows would therefore imply source
logarithmic limsup at least two.

## Category correction and finite diagnostics

The earlier logarithm-first radial staircase was reconstructed through target
row six and passed the typed right-`dexp` round trip, but it chooses from the
larger cone.  From row four onward its representatives differ from the unique
pure contact-zero parity section by positive-contact terms.  Its old quotient
leaders

| target row \(n\) | log order \(q\) | \(\deg_r\Delta\) | leading coefficient |
|---:|---:|---:|---:|
| 1 | 2 | 3 | \(-1/16\) |
| 2 | 3 | 4 | \(-1/64\) |
| 3 | 4 | 5 | \(-3/1024\) |
| 4 | 5 | 6 | \(-137/229376\) |
| 5 | 6 | 7 | \(-5359/44040192\) |
| 6 | 7 | 8 | \(-920333/43159388160\) |

are therefore ambient mixed-contact diagnostics, not the pure sequence.
They must not be used in the \(m=0\) induction.

The exact parity-owned recurrence instead begins

| target row \(n\) | log order \(q\) | pure-parity leader |
|---:|---:|---:|
| 1 | 2 | \(-1/16\) |
| 2 | 3 | \(-1/64\) |
| 3 | 4 | \(-3/1024\) |
| 4 | 5 | \(-155/258048\) |
| 5 | 6 | \(-4237/37158912\) |
| 6 | 7 | \(-43177/2427715584\) |

It remains nonzero through every exactly computed row, but those values are
diagnostics rather than an all-index argument.  The deterministic replay now
reports the ambient and pure-parity sequences under distinct keys and asserts
that they diverge.

## Finite supercritical-prefix audit

The degenerate prefix route cannot be dismissed by saying that a
noncommuting pair creates an infinite logarithmic cascade.  The existing
exact \(Q^3C\) prefix replay gives a counterexample to that argument on its
leading ray:

- one finite target prefix produces source logarithm coefficients at costs
  two and three;
- the cost-three coefficient does not commute with the cost-two coefficient;
- forward `dexp` has nonzero terminal velocity coefficients at every odd
  cost \(3,5,7,\ldots\); and
- the logarithm has no higher terminal coefficient.

The all-order forward-`dexp` statement is exact for the displayed finite
logarithm.  The normalized staircase matches it in the full projected
window through held-out cost nine.  Hence the adjoint velocity cascade is
not itself a logarithmic tail payment.

This particular prefix is a multiple of \(C\), so its radial restriction is
zero and it cannot absorb the radial cusp deformation measured above.  It
does show that an arbitrary finite prefix must be handled in the quotient
sequence rather than charged merely because a second coefficient appears.

## Sharp missing lemma

For a finite rational supercritical prefix \(B\), let \(H_{n,B}\) be the
source logarithmic coefficient after all radial weights above four have been
cancelled at row \(n\), and put

\[
\delta_n(B)=[r^{n+2}]\Delta(H_{n,B}).
\]

The remaining construction-versus-obstruction discriminator is:

\[
\boxed{
\text{For every finite }B,
\quad \delta_n(B)\ne0\text{ for infinitely many }n,
}
\]

or else an explicit finite \(B\) and exact recurrence with
\(\delta_n(B)=0\) eventually.

Equivalently, one needs the generating function of the normalized
compatibility leaders and a proof that no finite rational prefix makes it a
polynomial.  This statement includes the finite-prefix loophole and is
strictly sharper than either radial triangularity or wordwise adjoint
nonvanishing.

No below-rate-two schedule is promoted from the finite rows.  Such a
candidate would still need coefficientwise polynomiality, cone support,
source divisibility, and typed source and target `dexp` replay at arbitrary
depth.

## Replay

The deterministic companion is
[`gauge_pure_contact_zero_subcritical_schedule_search.py`](gauge_pure_contact_zero_subcritical_schedule_search.py).
It checks the exact cusp pullback, the all-polynomial kernel compatibility,
the radial diagonal, the multiplier conductor, both explicitly typed finite
diagnostic sequences, the source typed round trip, and the finite-terminal
prefix audit.
