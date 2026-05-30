from pathlib import Path

from src.ztare.formal import lean_repl


def test_extractors_capture_stub_structure() -> None:
    code = """
import Mathlib
import Mathlib.Data.Real.Basic

axiom foo : Nat
variable (x : Nat)

theorem sample_theorem : x = x := by
  sorry

lemma helper_lemma : True := by
  admit
"""

    assert lean_repl._extract_imports(code) == [
        "Mathlib",
        "Mathlib.Data.Real.Basic",
    ]
    assert lean_repl._extract_declarations(code) == [
        "sample_theorem",
        "helper_lemma",
    ]
    assert lean_repl._extract_assumptions(code) == [
        "foo : Nat",
        "(x : Nat)",
    ]

    open_sites = lean_repl._extract_open_goal_sites(code)
    assert open_sites == [
        {"line": 9, "marker": "sorry", "snippet": "sorry"},
        {"line": 12, "marker": "admit", "snippet": "admit"},
    ]


def test_classify_and_summarize_attempt_detects_repeated_bottleneck() -> None:
    code = "theorem t : True := by\n  simp\n"
    lean_error = {
        "success": False,
        "errors": ["error: unknown identifier 'missing_lemma'"],
        "returncode": 1,
    }

    first = lean_repl._summarize_attempt(1, code, lean_error, None)
    second = lean_repl._summarize_attempt(2, code, lean_error, first)
    third = lean_repl._summarize_attempt(3, code, lean_error, second)

    assert first["error_classes"] == ["unknown_identifier"]
    assert first["progress_verdict"] == "initial"
    assert second["progress_verdict"] == "stalled"
    assert third["stall_streak"] == lean_repl.STALL_THRESHOLD
    assert third["bottleneck_label"] == "premise_retrieval"


def test_attempt_proof_writes_ledger_and_uses_structured_feedback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    prompts: list[str] = []
    responses = iter(
        [
            "theorem t : True := by\n  sorry\n",
            "theorem t : True := by\n  trivial\n",
        ]
    )

    class FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

    class FakeRuntime:
        def call_text(self, prompt: str, **_: object) -> FakeResponse:
            prompts.append(prompt)
            return FakeResponse(next(responses))

    lean_results = iter(
        [
            {
                "success": True,
                "errors": [],
                "stderr": "",
                "stderr_lines": [],
                "returncode": 0,
            },
            {
                "success": True,
                "errors": [],
                "stderr": "",
                "stderr_lines": [],
                "returncode": 0,
            },
        ]
    )

    monkeypatch.setattr(lean_repl, "LLMRuntime", FakeRuntime)
    monkeypatch.setattr(lean_repl, "resolve_model_id", lambda model: model)
    monkeypatch.setattr(lean_repl, "check_lean", lambda code: next(lean_results))

    project_dir = tmp_path / "demo_project"
    result = lean_repl.attempt_proof(
        "theorem t : True := by\n  sorry\n",
        max_attempts=2,
        model="gpt4.1",
        project_dir=project_dir,
    )

    assert result["proved"] is True
    assert result["attempts"] == 2
    assert "Structured feedback from previous attempt" in prompts[1]
    assert "status: compiles_with_sorry" in prompts[1]

    ledger_path = project_dir / "workspace" / lean_repl.LEDGER_FILENAME
    proof_path = project_dir / "workspace" / "verified_proof.lean"

    assert ledger_path.exists()
    assert proof_path.exists()

    ledger = result["proof_obligation_ledger"]
    assert len(ledger["attempts"]) == 2
    assert ledger["attempts"][0]["status"] == "compiles_with_sorry"
    assert ledger["attempts"][1]["status"] == "verified"
