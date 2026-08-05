# Covariant high-transverse quotient and the rate-two boundary

**Status:** successor pencil after rejection of the named (Q^2C) terminal

## Eigenquestion

Let the complete cost-two contact-zero resonance remove the difference-two
source support of the leading-amplitude (Q^2C) response.  The remaining
cost-two class is nonzero in the quotient by every polynomial contact-zero
pullback.  Does its covariant transport force infinitely many source-log
coefficients of limiting derivation rate at least two, or can an arbitrary
coefficientwise-polynomial contact-zero connection cancel it below that
rate?

The target lower-bound input is the exact radial staircase

\[
\sigma_{\rm ct}\le 2.
\]

A matching contact-zero obstruction must therefore be invariant under every
finite polynomial row and must charge any cancellation through either a
source pivot or target degree.  A bounded continuation does not suffice.

## Governing category

Use density-(z^2) source Hamiltonians.  For monomials,

\[
[u^az^b,u^cz^d]
=(bc-ad)u^{a+c-1}z^{b+d-3}.
\]

The rate-two total excess

\[
E(a,b;q)=a+b-2q-4
\]

is additive under brackets.  The normal-cost degree

\[
N(a,b;q)=q+(b-a)-2
\]

is also additive.  These two filtrations separate asymptotic payment from
the finite normal strips through which a cancellation can enter.

The complete contact-zero source image is the pullback of

\[
\mathbb Q+(P^3,PQ,Q^2)\subset\mathbb Q[P,Q].
\]

Every monomial in such a pullback has nonnegative normal order (b-a).
This property is closed under its source Lie bracket because the pullback is
a Lie map.

## Exact exceptional cost-two representative

The unique weights-five-through-twelve schedule that cancels every
difference-two monomial gives a cost-two Hamiltonian (A_*) with 35 terms.
Its unique northeast term is

\[
\operatorname{NE}(A_*)=\frac{27}{1280}u^{12}z^{12}.
\]

The cost-three seed is the exact (L_3) already replayed in the (Q^2C)
terminal calculation.  A direct sparse-bracket orientation pass gives

\[
\begin{array}{c|c|c}
k&\operatorname{NE}(\operatorname{ad}_{A_*}^kL_3)&\text{coefficient}\\ \hline
0&u^9z^{11}&9/256\\
1&u^{20}z^{20}&-729/40960\\
2&u^{27}z^{27}&1318761/13107200\\
3&u^{38}z^{35}&-114614109/4194304000.
\end{array}
\]

For (k\ge3), the proposed terminal pivot is

\[
T_k=u^{11k+5}z^{9k+8}.
\]

Only the northeast (u^{12}z^{12}) term can reach the next northeast
coordinate.  Therefore its coefficient (c_k) should satisfy

\[
c_{k+1}=\frac{81(2k-3)}{320}c_k,
\qquad k\ge3.
\]

This multiplier is positive and nonzero.  At cost (n=2k+3), (T_k) has
Hamiltonian degree (20k+13) and density-(z^2) derivation degree

\[
20k+10=10n-20.
\]

The right-forward-`dexp` coefficient of the word with one cost-three seed
and (k) cost-two letters is

\[
\frac{(-1)^k}{(k+1)!},
\]

so the pure terminal word is nonzero at every (k\ge3).

## Attack vectors and counterattacks

### A. Covariant terminal functional

Define a shifted functional \(\ell_k\) that reads the coefficient of
(T_k) after quotienting every coordinate strictly northeast of it.
Compile the complete current contact-zero image at each cost and test

\[
\ell_k(\text{current image})=0,
\qquad
\ell_{k+1}[A_*,H]
=\frac{81(2k-3)}{320}\ell_k(H).
\]

The orientation replay already finds that the (k=3) terminal functional
annihilates all canonical contact-zero weights 5 through 24.  This finite
fact is only a base window.  The proof must use source support, triangular
pivots, and the complete discriminant-depth decomposition.

**Counterattack:** a higher-weight contact-zero row can hit (T_k) through a
lower monomial while carrying a larger coordinate.  The functional alone
must not discard that larger coordinate.

### B. Surplus-or-terminal compiler

For a finite set of current columns, split the codomain into a terminal
projection and a strictly-higher projection.  Restrict controls to the
kernel of the higher projection, then ask whether their terminal projection
reaches the distinguished terminal.  This computes

\[
\text{terminal image of }\ker(\text{higher image}).
\]

If the terminal is outside that image, every cancellation either fails or
accepts a higher pivot.  This is a general filtered-obstruction lifecycle,
distinct from ambient cokernel and forcing reachability.  It belongs beside
the existing exact compiler if alien controls confirm its identity and
boundary behavior.

**Counterattack:** two higher pivots can cancel each other before reaching
the terminal.  The compiler must take the complete kernel of the full higher
projection, rather than test columns one at a time.

### C. Normal-cost exceptional graph

Since (N) is additive and the northeast cost-two actor has (N=0), the
terminal ray stays at (N=4).  A one-column top-symbol calculation leaves
only the seed strips

\[
(q,b-a)=(3,3),\qquad(5,1)
\]

as possible same-ray contact entries; the formal seed coordinates are
((5,8)) and ((16,17)).  Exact base calculations find zero terminal
pairing for canonical contact-zero symbols in both strips.

**Counterattack:** lower monomials of a high-weight symbol can enter the same
strip while its leading source pivot lies above the terminal.  The graph
must record the leading pivot as a charged exit rather than treating its
terminal coordinate as an independent control.

### D. Arbitrary earlier-row words

Contact-zero letters form a Lie subalgebra, so any word containing no
(Q^2C) defect remains in nonnegative normal order.  A word containing the
defect is organized by the additive pair ((E,N)).  At the first attempted
terminal cancellation, select the largest source pivot among the finitely
many coefficients used at that order.  The proposed triangular alternative
is:

1. its higher projection is nonzero, giving a same-order source payment; or
2. it lies in the higher kernel, where the covariant terminal functional
   excludes cancellation.

**Counterattack:** an infinite exceptional path may move between equal
leading pivots.  The exact transition graph must show either no return or a
strictly increasing charged filtration.

## Candidate result

For the exceptional cost-two resonance, the complete contact-zero current
algebra admits a covariant surplus-or-terminal certificate.  The terminal
word (T_k) is nonzero for infinitely many (k), or the first cancellation
creates a source pivot of at least the same asymptotic charge.  Any target
column whose leading source weight grows fast enough to enter the terminal
strip has target ordinary degree rate at least two.

Together with the nonresonant difference-two recurrence, this would exclude
every coefficientwise-polynomial contact-zero continuation of the Q2C lane.

## Kill conditions

- A complete higher-kernel contains an exact terminal-canceling schedule.
- The proposed \(\ell_k\) fails relation descent for a contact-zero symbol.
- A held-out weight or cost creates a same-grade control with no higher
  source or target payment.
- The exceptional graph has an infinite zero-payment path.
- The forward-`dexp` terminal receives another defect word with the same
  pivot and an independently adjustable coefficient.
- Any all-weight conclusion depends on stabilization at a finite cap.

## Intended formal surface

1. A substrate-neutral exact `surplus reachability` certificate computing
   terminal reachability inside the kernel of a complete higher projection.
2. Alien examples for direct cancellation, columnwise-false but
   kernelwise-true cancellation, malformed projections, and terminal
   survival with a forced surplus.
3. A Jacobian adapter producing exact finite base/held-out certificates and
   the symbolic monomial transition formula.
4. A small arithmetic module only after the pencil isolates the finite
   inequalities and nonzero multipliers required by the all-weight proof.

## Stop rule

This tick stops only after the exceptional cost-two representative is
handled for arbitrary contact-zero rows by an all-weight triangular or
covariant argument, or after an exact below-rate-two cancellation schedule
passes direct sparse-bracket and side-typed Magnus replay.  A finite
nonvanishing prefix does not meet the criterion.

## Category audit: the first coupled counterattack

Expanding the controls from the contact-zero associated grade to every
monomial in the lift algebra produces an exact cancellation.  The compiler
decomposition is

\[
L_2=8\left(
-\frac12P^2Q^2+2P^3Q^2+2Q^3-9PQ^3+\frac{27}{2}Q^4
\right)(P_0,Q_0).
\]

The target polynomial in parentheses is (Q^2C/2).  Hence the additional
direction has positive (C)-adic valuation and vanishes in the contact-zero
associated grade.  The high-transverse quotient remains valid for the frozen
contact-zero question, while the unrestricted campaign gains the exact
counterattack

\[
K_2^{\rm repair}=-\frac12Q^2C.
\]

After this repair, (L_3) survives the complete lift-compatible monomial
span.  Its annihilator reads only (z)-exponents seven through nine, making
the weight-22 computation all-weight complete.  Thus the coupled successor
starts from the cost-three quotient rather than the cost-two transverse ray.
