from pathlib import Path

import pytest

import ztare.gates.lean_proof_gate as lean_proof_gate
from ztare.gates.lean_proof_gate import (
    ANTI_LAUNDERING_ORGANS,
    TARGET_RATIFICATION_AUTHORITIES,
    TARGET_RATIFICATION_AUTHORITY_ROSTER_SHA256,
    run_anti_laundering_kernel,
)
from ztare.gates.v33_indirect_leakage_gate import build_indirect_probe_sources
from ztare.gates.v33_preflight_risk_detector import detect_risks
from ztare.gates.v33_single_lemma_exact_gate import (
    build_exact_probe_source,
    classify_exact_output,
)
from ztare.leanmill.solver import canonical_reelaboration
from ztare.leanmill.solver import leanmill_cage


REPO_ROOT = Path(__file__).resolve().parents[1]
LEAN_ROOT = REPO_ROOT / "ztare_proofs"


def test_governance_organ_set_is_finite_and_explicit() -> None:
    assert frozenset(ANTI_LAUNDERING_ORGANS) == {
        "v33_consequence_exposure_gate",
        "v33_currency_mismatch_gate",
        "v33_indirect_leakage_gate",
        "v33_paraphrase_gate",
        "v33_preflight_risk_detector",
        "v33_single_lemma_exact_gate",
    }
    assert all(
        module.__name__ == f"ztare.gates.{name}"
        for name, module in ANTI_LAUNDERING_ORGANS.items()
    )
    with pytest.raises(TypeError):
        ANTI_LAUNDERING_ORGANS["adapter_supplied"] = object()


def test_target_ratification_authority_roster_is_closed_and_content_addressed() -> None:
    from ztare.leanmill.ratification_policy import (
        FINAL_RATIFICATION_AUTHORITIES,
        FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256,
    )

    assert TARGET_RATIFICATION_AUTHORITIES == {
        "v33_consequence_exposure_gate",
        "v33_currency_mismatch_gate",
        "v33_indirect_leakage_gate",
        "v33_paraphrase_gate",
        "v33_preflight_risk_detector",
        "v33_single_lemma_exact_gate",
        "target_identity",
        "target_declaration",
        "target_signature",
        "statement_integrity",
        "canonical_reelaboration",
    }
    import hashlib

    assert TARGET_RATIFICATION_AUTHORITY_ROSTER_SHA256 == hashlib.sha256(
        "\n".join(sorted(TARGET_RATIFICATION_AUTHORITIES)).encode("utf-8")
    ).hexdigest()
    with pytest.raises(AttributeError):
        TARGET_RATIFICATION_AUTHORITIES.add("adapter_supplied")
    assert FINAL_RATIFICATION_AUTHORITIES == {
        *TARGET_RATIFICATION_AUTHORITIES,
        "kernel_compile_receipt",
        "matched_negative_control_receipt",
        "axiom_allowlist_receipt",
    }
    assert FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256 == hashlib.sha256(
        "\n".join(sorted(FINAL_RATIFICATION_AUTHORITIES)).encode("utf-8")
    ).hexdigest()


def test_exact_probe_output_has_three_distinct_states() -> None:
    assert classify_exact_output("Try this: exact Nat.add_zero n")[0] is True
    assert classify_exact_output("`exact?` could not close the goal")[0] is False
    assert classify_exact_output("error: unknown tactic\nunsolved goals")[0] is None
    assert classify_exact_output("")[0] is None


MULTI_DECL_SOURCE = """\
import Mathlib

namespace Circular

theorem target (Q : Nat → Prop) (h : Q 0) : Q 0 := h

end Circular

namespace Useful

theorem target (n : Nat) : n + 0 = n := by simp

end Useful
"""


def test_target_ratification_declares_every_authority_disposition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = MULTI_DECL_SOURCE.replace(
        "theorem target (n : Nat) : n + 0 = n := by simp",
        "theorem target (n : Nat) : n + 0 = n := by sorry",
    )
    monkeypatch.setattr(
        canonical_reelaboration,
        "check",
        lambda *_args, **_kwargs: (True, "canonical target type matches"),
    )

    verdict = run_anti_laundering_kernel(
        MULTI_DECL_SOURCE,
        tmp_path / "TargetRatification.lean",
        LEAN_ROOT,
        original_source=original,
        target_name="Useful.target",
    )

    assert verdict["policy_profile"] == "target_ratification"
    assert set(verdict["required_authorities"]) == TARGET_RATIFICATION_AUTHORITIES
    assert set(verdict["authority_disposition"]) == TARGET_RATIFICATION_AUTHORITIES
    assert all(
        disposition in {"passed", "rejected", "unavailable", "inapplicable"}
        for disposition in verdict["authority_disposition"].values()
    )
    assert verdict["authority_disposition"]["statement_integrity"] == "passed"
    assert verdict["authority_disposition"]["canonical_reelaboration"] == "passed"
    assert verdict["authority_roster_sha256"] == (
        TARGET_RATIFICATION_AUTHORITY_ROSTER_SHA256
    )


def test_vacuity_detector_is_fenced_to_qualified_target_in_multidecl_module(
    tmp_path: Path,
) -> None:
    # This witnesses the pre-fix failure: module-wide parsing reads the first
    # declaration's circular statement even when LeanMill carries Useful.target.
    assert detect_risks(MULTI_DECL_SOURCE)["vacuity_suspected"] is True

    verdict = run_anti_laundering_kernel(
        MULTI_DECL_SOURCE,
        tmp_path / "MultiDecl.lean",
        LEAN_ROOT,
        target_name="Useful.target",
    )

    assert verdict["passed"] is True
    assert "vacuity_suspect" not in verdict["confirmed"]
    assert verdict["detail"]["vacuity"]["vacuity_suspected"] is False
    assert verdict["detail"]["vacuity_scope"] == {
        "mode": "resolved_target_signature",
        "selector": "Useful.target",
        "qualified_target": "Useful.target",
        "written_target": "target",
    }
    preview = verdict["detail"]["vacuity"]["statement_preview"]
    assert "n : Nat" in preview
    assert "Circular" not in preview


def test_target_scoping_preserves_circularity_detector_strength(tmp_path: Path) -> None:
    verdict = run_anti_laundering_kernel(
        MULTI_DECL_SOURCE,
        tmp_path / "MultiDecl.lean",
        LEAN_ROOT,
        target_name="Circular.target",
    )

    assert verdict["passed"] is False
    assert "vacuity_suspect" in verdict["confirmed"]
    assert "circular_conclusion" in verdict["detail"]["vacuity"]["risk_flags"]
    assert verdict["detail"]["vacuity_scope"]["qualified_target"] == "Circular.target"


def test_proof_shape_organs_are_fenced_to_selected_declaration(
    tmp_path: Path,
) -> None:
    source = """\
import Mathlib

namespace Earlier
theorem target (f : ℝ → ℝ) (hf : Continuous f) (a b : ℝ)
    (hab : a < b) (ha : f a < 0) (hb : 0 < f b) :
    ∃ c ∈ Set.Ioo a b, f c = 0 := by
  obtain ⟨c, hc_mem, hc_eq⟩ :=
    intermediate_value_Ioo hab.le hf.continuousOn (Set.mem_Ioo.mpr ⟨ha, hb⟩)
  exact ⟨c, hc_mem, hc_eq⟩
end Earlier

namespace Selected
theorem target (a b c : Nat) (h : a ≤ b) : a ≤ b + c := by
  exact le_trans h <| Nat.le_add_right b c
end Selected
"""

    verdict = run_anti_laundering_kernel(
        source,
        tmp_path / "ProofShapeScope.lean",
        LEAN_ROOT,
        target_name="Selected.target",
    )

    scope = verdict["detail"]["proof_shape_scope"]
    assert scope == {
        "mode": "resolved_target_declaration",
        "selector": "Selected.target",
        "qualified_target": "Selected.target",
        "written_target": "target",
    }
    preview = verdict["detail"]["gold_name_verbatim"]["detect"]["body_preview"]
    assert "Nat.le_add_right" in preview
    assert "intermediate_value_Ioo" not in preview


def test_deep_probe_builders_replace_only_qualified_target() -> None:
    exact = build_exact_probe_source(
        MULTI_DECL_SOURCE,
        target_name="Useful.target",
    )
    floor, automation = build_indirect_probe_sources(
        MULTI_DECL_SOURCE,
        "simp",
        target_name="Useful.target",
    )

    for probe in (exact, floor, automation):
        assert "theorem target (Q : Nat → Prop) (h : Q 0) : Q 0 := h" in probe
        assert "namespace Circular" in probe
        assert "namespace Useful" in probe
    assert "theorem target (n : Nat) : n + 0 = n := by\n  intros\n  exact?" in exact
    assert "theorem target (n : Nat) : n + 0 = n := by first | rfl" in floor
    assert "theorem target (n : Nat) : n + 0 = n := by simp" in automation
    assert build_exact_probe_source(
        MULTI_DECL_SOURCE,
        target_name="Missing.target",
    ) == ""
    assert build_indirect_probe_sources(
        MULTI_DECL_SOURCE,
        "simp",
        target_name="Missing.target",
    ) == ("", "")


def test_target_scoped_organs_exclude_later_siblings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = """\
import Mathlib

namespace Earlier
theorem helper (n : Nat) : n = n := by rfl
end Earlier

namespace Selected
theorem target (n : Nat) : n + 0 = n := by simp
end Selected

namespace Later
theorem contaminant (h : False) : (1 : ℝ) ≤ 2 := by contradiction
end Later
"""
    captured: dict[str, str] = {}

    def capture_consequence(text: str) -> dict:
        captured["consequence"] = text
        return {
            "consequence_exposure_suspect": False,
            "blocking": False,
            "smuggled_heads": [],
            "advisory_goalhead": False,
            "binders": [],
            "reason": "",
        }

    def capture_currency(text: str) -> dict:
        captured["currency"] = text
        return {
            "scalar_wrapper_suspect": False,
            "conclusion_is_scalar": False,
            "field_obligation_token": None,
            "preview": text[:160],
        }

    monkeypatch.setattr(
        ANTI_LAUNDERING_ORGANS["v33_consequence_exposure_gate"],
        "detect_shape",
        capture_consequence,
    )
    monkeypatch.setattr(
        ANTI_LAUNDERING_ORGANS["v33_currency_mismatch_gate"],
        "detect_shape",
        capture_currency,
    )
    verdict = run_anti_laundering_kernel(
        source,
        tmp_path / "TargetScopedOrgans.lean",
        LEAN_ROOT,
        target_name="Selected.target",
    )

    assert verdict["available"] is True
    assert "Earlier.helper" not in captured["consequence"]
    assert "theorem helper" in captured["consequence"]
    assert "theorem target" in captured["consequence"]
    assert "contaminant" not in captured["consequence"]
    assert "theorem target" in captured["currency"]
    assert "theorem helper" not in captured["currency"]
    assert "contaminant" not in captured["currency"]


def test_supplied_unresolved_target_is_typed_unavailable(tmp_path: Path) -> None:
    verdict = run_anti_laundering_kernel(
        MULTI_DECL_SOURCE,
        tmp_path / "MissingTarget.lean",
        LEAN_ROOT,
        target_name="Missing.target",
    )

    assert verdict["available"] is False
    assert verdict["passed"] is False
    assert verdict["unavailable_organs"] == ["target_identity"]
    assert verdict["detail"]["target_scope"]["reason"] == "target_identity_unresolved"


@pytest.mark.parametrize(
    ("organ_name", "result_key", "result"),
    [
        (
            "v33_single_lemma_exact_gate",
            "single_lemma_exact_confirmed",
            {"single_lemma_exact_confirmed": None, "timed_out": True},
        ),
        (
            "v33_indirect_leakage_gate",
            "indirect_leakage_confirmed",
            {
                "indirect_leakage_confirmed": None,
                "trivial_floor_closes": None,
                "global_automation_closes": None,
            },
        ),
    ],
)
def test_deep_probe_soft_failure_is_typed_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    organ_name: str,
    result_key: str,
    result: dict,
) -> None:
    organ = ANTI_LAUNDERING_ORGANS[organ_name]
    other_name = (
        "v33_indirect_leakage_gate"
        if organ_name == "v33_single_lemma_exact_gate"
        else "v33_single_lemma_exact_gate"
    )
    other = ANTI_LAUNDERING_ORGANS[other_name]
    monkeypatch.setattr(
        other,
        "detect_shape",
        (
            (lambda _source: {"indirect_leakage_suspect": False})
            if other_name == "v33_indirect_leakage_gate"
            else (lambda _source: {"single_lemma_exact_suspect": False})
        ),
    )
    if organ_name == "v33_single_lemma_exact_gate":
        monkeypatch.setattr(
            organ,
            "detect_shape",
            lambda _source: {"single_lemma_exact_suspect": True},
        )
        monkeypatch.setattr(
            organ,
            "independent_exact_verify_rowfile",
            lambda *_args, **_kwargs: result,
        )
    else:
        monkeypatch.setattr(
            organ,
            "detect_shape",
            lambda _source: {
                "indirect_leakage_suspect": True,
                "closer_tactic": "simp",
            },
        )
        monkeypatch.setattr(
            organ,
            "independent_verify",
            lambda *_args, **_kwargs: result,
        )

    verdict = run_anti_laundering_kernel(
        MULTI_DECL_SOURCE,
        tmp_path / "SoftFailure.lean",
        LEAN_ROOT,
        deep_verify=True,
        target_name="Useful.target",
    )

    assert result[result_key] is None
    assert verdict["available"] is False
    assert verdict["passed"] is False
    assert organ_name in verdict["unavailable_organs"]
    assert verdict["confirmed"] == []


def test_required_organ_crash_is_typed_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def crash(_source: str) -> dict:
        raise RuntimeError("injected required-organ crash")

    monkeypatch.setattr(
        ANTI_LAUNDERING_ORGANS["v33_preflight_risk_detector"],
        "detect_risks",
        crash,
    )
    verdict = run_anti_laundering_kernel(
        MULTI_DECL_SOURCE,
        tmp_path / "RequiredOrganCrash.lean",
        LEAN_ROOT,
        target_name="Useful.target",
    )

    assert verdict["available"] is False
    assert verdict["passed"] is False
    assert verdict["unavailable_organs"] == ["v33_preflight_risk_detector"]
    assert verdict["confirmed"] == []
    assert "governance_organ_unavailable" in verdict["flags"]


def test_outer_kernel_crash_withholds_gate_credit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = "theorem selected : (1 : Nat) = 1 := by rfl"
    monkeypatch.setattr(lean_proof_gate, "extract_lean_from_thesis", lambda _path: source)
    monkeypatch.setattr(
        lean_proof_gate,
        "write_lean_target",
        lambda _source, _slug, _root: tmp_path / "Selected.lean",
    )
    monkeypatch.setattr(
        lean_proof_gate,
        "compile_lean",
        lambda *_args: {
            "compiled": True,
            "exit_code": 0,
            "duration_s": 0.01,
            "stdout": "",
            "stderr": "",
        },
    )
    monkeypatch.setattr(
        lean_proof_gate,
        "audit_axioms",
        lambda *_args: {
            "axiom_audit_passed": True,
            "extra_axioms": [],
            "forbidden_tokens": [],
        },
    )
    monkeypatch.setattr(
        lean_proof_gate,
        "compute_secondary_observables",
        lambda _path: {
            "line_count": 1,
            "mathlib_lemma_count": 0,
            "applied_lemmas": [],
        },
    )
    monkeypatch.setattr(lean_proof_gate, "theorem_statement_hashes", lambda _source: [])

    def crash_kernel(*_args, **_kwargs) -> dict:
        raise RuntimeError("injected governance-kernel crash")

    monkeypatch.setattr(lean_proof_gate, "run_anti_laundering_kernel", crash_kernel)
    result = lean_proof_gate.run_lean_proof_gate(
        tmp_path / "thesis.md",
        "selected",
        LEAN_ROOT,
    )

    assert result["anti_laundering_passed"] is False
    assert result["gate_passed"] is False
    assert result["v33_organ_flags"] == ["governance_kernel_unavailable"]


def test_canonical_reelaboration_soft_failure_is_typed_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        canonical_reelaboration,
        "check",
        lambda *_args, **_kwargs: (
            None,
            "unavailable (injected compile infrastructure error)",
        ),
    )
    original = MULTI_DECL_SOURCE.replace(
        "theorem target (n : Nat) : n + 0 = n := by simp",
        "theorem target (n : Nat) : n + 0 = n := by sorry",
    )
    verdict = run_anti_laundering_kernel(
        MULTI_DECL_SOURCE,
        tmp_path / "CanonicalUnavailable.lean",
        LEAN_ROOT,
        original_source=original,
        target_name="Useful.target",
    )

    assert verdict["available"] is False
    assert verdict["passed"] is False
    assert "canonical_reelaboration" in verdict["unavailable_organs"]
    assert verdict["detail"]["canonical_reelaboration"]["ok"] is None


def test_cage_and_direct_kernel_failure_is_typed_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def crash(*_args, **_kwargs) -> dict:
        raise RuntimeError("injected cage and direct-kernel failure")

    monkeypatch.setattr(lean_proof_gate, "run_anti_laundering_kernel", crash)
    verdict = leanmill_cage.govern_via_cage(
        MULTI_DECL_SOURCE,
        tmp_path / "CageUnavailable.lean",
        LEAN_ROOT,
        target_name="Useful.target",
    )

    assert verdict["available"] is False
    assert verdict["passed"] is False
    assert verdict["unavailable_organs"] == ["leanmill_anti_laundering_kernel"]
