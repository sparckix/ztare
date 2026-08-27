"""Independent symbolic binding for Newton-style investment candidates."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

import sympy as sp


class LagrangianBindingError(ValueError):
    pass


def verify_newton_lagrangian_binding(module: Any, params: dict[str, float]) -> dict[str, Any]:
    """Derive an action's response surface and bind it to executable functions."""
    q_variables = list(getattr(module, "Q_VARIABLES", ()))
    if q_variables != ["q"]:
        raise LagrangianBindingError("Newton binding requires Q_VARIABLES = ['q']")

    background = list(getattr(module, "BACKGROUND", ()))
    parameter_names = list(getattr(module, "PARAMETER_NAMES", ()))
    if set(params) != set(parameter_names):
        raise LagrangianBindingError("calibrated parameters do not match PARAMETER_NAMES")

    names = ["q", *background, *parameter_names]
    symbols = {name: sp.Symbol(name, real=True) for name in names}
    action = sp.sympify(module.LAGRANGIAN, locals=symbols)
    substitutions = dict(getattr(module, "LAGRANGIAN_SUBSTITUTIONS", {}))
    for name, expression in substitutions.items():
        replacement = sp.sympify(expression, locals=symbols)
        unknown = replacement.free_symbols - set(symbols.values())
        if unknown:
            raise LagrangianBindingError(
                f"Lagrangian substitution {name!r} has undeclared symbols: "
                + ", ".join(sorted(str(value) for value in unknown))
            )
        action = action.subs(sp.Symbol(name), replacement)

    allowed = set(symbols.values())
    unknown = action.free_symbols - allowed
    if unknown:
        raise LagrangianBindingError(
            "Lagrangian has undeclared symbols: "
            + ", ".join(sorted(str(value) for value in unknown))
        )

    q = symbols["q"]
    gradient = sp.simplify(sp.diff(action, q))
    curvature = sp.simplify(sp.diff(gradient, q))
    roots = sp.solve(gradient, q, dict=False)
    if len(roots) != 1:
        raise LagrangianBindingError(
            f"Newton binding requires one symbolic stationary response; found {len(roots)}"
        )
    stationary = sp.simplify(roots[0])

    values = {symbols[name]: float(params[name]) for name in parameter_names}
    max_error = {"stationary_response": 0.0, "action_gradient": 0.0, "action_curvature": 0.0}
    sample_count = 0
    for force in (-0.4, -0.1, 0.0, 0.1, 0.4):
        for local_mass in (0.0, 0.05, 0.2):
            state = {
                **values,
                symbols["force"]: force,
                symbols["local_mass"]: local_mass,
            }
            derived_response = float(stationary.subs(state).evalf())
            executable_response = float(module.stationary_response(force, local_mass, params))
            max_error["stationary_response"] = max(
                max_error["stationary_response"], abs(derived_response - executable_response)
            )
            for response in (derived_response, derived_response * 0.75, derived_response + 0.01):
                point = {**state, q: response}
                derived_gradient = float(gradient.subs(point).evalf())
                derived_curvature = float(curvature.subs(point).evalf())
                executable_gradient = float(
                    module.action_gradient(response, force, local_mass, params)
                )
                executable_curvature = float(
                    module.action_curvature(response, local_mass, params)
                )
                max_error["action_gradient"] = max(
                    max_error["action_gradient"], abs(derived_gradient - executable_gradient)
                )
                max_error["action_curvature"] = max(
                    max_error["action_curvature"], abs(derived_curvature - executable_curvature)
                )
                sample_count += 1

    passed = all(math.isfinite(value) and value <= 1e-10 for value in max_error.values())
    canonical = {
        "action": sp.sstr(action),
        "gradient": sp.sstr(gradient),
        "curvature": sp.sstr(curvature),
        "stationary_response": sp.sstr(stationary),
    }
    return {
        "schema": "ztare-newton-lagrangian-binding-v1",
        "passed": passed,
        "canonical": canonical,
        "derivation_sha256": hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "sample_count": sample_count,
        "max_absolute_error": max_error,
        "candidate_functions_are_derivation_authority": False,
    }
