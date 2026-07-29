#!/usr/bin/env python3
"""Seventh-order obstruction over a complete fixed-bound prefix family."""
from __future__ import annotations

import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from gauge_bound_six_extension import build_through_six  # noqa: E402
from gauge_bound_six_obstruction import (  # noqa: E402
    fixed_bound_obstruction,
)


def run(
    bound: int = 9, *, compute_groebner: bool = True
) -> dict[str, object]:
    result = fixed_bound_obstruction(
        family=build_through_six(bound),
        order=7,
        bound=bound,
        parameter_key="complete_parameters_through_six",
        compute_groebner=compute_groebner,
    )
    return {
        "schema": "axiompack.jacobian_fixed_bound_seven_obstruction.v1",
        **result,
        "complete_dimension_through_six": result[
            "complete_lower_dimension"
        ],
        "seventh_residual_component_degrees": result[
            "residual_component_degrees"
        ],
        "seventh_residual_parameter_degree": result[
            "residual_parameter_degree"
        ],
        "seventh_residual_parameter_monomial_count": result[
            "residual_parameter_monomial_count"
        ],
        "seventh_image_rank": result["image_rank"],
        "seventh_image_plus_residual_rank": result[
            "image_plus_residual_rank"
        ],
        "seventh_quotient_dimension": result["quotient_dimension"],
        "seventh_target_window": result["target_window"],
    }


if __name__ == "__main__":
    selected_bound = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    use_groebner = "--no-groebner" not in sys.argv[2:]
    print(json.dumps(
        run(selected_bound, compute_groebner=use_groebner),
        indent=2,
        sort_keys=True,
    ))
