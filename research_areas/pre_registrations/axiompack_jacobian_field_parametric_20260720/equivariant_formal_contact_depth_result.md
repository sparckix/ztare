# Exact quotient-coordinate contact through order six

**Status:** exact bounded replay; all-order removability subsequently explained
by standard formal etaleness

## Question and method

For the normalized public cubic family `F_s`, remove the forced target motion

\[
\phi_s=\exp(sX_H),\qquad
X_H=-\frac Q2\partial_P+\frac{P^2}{12}\partial_Q,
\]

and solve recursively

\[
F_0\circ\psi_s=\phi_{-s}\circ F_s,
\qquad
\psi_s=(v,t)+\sum_{n\ge2}s^n(a_n,b_n).
\]

At order `n`, the new source coefficient enters through `dF_0(a_n,b_n)`;
all nonlinear contributions from earlier source coefficients are retained.  The
seed quotient Jacobian has determinant `-gamma^2`, so exact cancellation of
the apparent denominator is the discriminator.

## Bounded result

The recursion was evaluated exactly over `Q[v,t]` through order six.

| order | `deg a_n` | `deg b_n` | polynomial | infinitesimal lift ideals | recomposition |
|---:|---:|---:|:---:|:---:|:---:|
| 2 | 11 | 11 | yes | yes | zero |
| 3 | 13 | 13 | yes | yes | zero |
| 4 | 21 | 21 | yes | yes | zero |
| 5 | 23 | 23 | yes | yes | zero |
| 6 | 31 | 31 | yes | yes | zero |

Here the lift conditions are

\[
a_n\in(v,t),\qquad b_n\in(t,v^2).
\]

They are precisely the quotient conditions for lifting each coefficient to a
divergence-free equivariant infinitesimal vector field. They do not certify
that the assembled map preserves volume: `Id+s^2(x,-y,0)` already has a
divergence-free coefficient and determinant `1-s^4`. Nonlinear determinant
terms first contribute at order four. The full source series is
volume-preserving by formal etaleness in the original three coordinates and
the determinant chain rule. Orders two and three also
reproduce the independently derived derivative fields after multiplication by
`2!` and `3!`.

The exact coefficient hashes are:

| order | `a_n` SHA-256 | `b_n` SHA-256 |
|---:|---|---|
| 2 | `d56f643a66936bb556d56fa1a93c3ff2ec1204fcaeb46832bbec7748cb11658f` | `3f9a0621b96ab1ce4142ab6a2ca7cb260a6dee694ce44e4abb5e4817eef15226` |
| 3 | `e204b6a7ae8d61ecc769e55a5e445ed67d94bb9f249bef5e8cf42f163e308090` | `28a2a15cc030933c5d1bf6501647504c57315b55b56d83ad7f55476ab26cdde2` |
| 4 | `3a423c5e8bc563e5d2ac1fba5f6ae2e8faa32d5d42249b3743bb8e0f68d8736a` | `6cd957a0e003e7bc8bad5395701be2e4122a84352d99c03599e2c88d105cb969` |
| 5 | `9bfd713d2a512b21fc663246749955663c2d6822f6215cbcbadcdbabfc4ef371` | `a430984efad96d6bb134a987b250e04839b71544d0c759a52ddf287b33ec8d8d` |
| 6 | `b28f8543f87740a0ba9bd9ef2067fc3f54991538c19c022a3d1caf959f111093` | `355860ee36da4bfa122e29b7d124ba7bcfafc7657552051934c5679a814442df` |

## Falsified prediction and stronger residual

The preregistered law `deg(a_n)=deg(b_n)=2n+7` fails at order four.  The
observed degree sequence

\[
11,13,21,23,31
\]

has alternating increments `+2,+8`.  On the observed range it is described by

\[
\deg(a_n)=\deg(b_n)=
\begin{cases}
5n+1,&n\text{ even},\\
5n-2,&n\text{ odd}.
\end{cases}
\]

This parity law describes one fixed target gauge.  The subsequent
formal-etaleness audit shows that coefficientwise polynomial source
triviality is automatic for every polynomial deformation through a
unit-Jacobian seed.  Higher-order target corrections may change the displayed
source degrees, so the raw parity sequence is not yet an invariant.  The next
high-information task is to minimize degree over the admissible source/target
gauge or prove a gauge-independent lower bound.

## Claim boundary

The calculation directly checks quotient-coordinate contact only through
order six and checks only infinitesimal admissibility of its source
coefficients. The rows are consistency checks for the stronger
three-coordinate construction, not a group-level certificate.
Standard formal etaleness extends removability to every Artin parameter order,
but it does not give a polynomial conjugacy at fixed nonzero parameter or a
new counterexample.  The recent public dimension-3 counterexample and its
generic degree jump are inputs to this analysis.  This finite computation is
a calibration of the standard mechanism.  Possible family-specific content
begins with a sharp filtered degree or non-algebraizability invariant.

## Replay

The exact replay is
`equivariant_formal_contact_depth.py`.  It uses rational symbolic algebra,
checks denominator cancellation and the infinitesimal lift ideals at every order, and
requires coefficientwise zero recomposition through the requested depth.
