# Pure contact-zero finite-prefix induction

## Result

For every coefficientwise-polynomial pure contact-zero gauge schedule for
the normalized Jacobian family, including an arbitrary finite
supercritical/polar prefix, the symmetric logarithmic limsup is at least
two.

Together with the existing radial staircase, this determines the minimax
value within the pure contact-zero category:

\[
\boxed{\sigma_{\rm pure\;ct0}=2.}
\]

This result does not include positive-contact corrections coupled to an
arbitrary contact-zero backbone.

## Critical source quotient

In the critical normal-two/normal-three algebra, use the split coordinate

\[
\widehat J=\widehat B+
\frac{3x\widehat A'+5\widehat A}{9},
\qquad
\rho(A)J=2xAJ'-3xA'J-5AJ.
\]

Every target-kernel control has (J=0).  Factoring the complete Witt
logarithm to that target side leaves an abelian source residual (K).  In
row-indexed variables (\widehat A=xa), (\widehat J=xj), it obeys

\[
x(1+2xa)k'=j+(6xa+3x^2a'-1)k.
\]

The coefficients lie in
(\mathbb Q(x,\sqrt{36+12x-3x^2})).  Separating the rational and radical
parts gives two exact first-order rows.  Their Cramer candidate for (k) is
differentially incompatible with the candidate for (k').  Thus (k) is not
rational, hence not polynomial, and has infinite critical support.

The replay
[`gauge_pure_contact_zero_tensor_density_holonomy.py`](gauge_pure_contact_zero_tensor_density_holonomy.py)
checks the algebraic normal-three connection, source/right BCH
factorization, the formal ODE, and the quadratic differential certificate.

## Arbitrary finite polar prefix

At a maximal positive Rees face choose its least monomial

\[
X=s^{-h}x^d,\qquad h>0,\quad d>h.
\]

For a module seed (x^e),

\[
\rho(x^d)^k(x^e)=
\left(\prod_{i=0}^{k-1}
  (2e+(2i-3)d-5)\right)x^{e+kd}.
\]

Only the at-most-four positive exponents satisfying
(2e=(3-2i)d+5) for (0\le i\le3) can terminate.  The remaining maximal-face
defects also occupy finitely many Newton classes.  Infinite support of (K)
therefore supplies a nonresonant seed separated by

\[
\chi=he+d\nu.
\]

The exact semidirect inverse transfer (z/(1-e^{-z})) has nonzero positive
even-depth coefficients.  Since the target module is zero, the resulting
infinite orbit is paid by the source.  Its parameter-order increment is
(d-h), its source-degree increment is (2d), and

\[
\frac{2d}{d-h}>2.
\]

Hence a strict below-two factorization has no positive Rees face.  The
finite induction reaches the already certified critical two-flow terminal.

The replay
[`gauge_pure_contact_zero_polar_tensor_induction.py`](gauge_pure_contact_zero_polar_tensor_induction.py)
binds the critical module, tensor recurrence, Newton separation,
semidirect transfer, cost dictionary, and terminal certificate to the
general-purpose filtered-obstruction compiler.

The migrated compiler input has no Boolean assertion fields.  One
content-bound context selects the universal split model
`split_witt_density_2_neg3_neg5`; exactly three receipts bind the finite
maximal-face decomposition, critical-module infinite support, and critical
terminal exclusion.  The theorem identity is unchanged:

```text
polar_tensor_certificate_sha256 =
2790198e149ffbd07ef7e677c45fff7df2d4e539d02af9ce3081bb67ebdab632
```

The evidence envelope has identity

```text
proof_contract_sha256 =
c3ac1c7ca4b850303eee0da24df11b5a472f43cd3b55eccb968c2bdfeb956023
```

## Verification boundary

The reusable compiler owns the resonance bound, Newton separation,
semidirect transfer, and rate arithmetic.  The Jacobian adapter owns the
exact split quotient, the (J=0) target-kernel identity, the quadratic-field
critical residual, and the source degree dictionary.  Finite recurrence
rows are used only to verify orientation of the all-order algebraic
identities.

The separate moving-backbone induction now covers schedules with positive
contact depth, and the exhaustive global composition is recorded in
[`gauge_unrestricted_tail_minimax_result.md`](gauge_unrestricted_tail_minimax_result.md).
