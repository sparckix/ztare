"""Binomial-message spectrum for the selected quasicyclic graph family."""
from __future__ import annotations

from itertools import product
import json

from qc_graph_family_oracle import (
    G,
    canonical_shift_orbit,
    multiply_mod_x25_minus_one,
    phase_mask,
)
from ztare.leanmill.theory_ir import content_hash


representatives: dict[int, int] = {}
for raw in product(range(5), repeat=5):
    canonical, orbit = canonical_shift_orbit(phase_mask(tuple(raw)))
    if len(orbit) != 25:
        raise AssertionError("autocorrelation screen crossed the shift quotient")
    representatives[canonical] = representatives.get(canonical, 0) + 1

if len(representatives) != 125 or set(representatives.values()) != {25}:
    raise AssertionError("autocorrelation screen did not recover the exact domain")

members = []
for canonical_a in sorted(representatives):
    second_seed = multiply_mod_x25_minus_one(G, canonical_a)
    spectrum = []
    for shift in range(1, 20):
        message = 1 | (1 << shift)
        first = multiply_mod_x25_minus_one(G, message)
        second = multiply_mod_x25_minus_one(second_seed, message)
        spectrum.append(
            {
                "shift": shift,
                "message_hex": f"0x{message:05x}",
                "first_block_weight": first.bit_count(),
                "second_block_weight": second.bit_count(),
                "total_weight": first.bit_count() + second.bit_count(),
            }
        )
    minimum = min(row["total_weight"] for row in spectrum)
    killing = [row for row in spectrum if row["total_weight"] == minimum]
    core = {
        "schema": "axiompack.qc_binomial_spectrum_member.v1",
        "parameter_id": f"a25:0x{canonical_a:07x}",
        "canonical_multiplier_hex": f"0x{canonical_a:07x}",
        "spectrum": spectrum,
        "minimum_binomial_weight": minimum,
        "margin_from_target": minimum - 14,
        "minimizers": killing,
        "status": "binomial_killed" if minimum < 14 else "exact_replay_residual",
    }
    members.append({**core, "receipt_sha256": content_hash(core)})

residuals = [row for row in members if row["status"] == "exact_replay_residual"]
core = {
    "schema": "axiompack.qc_binomial_spectrum.v1",
    "family_id": "qc-graph-g-1-plus-x5-two-separated-phases",
    "parameter_count": len(members),
    "shift_domain": list(range(1, 20)),
    "members": members,
    "binomial_killed_count": len(members) - len(residuals),
    "residual_count": len(residuals),
    "residual_parameter_ids": [row["parameter_id"] for row in residuals],
    "claim_scope": "binomial_message_screen_only_exact_residuals_remain_unclassified",
    "authority": "deterministic_quasicyclic_autocorrelation_screen",
}
print(json.dumps({**core, "receipt_sha256": content_hash(core)}, sort_keys=True))
