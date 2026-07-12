"""Optional batch-prediction protocol for leaf carriers (GP-250).

Leaf carriers that can predict multiple states in a single forward pass may
expose:

    predict_batch(states_uint8_array: np.ndarray, action: int) -> np.ndarray

where:
- `states_uint8_array` is shape (N, H, W) uint8.
- `action` is an int action index (same semantics as the scalar predict call).
- returns shape (N, H, W) uint8 predicted next states.

Carriers that do NOT expose predict_batch are not penalised — this is a
performance hint, never a requirement. The fallback path (per-state predict via
the frontier_codec) is always used when the hook is absent.

Usage (planner / frontier expansion):

    from ztare.worldmodel.batch_transition import predict_batch_or_fallback

    next_arrays = predict_batch_or_fallback(carrier, state_arrays, action, codec)

ponytail: protocol = duck-typed attribute check; no ABC, no registration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ztare.worldmodel.frontier_codec import StateInterner

    Grid = tuple[tuple[int, ...], ...]


def predict_batch_or_fallback(
    carrier,
    states: "np.ndarray",  # (N, H, W) uint8
    action: int,
    step: int,
    *,
    codec_array_to_grid,  # frontier_codec.array_to_grid
    codec_grid_to_array,  # frontier_codec.grid_to_array
) -> "list[np.ndarray | None]":
    """Run batch prediction if carrier supports it; else fall back per-state.

    Returns a list of length N: each element is either:
    - np.ndarray (H, W) uint8 for the predicted next state, or
    - None if the carrier returned None for that state (inadmissible transition).

    `step` is passed to the per-state fallback (predict(grid, action, step)).
    Batch carriers receive it as-is; they may ignore it if stateless.
    """
    n = len(states)
    if n == 0:
        return []

    # Fast path: carrier exposes predict_batch
    if hasattr(carrier, "predict_batch"):
        try:
            result = carrier.predict_batch(states, action)  # (N, H, W) or ragged
            if result is not None and hasattr(result, "__len__") and len(result) == n:
                return [
                    np.asarray(r, dtype=np.uint8) if r is not None else None
                    for r in result
                ]
        except Exception:
            pass  # ponytail: silent fallback — batch is optional, never load-bearing

    # Fallback: per-state predict via codec round-trip
    # carrier must have a __call__(grid, action, step) -> Grid | None interface
    out = []
    for i in range(n):
        grid = codec_array_to_grid(states[i])
        try:
            nxt = carrier(grid, action, step)
        except Exception:
            nxt = None
        if nxt is None:
            out.append(None)
        else:
            out.append(codec_grid_to_array(nxt))
    return out
