#!/usr/bin/env python3
"""Deterministic gate for proof-closure strategy candidates.

The gate is intentionally domain-light. A substrate can ask a mutator to emit
one fenced JSON object describing a proof-closure move, then use this script to
reject verbal recursion, missing evidence anchors, circular source routes, and
non-executable next steps before judge scoring.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

CLOSURE_MOVE_REQUIRED_FIELDS = (
    "id",
    "target_constructor",
    "theorem_endpoint",
    "source_route",
    "evidence_anchors",
    "non_circularity",
    "falsifier",
    "executable_next_step",
    "value_of_information",
    "secondary_observable",
    "recursive_update",
    "generalization_payload",
)

PROOF_PROGRESS_REQUIRED_FIELDS = (
    "id",
    "proof_state_summary",
    "progress_delta_since_last_run",
    "live_bottleneck",
    "pde_vocab_tags",
    "evidence_anchors",
    "diagnostic_confidence",
    "anti_tautology_check",
    "falsifier",
    "next_codex_action",
    "post_action_refresh",
    "belief_update",
    "recursive_learning",
    "generalization_payload",
)

FORBIDDEN_SOURCE_TERMS = (
    "GP216BridgeCompositionReceipt",
    "gp216_bridge_composition_receipt",
    "TrackBClosureFinalEndpoint",
    "final endpoint as premise",
    "assume the target",
    "assume closure",
)

EXECUTABLE_MARKERS = (
    "lake build",
    "lake env lean",
    "lean ",
    "scripts/public/",
    "./venv/bin/python",
    "python ",
    "pde_inequality_dimensional_gate",
    "mathlib_lemma_scout",
    "structure_instantiation_workmap",
)

KNOWN_TOOL_PATHS = {
    "pde_inequality_dimensional_gate": (
        "projects/ns_millennium_hunt/scripts/pde_inequality_dimensional_gate.py",
        "src/ztare/gates/pde_inequality_dimensional_gate.py",
    ),
    "proof_closure_candidate_gate": ("scripts/public/lean/proof_closure_candidate_gate.py",),
    "mathlib_lemma_scout": ("scripts/public/lean/mathlib_lemma_scout.py",),
    "structure_instantiation_workmap": ("scripts/public/lean/structure_instantiation_workmap.py",),
    "ns_graphs": ("projects/ns_millennium_hunt/scripts/ns_graph.py",),
}

KNOWN_SCRIPT_FLAGS = {
    "scripts/public/lean/proof_closure_candidate_gate.py": {
        "--candidate-file",
        "--repo-root",
        "--emit-deterministic-gates",
    },
    "projects/ns_millennium_hunt/scripts/pde_inequality_dimensional_gate.py": {
        "--inequality",
        "--allowed",
        "--allowed-json",
        "--dims-json",
        "--test-lifting",
        "--target",
        "--theorem-endpoint",
        "--pretty",
    },
    "scripts/public/lean/structure_instantiation_workmap.py": {
        "--graph",
        "--receipt-id",
        "--root-structure",
        "--out-json",
        "--out-meta-json",
        "--out-md",
        "--target",
        "--show-fields",
    },
    "scripts/public/lean/decomposition_candidate_enumerator.py": {
        "--field",
        "--lean-root",
        "--max-results",
        "--window-lines",
        "--json",
        "--logfile",
    },
}


def _extract_json_candidates(text: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for match in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL):
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            candidates.append(parsed)
    if candidates:
        return candidates

    # Fallback for a raw JSON-only thesis. Keep this conservative: if the
    # document contains prose around braces, malformed extraction should fail.
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, dict):
            return [parsed]
    return []


def _candidate_from_python_packet(path: Path) -> dict[str, Any] | None:
    """Load a Python theorem-packet candidate.

    This is intended for local candidate files emitted by the autoresearch
    loop. It is not used for arbitrary remote content, and it keeps the
    deterministic gate aligned with theorem-packet substrates that do not emit
    fenced JSON directly.
    """

    if path.suffix != ".py" or not path.exists():
        return None
    module_name = f"_proof_closure_candidate_{abs(hash(path.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(path.parent.resolve()))
        spec.loader.exec_module(module)
    except Exception:
        return None
    finally:
        sys.path[:] = old_path
    packet_fn = getattr(module, "proof_progress_review", None)
    if not callable(packet_fn):
        packet_fn = getattr(module, "closure_move_packet", None)
    if not callable(packet_fn):
        return None
    try:
        packet = packet_fn()
    except Exception:
        return None
    return packet if isinstance(packet, dict) else None


def _unwrap_candidate(raw: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    for key in ("proof_progress_review", "closure_move", "proof_closure_move", "candidate"):
        value = raw.get(key)
        if isinstance(value, dict):
            return key, value
    return "raw", raw


def _as_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _gate(name: str, passed: bool, reason: str, actual: float, threshold: float = 1.0) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "actual": actual,
        "threshold": threshold,
        "operator": "ge",
        "reason": reason,
    }


def _resolve_repo_path(path_text: str, repo_root: Path) -> Path | None:
    if not path_text:
        return None
    path = Path(path_text)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        return None
    return resolved


def _command_resolution_gate(command: str, repo_root: Path) -> tuple[bool, str]:
    """Conservatively verify that referenced repo-local tools exist.

    This is intentionally not a shell executor. It catches phantom commands
    such as `python scripts/public/missing_gate.py ...` while allowing opaque but
    standard commands like `lake build ...` to pass to the human/operator.
    """

    command = command.strip()
    if not command:
        return False, "empty command"
    if "lake build" in command or "lake env lean" in command:
        return True, "lake command"

    script_refs = set(re.findall(r"\b(?:scripts|src|ztare_proofs)/[A-Za-z0-9_./-]+\.(?:py|lean|sh)\b", command))
    missing: list[str] = []
    for ref in sorted(script_refs):
        resolved = _resolve_repo_path(ref, repo_root)
        if resolved is None or not resolved.exists():
            missing.append(ref)

    for tool_name, path_options in KNOWN_TOOL_PATHS.items():
        if tool_name not in command:
            continue
        if not any((repo_root / option).exists() for option in path_options):
            missing.append(f"{tool_name} ({' or '.join(path_options)})")

    if missing:
        return False, "missing referenced repo tool(s): " + ", ".join(sorted(set(missing)))

    try:
        tokens = shlex.split(command)
    except ValueError:
        return False, "command is not shell-tokenizable"

    unknown_flag_errors: list[str] = []
    for script_ref in sorted(script_refs):
        allowed_flags = KNOWN_SCRIPT_FLAGS.get(script_ref)
        if allowed_flags is None:
            continue
        if script_ref not in tokens:
            continue
        script_idx = tokens.index(script_ref)
        for tok in tokens[script_idx + 1:]:
            if tok in {";", "&&", "||"}:
                break
            if tok.startswith("--"):
                flag = tok.split("=", 1)[0]
                if flag not in allowed_flags:
                    unknown_flag_errors.append(f"{script_ref} does not accept {flag}")
    if unknown_flag_errors:
        return False, "; ".join(unknown_flag_errors)

    if script_refs or any(tool in command for tool in KNOWN_TOOL_PATHS):
        return True, "referenced repo-local tools resolve"

    # Last resort: accept simple commands whose executable token can be parsed
    # and whose safety was already screened by EXECUTABLE_MARKERS.
    if tokens and tokens[0] in {"python", "python3", "./venv/bin/python", "./venv/bin/python3", "rg"}:
        return True, "simple executable marker"
    return True, "no repo-local script path to verify"


def _closure_schema_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in CLOSURE_MOVE_REQUIRED_FIELDS if field not in candidate]
    if missing:
        return _gate(
            "closure_move_schema",
            False,
            f"missing required fields: {', '.join(missing)}",
            (len(CLOSURE_MOVE_REQUIRED_FIELDS) - len(missing)) / len(CLOSURE_MOVE_REQUIRED_FIELDS),
        )
    return _gate("closure_move_schema", True, "all required fields present", 1.0)


def _proof_progress_schema_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in PROOF_PROGRESS_REQUIRED_FIELDS if field not in candidate]
    if missing:
        return _gate(
            "proof_progress_review_schema",
            False,
            f"missing required fields: {', '.join(missing)}",
            (len(PROOF_PROGRESS_REQUIRED_FIELDS) - len(missing)) / len(PROOF_PROGRESS_REQUIRED_FIELDS),
        )
    return _gate("proof_progress_review_schema", True, "all required fields present", 1.0)


def _anchor_gate(candidate: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    anchors = candidate.get("evidence_anchors")
    if not isinstance(anchors, list) or not anchors:
        return _gate("evidence_anchors_resolve", False, "evidence_anchors must be a non-empty list", 0.0)

    failures: list[str] = []
    passed = 0
    for idx, anchor in enumerate(anchors):
        if not isinstance(anchor, dict):
            failures.append(f"anchor {idx} is not an object")
            continue
        path = _resolve_repo_path(str(anchor.get("path", "")), repo_root)
        pattern = str(anchor.get("pattern", "")).strip()
        if path is None:
            failures.append(f"anchor {idx} path is outside repo or empty")
            continue
        if not path.exists():
            failures.append(f"anchor {idx} path does not exist: {path.relative_to(repo_root)}")
            continue
        if not pattern:
            failures.append(f"anchor {idx} has empty pattern")
            continue
        try:
            body = path.read_text(errors="ignore")
        except OSError as exc:
            failures.append(f"anchor {idx} unreadable: {type(exc).__name__}")
            continue
        if pattern not in body:
            failures.append(f"anchor {idx} pattern not found in {path.relative_to(repo_root)}")
            continue
        passed += 1

    total = len(anchors)
    ok = passed == total
    reason = "all evidence anchors resolve" if ok else "; ".join(failures[:4])
    return _gate("evidence_anchors_resolve", ok, reason, passed / total if total else 0.0)


def _non_circularity_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    noncirc = candidate.get("non_circularity")
    if not isinstance(noncirc, dict):
        return _gate("source_route_non_circular", False, "non_circularity must be an object", 0.0)

    source_route_text = _as_text(candidate.get("source_route", {}))
    forbidden_hits = [term for term in FORBIDDEN_SOURCE_TERMS if term in source_route_text]
    has_forbidden_list = bool(noncirc.get("forbidden_backflow"))
    independence = str(noncirc.get("independence_check", "")).strip()
    if forbidden_hits:
        return _gate(
            "source_route_non_circular",
            False,
            f"source_route contains forbidden backflow terms: {', '.join(forbidden_hits)}",
            0.0,
        )
    if not has_forbidden_list or len(independence) < 24:
        return _gate(
            "source_route_non_circular",
            False,
            "must name forbidden_backflow and a concrete independence_check",
            0.5 if has_forbidden_list else 0.0,
        )
    return _gate("source_route_non_circular", True, "source route excludes final-endpoint backflow", 1.0)


def _falsifier_gate(candidate: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    falsifier = candidate.get("falsifier")
    if not isinstance(falsifier, dict):
        return _gate("falsifier_is_operational", False, "falsifier must be an object", 0.0)
    named_escape = str(falsifier.get("named_escape", "")).strip()
    command = str(
        falsifier.get("command_or_probe")
        or falsifier.get("command")
        or falsifier.get("lean_probe")
        or ""
    ).strip()
    if len(named_escape) < 8 or len(command) < 12:
        return _gate(
            "falsifier_is_operational",
            False,
            "falsifier must name an escape class and a command/probe",
            0.5 if named_escape else 0.0,
        )
    resolves, reason = _command_resolution_gate(command, repo_root)
    if not resolves:
        return _gate(
            "falsifier_is_operational",
            False,
            reason,
            0.5,
        )
    return _gate("falsifier_is_operational", True, "falsifier names an executable escape probe", 1.0)


def _next_step_gate(candidate: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    next_step = candidate.get("executable_next_step")
    if not isinstance(next_step, dict):
        return _gate("executable_next_step_defined", False, "executable_next_step must be an object", 0.0)
    mode = str(next_step.get("mode", "immediate_command")).strip() or "immediate_command"
    command = str(next_step.get("command", "")).strip()
    directive = str(next_step.get("research_directive", "")).strip()
    operationalization = str(next_step.get("operationalization", "")).strip()
    expected = str(next_step.get("expected_pass_or_fail", "")).strip()
    has_marker = any(marker in command for marker in EXECUTABLE_MARKERS)
    if mode == "strategic_directive":
        if len(directive) >= 24 and len(operationalization) >= 24 and expected:
            return _gate(
                "executable_next_step_defined",
                True,
                "next step is a source-anchored strategic directive with an operationalization trigger",
                1.0,
            )
        return _gate(
            "executable_next_step_defined",
            False,
            "strategic directive mode must include research_directive, operationalization, and expected outcome",
            0.5 if directive or operationalization else 0.0,
        )
    if not command or not expected or not has_marker:
        return _gate(
            "executable_next_step_defined",
            False,
            "next step must include a concrete repo command and expected pass/fail outcome",
            0.5 if command else 0.0,
        )
    resolves, reason = _command_resolution_gate(command, repo_root)
    if not resolves:
        return _gate(
            "executable_next_step_defined",
            False,
            reason,
            0.5,
        )
    return _gate("executable_next_step_defined", True, "next step is executable and outcome-typed", 1.0)


def _recursive_update_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    update = candidate.get("recursive_update")
    voi = candidate.get("value_of_information")
    if not isinstance(update, dict) or not isinstance(voi, dict):
        return _gate(
            "recursive_update_defined",
            False,
            "recursive_update and value_of_information must be objects",
            0.0,
        )
    has_tag = bool(str(update.get("failure_log_tag", "")).strip())
    has_fail_update = bool(str(update.get("if_fail_update", "")).strip())
    has_pass = bool(str(voi.get("if_pass", "")).strip())
    has_fail = bool(str(voi.get("if_fail", "")).strip())
    score = sum([has_tag, has_fail_update, has_pass, has_fail]) / 4
    if score < 1.0:
        return _gate(
            "recursive_update_defined",
            False,
            "must state failure_log_tag, if_fail_update, if_pass, and if_fail",
            score,
        )
    return _gate("recursive_update_defined", True, "candidate states how the loop learns from pass/fail", 1.0)


def _generalization_payload_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    payload = candidate.get("generalization_payload")
    if not isinstance(payload, dict):
        return _gate(
            "generalization_payload_defined",
            False,
            "generalization_payload must be an object",
            0.0,
        )
    applies_to = payload.get("applies_to")
    applies_ok = isinstance(applies_to, list) and bool(applies_to)
    artifact_to_update = str(payload.get("artifact_to_update", "")).strip()
    promotion_condition = str(payload.get("promotion_condition", "")).strip()
    do_not_promote_if = str(payload.get("do_not_promote_if", "")).strip()
    score = sum(
        [
            applies_ok,
            len(artifact_to_update) >= 4,
            len(promotion_condition) >= 16,
            len(do_not_promote_if) >= 16,
        ]
    ) / 4
    if score < 1.0:
        return _gate(
            "generalization_payload_defined",
            False,
            "must state applies_to, artifact_to_update, promotion_condition, and do_not_promote_if",
            score,
        )
    return _gate(
        "generalization_payload_defined",
        True,
        "candidate states when the local proof pattern becomes reusable apparatus",
        1.0,
    )


def _proof_state_summary_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    summary = candidate.get("proof_state_summary")
    delta = candidate.get("progress_delta_since_last_run")
    bottleneck = candidate.get("live_bottleneck")
    if not isinstance(summary, dict) or not isinstance(delta, dict) or not isinstance(bottleneck, dict):
        return _gate(
            "proof_state_summary_defined",
            False,
            "proof_state_summary, progress_delta_since_last_run, and live_bottleneck must be objects",
            0.0,
        )
    current_state = str(summary.get("current_state", "")).strip()
    not_progress = str(summary.get("not_progress", "")).strip()
    bottleneck_class = str(bottleneck.get("bottleneck_class", "")).strip()
    primary_target = str(
        bottleneck.get("primary_target")
        or bottleneck.get("target_constructor")
        or bottleneck.get("target")
        or ""
    ).strip()
    route_vs_closure = str(
        delta.get("route_compression_vs_closure")
        or delta.get("actual_delta")
        or delta.get("what_changed")
        or ""
    ).strip()
    score = sum(
        [
            len(current_state) >= 24,
            len(not_progress) >= 16,
            len(bottleneck_class) >= 4,
            len(primary_target) >= 4,
            len(route_vs_closure) >= 16,
        ]
    ) / 5
    if score < 1.0:
        return _gate(
            "proof_state_summary_defined",
            False,
            "review must distinguish actual proof state, non-progress, bottleneck class, primary target, and route-compression vs closure",
            score,
        )
    return _gate(
        "proof_state_summary_defined",
        True,
        "review names the live proof state and controlling bottleneck",
        1.0,
    )


def _anti_tautology_review_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    check = candidate.get("anti_tautology_check")
    if not isinstance(check, dict):
        return _gate(
            "anti_tautology_check_defined",
            False,
            "anti_tautology_check must be an object",
            0.0,
        )
    text = _as_text(check).lower()
    required_concepts = ("circular", "tautolog", "final", "self", "vacu")
    hits = [term for term in required_concepts if term in text]
    has_escape = len(str(check.get("would_be_invalid_if", "")).strip()) >= 16 or len(str(check.get("invalid_if", "")).strip()) >= 16
    score = min(1.0, (len(hits) / 3) * 0.75 + (0.25 if has_escape else 0.0))
    if score < 1.0:
        return _gate(
            "anti_tautology_check_defined",
            False,
            "must explicitly name circular/tautology/final-endpoint/self-reference or vacuity risk and a concrete invalidating condition",
            score,
        )
    return _gate(
        "anti_tautology_check_defined",
        True,
        "review includes an explicit non-circularity and vacuity check",
        1.0,
    )


def _belief_update_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    update = candidate.get("belief_update")
    confidence = candidate.get("diagnostic_confidence")
    if not isinstance(update, dict):
        return _gate(
            "belief_update_defined",
            False,
            "belief_update must be an object",
            0.0,
        )
    prior = str(update.get("prior", "")).strip()
    posterior = str(update.get("posterior", "")).strip()
    changed_action = str(
        update.get("changed_next_action")
        or update.get("action_delta")
        or update.get("what_codex_should_stop_doing")
        or ""
    ).strip()
    confidence_ok = bool(str(confidence).strip())
    score = sum([len(prior) >= 8, len(posterior) >= 8, len(changed_action) >= 16, confidence_ok]) / 4
    if score < 1.0:
        return _gate(
            "belief_update_defined",
            False,
            "must state prior, posterior, changed next action, and diagnostic_confidence",
            score,
        )
    return _gate(
        "belief_update_defined",
        True,
        "review states how the proof-state diagnosis changes Codex's next action",
        1.0,
    )


def _post_action_refresh_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    refresh = candidate.get("post_action_refresh")
    if not isinstance(refresh, dict):
        return _gate(
            "post_action_refresh_defined",
            False,
            "post_action_refresh must be an object",
            0.0,
        )
    text = _as_text(refresh)
    has_graph = "projects/ns_millennium_hunt/scripts/ns_graph.py all" in text
    has_workmap = "scripts/public/lean/structure_instantiation_workmap.py" in text
    has_pass = bool(
        str(refresh.get("pass_condition", "")).strip()
        or str(refresh.get("diff_criterion", "")).strip()
        or str(refresh.get("expected_delta", "")).strip()
    )
    score = sum([has_graph, has_workmap, has_pass]) / 3
    if score < 1.0:
        return _gate(
            "post_action_refresh_defined",
            False,
            "must name graph refresh, workmap refresh, and a concrete diff/pass criterion",
            score,
        )
    return _gate(
        "post_action_refresh_defined",
        True,
        "review includes post-action graph/workmap refresh with a diff criterion",
        1.0,
    )


def _next_codex_action_gate(candidate: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    action = candidate.get("next_codex_action")
    gate = _next_step_gate({"executable_next_step": action}, repo_root)
    gate = dict(gate)
    gate["name"] = "next_codex_action_defined"
    if gate["passed"]:
        gate["reason"] = "next_codex_action is executable or operationalized as a strategic directive"
    return gate


def _recursive_learning_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    learning = candidate.get("recursive_learning")
    if not isinstance(learning, dict):
        return _gate(
            "recursive_learning_defined",
            False,
            "recursive_learning must be an object",
            0.0,
        )
    tag = str(learning.get("failure_log_tag", "")).strip()
    if_wrong = str(
        learning.get("if_wrong_update")
        or learning.get("if_fail_update")
        or learning.get("substrate_update")
        or ""
    ).strip()
    do_not_update = str(learning.get("do_not_update_if", "")).strip()
    score = sum([len(tag) >= 4, len(if_wrong) >= 16, len(do_not_update) >= 16]) / 3
    if score < 1.0:
        return _gate(
            "recursive_learning_defined",
            False,
            "must state failure_log_tag, if_wrong_update, and do_not_update_if",
            score,
        )
    return _gate(
        "recursive_learning_defined",
        True,
        "review states how wrong diagnoses update the loop without overfitting",
        1.0,
    )


def _evaluate_proof_progress_review(candidate: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    gates = [
        _proof_progress_schema_gate(candidate),
        _proof_state_summary_gate(candidate),
        _anchor_gate(candidate, repo_root),
        _anti_tautology_review_gate(candidate),
        _falsifier_gate(candidate, repo_root),
        _next_codex_action_gate(candidate, repo_root),
        _post_action_refresh_gate(candidate),
        _belief_update_gate(candidate),
        _recursive_learning_gate(candidate),
        _generalization_payload_gate(candidate),
    ]
    return {"gates": gates}


def _evaluate_closure_move(candidate: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    gates = [
        _closure_schema_gate(candidate),
        _anchor_gate(candidate, repo_root),
        _non_circularity_gate(candidate),
        _falsifier_gate(candidate, repo_root),
        _next_step_gate(candidate, repo_root),
        _recursive_update_gate(candidate),
        _generalization_payload_gate(candidate),
    ]
    return {"gates": gates}


def evaluate_candidate_text(text: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    raw_candidates = _extract_json_candidates(text)
    if not raw_candidates:
        gates = [
            _gate(
                name,
                False,
                "no fenced JSON proof-closure candidate found",
                0.0,
            )
            for name in (
                "proof_progress_review_schema",
                "evidence_anchors_resolve",
                "anti_tautology_check_defined",
                "falsifier_is_operational",
                "next_codex_action_defined",
                "post_action_refresh_defined",
                "belief_update_defined",
                "recursive_learning_defined",
                "generalization_payload_defined",
            )
        ]
        return {"gates": gates, "candidate_count": 0}

    candidate_kind, candidate = _unwrap_candidate(raw_candidates[0])
    if candidate_kind == "proof_progress_review":
        result = _evaluate_proof_progress_review(candidate, repo_root)
    else:
        result = _evaluate_closure_move(candidate, repo_root)
    result["candidate_count"] = len(raw_candidates)
    result["candidate_kind"] = candidate_kind
    return result


def evaluate_candidate_file(path: Path, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    packet = _candidate_from_python_packet(path)
    if packet is not None:
        text = "```json\n" + json.dumps(packet, indent=2, sort_keys=True) + "\n```"
    else:
        text = path.read_text(errors="ignore")
    return evaluate_candidate_text(text, repo_root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-file", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--emit-deterministic-gates", action="store_true")
    args = parser.parse_args()

    result = evaluate_candidate_file(args.candidate_file, args.repo_root.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))

    if args.emit_deterministic_gates:
        return 0
    return 0 if all(gate["passed"] for gate in result["gates"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
