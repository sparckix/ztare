# Pure contact-zero finite-prefix induction

## Conditional result and unconditional upper bound

For every coefficientwise-polynomial pure contact-zero gauge schedule for
the normalized Jacobian family, the maximal-positive-Rees-face induction
forces a rate strictly above two until it reaches the zero-positive-face
terminal.  The local all-degree theorem excludes the exact intrinsic critical
holonomy from the normalized two-polynomial-flow category, and a second
kernel theorem excludes its regular Rees lift.  That is the finite
target-critical route.  The v105 rate-gap theorem shows that strict ordinary
target rate alone does not force finite critical support.  The remaining
premise must therefore split every actual strict zero-positive-face schedule
into a finite branch constructing the regular Rees carrier or an infinite
branch constructing the exact semidirect exponential transfer from the finite
polynomial source Lie pair `(A,J)` and excluding its generally nonpolynomial
group-module orbit.

The existing radial staircase establishes the unconditional upper bound

\[
\sigma_{\rm pure\;ct0}\le 2.
\]

Conditional on exclusion of both target-critical routes, the lower induction
and the staircase give \(\sigma_{\rm pure\;ct0}=2\).  Positive-contact
corrections coupled to an arbitrary contact-zero backbone are handled by a
separate induction.

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

Hence a strict below-two factorization has no positive Rees face.  The finite
induction reaches the zero-positive-face critical terminal.  If its target
critical support is finite, formal inversion identifies the resulting
two-flow terminal with the intrinsic July holonomy, and the regular Rees
kernel excludes it after the exact schedule carrier is built.  If the target
critical support is infinite, the finite-Rees specialization is unavailable;
the required carrier instead binds the schedule's finite polynomial Lie pair
`(A,J)` to the exact transfer
`(1-exp(-rho(A)))/rho(A) J`.  The prior finite-polynomial `L` reduction is not
valid in general: the v123 kernel counterexample has finite `A,J` but a
nonterminating group-module coordinate.  The existing density-clock endpoint
arithmetic therefore applies only if a separate polynomiality theorem is
proved; a transfer-aware all-degree obstruction remains the active route.

The replay
[`gauge_pure_contact_zero_polar_tensor_induction.py`](gauge_pure_contact_zero_polar_tensor_induction.py)
binds the critical module, tensor recurrence, Newton separation,
semidirect transfer, and cost dictionary.  It now stops at the critical
terminal and reports no compiled pure lower bound until the realization
certificate exists.

The general compiler input has no Boolean assertion fields.  Its terminal
lifecycle now requires two separate content-bearing arrows: exact zero-face
realization and exact factorization-category exclusion.  The polar compiler
then consumes the resulting certificate object.  Empty terminal conclusions,
arbitrary digests, finite-window evidence, cross-germ grafts, and the older
Puiseux factorization receipt are rejected.  The replay therefore exposes
only the positive-face descent certificate until the missing realization
arrow is constructed.  The current positive-face identity is:

```text
positive_face_descent_certificate_sha256 =
0961e9e3a10bd71e4869495098239ae12686ab3a51510fdc7a78d78a2b6a0a8c
```

The historical polar tensor and proof-contract hashes are not carried as
current lower-bound evidence.

## Verification boundary

The reusable compiler owns the resonance bound, Newton separation,
semidirect transfer, and rate arithmetic.  The Jacobian adapter owns the
exact split quotient, the (J=0) target-kernel identity, the quadratic-field
critical residual, and the source degree dictionary.  Finite recurrence
rows are used only to verify orientation of the all-order algebraic
identities.

The separate moving-backbone induction covers schedules with positive
contact depth.  The current global composition, whose contact-zero lower
branch retains the schedule-to-Rees specialization dependency, is recorded in
[`gauge_unrestricted_tail_minimax_result.md`](gauge_unrestricted_tail_minimax_result.md).
