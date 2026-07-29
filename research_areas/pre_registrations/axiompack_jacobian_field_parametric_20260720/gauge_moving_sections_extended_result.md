# Complete affine replay of the cone and parity moving sections

## Scope and convention

This result extends the preregistered cone and parity moving-contact tests
through instantaneous order six.  Coefficients are derivative-normalized:

\[
\partial_sF_s=X_{K_s}(F_s)+dF_sV_s,\qquad
K_s=\sum_{j\ge0}\frac{s^j}{j!}K_j,\quad
V_s=\sum_{j\ge0}\frac{s^j}{j!}V_j.
\]

At order \(j\), the target window is the complete \(C\)-normal lift
restricted to

\[
\operatorname{wt}K_j\le j+6.
\]

The replay
[`gauge_moving_section_affine_extension.py`](gauge_moving_section_affine_extension.py)
does not freeze an arbitrary earlier solution.  It carries a base point and
the complete homogeneous prefix kernel.  At the next order, every lower
kernel direction is inserted as an additional exact residual column.  The
nullspace of that joint system becomes the complete affine family carried
to the following order.

## Exact source-cap profiles

The complete affine carry gives

\[
\boxed{
\begin{aligned}
\text{cone:}&\quad(5,5,7,9,11,13,14),\\
\text{parity:}&\quad(5,5,7,9,11,13,15).
\end{aligned}}
\]

Here the entries are source velocity caps for instantaneous orders
\(j=0,\ldots,6\).  They are not degrees of a Magnus logarithm.

### Cone

The cone target dimensions are

\[
(2,3,4,5,6,7,9).
\]

| \(j\) | lower affine dim. in | previous cap | previous matrix | rank/aug. | selected cap | selected matrix | rank | affine dim. out |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 4 | \(107\times29\) | \(29/30\) | 5 | \(134\times41\) | 41 | 0 |
| 1 | 0 | 4 | \(118\times30\) | \(30/31\) | 5 | \(134\times42\) | 42 | 0 |
| 2 | 0 | 6 | \(177\times57\) | \(57/58\) | 7 | \(197\times73\) | 72 | 1 |
| 3 | 1 | 8 | \(248\times93\) | \(91/92\) | 9 | \(272\times113\) | 110 | 3 |
| 4 | 3 | 10 | \(331\times138\) | \(133/134\) | 11 | \(359\times162\) | 156 | 6 |
| 5 | 6 | 12 | \(426\times192\) | \(183/184\) | 13 | \(458\times220\) | 210 | 10 |
| 6 | 10 | 13 | \(500\times226\) | \(212/213\) | 14 | \(533\times256\) | 242 | 14 |

### Parity

The parity target dimensions are

\[
(2,3,4,5,6,7,8).
\]

| \(j\) | lower affine dim. in | previous cap | previous matrix | rank/aug. | selected cap | selected matrix | rank | affine dim. out |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 4 | \(107\times29\) | \(29/30\) | 5 | \(134\times41\) | 41 | 0 |
| 1 | 0 | 4 | \(118\times30\) | \(30/31\) | 5 | \(134\times42\) | 42 | 0 |
| 2 | 0 | 6 | \(177\times57\) | \(57/58\) | 7 | \(197\times73\) | 72 | 1 |
| 3 | 1 | 8 | \(248\times93\) | \(91/92\) | 9 | \(272\times113\) | 110 | 3 |
| 4 | 3 | 10 | \(331\times138\) | \(133/134\) | 11 | \(359\times162\) | 156 | 6 |
| 5 | 6 | 12 | \(426\times192\) | \(183/184\) | 13 | \(458\times220\) | 210 | 10 |
| 6 | 10 | 14 | \(533\times255\) | \(241/242\) | 15 | \(569\times287\) | 272 | 15 |

Because source spaces are nested by cap, inconsistency at the immediately
preceding cap rules out every smaller cap.

## Primitive lower-cap cokernels

The primitive duals below use semantic rows
`(equation slot, v exponent, t exponent)`.  Slots zero and one are the two
contact equations.  The hashes cover the complete normalized integer
support, not only its top entries.

### Cone

| \(j\) | cap | support size | evaluation on residual | top semantic support | support SHA-256 |
|---:|---:|---:|---:|---|---|
| 2 | 6 | 17 | \(3105/56\) | \(0:(5,5)\mapsto144;\ 1:(0,4)\mapsto108\) | `e9a0c0751150fc710dc492d4cdd60c4eb4146cd1901486989feec3919648f273` |
| 3 | 8 | 36 | \(-17577/64\) | \(0:(6,6)\mapsto-504;\ 1:(1,5)\mapsto-72\) | `ec8de40894bc4bf9abbd71062491a82262ac933123cf4f7c89a109891728e8c9` |
| 4 | 10 | 61 | \(850905/64\) | \(0:(7,7)\mapsto10080;\ 1:(2,6)\mapsto216\) | `d3285b104e42fbcb1f99eb58d0a332ac20cf0e1f7111b571dc64edd948a704d4` |
| 5 | 12 | 91 | \(-22680405/64\) | \(0:(8,8)\mapsto-133056;\ 1:(3,7)\mapsto-1296\) | `a40f4a5ba317a00fddfff58d2da5cd3784854fa2ab02cb1f8dde3b0fd6282294` |
| 6 | 13 | 2 | \(45/8\) | \(0:(8,9)\mapsto25,\ (9,8)\mapsto2\) | `a422b198f0f9c165c32e88be4290ec7622d22c9f4bfea7cd49236149796d69ce` |

For \(j=2,\ldots,5\), the top semantic support shifts by \((1,1)\) in
slot zero and by \((1,1)\) in slot one.  The coefficients do not follow a
derived recurrence.  At \(j=6\), the old functional changes category:
its support collapses to two rows in the first contact equation.

### Parity at the phase transition

At \(j=6\), the primitive cap-fourteen parity cokernel has support

\[
(0,9,9)\longmapsto1,
\]

evaluation \(1330/81\), and support hash
`8572fd5a23de48fbba8ecd2421fe1ce568e76d40098700d4cefa4bf6bf617f81`.

## Weight-twelve phase transition

At weight twelve the cone has two independent top monomials,

\[
Y^4,\qquad X^3Y^2,
\]

whereas the parity section has only \(X^6\).  This is the first tested order
where the higher-rank cone reduces the paired source cost:

\[
\deg V_6^{\rm cone}=14
<15=\deg V_6^{\rm parity}.
\]

The comparison survives all lower affine freedoms.  It is therefore a
property of the two declared target languages in this exact finite window,
not an artifact of a sequential pivot choice.

## Claim boundary

This is exact finite evidence through instantaneous order six.  It rejects
the proposed all-order extrapolation \(\deg V_j=2j+3\): the cone already
passes one degree earlier at \(j=6\), precisely when its top target symbol
becomes rank two.  It does not prove eventual bounded source cost, an
all-order triangular lifting theorem, or a contact-complexity value.
