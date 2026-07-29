# Cyclic-transversal obstruction for the selected graph family

Date: 2026-07-19

## Eigenquestion

Can the 125-member exact failure be compressed into a proof that excludes
every phase tuple before enumerating its `2^20-1` nonzero messages?

## Candidate obstruction

Let

\[
R=\mathbf F_2[x]/(x^{25}-1),\qquad g=1+x^5,
\]

and let

\[
a=\sum_{r=0}^4\left(x^{r+5\phi_r}+x^{r+5(\phi_r+2)}\right)
\]

for arbitrary phases \(\phi_r\in\mathbf Z/5\). Then the graph code

\[
C_a=\{(gf,gfa):\deg f<20\}
\]

has minimum distance at most 10. Consequently no member of this entire
phase family is a binary `[50,20,14]` code.

This is a family obstruction only. It makes no assertion about the ambient
open `[50,20,14]` table cell.

## Proof skeleton

1. Put \(b=ga\). In each residue class modulo 5, the support of \(a\) is at
   heights \(\phi_r\) and \(\phi_r+2\); multiplication by \(1+x^5\) adds
   heights \(\phi_r+1\) and \(\phi_r+3\). Thus \(b\) contains four of the
   five positions in that residue class. There is a transversal
   \(M\subset\mathbf Z/25\), with one point in every residue class modulo 5,
   such that

   \[
   b=\mathbf 1_{\mathbf Z/25}+\mathbf 1_M
   \]

   over \(\mathbf F_2\).

2. Fix a nonzero residue increment \(\delta\in\mathbf Z/5\). Write the
   transversal as \(M=\{m_r:r\in\mathbf Z/5,\ m_r\equiv r\pmod 5\}\) and
   consider the five differences

   \[
   D_\delta=\{m_{r+\delta}-m_r:r\in\mathbf Z/5\}\subset\mathbf Z/25.
   \]

   Their sum is zero because the two indexed sums telescope. If all five
   differences were distinct, they would be the entire coset
   \(\delta+5\mathbf Z/25\), whose sum is

   \[
   \sum_{j=0}^4(\delta+5j)=5\delta+50\equiv5\delta\not\equiv0\pmod{25}.
   \]

   This is impossible. Hence some nonmultiple-of-5 difference \(s\) occurs
   at least twice, so \(|M\cap(M+s)|\ge2\). Replacing \(s\) by \(-s\) if
   necessary gives an integer representative \(1\le s\le12\), inside the
   tested message range.

3. Take the binomial message \(f=1+x^s\). Since \(5\nmid s\), the four
   positions in \(g(1+x^s)\) are distinct, so its weight is 4. The all-ones
   terms in \(b+x^sb\) cancel, leaving the symmetric difference of \(M\)
   and \(M+s\). Therefore

   \[
   \operatorname{wt}(b(1+x^s))
   =|M\mathbin\triangle(M+s)|
   =10-2|M\cap(M+s)|\le6.
   \]

   The resulting codeword has weight at most \(4+6=10\).

## Stress tests and kill conditions

- The exact 125-member oracle must agree that every member has distance at
  most 10. Its observed histogram is `d=6:10`, `d=8:50`, `d=10:65`.
- The independently generated 19-shift binomial spectrum must leave no
  residual member and must attain the same minimum histogram.
- Kill the proof if `ga` is not the complement of a residue transversal, if
  the fixed-\(\delta\) difference sum is not zero in `ZMod 25`, or if the
  repeated difference does not yield the stated intersection multiplicity.
- No global code-table conclusion may be inferred from this construction
  family.

## Recurrence and intended formal surface

The exact enumeration came first and exposed binomial killing messages. The
compression from 125 exhaustive message replays to a cyclic-transversal
difference argument is new within this campaign. Its combinatorial core is a
known relative-difference-set classification result: an odd-prime cyclic group
of order `p^2` has no `(p,p,p,1)` relative difference set. In particular the
`p=5`, `ZMod 25` obstruction is recovery, not a novelty candidate. The
code-specific consequence `d(C_a) <= 10` is the useful translation retained by
the campaign; no novelty claim is attached to it.

The intended formal statement quantifies over a five-point subset of
`ZMod 25` meeting every fiber of reduction modulo 5 once, proves the existence
of a nonzero nonmultiple-of-5 shift with intersection cardinality at least 2,
and then derives the weight-10 graph-code witness. LeanMill should ratify that
statement after the campaign has authored or admitted the corresponding
formal task; the finite oracle remains an independent stress receipt.
