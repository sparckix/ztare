"""Tests for orchestrator/prompt.py (GP-157 v5.0 Phase 4d).

Pin down the substrate-contract-hint selector. Surfaced by gp159
mutator-empty-Python failure (other agent diagnosis 2026-04-25):
custom-substrate without fit primitive has no contract instruction in
the standard mutator prompt.
"""

from __future__ import annotations

import pytest

from pathlib import Path

from src.ztare.orchestrator.prompt import (
    needs_override_contract_hint,
    needs_scalar_contract_hint,
    select_substrate_contract_hint,
    verify_class_consistency_with_substrate,
    verify_convention_bridge_in_form,
)


class TestNeedsOverrideContractHint:
    def test_legacy_no_cage_meta(self):
        assert needs_override_contract_hint({}) is False

    def test_legacy_class_1d(self):
        assert needs_override_contract_hint({"cage_meta": {"class": "1d"}}) is False

    def test_fit_primitive_enabled_blocks_hint(self):
        assert needs_override_contract_hint({
            "enable_fit_primitive": True,
            "cage_meta": {"class": "nd_features"},
        }) is False

    def test_fit_primitive_features_enabled_blocks_hint(self):
        assert needs_override_contract_hint({
            "enable_fit_primitive_features": True,
            "cage_meta": {"class": "nd_features"},
        }) is False

    def test_nd_features_with_no_fit_primitive_triggers(self):
        result = needs_override_contract_hint({
            "enable_fit_primitive": False,
            "enable_fit_primitive_features": False,
            "cage_meta": {"class": "nd_features"},
        })
        assert result is True

    @pytest.mark.parametrize(
        "non_nd_class",
        ["audit", "literature", "proof_target"],
    )
    def test_audit_literature_proof_target_no_longer_get_override_hint(self, non_nd_class):
        # NARROWED 2026-04-25: these substrates do NOT use the
        # I_model(features) contract — audit scores on critique, literature
        # on prose, proof_target on Lean tactics. The feature-dict hint
        # was being injected wrongly for them; now silent.
        result = needs_override_contract_hint({
            "cage_meta": {"class": non_nd_class},
        })
        assert result is False

    def test_unknown_class_no_hint(self):
        # Defense: unknown class doesn't blindly opt-in. Better to be silent
        # than to inject conflicting instructions.
        assert needs_override_contract_hint({
            "cage_meta": {"class": "tensor_target"},
        }) is False

    def test_class_case_insensitive(self):
        assert needs_override_contract_hint({
            "cage_meta": {"class": "ND_FEATURES"},
        }) is True

    def test_non_mapping_cage_meta_no_hint(self):
        # Defense against malformed rubric: cage_meta as a string
        assert needs_override_contract_hint({"cage_meta": "broken"}) is False

    def test_closed_form_constant_no_hint(self):
        # GP-145 substrates have their own contract; not in override set.
        assert needs_override_contract_hint({
            "cage_meta": {"class": "closed_form_constant"},
        }) is False

    def test_time_series_no_hint(self):
        # Time-series substrates (chaotic + non-chaotic) use the trajectory
        # contract, not I_model override.
        assert needs_override_contract_hint({
            "cage_meta": {"class": "time_series"},
        }) is False


class TestSelectSubstrateContractHint:
    def test_returns_empty_when_not_needed(self):
        assert select_substrate_contract_hint({}) == ""

    def test_returns_nonempty_for_nd_features_no_fit(self):
        s = select_substrate_contract_hint({
            "cage_meta": {"class": "nd_features"},
        })
        assert s != ""
        assert "I_model" in s
        assert "VISIBLE_SET" in s
        assert "HOLDOUT_SET" in s

    def test_hint_forbids_assert_pattern(self):
        s = select_substrate_contract_hint({
            "cage_meta": {"class": "nd_features"},
        })
        # The hint must explicitly tell the mutator NOT to write
        # assert-based discriminator tests.
        assert "FORBIDDEN" in s
        assert "assert" in s.lower()

    def test_hint_warns_against_nan_return(self):
        s = select_substrate_contract_hint({
            "cage_meta": {"class": "nd_features"},
        })
        # The original gp159 bug was I_model returning NaN; the hint
        # must call this out explicitly.
        assert "NaN" in s or "nan" in s

    def test_hint_imports_from_features_module(self):
        # Only nd_features class triggers the I_model(features) hint
        # post-narrowing. audit/literature/proof_target use other contracts.
        s = select_substrate_contract_hint({
            "cage_meta": {"class": "nd_features"},
        })
        assert "from features import" in s

    def test_fit_primitive_route_returns_empty(self):
        # When the existing fit_primitive_features_context block fires,
        # this hint must be silent to avoid double-instruction.
        s = select_substrate_contract_hint({
            "enable_fit_primitive_features": True,
            "cage_meta": {"class": "nd_features"},
        })
        assert s == ""


class TestNeedsScalarContractHint:
    """Pin down Contract C detection. Surfaced by gp159 module-level
    I_model + deferred-assert metaprogramming on iter 3 (score 0)."""

    def test_no_project_dir_returns_false(self):
        assert needs_scalar_contract_hint(
            {"cage_meta": {"class": "1d"}},
            project_dir=None,
        ) is False

    def test_class_1d_with_authored_test_model_triggers(self, tmp_path):
        (tmp_path / "test_model.py").write_text(
            "MODEL_PARAMS = {}\n"
            "def I_model(d, params=MODEL_PARAMS):\n"
            "    return 0.0\n"
        )
        assert needs_scalar_contract_hint(
            {"cage_meta": {"class": "1d"}},
            project_dir=tmp_path,
        ) is True

    def test_class_1d_without_test_model_returns_false(self, tmp_path):
        # No test_model.py at all → mutator will write from scratch via
        # the legacy assert-based prompt; do not inject Contract C.
        assert needs_scalar_contract_hint(
            {"cage_meta": {"class": "1d"}},
            project_dir=tmp_path,
        ) is False

    def test_class_1d_test_model_without_imodel_returns_false(self, tmp_path):
        (tmp_path / "test_model.py").write_text("# stub")
        assert needs_scalar_contract_hint(
            {"cage_meta": {"class": "1d"}},
            project_dir=tmp_path,
        ) is False

    def test_class_1d_with_features_py_excludes_contract_c(self, tmp_path):
        # If features.py exists alongside, the substrate is Contract B
        # territory; do not double-inject Contract C even if test_model.py
        # has def I_model(.
        (tmp_path / "test_model.py").write_text("def I_model(features): return 0.0")
        (tmp_path / "features.py").write_text("def visible_rows(): return []")
        assert needs_scalar_contract_hint(
            {"cage_meta": {"class": "1d"}},
            project_dir=tmp_path,
        ) is False

    def test_nd_features_class_does_not_trigger_scalar(self, tmp_path):
        (tmp_path / "test_model.py").write_text("def I_model(features): return 0.0")
        assert needs_scalar_contract_hint(
            {"cage_meta": {"class": "nd_features"}},
            project_dir=tmp_path,
        ) is False

    def test_fit_primitive_blocks_scalar_hint(self, tmp_path):
        (tmp_path / "test_model.py").write_text("def I_model(d): return 0.0")
        assert needs_scalar_contract_hint(
            {"enable_fit_primitive": True, "cage_meta": {"class": "1d"}},
            project_dir=tmp_path,
        ) is False

    def test_select_returns_scalar_hint(self, tmp_path):
        (tmp_path / "test_model.py").write_text("def I_model(d): return 0.0")
        s = select_substrate_contract_hint(
            {"cage_meta": {"class": "1d"}},
            project_dir=tmp_path,
        )
        # Hint identifies as Contract C / SCALAR; precedence statement
        # must be present so the LLM resolves conflicts vs current_test_model.
        assert "Contract C" in s or "SCALAR" in s
        assert "OVERRIDES" in s.upper()  # precedence sentence
        assert "MODEL_PARAMS" in s
        assert "module-level" in s.lower() or "module scope" in s.lower()

    def test_scalar_hint_forbids_module_level_call(self, tmp_path):
        (tmp_path / "test_model.py").write_text("def I_model(d): return 0.0")
        s = select_substrate_contract_hint(
            {"cage_meta": {"class": "1d"}},
            project_dir=tmp_path,
        )
        # Must explicitly forbid module-level I_model(...) — the gp159 R1 strike.
        assert "DO NOT call" in s and "module" in s.lower()

    def test_scalar_hint_warns_against_deferred_asserts(self, tmp_path):
        (tmp_path / "test_model.py").write_text("def I_model(d): return 0.0")
        s = select_substrate_contract_hint(
            {"cage_meta": {"class": "1d"}},
            project_dir=tmp_path,
        )
        # Must warn against the gp159 iter-3 deferred-assert metaprogramming.
        assert "_post_fit_sanity" in s or "deferred" in s.lower()


class TestVerifyConventionBridge:
    """Gap #4: heterogeneous substrates must declare a bridge in their FORM.
    Class K (gp154) was the motivating case — Kaplan/Chinchilla/Bahri
    pooled without a bridge produces mathematically meaningless averages."""

    def test_homogeneous_no_bridge_required(self):
        msg = verify_convention_bridge_in_form(
            "a * x + b",
            {"target_convention_homogeneity": "homogeneous"},
        )
        assert msg is None

    def test_heterogeneous_missing_bridge_flagged(self):
        msg = verify_convention_bridge_in_form(
            "a * x + b",  # no convention reference
            {"target_convention_homogeneity": "heterogeneous"},
        )
        assert msg is not None
        assert "convention" in msg.lower()

    def test_heterogeneous_with_features_subscript_passes(self):
        msg = verify_convention_bridge_in_form(
            "a * x + b * features['fit_convention']",
            {"target_convention_homogeneity": "heterogeneous"},
        )
        assert msg is None

    def test_heterogeneous_with_per_convention_coefficient_passes(self):
        msg = verify_convention_bridge_in_form(
            "(kaplan_alpha * x) + (chinchilla_alpha * y)",
            {"target_convention_homogeneity": "heterogeneous"},
        )
        assert msg is None

    def test_heterogeneous_with_conditional_bridge_passes(self):
        msg = verify_convention_bridge_in_form(
            "a if features.get('fit_convention') == 'kaplan' else b",
            {"target_convention_homogeneity": "heterogeneous"},
        )
        assert msg is None


class TestVerifyClassConsistency:
    """Pin down the gp159 wrong-class regression: substrate declared
    nd_features but had no features.py → wrong contract hint injected."""

    def test_no_class_declaration_passes(self, tmp_path):
        assert verify_class_consistency_with_substrate("", tmp_path) is None

    def test_nd_features_without_features_py_fails(self, tmp_path):
        # The exact gp159 regression — declared nd_features, no features.py.
        (tmp_path / "test_model.py").write_text("def I_model(d): return d")
        msg = verify_class_consistency_with_substrate("nd_features", tmp_path)
        assert msg is not None
        assert "features.py" in msg
        # Hints at the right fix: declare class="1d"
        assert '"1d"' in msg or "1d" in msg

    def test_nd_features_with_features_py_passes(self, tmp_path):
        (tmp_path / "features.py").write_text("def visible_rows(): return []")
        assert verify_class_consistency_with_substrate("nd_features", tmp_path) is None

    def test_class_1d_passes_without_features(self, tmp_path):
        # 1D substrates do NOT need features.py — declaration is consistent
        # whether features.py exists or not.
        assert verify_class_consistency_with_substrate("1d", tmp_path) is None

    def test_proof_target_without_lean_fails(self, tmp_path):
        (tmp_path / "evidence.txt").write_text("just data")
        msg = verify_class_consistency_with_substrate("proof_target", tmp_path)
        assert msg is not None
        assert "Lean" in msg

    def test_proof_target_with_lean_file_passes(self, tmp_path):
        (tmp_path / "proof.lean").write_text("theorem foo : True := by trivial")
        assert verify_class_consistency_with_substrate("proof_target", tmp_path) is None

    def test_proof_target_with_lean_in_evidence_passes(self, tmp_path):
        (tmp_path / "evidence.txt").write_text("Submit a Lean theorem proof obligation.")
        assert verify_class_consistency_with_substrate("proof_target", tmp_path) is None

    def test_closed_form_constant_without_pslq_fails(self, tmp_path):
        (tmp_path / "evidence.txt").write_text("data only")
        msg = verify_class_consistency_with_substrate("closed_form_constant", tmp_path)
        assert msg is not None
        assert "PSLQ" in msg or "integer" in msg.lower()

    def test_closed_form_constant_with_pslq_passes(self, tmp_path):
        (tmp_path / "evidence.txt").write_text("Use PSLQ to find integer relations.")
        assert verify_class_consistency_with_substrate("closed_form_constant", tmp_path) is None

    def test_audit_with_fitting_harness_fails(self, tmp_path):
        (tmp_path / "gate_harness.py").write_text(
            "def _ground_truth(x): return 2*x"
        )
        msg = verify_class_consistency_with_substrate("audit", tmp_path)
        assert msg is not None
        assert "audit" in msg.lower()

    def test_audit_without_fitting_harness_passes(self, tmp_path):
        # Audit substrate with a non-fitting gate_harness (no _ground_truth)
        (tmp_path / "gate_harness.py").write_text(
            "def evaluate_audit_thesis(thesis): return {'score': 0}"
        )
        assert verify_class_consistency_with_substrate("audit", tmp_path) is None

    def test_class_case_insensitive_consistency(self, tmp_path):
        msg = verify_class_consistency_with_substrate("ND_FEATURES", tmp_path)
        assert msg is not None  # uppercase still triggers the check
