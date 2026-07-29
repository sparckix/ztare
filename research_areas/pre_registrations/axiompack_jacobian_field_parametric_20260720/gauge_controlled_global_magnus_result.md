# Fixed-slice global Magnus finite replay

## Replay

```bash
./venv/bin/python \
  research_areas/pre_registrations/axiompack_jacobian_field_parametric_20260720/gauge_controlled_global_magnus.py
```

Replay script SHA-256:

```text
1ca551ba094b56170d7e613ad0d463d084aa33f2a44dc63b57c86e3b4665df2a
```

The replay reconstructs the normalized family and the fixed-slice target
control

\[
K_s=a(s)P^3+b(s)PQ-\frac14Q^2,
\]

checks that its target-relative source velocity vanishes at \(s=0\), solves
the source-flow Magnus recursion through order eight, and compares the leading
homogeneous fields with explicit weighted Hamiltonians.

Here \(\partial_s\psi_s=D\psi_sV_s\), so the velocity multiplies the flow
on the right and the first inverse-`dexp` bracket coefficient is \(+1/2\).
The replay also applies the matching forward `dexp` and recovers every
input coefficient.

## Exact finite result

The source velocity degrees at parameter orders \(0,\ldots,7\) are

\[
-\infty,11,13,15,15,15,15,15.
\]

The source logarithm degrees at orders \(1,\ldots,8\) are

\[
-\infty,11,13,15,17,22,24,26.
\]

With \(g=2t-3v\), the top fields at orders six, seven, and eight are the
weighted-Hamiltonian fields of

\[
\frac{v^{13}g^{12}}{1048576},\qquad
-\frac{619v^{14}g^{13}}{1321205760},\qquad
\frac{343v^{15}g^{14}}{6794772480}.
\]

They are nonzero and have degrees \(22,24,26\), respectively.  Equivalently,
the three computed coefficients lie on the ray

\[
X_{c_n v^{n+7}g^{n+6}},\qquad c_n\ne0.
\]

## Boundary

This is an exact order-six-to-eight statement for one connection.  It gives
no asymptotic theorem.  The proposed continuation is falsified at any exact
order \(n\ge9\) if the degree differs from \(2n+10\), the top projection
leaves the displayed ray, or its scalar coefficient vanishes.

Even persistence at every order would describe this gauge only.  It would
not prove a minimax lower bound over all contacts or strengthen the existing
\(\sigma_{\rm ct}\le2\) upper bound.  The finite ray is a diagnostic for the
remaining gauge search.
