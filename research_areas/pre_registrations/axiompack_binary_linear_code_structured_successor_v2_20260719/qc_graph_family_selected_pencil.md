# Selected quasicyclic graph-family attack

Date: 2026-07-19

## Eigenquestion

Does the exact 125-orbit family

\[
C_\phi=\{(gf,gfa_\phi):\deg f<20\}\subseteq\mathbf F_2^{50}
\]

contain a binary `[50,20,14]` code?

Here `R=F_2[x]/(x^25-1)`, `g=1+x^5`, and

\[
a_\phi=\sum_{r=0}^4
  \left(x^{r+5\phi_r}+x^{r+5(\phi_r+2)}\right),
\qquad \phi\in(\mathbb Z/5)^5.
\]

Parameters are quotiented by the 25 cyclic shifts of `a`; the evaluator must
verify, rather than assume, that the canonical domain has cardinality 125.

## Candidate theorem or obstruction

Every member has rank 20 because multiplication by `1+x^5` is injective on
polynomials of degree below 20. Every member has distance at most 14: the
fixed message `f=1+x^10` gives first-block weight 4 and second-block weight
10. Therefore exact minimum-distance replay has a sharp two-way outcome:

- a member with no word below weight 14 is an explicit `[50,20,14]` witness;
- a weight-at-most-13 word kills that member.

## Attack vectors and counterattacks

- **Orbit error:** canonical masks may fail to cover the 3125 tuples exactly.
  Kill on any orbit size other than 25, any multiplicity mismatch, or domain
  cardinality other than 125.
- **Rank error:** the matrix lowering may not preserve the claimed graph
  presentation. Kill any member whose registered GF(2) verifier reports rank
  below 20.
- **Universal-word error:** independently encode `f=1+x^10` for every member
  and kill if its codeword weight is not 14.
- **Verifier insufficiency:** no member receives positive credit unless the
  registered exact verifier examines all `2^20-1` nonzero messages.
- **Duplicate-code inflation:** cyclic shifts are quotiented before target
  evaluation. Further equivalences may reduce information yield but cannot
  create a false positive because each surviving artifact is verified.

## Intended formal surface

A positive artifact enters the existing governed witness and construction-
artifact ratification path. A negative aggregate claims only exhaustion of
this exact byte-frozen 125-member family. It does not decide the ambient open
table cell.

## Recurrence check and tool choice

The capability-amnesia precheck found no direct family enumerator and its
semantic embedder was unavailable. The evaluator will therefore reuse the
existing binary adapter's `verify_binary_linear_code` exact primitive and add
only the family-specific polynomial lowering under this research directory;
no common-kernel primitive is added.
