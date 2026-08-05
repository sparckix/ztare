# Logarithm-first cone triangular staircase

**Status:** exact corrected replay completed through target order ten;
one-\(C\)-layer sub-two lane negative

## Claim boundary

The velocity-first radial and \(C\)-normal staircases solve exact
instantaneous shells but BCH recreates both radial and second-normal
degree at logarithmic order seven.  This pencil tests the rowwise
logarithmic normal form.  It does not infer an all-order rate from a finite
prefix.

## Eigenquestion

At every target order \(n\), can the current cone-valued connection row be
chosen so that the source right-Magnus coefficient
\(\Omega^{\rm src}_{n+1}\), rather than the instantaneous velocity
coefficient, has all high radial and second-normal shells removed?

## Triangular current-row action

Fix all target rows below \(n\).  The source logarithmic coefficient has
the form

\[
\Omega^{\rm src}_{n+1}
=\frac1{n+1}V_n+B_n(V_0,\ldots,V_{n-1}),
\]

where \(B_n\) is already determined.  Adding a current target monomial
\(\lambda P^aQ^b\) changes only \(V_n\) at this order, so it changes the
logarithmic coefficient by

\[
\frac{8\lambda}{n+1}P_0^aQ_0^b.
\]

The same seed radial diagonal used by the velocity staircase therefore
remains nonzero, scaled by \(1/(n+1)\).  After the radial logarithmic shell
is reduced to the exceptional weights \(2,4\), a current
\(\lambda P^aQ^bC\) changes the second-normal logarithmic diagonal by

\[
-\frac{9\lambda}{2(n+1)}
\left(-\frac34\right)^a
\left(-\frac14\right)^b.
\]

Thus the solve is coefficientwise finite and triangular at each fixed row
if no unrepresented high shell appears.

## First discriminating row

At order seven, the velocity-first connection has logarithmic top shell

\[
\frac{1186929}{2014104780800}u^9z^9
+
\frac{232227}{1611283824640}u^8z^{10}.
\]

The logarithm-first row must use an ordinary weight-nine cone direction to
remove the radial term and \(Q^2C\) to remove the second-normal term.  It
must then recompute the entire shell because the radial correction also
has a \(z^2\) component.

## Discriminating replay

1. At each row, form the exact source Magnus coefficient before choosing
   the current target row.
2. Solve its radial weights in descending order with the canonical cone
   monomials.
3. On the updated logarithmic coefficient, solve every representable
   second-normal radial degree with \(P^aQ^bC\).
4. Verify that the final logarithmic radial support is confined to weights
   \(2,4\), and record the finite \(C\)-multiplier gaps.
5. Carry through target order ten and compare logarithmic source degrees
   against both the velocity-first and radial-only prefixes.
6. Recompute the target left-Magnus logarithm and its degree envelope.
7. Run side-typed forward-`dexp` round trips on the promoted prefix.

## Success and kill conditions

The lane advances if every row has an exact rational finite solve, the
order-seven degree-\(18\) shell disappears completely, target logarithmic
rate stays below the source rate, and no uncancelled first- or
higher-normal shell restores the same top degree.

It is killed by a high radial logarithmic weight outside the cone
semigroup, a \(C\)-multiplier rank failure beyond the declared finite gaps,
lower-normal feedback after the descending solve, target degree growth
matching the source improvement, or a higher-normal logarithmic shell
whose envelope remains two.

If this finite test advances, the successor must schedule powers \(C^k\)
and prove a normal-order coverage inequality compatible with the
source-Magnus bracket, whose density-\(z^2\) bracket lowers total normal
order by two.

## Exact outcome

After excluding the bare \(Q\) column, every instantaneous source row is a
polynomial density-\(z^2\) Hamiltonian field.  The logarithm-first radial
solve is finite through target order ten, and the first \(C\)-normal
coefficient is

\[
\boxed{-\frac{1210823}{64739082240}Q^2C}
\]

at target order six.  It removes the complete order-seven radial and top
second-normal logarithmic shell, reducing that order from degree \(18\) to
\(16\).

The complete logarithmic Hamiltonian degrees at target orders five through
ten are

\[
(16,16,20,20,21,26).
\]

The order-seven and order-ten peaks are exactly the finite multiplier gaps
\(w=7,10\).  More significantly, the quotient with negative cusp-normal
order has top degree

\[
19,\ 21,\ 23
\]

at target orders \(8,9,10\), respectively.  These are \(2n+3\).  Current
target pullbacks start in normal order zero, while current \(C\)-kernel
directions start in normal order two; after the radial and second-normal
diagonals are fixed, neither directly changes this quotient.

Thus the finite solve succeeds algebraically but fails the sub-two success
criterion: the one-\(C\)-layer logarithmic staircase still exhibits slope
two.  This does not exclude a delayed \(C^k\) schedule, because an earlier
higher-normal row can enter later Magnus brackets after the bracket lowers
normal order.

The promoted order-ten prefix passes both forward-`dexp` round trips.  Its
complete source logarithmic degree profile is

\[
(-\infty,8,10,12,14,16,16,20,20,21,26),
\]

while the target profile is

\[
(-\infty,3,3,3,4,4,5,5,6,6,6).
\]
