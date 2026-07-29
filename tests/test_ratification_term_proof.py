from pathlib import Path

from ztare.leanmill.lean_source import (
    open_decl_for_ratification,
    replace_decl_proof,
)
from ztare.leanmill.solver import solver_core


TERM_PROOF_SOURCE = """\
namespace TermRoute

theorem pair : True ∧ True :=
  ⟨trivial, trivial⟩

end TermRoute
"""


def test_preverified_term_classifier_covers_production_ratification_branch() -> None:
    assert solver_core._preverified_proof_is_term(True, "⟨trivial, trivial⟩")
    assert not solver_core._preverified_proof_is_term(True, "by\n  constructor")
    assert not solver_core._preverified_proof_is_term(False, "⟨trivial, trivial⟩")


def test_named_replacement_preserves_carried_term_proof_category() -> None:
    opened, proof = open_decl_for_ratification(TERM_PROOF_SOURCE, "TermRoute.pair")
    assert proof == "⟨trivial, trivial⟩"

    closed = replace_decl_proof(
        opened,
        "TermRoute.pair",
        proof,
        proof_is_term=True,
    )

    assert "sorry" not in closed
    assert ":= ⟨trivial, trivial⟩" in closed
    assert ":= by\n  ⟨trivial, trivial⟩" not in closed


def test_campaign_compile_uses_term_preserving_splice(
    tmp_path: Path, monkeypatch
) -> None:
    opened, proof = open_decl_for_ratification(TERM_PROOF_SOURCE, "TermRoute.pair")
    captured = {}

    from ztare.formal import repl_compile
    from ztare.gates import v33_preflight_risk_detector

    monkeypatch.setattr(repl_compile, "get_campaign_substrate", lambda: None)

    def fake_compile(probe, *_args, **_kwargs):
        captured["probe"] = probe
        return True

    monkeypatch.setattr(v33_preflight_risk_detector, "_compile_probe", fake_compile)

    assert solver_core._campaign_aware_proof_compiles(
        opened,
        proof,
        tmp_path,
        10,
        target_name="TermRoute.pair",
        proof_is_term=True,
    ) is True
    assert ":= ⟨trivial, trivial⟩" in captured["probe"]
    assert "sorry" not in captured["probe"]
