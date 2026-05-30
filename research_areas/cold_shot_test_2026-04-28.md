# Cold-shot meta-falsification test, gpt-5.5, 2026-04-28 (retry)

## Output

```text
LAGRANGIAN
  Let a0 = 1.20e-10 m s^-2, m = mass_log10, r = radius_log10, d = rho_local_log10,
      y = g_bar/a0, and cbrt(.) denote the real cube root.

  Dimensionless environmental source:
      A(g_bar,m,r,d) =
        (y + 1.0e-4)^(-1/2)
        * 10^[0.025 (m - 11)]
        * 10^[0.035 (r - 1)]
        * 10^[-0.80 (d + 2.6)]

      C_cl(m,r) =
        [1 + 10^(-2.0 (m - 13.2))]^-1
        * [1 + 10^(-2.0 (r - 1.6))]^-1

      O_cl(r) =
        [1 + 10^(-2.5 (r - 2.25))]^-1

      B_cl(m,r,d) =
        C_cl(m,r) * O_cl(r) * [1 + 10^(0.50 (d + 2.6))]^-1

      J(g_bar,m,r,d) =
        1.85 A/(1 + 0.18 A) + 0.90 B_cl

  Scalar sector:
      L_phi = -(a0^2/8πG) { (ℓ_phi^2/2) |∇phi|^2 + V(phi;J) }

      V(phi;J) = 0.5 phi^2 + 0.25 phi^4 - J phi

      Static Euler-Lagrange equation:
        -ℓ_phi^2 ∇^2 phi + phi + phi^3 = J(g_bar,m,r,d)

      Homogeneous closed-form branch used in the acceleration law:
        phi =
          cbrt[J/2 + sqrt(J^2/4 + 1/27)]
        + cbrt[J/2 - sqrt(J^2/4 + 1/27)]

      Screen factor:
        S = phi^2/(phi^2 + 0.35^2)

ACCELERATION LAW
  MOND interpolation:
      nu(y) = [1 - exp(-sqrt(y))]^-1

  Cluster-reservoir enhancement, active only for high-mass extended systems:
      E_cl = 0.72 C_cl(m,r) [0.20 + 0.80 O_cl(r)]

  Closed-form prediction:
      g_obs(g_bar,m,r,d) =
        g_bar * { 1 + S [nu(y) - 1] [1 + E_cl] }

ANCHOR CHECKS IMPLIED BY THE FORM
  Galaxy outskirts: m≈11, r≈1, d≲-3, y<<1 gives S≈1, C_cl≈0, hence g_obs≈sqrt(a0 g_bar).
  Tian/CLASH outer cluster: m≈14.5, r≳2.5, d≲-3.5 gives S≈1 and E_cl≈0.6–0.7, i.e. enhanced outer RAR.
  Tian/CLASH inner cluster: r≲2, d higher gives S and O_cl smaller, hence a more Newtonian inner prediction than the outer one.
  Chae 2023 wide binaries: m≈0, r≈-4, d≈-2.6, y≈1 gives g_obs/g_bar≈1.38.
  Banik 2024 null wide binaries: same binary scale but d≈-1 gives S≈0.01 and g_obs/g_bar≈1.00.
  Solar system: y>>1 and high d give nu→1, S→0, hence g_obs/g_bar→1.
```

This is a nontrivial chameleon-like scalar because the static solution is the cubic algebraic response `phi + phi^3 = J(g_bar,m,r,d)`, not a cosmetic equality to one background field.  The density dependence screens high-density inner clusters, Banik binaries, and the Solar System, while the mass–radius gates add an outer-cluster reservoir without activating in disks or binaries.  The same universal `a0` and scalar-potential constants are used in every class, and each input controls a distinct failure mode: RAR scale, cluster identification, inner/outer radius behavior, and environmental screening.
