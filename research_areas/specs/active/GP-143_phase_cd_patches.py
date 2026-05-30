"""GP-143 PHASE C / PHASE D reference patches for autoresearch_loop.py.

This file is SPEC-LEVEL. It is NOT applied to autoresearch_loop.py. Per
INV-10, these patches land only after seam + spec convergence and the
gp140 promotion gate clears. They are version-controlled here so reviewers
can see the exact proposed edits before an implementation PR.

Each section below corresponds to an exact-line patch location in
src/ztare/validator/autoresearch_loop.py as of 2026-04-24. Line numbers
drift with upstream edits; grep anchors are provided to rediscover
locations on implementation day.
"""
from __future__ import annotations

# ============================================================================
# PATCH 1: module-level import (near top of autoresearch_loop.py, ~line 60)
# ============================================================================
# Grep anchor: "from src.ztare.gates.derived_constraints import"
# Add AFTER the existing gates import:

PATCH_1_IMPORT = """
from src.ztare.gates.wasserstein_persistence_gate import (
    run_gate as _run_wasserstein_persistence_gate,
    filter_per_candidate_for_mutator_prompt as _filter_wasserstein_for_mutator,
)
"""


# ============================================================================
# PATCH 2: rubric validator (in src/ztare/rubrics/review_rubric.py; fires
# before autoresearch_loop main()). Grep anchor: "def review_rubric"
# ============================================================================

PATCH_2_RUBRIC_VALIDATOR = """
def _validate_dynamical_lattice_block(rubric: dict) -> list[str]:
    '''GP-143: validate dynamical_lattice rubric block.

    Returns list of validation errors (empty if valid).
    '''
    if rubric.get('fit_score_mode') != 'dynamical_lattice':
        return []
    errors = []
    dl = rubric.get('dynamical_lattice')
    if not isinstance(dl, dict):
        return ['fit_score_mode=dynamical_lattice requires a dynamical_lattice block']
    required = ('substrate_class', 'observation_dt', 'observation_T',
                'method_a_variant')
    for key in required:
        if key not in dl:
            errors.append(f'dynamical_lattice missing required key: {key}')
    # Threshold route: either wasserstein_noise_floor OR
    # (noise_envelope_sigma + observation_T) must be present.
    has_floor = 'wasserstein_noise_floor' in dl
    has_sigma = 'noise_envelope_sigma' in dl
    if not (has_floor or has_sigma):
        errors.append(
            'dynamical_lattice requires either wasserstein_noise_floor '
            '(calibrated floor route) or noise_envelope_sigma (Fasy fallback)'
        )
    from src.ztare.fit.continuous_chaotic import METHOD_A_REGISTRY
    if dl.get('method_a_variant') not in METHOD_A_REGISTRY:
        errors.append(
            f'unknown method_a_variant: {dl.get(\"method_a_variant\")}; '
            f'valid: {sorted(METHOD_A_REGISTRY)}'
        )
    # Component D incompatibility guard (seam OQ-5)
    if rubric.get('enable_component_d'):
        errors.append(
            'GP-143: enable_component_d is incompatible with '
            'dynamical_lattice; disable in rubric'
        )
    return errors
"""


# ============================================================================
# PATCH 3: PHASE C bifurcation (autoresearch_loop.py, ~line 3070)
# Grep anchor: "# PHASE C" or the first occurrence of fit_parameters(...)
# call inside main(). Insert the if-else block BEFORE the existing call.
# ============================================================================

PATCH_3_PHASE_C = """
# GP-143: dynamical_lattice bifurcation (continuous-chaotic substrate)
if rubric_data.get('fit_score_mode') == 'dynamical_lattice':
    from src.ztare.fit.continuous_chaotic import run_pipeline as _run_cc_pipeline
    cc_params = rubric_data['dynamical_lattice']
    trajectory, initial_state = _load_dynamical_lattice_holdout(
        PROJECT_DIR, cc_params
    )
    cc_result = _run_cc_pipeline(
        trajectory=trajectory,
        dt=cc_params['observation_dt'],
        rubric_params=cc_params,
        holdout_path=Path(PROJECT_DIR) / '_holdout_locked',
        initial_state=initial_state,
    )
    _fit_result = _adapt_cc_result_to_fit_result(cc_result)
    # Mutator-visibility boundary (seam Round 3 MA): inject filtered view
    _fit_result_for_mutator = _filter_wasserstein_for_mutator(
        _fit_result.gate_result
    )
else:
    # legacy path (scalar-function substrate) — unchanged
    _fit_result = fit_parameters(...)  # existing call site
    _fit_result_for_mutator = None
"""


# ============================================================================
# PATCH 4: PHASE D INV-3 deterministic test_model.py writer
# Grep anchor: "INV-3" or "# PHASE D" or "test_model.py" writer block.
# ============================================================================

PATCH_4_PHASE_D = '''
def _write_cc_test_model_py(
    project_dir: Path,
    cc_result: 'ContinuousChaoticResult',
    rubric_params: dict,
) -> None:
    """GP-143 PHASE D INV-3 writer.

    Emits a deterministic test_model.py that replays the Wasserstein-
    persistence gate against the designated champion. No LLM authors any
    function body; INV-3 compliant by construction.
    """
    champion = cc_result.champion
    if champion is None:
        return
    import json as _j
    # Persist certified subset for test_model.py to load
    (project_dir / 'certified_subset.json').write_text(
        _j.dumps([c.__dict__ for c in cc_result.certified_subset], indent=2)
    )
    template = """
# AUTO-GENERATED by GP-143 PHASE D INV-3 writer. Do not edit by hand.
import hashlib
import json
from pathlib import Path

import numpy as np


def test_champion_certified():
    here = Path(__file__).parent
    certified = json.loads((here / 'certified_subset.json').read_text())
    champion = next(c for c in certified if c['candidate_id'] == {champion_id!r})

    # Hash-commitment replay FIRST (seam OQ-4)
    payload = {{k: v for k, v in champion.items() if k != 'sha256_commitment'}}
    computed = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    assert computed == champion['sha256_commitment'], \\
        'hash_commitment_violation: candidate mutated post-emission'

    # Gate verdict replay
    from src.ztare.gates.wasserstein_persistence_gate import run_gate
    holdout = np.load(here / '_holdout_locked' / 'trajectories' / 'traj_5.npy')
    ic = np.array([1.0, 1.0, 1.0])  # TODO: pull from truth.json
    result = run_gate(
        [champion],
        holdout,
        {rubric_params!r},
        ic,
        {dt!r},
    )
    assert result['passed'], f'gate verdict replay failed: {{result[\"reason\"]}}'


if __name__ == '__main__':
    test_champion_certified()
    print('GP-143 PHASE D replay: PASS')
""".format(
        champion_id=champion.candidate_id,
        rubric_params=rubric_params,
        dt=rubric_params['observation_dt'],
    )
    (project_dir / 'test_model.py').write_text(template)
'''


# ============================================================================
# PATCH 5: FitResult shape extension (OQ-2 resolution)
# Grep anchor: class FitResult or dataclass definition for FitResult.
# ============================================================================

PATCH_5_FITRESULT = """
@dataclass
class FitResult:
    # ... existing fields ...
    coefficients: dict[str, float]
    residual: float
    # ... etc ...

    # GP-143 extensions (optional; legacy consumers ignore)
    certified_subset: Optional[list[dict]] = None
    gate_result: Optional[dict] = None
    method_a_variant: Optional[str] = None
"""


if __name__ == '__main__':
    print(__doc__)
    for name, patch in [
        ('PATCH_1_IMPORT', PATCH_1_IMPORT),
        ('PATCH_2_RUBRIC_VALIDATOR', PATCH_2_RUBRIC_VALIDATOR),
        ('PATCH_3_PHASE_C', PATCH_3_PHASE_C),
        ('PATCH_4_PHASE_D', PATCH_4_PHASE_D),
        ('PATCH_5_FITRESULT', PATCH_5_FITRESULT),
    ]:
        print(f'\n===== {name} =====')
        print(patch)
