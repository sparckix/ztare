"""Tests for FrozenFittedModel (GP-157 Gap #5)."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from ztare.orchestrator.fitted_model import FrozenFittedModel


def _example_imodel(d: float, params=None) -> float:
    p = params or {}
    return p.get("a", 1.0) * d


class TestFrozenFittedModel:
    def test_construct_via_factory(self):
        m = FrozenFittedModel.from_components(
            I_model=_example_imodel,
            fitted_params={"a": 3.7, "b": 0.9},
            expression_str="a * d",
            abi_name="SCALAR_1D",
        )
        assert m.fitted_params["a"] == 3.7
        assert m.expression_str == "a * d"
        assert m.abi_name == "SCALAR_1D"

    def test_dataclass_is_frozen(self):
        m = FrozenFittedModel.from_components(_example_imodel, {"a": 1.0})
        with pytest.raises(Exception):
            m.expression_str = "tampered"  # type: ignore[misc]

    def test_fitted_params_read_only(self):
        m = FrozenFittedModel.from_components(_example_imodel, {"a": 1.0})
        with pytest.raises(TypeError):
            m.fitted_params["a"] = 99.0  # type: ignore[index]

    def test_extras_read_only(self):
        m = FrozenFittedModel.from_components(
            _example_imodel, {"a": 1.0}, extras={"foo": "bar"},
        )
        with pytest.raises(TypeError):
            m.extras["foo"] = "tampered"  # type: ignore[index]

    def test_phase2_can_call_imodel_but_not_modify(self):
        m = FrozenFittedModel.from_components(
            _example_imodel, {"a": 2.0},
        )
        assert m.I_model(3.0, dict(m.fitted_params)) == 6.0
        # But cannot mutate the params dict
        with pytest.raises(TypeError):
            m.fitted_params["a"] = 99.0  # type: ignore[index]
