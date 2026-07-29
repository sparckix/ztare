# Complete fixed-bound transition through order eight

**Status:** generic transition regression passed; degree-nine order-eight
compatibility locus proved empty

## Generic transition regression

The order-independent transition in
`gauge_fixed_bound_family_extension.py` was replayed from the complete
degree-seven family through order four to order five.  It agrees exactly with
the existing specialized implementation:

- identical compatibility obstructions;
- identical compatibility substitution;
- identical compatible lower-parameter coordinates;
- image rank \(80\) and nullity \(3\);
- complete parameter dimension \(8\);
- parameter-polynomial replay through order five.

Compatibility coverage is certified only in either of two cases:

- a nonzero constant proves the locus empty;
- an affine-linear system is replaced by its exact RREF graph.

Graphs merely exposed by a nonlinear symbolic solver are typed as partial
coverage and cannot be consumed as a complete family.

## Complete degree-nine family through order seven

The existing complete degree-nine family through order six has dimension
\(18\).  Applying the generic transition at order seven gives:

- residual component degrees \((22,24)\);
- residual parameter degree \(2\) with \(34\) parameter monomials;
- next-order image rank \(129\), nullity \(6\);
- quotient dimension \(4\).

The four compatibility equations are affine-linear.  Exact RREF has rank
four, so its graph is equivalent to the whole compatibility locus.  Four
lower coordinates are eliminated, leaving \(14\) compatible lower
parameters.  Adding the six-dimensional homogeneous order-seven fiber gives
the complete \(20\)-parameter degree-nine family through order seven.  Both
components of its universal \(Y_7\) have degree nine.

## Global order-eight obstruction at bound nine

Applying the same transition to that complete \(20\)-parameter family gives:

- residual component degrees \((22,24)\);
- residual parameter degree \(2\) with \(49\) parameter monomials;
- next-order image rank \(129\), nullity \(6\);
- quotient dimension \(10\).

One exact cokernel pairing is the literal constant

\[
1.
\]

Therefore the compatibility locus is empty before any branch solver is
invoked.  No compatible degree-nine lower prefix through order seven extends
to order eight at source bound nine.

Consequently, in the fixed first-order slice,

\[
c_8>9.
\]

The existing carried prefix with \(\deg Y_8=17\) supplies

\[
10\le c_8\le17.
\]

The exact value is obtained by applying the same complete-family transition
at bounds \(10,11,\ldots\) until the first compatible order-eight locus.
This result does not infer the global obstruction from the previously failed
frozen witness, and it does not establish an all-order degree law.
