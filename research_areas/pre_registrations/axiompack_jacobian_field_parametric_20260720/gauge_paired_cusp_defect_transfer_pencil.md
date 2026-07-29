# Paired transfer cost of the minimum-section cusp defect

**Status:** preregistered before the source-degree calculation

## Eigenquestion

For the minimum-degree cusp section, two distinct residue-one inputs have
the exact target defect

\[
\delta_{m,n}
=\frac{q-p}{3}DY^{p+q-3},
\qquad
m=3p+1,\quad n=3q+1,
\]

where

\[
D=X^3-Y^2=-C/108.
\]

What is the exact polynomial source cost if this stabilizer defect is moved
across the seed contact rather than retained on the target side?

## Seed transfer identities

Use

\[
f(r)=(-3r^2,-2r^3),\qquad
T=(1,r),\qquad
f'=-6rT,
\]

and normalized restriction

\[
X\mapsto r^2,\qquad Y\mapsto r^3.
\]

The seed stabilizer acts tangentially:

\[
X_C(f)=-108r^3T.
\]

Therefore

\[
X_D(f)=r^3T.
\]

If

\[
j=p+q-3,\qquad
w=m+n-5=3j+6,
\]

then

\[
X_{\delta_{m,n}}(f)
=\frac{q-p}{3}r^{3j+3}T.
\]

Writing this as \(f'u\) gives the candidate source curve velocity

\[
u=-\frac{q-p}{18}r^{3j+2}
=-\frac{q-p}{18}r^{w-4}.
\]

The strict weighted-volume lift \(U_k\) of \(r^k\) has ordinary source degree

\[
\deg U_k=2k-1.
\]

Hence the proposed exact transfer cost is

\[
\boxed{\deg U_{w-4}=2w-9.}
\]

The same target defect has ordinary Hamiltonian degree

\[
\deg(DY^j)=j+3=\frac w3+1.
\]

## Counterattacks

1. **Normalization sign:** replay \(D=-C/108\) and
   \(X_C(f)=-108r^3T\) before using \(X_D(f)=r^3T\).

2. **Wrong source lift:** the curve velocity \(r^{w-4}\) must be lifted by
   the strict weighted-volume field \(U_{w-4}\), not by an arbitrary
   one-variable vector field.  Verify \(w-4\ge2\) and both source lift ideals.

3. **Degree convention:** record polynomial field degree \(2k-1\)
   separately from derivation excess \(2k-2\).

4. **Global inference:** one transferred defect gives a cost identity.
   A lower bound for \(\sigma_{\rm ct}\) requires proving that infinitely
   many such defects occur for the moving connection or that avoiding them
   forces the unique half-rate target section.

## Success and kill conditions

- **Success:** exact target/source transfer formulas with the two degree
  costs \(\frac w3+1\) and \(2w-9\).
- **Kill:** a sign or exponent mismatch under direct substitution, or a
  lower-degree strict source lift of the same curve velocity.
- **Campaign boundary:** success supplies a local minimax mechanism; it does
  not establish which defect sequence the full moving family excites.

## Intended verification surface

Use the already proved seed stabilizer action and weighted-volume source
lift formula.  The new formal endpoint should be the exponent and degree
arithmetic, reusing the existing seed-quotient carrier rather than
formalizing the entire cusp map again.

## Settled transfer theorem

The proposed formulas hold exactly.

Let \(p,q\ge2\), \(p\ne q\), and put

\[
m=3p+1,\qquad n=3q+1,\qquad
j=p+q-3,\qquad w=m+n-5.
\]

Then

\[
w=3j+6
\]

and the target defect is

\[
\delta_{m,n}=\frac{q-p}{3}DY^j.
\]

Since \(D(f)=0\), the Hamiltonian product rule gives

\[
X_{DY^j}(f)
=Y(f)^jX_D(f)
=r^{3j+3}T.
\]

Consequently

\[
\begin{aligned}
X_{\delta_{m,n}}(f)
&=\frac{q-p}{3}r^{3j+3}T\\
&=f'\left(-\frac{q-p}{18}r^{3j+2}\right)\\
&=f'\left(-\frac{q-p}{18}r^{w-4}\right).
\end{aligned}
\]

Because \(p,q\ge2\), one has \(j\ge1\) and \(w-4=3j+2\ge5\).
The source mode is therefore in the strict lift range.  The canonical
weighted-volume lift \(U_{w-4}\) has both components homogeneous of degree

\[
2(w-4)-1=2w-9.
\]

This degree is minimal even before the weighted-volume constraint.  If a
polynomial field \(U\) has degree \(d\), then
\(\deg U(r)\le d+1\) because \(r=VG\).  The identity
\(U(r)=r^{w-4}\) therefore forces

\[
d+1\ge2(w-4),
\]

or \(d\ge2w-9\).

On the target side,

\[
DY^j=X^3Y^j-Y^{j+2},
\]

so

\[
\deg(DY^j)=j+3=\frac{w-6}{3}+3=\frac w3+1.
\]

For a nonzero defect \(p\ne q\), the bounds \(p,q\ge2\) give \(j\ge2\).
Both monomials

\[
X^3Y^j,\qquad Y^{j+2}
\]

therefore lie in the higher-rank cone \(b\ge1,\ a\le2b\).  Thus retaining
the defect as an independent target stabilizer direction preserves that
cone.

Thus the exact paired cost is

\[
\boxed{
\text{target retention: }\frac w3+1,
\qquad
\text{source export: }2w-9.
}
\]

For the first countercycle \(p=2,q=3\), this reads

\[
w=12,\qquad
\delta=\frac13DY^2,\qquad
u=-\frac1{18}r^8,
\]

with target degree \(5\) and source degree \(15\).

## Parameter-order corollary

If a sequence of these defects occurs at logarithmic order \(N\) with the
natural cusp weight

\[
w=N+5,
\]

then exporting it produces a source vector field of degree

\[
2N+1
\]

and derivation excess \(2N\).  Any infinite unbounded such sequence has
source slope exactly two.  Retaining individual defects on the target costs
only asymptotic rate \(1/3\).  There are then two distinct compatibility
categories:

- forcing one target line per cusp weight selects the unique rank-one
  section and rate \(1/2\);
- retaining independent stabilizer directions permits the sharp
  higher-rank Lie cone of rate \(3/7\).

The paired transfer therefore gives a three-way conditional tradeoff:

- infinitely many defects transferred off the target force source slope
  two;
- rank-one target absorption costs rate \(1/2\);
- higher-rank target retention can stay in the \(3/7\) cone, while its
  paired moving-family source cost remains to be determined.

The remaining missing hypothesis is excitation by the full normalized
moving family.

## Formal carrier and provider-free ratification

The defect-weight arithmetic, nonzero scalar, target degree, exported source
exponent, exact source degree, and parameter-order specialization are
formalized in
[`AxiomPackJacobianPairedCuspDefectTransferArithmetic.lean`](../../../ztare_proofs/ZtareProofs/AxiomPackJacobianPairedCuspDefectTransferArithmetic.lean).
The module compiles without `sorry`, `admit`, or declared axioms.

LeanMill ratified

`AxiomPackJacobianPairedCuspDefectTransferArithmetic.paired_cusp_defect_transfer_arithmetic_terminal_certificate`

through the provider-free carried-artifact route with zero inference calls.
Target identity, statement integrity, the axiom allowlist, matched negative
control, governance, and kernel compilation all passed.

- source/closure SHA-256:
  `7dfed1873ade1b4f6baf47de3398f576c17359c41c0bfe0930269d8e2c6bf6c0`
- target-signature SHA-256:
  `12b6181d2ebdba3d0e863da39cb290e5ab02e5014a8461206283ad902e79ac61`
- kernel-parity record SHA-256:
  `b2be5bd241d39de2896518bc537ebdac308cd8083da0c78a606fd04b22c1771c`
- closure-certificate record SHA-256:
  `d6f370dc83ea606f49e9c9e7427768334145764878d38f917a5fe4204ad0808d`
- closure artifact:
  [`AxiomPackJacobianPairedCuspDefectTransferArithmetic.paired_cusp_defect_transfer_arithmetic_terminal_certificate_7dfed1873ade.lean`](../../../ztare_proofs/closures/AxiomPackJacobianPairedCuspDefectTransferArithmetic.paired_cusp_defect_transfer_arithmetic_terminal_certificate_7dfed1873ade.lean)

The Hamiltonian product rule on the cusp, construction and minimality of the
strict source lift, and excitation by the moving family remain in the pencil
argument.
