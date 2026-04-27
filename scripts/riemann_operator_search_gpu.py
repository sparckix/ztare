#!/usr/bin/env python3
"""GP-125: Riemann Operator Search on GPU (A100).

Searches for a Hilbert-Pólya operator whose eigenvalues match
the Riemann zeta zeros. Uses differentiable eigendecomposition
with gradient descent on parameterized Hamiltonians.

Self-contained — no ZTARE dependencies. Just needs PyTorch + zeros data.

Usage:
    python riemann_operator_search_gpu.py
    python riemann_operator_search_gpu.py --n-zeros 200 --n-matrix 500 --restarts 100

Results saved to riemann_operator_result.json
"""

import argparse
import json
import time
import torch
import numpy as np


def compute_riemann_zeros(n_zeros):
    """Compute first n Riemann zeros via mpmath (slow but exact)."""
    try:
        from mpmath import zetazero
        print(f"Computing {n_zeros} Riemann zeros via mpmath...")
        zeros = []
        for k in range(1, n_zeros + 1):
            zeros.append(float(zetazero(k).imag))
            if k % 50 == 0:
                print(f"  {k}/{n_zeros}")
        return zeros
    except ImportError:
        print("mpmath not available — using hardcoded first 50 zeros")
        return HARDCODED_ZEROS[:n_zeros]


# First 50 zeros hardcoded for environments without mpmath
HARDCODED_ZEROS = [
    14.134725, 21.022040, 25.010858, 30.424876, 32.935062,
    37.586178, 40.918719, 43.327073, 48.005151, 49.773832,
    52.970321, 56.446248, 59.347044, 60.831779, 65.112544,
    67.079811, 69.546402, 72.067158, 75.704691, 77.144840,
    79.337375, 82.910381, 84.735493, 87.425275, 88.809111,
    92.491899, 94.651344, 95.870634, 98.831194, 101.317851,
    103.725538, 105.446623, 107.168611, 111.029536, 111.874659,
    114.320220, 116.226680, 118.790783, 121.370125, 122.946829,
    124.256819, 127.516684, 129.578704, 131.087688, 133.497737,
    134.756510, 138.116042, 139.736209, 141.123707, 143.111846,
]


def compute_von_mangoldt(n):
    """Compute Λ(n): log(p) if n=p^k for some prime p, else 0."""
    if n <= 1:
        return 0.0
    # Trial division to check if n is a prime power
    d = 2
    while d * d <= n:
        if n % d == 0:
            # d divides n; check if n = d^k
            val = n
            while val > 1:
                if val % d != 0:
                    return 0.0  # n has another prime factor
                val //= d
            return np.log(d)
        d += 1
    # n is prime (n = n^1)
    return np.log(n)


def compute_radical(n):
    """Radical of n = product of distinct primes dividing n.
    log(rad(n)) = sum of log(p) over distinct primes p | n."""
    if n <= 1:
        return 1
    result = 1
    d = 2
    while d * d <= n:
        if n % d == 0:
            result *= d
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        result *= n
    return result


def compute_gcd(a, b):
    """Euclidean GCD."""
    while b:
        a, b = b, a % b
    return a


def compute_sigma(n):
    """Sum of divisors of n."""
    if n <= 0:
        return 0
    s = 0
    d = 1
    while d * d <= n:
        if n % d == 0:
            s += d
            if d != n // d:
                s += n // d
        d += 1
    return s


def compute_tau(n):
    """Number of divisors of n."""
    if n <= 0:
        return 0
    t = 0
    d = 1
    while d * d <= n:
        if n % d == 0:
            t += 1
            if d != n // d:
                t += 1
        d += 1
    return t


def build_dense_arithmetic(N):
    """Build DENSE arithmetic operators: Hankel, Toeplitz, XY-coupling.

    The sparse off-diagonal operators (build_arithmetic_offdiag) couple
    only pairs (i,j) with gcd>1 — about 39% density (via Mertens' 6/π²).
    This is too sparse to induce Wigner-Dyson level repulsion.

    Dense operators required:
    - Hankel: H[i,j] = f(i+j+2), nonzero whenever f is nonzero at i+j+2
    - Toeplitz: T[i,j] = f(|i-j|+1), similar density
    - XY-coupling: X[i,j] = g(i+1)·g(j+1)/((i-j)^2+1), long-range dense

    These are the operator classes historically associated with Hilbert-
    Pólya candidates (Connes, Pólya program). All returned matrices are
    symmetric.
    """
    # Precompute arithmetic values up to 2N+2 (Hankel needs i+j+2)
    limit = 2 * N + 4
    lam = [compute_von_mangoldt(k) for k in range(limit)]
    sig = [float(compute_sigma(k)) for k in range(limit)]
    tau = [float(compute_tau(k)) for k in range(limit)]
    # Rescale sigma (grows like n log log n) by n to keep numerics bounded
    sig_scaled = [sig[k] / max(k, 1) for k in range(limit)]
    tau_scaled = [tau[k] / max(np.log(max(k, 2)), 1.0) for k in range(limit)]

    H_mangoldt = np.zeros((N, N))
    H_sigma = np.zeros((N, N))
    H_tau = np.zeros((N, N))
    T_mangoldt = np.zeros((N, N))
    T_sigma = np.zeros((N, N))
    XY_mangoldt = np.zeros((N, N))

    for i in range(N):
        for j in range(N):
            s = i + j + 2               # Hankel index
            d = abs(i - j) + 1          # Toeplitz index
            H_mangoldt[i, j] = lam[s] if s < limit else 0.0
            H_sigma[i, j] = sig_scaled[s] if s < limit else 0.0
            H_tau[i, j] = tau_scaled[s] if s < limit else 0.0
            T_mangoldt[i, j] = lam[d] if d < limit else 0.0
            T_sigma[i, j] = sig_scaled[d] if d < limit else 0.0
            if i != j:
                # XY-coupling: long-range, normalized
                XY_mangoldt[i, j] = lam[i + 1] * lam[j + 1] / ((i - j) ** 2 + 1.0)
            else:
                # Self-term for XY: keep bounded
                XY_mangoldt[i, j] = lam[i + 1] ** 2

    return {
        "hankel_mangoldt": H_mangoldt,
        "hankel_sigma": H_sigma,
        "hankel_tau": H_tau,
        "toeplitz_mangoldt": T_mangoldt,
        "toeplitz_sigma": T_sigma,
        "xy_mangoldt": XY_mangoldt,
    }


def build_arithmetic_offdiag(N):
    """Build off-diagonal arithmetic matrices.

    These matrices encode number-theoretic relationships BETWEEN indices
    (rather than diagonal shifts). Off-diagonal coupling is REQUIRED for
    level repulsion (Wigner-Dyson statistics) — diagonal terms alone
    cannot produce the eigenvalue correlation that GUE statistics require.

    Per Gemini Pro 2026-04-23 inversion: diagonal arithmetic terms can
    only inject IRREGULAR POSITIONS into the spectrum, not IRREGULAR
    REPULSION. The latter requires off-diagonal entries that depend on
    prime-divisibility relationships between row/column indices.

    All returned matrices are symmetric (gcd is symmetric in its args).

    Returns: dict of NumPy arrays of shape (N, N), zeros on diagonal.
    """
    M_gcd = np.zeros((N, N))           # log(gcd(i+1, j+1))
    M_prime_coupling = np.zeros((N, N)) # 1 if gcd(i+1, j+1) > 1
    M_adelic = np.zeros((N, N))        # log(rad(gcd(i+1, j+1)))
    M_divisor = np.zeros((N, N))       # number of divisors of gcd

    for i in range(N):
        for j in range(i + 1, N):  # upper triangle only; mirror via symmetry
            g = compute_gcd(i + 1, j + 1)
            if g > 1:
                M_gcd[i, j] = np.log(g)
                M_prime_coupling[i, j] = 1.0
                M_adelic[i, j] = np.log(compute_radical(g))
                # divisor count
                divisors = 0
                d = 1
                while d * d <= g:
                    if g % d == 0:
                        divisors += 1
                        if d != g // d:
                            divisors += 1
                    d += 1
                M_divisor[i, j] = float(divisors)

    # Mirror to lower triangle
    M_gcd = M_gcd + M_gcd.T
    M_prime_coupling = M_prime_coupling + M_prime_coupling.T
    M_adelic = M_adelic + M_adelic.T
    M_divisor = M_divisor + M_divisor.T

    return {
        "gcd": M_gcd, "prime_coupling": M_prime_coupling,
        "adelic": M_adelic, "divisor": M_divisor,
    }


def build_operators(N, device, dtype):
    """Build the oscillator basis operators including number-theoretic terms."""
    x_mat = torch.zeros(N, N, device=device, dtype=dtype)
    for j in range(N - 1):
        x_mat[j, j + 1] = ((j + 1) ** 0.5) / (2 ** 0.5)
        x_mat[j + 1, j] = ((j + 1) ** 0.5) / (2 ** 0.5)

    x2 = x_mat @ x_mat
    x4 = x2 @ x2
    diag_n = torch.diag(torch.arange(N, device=device, dtype=dtype) + 0.5)
    diag_log = torch.diag(torch.log(torch.arange(N, device=device, dtype=dtype) + 2.0))
    diag_nlogn = torch.diag(
        (torch.arange(N, device=device, dtype=dtype) + 0.5)
        * torch.log(torch.arange(N, device=device, dtype=dtype) + 2.0)
    )
    # n^2 term for additional flexibility
    diag_n2 = torch.diag((torch.arange(N, device=device, dtype=dtype) + 0.5) ** 2 / N)
    # log^2 term
    diag_log2 = torch.diag(torch.log(torch.arange(N, device=device, dtype=dtype) + 2.0) ** 2)

    # --- Number-theoretic diagonal terms (GP-125 grammar expansion) ---
    # von Mangoldt Λ(n): log(p) if n=p^k, else 0
    # Injects prime-structure irregularity into eigenvalue spacings
    mangoldt_vals = [compute_von_mangoldt(n + 1) for n in range(N)]
    diag_mangoldt = torch.diag(torch.tensor(mangoldt_vals, device=device, dtype=dtype))

    # Chebyshev ψ(n) = Σ_{k≤n} Λ(k) — running sum of von Mangoldt
    # ψ(n) ~ n by Prime Number Theorem
    psi_vals = np.cumsum(mangoldt_vals).tolist()
    diag_psi = torch.diag(torch.tensor(psi_vals, device=device, dtype=dtype))

    # Prime indicator: 1 if n is prime, 0 otherwise
    # Sparser than von Mangoldt (no prime powers)
    prime_vals = []
    for n in range(1, N + 1):
        if n < 2:
            prime_vals.append(0.0)
        elif n == 2:
            prime_vals.append(1.0)
        elif n % 2 == 0:
            prime_vals.append(0.0)
        else:
            is_prime = True
            d = 3
            while d * d <= n:
                if n % d == 0:
                    is_prime = False
                    break
                d += 2
            prime_vals.append(1.0 if is_prime else 0.0)
    diag_prime = torch.diag(torch.tensor(prime_vals, device=device, dtype=dtype))

    # Möbius-weighted: μ(n)·log(n) — appears in explicit formulae
    # μ(n) = (-1)^k if n = p1·p2·...·pk (squarefree), 0 if squareful
    mobius_vals = []
    for n in range(1, N + 1):
        if n == 1:
            mobius_vals.append(0.0)
            continue
        # Factorize
        val = n
        factors = 0
        squarefree = True
        d = 2
        while d * d <= val:
            if val % d == 0:
                factors += 1
                val //= d
                if val % d == 0:
                    squarefree = False
                    break
                d += 1
            else:
                d += 1
        if val > 1:
            factors += 1
        if squarefree:
            mobius_vals.append((-1) ** factors * np.log(n))
        else:
            mobius_vals.append(0.0)
    diag_moblog = torch.diag(torch.tensor(mobius_vals, device=device, dtype=dtype))

    # --- Off-diagonal arithmetic (level-repulsion-capable) ---
    # Per Gemini Pro physics inversion: diagonal terms cannot produce
    # GUE level repulsion. Off-diagonal coupling depending on number-
    # theoretic relationships between row/col indices is required.
    offdiag = build_arithmetic_offdiag(N)
    offdiag_torch = {
        f"od_{k}": torch.tensor(v, device=device, dtype=dtype)
        for k, v in offdiag.items()
    }

    # --- Dense arithmetic operators (Hankel / Toeplitz / XY) ---
    # Sparse off-diagonal (od_*) fills only gcd>1 pairs (~39% density via
    # Mertens 6/π²). Too sparse to break level-repulsion. Dense operators
    # couple all (i,j) pairs simultaneously. Historically connected to
    # Hilbert-Pólya via Pólya's Hankel program and Connes' adelic work.
    dense = build_dense_arithmetic(N)
    dense_torch = {
        f"dn_{k}": torch.tensor(v, device=device, dtype=dtype)
        for k, v in dense.items()
    }

    operators = {
        "x": x_mat, "x2": x2, "x4": x4,
        "n": diag_n, "log": diag_log, "nlogn": diag_nlogn,
        "n2": diag_n2, "log2": diag_log2,
        "mangoldt": diag_mangoldt, "psi": diag_psi,
        "prime": diag_prime, "moblog": diag_moblog,
        "I": torch.eye(N, device=device, dtype=dtype),
    }
    operators.update(offdiag_torch)
    operators.update(dense_torch)
    return operators


# Generator families — the LLM outer loop would propose these
GENERATORS = {
    "ST": {
        "n_params": 5,
        "terms": ["n", "log", "nlogn", "x2", "I"],
        "desc": "Sierra-Townsend: n + log + nlogn + x^2 + shift",
    },
    "ST_x4": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "x4", "I"],
        "desc": "ST + quartic",
    },
    "ST_log2": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "log2", "x2", "I"],
        "desc": "ST + log^2",
    },
    "ST_n2": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "n2", "x2", "I"],
        "desc": "ST + n^2",
    },
    "full": {
        "n_params": 8,
        "terms": ["n", "log", "nlogn", "log2", "n2", "x2", "x4", "I"],
        "desc": "Full: all polynomial terms",
    },
    # --- Number-theoretic generators (GP-125 grammar expansion) ---
    "ST_mangoldt": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "mangoldt", "I"],
        "desc": "ST + von Mangoldt Λ(n)",
    },
    "connes_lite": {
        "n_params": 5,
        "terms": ["nlogn", "x2", "mangoldt", "psi", "I"],
        "desc": "Connes-inspired: nlogn + x^2 + Λ + ψ",
    },
    "ST_psi": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "psi", "I"],
        "desc": "ST + Chebyshev ψ(n)",
    },
    "ST_prime": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "prime", "I"],
        "desc": "ST + prime indicator",
    },
    "arith_full": {
        "n_params": 9,
        "terms": ["n", "log", "nlogn", "x2", "mangoldt", "psi", "prime", "moblog", "I"],
        "desc": "Full arithmetic: all number-theoretic + polynomial",
    },
    # Pure-arithmetic (no polynomial x^k confinement): tests whether
    # arithmetic terms alone can encode GUE statistics.
    "pure_arith": {
        "n_params": 6,
        "terms": ["n", "nlogn", "mangoldt", "psi", "moblog", "I"],
        "desc": "Pure arithmetic: no x^k confinement, only diagonal arithmetic",
    },
    # Connes adelic-inspired: (xp+px)-like (via n) + arithmetic only,
    # no polynomial confinement at all.
    "connes_pure": {
        "n_params": 5,
        "terms": ["nlogn", "mangoldt", "psi", "moblog", "I"],
        "desc": "Connes-pure: nlogn + Λ + ψ + μ·log — no polynomial",
    },
    # --- OFF-DIAGONAL ARITHMETIC GENERATORS (2026-04-23 addition) ---
    # These add coupling terms that depend on number-theoretic relationships
    # BETWEEN matrix indices. Required for GUE-style level repulsion which
    # diagonal-only operators cannot produce.
    "ST_gcd": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "od_gcd", "I"],
        "desc": "ST + off-diagonal log(gcd) coupling",
    },
    "ST_adelic": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "od_adelic", "I"],
        "desc": "ST + off-diagonal log(rad(gcd)) coupling (Connes-style)",
    },
    "ST_prime_coupling": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "od_prime_coupling", "I"],
        "desc": "ST + off-diagonal binary prime-coupling coupling",
    },
    "ST_divisor": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "od_divisor", "I"],
        "desc": "ST + off-diagonal divisor-count coupling",
    },
    # Combined: best polynomial baseline + off-diagonal arithmetic
    "ST_n2_gcd": {
        "n_params": 7,
        "terms": ["n", "log", "nlogn", "n2", "x2", "od_gcd", "I"],
        "desc": "ST_n2 (best polynomial) + off-diagonal log(gcd)",
    },
    # Pure off-diagonal (no diagonal arithmetic, just polynomial backbone + coupling)
    "ST_full_offdiag": {
        "n_params": 8,
        "terms": ["n", "log", "nlogn", "x2", "od_gcd", "od_adelic",
                  "od_prime_coupling", "I"],
        "desc": "ST + all off-diagonal arithmetic (gcd + adelic + prime)",
    },
    # Connes-style: minimal polynomial + heavy off-diagonal arithmetic
    "connes_offdiag": {
        "n_params": 5,
        "terms": ["nlogn", "od_gcd", "od_adelic", "od_prime_coupling", "I"],
        "desc": "Connes off-diag: nlogn + 3 off-diag arithmetic — no x^k confinement",
    },
    # --- DENSE ARITHMETIC GENERATORS (2026-04-23 PM addition) ---
    # Sparse off-diagonals above (od_*) could not break level-repulsion
    # barrier (informative null from 2026-04-23 AM run). Dense operators
    # (Hankel, Toeplitz, XY-coupling) test the "arithmetic must be dense"
    # conjecture: Wigner-Dyson requires many simultaneous couplings, not
    # gcd-sparse ones.
    "ST_hankel_mangoldt": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "dn_hankel_mangoldt", "I"],
        "desc": "ST + Hankel of von Mangoldt Λ(i+j) — dense coupling",
    },
    "ST_hankel_sigma": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "dn_hankel_sigma", "I"],
        "desc": "ST + Hankel of σ(i+j)/n — dense divisor-sum coupling",
    },
    "ST_toeplitz_mangoldt": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "dn_toeplitz_mangoldt", "I"],
        "desc": "ST + Toeplitz of Λ(|i-j|) — Chebyshev-ψ-style dense coupling",
    },
    "ST_toeplitz_sigma": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "dn_toeplitz_sigma", "I"],
        "desc": "ST + Toeplitz of σ(|i-j|)/n — dense shift-invariant coupling",
    },
    "ST_xy_mangoldt": {
        "n_params": 6,
        "terms": ["n", "log", "nlogn", "x2", "dn_xy_mangoldt", "I"],
        "desc": "ST + XY-coupling Λ(i)Λ(j)/((i-j)²+1) — long-range dense",
    },
    # Pure dense: no polynomial backbone — does dense arithmetic alone
    # suffice?
    "pure_dense_hankel": {
        "n_params": 3,
        "terms": ["nlogn", "dn_hankel_mangoldt", "I"],
        "desc": "nlogn + Hankel(Λ) — pure dense arithmetic test",
    },
    "polya_hankel": {
        "n_params": 4,
        "terms": ["nlogn", "dn_hankel_sigma", "dn_hankel_tau", "I"],
        "desc": "Pólya program-inspired: Hankel(σ) + Hankel(τ) + nlogn",
    },
    "connes_dense": {
        "n_params": 5,
        "terms": ["nlogn", "dn_toeplitz_mangoldt", "dn_xy_mangoldt",
                  "dn_hankel_mangoldt", "I"],
        "desc": "Connes-dense: nlogn + 3 dense Λ-operators (Toeplitz + XY + Hankel)",
    },
    # Combined best polynomial + dense
    "ST_log2_hankel": {
        "n_params": 7,
        "terms": ["n", "log", "nlogn", "log2", "x2", "dn_hankel_mangoldt", "I"],
        "desc": "ST_log2 (prior best polynomial) + Hankel(Λ)",
    },
}


def make_hamiltonian(params, ops, terms):
    """Build Hamiltonian from parameters and operator terms."""
    H = torch.zeros_like(ops["I"])
    for i, term in enumerate(terms):
        H = H + params[i] * ops[term]
    return (H + H.T) / 2


def precision_polish(params_init, ops, terms, target_tensor, n_steps=2000,
                     device="cpu"):
    """L-BFGS precision polish: grind AdamW params to ~15 stable digits.

    Returns dict with polished params, loss, and constant recognition results.
    """
    dtype = torch.float64
    ops_64 = {k: v.to(dtype=dtype) for k, v in ops.items()}
    target_64 = target_tensor.to(dtype=dtype)
    n_match = len(target_64)

    if isinstance(params_init, torch.Tensor):
        p_vals = params_init.tolist()
    else:
        p_vals = [params_init[t] for t in terms]

    params = torch.tensor(p_vals, device=device, dtype=dtype, requires_grad=True)

    # Initial loss
    with torch.no_grad():
        H0 = make_hamiltonian(params, ops_64, terms)
        eigs0, _ = torch.linalg.eigh(H0)
        loss_before = float(torch.mean((eigs0[:n_match] - target_64) ** 2))

    print(f"\n  L-BFGS Polish: loss_before={loss_before:.10e}")

    optimizer = torch.optim.LBFGS(
        [params], lr=1.0, max_iter=20,
        line_search_fn="strong_wolfe",
        tolerance_grad=1e-15, tolerance_change=1e-16,
    )

    best_loss = loss_before
    best_params = params.detach().clone()
    loss_history = []
    N = ops_64["I"].shape[0]

    for epoch in range(n_steps // 20):
        def closure():
            optimizer.zero_grad()
            H = make_hamiltonian(params, ops_64, terms)
            eigs, _ = torch.linalg.eigh(H)
            loss = torch.mean((eigs[:n_match] - target_64) ** 2)
            n_rep = min(2 * n_match, N)
            diffs = eigs[:n_rep].unsqueeze(0) - eigs[:n_rep].unsqueeze(1)
            mask = 1.0 - torch.eye(n_rep, device=device, dtype=dtype)
            repulsion = torch.sum(mask / (diffs.abs() + 1e-8)) * 1e-10
            total = loss + repulsion
            if not torch.isnan(total):
                total.backward()
            return total

        loss_val = optimizer.step(closure)
        if loss_val is not None and not torch.isnan(loss_val):
            lv = float(loss_val)
            loss_history.append(lv)
            if lv < best_loss:
                best_loss = lv
                best_params = params.detach().clone()

        if len(loss_history) > 10:
            recent = loss_history[-10:]
            if max(recent) - min(recent) < 1e-15:
                print(f"  Polish converged at epoch {epoch}")
                break

        if epoch % 10 == 0:
            print(f"  Polish epoch {epoch}: loss={best_loss:.15e}")

    stable_digits = max(0, int(-np.log10(best_loss + 1e-30)))
    polished = {terms[i]: float(best_params[i]) for i in range(len(terms))}

    print(f"  Polish done: loss={best_loss:.15e}, ~{stable_digits} stable digits")
    for t in terms:
        print(f"    {t:>8} = {polished[t]:.15f}")

    # --- Constant recognition ---
    recognition = {}
    try:
        recognition = run_constant_recognition(polished, stable_digits)
    except Exception as e:
        print(f"  Constant recognition failed: {e}")

    return {
        "params": polished,
        "loss_before": loss_before,
        "loss_after": best_loss,
        "stable_digits": stable_digits,
        "recognition": recognition,
    }


def run_constant_recognition(params, stable_digits):
    """Run PSLQ + mpmath.identify on polished coefficients."""
    try:
        from mpmath import mp, mpf, pslq, identify, pi, euler, log, sqrt, zeta
    except ImportError:
        print("  mpmath not available — skipping constant recognition")
        return {}

    if stable_digits < 8:
        print(f"  Only {stable_digits} stable digits — below PSLQ minimum (8).")
        print("  Constant recognition would hallucinate. Skipping.")
        return {"skipped": True, "reason": f"only {stable_digits} digits"}

    mp.dps = max(stable_digits + 10, 30)

    constants = {
        "1": mpf(1), "pi": pi, "pi^2": pi**2, "e": mp.e,
        "gamma": euler, "ln2": log(2), "sqrt2": sqrt(2),
        "sqrt3": sqrt(3), "zeta3": zeta(3), "1/(2pi)": 1/(2*pi),
        "2pi": 2*pi, "ln(2pi)": log(2*pi), "sqrt(2pi)": sqrt(2*pi),
    }

    results = {}
    for name, value in params.items():
        x = mpf(value)

        # Strategy 1: mpmath.identify
        ident = identify(x, tol=mpf(10)**(-(stable_digits-2)),
                        maxcoeff=1000, full=True)
        best_ident = min(ident, key=len) if ident else None

        # Strategy 2: PSLQ against constant basis
        basis_names = ["1", "pi", "e", "gamma", "ln2", "sqrt2", "zeta3"]
        basis_vals = [constants[n] for n in basis_names]
        rel = pslq([x] + basis_vals, maxcoeff=1000,
                   tol=mpf(10)**(-(stable_digits-3)))

        pslq_expr = None
        if rel is not None and rel[0] != 0:
            parts = []
            for i, bname in enumerate(basis_names):
                ci = rel[i+1]
                if ci == 0:
                    continue
                coeff = -ci / rel[0]
                if coeff == int(coeff):
                    coeff = int(coeff)
                parts.append(f"{coeff}*{bname}")
            pslq_expr = " + ".join(parts) if parts else None

        # Confidence
        confidence = "none"
        identity = pslq_expr or best_ident
        if rel is not None:
            max_c = max(abs(c) for c in rel)
            if max_c <= 10 and stable_digits >= 12:
                confidence = "high"
            elif max_c <= 50 and stable_digits >= 10:
                confidence = "medium"
            elif stable_digits >= 8:
                confidence = "low"
        elif best_ident:
            confidence = "medium" if stable_digits >= 12 else "low"

        results[name] = {
            "value": value,
            "identity": identity,
            "pslq_relation": [int(r) for r in rel] if rel else None,
            "identify_result": best_ident,
            "confidence": confidence,
        }

        tag = f"[{confidence}]" if identity else ""
        print(f"  {name:>8} = {value:.15f}  →  {identity or 'no match'} {tag}")

    return results


def fit_one_restart(target, ops, terms, n_params, n_steps, lr, device, dtype,
                     loss_type="mse", cv_lambda=0.0, target_cv=0.4519):
    """Single optimization restart.

    loss_type:
      "mse"    — standard MSE on first n_match eigenvalues (original)
      "mse_cv" — MSE + cv_lambda * (predicted_CV - target_CV)^2
                 Penalizes spacing variance mismatch with Riemann GUE.
                 Requires off-diagonal arithmetic terms in operator family
                 to actually generate level repulsion.

    cv_lambda: weight on the CV penalty (only used if loss_type='mse_cv').
               Default 0.0 means MSE-only even if loss_type='mse_cv'.
    target_cv: target spacing CV (Riemann GUE = 0.4519).
    """
    N = ops["I"].shape[0]
    n_match = len(target)

    params = torch.randn(n_params, device=device, dtype=dtype) * 0.5
    params[0] = 2.0 + torch.randn(1, device=device, dtype=dtype).item()
    params[-1] = 10.0 + torch.randn(1, device=device, dtype=dtype).item() * 5.0
    params.requires_grad_(True)

    opt = torch.optim.AdamW([params], lr=lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        opt, T_max=n_steps, eta_min=lr / 100
    )

    best_loss = float("inf")  # tracks MSE only for reporting consistency
    best_total = float("inf")  # tracks combined loss used for selection
    best_params = None
    best_eigs = None

    for step in range(n_steps):
        opt.zero_grad()
        try:
            H = make_hamiltonian(params, ops, terms)
            eigs, _ = torch.linalg.eigh(H)
        except Exception:
            break

        pred = eigs[:n_match]
        mse = torch.mean((pred - target) ** 2)

        # Optional CV (multi-objective) penalty
        if loss_type == "mse_cv" and cv_lambda > 0:
            spacings = pred[1:] - pred[:-1]
            sp_mean = spacings.mean()
            sp_std = spacings.std()
            pred_cv = sp_std / (sp_mean + 1e-9)
            cv_penalty = cv_lambda * (pred_cv - target_cv) ** 2
        else:
            cv_penalty = torch.tensor(0.0, device=device, dtype=dtype)

        # Coulomb repulsion (numerical regularizer, unchanged)
        n_rep = min(2 * n_match, N)
        diffs = eigs[:n_rep].unsqueeze(0) - eigs[:n_rep].unsqueeze(1)
        mask = 1.0 - torch.eye(n_rep, device=device, dtype=dtype)
        repulsion = torch.sum(mask / (diffs.abs() + 1e-6)) * 1e-8

        total = mse + cv_penalty + repulsion
        if torch.isnan(total):
            break
        total.backward()
        torch.nn.utils.clip_grad_norm_([params], 1.0)
        opt.step()
        scheduler.step()

        # Track BEST by combined objective (so multi-obj selects right basin),
        # but report MSE separately for cross-run comparison
        if total.item() < best_total:
            best_total = total.item()
            best_loss = mse.item()
            best_params = params.detach().clone()
            best_eigs = eigs[:n_match].detach().tolist()

    return best_loss, best_params, best_eigs


def run_search(
    zeros,
    n_matrix=250,
    n_restarts=50,
    n_steps=10000,
    lr=0.01,
    generators=None,
    device="cuda",
    dtype=torch.float64,
    loss_type="mse",
    cv_lambda=0.0,
):
    """Run the full grammar search across generator families."""
    if generators is None:
        generators = GENERATORS

    target = torch.tensor(zeros, device=device, dtype=dtype)
    ops = build_operators(n_matrix, device, dtype)

    print(f"\nOperator Search: {len(zeros)} zeros, N={n_matrix}, "
          f"{n_restarts} restarts, {n_steps} steps")
    print(f"Device: {device}, dtype: {dtype}")
    print("=" * 60)

    best_global_loss = float("inf")
    best_global_name = ""
    best_global_params = None
    best_global_eigs = None
    all_results = []

    for gen_name, gen_cfg in generators.items():
        terms = gen_cfg["terms"]
        n_params = gen_cfg["n_params"]
        print(f"\n  Generator: {gen_name} ({gen_cfg['desc']})")

        gen_best_loss = float("inf")
        gen_best_params = None
        gen_best_eigs = None
        t0 = time.time()

        for r in range(n_restarts):
            loss, params, eigs = fit_one_restart(
                target, ops, terms, n_params, n_steps, lr, device, dtype,
                loss_type=loss_type, cv_lambda=cv_lambda,
            )
            if loss < gen_best_loss:
                gen_best_loss = loss
                gen_best_params = params
                gen_best_eigs = eigs

            if (r + 1) % max(1, n_restarts // 5) == 0:
                print(f"    R{r+1:>3}/{n_restarts}: best_loss={gen_best_loss:.8f}")

        elapsed = time.time() - t0

        if gen_best_loss < best_global_loss:
            best_global_loss = gen_best_loss
            best_global_name = gen_name
            best_global_params = gen_best_params
            best_global_eigs = gen_best_eigs

        sp = np.diff(gen_best_eigs) if gen_best_eigs else [0]
        sp_var = np.std(sp) / np.mean(sp) if np.mean(sp) > 0 else 0

        # --- Spectral Form Factor metric (GP-125 post-ship gate) ---
        # K(t) = |Σ exp(i E_n t)|² / N. Unfold eigenvalues first.
        sff_l1 = None
        sff_target_samples = None
        sff_gen_samples = None
        if gen_best_eigs is not None and len(gen_best_eigs) >= len(zeros):
            try:
                eigs_arr = np.array(gen_best_eigs[:len(zeros)])
                eigs_sorted = np.sort(eigs_arr)
                unf_gen = (eigs_sorted - eigs_sorted[0]) / np.mean(np.diff(eigs_sorted))
                zeros_arr = np.array(zeros)
                zeros_sorted = np.sort(zeros_arr)
                unf_tgt = (zeros_sorted - zeros_sorted[0]) / np.mean(np.diff(zeros_sorted))
                t_grid = np.linspace(0.1, 15.0, 80)
                sff_tgt = np.abs(np.exp(1j * np.outer(t_grid, unf_tgt)).sum(axis=1)) ** 2 / len(unf_tgt)
                sff_gen = np.abs(np.exp(1j * np.outer(t_grid, unf_gen)).sum(axis=1)) ** 2 / len(unf_gen)
                sff_l1 = float(np.mean(np.abs(sff_gen - sff_tgt)))
                sample_ts = [1.0, 2.0, 4.0, 7.0, 10.0]
                sff_target_samples = {
                    f"t={t}": float(
                        np.abs(np.exp(1j * np.array([t]) * unf_tgt).sum()) ** 2 / len(unf_tgt)
                    ) for t in sample_ts
                }
                sff_gen_samples = {
                    f"t={t}": float(
                        np.abs(np.exp(1j * np.array([t]) * unf_gen).sum()) ** 2 / len(unf_gen)
                    ) for t in sample_ts
                }
            except Exception as sff_exc:
                sff_l1 = None

        result = {
            "generator": gen_name,
            "loss": gen_best_loss,
            "params": {t: float(gen_best_params[i]) for i, t in enumerate(terms)}
                      if gen_best_params is not None else {},
            "eig_range": [gen_best_eigs[0], gen_best_eigs[-1]]
                         if gen_best_eigs else [0, 0],
            "spacing_var": sp_var,
            "sff_l1": sff_l1,
            "sff_target_samples": sff_target_samples,
            "sff_gen_samples": sff_gen_samples,
            "time_seconds": round(elapsed, 1),
        }
        all_results.append(result)
        print(f"    BEST: loss={gen_best_loss:.8f}, range=[{result['eig_range'][0]:.2f}, "
              f"{result['eig_range'][1]:.2f}], spvar={sp_var:.4f}, time={elapsed:.1f}s")

    # Target spacing stats
    tsp = np.diff(zeros)
    target_sp_var = np.std(tsp) / np.mean(tsp)

    # Print final summary
    print("\n" + "=" * 60)
    print(f"BEST OVERALL: {best_global_name}, loss={best_global_loss:.10f}")
    print(f"Target spacing var: {target_sp_var:.4f}")
    print(f"\nCoefficients (15 digits):")
    terms = GENERATORS[best_global_name]["terms"]
    for i, term in enumerate(terms):
        val = float(best_global_params[i])
        print(f"  {term:>8} = {val:.15f}")

    print(f"\nFirst 10 eigenvalues vs zeros:")
    for i in range(min(10, len(zeros))):
        err = abs(best_global_eigs[i] - zeros[i])
        print(f"  eig[{i:>2}] = {best_global_eigs[i]:>14.8f}  "
              f"zero[{i:>2}] = {zeros[i]:>14.8f}  err = {err:.8f}")

    # Save results
    output = {
        "best_generator": best_global_name,
        "best_loss": best_global_loss,
        "best_params": {t: float(best_global_params[i]) for i, t in enumerate(terms)},
        "eigenvalues": best_global_eigs,
        "target_zeros": zeros,
        "target_spacing_var": target_sp_var,
        "all_results": all_results,
        "config": {
            "n_matrix": n_matrix,
            "n_restarts": n_restarts,
            "n_steps": n_steps,
            "device": str(device),
        },
    }
    with open("riemann_operator_result.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to riemann_operator_result.json")

    # --- Precision polish + constant recognition ---
    # Only fires if loss < 0.01 (manifold is viable)
    if best_global_loss < 0.01:
        print("\n" + "=" * 60)
        print("LOSS < 0.01 — Running precision polish + constant recognition")
        print("=" * 60)
        polish_result = precision_polish(
            params_init=best_global_params,
            ops=ops,
            terms=terms,
            target_tensor=target,
            n_steps=2000,
            device=device,
        )
        output["polish"] = polish_result

        with open("riemann_operator_result.json", "w") as f:
            json.dump(output, f, indent=2)
        print("Updated results saved with polish + recognition data")
    else:
        print(f"\nLoss {best_global_loss:.6f} > 0.01 — skipping precision polish.")
        print("Expand grammar or increase restarts before constant recognition.")

    return output


def main():
    parser = argparse.ArgumentParser(description="Riemann Operator Search")
    parser.add_argument("--n-zeros", type=int, default=50)
    parser.add_argument("--n-matrix", type=int, default=250)
    parser.add_argument("--restarts", type=int, default=50)
    parser.add_argument("--steps", type=int, default=10000)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--zeros-file", type=str, default=None,
                        help="JSON file with precomputed zeros")
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--dtype", choices=["float32", "float64"], default="float64",
                        help="Precision for operator construction and eigh. "
                             "float32 is ~3-5× faster on A10/A100 but may be less stable "
                             "for near-degenerate eigenvalues.")
    parser.add_argument("--loss-type", choices=["mse", "mse_cv"], default="mse",
                        help="Loss function: mse (original) or mse_cv "
                             "(MSE + lambda * (predicted_CV - target_CV)^2)")
    parser.add_argument("--cv-lambda", type=float, default=0.0,
                        help="Weight on CV penalty (only used if --loss-type mse_cv)")
    args = parser.parse_args()

    # Device selection
    if args.cpu:
        device = "cpu"
    elif torch.cuda.is_available():
        device = "cuda"
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "cpu"  # eigh doesn't support MPS backward
    else:
        device = "cpu"

    # Load zeros
    if args.zeros_file:
        data = json.load(open(args.zeros_file))
        if isinstance(data, dict) and "zeros" in data:
            zeros = data["zeros"][:args.n_zeros]
        elif isinstance(data, list):
            zeros = data[:args.n_zeros]
        else:
            zeros = compute_riemann_zeros(args.n_zeros)
    else:
        zeros = compute_riemann_zeros(args.n_zeros)

    print(f"Zeros loaded: {len(zeros)} values, {zeros[0]:.4f} to {zeros[-1]:.4f}")

    dtype = torch.float32 if args.dtype == "float32" else torch.float64
    print(f"Using dtype: {dtype}")

    run_search(
        zeros=zeros,
        n_matrix=args.n_matrix,
        n_restarts=args.restarts,
        n_steps=args.steps,
        lr=args.lr,
        device=device,
        dtype=dtype,
        loss_type=args.loss_type,
        cv_lambda=args.cv_lambda,
    )


if __name__ == "__main__":
    main()
