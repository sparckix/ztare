"""Tests for orchestrator/contract_table.py + protocols.py + render_evidence_template.py."""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Mapping, Optional

import pytest

from ztare.orchestrator.contract_table import (
    CONTRACT_REGISTRY,
    ContractSpec,
    SubstrateABI,
    get_spec,
    get_spec_by_class,
    list_substrate_classes,
)
from ztare.orchestrator.protocols import (
    CONTRACT_ERROR_CODES,
    ContractError,
    FeatureModel,
    ScalarModel,
    adapt,
)
from ztare.orchestrator.render_evidence_template import (
    render_active_contract_label,
    render_evidence_set_d,
)


# ── Contract table ───────────────────────────────────────────────────────


class TestContractTable:
    def test_registry_has_all_abis(self):
        assert set(CONTRACT_REGISTRY.keys()) == set(SubstrateABI)

    def test_get_spec_returns_correct_abi(self):
        spec = get_spec(SubstrateABI.SCALAR_1D)
        assert spec.abi is SubstrateABI.SCALAR_1D

    def test_get_spec_unknown_raises(self):
        # SubstrateABI is closed; pass a sentinel that isn't in the registry.
        with pytest.raises(KeyError):
            CONTRACT_REGISTRY[object()]  # type: ignore[index]

    def test_class_to_abi_mapping(self):
        assert get_spec_by_class("1d").abi is SubstrateABI.SCALAR_1D
        assert get_spec_by_class("nd_features").abi is SubstrateABI.FEATURE_DICT
        assert get_spec_by_class("closed_form_constant").abi is SubstrateABI.DISCRIMINATOR
        assert get_spec_by_class("proof_target").abi is SubstrateABI.LEAN_PROOF

    def test_unknown_class_returns_none(self):
        assert get_spec_by_class("tensor_target") is None
        assert get_spec_by_class("") is None
        assert get_spec_by_class(None) is None  # type: ignore[arg-type]

    def test_class_lookup_case_insensitive(self):
        assert get_spec_by_class("1D").abi is SubstrateABI.SCALAR_1D
        assert get_spec_by_class("ND_FEATURES").abi is SubstrateABI.FEATURE_DICT

    def test_list_substrate_classes(self):
        classes = list_substrate_classes()
        assert "1d" in classes
        assert "nd_features" in classes
        assert "closed_form_constant" in classes
        assert "proof_target" in classes

    def test_scalar_1d_required_globals(self):
        spec = get_spec(SubstrateABI.SCALAR_1D)
        assert "I_model" in spec.required_module_globals
        assert "MODEL_PARAMS" in spec.required_module_globals
        assert "VISIBLE_SET" in spec.required_module_globals

    def test_feature_dict_requires_features_py(self):
        spec = get_spec(SubstrateABI.FEATURE_DICT)
        assert "features.py" in spec.required_filesystem_caps

    def test_skeletons_present_for_imodel_abis(self):
        assert "def I_model" in get_spec(SubstrateABI.SCALAR_1D).skeleton_template
        assert "def I_model" in get_spec(SubstrateABI.FEATURE_DICT).skeleton_template

    def test_cage_meta_class_property(self):
        assert get_spec(SubstrateABI.SCALAR_1D).cage_meta_class == "1d"
        assert get_spec(SubstrateABI.FEATURE_DICT).cage_meta_class == "nd_features"

    def test_nullable_feature_keys_default_empty(self):
        # Gap #2: Scalar 1D doesn't have nullable features by default
        spec = get_spec(SubstrateABI.SCALAR_1D)
        assert spec.nullable_feature_keys == frozenset()
        assert spec.nullable_asymptotic_limits == {}

    def test_feature_dict_declares_nullable_intrinsic_dim_d(self):
        # gp154 case: LLM substrates have no intrinsic dimension; must be nullable
        spec = get_spec(SubstrateABI.FEATURE_DICT)
        assert "intrinsic_dim_d" in spec.nullable_feature_keys
        # Asymptotic limit for missing intrinsic dimension is ∞ (LLM embedding limit)
        assert spec.nullable_asymptotic_limits.get("intrinsic_dim_d") == float("inf")

    def test_nullable_keys_have_declared_limits(self):
        # Every nullable key must have an asymptotic limit declared.
        for spec in CONTRACT_REGISTRY.values():
            for key in spec.nullable_feature_keys:
                assert key in spec.nullable_asymptotic_limits, (
                    f"{spec.abi.name}: nullable key {key!r} has no "
                    f"asymptotic limit declared"
                )


# ── adapt() ──────────────────────────────────────────────────────────────


class TestAdaptScalar1D:
    def _module_with(self, **attrs):
        return SimpleNamespace(**attrs)

    def test_clean_scalar_module_passes(self):
        def I_model(d: float, params: Optional[Mapping] = None) -> float:
            return d * 2.0

        mod = self._module_with(
            I_model=I_model,
            MODEL_PARAMS={},
            VISIBLE_SET=[],
            HOLDOUT_SET=[],
        )
        spec = get_spec(SubstrateABI.SCALAR_1D)
        adapted = adapt(mod, spec)
        assert adapted is I_model
        assert adapted(3.0) == 6.0

    def test_missing_imodel_raises(self):
        # I_model is in required_module_globals so it's checked at step 1.
        # Missing entirely → MISSING_MODULE_GLOBAL. Present but non-callable →
        # MISSING_IMODEL. Test both branches.
        mod_missing = self._module_with(MODEL_PARAMS={}, VISIBLE_SET=[], HOLDOUT_SET=[])
        spec = get_spec(SubstrateABI.SCALAR_1D)
        with pytest.raises(ContractError) as exc_info:
            adapt(mod_missing, spec)
        assert exc_info.value.code == "MISSING_MODULE_GLOBAL"

        mod_non_callable = self._module_with(
            I_model=None, MODEL_PARAMS={}, VISIBLE_SET=[], HOLDOUT_SET=[],
        )
        with pytest.raises(ContractError) as exc_info:
            adapt(mod_non_callable, spec)
        assert exc_info.value.code == "MISSING_IMODEL"

    def test_missing_module_global_raises(self):
        def I_model(d): return d
        mod = self._module_with(I_model=I_model, MODEL_PARAMS={})  # missing VISIBLE_SET
        spec = get_spec(SubstrateABI.SCALAR_1D)
        with pytest.raises(ContractError) as exc_info:
            adapt(mod, spec)
        assert exc_info.value.code == "MISSING_MODULE_GLOBAL"
        assert "VISIBLE_SET" in str(exc_info.value)

    def test_wrong_signature_features_for_scalar(self):
        # Mutator emitted Contract B shape (`features`) on Contract C substrate.
        def I_model(features): return 0.0
        mod = self._module_with(
            I_model=I_model,
            MODEL_PARAMS={},
            VISIBLE_SET=[],
            HOLDOUT_SET=[],
        )
        spec = get_spec(SubstrateABI.SCALAR_1D)
        with pytest.raises(ContractError) as exc_info:
            adapt(mod, spec)
        assert exc_info.value.code == "WRONG_SIGNATURE"


class TestAdaptFeatureDict:
    def test_clean_feature_module_passes(self):
        def I_model(features: Mapping) -> float:
            return features.get("x", 0.0)

        mod = SimpleNamespace(
            I_model=I_model,
            MODEL_PARAMS={},
            VISIBLE_SET=[],
            HOLDOUT_SET=[],
        )
        spec = get_spec(SubstrateABI.FEATURE_DICT)
        adapted = adapt(mod, spec)
        assert adapted({"x": 5.0}) == 5.0

    def test_wrong_signature_scalar_for_features(self):
        def I_model(d): return d
        mod = SimpleNamespace(
            I_model=I_model,
            MODEL_PARAMS={},
            VISIBLE_SET=[],
            HOLDOUT_SET=[],
        )
        spec = get_spec(SubstrateABI.FEATURE_DICT)
        with pytest.raises(ContractError) as exc_info:
            adapt(mod, spec)
        assert exc_info.value.code == "WRONG_SIGNATURE"


class TestAdaptNonImodelAbis:
    def test_discriminator_no_imodel_required(self):
        # DISCRIMINATOR ABI does not require I_model
        mod = SimpleNamespace()  # nothing
        spec = get_spec(SubstrateABI.DISCRIMINATOR)
        adapted = adapt(mod, spec)
        # Returns a sentinel that raises if called
        with pytest.raises(ContractError):
            adapted(1.0)

    def test_lean_proof_no_imodel_required(self):
        mod = SimpleNamespace()
        spec = get_spec(SubstrateABI.LEAN_PROOF)
        adapted = adapt(mod, spec)
        with pytest.raises(ContractError):
            adapted()


# ── ContractError ────────────────────────────────────────────────────────


class TestContractError:
    def test_codes_are_canonical(self):
        spec = get_spec(SubstrateABI.SCALAR_1D)
        for code in CONTRACT_ERROR_CODES:
            err = ContractError(code, spec)
            assert err.code == code

    def test_error_carries_remediation(self):
        spec = get_spec(SubstrateABI.SCALAR_1D)
        err = ContractError("MISSING_IMODEL", spec, remediation="add def I_model(d)")
        assert "add def I_model" in err.remediation


# ── Protocols (runtime_checkable) ────────────────────────────────────────


class TestProtocolIsinstance:
    def test_scalar_model_isinstance(self):
        def fn(d, params=None): return d
        assert isinstance(fn, ScalarModel)

    def test_feature_model_isinstance(self):
        def fn(features): return 0.0
        assert isinstance(fn, FeatureModel)


# ── Evidence template rendering ──────────────────────────────────────────


class TestRenderEvidence:
    def test_scalar_1d_render_contains_signature(self):
        spec = get_spec(SubstrateABI.SCALAR_1D)
        text = render_evidence_set_d(spec)
        assert "Evidence Set D" in text
        assert spec.signature_str in text
        assert "auto-generated" in text

    def test_scalar_1d_render_includes_skeleton(self):
        spec = get_spec(SubstrateABI.SCALAR_1D)
        text = render_evidence_set_d(spec)
        assert "def I_model" in text
        assert "MODEL_PARAMS" in text
        assert "p.get(" in text

    def test_scalar_1d_render_forbids_module_level_call(self):
        spec = get_spec(SubstrateABI.SCALAR_1D)
        text = render_evidence_set_d(spec)
        assert "DO NOT call `I_model" in text
        assert "_post_fit_sanity" in text  # explicit forbid
        assert "__main__" in text  # legitimate alternative

    def test_feature_dict_render_mentions_features_py(self):
        spec = get_spec(SubstrateABI.FEATURE_DICT)
        text = render_evidence_set_d(spec)
        assert "features.py" in text
        assert "from features import" in text

    def test_active_contract_label_one_liner(self):
        spec = get_spec(SubstrateABI.SCALAR_1D)
        label = render_active_contract_label(spec)
        assert "ACTIVE CONTRACT" in label
        assert "OVERRIDES" in label
        assert spec.abi.name in label

    def test_discriminator_render_no_imodel(self):
        spec = get_spec(SubstrateABI.DISCRIMINATOR)
        text = render_evidence_set_d(spec)
        # Non-I_model template — should NOT contain "def I_model"
        assert "def I_model" not in text
