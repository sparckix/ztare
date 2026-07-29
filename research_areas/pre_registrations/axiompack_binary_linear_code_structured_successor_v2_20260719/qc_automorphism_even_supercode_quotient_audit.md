# QC automorphism and even-supercode quotient audit

Date: 2026-07-20

Status: deterministic pencil/replay audit of the frozen `[51,20,14]` source;
no construction witness, cone exhaustion, or priority claim.

## Exact coordinate action

Label the five length-10 QC blocks by `(b,t)`, with `0 <= b < 5` and
`t in Z/10`, and label the appended parity coordinate by `infinity`.  The
permutation

\[
\sigma(b,t)=(b,t+1),\qquad \sigma(\infty)=\infty
\]

is an automorphism of the frozen code `L`: on the displayed generator it
maps row `t` to row `t+1` and row `10+t` to row `10+(t+1)`, with indices
modulo 10.  Thus `<sigma>` is a certified cyclic subgroup of order 10.

Complete enumeration of the frozen row span gives the following
coordinate colors

\[
N(j)=(\#\{c:\operatorname{wt}(c)=14,\ c_j=1\},
      \#\{c:\operatorname{wt}(c)=16,\ c_j=1\}):
\]

| coordinates | `N(j)` |
|---|---:|
| `0..9` | `(440,2062)` |
| `10..19` | `(432,2100)` |
| `20..29` | `(436,2100)` |
| `30..39` | `(442,2080)` |
| `40..49` | `(440,2066)` |
| `50` | `(430,2112)` |

Every coordinate automorphism preserves this color, so it cannot mix these
six sets.  Since `sigma` is transitive on each ten-set, these are the exact
coordinate orbits.

As a stronger check, color the complete coordinate graph by the vertex color
above and by

\[
M(i,j)=\#\{c:\operatorname{wt}(c)=14,\ c_i=c_j=1\}.
\]

Exact color-preserving backtracking returns ten graph automorphisms, precisely
`sigma^r` for `0 <= r < 10`.  A code automorphism must preserve this graph,
while all ten returned permutations already preserve the generator row
space.  Hence the full coordinate automorphism group of the frozen `L` is

\[
\operatorname{Aut}_{\rm coord}(L)=\langle\sigma\rangle\cong C_{10}.
\]

Replay anchors: the frozen source digest is
`213c591c8870333c54944c011f15e035ee1baa56ab451897ace39bc671588d4e`;
the upper-triangular `M` list in lexicographic pair order has SHA-256
`1da9aac369f719f03b34d00f851040162816c6ac5f68c4968bd1130b3b8d1425`;
the sorted ten permutation lists have SHA-256
`265f849d764ede015d68118871afcf384a3961a96768fec9657530dabbcfd5ea`.
The deterministic replay is
`qc_automorphism_even_supercode_oracle.py`; its byte-frozen output is
`qc_automorphism_even_supercode_oracle_receipt.json`, receipt SHA-256
`bad07411eab06f96227d49a56c399231184a9123c449093899d63b815a3046eb`.

## What this does to the 51 punctures

Punctures whose deleted coordinates lie in one orbit are equivalent through
the indicated power of `sigma`.  Punctures from different orbits are
inequivalent.  Indeed, because `L` is even, it is recovered canonically from
any puncture `C_j=pi_j(L)` by reinserting the parity of the remaining word at
coordinate `j`.  Therefore any coordinate equivalence `C_i -> C_j` would
lift to a coordinate automorphism of `L` carrying `i` to `j`, which the orbit
colors forbid.  The 51 punctured base codes consequently form exactly six
coordinate-equivalence classes.

This six-class statement concerns the base codes.  Their coset-extension
**decision problems** have a stronger common carrier.  Let

\[
W=\{x\in\mathbf F_2^{51}:\operatorname{wt}(x)\equiv0\pmod2\}.
\]

For every coordinate `j`, insert the parity bit at `j` to obtain a linear
map `iota_j : F_2^50 -> W`.  It induces a bijection

\[
\Lambda_j:\mathbf F_2^{50}/C_j\;\longrightarrow\;W/L,
\qquad [v]\longmapsto[\iota_j(v)].
\]

For every punctured difference `y`,

\[
\operatorname{wt}(\iota_j(y))
=\operatorname{wt}(y)+(\operatorname{wt}(y)\bmod2).
\]

Pointwise, the right side is at least 14 exactly when `wt(y)>=13`.  Hence

\[
d(v,C_j)\geq13
\quad\Longleftrightarrow\quad
d(\iota_j(v),L)\geq14.
\]

The 51 searches should therefore share one byte-frozen 30-dimensional
even-supercode quotient `W/L`; running one search per puncture repeats the
same finite decision problem.  A witness in this common quotient lowers to
the parity-kernel `[50,20,14]` construction at every selected coordinate.

## Maximal coordinate-symmetry quotient of the common carrier

Let `R=F_2[x]/(x^10-1)` and use the systematic QC presentation

\[
(u,v)\longmapsto(u,v,ua+vd,ub+ve,uc+vf,\epsilon(v)),
\]

where `epsilon(f)=f(1)`.  Subtracting the two systematic blocks gives every
class in `W/L` a unique residual

\[
(0,0,s_2,s_3,s_4,\epsilon(s_2+s_3+s_4)).
\]

Thus `W/L` is `R^3`, and `sigma` acts by simultaneous multiplication by
`x`.  Reading the three coefficient bits at each cyclic position as one
symbol identifies the exact coordinate-symmetry quotient with length-10
necklaces over an eight-symbol alphabet.

Burnside gives

\[
|R^3/C_{10}|=
\frac{8^{10}+4\cdot8+4\cdot8^2+8^5}{10}
=107{,}377{,}488.
\]

The orbit counts by exact size are `8` of size 1, `28` of size 2, `6,552`
of size 5, and `107,370,900` of size 10.  Since the colored-graph audit proves
that `C_10` is the full coordinate automorphism group, no larger quotient by
coordinate symmetries is available for this frozen source.

## Kill conditions and claim boundary

- Kill the six-class result if the row-space replay for `sigma`, either
  complete incidence color, or the parity-extension lifting argument fails.
- Kill the common-carrier quotient if `Lambda_j` is not bijective or the
  displayed pointwise weight equivalence fails.  Both are algebraic
  identities here.
- Kill the necklace chart as an exhaustive campaign representation: it
  leaves over 107 million representatives and almost every orbit has size
  10.  Its exact deduplication rule still leaves exhaustive use far beyond
  the current campaign boundary.
- A CRT decomposition of `R` does not split Hamming weight under the inverse
  transform.  Without a separate metric-preservation theorem it may not be
  promoted as further distance compression.
- Failure to find a necklace representative proves nothing about the common
  quotient.  A negative result still requires a checked covering/refutation
  certificate; no such certificate was produced in this audit.
