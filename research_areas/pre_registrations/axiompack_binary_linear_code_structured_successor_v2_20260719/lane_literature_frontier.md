# Independent source/frontier audit: binary linear \([50,20]\)

Date of live audit: 2026-07-19
Lane: PATTERN-008 three-leg verification (positive source, adversarial priority/nonexistence search, neighboring-parameter edge case)

## Verdict

The parameter cell remains open in the current best-known-code record:

\[
13 \le d_2(50,20) \le 14.
\]

The [live Grassl entry for binary \([50,20]\)](https://www.codetables.de/BKLC/BKLC.php?k=20&n=50&q=2) gives lower bound 13, upper bound 14, and an explicit \([50,20,13]_2\) quasi-cyclic construction. Grassl's [reverse-chronological update ledger](https://codetables.de/updates.html) records its adoption on 2025-05-14 and contains a later binary-code update dated 2025-12-11, so the cell is not merely an untouched pre-2025 snapshot.

No primary source located in this bounded audit supplies either:

- a binary linear \([50,20,14]_2\) construction; or
- a global nonexistence/classification result ruling out every \([50,20,14]_2\) code.

That negative search result is evidence about the currently visible literature, not a proof of absence. The scientifically safe disposition is therefore:

- **frontier status of the question:** confirmed in the limited, concrete sense of an unresolved best-known-code table cell;
- **frontier mathematical result from this campaign:** not established by this lane; it requires a verified distance-14 witness or a global nonexistence proof;
- **known recovery boundary:** the \([50,20,13]_2\) quasi-cyclic code and its \([51,20,14]_2\) extension are prior work.

## Positive leg: current database status and upper-bound provenance

For \(d_2(n,k)\), the largest possible minimum distance of a binary linear length-\(n\), dimension-\(k\) code, the live Grassl cell states \(13\le d_2(50,20)\le14\). It attributes the lower bound to the Chubenko--Kurz construction. It attributes the upper-bound chain to shortening and parity arguments ending in the Jaffe nonexistence bounds. Thus the recorded upper bound excludes distance 15 or higher; it does not decide existence at distance 14. The cited original nonexistence program is David Jaffe's [*New results on binary linear codes*](https://arxiv.org/abs/math/9508219).

The two possible closures have different meanings:

| Result | Consequence for the cell |
|---|---|
| Explicit \([50,20,14]_2\), with rank and exact minimum distance independently checked | \(d_2(50,20)=14\); improves the recorded lower bound and reaches the recorded upper bound |
| Proof that no \([50,20,14]_2\) exists | \(d_2(50,20)=13\); turns the Chubenko--Kurz lower-bound construction into an optimal code |
| Exhaustion of one quasi-cyclic, bordered, or other structured family | Excludes that family only; the global cell remains open |

## Known \([50,20,13]_2\) construction

The current author version of Vladimir Chubenko and Sascha Kurz, [*Divisible minimal codes*, arXiv:2312.00885v3](https://arxiv.org/pdf/2312.00885), displays a systematic \(20\times50\) generator matrix for a \([50,20,13]_2\) code and then gives its compact quasi-cyclic form in Remark 5. The institutional record identifies the work as a peer-reviewed article in *Serdica Journal of Computing* 18(2), 97--124; see the [University of Bayreuth publication record](https://eref.uni-bayreuth.de/93969).

Let

\[
R=\mathbb F_2[x]/(x^{10}-1).
\]

Using the paper's compact polynomial sequence together with the displayed systematic matrix, the code has the \(2\times5\) circulant-block generator

\[
G(x)=
\begin{pmatrix}
1&0&a&b&c\\
0&1&d&e&f
\end{pmatrix},
\]

where

\[
\begin{aligned}
a&=x^9+x^8+x^7+x^6+x^5+x^3+x^2+x,\\
b&=x^9+x^3+x^2+x,\\
c&=x^9+x^6+x^3,\\
d&=x^8+x^7+x^6+x+1,\\
e&=x^6+x^5+x^3+x,\\
f&=x^9+x^8+x^3.
\end{aligned}
\]

Each ring entry represents a \(10\times10\) binary circulant block. The first two block columns give the systematic \(I_{20}\), five block columns give length 50, and two block rows give dimension 20. This is the database's “quasicyclic of degree 5, stacked to height 2” representation. The current [Magma handbook entry for `QuasiCyclicCode`](https://magma.maths.usyd.edu.au/magma/handbook/text/1977) confirms that a height-\(h\) polynomial sequence is joined two-dimensionally; here ten polynomials, height two, and length 50 give a two-by-five array of length-10 cyclic/circulant blocks.

Accordingly, rediscovering this matrix, an equivalent generator basis, a coordinate permutation, or another presentation of the same code is recovery of the published lower-bound witness. A distinct \([50,20,13]_2\) code could be a new equivalence-class observation, but it would not improve \(d_2(50,20)\).

## Edge leg: why \([51,20,14]_2\) does not close the target

The [live Grassl \([51,20]\) entry](https://www.codetables.de/BKLC/BKLC.php?k=20&n=51&q=2) constructs \([51,20,14]_2\) by applying `ExtendCode` by one coordinate to the preceding \([50,20,13]_2\) code. Chubenko--Kurz also list \([51,20,14]_2\) among the consequences of their three displayed generators.

For a binary code, this extension appends the overall parity bit:

\[
c\longmapsto \bigl(c,\operatorname{wt}(c)\bmod2\bigr).
\]

A minimum word of weight 13 becomes weight 14; every other nonzero word has original weight at least 13, with odd weights increasing by one and even weights unchanged. The dimension stays 20, so this proves \([51,20,14]_2\).

The reverse operations expose the boundary:

- puncturing the appended parity coordinate recovers the known \([50,20,13]_2\) code;
- shortening at that active parity coordinate selects the even-weight subcode, drops the dimension to 19, and yields the reported \([50,19,14]_2\) consequence;
- an arbitrary puncture of a distance-14 code can reduce its minimum distance to 13.

Thus the length-51 code is a useful positive control for the construction machinery, but it is not a length-50, dimension-20, distance-14 witness. Any campaign rule that promotes “neighbor has distance 14” without replaying the exact \((n,k,d)=(50,20,14)\) identity has crossed the target boundary.

## Adversarial leg: target construction, nonexistence, and classification search

The audit used exact and notation-variant searches for

- `"[50,20,14]"`, `"[50, 20, 14]"`, and versions carrying the binary subscript;
- `d_2(50,20)` and `d(50,20)`;
- the same parameters combined with `binary linear code`, `quasi-cyclic`, `construction`, `nonexistence`, `classification`, and `optimal`;
- arXiv, DOI/publisher results, author repositories, and the Grassl update ledger.

The search recovered the expected \([50,20,13]_2\) source, the \([51,20,14]_2\) parity extension, and Jaffe's older upper-bound provenance. It did not recover a target witness or a target-specific nonexistence/classification theorem. As a cross-check on nearby recent construction literature, the paper that Chubenko--Kurz cite for other circulant improvements, Cong Yu and Shixin Zhu's [2025 group-ring construction paper](https://www.sciencedirect.com/science/article/abs/pii/S0012365X24004801), enumerates its headline new parameters and does not include \([50,20,14]_2\).

This search cannot exclude an unindexed manuscript, a private computation, a result described only through a derived-code chain, or a very recent contribution not yet incorporated by Grassl. A future positive campaign result should therefore trigger, in this order:

1. exact rank and minimum-distance replay from the carried generator artifact;
2. equivalence testing against the Chubenko--Kurz code and its standard transforms;
3. a fresh Grassl-cell and update-ledger replay;
4. a target-parameter search repeated on the result date;
5. direct notification to the database maintainer and a small number of coding-theory experts before a priority claim.

## Claim ledger for the successor campaign

| Claim category | Current disposition |
|---|---|
| Database status | **Confirmed:** \(13\le d_2(50,20)\le14\) on 2026-07-19 |
| Known construction family | **Confirmed prior work:** systematic quasi-cyclic degree/index 5, height 2, \([50,20,13]_2\) |
| Neighboring relation | **Confirmed prior work:** overall-parity extension gives \([51,20,14]_2\); puncturing it returns distance 13 at \((50,20)\) |
| Campaign mathematical discovery | **Open:** this lane certifies no distance-14 witness and no global nonexistence result |
| Novelty if a verified \([50,20,14]_2\) appears | **Strong candidate:** it would close the current database gap, subject to same-day priority and equivalence checks |
| Novelty of a family-only negative | **Separate, narrower question:** potentially publishable only with a precise family definition and its own prior-art audit; it does not determine \(d_2(50,20)\) |

The campaign is therefore aimed at a legitimate frontier cell. It reaches frontier mathematics only when the exact cell is closed, or when it proves a separately stated structured-family theorem that survives an independent novelty audit.
