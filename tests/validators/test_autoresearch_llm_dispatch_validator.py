from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
VALIDATOR = REPO / "scripts" / "public" / "validators" / "validate_autoresearch_llm_dispatch.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_autoresearch_llm_dispatch", VALIDATOR)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_autoresearch_llm_dispatch_validator_has_no_findings() -> None:
    module = _load_validator()
    report = module.validate(REPO)

    assert report["summary"]["findings"] == 0
    assert report["summary"]["wrapped_sites"] >= 10
    assert report["summary"]["direct_allowed_sites"] == 4
    assert len(report["direct_allowed"]) == 4


def test_autoresearch_llm_dispatch_validator_names_core_direct_exceptions() -> None:
    module = _load_validator()
    report = module.validate(REPO)
    direct_sites = {
        (row["path"], row["function"], row["call_site"])
        for row in report["dispatch_sites"]
        if row["call_site"].startswith("direct:")
    }
    direct_summary = {
        (row["path"], row["function"], row["reason"])
        for row in report["direct_allowed"]
    }

    assert (
        "src/ztare/validator/autoresearch_loop.py",
        "safe_mutate",
        "direct:dispatch-covered mutator fallback",
    ) in direct_sites
    assert (
        "src/ztare/validator/test_thesis.py",
        "safe_generate",
        "direct:dispatch-covered judge fallback",
    ) in direct_sites
    assert (
        "src/ztare/validator/generate_committee.py",
        "safe_generate_committee",
        "direct:dispatch-covered committee fallback",
    ) in direct_sites
    assert (
        "src/ztare/validator/autoresearch_loop.py",
        "safe_mutate",
        "dispatch-covered mutator fallback",
    ) in direct_summary


def test_autoresearch_llm_dispatch_validator_covers_rd_substrate_recommender() -> None:
    module = _load_validator()
    report = module.validate(REPO)
    wrapped_sites = {
        (row["path"], row["function"], row["call_site"])
        for row in report["dispatch_sites"]
        if not row["call_site"].startswith("direct:")
    }

    assert (
        "src/ztare/research_director/substrate_recommender.py",
        "call_recommender_model",
        "substrate_recommender",
    ) in wrapped_sites
