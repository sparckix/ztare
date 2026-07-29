# Coset-extension pencil for binary `[50,20,14]`

Date: 2026-07-20

Status: preregistered mathematical orientation; no coset search had run when
this file was written.

## Eigenquestion

Fix one byte-frozen shortening

\[
C\leq \mathbf F_2^{50},\qquad \dim C=19,\qquad d(C)=14.
\]

Does there exist `v` outside `C` such that

\[
\min_{c\in C}\operatorname{wt}(v+c)\geq 14?
\]

If so, `D = span(C,v)` is the disjoint union `C ∪ (v+C)`, hence

\[
\dim D=20,\qquad
d(D)=\min\left(d(C),\min_{c\in C}\operatorname{wt}(v+c)\right)=14.
\]

This is the exact missing-generator problem. It changes the search carrier
from 1,000 raw matrix bits to one point of the 31-dimensional quotient
`F_2^50 / C`.

## Canonical quotient gauge

Row-reduce a basis of `C` while preserving coordinate order. Let the 19 pivot
coordinates be `P`. Every coset has exactly one representative whose bits on
`P` are zero: subtract the unique codeword having the same pivot pattern.
The remaining 31 free coordinates therefore parameterize all cosets without
duplication. The zero representative is the code itself and cannot satisfy
the distance threshold because its coset contains zero.

The gauge must be replayed by checking:

1. the reduced rows span the original shortening;
2. their pivot restriction is the identity;
3. every generated representative is zero on all pivot coordinates; and
4. two different 31-bit assignments have different syndromes modulo `C`.

## Exact CEGIS skeleton

Maintain a Boolean solver over the 31 quotient bits. For each codeword `c`
returned by the referee, add the cardinality constraint

\[
\operatorname{wt}(v\oplus c)\geq 14.
\]

For every solver candidate `v`, enumerate all `2^19` codewords of `C` in Gray
order and compute the exact least weight in `v+C`.

- If the least weight is at least 14, append `v` to the shortening basis and
  invoke the registered binary-code verifier over all `2^20-1` nonzero
  messages.
- If the least weight is at most 13, store the exact offending message,
  codeword, coset word, and weight, then add that codeword's constraint.
- If the outer formula becomes UNSAT, preserve its canonical Boolean form and
  require an independently checkable proof before asserting that this
  shortening has covering radius at most 13.

The loop is finite but the worst-case iteration count is too large to use as
a termination argument. The pilot stop rule is a fixed iteration/time cap;
nontermination is a chart-efficiency result, not an extension-cone null.

## Attack vectors and counterattacks

- **Gauge loss.** A mistaken pivot convention can omit the successful coset.
  Counterattack: construct and replay the exact complement map and syndrome
  uniqueness check.
- **Inner sampling.** A candidate can look distant under a partial word list.
  Counterattack: the decisive inner query always scans all `2^19` words.
- **Constraint mismatch.** A stored center may not be the codeword whose ball
  rejected the candidate. Counterattack: replay `v xor c`, its weight, and
  membership of `c` in the frozen row span before adding the constraint.
- **Solver-only null.** A process exit saying UNSAT is weaker than the desired
  finite-family statement. Counterattack: retain the canonical instance and
  demand a second solver or checkable proof; otherwise report `unavailable`.
- **Equivalent-shortening inflation.** Running 51 coordinate shortenings may
  repeat one cone. Counterattack: transfer results only through a certified
  coordinate automorphism; otherwise keep all identities distinct.
- **Raw-search recurrence.** Solving directly for another 20-row matrix loses
  the quotient compression. Counterattack: every candidate is a canonical
  coset representative of a fixed reviewed subcode.

## Exact kill and success conditions

Success is one explicit `v` followed by independent rank-20 and complete
minimum-distance replay, then the normal LeanMill construction-artifact path.

A scientific negative for one shortening requires certificate-backed UNSAT of
the complete quotient formula. A capped run that has neither a witness nor a
certificate records only the observed coset-distance trajectory and the next
algorithmic discriminator.

## Recurrence and tool check

The semantic primitive precheck returned generic symbolic existential and
counterexample helpers, but no binary-code coset or covering-radius engine.
The existing `binary_linear_code.v1` adapter remains the final referee; the
new work, if useful beyond this pilot, belongs in a domain adapter or
construction-family operation rather than in the common campaign kernel.

## Intended formal surface

No Lean file precedes an exact candidate or finite certificate. A positive
artifact reuses the existing concrete generator-matrix certificate. A
negative formal artifact, if obtained, should state only that every canonical
coset representative for the named finite `C` lies within distance 13 of a
codeword, with the finite coverage certificate as data.
