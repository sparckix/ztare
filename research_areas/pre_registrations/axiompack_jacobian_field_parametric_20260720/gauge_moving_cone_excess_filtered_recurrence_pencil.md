# Excess-filtered Magnus recurrence for the transverse source ray

**Status:** pre-computation recurrence pencil

## Eigenquestion

The complete-affine source logarithm has four successive shells

\[
\operatorname{top}_{4m-6}\Omega^{\rm src}_m=c_mZ_m,
\qquad m=5,6,7,8,
\]

with every displayed \(c_m\ne0\).  Are these coefficients the beginning of
an exact nonvanishing recurrence in the spatial-excess quotient

\[
\epsilon(\text{monomial in }\Omega_m)
=\deg_{\rm src}-4m?
\]

The \(Z_m\) ray has \(\epsilon=-6\).  The leading order-one field
\(W_4/4\) has \(\epsilon=1\), and a Lie bracket obeys

\[
\epsilon([A_i,B_j])
=\epsilon(A_i)+\epsilon(B_j)-1.
\]

Therefore brackets with \(W_4\) preserve the target excess, while a term
already below excess \(-6\) can never return to it.

## Exact filtered algorithm

Implement the right-multiplication Magnus recursion with an exact projection
after every series bracket:

\[
\Pi_n X
=\sum_{\deg\ge4(n+1)-6} [X]_{\deg}
\]

for derivative-series coefficient \(s^n\), and the corresponding
\(\deg\ge4m-6\) projection for \(\Omega_m\).

This projection is exact for the retained band because every logarithmic
factor has excess at most one.  A discarded term has excess below \(-6\);
bracketing it with any retained factor keeps it below \(-6\).

At derivative orders \(n\ge3\), a velocity degree bound

\[
\deg V_n<4(n+1)-6
\]

makes the projected instantaneous input zero.  The observed minimum-cap
connection satisfies this through \(n=7\).  The recurrence computation will
first set the later projected inputs to zero and state that condition
explicitly; it may not silently promote the finite bound to all orders.

## Discriminating tests

1. Carry the complete order-two affine family with parameter \(\lambda\).
2. Transform its first three source velocities to \((V,G)\).
3. Run the exact excess-filtered Magnus recursion through at least order
   forty.
4. Cross-check every retained coefficient through order eight against the
   full symbolic complete-affine replays.
5. Extract the coefficient \(c_m(\lambda)\) of \(Z_m\).
6. Determine whether \(\lambda\) disappears, whether any exact coefficient
   vanishes, and whether the sequence admits:
   - the existing constant-coefficient recurrence primitive;
   - a rational first-order ratio; or
   - a low-order polynomial-coefficient recurrence whose replay is exact on
     a held-out suffix.

## Success and kill conditions

A finite nonzero prefix is not an all-order theorem.  Success requires an
exact recurrence with a proof of nonvanishing, or a closed generating
function with the same consequence.

The proposed excess quotient is killed if its filtered coefficients disagree
with any full replay through order eight.  The finite-prefix escape
hypothesis succeeds if some rational \(\lambda\) annihilates all sufficiently
late \(c_m\), not merely one coefficient.

If no recurrence is found, report the exact sequence and the failed
recurrence classes.  Do not infer nonexistence from a bounded search.

## Transfer boundary

Even an all-order nonzero recurrence here is conditional on later
instantaneous velocities having no excess-\(-6\) input.  To affect the
symmetric tail statistic it must be paired with either:

- an all-order degree bound proving that condition for every compatible
  minimum-cap continuation; or
- a cost transfer showing that any new excess-\(-6\) source input requires a
  target logarithmic shell with the same or larger asymptotic charge.

## Exact finite outcome

The replay
[`gauge_moving_cone_excess_filtered_recurrence.py`](gauge_moving_cone_excess_filtered_recurrence.py)
uses sparse monomial dictionaries and applies the excess cutoff during every
bracket.  An unfiltered symbolic Magnus calculation agrees with the retained
band through order eight, including all four complete-affine shells.

With projected velocity inputs set to zero from derivative order three
onward, the exact coefficients \(c_5,\ldots,c_{41}\) are all nonzero and
independent of the complete order-two affine parameter.  The sequence begins

\[
\begin{aligned}
c_5&=\frac7{276480},&
c_6&=-\frac1{184320},&
c_7&=-\frac1{1376256},&
c_8&=\frac5{14155776},\\
c_9&=\frac{11}{125829120},&
c_{10}&=-\frac{11}{167772160},&
c_{11}&=-\frac{169}{7247757312},&
c_{12}&=\frac{455}{19327352832}.
\end{aligned}
\]

Every checked sign obeys

\[
\operatorname{sgn}(c_m)=(-1)^{\lfloor m/2\rfloor}.
\]

No recurrence was found in any of the preregistered bounded classes:

- constant coefficients of order at most sixteen;
- rational ratios \(c_{m+r}/c_m\) for \(r=1,2,4\) with numerator-plus-
  denominator degree at most twelve;
- polynomial-coefficient recurrences in the tested order/degree window
  (orders at most four and degrees at most five, subject to at least eight
  held-out equations);
- SymPy's product/rational sequence guesser through three iterations; or
- rational generating functions for the raw, sign-normalized, or four
  residue-class subsequences.

This is a finite exact nonvanishing and parameter-independence certificate,
not evidence that no higher-complexity recurrence exists.  The main
all-order residual is unchanged: prove the velocity-filtration condition or
an equivalent symmetric cancellation-cost transfer, then prove
nonvanishing beyond the checked prefix.
