# Target-lift repair of the radial cone staircase

## Claim boundary

The first radial staircase enforced the minimum cone support
\(b\ge1,\ a\le2b\) but omitted the independent target-lift exclusion of
\(Q,P,P^2\).  Since the cone already excludes \(P,P^2\), the missed
monomial is exactly \(Q\).  This pencil tests whether removing it repairs
polynomial source admissibility without changing the rate-two envelope.

## Eigenquestion

After forbidding the bare target Hamiltonian \(Q\), do the remaining
cone-and-lift-compatible monomials still solve every unbounded radial
weight, leaving only a bounded polynomial source remainder?

## Category countercheck

At the seed,

\[
\operatorname{ord}_z(P_0^aQ_0^b)=a+2b.
\]

For a source Hamiltonian \(H\) with density \(z^2\),

\[
X_H=(H_z/z^2,-H_u/z^2)
\]

is polynomial only when every nonconstant monomial of \(H\) has
\(z\)-exponent at least three.  Among cone monomials, \(Q\) is the unique
failure: its seed order is two.  This agrees with the previously declared
target-lift support predicate, which excludes \(Q,P,P^2\).

In the first staircase row, the selected bare-\(Q\) coefficient creates

\[
-\frac{43}{1680}r^2
\]

while canceling a bounded \(r^3\) term.  Thus the apparent weight-two
remainder is an artifact of the missed lift condition.

## Repaired radial semigroup

The radial weights represented by monomials satisfying both the cone and
target-lift conditions should be

\[
\boxed{\{w:w\ge5\}}.
\]

Descending radial elimination should therefore leave only weights
\(0,1,2,3,4\).  Polynomial source admissibility requires the actual
nonconstant remainder to start at weight three; a surviving \(r^2\) term
kills the repair.

## Discriminating replay

1. Exclude \(Q\) in the canonical radial monomial selector.
2. Recompute the first five exact rows from scratch.
3. At every row, assert that every nonconstant source Hamiltonian monomial
   has \(z\)-exponent at least three.
4. Record the repaired row dimensions, bounded radial remainder, source
   Hamiltonian degrees, and target support.
5. Run source/right and target/left forward-`dexp` round trips with the
   constant-density target bracket.
6. Recheck the moving affine-chart tangency and coefficientwise Rees
   estimate.

## Success and kill conditions

The repair advances if every row is rational and finite, the only radial
remainder is supported in weights three and four, every source row is
polynomial, the source/logarithmic degree profile remains
\(2q+4\) at Hamiltonian level, and the target logarithmic rate remains at
most one.

It is killed by an unrepresented radial weight at least five, any
nonconstant source monomial with \(z\)-exponent below three, failure of
either side-typed round trip, or a target/source degree envelope above the
previous rate-two bound.

An advancing finite replay still owes the corrected all-order induction and
an updated arithmetic certificate; the certificate for the uncorrected
weight-three semigroup cannot be cited.

## Exact outcome

The repair advances.  The first five row dimensions are

\[
\boxed{(3,4,5,6,7)}.
\]

Every coefficient multiplying \(Q\) disappears and every other target
coefficient agrees with the earlier replay.  The first two repaired rows
are

\[
\begin{aligned}
K_1={}&-\frac1{168}P^2Q
+\frac{325}{1344}Q^2
-\frac{43}{3360}PQ,\\
K_2={}&-\frac1{5376}PQ^2
+\frac{11}{2016}P^2Q
-\frac{8347}{107520}Q^2
+\frac{883}{161280}PQ.
\end{aligned}
\]

Their radial remainders are supported at \(r^3,r^4\), every source
Hamiltonian passes the \(z^3\)-divisibility gate, and the source degree
profile remains

\[
(8,10,12,14,16).
\]

The source right-Magnus and target left-Magnus round trips pass.  Their
logarithmic Hamiltonian degree profiles are respectively

\[
(-\infty,8,10,12,14,16)
\quad\text{and}\quad
(-\infty,3,3,3,4,4).
\]

Thus the target-lift correction changes the bounded radial remainder but
does not change the rate-two upper envelope.
