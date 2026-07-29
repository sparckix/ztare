# Compact syndrome-certificate discriminator result

Date: 2026-07-20

Hypothesis: `H-AXIOMPACK-BLC-20260720-02`

Status: `certificate_unavailable`. Three structural upper-certificate formats
were killed, and the proof-producing majority cores are SAT. No covering bound
or extension witness was produced.

## Frozen identity

The coordinate-zero shortening has artifact SHA-256
`1d7fb9205a7daf9d95d65213b248e153dff5e56e624369cabc4f2338a20b715f`.
Its canonical generator is `[I_19 | A]`; the systematic parity-check is
`[A^T | I_31]`. Consequently the prior 31-bit quotient gauge is exactly the
syndrome, and the leader function is

\[
\ell(s)=\min_{u\in\mathbf F_2^{19}}
  (\operatorname{wt}(u)+\operatorname{wt}(s+uA)).
\]

This identity was checked directly from all 19 frozen rows.

## Exact kill 1: dual-spectrum certificate

Complete enumeration of the `2^19` primal words gives support

`0, 14, 16, 18, ..., 40`.

The integer MacWilliams transform has nonzero dual multiplicity at every
weight `6,7,...,44` and at `50`. Its nonzero support count is therefore `40`.
The Delsarte external-distance bound supplies only `rho(C) <= 40`, so it
cannot prove the required `rho(C) <= 13`.

All coefficients, total masses `2^19` and `2^31`, and the complete measured
resource curve are frozen in `coset_syndrome_resource_probe_receipt.json`
(receipt SHA-256
`c291624fdcc48e4064688b37b2941f75017e4cfd9862185b81b8dd077fb1257a`).

## Exact kill 2: localized QC/block direct sums

The syndrome was split into the three ten-bit QC output blocks plus the parity
bit. For each block `S`, all `2^19` messages were enumerated and the exact
least weight of an error whose syndrome is supported only in `S` was computed.
The four localized radii are `10,10,10,1`, summing to `31`.

Grouping the first two blocks gives exact localized radii `11+11=22` for a
`20+11` split. Natural `15+16` and `16+15` splits also give `11+11=22`.
Among 400 deterministic random 15-coordinate splits, the best sum was `21`
(`10+11`). Thus this lift format is far above 13; its defect is the cost of
cancelling the complementary syndrome coordinates, not a solver timeout.

## Exact kill 3: normalized QC trellis

In the published `2 x 5` presentation over
`F_2[x]/(x^10-1)`, the shortened message is `(u,v)` with `u_0=0`, hence a
19-bit separator. The exact trellis connectivity profile is

\[
s(P,Q)=\operatorname{rank}(G_P)+\operatorname{rank}(G_Q)-19.
\]

The QC block and time-major orders both peak at state dimension `19`; a
coordinate-order heuristic found profiles peaking at `17`, but it removed the
QC block semantics. More decisively, normalizing the systematic-prefix metric
translates by its unique codeword and leaves the residual
`q in R^3 x F_2`, which is the same rank-31 syndrome. With no certified
further orbit quotient, a normalized-metric receipt must distinguish the full
residual carrier. The proposed trellis is therefore a re-encoding of the
killed table rather than a compact certificate.

## Majority-cover result and hostile witness

A weight-14 coset leader `x` must satisfy

\[
|\operatorname{supp}(x)\cap\operatorname{supp}(c)|
\leq \operatorname{wt}(c)/2
\]

for every codeword `c`; otherwise `x+c` is lighter. It is enough to rule out
leaders of weight exactly 14, because any 14-subset of a heavier leader also
satisfies every majority inequality.

The 1,155 weight-14 codewords alone do **not** form such a majority cover. An
exact Boolean model is

`x = 0x070000044c71e`, with `wt(x)=14`.

It meets every weight-14 codeword in at most seven coordinates. Complete
row-span replay nevertheless gives

- exact coset minimum: `10`;
- reducing message: `0x0a716`;
- reducing codeword: `0x07a801250a716`, of weight `18`;
- intersection with `x`: `11`;
- reduced word: `0x00a8012146008`, of weight `10`;
- examined source words: `524,288`.

So minimum-word incidence is insufficient; weight-18 constraints contain new
covering information. A certificate using all necessary majority classes is
still a valid compact target, but no checkable UNSAT/covering proof has been
produced. Solver termination without that proof carries no upper-bound credit.

## Proof-producing shared-BDD discriminator

The bounded core selector ran for `300,011 ms` and completed 855 exact
counterexample-replay iterations before Z3 returned `canceled`. Its 2,010
named inequalities have weight histogram

`14:1155, 16:328, 18:290, 20:193, 22:39, 24:5`.

The proposal receipt is
`04ab1b0750c6e79441b84a99254b1a93a85eb96f53bcfe6f7f10bb8f5e699d66`.
It is selection evidence only, not an UNSAT core.

To distinguish an encoding failure from a nonterminal core, every threshold
was compiled into a reduced ordered BDD. Nodes were hash-consed globally by
their original coordinate and low/high children; each asserted positive root
uses two path-implication clauses per decision node. The encoder self-test
replayed 768 small assignments. CaDiCaL 2.1.2 then returned SAT on all three
frozen instances, and every 50-bit support was checked against the named
inequalities and all `2^19` source words:

| instance | constraints | variables | clauses | CNF bytes | result | exact coset minimum |
|---|---:|---:|---:|---:|---|---:|
| all weight 14 | 1,155 | 58,747 | 112,481 | 1,989,035 | SAT | 10 |
| smallest mixed prefix | 1,156 | 58,831 | 112,643 | 1,991,969 | SAT | 10 |
| accumulated mixed trace | 2,010 | 126,965 | 244,596 | 4,486,852 | SAT | 8 |

The first two encodings fit the frozen `100,000`-variable and
`250,000`-clause caps, but SAT rules out an LRAT false proof. The accumulated
trace exceeds the variable cap and is also SAT, so changing only the counter
encoding does not make the selected inequalities terminal. Its replayed SAT
support is `0x040700005478d`; the exact reducer is the weight-18 codeword
`0x0d0740885072d`, leaving weight 8.

No LRAT trace was generated: LRAT applies only to a false CNF, while these
three exact CNFs have replayed models. The deterministic receipt is
`majority_cover_shared_bdd_receipt.json`, SHA-256 identity
`dc0a255ed9bc29b66a5b2fdbbda80419f8bf4db18e17c16cce6722b1d3c6b618`.
The CNF byte hashes are frozen in that receipt.

## Full-table resource result

The byte-table route was benchmarked only through 26 syndrome bits. The
31-bit model requires `2,147,483,648` bytes and
`66,571,993,088` directional relaxations. Even if execution is feasible, a
table hash is not an independently replayable mathematical certificate and
the object is full-quotient enumeration. The native probe now refuses more
than 26 bits; the receipt records `execution_authorized=false` for the full
instance.

## Claim boundary and disposition

No covering-radius bound and no distance-14 coset witness was obtained. The
results concern one frozen shortening only and say nothing about the other 50
shortenings or ambient `[50,20,14]` existence.

The shared BDD showed that the minimum-word base can fit the proof envelope,
but it also supplied a model; the accumulated mixed trace remains a model and
crosses the variable cap. The normalized QC chart supplied no smaller
certified orbit carrier than the rank-31 syndrome. Under the preregistered
formats and caps, the typed result is therefore `certificate_unavailable`.
Another incremental center loop, a full `2^31` table, or an LRAT run on a SAT
core is excluded. This disposition does not infer that the extension cone is
closed.
