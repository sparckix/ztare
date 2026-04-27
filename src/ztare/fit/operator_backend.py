"""GP-125: Differentiable Topology Backend for ZTARE.

Replaces curve_fit with PyTorch eigenvalue optimization for
operator discovery. The LLM proposes the STRUCTURE of a matrix
generator. This backend fits the PARAMETERS via gradient descent
on eigenvalue MSE.

The discovery: a low-complexity generator whose eigenvalues match
a target spectrum IS the operator (e.g., Hilbert-Pólya for RH).

Usage:
    from src.ztare.fit.operator_backend import fit_operator
    result = fit_operator(
        generator_fn=berry_keating_generator,
        target_spectrum=riemann_zeros[:100],
        n_params=5,
        n_steps=1000,
    )
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import torch


@dataclass
class OperatorResult:
    """Result of operator fitting."""
    loss: float
    params: dict[str, float]
    n_steps: int
    eigenvalues: list[float]
    converged: bool
    time_seconds: float


def spectral_berry_keating_generator(params: torch.Tensor, N: int) -> torch.Tensor:
    """Generate Berry-Keating Hamiltonian in the harmonic oscillator basis.

    Uses creation/annihilation operators (a, a†) instead of spatial grid.
    This eliminates the "infinite fall" problem of spatial discretization.

    x = (a + a†) / sqrt(2)
    p = -i(a - a†) / sqrt(2)
    H = xp + px + V(x; params)

    The matrix is structurally exact — no edge artifacts.

    params[0] = scale factor for xp+px
    params[1] = x^2 coefficient (harmonic confinement)
    params[2] = x^4 coefficient (anharmonic correction)
    params[3] = x^6 coefficient (higher-order correction)
    params[4] = overall energy shift
    """
    # Build creation/annihilation operators in complex dtype
    a_dag = torch.zeros(N, N, dtype=torch.complex64)
    for j in range(N - 1):
        a_dag[j, j + 1] = (j + 1) ** 0.5

    a = a_dag.T.clone()

    # Position and momentum in oscillator basis (complex)
    x_op = (a + a_dag) / (2 ** 0.5)
    p_op = -1j * (a - a_dag) / (2 ** 0.5)

    # xp + px (Hermitian: result should be real)
    xp_px = x_op @ p_op + p_op @ x_op
    H_kinetic = xp_px.real * params[0]

    # Polynomial potential V(x) = c2*x^2 + c4*x^4 + c6*x^6
    x2 = (x_op @ x_op).real
    x4 = (x2 @ x2)
    x6 = (x4 @ x2)

    V = params[1] * x2 + params[2] * x4 + params[3] * x6

    # Total Hamiltonian
    H = H_kinetic + V + params[4] * torch.eye(N)

    # Ensure Hermitian (should already be, but numerical safety)
    H = (H + H.T) / 2

    return H


def berry_keating_generator(params: torch.Tensor, N: int) -> torch.Tensor:
    """Generate a Berry-Keating-style Hamiltonian.

    H = x·p + p·x + V(x; params)

    Discretized on a grid of N points. The potential V(x) is
    parameterized by the input params tensor.

    params[0] = overall scale
    params[1] = boundary condition parameter
    params[2] = potential depth
    params[3] = potential width
    params[4] = asymmetry parameter
    """
    # Discretize on [0, L] with L determined by params
    L = 10.0 + params[0].abs() * 5.0
    dx = L / N
    x = torch.linspace(dx / 2, L - dx / 2, N)

    # Kinetic term: p = -i d/dx, discretized as tridiagonal
    # xp + px = -i(x d/dx + d/dx x) = -i(2x d/dx + 1)
    # Discretize d/dx as centered difference
    diag = torch.zeros(N)
    off_diag = torch.zeros(N - 1)

    for j in range(N):
        diag[j] = x[j] * 0  # diagonal of xp+px is zero for Hermitian form

    for j in range(N - 1):
        # Off-diagonal: (x_{j+1} + x_j) / (2 dx)
        off_diag[j] = (x[j + 1] + x[j]) / (2 * dx)

    # Build the kinetic matrix (symmetric tridiagonal)
    H = torch.diag(diag) + torch.diag(off_diag, 1) + torch.diag(off_diag, -1)

    # Potential V(x) = params[2] * exp(-(x - params[3])^2 / params[4]^2)
    V_depth = params[2]
    V_center = params[3].abs() * L / 2
    V_width = params[4].abs() + 0.1  # prevent zero width
    V = V_depth * torch.exp(-((x - V_center) ** 2) / (V_width ** 2))

    # Add boundary condition modification
    bc = params[1]
    V[0] += bc
    V[-1] += bc

    H = H + torch.diag(V)

    # Ensure Hermitian
    H = (H + H.T) / 2

    return H


def fit_operator(
    target_spectrum: list[float] | np.ndarray,
    n_matrix: int = 200,
    n_params: int = 5,
    n_steps: int = 1000,
    lr: float = 0.01,
    generator_fn=None,
    verbose: bool = True,
) -> OperatorResult:
    """Fit an operator's eigenvalues to a target spectrum via gradient descent.

    The generator function takes a parameter tensor and matrix size N,
    returns an N×N Hermitian matrix. The optimizer adjusts the parameters
    to minimize MSE between the matrix's eigenvalues and the target spectrum.

    Args:
        target_spectrum: The target eigenvalues to match (e.g., Riemann zeros)
        n_matrix: Size of the matrix (N×N)
        n_params: Number of generator parameters
        n_steps: Gradient descent steps
        lr: Learning rate
        generator_fn: Function(params, N) → N×N Hermitian tensor.
                      Defaults to Berry-Keating generator.
        verbose: Print progress
    """
    if generator_fn is None:
        generator_fn = berry_keating_generator

    target = torch.tensor(target_spectrum[:n_matrix], dtype=torch.float32)
    n_target = len(target)

    # Initialize parameters
    params = torch.randn(n_params, dtype=torch.float32) * 0.1
    params.requires_grad_(True)

    optimizer = torch.optim.AdamW([params], lr=lr, weight_decay=0.01)

    if verbose:
        print(f"  🔬 Operator backend: fitting {n_params} params to {n_target} eigenvalues")
        print(f"  🔬 Matrix size: {n_matrix}×{n_matrix}, steps: {n_steps}")

    t0 = time.time()
    best_loss = float("inf")
    best_params = params.detach().clone()

    for step in range(n_steps):
        optimizer.zero_grad()

        # Generate matrix from parameters
        try:
            H = generator_fn(params, n_matrix)
        except Exception:
            break

        # Compute eigenvalues (sorted ascending)
        try:
            eigenvalues, _ = torch.linalg.eigh(H)
        except Exception:
            break

        # Match the lowest n_target eigenvalues to the target
        # Sort target and predicted, compute MSE
        pred = eigenvalues[:n_target]
        loss = torch.mean((pred - target) ** 2)

        # Complexity penalty (L2 on params = weight decay already handles)
        complexity = torch.mean(H ** 2) * 0.001

        # GP-125: Coulomb repulsion penalty — prevents eigenvalue degeneracy
        # which causes eigh backward pass to explode (1/(λ_i - λ_j) → ∞).
        # Acts as electrostatic repulsion keeping eigenvalues separated.
        diffs = eigenvalues.unsqueeze(0) - eigenvalues.unsqueeze(1)
        # Mask diagonal (self-interaction)
        mask = 1.0 - torch.eye(len(eigenvalues))
        # Regularized inverse: 1/(|diff| + epsilon) to avoid division by zero
        repulsion = torch.sum(mask / (diffs.abs() + 1e-6)) * 1e-5

        total_loss = loss + complexity + repulsion

        if torch.isnan(total_loss):
            if verbose:
                print(f"    Step {step}: NaN loss, stopping")
            break

        total_loss.backward()
        torch.nn.utils.clip_grad_norm_([params], max_norm=1.0)
        optimizer.step()

        if loss.item() < best_loss:
            best_loss = loss.item()
            best_params = params.detach().clone()

        if verbose and (step % 200 == 0 or step == n_steps - 1):
            print(f"    Step {step}: loss={float(loss):.6f}, "
                  f"complexity={float(complexity):.6f}")

    elapsed = time.time() - t0

    # Get final eigenvalues with best params
    with torch.no_grad():
        H_best = generator_fn(best_params, n_matrix)
        final_eigs, _ = torch.linalg.eigh(H_best)

    result = OperatorResult(
        loss=best_loss,
        params={f"p{i}": float(best_params[i]) for i in range(n_params)},
        n_steps=n_steps,
        eigenvalues=final_eigs[:n_target].tolist(),
        converged=best_loss < 0.01,
        time_seconds=round(elapsed, 1),
    )

    if verbose:
        print(f"  🔬 Operator fit: loss={best_loss:.6f}, "
              f"converged={result.converged}, time={elapsed:.1f}s")

    return result


def fit_riemann_operator(
    n_zeros: int = 100,
    n_matrix: int = 200,
    n_steps: int = 2000,
    verbose: bool = True,
) -> OperatorResult:
    """Attempt to find an operator whose eigenvalues match the Riemann zeros.

    This is the GP-125 Millennium experiment: can gradient descent on a
    parameterized Hermitian matrix find the Hilbert-Pólya operator?
    """
    # Load Riemann zeros
    from mpmath import zetazero
    if verbose:
        print(f"  Loading {n_zeros} Riemann zeros...")
    zeros = [float(zetazero(k).imag) for k in range(1, n_zeros + 1)]

    if verbose:
        print(f"  Zeros loaded: t_1={zeros[0]:.4f} to t_{n_zeros}={zeros[-1]:.4f}")

    return fit_operator(
        target_spectrum=zeros,
        n_matrix=n_matrix,
        n_params=5,
        n_steps=n_steps,
        generator_fn=berry_keating_generator,
        verbose=verbose,
    )
