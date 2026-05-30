from pathlib import Path
import importlib.util
import sys


SCRIPT_PATH = Path(
    "projects/ns_millennium_hunt/scripts/"
    "fresh_annular_innovation_residual_witness.py"
).resolve()


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "fresh_annular_innovation_residual_witness",
        SCRIPT_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_positive_innovation_can_still_be_scalar_and_post_payoff() -> None:
    module = _load_module()
    witness = module.build_witness(n_terms=12, ratio=0.5, epsilon=0.2)

    assert witness.innovation_part_present is True
    assert witness.innovation_mass_lower_bound_positive is True
    assert witness.same_source_binding_present is True
    assert witness.innovation_zero_mean_on_invoice_bins is True
    assert witness.pointwise_payment_ok is True
    assert witness.prefix_budget_ok is True
    assert witness.monotone_tail_compatible is True
    assert witness.scalar_measure_compatible is True
    assert witness.uniform_enstrophy_disguise_compatible is True
    assert witness.source_can_still_be_declared_after_payoff is True
    assert witness.non_disguise_morphology_forced is False
    assert witness.source_nondeclaration_timing_forced is False
