# Cokernel recurrence for the moving cone source cost

**Status:** preregistered after the order-four cone pass and before dual
functional extraction

## Eigenquestion

The exact moving-contact solve with cone-valued target Hamiltonians has
minimum source-degree profile

\[
(5,5,7,9)
\]

through instantaneous orders \(0,1,2,3\).  At orders two and three, the
system at one degree below the minimum fails by one rank:

\[
57<58,\qquad 91<92.
\]

Do these two codimension-one failures arise from one shifted
associated-graded functional that persists at every order \(j\ge2\), forcing

\[
\deg V_j\ge2j+3?
\]

## Discriminating calculation

For the cone-constrained system at instantaneous order \(j=2,3\) and source
cap \(2j+2\):

1. compute the exact left kernel of the coefficient matrix;
2. retain the functional that evaluates nontrivially on the residual;
3. normalize it by its first nonzero coefficient;
4. express its support in shifted source monomial coordinates;
5. compare the two normalized functionals after removing the order shift.

If they match, derive a candidate formula from the exact source/target
associated-graded map.  If they differ, identify the first structural
coordinate responsible rather than fitting a scalar sequence.

## Counterattacks

1. **Row-order artifact:** compare functionals by coefficient labels, not
   raw vector positions.

2. **Pivot-dependent source term:** the particular degree-\(2j+3\) solution
   can vary along null directions.  The lower-cap cokernel evaluation is the
   invariant object.

3. **Finite recurrence fitting:** two functionals can suggest a shift but
   cannot prove persistence.  Promotion requires an exact symbolic family
   or an associated-graded module theorem.

4. **Target-window truncation:** verify that enlarging the complete target
   component window cannot change the lower-cap cokernel.

## Success and kill conditions

- **Finite structural success:** the two lower-cap failures are the same
  shifted functional with nonzero residual evaluations.
- **Recurrence success:** an all-order formula proves nonzero evaluation and
  the lower bound \(\deg V_j\ge2j+3\).
- **Kill:** the functionals are structurally different, an enlarged target
  window removes them, or a carried lower-order affine direction makes the
  lower cap consistent.

## Campaign boundary

An all-order instantaneous lower bound still needs the standard
instantaneous-to-logarithmic filtration step before it determines the source
contribution to \(\sigma_{\rm ct}\).

## Exact disposition

The complete-affine dual extraction through order six is recorded in
[`gauge_moving_sections_extended_result.md`](gauge_moving_sections_extended_result.md).
The shifted top support persists through \(j=5\), but the proposed
all-order cokernel recurrence is killed at \(j=6\).  At the preceding cap
thirteen the primitive cone functional has only

\[
(0,8,9)\mapsto25,\qquad(0,9,8)\mapsto2,
\]

and evaluates to \(45/8\).  The old two-slot functional has changed
category exactly where the weight-twelve cone target acquires its second
independent symbol.  The cone then passes at cap fourteen rather than the
extrapolated cap fifteen.
