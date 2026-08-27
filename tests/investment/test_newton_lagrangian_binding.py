from pathlib import Path
import importlib.util

from ztare.investment.newton_lagrangian_binding import verify_newton_lagrangian_binding


def test_candidate_functions_are_bound_to_independent_action_derivation():
    path = Path("projects/jaggedthoughts_probability_current_newton/test_model.py")
    spec = importlib.util.spec_from_file_location("newton_candidate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    params = module.fit_model([])

    assert verify_newton_lagrangian_binding(module, params)["passed"] is True
    original = module.action_gradient
    module.action_gradient = lambda *args: original(*args) + 0.01
    assert verify_newton_lagrangian_binding(module, params)["passed"] is False
