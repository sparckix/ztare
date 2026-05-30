"""GP-119: Post-Champion Inverter Agent.

After a new champion is promoted, the Inverter agent receives the
champion thesis and proposes specific falsification TESTS (not
narrative skepticism). The tests run. The results decide. No
narrative kills.

The Inverter is a Popper agent, not a Munger agent:
- Popper: "Here is a specific test that would falsify this. Run it."
- Munger: "This seems suspicious. Are you sure?"
Munger narrative-kills good champions. Popper evidence-kills bad ones.

Architecture: post-champion hook inside autoresearch_loop.
Fires after champion_eval_results is written.
Results injected into derived_constraints.json.

Usage (called automatically by autoresearch_loop):
    from src.ztare.validator.inverter_agent import run_inverter
    result = run_inverter(project_dir, champion_thesis, champion_score)
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from src.ztare.common.llm_runtime import LLMRuntime, resolve_model_id


# The Inverter's prompt: Popper-style, not Munger-style.
# It must propose TESTS, not DOUBTS.
INVERTER_SYSTEM_PROMPT = """You are an epistemic review agent for scientific findings.
You operate in two modes, sequentially:

MODE 1 — MUNGER INVERSION (generate the counter-hypothesis):
Ask: "What would make this finding completely wrong?" Identify the
specific mechanism that could produce the same result as an artifact.
Be creative and adversarial. The best inversions identify measurement
artifacts, granularity mismatches, confounds with known phenomena,
or assumptions that were never tested.

MODE 2 — POPPER SPECIFICATION (design the test):
For each inversion from Mode 1, propose a SPECIFIC, EXECUTABLE test
with pre-committed pass/fail criteria. The test must be concrete
enough that a programmer could implement it without further guidance.

The key discipline: Mode 1 generates the DOUBT. Mode 2 converts
the doubt into a TEST. A doubt without a test is narrative
skepticism (harmful). A test without a doubt is busywork (wasteful).
Both modes are required for every proposed falsification.

Rules:
1. Every proposal must have BOTH a Munger inversion AND a Popper test.
2. Each test must have a pre-committed PASS/FAIL criterion.
3. You must propose at least one test from EACH of these categories:
   a) MEASUREMENT ARTIFACT: could the finding be an artifact of how
      the data was collected or processed?
   b) CONFOUND: is there an unmeasured variable that explains the result?
   c) GENERALIZATION: does the finding hold outside the specific
      conditions it was measured under?
4. If you cannot think of a plausible inversion, say so explicitly.
   "I cannot identify a mechanism that would make this wrong" is a
   legitimate output that STRENGTHENS the champion.
5. The Munger inversion may be speculative. The Popper test must be concrete.

Output format (JSON):
{
  "tests": [
    {
      "category": "measurement_artifact | confound | generalization",
      "munger_inversion": "What mechanism would make this wrong?",
      "popper_test": "The specific test to run",
      "procedure": "How to execute the test (concrete steps)",
      "pass_criterion": "If this result, the finding STANDS",
      "fail_criterion": "If this result, the finding is KILLED",
      "required_artifacts": ["specific artifact path or field needed to interpret the test"],
      "instrument_risk": "main way the proposed test could be uninterpretable",
      "auto_testable": true/false,
      "estimated_cost": "cheap | moderate | expensive"
    }
  ],
  "overall_assessment": "One sentence: how vulnerable is this champion?",
  "confidence_the_champion_survives": 0.0 to 1.0
}
"""


def _load_dag_weakest_node(project_dir: Path) -> str:
    """Read the probability DAG and return the weakest node as context for the Inverter.

    GP-123: The DAG tells the Inverter exactly WHERE the champion is
    most vulnerable. Without the DAG, the Inverter generates generic
    tests. With it, the Inverter targets the specific assumption that
    has the lowest probability.
    """
    dag_path = project_dir / "champion_probability_dag.json"
    if not dag_path.exists():
        dag_path = project_dir / "latest_probability_dag.json"
        if dag_path.exists():
            print("  🔬 WARNING: champion DAG not found, using latest DAG (may not match champion)")
    if not dag_path.exists():
        return ""

    try:
        dag = json.loads(dag_path.read_text())
        nodes = dag.get("nodes", [])
        if not nodes:
            return ""

        # Find weakest node
        weakest = min(nodes, key=lambda n: n.get("probability", 1.0))
        outcome = dag.get("outcome", {})

        lines = [
            "## Probability DAG (weakest assumptions)",
            f"Overall outcome probability: {outcome.get('probability', '?')}",
            f"WEAKEST NODE: {weakest.get('label', '?')} (p={weakest.get('probability', '?')})",
            f"Watch signal: {weakest.get('watch_signal', 'none specified')}",
            "",
            "All nodes:",
        ]
        for n in sorted(nodes, key=lambda n: n.get("probability", 1.0)):
            lines.append(f"  - {n.get('id', '?')}: {n.get('label', '?')} (p={n.get('probability', '?')})")

        return "\n".join(lines)
    except Exception:
        return ""


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if "```json" in stripped:
        return stripped.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in stripped:
        return stripped.split("```", 1)[1].split("```", 1)[0].strip()
    return stripped


def _extract_first_brace_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _salvage_inverter_tests(text: str) -> list[dict]:
    tests: list[dict] = []
    for category in ("measurement_artifact", "confound", "generalization"):
        if category not in text:
            continue
        block_start = text.find(f'"category": "{category}"')
        if block_start < 0:
            continue
        block = text[block_start:block_start + 1800]

        def _grab(field: str) -> str:
            m = re.search(rf'"{field}"\s*:\s*"([^"]*)"', block, flags=re.S)
            return m.group(1).strip() if m else ""

        tests.append(
            {
                "category": category,
                "munger_inversion": _grab("munger_inversion"),
                "popper_test": _grab("popper_test"),
                "procedure": _grab("procedure"),
                "pass_criterion": _grab("pass_criterion"),
                "fail_criterion": _grab("fail_criterion"),
                "required_artifacts": [],
                "instrument_risk": _grab("instrument_risk"),
                "auto_testable": False,
                "estimated_cost": _grab("estimated_cost") or "unknown",
                "salvaged_from_partial_json": True,
            }
        )
    return tests


def _parse_or_salvage_inverter_response(response_text: str) -> dict:
    cleaned = _strip_code_fences(response_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    candidate = _extract_first_brace_object(cleaned)
    if candidate:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    salvaged_tests = _salvage_inverter_tests(cleaned)
    if salvaged_tests:
        return {
            "tests": salvaged_tests,
            "overall_assessment": (
                "Inverter response was partial/truncated JSON; salvaged test proposals "
                "from the structured prefix"
            ),
            "confidence_the_champion_survives": 0.5,
            "partial_json_salvaged": True,
            "raw_response": cleaned[:4000],
        }

    raise json.JSONDecodeError("Could not parse inverter JSON", cleaned, 0)


def run_inverter(
    project_dir: Path,
    champion_thesis: str,
    champion_score: int,
    champion_weakest_point: str = "",
    evidence_summary: str = "",
    inverter_model: str = "gpt4.1",
    skip_if_score_below: int = 50,
) -> dict:
    """Run the Inverter agent on a newly promoted champion.

    Returns a dict with proposed tests, overall assessment, and
    confidence the champion survives.

    If the champion score is below skip_if_score_below, the Inverter
    skips (low-scoring champions are not worth falsifying — they'll
    be replaced soon).
    """
    if champion_score < skip_if_score_below:
        return {
            "skipped": True,
            "reason": f"Score {champion_score} < {skip_if_score_below}, not worth falsifying",
        }

    # GP-123: Load the probability DAG to target the weakest assumption
    dag_context = _load_dag_weakest_node(project_dir)

    # Build the user prompt with the champion's details
    user_prompt = f"""## Champion Thesis (score: {champion_score})

{champion_thesis}

## Weakest Point (identified by judge)

{champion_weakest_point}

## Evidence Summary

{evidence_summary if evidence_summary else "(not provided)"}

{dag_context}

## Your Task

Propose 2-4 specific falsification tests for this champion thesis.
Each test must have a pre-committed pass/fail criterion.
Focus on measurement artifacts, confounds, and generalization.
{"PRIORITY: Target the WEAKEST NODE in the probability DAG above. The node with the lowest probability is where the champion is most vulnerable." if dag_context else ""}
Output valid JSON matching the schema in your system prompt.
"""

    # Call the Inverter model (must be DIFFERENT from mutator/judge)
    runtime = LLMRuntime()
    model_id = resolve_model_id(inverter_model)

    print(f"  🔬 GP-119 Inverter: querying {inverter_model}...")

    try:
        full_prompt = f"{INVERTER_SYSTEM_PROMPT}\n\n{user_prompt}"
        llm_response = runtime.call_text(
            full_prompt,
            model_id=model_id,
            max_tokens=2000,
            request_label="gp119_inverter",
        )
        response = llm_response.text if hasattr(llm_response, 'text') else str(llm_response)

        # Parse the JSON response. Be robust to fenced JSON, trailing commentary,
        # and partial/truncated structured outputs: salvage structured tests when
        # possible rather than emitting an empty inverter review.
        response_text = response.strip()
        result = _parse_or_salvage_inverter_response(response_text)

    except json.JSONDecodeError:
        result = {
            "tests": [],
            "overall_assessment": "Inverter response was not valid JSON",
            "confidence_the_champion_survives": 0.5,
            "raw_response": response_text[:4000] if 'response_text' in dir() else "no response",
        }
    except Exception as e:
        result = {
            "tests": [],
            "overall_assessment": f"Inverter failed: {e}",
            "confidence_the_champion_survives": 0.5,
            "error": str(e),
        }

    # Log the result
    result["timestamp"] = datetime.now().isoformat()
    result["champion_score"] = champion_score
    result["inverter_model"] = inverter_model

    # Count test categories
    tests = result.get("tests", [])
    auto_tests = [t for t in tests if t.get("auto_testable")]
    result["total_tests_proposed"] = len(tests)
    result["auto_testable_count"] = len(auto_tests)

    # Save to workspace
    out_path = project_dir / "workspace" / "inverter_review.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))

    # GP-190: persist the "what should we test next?" object as a typed
    # queue artifact. The Inverter remains a proposal generator; this
    # deterministic translator makes the proposal replayable and auditable.
    try:
        from src.ztare.orchestrator.discriminator_queue import (
            append_discriminators,
            proposals_from_inverter_result,
        )

        proposals = proposals_from_inverter_result(
            project=project_dir.name,
            trigger_artifact="workspace/inverter_review.json",
            claim_under_pressure=(champion_thesis or "champion thesis")[:1200],
            inverter_result=result,
        )
        if proposals:
            q_path, q_count = append_discriminators(project_dir, proposals)
            result["next_discriminator_queue_path"] = str(q_path)
            result["next_discriminator_queue_count"] = q_count
            # Keep inverter_review.json self-describing after queue write.
            out_path.write_text(json.dumps(result, indent=2, default=str))
            print(f"  🔬 GP-190 queue: {q_count} discriminator proposal(s) appended")
    except Exception as exc:  # noqa: BLE001
        result["next_discriminator_queue_error"] = str(exc)[:300]
        out_path.write_text(json.dumps(result, indent=2, default=str))
        print(f"  🔬 GP-190 queue: failed to append discriminator proposals: {exc}")

    # Print summary
    confidence = result.get("confidence_the_champion_survives", 0.5)
    assessment = result.get("overall_assessment", "")
    print(f"  🔬 Inverter: {len(tests)} tests proposed ({len(auto_tests)} auto-testable)")
    print(f"  🔬 Confidence champion survives: {confidence:.0%}")
    print(f"  🔬 Assessment: {assessment[:100]}")

    # Inject auto-testable tests as constraints for the mutator
    # (so the mutator knows what the Inverter is watching for)
    if auto_tests:
        _inject_inverter_constraints(project_dir, auto_tests, champion_score)

    return result


def _inject_inverter_constraints(
    project_dir: Path,
    tests: list[dict],
    champion_score: int,
) -> None:
    """Inject Inverter-proposed tests into derived_constraints.json
    so the mutator is aware of what the Inverter is watching for."""

    dc_path = project_dir / "workspace" / "derived_constraints.json"
    if dc_path.exists():
        dc = json.loads(dc_path.read_text())
    else:
        dc = {
            "project": project_dir.name,
            "confirmed_constraints": [],
            "provisional_constraints": [],
            "confirmed_constraint_count": 0,
            "provisional_constraint_count": 0,
        }

    for test in tests:
        constraint = {
            "signature": f"inverter_{datetime.now().strftime('%H%M%S')}",
            "constraint": (
                f"INVERTER WATCH: {test.get('description', '')}. "
                f"Pass criterion: {test.get('pass_criterion', 'not specified')}. "
                f"Fail criterion: {test.get('fail_criterion', 'not specified')}."
            ),
            "applies_to": "champion thesis",
            "failure_family": f"inverter_{test.get('category', 'unknown')}",
            "severity": "enriching",  # NOT degrading — these are proposed tests, not confirmed failures
            "producer": "inverter_agent_gp119",
            "rationale": test.get("procedure", ""),
            "status": "provisional",
            "constraint_id": f"INV-{datetime.now().strftime('%H%M%S')}",
        }
        dc["provisional_constraints"] = dc.get("provisional_constraints", [])
        dc["provisional_constraints"].append(constraint)

    dc["provisional_constraint_count"] = len(dc.get("provisional_constraints", []))
    dc["updated_on"] = datetime.now().isoformat()
    dc_path.write_text(json.dumps(dc, indent=2, default=str))
