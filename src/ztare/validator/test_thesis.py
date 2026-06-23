import os
import json
import argparse
import time
import subprocess
import tempfile
import hashlib
import concurrent.futures
import sys
from pathlib import Path
from google.genai import types
from ztare.common import utils
from ztare.common.llm_runtime import (
    LLMTextResponse,
    LLMRuntime,
    LLMUsage,
    MODEL_FAMILY_CHOICES,
    PRODUCTION_CALL_RETRIES,
    get_model_family,
    pricing_model_name,
    resolve_model_id,
)
from ztare.common.dispatch_model import (
    dispatch_env_for_call_site,
    dispatch_model,
    dispatch_result_receipt,
    resolve_dispatch_capability,
)
from ztare.common.paths import PROJECTS_DIR, REPO_ROOT, RUBRICS_DIR
import re
from ztare.primitives.primitive_library import (
    format_attack_templates,
    format_judge_guardrail,
    retrieve_primitives,
    retrieve_primitives_by_keys,
)
from ztare.validator.core.primitive_routing import route_primitives_for_v4
from ztare.gates.semantic_gate_stabilization import (
    derive_self_reference_gate,
    persist_semantic_gate_analysis,
)
from ztare.findings.proxy_signature import compute_anchor_proxy_coverage
from ztare.validator.core.charter_parsing import (
    extract_anchor_proxies_from_charter,
    extract_asymptotic_claim_contract_from_charter,
    extract_forecast_type_from_charter,
)
from ztare.gates.asymptotic_claim_discipline import (
    assess_asymptotic_claim_discipline,
)
from ztare.gates.deterministic_charter_gates import (
    declared_gate_names,
    evaluate_deterministic_charter_gates,
    gate_results_to_dicts,
    soft_cap_entries_for_evaluation,
)
from ztare.validator.utilities.harness_failure_mode import (
    FAIL_ASSERT,
    FAIL_OTHER,
    FAIL_RUNTIME,
    classify_harness_failure,
    harness_defect_banner,
    sanitize_stderr_for_mutator,
)
from ztare.validator.core.meta_judge_schema import (
    RAW_META_JUDGE_REQUIRED_FIELDS,
    coerce_raw_meta_judge_score as _coerce_raw_meta_judge_score,
    raw_meta_judge_shape_errors as _raw_meta_judge_shape_errors,
)
from ztare.gates.derived_constraints import (
    render_confirmed_constraints_prompt_section,
    sanitize_constraint_proposals,
)
from ztare.validator.core.rubric_score_caps import (
    apply_evidence_gap_score_caps,
)
from ztare.workspace.evidence_gaps import (
    canonicalize_evidence_gap_recovery_contract,
)
from ztare.supervisor.supervisor_usage import estimate_cost_usd, load_model_pricing
from ztare.validator.utilities.v4_family import is_v4_family_project

# 1. Setup & Args
parser = argparse.ArgumentParser()
parser.add_argument("--project", required=True)
parser.add_argument("--rubric", default=None, help="Rubric name (defaults to --project value)")
parser.add_argument("--dynamic", action="store_true")
parser.add_argument(
    "--judge_model",
    type=str,
    default="gemini",
    choices=MODEL_FAMILY_CHOICES,
)
parser.add_argument(
    "--mutator_model",
    type=str,
    default="gemini",
    choices=MODEL_FAMILY_CHOICES,
)
parser.add_argument("--use_primitives", action="store_true")
parser.add_argument(
    "--primitive_routing_profile",
    choices=["v4"],
    help="Optional routing profile for primitive-enabled evaluation. `v4` enables exploit-family routing outside the canonical project name.",
)
parser.add_argument("--use_mutator_primitives", action="store_true")
parser.add_argument("--use_transfer_hypotheses", action="store_true")
parser.add_argument(
    "--crux_first_primitives",
    action="store_true",
    help="Identify the crux claim / eigenquestion before injecting primitive context into the meta-judge.",
)
parser.add_argument("--primitive_top_k", type=int, default=3)
parser.add_argument(
    "--disable_attacker_tools",
    action="store_true",
    help="Disable Gemini automatic function-calling for the default attacker path. Useful for benchmark runs where specimen code names can collide with tool-calling.",
)
parser.add_argument(
    "--deterministic_score_gates",
    action="store_true",
    help="Use Python-enforced hard gates and criterion booleans instead of trusting a raw LLM score.",
)
parser.add_argument(
    "--eval_results_path",
    default="eval_results.json",
    help="Path to write the final evaluation JSON. Defaults to eval_results.json in the current working directory.",
)
parser.add_argument(
    "--llm_timeout_seconds",
    type=int,
    default=int(os.environ.get("ZTARE_AUTORESEARCH_LLM_TIMEOUT_SECONDS", "300")),
    help="Per-call LLM timeout for judge calls.",
)
parser.add_argument(
    "--llm_retries",
    type=int,
    default=int(os.environ.get("ZTARE_AUTORESEARCH_LLM_RETRIES", str(PRODUCTION_CALL_RETRIES))),
    help="Per-call retry budget for judge calls.",
)
parser.add_argument(
    "--thesis_path_override",
    default=None,
    help="If set, read thesis from this path instead of current_iteration.md. "
         "Used by the post-run synthesizer to score candidate theses without "
         "modifying the live working path.",
)
args = parser.parse_known_args()[0]
if args.rubric is None:
    args.rubric = args.project
if getattr(args, "use_transfer_hypotheses", False):
    args.use_mutator_primitives = True
if args.use_mutator_primitives:
    args.use_primitives = True

JUDGE_MODEL_ID = resolve_model_id(args.judge_model)
JUDGE_PROVIDER_FAMILY = get_model_family(JUDGE_MODEL_ID)
MUTATOR_MODEL_ID = args.mutator_model
print(f"⚖️  Judge: {JUDGE_MODEL_ID}")
print(f"🧬 Mutator: {MUTATOR_MODEL_ID}")

RUNTIME = LLMRuntime()

# Keep legacy `client` pointing to Gemini for ATTACKER_CONFIG function calling
client = RUNTIME.require_gemini_client()
JUDGE_USAGE = {
    "model_name": None,
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "estimated_cost_usd": 0.0,
    "cost_known": False,
}
JUDGE_EFFECTIVE_MODELS_USED: set[str] = set()
JUDGE_FALLBACK_EVENTS: list[dict[str, str]] = []
JUDGE_WORKER_DISPATCH_RECEIPTS: list[dict[str, object]] = []


def _load_v4_stage_index() -> int | None:
    if not is_v4_family_project(args.project):
        return None
    state_path = Path("projects") / args.project / "meta_runner_state.json"
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text()).get("current_stage")
    except Exception:
        return None
PROJECT_DIR = str(PROJECTS_DIR / args.project)
WORKING_PATH = (
    args.thesis_path_override
    if getattr(args, "thesis_path_override", None)
    else f"{PROJECT_DIR}/current_iteration.md"
)
EVIDENCE_PATH = f"{PROJECT_DIR}/evidence.txt"
PROJECT_CHARTER_PATH = f"{PROJECT_DIR}/project_charter.md"
WORKSPACE_DIR = f"{PROJECT_DIR}/workspace"
LATEST_EVAL_RESULTS_PATH = f"{PROJECT_DIR}/latest_eval_results.json"
LATEST_PROBABILITY_DAG_PATH = f"{PROJECT_DIR}/latest_probability_dag.json"
LATEST_EVIDENCE_GAPS_PATH = f"{WORKSPACE_DIR}/latest_evidence_gaps.json"
LATEST_CONSTRAINT_PROPOSALS_PATH = f"{WORKSPACE_DIR}/latest_constraint_proposals.json"
DERIVED_CONSTRAINTS_PATH = f"{WORKSPACE_DIR}/derived_constraints.json"
MAIN_RUBRIC_PATH = str(RUBRICS_DIR / f"{args.rubric}.json")
DYNAMIC_RUBRIC_PATH = str(RUBRICS_DIR / f"dynamic_{args.project}.json")
SCORE_REGIME_VERSION_MAP = {
    "deterministic_gates": 7,
    "raw_llm_score": 1,
}
ANCHOR_PROXY_MIN_COVERAGE = 0.5
test_path = f"{PROJECT_DIR}/test_model.py"
EVIDENCE_GAP_TYPES = {
    "missing_external_comparator",
    "missing_threshold_grounding",
    "missing_independent_taxonomy",
    "missing_external_validation",
    "missing_rival_mechanism",
    "missing_scope_boundary_evidence",
    "other",
}
EVIDENCE_GAP_SEVERITIES = {"blocking", "degrading", "enriching"}
EVIDENCE_GAP_PRODUCERS = {"meta_judge", "verification_gate", "adjudicator", "inferred"}

# --- HELPER FUNCTIONS ---
def read_file(filepath):
    with open(filepath, "r") as f:
        return f.read()


def read_optional_file(filepath):
    if not os.path.exists(filepath):
        return None
    return read_file(filepath)


test_code_content = (
    read_file(test_path) if os.path.exists(test_path) else "No code provided."
)
project_charter_content = read_optional_file(PROJECT_CHARTER_PATH)
project_charter_anchor_proxies = extract_anchor_proxies_from_charter(project_charter_content)
project_charter_forecast_type = extract_forecast_type_from_charter(project_charter_content)
project_charter_asymptotic_contract = extract_asymptotic_claim_contract_from_charter(
    project_charter_content
)


def _normalize_evidence_gap_type(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return normalized if normalized in EVIDENCE_GAP_TYPES else "other"


def _normalize_evidence_gap_severity(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return normalized if normalized in EVIDENCE_GAP_SEVERITIES else "degrading"


def _normalize_evidence_gap_producer(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return normalized if normalized in EVIDENCE_GAP_PRODUCERS else "meta_judge"


def _infer_fetch_query(gap_type: str, target: str, description: str) -> str:
    base = f"{target} {description}".strip().lower()
    if gap_type == "missing_external_comparator":
        return f"{base} historical comparator case contrary evidence".strip()
    if gap_type == "missing_threshold_grounding":
        return f"{base} threshold historical range contrary evidence".strip()
    if gap_type == "missing_independent_taxonomy":
        return f"{base} external classification framework taxonomy".strip()
    if gap_type == "missing_external_validation":
        return f"{base} external validation comparative case".strip()
    if gap_type == "missing_rival_mechanism":
        return f"{base} rival mechanism evidence counterexample".strip()
    if gap_type == "missing_scope_boundary_evidence":
        return f"{base} scope boundary counterexample".strip()
    return f"{base} counterexample evidence".strip()


def _build_evidence_gap(
    *,
    gap_type: str,
    target: str,
    description: str,
    severity: str = "degrading",
    producer: str = "meta_judge",
    producer_rationale: str = "",
    fetch_query: str | None = None,
    adversarial_direction: bool = True,
    recovery_kind: str | None = None,
    recovery_channel: str | None = None,
    required_surface: str | None = None,
    can_public_fetch: bool | None = None,
    in_loop_consumable: bool | None = None,
) -> dict:
    target = (target or "").strip() or "unspecified_target"
    description = (description or "").strip() or "No description provided."
    producer_rationale = (producer_rationale or "").strip() or description
    gap_type = _normalize_evidence_gap_type(gap_type)
    severity = _normalize_evidence_gap_severity(severity)
    producer = _normalize_evidence_gap_producer(producer)
    gap = {
        "gap_type": gap_type,
        "target": target,
        "description": description,
        "severity": severity,
        "producer": producer,
        "producer_rationale": producer_rationale,
        "fetch_query": (fetch_query or _infer_fetch_query(gap_type, target, description)).strip(),
        "adversarial_direction": bool(adversarial_direction),
    }
    return canonicalize_evidence_gap_recovery_contract(
        gap,
        recovery_kind=recovery_kind,
        recovery_channel=recovery_channel,
        required_surface=required_surface,
        can_public_fetch=can_public_fetch,
        in_loop_consumable=in_loop_consumable,
    )


def _judge_format_error_evaluation(malformed_payload: object, errors: list[str]) -> dict:
    gap_text = ""
    evidence_gaps: list[dict] = []
    if isinstance(malformed_payload, dict) and any(
        field in malformed_payload for field in ("gap_type", "target", "description")
    ):
        gap_type = str(malformed_payload.get("gap_type", "other") or "other")
        target = str(malformed_payload.get("target", "") or "malformed judge payload")
        description = str(
            malformed_payload.get("description", "")
            or malformed_payload.get("producer_rationale", "")
            or "Judge returned an evidence-gap object where a verdict object was required."
        )
        severity = str(malformed_payload.get("severity", "blocking") or "blocking")
        producer = str(malformed_payload.get("producer", "meta_judge") or "meta_judge")
        evidence_gaps.append(
            _build_evidence_gap(
                gap_type=gap_type,
                target=target,
                description=description,
                severity=severity,
                producer=producer,
                producer_rationale=str(
                    malformed_payload.get("producer_rationale", "") or description
                ),
                fetch_query=str(malformed_payload.get("fetch_query", "") or "") or None,
                adversarial_direction=bool(
                    malformed_payload.get("adversarial_direction", True)
                ),
            )
        )
        gap_text = f" Judge gap type: {gap_type} | target={target} | {description}"

    return {
        "score": 0,
        "weakest_point": (
            "JUDGE_FORMAT_ERROR: raw judge returned valid JSON with the wrong "
            f"top-level schema after retry; defects={errors}.{gap_text}"
        ),
        "verified_axioms": [],
        "retired_axioms_approved": [],
        "evidence_gaps": evidence_gaps,
        "derived_constraints": [],
        "logic_gaps": [
            "Judge returned valid JSON that was not a meta-judge verdict object."
        ],
        "debate_summary": (
            "Judge-format failure. Treat this as an apparatus error, not a scientific "
            "verdict or thesis demotion."
        ),
        "adversarial_alignment": "",
        "friction_points": [],
        "probability_dag": {
            "outcome": {"label": "judge_format_error", "probability": 0.0},
            "nodes": [],
            "edges": [],
        },
        "judge_format_error": True,
        "score_cap_reason": "judge_format_error_wrong_top_level_schema",
        "judge_format_errors": list(errors),
        "malformed_judge_payload": malformed_payload,
    }


def _infer_evidence_gaps_from_text(evaluation: dict) -> list[dict]:
    inferred: list[dict] = []
    weakest_point = str(evaluation.get("weakest_point", "") or "")
    logic_gaps = [str(item) for item in evaluation.get("logic_gaps", [])]
    all_text = " ".join([weakest_point] + logic_gaps).lower()

    if "comparator" in all_text:
        inferred.append(
            _build_evidence_gap(
                gap_type="missing_external_comparator",
                target="external comparator",
                description=weakest_point or "Need an external comparator to test the current boundary.",
                severity="blocking",
                producer="inferred",
            )
        )
    if any(token in all_text for token in ["threshold", "sizeable", "sufficient", "material fiscal", "fiscal capacity"]):
        inferred.append(
            _build_evidence_gap(
                gap_type="missing_threshold_grounding",
                target="threshold grounding",
                description=weakest_point or "Need independent threshold grounding.",
                severity="blocking",
                producer="inferred",
            )
        )
    if any(token in all_text for token in ["taxonomy", "classification", "ontology", "external validation"]):
        inferred.append(
            _build_evidence_gap(
                gap_type="missing_external_validation",
                target="external validation",
                description=weakest_point or "Need external validation of the classification boundary.",
                severity="blocking",
                producer="inferred",
            )
        )
    if "rival" in all_text:
        inferred.append(
            _build_evidence_gap(
                gap_type="missing_rival_mechanism",
                target="rival mechanism",
                description=weakest_point or "Need external evidence addressing the rival mechanism.",
                severity="degrading",
                producer="inferred",
            )
        )

    deduped: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for gap in inferred:
        key = (gap["gap_type"], gap["target"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(gap)
    return deduped


def sanitize_evidence_gaps(evaluation: dict) -> list[dict]:
    raw_gaps = evaluation.get("evidence_gaps")
    cleaned: list[dict] = []
    if isinstance(raw_gaps, list):
        for item in raw_gaps:
            if not isinstance(item, dict):
                continue
            cleaned.append(
                _build_evidence_gap(
                    gap_type=str(item.get("gap_type", "other")),
                    target=str(item.get("target", "") or ""),
                    description=str(item.get("description", "") or ""),
                    severity=str(item.get("severity", "degrading")),
                    producer=str(item.get("producer", "meta_judge")),
                    producer_rationale=str(item.get("producer_rationale", "") or ""),
                    fetch_query=str(item.get("fetch_query", "") or "") or None,
                    adversarial_direction=bool(item.get("adversarial_direction", True)),
                    recovery_kind=str(item.get("recovery_kind", "") or "") or None,
                    recovery_channel=str(item.get("recovery_channel", "") or "") or None,
                    required_surface=str(item.get("required_surface", "") or "") or None,
                    can_public_fetch=item.get("can_public_fetch"),
                    in_loop_consumable=item.get("in_loop_consumable"),
                )
            )
    if not cleaned:
        cleaned = _infer_evidence_gaps_from_text(evaluation)
    return cleaned


def _score_regime_fingerprint_from_evaluation(evaluation: dict) -> str:
    score_contract = evaluation.get("score_contract", {})
    if not isinstance(score_contract, dict):
        return ""
    fingerprint = score_contract.get("regime_fingerprint")
    return str(fingerprint).strip() if fingerprint else ""


def _evaluation_artifact_payload(evaluation: dict, *, artifact_role: str) -> dict:
    payload = dict(evaluation)
    payload["artifact_role"] = artifact_role
    payload["describes_baseline"] = artifact_role
    fingerprint = _score_regime_fingerprint_from_evaluation(evaluation)
    if fingerprint:
        payload["score_regime_fingerprint"] = fingerprint
    return payload


def persist_evidence_gap_artifact(evaluation: dict, *, artifact_role: str = "latest", output_path: Path | None = None) -> None:
    workspace_dir = Path(WORKSPACE_DIR)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    gap_path = output_path or Path(LATEST_EVIDENCE_GAPS_PATH)
    gaps = sanitize_evidence_gaps(evaluation)
    fingerprint = _score_regime_fingerprint_from_evaluation(evaluation)
    payload = {
        "project": args.project,
        "judge_model": JUDGE_MODEL_ID,
        "generated_on": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifact_role": artifact_role,
        "describes_baseline": artifact_role,
        "score": evaluation.get("score"),
        "weakest_point": evaluation.get("weakest_point", ""),
        "evidence_boundary_ceiling_detected": bool(
            evaluation.get("score_contract", {}).get("evidence_boundary_ceiling_detected", False)
        ),
        "cap_reason": evaluation.get("score_contract", {}).get("cap_reason", "none"),
        "cap_reason_detail": evaluation.get("score_contract", {}).get("cap_reason_detail", ""),
        "score_regime_fingerprint": fingerprint,
        "evidence_gaps": gaps,
    }
    gap_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _evidence_gap_response_schema() -> dict:
    return {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "gap_type": {"type": "STRING"},
                "target": {"type": "STRING"},
                "description": {"type": "STRING"},
                "severity": {"type": "STRING"},
                "producer": {"type": "STRING"},
                "producer_rationale": {"type": "STRING"},
                "fetch_query": {"type": "STRING"},
                "adversarial_direction": {"type": "BOOLEAN"},
                "recovery_kind": {"type": "STRING"},
                "recovery_channel": {"type": "STRING"},
                "required_surface": {"type": "STRING"},
                "can_public_fetch": {"type": "BOOLEAN"},
                "in_loop_consumable": {"type": "BOOLEAN"},
            },
            "required": [
                "gap_type",
                "target",
                "description",
                "severity",
                "producer",
                "producer_rationale",
                "fetch_query",
                "adversarial_direction",
                "recovery_kind",
                "recovery_channel",
                "required_surface",
                "can_public_fetch",
                "in_loop_consumable",
            ],
        },
    }


def attach_evidence_gap_metadata(evaluation: dict) -> dict:
    gaps = sanitize_evidence_gaps(evaluation)
    blocking = [gap for gap in gaps if gap.get("severity") == "blocking"]
    degrading = [gap for gap in gaps if gap.get("severity") == "degrading"]
    enriching = [gap for gap in gaps if gap.get("severity") == "enriching"]

    existing = evaluation.get("score_contract")
    if not isinstance(existing, dict):
        existing = {}

    existing.update(
        {
            "evidence_gap_count": len(gaps),
            "blocking_evidence_gap_count": len(blocking),
            "degrading_evidence_gap_count": len(degrading),
            "enriching_evidence_gap_count": len(enriching),
            "evidence_gap_types": sorted({str(gap.get("gap_type", "other")) for gap in gaps}),
            "evidence_gap_targets": [str(gap.get("target", "")) for gap in gaps if gap.get("target")],
            "evidence_boundary_ceiling_detected": bool(blocking),
            "evidence_boundary_detail": "; ".join(
                f"{gap.get('gap_type', 'other')}::{gap.get('target', 'unspecified_target')}"
                for gap in blocking[:3]
            ),
        }
    )
    evaluation["evidence_gaps"] = gaps
    evaluation["score_contract"] = existing
    return evaluation


def persist_constraint_proposal_artifact(
    evaluation: dict,
    *,
    artifact_role: str = "latest",
    output_path: Path | None = None,
) -> None:
    workspace_dir = Path(WORKSPACE_DIR)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = output_path or Path(LATEST_CONSTRAINT_PROPOSALS_PATH)
    proposals = sanitize_constraint_proposals(evaluation.get("derived_constraints"))
    fingerprint = _score_regime_fingerprint_from_evaluation(evaluation)
    payload = {
        "project": args.project,
        "judge_model": JUDGE_MODEL_ID,
        "generated_on": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifact_role": artifact_role,
        "describes_baseline": artifact_role,
        "score": evaluation.get("score"),
        "weakest_point": evaluation.get("weakest_point", ""),
        "score_regime_fingerprint": fingerprint,
        "derived_constraints": proposals,
    }
    proposal_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def attach_constraint_proposal_metadata(evaluation: dict) -> dict:
    proposals = sanitize_constraint_proposals(evaluation.get("derived_constraints"))
    existing = evaluation.get("score_contract")
    if not isinstance(existing, dict):
        existing = {}
    existing.update(
        {
            "derived_constraint_proposal_count": len(proposals),
            "derived_constraint_failure_families": sorted(
                {str(item.get("failure_family", "other")) for item in proposals}
            ),
            "derived_constraint_targets": [
                str(item.get("applies_to", ""))
                for item in proposals
                if item.get("applies_to")
            ],
        }
    )
    evaluation["derived_constraints"] = proposals
    evaluation["score_contract"] = existing
    return evaluation

def _accumulate_judge_usage(
    *,
    model_name,
    input_tokens,
    output_tokens,
    cache_creation_input_tokens=0,
    cache_read_input_tokens=0,
    direct_cost_usd=None,
):
    JUDGE_USAGE["model_name"] = model_name or JUDGE_USAGE["model_name"] or JUDGE_MODEL_ID
    input_tokens = int(input_tokens or 0)
    output_tokens = int(output_tokens or 0)
    cache_creation_input_tokens = int(cache_creation_input_tokens or 0)
    cache_read_input_tokens = int(cache_read_input_tokens or 0)
    JUDGE_USAGE["input_tokens"] += input_tokens
    JUDGE_USAGE["output_tokens"] += output_tokens
    JUDGE_USAGE["cache_creation_input_tokens"] += cache_creation_input_tokens
    JUDGE_USAGE["cache_read_input_tokens"] += cache_read_input_tokens
    pricing = load_model_pricing()
    estimated_cost = (
        float(direct_cost_usd)
        if direct_cost_usd is not None
        else estimate_cost_usd(
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
        )
    )
    JUDGE_USAGE["estimated_cost_usd"] += estimated_cost
    normalized_model_name = pricing_model_name(model_name)
    if direct_cost_usd is not None or (normalized_model_name is not None and normalized_model_name in pricing):
        JUDGE_USAGE["cost_known"] = True


def _prompt_with_response_config_hint(prompt: str, config) -> str:
    if config is None:
        return prompt
    response_mime = getattr(config, "response_mime_type", None)
    response_schema = getattr(config, "response_schema", None)
    if not response_mime and response_schema is None:
        return prompt
    try:
        schema_text = json.dumps(response_schema, default=str, indent=2) if response_schema is not None else ""
    except TypeError:
        schema_text = str(response_schema)
    return (
        prompt.rstrip()
        + "\n\nRESPONSE CONTRACT FOR SUBSCRIPTION WORKER:\n"
        + (f"- MIME/type expectation: {response_mime}\n" if response_mime else "")
        + (
            "- Return only a JSON value matching this schema. No markdown, "
            "no code fences, no explanatory preamble.\n"
            f"{schema_text}\n"
            if schema_text
            else ""
        )
    )


def safe_generate(prompt, config=None, model_id=None):
    """Exponential backoff with dynamic model routing."""
    if model_id is None:
        model_id = JUDGE_MODEL_ID
    capability = resolve_dispatch_capability("judge")
    if capability == "agent":
        result = dispatch_model(
            _prompt_with_response_config_hint(prompt, config),
            capability="agent",
            fungible=True,
            stateful=False,
            backend=os.environ.get("ZTARE_AUTORESEARCH_JUDGE_AGENT_RUNTIME"),
            repo=REPO_ROOT,
            agent_id=f"autoresearch_judge_{args.project}",
            timeout_seconds=int(os.environ.get("ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS", "600")),
            enabled_env=dispatch_env_for_call_site("judge"),
        )
        effective_model_name = f"{result.transport}:{result.command[0] if result.command else 'agent'}"
        JUDGE_EFFECTIVE_MODELS_USED.add(effective_model_name)
        JUDGE_USAGE["model_name"] = effective_model_name
        if result.returncode != 0:
            raise RuntimeError(
                "subscription judge dispatch failed "
                f"(returncode={result.returncode}): {result.stderr[:1200]}"
            )
        JUDGE_WORKER_DISPATCH_RECEIPTS.append(
            dispatch_result_receipt("judge", result)
        )
        if result.recovery_note:
            print(f"🔁 Subscription judge recovery: {result.recovery_note}")
        return LLMTextResponse(
            text=result.text,
            model_name=effective_model_name,
            usage=LLMUsage(model_name=effective_model_name),
            raw_response=result,
            requested_model_id=model_id,
            effective_model_id=effective_model_name,
        )
    if capability != "llm":
        raise ValueError(f"unsupported judge dispatch capability: {capability}")
    response = RUNTIME.call_text(
        prompt,
        model_id=model_id,
        config=config,
        retries=args.llm_retries,
        timeout_seconds=args.llm_timeout_seconds,
        request_label="request",
        progress_printer=print,
        transient_wait_seconds=20,
        timeout_wait_seconds=15,
    )
    effective_model_name = response.usage.model_name or response.effective_model_id or model_id
    canonical_effective_model = pricing_model_name(effective_model_name) or effective_model_name
    JUDGE_EFFECTIVE_MODELS_USED.add(canonical_effective_model)
    if response.fallback_from_model_id:
        fallback_event = {
            "from": response.fallback_from_model_id,
            "to": canonical_effective_model,
        }
        if fallback_event not in JUDGE_FALLBACK_EVENTS:
            JUDGE_FALLBACK_EVENTS.append(fallback_event)
    _accumulate_judge_usage(
        model_name=response.usage.model_name or model_id,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cache_creation_input_tokens=response.usage.cache_creation_input_tokens,
        cache_read_input_tokens=response.usage.cache_read_input_tokens,
        direct_cost_usd=response.usage.direct_cost_usd,
    )
    return response

# --- LEVEL 3: THE TOOL ---
# SECURITY: this runs attacker-authored code. It used to cwd into REPO_ROOT
# with PYTHONPATH=REPO_ROOT, which let a gemini-pro attacker exfiltrate the
# full repo (sibling projects' test_model.py, AGENTS.md, git status, etc.)
# by writing a "counter-test" that just calls os.listdir / subprocess find.
# That is a contamination vector in any paired A/B experiment where sealed
# hash sets define the mutator-visible fileset — the attacker path bypasses
# the seal. We now execute inside an isolated tempdir with a stripped env,
# so the attacker's python has no ambient view of the repo.
def execute_python_code(code: str) -> str:
    """Executes attacker-authored Python code inside an isolated sandbox dir."""
    sandbox_dir = tempfile.mkdtemp(prefix="ztare_attacker_sbx_")
    tmp_path = os.path.join(sandbox_dir, "counter_test.py")
    with open(tmp_path, "w") as tmp:
        tmp.write(code)
    try:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": sandbox_dir,
            "TMPDIR": sandbox_dir,
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "PYTHONPATH": "",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
        res = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=sandbox_dir,
            env=env,
        )
        if res.stdout:
            print(f"📊 OUTPUT: {res.stdout.strip()}")
        if res.stderr:
            print(f"⚠️ ERROR: {res.stderr.strip()}")
        return res.stdout if not res.stderr else f"Error: {res.stderr}"
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        try:
            os.rmdir(sandbox_dir)
        except OSError:
            pass


# --- CONFIGURATION (Defined once to stay DRY/Clean) ---
ATTACKER_CONFIG = types.GenerateContentConfig(
    tools=[execute_python_code],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(),
)
ATTACKER_NO_TOOL_CONFIG = types.GenerateContentConfig(temperature=0.2)


def _route_v4_primitives(thesis_text, evidence_text, critiques_text=""):
    v4_routing_enabled = (
        args.use_primitives
        and (
            is_v4_family_project(args.project)
            or args.primitive_routing_profile == "v4"
        )
    )
    if not v4_routing_enabled:
        return None, []
    decision = route_primitives_for_v4(
        thesis_text=thesis_text,
        evidence_text=evidence_text,
        critiques_text=critiques_text,
    )
    primitives = retrieve_primitives_by_keys(decision.primitive_keys)
    return decision, primitives

def run_specialized_attacker(thesis_text, evidence_text, attacker_profile):
    primitive_context = "None."
    if args.use_primitives:
        routed_decision, routed_primitives = _route_v4_primitives(
            thesis_text,
            evidence_text,
            attacker_profile["focus_area"],
        )
        if routed_decision:
            attack_templates = [p for p in routed_primitives if p.get("epistemic_role") == "attack_template"]
            if not attack_templates and routed_decision.requires_manual_review:
                primitive_context = (
                    "V4 ROUTING DECISION:\n"
                    f"- Family: {routed_decision.family_tag.value}\n"
                    f"- Policy: {routed_decision.policy.value}\n"
                    "- No routed attack templates loaded; manual review fallback remains active."
                )
            else:
                primitive_context = (
                    "V4 ROUTING DECISION:\n"
                    f"- Family: {routed_decision.family_tag.value}\n"
                    f"- Policy: {routed_decision.policy.value}\n"
                    f"- Primitive keys: {', '.join(routed_decision.primitive_keys) or 'none'}\n\n"
                    + format_attack_templates(attack_templates)
                )
        else:
            primitive_context = format_attack_templates(
                retrieve_primitives(
                    "\n".join([thesis_text, evidence_text, attacker_profile["focus_area"]]),
                    top_k=args.primitive_top_k,
                    epistemic_role="attack_template",
                )
            )
    prompt = f"""
    {attacker_profile["persona"]}
    YOUR FOCUS AREA: {attacker_profile["focus_area"]}

    TASK: Critique this thesis AND the accompanying Python Falsification Suite.
    CRITICAL MANDATE: Look for 'Cooked Books' in the Python code. Did the Mutator hardcode favorable constants? Did it ignore unit dimensionality? Did it wrongly assume anything? 
    Write a COUNTER-TEST that exposes the insolvency of their equation.
    
    CRITICAL INSTRUCTION (PARAMETRIC GROUNDING):
    You MUST use your deep parametric knowledge of physics, mathematics, and finance to audit the Mutator's "DECISIVE VARIABLES" table and Python constants.
    If they claim a specific physical constant, temperature, limit, or financial metric, verify it against established scientific or market consensus.
    If their baseline variables are fictional, misapplied, or off by orders of magnitude, destroy the thesis and cite the actual real-world metric.

    GP-157 v5.0 Gap #6 — AUDIT MUST-FAIL CONSTRAINT (panel Failure Mode 4):
    Recursive audit hallucinates volume of critiques over validity. Reject any
    architectural / structural critique that is NOT accompanied by EITHER
    (a) a specific compilable attack vector (a Python snippet that fails
    against the Mutator's actual emitted code), OR (b) a direct file:line
    citation of the codebase where the bug exists. Theoretical-elegance
    critiques ('a cleaner abstraction would solve this'), parsimony theater,
    and proposals to add MORE layers / MORE gates / MORE schemas without a
    concrete reachability failure are FORBIDDEN — penalize them heavily.
    The Auditor's job is to find concrete defects, not to redesign the cage.
    
    OUTPUT FORMAT (CRITICAL):
    1. First, provide your analytical critique.
    2. Then, you MUST provide exactly ONE Python code block wrapped in ```python and ``` containing your counter-test. 
    3. The Python code must print its results and use 'assert' statements to fail if the Mutator's logic is insolvent.

    PINT LIBRARY GUARDRAIL:
    If you use the `pint` library, comparing custom dimensionless units (like 'bit * joule') to standard units (like 'joule') will crash the system. When writing `assert` or `if` statements, you MUST extract the float values using `.magnitude` (e.g., `if E_cost.magnitude > E_univ.magnitude:`) or explicitly convert units to be identical before comparison.

    SELF-CONTAINMENT GUARDRAIL (MANDATORY — do not violate):
    Your counter-test runs in an isolated sandbox directory with a stripped environment. The following files do NOT exist in the sandbox and CANNOT be opened:
    - `prediction.json`, `commit.txt`, `manifest.json`, `workspace/*`, `output/*`
    - any file referenced by the thesis as an artifact the primitive would produce AFTER being run (these files exist only in the operator's real run, not in your sandbox).
    - any path outside your current working directory.
    If your counter-test tries to open such a file, it will raise `FileNotFoundError` and the counter-test will be INVALIDATED (not credited as thesis survivorship; not credited as falsification). You will have written a non-test.
    THEREFORE: your counter-test MUST be entirely self-contained. All numeric constants, test inputs, and expected values must be HARDCODED into the Python block. Re-implement any required primitive inline if you need to probe it. Do NOT `open()`, `read_text()`, or `pathlib.Path().exists()` any external file. Do NOT `subprocess.run` or shell out.
    If the thesis's correctness hinges on an artifact you cannot produce, your counter-test should SYMBOLICALLY simulate the artifact (with hardcoded representative values) and probe the thesis's logic against those values, not assert the artifact's presence.

    CONSISTENCY CHECK (MANDATORY):
    Before writing the Python block, walk through your own counter-test mentally and verify:
    (a) Every variable it uses is defined IN the block;
    (b) Every file it might open is either created by the block itself FIRST or is not referenced at all;
    (c) Every import is of a stdlib or numpy/scipy module (no pandas, no requests, no third-party that may be absent);
    (d) The block terminates in under 10 seconds;
    (e) All asserts have informative error messages.
    If any of (a)-(e) fails on inspection, rewrite the block before submitting.
    
    TONE GUARDRAIL (MANDATORY):
    Your output MUST be entirely sterile, clinical, and strictly academic/financial. 
    You are forbidden from using dramatic, aggressive, or sensational metaphors. Do not use terms related to physical destruction, biological harm, or catastrophic violence. Instead, use precise systemic/symbolic terms.
    
    STRUCTURAL FAILURE PATTERNS (check the thesis against each):
    1. Cooked Constants: Are any numerical constants hardcoded to match evidence rather than derived from first principles? Test: perturb each constant by 10% — does the thesis narrative still hold?
    2. Smuggled Parameters: Does the model use non-fitted constants (grid scales, modular bases, rounding thresholds) that are not counted in the parameter budget? A model with 4 "free" parameters and 3 hidden constants is really a 7-parameter model.
    3. Overfitting Disguised as Structure: Does the expression have enough free parameters to interpolate the visible evidence regardless of the generating rule? Test: could a generic polynomial of the same parameter count achieve similar residuals?
    4. Dimensional Incoherence: Do the units of the claimed physical/mathematical constants match their usage in the expression? Are conversion factors silently absorbed into fitted parameters?
    5. Domain Extrapolation Failure: Does the proposed model make physically/mathematically absurd predictions outside the evidence range? Test the model at 2x, 5x, and 10x the evidence domain boundaries.
    6. Suite Omission: Does the test suite avoid testing the most fragile claim? Look for what the tests do NOT check — the gap is often where the thesis breaks.
    7. Structural Mimicry: Does the expression structurally resemble the evidence pattern without capturing the generating mechanism? A sum of sines can approximate any periodic signal but reveals nothing about the true generator.

    FINAL MANDATE:
    You must synthesize the "So What" for the Meta-Judge before writing your Python block.

    KNOWN ADVERSARIAL PRECEDENTS:
    {primitive_context}
    
    EVIDENCE: {evidence_text}
    THESIS: {thesis_text}
    PYTHON TEST CODE WRITTEN BY MUTATOR:
    ```python
    {test_code_content}
    ```
    """

    # Only pass Gemini config if judge is Gemini; other providers receive
    # schema/format instructions through the shared runtime prompt contract.
    config = (
        types.GenerateContentConfig(temperature=0.2)
        if JUDGE_PROVIDER_FAMILY == "google"
        else None
    )

    print(f"\n🚀 ATTACKER LAUNCHED: {attacker_profile['role']}")
    print(f"🎯 FOCUS: {attacker_profile['focus_area']}")

    # GP-134 wrap-and-retry (2026-04-23): RUNTIME.call_text returns an
    # envelope with model-agnostic .text/.raw; on empty-text replies
    # (transient judge-side), retry up to MAX_EMPTY_RETRIES with small
    # backoff before giving up. The earlier code aborted on first empty
    # response, producing empty debate logs (e.g., 1776971609.md 0 bytes).
    MAX_EMPTY_RETRIES = 3
    response = None
    raw_text: str | None = None
    for _empty_attempt in range(MAX_EMPTY_RETRIES):
        response = safe_generate(prompt, config=config, model_id=JUDGE_MODEL_ID)

        # --- 🔍 SAFETY METADATA DEBUGGER (Gemini-shape only) ---
        # Guard against non-Gemini response shapes: only print safety-ratings
        # debug when the response actually has Gemini .candidates or
        # .prompt_feedback attributes. Non-Gemini judges (claude, gpt, o1, o3)
        # return different response envelopes and this debug was producing
        # spurious "RESPONSE OBJECT IS EMPTY OR MALFORMED" on every non-Gemini
        # iter even when the content was fine.
        is_gemini_shape = hasattr(response, 'candidates') or hasattr(response, 'prompt_feedback')
        if is_gemini_shape and hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            reason = str(candidate.finish_reason)
            if "STOP" not in reason:
                print(f"\n🛑 [DEBUG] API HALT DETECTED. Finish Reason: {reason}")
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    print("🚨 Safety Ratings Breakdown:")
                    for rating in candidate.safety_ratings:
                        if "MEDIUM" in str(rating.probability) or "HIGH" in str(rating.probability):
                            print(f"   -> {rating.category}: {rating.probability}")
        elif is_gemini_shape and hasattr(response, 'prompt_feedback'):
            print(f"\n🛑 [DEBUG] PROMPT BLOCKED AT INTAKE: {response.prompt_feedback}")

        # --- 🛡️ BULLETPROOF TEXT EXTRACTION ---
        try:
            raw_text = response.text if response else None
        except ValueError:
            raw_text = None
        except Exception as e:
            print(f"⚠️ Unexpected extraction error: {e}")
            raw_text = None

        if raw_text:
            break
        if _empty_attempt < MAX_EMPTY_RETRIES - 1:
            print(
                f"⚠️  Empty response from judge (attempt {_empty_attempt + 1}/"
                f"{MAX_EMPTY_RETRIES}); retrying in {2 * (_empty_attempt + 1)}s..."
            )
            time.sleep(2 * (_empty_attempt + 1))

    if not raw_text:
        reason = "UNKNOWN"
        if response and hasattr(response, 'candidates') and response.candidates:
            reason = str(response.candidates[0].finish_reason)

        if "SAFETY" in reason:
            return "⚠️ ATTACK BLOCKED BY SAFETY FILTERS: The model's critique triggered corporate safety guardrails."
        else:
            return (
                f"⚠️ ATTACK ABORTED after {MAX_EMPTY_RETRIES} empty-response retries. "
                f"Finish Reason: {reason}. Treat this as a structural failure."
            )

    # --- THE NUCLEAR EXTRACTION (REGEX) ---
    tool_output_text = ""
    # Find the python code block in the markdown
    code_match = re.search(r"```python\n(.*?)\n```", raw_text, re.DOTALL)
    
    if code_match:
        extracted_code = code_match.group(1)
        # Execute the code manually using your existing tool function
        execution_result = execute_python_code(extracted_code)
        # GP-135 (2026-04-23): when the attacker's own code fails with
        # NameError / SyntaxError / ModuleNotFoundError / AttributeError /
        # ImportError, it is the ATTACKER'S code that is broken, not the
        # thesis. Without annotation the judge cannot distinguish "thesis
        # survived a real attack" from "attacker wrote broken code, no
        # test was performed." Measured 19% attacker-code-failure rate on
        # ztare_on_ztare — significant noise source. Prepend an explicit
        # marker so the judge reads attack-invalidation, not thesis-signal.
        # GP-135 extended (2026-04-23 session 2): also catch filesystem /
        # scaffolding errors. FileNotFoundError: attacker tried to open a
        # file that does not exist in the sandbox (common pattern: loading
        # a JSONL fit context that only exists in the main repo).
        # PermissionError / OSError: same class of scaffolding breakage.
        # TimeoutError / TabError: rare but same category.
        # Deliberately NOT including TypeError, ValueError, KeyError,
        # IndexError, ZeroDivisionError — those can be LEGITIMATE
        # falsification signals when the attacker probes the thesis with
        # edge-case inputs and the thesis genuinely breaks.
        _attacker_broken_patterns = (
            "NameError:", "SyntaxError:", "ModuleNotFoundError:",
            "AttributeError:", "ImportError:", "IndentationError:",
            "FileNotFoundError:", "PermissionError:", "OSError:",
            "IOError:", "NotADirectoryError:", "IsADirectoryError:",
            "TimeoutError:", "TabError:",
        )
        if any(pat in execution_result for pat in _attacker_broken_patterns):
            attacker_invalidation = (
                "⚠️ ATTACKER CODE INVALID — the counter-test itself raised a "
                "Python error (NameError, SyntaxError, ImportError, etc.). "
                "This is NOT evidence that the thesis survived; no test was "
                "actually performed. Meta-Judge MUST discount this attack "
                "entirely and MUST NOT cite it as thesis survivorship."
            )
            tool_output_text = (
                f"\n\n### PYTHON EXECUTION OUTPUT:\n{attacker_invalidation}\n\n"
                f"Raw execution output:\n{execution_result}"
            )
            print(f"🧪 Attacker code invalid ({_attacker_broken_patterns[0] if 'NameError' in execution_result else 'other exception'}); critique annotated for Meta-Judge.")
        else:
            # Append the output directly to the critique so the Meta-Judge can read it
            tool_output_text = f"\n\n### PYTHON EXECUTION OUTPUT:\n{execution_result}"
    else:
        tool_output_text = "\n\n### PYTHON EXECUTION OUTPUT:\n⚠️ No Python block found. Attacker failed to provide a quantitative counter-test."

    # Combine the textual critique with the stdout/stderr from the Python execution
    final_critique = raw_text + tool_output_text

    #print("\n--- ADVERSARIAL LOGIC ---")
    #print(final_critique)
    print("--- END ATTACK ---\n")

    print(f"💥 CRITIQUE MAGNITUDE: {len(final_critique)} chars.")
    return final_critique

def run_meta_judge(text, evidence, main_rubric_data, aggregated_critiques, axioms):
    v4_stage_index = _load_v4_stage_index()
    rubric_str = "\n".join(
        [f"- {k}: {v}" for k, v in main_rubric_data["criteria"].items()]
    )
    axiom_str = "\n".join([f"- {a}" for a in axioms]) if axioms else "None yet."
    crux_analysis = None
    primitive_context = "None."
    routing_decision = None
    if args.crux_first_primitives and args.use_primitives:
        crux_analysis = identify_crux_analysis(
            text, evidence, main_rubric_data, aggregated_critiques
        )
    if args.use_primitives:
        routing_decision, routed_primitives = _route_v4_primitives(
            text,
            evidence,
            aggregated_critiques,
        )
        if routing_decision:
            primitive_context = (
                "V4 ROUTING DECISION:\n"
                f"- Family: {routing_decision.family_tag.value}\n"
                f"- Policy: {routing_decision.policy.value}\n"
                f"- Primitive keys: {', '.join(routing_decision.primitive_keys) or 'none'}\n"
                f"- Manual review required: {routing_decision.requires_manual_review}\n"
                f"- Rationale: {routing_decision.rationale}\n\n"
                + format_judge_guardrail(
                    routed_primitives,
                    require_transfer_proof=args.use_mutator_primitives,
                )
            )
        else:
            primitive_query_parts = [text, evidence, aggregated_critiques]
            if crux_analysis:
                primitive_query_parts.extend(
                    [
                        crux_analysis.get("eigenquestion", ""),
                        _crux_claim_from_analysis(crux_analysis),
                        _why_crux_from_analysis(crux_analysis),
                        crux_analysis.get("mismatch_reason", ""),
                        "\n".join(crux_analysis.get("crux_keywords", [])),
                    ]
                )
            primitive_context = format_judge_guardrail(
                retrieve_primitives(
                    "\n".join(part for part in primitive_query_parts if part),
                    top_k=args.primitive_top_k,
                ),
                require_transfer_proof=args.use_mutator_primitives,
            )
    crux_context = "None."
    crux_instruction = ""
    if crux_analysis:
        crux_context = json.dumps(crux_analysis, indent=2)
        crux_instruction = """
    RULES FOR CRUX-FIRST ORDERING:
    - The crux analysis above was produced before any failure precedents were shown.
    - Treat that crux claim as the anchor for this evaluation unless the verification-panel evidence directly refutes it.
    - Decide first whether the falsification suite actually tests that crux.
    - Use failure precedents only to pressure-test the crux; do not let them redefine the crux or soften a claim-test mismatch.
    - If `test_targets_claim` is false or `mismatch_risk` is high, scrutinize selective rigor, halo validation, suite omission, and tautological verification before granting credit for passing tests.
"""
    confirmed_constraint_context = render_confirmed_constraints_prompt_section(
        Path(DERIVED_CONSTRAINTS_PATH)
    )
    prompt = f"""
    {main_rubric_data["persona"]}
    MANDATE: You are the Meta-Judge (Bar-Raiser). Synthesize the attacks and score the thesis.
    
    CRITICAL MANDATE (THE AXIOMATIC GATE):
    Below are the IMMUTABLE AXIOMS already proven in previous iterations. 
    If the current thesis contradicts any of these axioms, you must apply a -50 point penalty.
    --- IMMUTABLE AXIOMS ---
    {axiom_str}

    --- PRECEDENT-FREE CRUX IDENTIFICATION ---
    {crux_context}
    {crux_instruction}

    --- KNOWN FAILURE PRECEDENTS ---
    {primitive_context}

    --- PROJECT CHARTER ---
    {project_charter_content or "No project charter provided for this project."}

    --- CONFIRMED DERIVED CONSTRAINTS ---
    {confirmed_constraint_context or "No confirmed derived constraints recorded yet."}

    PROJECT DRIFT CHECK (MANDATORY):
    If a project charter is present, evaluate whether the thesis still answers the charter's Core Question and stays inside its intended scope.
    A thesis has drifted if it materially narrows into a subproblem that the charter marks as insufficient, collapses distinct end states that the charter requires to be separated, makes claims the charter marks out of scope, or otherwise stops answering the broader project object.
    Do NOT mark drift merely because the thesis became sharper, more bounded, or more testable. Mark drift only when the sharpened thesis ceases to answer the chartered project.
    IMPORTANT: your `drift_detected` verdict is advisory only. Mathematical drift is computed independently from the charter's `Anchor Proxies` section and is the primary enforcement signal.

    FORECAST TYPE CHECK (MANDATORY):
    The charter may declare a `Forecast Type`.
    - If it is `directional_forecast`, bounded tilt language is allowed, but unsupported point-probability claims should be treated as out of scope / overclaim.
    - If it is `probabilistic_forecast`, a point probability is allowed only if the thesis clearly defines the forecast target, horizon, and the model basis for the number.
    - If it is `none` or absent, do not require a forecast layer and do not reward an irrelevant one.
    
    CRITICAL MANDATE (THE POPPERIAN CONSTRAINT):
    Before grading the logic against the rubric, you must evaluate Falsifiability. Does this thesis make a specific, testable prediction that could theoretically be proven wrong by a future data point or simulation?
    If the thesis only offers post-hoc rationalizations or relies on unmeasurable variables, the maximum allowable score is 40.
    If the Mutator proposes retiring an axiom, evaluate if it is a valid dimensional shift or just lazy accounting. If valid, add it to retired_axioms_approved. If it is a fraudulent attempt to evade a constraint, penalize the score by -30

    PROBABILITY DAG MANDATE (SUPERFORECASTING OUTPUT):
    After scoring, you must extract the 3-5 most critical variables from the thesis and express them as a probability DAG.

    CRITICAL PROBABILITY SEMANTICS (read carefully before assigning numbers):
    - Each node probability represents: P(this node is TRUE | the thesis direction is correct).
      Think of it as: "If this thesis is roughly right, how confident are we this specific mechanism holds?"
      A node that survived the verification panel intact should be 0.60-0.85. One with major holes: 0.20-0.45.
      Do NOT assign node probabilities as marginal base rates of global catastrophes (e.g. 0.05%).
    - The outcome_probability is a WEIGHTED SUM (not a product) of upstream node probabilities:
      outcome = sum(node_i.probability * edge_i.weight) / sum(edge_i.weight)
      This is a causal confidence score, not a joint probability of independent events.
    - Edge weights (0.0-1.0) represent causal contribution: how much does this node drive the outcome?
      The highest-leverage critical variable gets weight ~0.8-1.0. Supporting nodes: 0.3-0.6.

    CALIBRATION CHECK: If your outcome_probability is below 0.05, you have made a math error.
    The DAG measures thesis confidence, not actuarial risk of the worst-case scenario.
    This DAG is appended to the thesis output — it does NOT replace the hardened essay.
    
    --- CORE RUBRIC ---
    {rubric_str}

    --- APPARATUS CONTRACT (MANDATORY — READ BEFORE PENALIZING STRUCTURE) ---
    The mutator's `test_model.py` must satisfy MULTIPLE machine-checked contracts that
    your prose review may not have visibility into. Do NOT penalize the thesis for
    complying with these contracts; the apparatus rejects non-compliance at R1 BEFORE
    you see the submission.

      1. NO MODULE-LEVEL `I_model(...)` CALLS (R1 contract; GP-156 Bug #11/#14).
         At module load time `MODEL_PARAMS = {{}}` (empty), so any module-level
         `I_model(features, params)` call raises KeyError and crashes import.
         The mutator must REMOVE such calls entirely. The apparatus does NOT
         invoke any private helper like `_post_fit_sanity()` — putting calls
         there leaves them unrun AND I_model unverified.
         → Do NOT accept "deferring validation/sanity checks into a private
           helper" as compliance — it's an evasion that produces NaN-returning
           I_model. Mark such submissions as a defect of the same severity as
           module-level calls.
         → DO accept "removed module-level I_model(...) calls; placed any
           debug-only checks inside `if __name__ == \"__main__\":`" as proper
           compliance, since that block is not executed by the apparatus.

      2. PARAMETRIC FORM CONTRACT (GP-156 Proposal 3).
         If the mutator declares `PARAMETRIC_FORM` (str) + `PARAMETER_NAMES` (list) +
         `MODEL_PARAMS = {{}}` at module level, the apparatus runs scipy.optimize multi-
         start to fit the constants. The thesis SHOULD declare the form symbolically;
         numerical constants in the form are FILLED BY THE APPARATUS, not by the LLM.
         → Do NOT mark "constants not numerically specified" as a defect when
           PARAMETRIC_FORM is declared — the constants are intentionally apparatus-fitted.

      3. NUMERIC ASSERTIONS THAT DO NOT CALL `I_model` ARE STILL FALSIFIERS (G-FALSIFY).
         The mutator can satisfy G-FALSIFY's "≥1 numeric-threshold assertion" requirement
         with assertions on functional invariants that DO NOT depend on params, e.g.
         `assert PARAMETER_NAMES == sorted(set(PARAMETER_NAMES))`,
         `assert all(k in feature_keys() for k in [...])`, or math-identity asserts.
         → Reward such asserts as legitimate falsifiers; do not demand assertions
           that would necessarily call `I_model` at module level.

      4. GRADUATED NEAR-MISS BAND (GP-156 Bug #18).
         If the harness output contains the tag `[near_miss — REFINE this form, do not
         redesign]` in a gate-failure message, the proposed form is structurally close
         (within 1.5× threshold) to passing. In that case:
         → Score floor is 30 (do NOT zero the thesis).
         → Direct the mutator to REFINE the existing parametric form (tighten constants,
           adjust regime breakpoints) rather than redesign from scratch.
         → A redesign in response to near-miss is a Munger man-with-a-hammer failure
           that throws away signal calibration. Penalize redesign-on-near-miss in
           your `weakest_point` field with explicit guidance to refine.

      5. SILENT-CRASH CLASS (GP-156 Bug #16).
         If the harness output reports `crash_rate > 0.5` or `exception classes` for
         per-row I_model failures, the model NEVER PRODUCED PREDICTIONS — there is no
         falsification to grade. The MRE you see is artifact, not signal. Treat this
         as a HARNESS DEFECT class failure (apparatus-side) and direct the mutator to
         fix the contract (declare PARAMETRIC_FORM, populate MODEL_PARAMS, or remove
         params dependence). Do not score the thesis on prediction quality when the
         predictions never ran.

      6. PATHOLOGICAL-FIT CLASS (GP-156 Bug #26 — sparse-category overfitting).
         If `workspace/fit_features_result.json` reports `pathological: true`, the
         fit converged on EXTREME parameter values that are demonstrably out of the
         physical range of the y observable. Example: gp154 iter 1 fit
         delta_audio=128 on a substrate where y ∈ [-0.21, 4.0]. scipy moved slack
         into a sparse-category param to absorb visible noise; holdout will fail
         catastrophically (MRE often >> 1.0).
         → Do NOT mark the thesis structurally wrong if pathology is the only fault.
         → Direct the mutator to: (a) drop the offending sparse-category parameter
           and use a SHARED parameter across modalities, OR (b) check
           `feature_value_counts` in the JSON and remove params tied to categories
           with <3 visible rows. Underdetermined params will overfit every time.
         → A pathological-fit thesis with otherwise-sound structure should score
           in the 20-40 range with explicit refine guidance, not 0.

    --- VERIFICATION PANEL CRITIQUES ---
    {aggregated_critiques}
    --- EVIDENCE ---
    {evidence}
    --- THESIS ---
    {text}
    """
    if is_v4_family_project(args.project) and v4_stage_index == 3:
        prompt += """

STAGE 4 SCOPE ENFORCEMENT (MANDATORY):
Your score-bearing evaluation must focus only on Shadow Board behavior:
- board composition determinism
- role assignment correctness
- arbiter activation semantics
- typed-handoff recording / consumption behavior

For this stage, a thesis is allowed to consume `typed_handoff_available` as an upstream flag and make a bounded claim about deterministic board composition plus conservative fallback.
Do NOT score the thesis down merely because upstream provenance is unresolved, unless the thesis claims to verify that provenance itself, claims systemic trust repair, or claims stable whole-system adversarial coverage.

If you identify upstream semantic-gate, whitelist, quote-validation, or other stage-1/2/3 weaknesses:
- record them in `logic_gaps` or `debate_summary` as OUT-OF-SCOPE ARCHITECTURAL DEBT
- do NOT treat them as score-bearing failures for this stage
- do NOT use them as the main `weakest_point` unless they directly alter board behavior itself
"""
    criteria_keys = list(main_rubric_data["criteria"].keys())
    if args.deterministic_score_gates:
        criteria_key_str = "\n".join([f"- {key}" for key in criteria_keys])
        prompt += f"""

DETERMINISTIC SCORE CONTRACT (MANDATORY):
Do NOT optimize for rhetorical scoring. Your job is to produce machine-readable gate decisions and criterion booleans.

You must decide the following booleans:
- `is_falsified`: true if the thesis is directly falsified by the unit tests, its own quantitative evidence, or its own architecture claims.
- `computationally_feasible`: true only if the proposed architecture is executable and internally coherent as specified.
- `anti_gaming_preserved`: true only if the mutator still cannot influence its own evaluation.
- `architectural_abstraction_preserved`: true only if the proof remains an architectural mechanism rather than a domain-rich simulation.
- `contains_infallible_aggregator`: true if the proposal reintroduces an absolute veto, infallible aggregator, hidden trusted arbiter, or equivalent trust leak.
- `proof_is_self_referential`: true if the test suite merely recomputes thesis-authored formulas, bookkeeping identities, or self-declared metrics instead of creating an independent falsification environment that could invalidate the claimed mechanism.

You must also output a structured `self_reference_evidence` record for Python-side semantic-gate stabilization:
- `target_claim`: string
- `asserted_variable`: string
- `asserted_variable_origin`: one of `internal|external|mixed|unknown`
- `independent_grounding_present`: boolean
- `test_recomputes_thesis_authored_target`: boolean
- `causal_variable_perturbed`: boolean
- `crux_claim_directly_tested`: boolean
- `local_component_scope_disclaimer_present`: boolean
- `whole_system_availability_claim_present`: boolean
- `verifies_authored_mapping_only`: boolean
- `evidence_lines`: array of short strings
- `counterevidence_lines`: array of short strings
- `confidence`: one of `high|medium|low`

You must also output a structured quarantine assessment:
- `quarantined_crux_dependency`: boolean
- `quarantine_target`: one of `background_only|causal_mechanism|named_discriminator|falsification_environment|unknown`
- `quarantine_legitimate`: boolean
- `quarantine_rationale`: string
- `quarantine_gates_causal_mechanism`: boolean
- `quarantine_gates_named_discriminator`: boolean
- `quarantine_gates_falsification_environment`: boolean

Quarantine rule:
- explicit acknowledgment of an unresolved variable does NOT automatically make it non-score-bearing
- if the unresolved variable still gates the central causal mechanism, the named discriminator, or the falsification environment, it remains score-bearing even if the thesis explicitly quarantines it
- use `background_only` only when the unresolved variable genuinely does not gate the scored claim
- if the unresolved variable still determines whether the thesis's named discriminator actually discriminates between the thesis and the rival, set `quarantine_target = named_discriminator`
- if the unresolved variable still determines whether the test suite constitutes an independent falsification environment for the claim being made, set `quarantine_target = falsification_environment`
- if the unresolved variable still gates the central mechanism but not the named discriminator directly, set `quarantine_target = causal_mechanism`
- if you cannot localize the dependency precisely but it is still critical to the claim, set `quarantine_target = unknown`
- set the three `quarantine_gates_*` booleans independently and conservatively
- if `quarantine_gates_named_discriminator` is true, then `quarantine_gates_causal_mechanism` should normally also be true
- if `quarantine_gates_falsification_environment` is true, that is score-bearing even if the named discriminator is otherwise well-phrased
- use `quarantine_target` only as a summary label; the booleans are the authoritative structural record

You must also output a structured present-vs-future confirmation assessment:
- `current_discriminator_directly_confirmed`: boolean
- `current_support_is_directional_only`: boolean
- `decisive_confirmation_deferred_to_forward_observable`: boolean
- `confirmation_rationale`: string

Confirmation rule:
- a thesis cannot earn a perfect score merely because it is well-scoped and falsifiable if decisive confirmation of its central discriminator is explicitly deferred to a future observable
- if the current support is only directional, proxy-based, or historical-calibration-based rather than a direct current test of the named discriminator, set `current_support_is_directional_only = true`
- if the thesis says the decisive econometric, observational, or policy-separation confirmation will only arrive in a future episode / forward observable, set `decisive_confirmation_deferred_to_forward_observable = true`
- set `current_discriminator_directly_confirmed = true` only when the current evidence directly tests and confirms the named discriminator in the present, rather than merely aligning with it directionally
- if decisive confirmation is deferred but there is still substantial directional support now, that is a strong bounded thesis but not a perfect one
- if decisive confirmation is deferred and there is no meaningful direct present confirmation, prefer the more conservative classification

You must also output a forecast overclaim assessment:
- `unsupported_point_probability_claim`: boolean
- `forecast_overclaim_rationale`: string

Forecast overclaim rule:
- if the charter declares `directional_forecast`, set `unsupported_point_probability_claim = true` when the thesis states or implies a point probability, percentage, odds, or similarly precise numeric forecast claim for the future outcome
- a probability DAG does NOT by itself authorize a `%` forecast claim in a directional project
- if the charter declares `probabilistic_forecast`, a point probability is allowed only when the target event, horizon, and model basis are explicit
- if the project is not a forecast project or no point-probability overclaim is present, set `unsupported_point_probability_claim = false`
- use `forecast_overclaim_rationale` to explain the issue briefly

You must also output a project-drift assessment:
- `drift_detected`: boolean
- `drift_rationale`: string

Drift rule:
- if no project charter is present, set `drift_detected = false` and `drift_rationale = ""`
- if a charter is present, set `drift_detected = true` only when the thesis materially stops answering the chartered project
- examples of drift include: replacing a broad pillar-ranking project with a single narrow mechanism as if it answers the whole question; converting a mechanism project into a forecast project without explicit event boundaries; collapsing distinct chartered end states into one rhetorical outcome; or making claims the charter explicitly marks out of scope
- examples of non-drift include: sharpening a discriminator, narrowing an unwieldy thesis into a bounded version that still answers the charter, or deferring subordinate questions while preserving the primary project object
- use `drift_rationale` to explain the mismatch succinctly in plain language
- this `drift_detected` field is secondary and advisory; Python will compute a separate deterministic drift check from `Anchor Proxies`

You must also output a structured evidence-gap assessment:
- `evidence_gaps`: array of objects with:
  - `gap_type`: one of `missing_external_comparator|missing_threshold_grounding|missing_independent_taxonomy|missing_external_validation|missing_rival_mechanism|missing_scope_boundary_evidence|other`
  - `target`: short string naming the missing evidence object
  - `description`: short string describing what evidence is missing
  - `severity`: one of `blocking|degrading|enriching`
  - `producer`: one of `meta_judge|verification_gate|adjudicator`
  - `producer_rationale`: short string for why this is an evidence gap rather than a pure logic flaw
  - `fetch_query`: adversarial search string aimed at finding evidence that could test or break the relevant claim
  - `adversarial_direction`: boolean
  - `recovery_kind`: one of `public_evidence|local_verification`
  - `recovery_channel`: `out_of_loop_evidence_recovery` for public evidence, `in_loop_focus_receipt` for local verification
  - `required_surface`: short string naming the needed surface, such as `public_source`, `public_or_local_source`, or `local_verifier_or_fixture`
  - `can_public_fetch`: boolean
  - `in_loop_consumable`: boolean

Evidence-gap rule:
- include missing evidence that could plausibly be reduced by either new public sources/datasets/comparators/threshold material OR a local verifier, fixture, code/log check, preflight, receipt, or discriminator needed by the autoresearch loop
- do NOT put pure logic defects, evaluator design flaws, or project-drift complaints into `evidence_gaps` unless the missing evidence is the actual blocker
- if the current weakest point is "the boundary is thesis-authored because there is no external comparator / taxonomy / threshold grounding", that belongs in `evidence_gaps`
- `producer` records which layer surfaced the gap; it does not change the artifact schema
- regardless of producer, `fetch_query` must be adversarially phrased toward testing the claim, not confirmatory phrasing like "evidence supporting X"
- set `recovery_kind=public_evidence`, `recovery_channel=out_of_loop_evidence_recovery`, `can_public_fetch=true`, and `in_loop_consumable=false` only when the next step is to collect or cite an external/public source, dataset, benchmark, comparator, or threshold grounding
- set `recovery_kind=local_verification`, `recovery_channel=in_loop_focus_receipt`, `can_public_fetch=false`, and `in_loop_consumable=true` when the next step is to extend a fixture, inspect local logs/code, add a preflight, run a verifier, create a receipt, or sharpen an in-loop discriminator
- if no evidence-solvable gap exists, return an empty array

You must also output a structured derived-constraint proposal lane:
- `derived_constraints`: array of objects with:
  - `constraint`: short structural limit future theses in this project should respect
  - `applies_to`: short string naming the claim family, mechanism, or variable this constrains
  - `failure_family`: short snake_case family tag for the failure pattern that produced the constraint
  - `severity`: one of `blocking|degrading|enriching`
  - `producer`: one of `meta_judge|verification_gate|adjudicator`
  - `rationale`: brief explanation grounded in evaluator-side critique
  - `non_applicability_condition`: short clause naming when this constraint would genuinely not apply

Derived-constraint rule:
- include only reusable structural limits discovered from the critique/evaluation side
- do NOT restate primary evidence facts, project charter text, or one-off tactical advice
- prefer compact rules like "X must be separated from Y" or "A cannot be treated as proof of B"
- if no reusable structural limit was surfaced, return an empty array
- treat previously confirmed constraints as read-only context; do not rewrite them unless the current critique clearly narrows or supersedes them

Backward-compatibility rule:
- still provide `proof_is_self_referential`
- but populate `self_reference_evidence` carefully, because Python will derive the final semantic gate from that structured record

Field intent for local safe-harbor cases:
- `local_component_scope_disclaimer_present` = true only when the thesis explicitly limits itself to a narrow local component and disclaims upstream truthfulness/completeness.
- `whole_system_availability_claim_present` = true when the thesis claims end-to-end protection, system-level guarantees, or explicit future-state outcomes such as insolvency, collapse, success, distress, or other whole-system predictions. Do not limit this field to phrases like "prevents" or "ensures"; forward predictions about the whole system also count.
- `verifies_authored_mapping_only` = true when the tests only verify the component's own authored deterministic mapping, thesis-authored thresholds, or thesis-authored future scenarios rather than a claim about independently grounded external reality. A counter-scenario or inverse scenario does NOT make this false if both scenarios are still thesis-authored.

Grounding rule for prediction claims:
- `independent_grounding_present` = true only if the specific crux variable or threshold that determines whether the central claim passes or fails is independently grounded.
- Do NOT set `independent_grounding_present` true merely because some other input variable is externally sourced, or because the thesis cites background evidence elsewhere.
- For forward prediction claims, if the decisive future variable, threshold, horizon, or causal multiplier is a thesis assumption, then `independent_grounding_present` must be false even if other inputs are externally cited.

Extraction rule for self-reference:
- If the tests recompute a thesis-authored future variable or thesis-authored threshold, treat that as self-referential unless the decisive pass/fail variable is independently grounded.
- If the claim is a whole-system future prediction and the decisive variable remains thesis-authored, prefer `asserted_variable_origin = internal` and `independent_grounding_present = false`.

For rubric criteria, you must output:
- `criteria_passed`: array of rubric keys that pass
- `criteria_failed`: array of rubric keys that fail

Use ONLY these rubric keys:
{criteria_key_str}

EVIDENTIARY SAFE HARBOR (MANDATORY):
Do not mark `anti_gaming_preserved` false or `contains_infallible_aggregator` true merely because a narrowly scoped local component consumes upstream booleans, status tokens, or scores.
If ALL of the following are true, evaluate the local contract on its own terms:
- the thesis explicitly disclaims solving upstream truthfulness, calibration, or completeness
- the code implements only a deterministic bounded mapping or a fail-closed gate
- the tests exhaustively validate that local mapping or gate
- the prose does not claim that local execution proves whole-system validity

For such bounded local components:
- exhaustive input-output checks are acceptable evidence for the local claim
- do NOT mark `proof_is_self_referential` true merely because the tests execute the exact mapping being claimed
- dependency on upstream inputs is allowed; false claims about their truthfulness are not

Hard rule:
- If the thesis is falsified, computationally infeasible, anti-gaming is not preserved, or an infallible aggregator is present, say so explicitly. Python will convert those gates into the final score.
"""
    # For non-Gemini judges, append JSON schema as instructions.
    is_non_gemini = JUDGE_PROVIDER_FAMILY != "google"
    if is_non_gemini:
        if args.deterministic_score_gates:
            prompt += """

CRITICAL: You must respond with ONLY a valid JSON object. No markdown, no explanation.
Required fields:
{
  "is_falsified": <boolean>,
  "computationally_feasible": <boolean>,
  "anti_gaming_preserved": <boolean>,
  "architectural_abstraction_preserved": <boolean>,
  "contains_infallible_aggregator": <boolean>,
  "proof_is_self_referential": <boolean>,
  "self_reference_evidence": {
    "target_claim": <string>,
    "asserted_variable": <string>,
    "asserted_variable_origin": <string>,
    "independent_grounding_present": <boolean>,
    "test_recomputes_thesis_authored_target": <boolean>,
    "causal_variable_perturbed": <boolean>,
    "crux_claim_directly_tested": <boolean>,
    "local_component_scope_disclaimer_present": <boolean>,
    "whole_system_availability_claim_present": <boolean>,
    "verifies_authored_mapping_only": <boolean>,
    "evidence_lines": [<string>, ...],
    "counterevidence_lines": [<string>, ...],
    "confidence": <string>
  },
  "quarantined_crux_dependency": <boolean>,
  "quarantine_target": <string>,
  "quarantine_legitimate": <boolean>,
  "quarantine_rationale": <string>,
  "quarantine_gates_causal_mechanism": <boolean>,
  "quarantine_gates_named_discriminator": <boolean>,
  "quarantine_gates_falsification_environment": <boolean>,
  "current_discriminator_directly_confirmed": <boolean>,
  "current_support_is_directional_only": <boolean>,
  "decisive_confirmation_deferred_to_forward_observable": <boolean>,
  "confirmation_rationale": <string>,
  "unsupported_point_probability_claim": <boolean>,
  "forecast_overclaim_rationale": <string>,
  "drift_detected": <boolean>,
  "drift_rationale": <string>,
  "criteria_passed": [<string>, ...],
  "criteria_failed": [<string>, ...],
  "weakest_point": <string>,
  "verified_axioms": [<string>, ...],
  "retired_axioms_approved": [<string>, ...],
  "evidence_gaps": [
    {
      "gap_type": <string>,
      "target": <string>,
      "description": <string>,
      "severity": <string>,
      "producer": <string>,
      "producer_rationale": <string>,
      "fetch_query": <string>,
      "adversarial_direction": <boolean>,
      "recovery_kind": <string>,
      "recovery_channel": <string>,
      "required_surface": <string>,
      "can_public_fetch": <boolean>,
      "in_loop_consumable": <boolean>
    }
  ],
  "derived_constraints": [
    {
      "constraint": <string>,
      "applies_to": <string>,
      "failure_family": <string>,
      "severity": <string>,
      "producer": <string>,
      "rationale": <string>,
      "non_applicability_condition": <string>
    }
  ],
  "logic_gaps": [<string>, ...],
  "debate_summary": <string>,
  "adversarial_alignment": <string>,
  "friction_points": [<string>, ...],
  "probability_dag": {
    "outcome": {"label": <string>, "probability": <number>},
    "nodes": [{"id": <string>, "label": <string>, "probability": <number>, "watch_signal": <string>}],
    "edges": [{"from": <string>, "to": <string>, "weight": <number>}]
  }
}"""
        else:
            prompt += """

CRITICAL: You must respond with ONLY a valid JSON object. No markdown, no explanation.
Required fields:
{
  "score": <integer>,
  "weakest_point": <string>,
  "verified_axioms": [<string>, ...],
  "retired_axioms_approved": [<string>, ...],
  "evidence_gaps": [
    {
      "gap_type": <string>,
      "target": <string>,
      "description": <string>,
      "severity": <string>,
      "producer": <string>,
      "producer_rationale": <string>,
      "fetch_query": <string>,
      "adversarial_direction": <boolean>,
      "recovery_kind": <string>,
      "recovery_channel": <string>,
      "required_surface": <string>,
      "can_public_fetch": <boolean>,
      "in_loop_consumable": <boolean>
    }
  ],
  "derived_constraints": [
    {
      "constraint": <string>,
      "applies_to": <string>,
      "failure_family": <string>,
      "severity": <string>,
      "producer": <string>,
      "rationale": <string>,
      "non_applicability_condition": <string>
    }
  ],
  "logic_gaps": [<string>, ...],
  "debate_summary": <string>,
  "adversarial_alignment": <string>,
  "friction_points": [<string>, ...],
  "probability_dag": {
    "outcome": {"label": <string>, "probability": <number>},
    "nodes": [{"id": <string>, "label": <string>, "probability": <number>, "watch_signal": <string>}],
    "edges": [{"from": <string>, "to": <string>, "weight": <number>}]
  }
}"""
        evaluation = utils.parse_llm_json_with_retry(
            lambda: safe_generate(prompt, config=None, model_id=JUDGE_MODEL_ID).text,
            call_site="run_meta_judge_unstructured",
        )
        if not args.deterministic_score_gates and (
            raw_shape_errors := _raw_meta_judge_shape_errors(evaluation)
        ):
            print(
                "⚠️ Raw judge returned malformed verdict JSON "
                f"({', '.join(raw_shape_errors)}) — retrying once with explicit schema reminder."
            )
            first_malformed_payload = evaluation
            retry_prompt = (
                prompt
                + "\n\n[SYSTEM RETRY]: Your previous response was valid JSON but was NOT "
                "the required meta-judge verdict schema. Do not return a single evidence-gap "
                "object, score_contract object, or diagnostic object as the top-level JSON. "
                "Return exactly the full verdict object with top-level fields: "
                f"{', '.join(RAW_META_JUDGE_REQUIRED_FIELDS)}. "
                "The `score` field is REQUIRED and must be an integer from 0 to 100. "
                "`weakest_point` and `debate_summary` are REQUIRED strings. "
                "Re-evaluate the thesis and respond only with the verdict JSON."
            )
            retry_eval = utils.parse_llm_json_with_retry(
                lambda: safe_generate(
                    retry_prompt, config=None, model_id=JUDGE_MODEL_ID
                ).text,
                call_site="run_meta_judge_unstructured_schema_retry",
            )
            retry_shape_errors = _raw_meta_judge_shape_errors(retry_eval)
            if retry_shape_errors:
                evaluation = _judge_format_error_evaluation(
                    retry_eval, retry_shape_errors
                )
                evaluation["initial_malformed_judge_payload"] = first_malformed_payload
                print(
                    "🚫 Raw judge schema retry still malformed; recording explicit "
                    "judge_format_error instead of silently treating the payload as a verdict."
                )
            else:
                evaluation = _coerce_raw_meta_judge_score(retry_eval)
                print("✅ Raw judge schema retry returned a valid verdict object.")
        elif not args.deterministic_score_gates:
            evaluation = _coerce_raw_meta_judge_score(evaluation)
        if crux_analysis:
            evaluation["crux_analysis"] = crux_analysis
        if routing_decision:
            evaluation["primitive_routing_decision"] = {
                "family_tag": routing_decision.family_tag.value,
                "policy": routing_decision.policy.value,
                "primitive_keys": list(routing_decision.primitive_keys),
                "punitive_primitives_allowed": routing_decision.punitive_primitives_allowed,
                "requires_manual_review": routing_decision.requires_manual_review,
                "rationale": routing_decision.rationale,
            }
        return evaluation

    if args.deterministic_score_gates:
        schema = {
            "type": "OBJECT",
            "properties": {
                "is_falsified": {"type": "BOOLEAN"},
                "computationally_feasible": {"type": "BOOLEAN"},
                "anti_gaming_preserved": {"type": "BOOLEAN"},
                "architectural_abstraction_preserved": {"type": "BOOLEAN"},
                "contains_infallible_aggregator": {"type": "BOOLEAN"},
                "proof_is_self_referential": {"type": "BOOLEAN"},
                "self_reference_evidence": {
                    "type": "OBJECT",
                    "properties": {
                        "target_claim": {"type": "STRING"},
                        "asserted_variable": {"type": "STRING"},
                        "asserted_variable_origin": {"type": "STRING"},
                        "independent_grounding_present": {"type": "BOOLEAN"},
                        "test_recomputes_thesis_authored_target": {"type": "BOOLEAN"},
                        "causal_variable_perturbed": {"type": "BOOLEAN"},
                        "crux_claim_directly_tested": {"type": "BOOLEAN"},
                        "local_component_scope_disclaimer_present": {"type": "BOOLEAN"},
                        "whole_system_availability_claim_present": {"type": "BOOLEAN"},
                        "verifies_authored_mapping_only": {"type": "BOOLEAN"},
                        "evidence_lines": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "counterevidence_lines": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "confidence": {"type": "STRING"},
                    },
                },
                "quarantined_crux_dependency": {"type": "BOOLEAN"},
                "quarantine_target": {"type": "STRING"},
                "quarantine_legitimate": {"type": "BOOLEAN"},
                "quarantine_rationale": {"type": "STRING"},
                "quarantine_gates_causal_mechanism": {"type": "BOOLEAN"},
                "quarantine_gates_named_discriminator": {"type": "BOOLEAN"},
                "quarantine_gates_falsification_environment": {"type": "BOOLEAN"},
                "current_discriminator_directly_confirmed": {"type": "BOOLEAN"},
                "current_support_is_directional_only": {"type": "BOOLEAN"},
                "decisive_confirmation_deferred_to_forward_observable": {"type": "BOOLEAN"},
                "confirmation_rationale": {"type": "STRING"},
                "unsupported_point_probability_claim": {"type": "BOOLEAN"},
                "forecast_overclaim_rationale": {"type": "STRING"},
                "drift_detected": {"type": "BOOLEAN"},
                "drift_rationale": {"type": "STRING"},
                "criteria_passed": {"type": "ARRAY", "items": {"type": "STRING"}},
                "criteria_failed": {"type": "ARRAY", "items": {"type": "STRING"}},
                "weakest_point": {"type": "STRING"},
                "verified_axioms": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                },
                "retired_axioms_approved": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                },
                "evidence_gaps": _evidence_gap_response_schema(),
                "derived_constraints": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "constraint": {"type": "STRING"},
                            "applies_to": {"type": "STRING"},
                            "failure_family": {"type": "STRING"},
                            "severity": {"type": "STRING"},
                            "producer": {"type": "STRING"},
                            "rationale": {"type": "STRING"},
                            "non_applicability_condition": {"type": "STRING"},
                        },
                        "required": [
                            "constraint",
                            "applies_to",
                            "failure_family",
                            "severity",
                            "producer",
                            "rationale",
                            "non_applicability_condition",
                        ],
                    },
                },
                "logic_gaps": {"type": "ARRAY", "items": {"type": "STRING"}},
                "debate_summary": {"type": "STRING"},
                "adversarial_alignment": {"type": "STRING"},
                "friction_points": {"type": "ARRAY", "items": {"type": "STRING"}},
                "probability_dag": {
                    "type": "OBJECT",
                    "properties": {
                        "outcome": {
                            "type": "OBJECT",
                            "properties": {
                                "label": {"type": "STRING"},
                                "probability": {"type": "NUMBER"}
                            }
                        },
                        "nodes": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "id": {"type": "STRING"},
                                    "label": {"type": "STRING"},
                                    "probability": {"type": "NUMBER"},
                                    "watch_signal": {"type": "STRING"}
                                }
                            }
                        },
                        "edges": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "from": {"type": "STRING"},
                                    "to": {"type": "STRING"},
                                    "weight": {"type": "NUMBER"}
                                }
                            }
                        }
                    }
                },
            },
            "required": [
                "is_falsified",
                "computationally_feasible",
                "anti_gaming_preserved",
                "architectural_abstraction_preserved",
                "contains_infallible_aggregator",
                "proof_is_self_referential",
                "self_reference_evidence",
                "quarantined_crux_dependency",
                "quarantine_target",
                "quarantine_legitimate",
                "quarantine_rationale",
                "quarantine_gates_causal_mechanism",
                "quarantine_gates_named_discriminator",
                "quarantine_gates_falsification_environment",
                "current_discriminator_directly_confirmed",
                "current_support_is_directional_only",
                "decisive_confirmation_deferred_to_forward_observable",
                "confirmation_rationale",
                "unsupported_point_probability_claim",
                "forecast_overclaim_rationale",
                "drift_detected",
                "drift_rationale",
                "criteria_passed",
                "criteria_failed",
                "weakest_point",
                "evidence_gaps",
                "derived_constraints",
                "logic_gaps",
                "verified_axioms",
                "retired_axioms_approved",
                "debate_summary",
            ],
        }
    else:
        schema = {
            "type": "OBJECT",
            "properties": {
                "score": {"type": "INTEGER"},
                "weakest_point": {"type": "STRING"},
                "verified_axioms": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Atomic truths that survived the verification panel.",
                },
                "retired_axioms_approved": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of proposed axiom retirements that the Judge agrees are valid for the new domain.",
                },
                "evidence_gaps": _evidence_gap_response_schema(),
                "derived_constraints": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "constraint": {"type": "STRING"},
                            "applies_to": {"type": "STRING"},
                            "failure_family": {"type": "STRING"},
                            "severity": {"type": "STRING"},
                            "producer": {"type": "STRING"},
                            "rationale": {"type": "STRING"},
                            "non_applicability_condition": {"type": "STRING"},
                        },
                        "required": [
                            "constraint",
                            "applies_to",
                            "failure_family",
                            "severity",
                            "producer",
                            "rationale",
                            "non_applicability_condition",
                        ],
                    },
                },
                "logic_gaps": {"type": "ARRAY", "items": {"type": "STRING"}},
                "debate_summary": {"type": "STRING"},
                "adversarial_alignment": {
                    "type": "STRING"
                },
                "friction_points": {"type": "ARRAY", "items": {"type": "STRING"}},
                "probability_dag": {
                    "type": "OBJECT",
                    "description": "Superforecasting probability model extracted from the thesis.",
                    "properties": {
                        "outcome": {
                            "type": "OBJECT",
                            "properties": {
                                "label": {"type": "STRING"},
                                "probability": {"type": "NUMBER"}
                            }
                        },
                        "nodes": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "id": {"type": "STRING"},
                                    "label": {"type": "STRING"},
                                    "probability": {"type": "NUMBER"},
                                    "watch_signal": {"type": "STRING"}
                                }
                            }
                        },
                        "edges": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "from": {"type": "STRING"},
                                    "to": {"type": "STRING"},
                                    "weight": {"type": "NUMBER"}
                                }
                            }
                        }
                    }
                },
            },
            "required": [
                "score",
                "weakest_point",
                "evidence_gaps",
                "derived_constraints",
                "logic_gaps",
                "verified_axioms",
                "retired_axioms_approved",
                "debate_summary",
            ],
        }
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
    )
    evaluation = utils.parse_llm_json_with_retry(
        lambda: safe_generate(prompt, config=config).text,
        call_site="run_meta_judge",
    )
    # GP-210 fix: gpt-4.1 (and other non-Gemini judges) occasionally returns
    # valid JSON that omits criteria_passed or returns an empty array, causing
    # a spurious score-0 even when the thesis is substantive. This happens when
    # the OpenAI structured-output adapter doesn't enforce the Gemini schema's
    # required fields. Retry once with an explicit reminder injected.
    if args.deterministic_score_gates and not evaluation.get("criteria_passed"):
        print("⚠️ Judge returned empty criteria_passed — retrying once with explicit schema reminder.")
        retry_prompt = (
            prompt
            + "\n\n[SYSTEM RETRY]: Your previous response omitted the `criteria_passed` field "
            "or returned an empty array. You MUST populate `criteria_passed` with every rubric "
            "criterion key that the thesis satisfies. This field is REQUIRED and must be a "
            "non-empty array when the thesis has any merit. Re-evaluate and respond."
        )
        retry_eval = utils.parse_llm_json_with_retry(
            lambda: safe_generate(retry_prompt, config=config).text,
            call_site="run_meta_judge_retry",
        )
        if retry_eval.get("criteria_passed"):
            evaluation = retry_eval
        else:
            evaluation["_judge_format_warning"] = "criteria_passed missing after retry"

    if crux_analysis:
        evaluation["crux_analysis"] = crux_analysis
    if routing_decision:
        evaluation["primitive_routing_decision"] = {
            "family_tag": routing_decision.family_tag.value,
            "policy": routing_decision.policy.value,
            "primitive_keys": list(routing_decision.primitive_keys),
            "punitive_primitives_allowed": routing_decision.punitive_primitives_allowed,
            "requires_manual_review": routing_decision.requires_manual_review,
            "rationale": routing_decision.rationale,
        }
    # GP-167 fix (2026-04-25): clamp judge-emitted score to
    # [0, 100]. The judge LLM has been observed to return 170 on
    # gp163d (gpt-5.5 judge), which propagates to all downstream
    # comparison logic (champion promotion, deltas, near-miss floors)
    # as if it were a legitimate score. Treat any out-of-bounds value
    # as a judge hallucination and clamp.
    try:
        raw_score = evaluation.get("score")
        if raw_score is not None:
            clamped = max(0, min(100, int(raw_score)))
            if clamped != raw_score:
                evaluation["score"] = clamped
                evaluation["score_clamp_applied"] = (
                    f"judge returned {raw_score!r}; clamped to [0, 100]"
                )
    except Exception:
        pass
    return evaluation


_LEGACY_CRUX_CLAIM_KEY = "load_" + "bearing_claim"
_LEGACY_WHY_CRUX_KEY = "why_load_" + "bearing"
_LEGACY_CRUX_TESTED_KEY = "load_" + "bearing_claim_directly_tested"
_LEGACY_QUARANTINED_CRUX_KEY = "quarantined_load_" + "bearing_dependency"


def _first_present(mapping: dict, *keys: str, default=None):
    for key in keys:
        if key in mapping:
            return mapping.get(key)
    return default


def _bool_first_present(mapping: dict, *keys: str, default: bool = False) -> bool:
    return bool(_first_present(mapping, *keys, default=default))


def _crux_claim_from_analysis(crux_analysis: dict | None) -> str:
    if not crux_analysis:
        return ""
    return str(_first_present(crux_analysis, "crux_claim", _LEGACY_CRUX_CLAIM_KEY, default="") or "")


def _why_crux_from_analysis(crux_analysis: dict | None) -> str:
    if not crux_analysis:
        return ""
    return str(_first_present(crux_analysis, "why_crux", _LEGACY_WHY_CRUX_KEY, default="") or "")


def identify_crux_analysis(text, evidence, main_rubric_data, aggregated_critiques):
    prompt = f"""
    {main_rubric_data["persona"]}
    TASK: Identify the single crux claim / eigenquestion of the thesis BEFORE reading any failure precedents.

    Return strict JSON with this schema:
    {{
      "eigenquestion": "<single foundational yes/no or either/or question>",
      "crux_claim": "<single claim whose failure makes much of the thesis irrelevant>",
      "why_crux": "<brief explanation of why this is the crux>",
      "test_targets_claim": true or false,
      "mismatch_risk": "high" | "medium" | "low",
      "mismatch_reason": "<brief explanation of whether the falsification suite targets the crux or only nearby scaffolding>",
      "crux_keywords": ["<short phrase>", "..."]
    }}

    Rules:
    - Pick exactly one crux, not a list.
    - Prefer the claim whose failure would render most downstream reasoning irrelevant.
    - `test_targets_claim = true` only if the provided falsification suite directly tests that crux.
    - If the tests mainly validate nearby arithmetic, scaffolding, peripheral derivations, or self-authored thresholds, set `test_targets_claim = false`.
    - `mismatch_risk = high` when the thesis appears to prove something adjacent to the crux rather than the crux itself.
    - Do not use external precedents or prior primitive labels. Work only from the thesis, evidence, and verification-panel critiques.

    --- THESIS ---
    {text}

    --- VERIFICATION PANEL CRITIQUES ---
    {aggregated_critiques}

    --- EVIDENCE ---
    {evidence}
"""
    is_non_gemini = JUDGE_PROVIDER_FAMILY != "google"
    if is_non_gemini:
        prompt += """

CRITICAL: You must respond with ONLY a valid JSON object. No markdown, no explanation.
Required fields:
{
  "eigenquestion": <string>,
  "crux_claim": <string>,
  "why_crux": <string>,
  "test_targets_claim": <boolean>,
  "mismatch_risk": <string>,
  "mismatch_reason": <string>,
  "crux_keywords": [<string>, ...]
}"""
        return utils.parse_llm_json_with_retry(
            lambda: safe_generate(prompt, config=None, model_id=JUDGE_MODEL_ID).text,
            call_site="identify_crux_analysis_unstructured",
        )

    schema = {
        "type": "OBJECT",
        "properties": {
            "eigenquestion": {"type": "STRING"},
            "crux_claim": {"type": "STRING"},
            "why_crux": {"type": "STRING"},
            "test_targets_claim": {"type": "BOOLEAN"},
            "mismatch_risk": {"type": "STRING"},
            "mismatch_reason": {"type": "STRING"},
            "crux_keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": [
            "eigenquestion",
            "crux_claim",
            "why_crux",
            "test_targets_claim",
            "mismatch_risk",
            "mismatch_reason",
            "crux_keywords",
        ],
    }
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
    )
    return utils.parse_llm_json_with_retry(
        lambda: safe_generate(prompt, config=config, model_id=JUDGE_MODEL_ID).text,
        call_site="identify_crux_analysis",
    )


def _rubric_fingerprint(main_rubric_data):
    canonical = json.dumps(main_rubric_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _evidence_fingerprint(path: str) -> str:
    evidence_path = Path(path)
    if not evidence_path.exists():
        return "missing"
    return hashlib.sha256(evidence_path.read_bytes()).hexdigest()[:16]


def _score_regime_payload(main_rubric_data):
    mode = "deterministic_gates" if args.deterministic_score_gates else "raw_llm_score"
    effective_judge_models = sorted(JUDGE_EFFECTIVE_MODELS_USED) or [JUDGE_MODEL_ID]
    return {
        "mode": mode,
        "version": SCORE_REGIME_VERSION_MAP[mode],
        "rubric_name": args.rubric,
        "rubric_fingerprint": _rubric_fingerprint(main_rubric_data),
        "judge_model": JUDGE_MODEL_ID,
        "requested_judge_model": JUDGE_MODEL_ID,
        "effective_judge_models": effective_judge_models,
        "judge_fallback_used": bool(JUDGE_FALLBACK_EVENTS),
        "dynamic_committee": bool(args.dynamic),
        "primitive_support": bool(args.use_primitives),
        "evidence_path": EVIDENCE_PATH,
        "evidence_fingerprint": _evidence_fingerprint(EVIDENCE_PATH),
        "project_forecast_type": project_charter_forecast_type or "unspecified",
    }


def attach_score_regime_metadata(evaluation, main_rubric_data, test_suite_status):
    regime = _score_regime_payload(main_rubric_data)
    regime_fingerprint = hashlib.sha256(
        json.dumps(regime, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]

    existing = evaluation.get("score_contract")
    if not isinstance(existing, dict):
        existing = {}

    existing.update(
        {
            "mode": regime["mode"],
            "version": regime["version"],
            "regime": regime,
            "regime_fingerprint": regime_fingerprint,
            "judge_model": regime["judge_model"],
            "requested_judge_model": regime["requested_judge_model"],
            "effective_judge_models": regime["effective_judge_models"],
            "judge_fallback_used": regime["judge_fallback_used"],
            "rubric_name": regime["rubric_name"],
            "rubric_fingerprint": regime["rubric_fingerprint"],
            "dynamic_committee": regime["dynamic_committee"],
            "primitive_support": regime["primitive_support"],
            "evidence_path": regime["evidence_path"],
            "evidence_fingerprint": regime["evidence_fingerprint"],
            "project_forecast_type": regime["project_forecast_type"],
            "test_suite_status": existing.get("test_suite_status", test_suite_status),
        }
    )
    evaluation["score_contract"] = existing
    return evaluation


def apply_semantic_gate_stabilization(evaluation):
    raw_flag = bool(evaluation.get("proof_is_self_referential", False))
    analysis = derive_self_reference_gate(
        evaluation.get("self_reference_evidence"),
        raw_flag=raw_flag,
    )
    summary = persist_semantic_gate_analysis(Path(PROJECT_DIR), analysis)

    evaluation["proof_is_self_referential_model_raw"] = raw_flag
    evaluation["proof_is_self_referential"] = analysis.proof_is_self_referential
    evaluation["semantic_gate_status"] = analysis.semantic_gate_status
    evaluation["self_reference_rule_fired"] = analysis.self_reference_rule_fired
    evaluation["self_reference_quorum_used"] = analysis.self_reference_quorum_used
    evaluation["self_reference_evidence"] = {
        **analysis.self_reference_evidence.__dict__,
    }
    evaluation["semantic_gate_unresolved_diagnosis"] = (
        analysis.unresolved_diagnosis.__dict__ if analysis.unresolved_diagnosis else None
    )
    evaluation["semantic_gate_summary"] = summary.__dict__
    return evaluation


def finalize_deterministic_score(evaluation, main_rubric_data, test_suite_status):
    criteria_keys = list(main_rubric_data["criteria"].keys())
    criteria_key_set = set(criteria_keys)
    passed = [key for key in evaluation.get("criteria_passed", []) if key in criteria_key_set]
    passed_set = set(passed)
    failed = [key for key in criteria_keys if key not in passed_set]

    hard_fail_reasons = []
    soft_score_caps = []
    safe_harbor_local_component = (
        evaluation.get("self_reference_rule_fired") == "safe_harbor_downgrade"
        and evaluation.get("semantic_gate_status") == "unresolved"
    )
    # P1 fix (deep audit, 2026-04-26): the holdout-hard-gate dispatch
    # runs BEFORE finalize now (callsite reordered). When holdout_hard_gate_fired
    # is True, the gate already zeroed the score; preserve that as a
    # hard-fail reason so finalize's logic doesn't undo it.
    if evaluation.get("holdout_hard_gate_fired"):
        hard_fail_reasons.append(
            "Holdout hard-gate fired — gate_harness.py reported MRE above "
            "threshold. Score zeroed by the gate; finalize honors this."
        )
    if test_suite_status != "pass":
        # Bug B fix (gp163d postmortem, 2026-04-25): when the gate
        # harness ran and produced a meaningful HOLDOUT signal — pass or
        # fail — the gate IS the falsification. The L3 in-test asserts
        # inside test_model.py's __main__ block are a SECONDARY check; a
        # fail_runtime / fail_other from those should not double-zero
        # the score by stacking on the gate's signal. The judge was
        # writing "harness defect, no Level 3 results" as weakest_point
        # even when latest_eval_results.json had real HOLDOUT MRE
        # numbers, basin-locking the mutator on suite-fixing instead of
        # form-fixing.
        #
        # Detection: `evaluation["holdout_hard_gate_fired"]` is set
        # (True or False) by the holdout dispatch when the gate harness
        # actually ran. Its presence — regardless of value — means the
        # gate produced a numeric verdict.
        gate_harness_ran = "holdout_hard_gate_fired" in evaluation
        if test_suite_status in ("fail_runtime", "fail_other"):
            if gate_harness_ran:
                # Gate harness produced numbers; demote L3 in-test issue
                # to a soft cap so the judge grades against the gate
                # values, not the suite defect.
                soft_score_caps.append(
                    {
                        "reason": (
                            f"Level 3 in-test asserts hit `{test_suite_status}` "
                            f"but gate_harness.py ran successfully and produced "
                            f"numeric HOLDOUT/FARTHER_TAIL signals; gate verdict "
                            f"takes precedence. Mutator should fix the form per "
                            f"the gate values, not the suite."
                        ),
                        "cap": 60,
                    }
                )
            else:
                hard_fail_reasons.append(
                    f"Level 3 harness defect ({test_suite_status}) — the suite did not run to completion. "
                    "Per the Phase 1 post-mortem, a harness that raised a runtime exception is a "
                    "categorization failure, not a falsification attempt."
                )
        elif test_suite_status == "fail_assert":
            hard_fail_reasons.append(
                "Level 3 falsification suite disproved the thesis by assertion (`fail_assert`)."
            )
        else:
            hard_fail_reasons.append(f"Level 3 falsification suite status was `{test_suite_status}`.")
    if evaluation.get("is_falsified", False):
        hard_fail_reasons.append("Meta-Judge marked the thesis as falsified.")
    if not evaluation.get("anti_gaming_preserved", True) and not safe_harbor_local_component:
        hard_fail_reasons.append("Meta-Judge found anti-gaming preservation was violated.")
    if evaluation.get("contains_infallible_aggregator", False) and not safe_harbor_local_component:
        hard_fail_reasons.append("Meta-Judge found an infallible aggregator / veto trust leak.")
    if not evaluation.get("computationally_feasible", True):
        soft_score_caps.append(
            {
                "reason": "Meta-Judge marked the thesis as computationally infeasible.",
                "cap": 40,
            }
        )
    if (
        evaluation.get("proof_is_self_referential", False)
        and evaluation.get("self_reference_rule_fired") == "hard_self_reference"
    ):
        hard_fail_reasons.append(
            "Structured semantic-gate derivation classified the proof as hard self-reference."
        )
    elif evaluation.get("proof_is_self_referential", False):
        soft_score_caps.append(
            {
                "reason": "Meta-Judge marked the proof as self-referential rather than a substantive falsification environment.",
                "cap": 25,
            }
        )

    quarantined_crux_dependency = _bool_first_present(
        evaluation,
        "quarantined_crux_dependency",
        _LEGACY_QUARANTINED_CRUX_KEY,
    )
    quarantine_target = str(evaluation.get("quarantine_target", "unknown") or "unknown")
    quarantine_legitimate = bool(evaluation.get("quarantine_legitimate", False))
    quarantine_rationale = str(evaluation.get("quarantine_rationale", "") or "").strip()
    quarantine_gates_causal_mechanism = bool(
        evaluation.get("quarantine_gates_causal_mechanism", False)
    )
    quarantine_gates_named_discriminator = bool(
        evaluation.get("quarantine_gates_named_discriminator", False)
    )
    quarantine_gates_falsification_environment = bool(
        evaluation.get("quarantine_gates_falsification_environment", False)
    )
    # Backward-compatible fallback for older evaluations or mis-specified outputs.
    if quarantined_crux_dependency:
        if quarantine_target == "causal_mechanism":
            quarantine_gates_causal_mechanism = True
        elif quarantine_target == "named_discriminator":
            quarantine_gates_causal_mechanism = True
            quarantine_gates_named_discriminator = True
        elif quarantine_target == "falsification_environment":
            quarantine_gates_falsification_environment = True
        elif quarantine_target == "unknown" and not (
            quarantine_gates_causal_mechanism
            or quarantine_gates_named_discriminator
            or quarantine_gates_falsification_environment
        ):
            quarantine_gates_causal_mechanism = True
    if quarantined_crux_dependency:
        if quarantine_gates_named_discriminator or quarantine_gates_falsification_environment:
            soft_score_caps.append(
                {
                    "reason": (
                        "Meta-Judge found a quarantined unresolved variable still gates the central "
                        "scored discriminator or falsification environment. "
                        f"{quarantine_rationale}".strip()
                    ),
                    "cap": 67,
                }
            )
        elif quarantine_gates_causal_mechanism:
            soft_score_caps.append(
                {
                    "reason": (
                        "Meta-Judge found a quarantined unresolved variable still gates the central "
                        f"causal mechanism. {quarantine_rationale}".strip()
                    ),
                    "cap": 83,
                }
            )
        elif quarantine_target == "background_only" and quarantine_legitimate:
            pass
        else:
            soft_score_caps.append(
                {
                    "reason": (
                        "Meta-Judge found a quarantined critical unresolved dependency with "
                        f"unclear scope. {quarantine_rationale}".strip()
                    ),
                    "cap": 83,
                }
            )

    current_discriminator_directly_confirmed = bool(
        evaluation.get("current_discriminator_directly_confirmed", False)
    )
    current_support_is_directional_only = bool(
        evaluation.get("current_support_is_directional_only", False)
    )
    decisive_confirmation_deferred_to_forward_observable = bool(
        evaluation.get("decisive_confirmation_deferred_to_forward_observable", False)
    )
    confirmation_rationale = str(evaluation.get("confirmation_rationale", "") or "").strip()
    if decisive_confirmation_deferred_to_forward_observable:
        if current_support_is_directional_only:
            soft_score_caps.append(
                {
                    "reason": (
                        "Meta-Judge found the central discriminator is only directionally "
                        "supported by current evidence and decisive confirmation is deferred "
                        f"to a forward observable. {confirmation_rationale}".strip()
                    ),
                    "cap": 83,
                }
            )
        elif not current_discriminator_directly_confirmed:
            soft_score_caps.append(
                {
                    "reason": (
                        "Meta-Judge found decisive confirmation of the central discriminator "
                        "is deferred to a forward observable without direct present confirmation. "
                        f"{confirmation_rationale}".strip()
                    ),
                    "cap": 67,
                }
            )

    project_forecast_type = project_charter_forecast_type or "unspecified"
    unsupported_point_probability_claim = bool(
        evaluation.get("unsupported_point_probability_claim", False)
    )
    forecast_overclaim_rationale = str(
        evaluation.get("forecast_overclaim_rationale", "") or ""
    ).strip()
    if project_forecast_type == "directional_forecast" and unsupported_point_probability_claim:
        soft_score_caps.append(
            {
                "reason": (
                    "Meta-Judge found an unsupported point-probability claim inside a "
                    "directional forecast project. "
                    f"{forecast_overclaim_rationale}".strip()
                ),
                "cap": 50,
            }
        )

    asymptotic_claim_assessment = assess_asymptotic_claim_discipline(
        thesis,
        project_charter_asymptotic_contract,
    )
    if asymptotic_claim_assessment.cap is not None:
        soft_score_caps.append(
            {
                "reason": asymptotic_claim_assessment.reason,
                "cap": asymptotic_claim_assessment.cap,
            }
        )

    anchor_proxy_coverage = None
    anchor_proxy_overlap = []
    anchor_proxy_active = []
    anchor_proxy_total = 0
    mathematical_drift_detected = False
    drift_distance = 0.0
    if os.path.exists(test_path) and project_charter_anchor_proxies:
        anchor_proxy_result = compute_anchor_proxy_coverage(
            Path(test_path),
            project_charter_anchor_proxies,
        )
        anchor_proxy_coverage = float(anchor_proxy_result["coverage"])
        anchor_proxy_overlap = list(anchor_proxy_result["overlap"])
        anchor_proxy_active = list(anchor_proxy_result["active_proxies"])
        anchor_proxy_total = int(anchor_proxy_result["anchor_total"])
        drift_distance = float(anchor_proxy_result["drift_distance"])
        mathematical_drift_detected = anchor_proxy_coverage < ANCHOR_PROXY_MIN_COVERAGE
        if mathematical_drift_detected:
            soft_score_caps.append(
                {
                    "reason": (
                        "Deterministic charter drift check found the active suite covers only "
                        f"{anchor_proxy_coverage:.2f} of declared Anchor Proxies "
                        f"(threshold={ANCHOR_PROXY_MIN_COVERAGE:.2f})."
                    ),
                    "cap": 50,
                }
            )

    drift_detected = bool(evaluation.get("drift_detected", False))
    drift_rationale = str(evaluation.get("drift_rationale", "") or "").strip()

    # GP-030 first slice: deterministic charter-gate evaluation. No-op
    # for projects whose charter has no `## Deterministic Gates`
    # section. For projects that DO declare gates, the gates bind to
    # `test_model.py` via the `--emit-deterministic-gates` harness
    # contract documented in `deterministic_charter_gates.py`. Gate
    # failures (and harness contract failures) fail-closed by adding
    # to `soft_score_caps` at `GATE_FAILURE_SCORE_CAP=50`.
    deterministic_gate_evaluation = evaluate_deterministic_charter_gates(
        charter_text=project_charter_content,
        test_model_path=Path(test_path),
    )
    deterministic_gate_caps = soft_cap_entries_for_evaluation(
        deterministic_gate_evaluation
    )
    if deterministic_gate_caps:
        soft_score_caps.extend(deterministic_gate_caps)

    criterion_score = round(100 * len(passed) / len(criteria_keys)) if criteria_keys else 0
    final_score = criterion_score
    cap_reason = "none"
    cap_reason_detail = ""
    if hard_fail_reasons:
        final_score = 0
        cap_reason = "hard_fail"
        cap_reason_detail = hard_fail_reasons[0]
    else:
        for cap in soft_score_caps:
            final_score = min(final_score, cap["cap"])
        if soft_score_caps:
            active_cap = min(soft_score_caps, key=lambda item: item["cap"])
            cap_reason = "soft_cap"
            cap_reason_detail = str(active_cap.get("reason", "") or "")
        final_score = max(0, min(100, final_score))

    evaluation["criteria_passed"] = passed
    evaluation["criteria_failed"] = failed
    evaluation["score_contract"] = {
        "mode": "deterministic_gates",
        "test_suite_status": test_suite_status,
        "criterion_score": criterion_score,
        "hard_fail_reasons": hard_fail_reasons,
        "soft_score_caps": soft_score_caps,
        "semantic_gate_status": evaluation.get("semantic_gate_status"),
        "self_reference_rule_fired": evaluation.get("self_reference_rule_fired"),
        "quarantined_crux_dependency": quarantined_crux_dependency,
        "quarantine_target": quarantine_target,
        "quarantine_legitimate": quarantine_legitimate,
        "quarantine_gates_causal_mechanism": quarantine_gates_causal_mechanism,
        "quarantine_gates_named_discriminator": quarantine_gates_named_discriminator,
        "quarantine_gates_falsification_environment": quarantine_gates_falsification_environment,
        "current_discriminator_directly_confirmed": current_discriminator_directly_confirmed,
        "current_support_is_directional_only": current_support_is_directional_only,
        "decisive_confirmation_deferred_to_forward_observable": decisive_confirmation_deferred_to_forward_observable,
        "confirmation_rationale": confirmation_rationale,
        "unsupported_point_probability_claim": unsupported_point_probability_claim,
        "forecast_overclaim_rationale": forecast_overclaim_rationale,
        "asymptotic_claim_discipline": asymptotic_claim_assessment.to_dict(),
        "project_charter_present": bool(project_charter_content),
        "project_forecast_type": project_forecast_type,
        "anchor_proxies_declared": list(project_charter_anchor_proxies),
        "anchor_proxy_total": anchor_proxy_total,
        "anchor_proxy_overlap": anchor_proxy_overlap,
        "anchor_proxy_coverage": anchor_proxy_coverage,
        "anchor_proxy_min_coverage": ANCHOR_PROXY_MIN_COVERAGE,
        "drift_distance": drift_distance,
        "mathematical_drift_detected": mathematical_drift_detected,
        "active_proxy_signature": anchor_proxy_active,
        "drift_detected": drift_detected,
        "drift_rationale": drift_rationale,
        "cap_reason": cap_reason,
        "cap_reason_detail": cap_reason_detail,
        "deterministic_charter_gates": {
            "declared": declared_gate_names(deterministic_gate_evaluation),
            "harness_invoked": deterministic_gate_evaluation.harness_invoked,
            "harness_failure_reason": deterministic_gate_evaluation.harness_failure_reason,
            "results": gate_results_to_dicts(deterministic_gate_evaluation),
            "any_failed": deterministic_gate_evaluation.any_failed,
            "failure_count": deterministic_gate_evaluation.failure_count,
            "score_cap_on_failure": 50,
        },
    }
    evaluation["unsupported_point_probability_claim"] = unsupported_point_probability_claim
    evaluation["forecast_overclaim_rationale"] = forecast_overclaim_rationale
    evaluation["project_forecast_type"] = project_forecast_type
    evaluation["effective_judge_models"] = sorted(JUDGE_EFFECTIVE_MODELS_USED) or [JUDGE_MODEL_ID]
    evaluation["judge_fallback_used"] = bool(JUDGE_FALLBACK_EVENTS)
    evaluation["score"] = final_score
    if hard_fail_reasons:
        strongest_reason = hard_fail_reasons[0]
        weakest_point = evaluation.get("weakest_point", "").strip()
        if not weakest_point:
            evaluation["weakest_point"] = strongest_reason
        elif strongest_reason not in weakest_point:
            evaluation["weakest_point"] = f"{strongest_reason} {weakest_point}"
    return evaluation


if __name__ == "__main__":
    thesis, evidence = read_file(WORKING_PATH), read_file(EVIDENCE_PATH)
    with open(MAIN_RUBRIC_PATH, "r") as f:
        main_rubric = json.load(f)

    critiques_text = ""

    log_path = f"{PROJECT_DIR}/debate_log_iter_{int(time.time())}.md"
    with open(log_path, "w") as log:
        log.write(f"# Adversarial Debate: {args.project}\n")
        log.write(
            f"<!-- rubric: {args.rubric} | mutator: {MUTATOR_MODEL_ID} | judge: {JUDGE_MODEL_ID} -->\n\n"
        )

        if args.dynamic and os.path.exists(DYNAMIC_RUBRIC_PATH):
            _raw_committee = json.load(open(DYNAMIC_RUBRIC_PATH))["committee"]
            # Normalize: committee may be a single dict or a list of dicts
            attackers = _raw_committee if isinstance(_raw_committee, list) else [_raw_committee]

            # Launch all attackers simultaneously
            print(f"🚀 Launching {len(attackers)} attackers in parallel...")
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(attackers)))
            try:
                future_to_attacker = {
                    executor.submit(run_specialized_attacker, thesis, evidence, att): att 
                    for att in attackers
                }
                for future in concurrent.futures.as_completed(future_to_attacker):
                    attacker = future_to_attacker[future]
                    try:
                        critique = future.result()
                        log.write(f"## Attacker: {attacker['role']}\n{critique}\n\n")
                        critiques_text += f"\n\n### Attack from {attacker['role']}:\n{critique}"
                    except Exception as exc:
                        print(f"❌ {attacker['role']} generated an exception: {exc}")
                        critiques_text += f"\n\n### Attack from {attacker['role']}:\nFAILED DUE TO EXCEPTION."
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
        else:
            # --- FIXED: Robust Extraction & Assignment ---
            prompt = f"Identify the single most catastrophic assumption in this thesis using tools if needed: {thesis}"
            attacker_config = None
            if JUDGE_PROVIDER_FAMILY == "google":
                attacker_config = (
                    ATTACKER_NO_TOOL_CONFIG if args.disable_attacker_tools else ATTACKER_CONFIG
                )
            response = safe_generate(prompt, config=attacker_config)
            
            try:
                # 1. Directly assign to critiques_text to avoid losing the AI's attack
                # The .text property raises a ValueError if the response was blocked by safety filters
                critiques_text = response.text if response and response.text else "⚠️ Attacker response was empty."
            except (ValueError, AttributeError) as exc:
                # 2. Capture and log safety blocks or empty candidates
                error_info = f"⚠️ Attack BLOCKED (Possible Safety Filter): {str(exc)}"
                if response and hasattr(response, 'candidates') and response.candidates:
                    reason = response.candidates[0].finish_reason
                    error_info = f"⚠️ Attack BLOCKED BY SAFETY FILTERS. Reason: {reason}"             
                print(f"\n🛑 {error_info}")
                critiques_text = error_info

        # --- LEVEL 3: THE FALSIFICATION SUITE (The "Tester") ---
        print("⚙️ Executing Falsification Suite (Level 3)...")
        test_path = f"{PROJECT_DIR}/test_model.py"
        test_result_summary = ""
        test_suite_status = "missing"

        # GP-211 substrate dispatch: when the rubric declares
        # cage_meta.substrate_class == "lean_proof", the test_model.py path is
        # NOT critical — the actual falsifier is `lake build` against the
        # mutator's ```lean fenced block in thesis.md. Closes the iter-1/iter-2
        # fake-95 path where Lean-shaped prose + a Python tautology scored as
        # "validated" because the judge can't run Lean.
        from ztare.validator.lean_substrate_runner import (
            is_lean_proof_substrate,
            run_lean_substrate_iteration,
        )
        _lean_substrate = is_lean_proof_substrate(main_rubric)
        if _lean_substrate:
            print("🧮 Lean-proof substrate detected — dispatching to lake build harness")
            _lean_iter = run_lean_substrate_iteration(
                project_dir=Path(PROJECT_DIR),
                rubric=main_rubric,
                iteration=int(time.time()),
            )
            test_result_summary = _lean_iter["test_result_summary"]
            test_suite_status = _lean_iter["test_suite_status"]
            # Persist the gate dict alongside the project for audit / debugging.
            try:
                _lean_audit_path = Path(PROJECT_DIR) / "lean_proof_gate_result.json"
                _lean_audit_path.write_text(
                    json.dumps(_lean_iter["lean_proof_gate"], indent=2),
                    encoding="utf-8",
                )
            except Exception as _exc:  # non-fatal
                print(f"⚠️ could not persist lean_proof_gate_result.json: {_exc}")
            print(f"   gate verdict: {test_suite_status}")
        elif os.path.exists(test_path):
            try:
                # Prefer a sibling `gate_harness.py` when present. The
                # frozen harness sits outside the mutator's write-scope
                # and runs the assertion suite against a frozen parser,
                # so mutator drift in test_model.py's own parser /
                # assertion block cannot cause fail_runtime. The frozen
                # harness imports I_model / MODEL_PARAMS from the
                # mutator's test_model.py, so substantive falsification
                # of the thesis still surfaces as fail_assert.
                frozen_harness_path = os.path.join(PROJECT_DIR, "gate_harness.py")
                if os.path.exists(frozen_harness_path):
                    run_cmd = [sys.executable, frozen_harness_path, "--run-visible-assertions"]
                else:
                    run_cmd = [sys.executable, test_path]
                # Run from the project directory. Candidate suites may use
                # project-relative paths such as workspace/... or raw/...
                # but repo-root paths like projects/<slug>/... are a
                # contract miss. Do not materialize a projects/ symlink here:
                # it leaks the repo tree into the project and hides that miss.
                res = subprocess.run(
                    run_cmd, capture_output=True, text=True, timeout=15,
                    cwd=PROJECT_DIR,
                )

                if res.returncode == 0:
                    test_result_summary = f"✅ PASS: The thesis survived its own falsification suite.\nOutput: {res.stdout}"
                    test_suite_status = "pass"
                    print("✅ Unit tests passed.")
                else:
                    # GP-023 Phase 1 post-mortem: distinguish an
                    # AssertionError (substantive falsification) from
                    # a runtime/import/syntax error (broken harness).
                    # The Phase 1 Judge rationalized an IndexError as
                    # "mostly passed" because stderr was dumped as
                    # opaque text with no categorization. Structuring
                    # the label removes that rationalization surface.
                    failure_mode, exception_name = classify_harness_failure(
                        res.stderr, getattr(res, "stdout", "") or ""
                    )
                    # GP-157 v5.0 Gap #1: sanitize stderr before it flows back
                    # to the mutator's prompt. Full stderr stays in operator
                    # logs (printed below); only the mutator-facing summary
                    # uses the sanitized leaf error. Closes Popper-leakage:
                    # mutator can't reverse-engineer file paths, line numbers,
                    # or apparatus stack frames into a test-passing regex.
                    _sanitized_err = sanitize_stderr_for_mutator(res.stderr, exception_name)
                    if failure_mode == FAIL_ASSERT:
                        test_result_summary = (
                            f"❌ FAIL (assertion): The thesis was DISPROVEN by its own unit tests.\n"
                            f"Error: {_sanitized_err}"
                        )
                        test_suite_status = "fail_assert"
                        print(f"❌ Unit tests failed (assertion): {res.stderr[:80]}...")
                    else:
                        banner = harness_defect_banner(exception_name)
                        test_result_summary = (
                            f"❌ FAIL (harness defect): {banner}\n"
                            f"Error: {_sanitized_err}"
                        )
                        test_suite_status = "fail_runtime" if failure_mode == FAIL_RUNTIME else "fail_other"
                        print(f"🚨 Harness defect ({test_suite_status}): {res.stderr[:80]}...")

            except subprocess.TimeoutExpired:
                test_result_summary = "❌ FAIL: The simulation timed out. The logic is computationally impossible."
                test_suite_status = "timeout"
                print("⏳ Simulation timed out.")
        else:
            test_result_summary = "⚠️ WARNING: No falsification suite (test_model.py) found for this iteration."
            test_suite_status = "missing"

        # MANDATORY: Append the results to critiques_text so the Judge sees it!
        critiques_text += (
            f"\n\n### LEVEL 3 QUANTITATIVE UNIT TEST RESULTS:\n{test_result_summary}"
        )
        log.write(f"\n## Level 3 Unit Test Results\n{test_result_summary}\n\n")
        AXIOM_PATH = f"{PROJECT_DIR}/verified_axioms.json"
        axioms = []
        if os.path.exists(AXIOM_PATH):
            with open(AXIOM_PATH, "r") as f:
                axioms = json.load(f)
        evaluation = run_meta_judge(
            thesis, evidence, main_rubric, critiques_text, axioms
        )
        # Lean-substrate hard ceiling on the judge's score: when the
        # G-LEAN-PROOF gate failed (compile or axiom audit), the judge
        # cannot return >10 regardless of prose-quality opinion. Closes
        # the iter-4 fake-70 path where the judge hallucinated compile
        # success in the same response that contained "compiled: False".
        # The judge's rationale text is preserved (useful signal for the
        # next iter's mutator); only the numeric score is clamped.
        if _lean_substrate and not _lean_iter["lean_proof_gate"].get("gate_passed", False):
            _judge_score = evaluation.get("score") or 0
            if _judge_score > 10:
                evaluation["lean_gate_clamp_applied"] = True
                evaluation["lean_gate_clamp_original_judge_score"] = _judge_score
                evaluation["score"] = 10
                print(
                    f"   🔒 Lean-gate clamp: judge score {_judge_score} → 10 "
                    f"(gate_passed=False)"
                )
        if args.deterministic_score_gates:
            evaluation = apply_semantic_gate_stabilization(evaluation)
            # P1 fix (deep audit, 2026-04-26): finalize_deterministic_score
            # was running here, BEFORE the holdout-hard-gate dispatch at
            # line 2393+ which sets evaluation["holdout_hard_gate_fired"].
            # That made the Bug B fix (gate_harness_ran demote) dead code
            # because the key is always absent at this point. Defer the
            # finalize call to after the gate dispatch.
            _defer_deterministic_finalize = True
        else:
            _defer_deterministic_finalize = False
            # H-JUDGE-01: in the raw-LLM-score path (no --deterministic_score_gates),
            # the HARNESS DEFECT banner is shown to the judge but not enforced.
            # Observed: judge scored 108 despite a ModuleNotFoundError, ignoring its
            # own "MUST NOT rationalize" instruction under structural compliance pressure.
            # Programmatically cap at 50 when the harness did not run to completion.
            if test_suite_status in ("fail_runtime", "fail_other"):
                llm_score = evaluation.get("score") or 0
                if llm_score > 50:
                    evaluation["score"] = 50
                    evaluation["cap_reason"] = "harness_defect_cap"
                    evaluation["cap_reason_detail"] = (
                        f"Score capped at 50 (was {llm_score}): "
                        f"test_suite_status={test_suite_status!r}. "
                        "Harness tooling failure — thesis was not tested. "
                        "See H-JUDGE-01 in ztare_mission_hypothesis_ledger_seam.md."
                    )
                    print(
                        f"🔒 Harness defect cap applied: score {llm_score} → 50 "
                        f"({test_suite_status})"
                    )
        # F-GP073-S15-04: Holdout hard-gate. If the rubric declares
        # holdout_hard_gate and a gate_harness.py + evidence_holdout.txt
        # exist, run the holdout gate. If it fails, score → 0. A compelling
        # derivation of a wrong formula is not science.
        if main_rubric.get("holdout_hard_gate"):
            holdout_evidence_path = os.path.join(PROJECT_DIR, "evidence_holdout.txt")
            holdout_harness_path = os.path.join(PROJECT_DIR, "gate_harness.py")
            if os.path.exists(holdout_evidence_path) and os.path.exists(holdout_harness_path):
                try:
                    # GP-135 fix (2026-04-23): pass --emit-deterministic-gates
                    # flag. Without it, the harness default branch emits
                    # {"exact_match": ..., "matches": ..., "errors": ...} with
                    # NO "harness_ok" or "gates" key → KeyError → "FIRED
                    # (exception)" every iter, zeroing valid proposals.
                    holdout_res = subprocess.run(
                        [sys.executable, holdout_harness_path, "--emit-deterministic-gates"],
                        capture_output=True, text=True, timeout=30,
                        cwd=PROJECT_DIR,
                    )
                    # GP-156 Bug #21 (2026-04-25): GP-156-style harnesses
                    # raise AssertionError after printing JSON, so returncode
                    # may be nonzero even when stdout has parseable JSON. Try
                    # to parse stdout regardless of returncode; only fall to
                    # the "harness error" branch if parsing genuinely fails.
                    _stdout_json = None
                    try:
                        if holdout_res.stdout:
                            _stdout_json = json.loads(holdout_res.stdout)
                    except json.JSONDecodeError:
                        _stdout_json = None
                    # GP-156-shape harness: emits {holdout: {passed, near_miss},
                    # farther_tail: {...}, all_gates_pass, any_near_miss}.
                    # Translate into the legacy {harness_ok, gates: [...]} shape
                    # the hard-gate expects, AND apply near-miss floor.
                    if _stdout_json is not None and "all_gates_pass" in _stdout_json \
                            and "harness_ok" not in _stdout_json:
                        _gates_list = []
                        for _gname in ("holdout", "farther_tail"):
                            _g = _stdout_json.get(_gname)
                            if isinstance(_g, dict):
                                _gates_list.append({
                                    "name": _gname.upper(),
                                    "passed": bool(_g.get("passed", False)),
                                    "near_miss": bool(_g.get("near_miss", False)),
                                    "value": _g.get("mean_relative_error"),
                                    "threshold": _g.get("threshold"),
                                    "operator": "<",
                                })
                        _stdout_json["harness_ok"] = True
                        _stdout_json["gates"] = _gates_list
                    if _stdout_json is not None and "harness_ok" in _stdout_json:
                        holdout_payload = _stdout_json
                    elif holdout_res.returncode == 0:
                        holdout_payload = json.loads(holdout_res.stdout)
                        if "harness_ok" not in holdout_payload:
                            raise KeyError(
                                "gate_harness.py output missing required key 'harness_ok'. "
                                f"Got keys: {list(holdout_payload.keys())}"
                            )
                    else:
                        holdout_payload = None
                    if holdout_payload is not None:
                        # Check harness_ok AND that every declared gate actually passed.
                        # exit code 0 alone is not sufficient — older harnesses return 0
                        # whenever harness_ok=True regardless of gate outcomes.
                        # GP-135 fix (2026-04-23): support BOTH dict and list gate formats,
                        # and read "passed" key (the actual harness emits "passed", not "pass").
                        gate_results = holdout_payload.get("gates", [])
                        if isinstance(gate_results, dict):
                            gate_iter = list(gate_results.values())
                        elif isinstance(gate_results, list):
                            gate_iter = gate_results
                        else:
                            gate_iter = []
                        # Check both "passed" (current harness) and "pass" (legacy) keys.
                        def _gate_passed(g):
                            return bool(g.get("passed", g.get("pass", False)))
                        all_gates_passed = holdout_payload["harness_ok"] and all(
                            _gate_passed(g) for g in gate_iter
                        )
                        failed_gates = [
                            f"{g.get('name', '?')}: {g.get('value', '?')} {g.get('operator', '?')} {g.get('threshold', '?')}"
                            for g in gate_iter
                            if not _gate_passed(g)
                        ]
                        # GP-156 Bug #21 (2026-04-25): the hard-gate is NAMED
                        # holdout_hard_gate but the legacy logic zeroed on ANY
                        # gate failing — including FARTHER_TAIL near-misses on
                        # an otherwise-passing HOLDOUT. The judge already saw
                        # the gate output (incl. [near_miss] tag from Bug #18)
                        # and calibrated. Refined semantics:
                        #   - HOLDOUT hard-miss     → score 0 (unchanged)
                        #   - HOLDOUT near-miss     → floor at 30 (model is
                        #                              structurally close)
                        #   - HOLDOUT pass + others → keep judge score (judge
                        #                              already calibrated for
                        #                              FARTHER_TAIL near-miss)
                        _holdout_gate = next(
                            (g for g in gate_iter if g.get("name") == "HOLDOUT"),
                            None,
                        )
                        _holdout_passed = bool(_holdout_gate and _gate_passed(_holdout_gate))
                        _holdout_near_miss = bool(_holdout_gate and _holdout_gate.get("near_miss"))
                        if not all_gates_passed and not _holdout_passed and not _holdout_near_miss:
                            pre_cap_score = evaluation.get("score", 0)
                            evaluation["score"] = 0
                            evaluation["holdout_hard_gate_fired"] = True
                            evaluation["holdout_hard_gate_detail"] = (
                                f"HOLDOUT hard-miss. failed_gates={failed_gates}. "
                                f"Score {pre_cap_score} → 0."
                            )
                            print(
                                f"🚫 Holdout hard-gate FIRED (hard-miss): "
                                f"failed_gates={failed_gates}, score {pre_cap_score} → 0"
                            )
                        elif not all_gates_passed and not _holdout_passed and _holdout_near_miss:
                            pre_cap_score = evaluation.get("score", 0)
                            _floor = 30
                            # GP-167 fix (2026-04-25, panel-revealed): the
                            # previous expression `min(pre_cap_score, _floor) if
                            # pre_cap_score >= _floor else _floor` always
                            # evaluated to _floor=30 regardless of input, which
                            # destroyed the judge's gradient signal — a
                            # well-rated near-miss (judge=70) and a poorly-rated
                            # near-miss (judge=15) collapsed to the same 30.
                            # Now: max-floor preserves the judge's score when
                            # it exceeds the floor, raises to floor only when
                            # it doesn't (graduated near-miss credit).
                            evaluation["score"] = max(pre_cap_score, _floor)
                            evaluation["holdout_hard_gate_fired"] = True
                            evaluation["holdout_hard_gate_detail"] = (
                                f"HOLDOUT near-miss. failed_gates={failed_gates}. "
                                f"Score floored to {evaluation['score']} (was {pre_cap_score}). "
                                f"REFINE the form, do not redesign."
                            )
                            print(
                                f"⚠️  Holdout hard-gate near-miss: floor={_floor}, "
                                f"score {pre_cap_score} → {evaluation['score']} (REFINE)"
                            )
                        elif not all_gates_passed and _holdout_passed:
                            # HOLDOUT passed; another gate (e.g. FARTHER_TAIL)
                            # failed. 2026-04-26 fix: when the rubric
                            # explicitly enforces per-class farther-tail,
                            # FARTHER_TAIL failure must NOT be silently
                            # non-blocking — the apparatus caps the score at
                            # `cage_constant_laundering_score_cap` (default 50)
                            # so the judge's qualitative reward for visible
                            # compliance can't paper over a cross-class
                            # generalization failure. R11 catches the per-class
                            # case explicitly; this catches the OVERALL
                            # FARTHER_TAIL failure on substrates where R11
                            # didn't engage (sparse class, harness path mismatch).
                            _enforce_ftail = bool(
                                main_rubric.get("enforce_per_class_farther_tail", False)
                            ) if isinstance(main_rubric, dict) else False
                            _ftail_failed = any(
                                "FARTHER_TAIL" in str(g) for g in (failed_gates or [])
                            )
                            if _enforce_ftail and _ftail_failed:
                                cap = int(main_rubric.get(
                                    "cage_constant_laundering_score_cap", 50
                                ))
                                pre_cap = int(evaluation.get("score", 0) or 0)
                                if pre_cap > cap:
                                    evaluation["score"] = cap
                                    evaluation["holdout_hard_gate_fired"] = True
                                    evaluation["holdout_hard_gate_detail"] = (
                                        f"HOLDOUT passed but FARTHER_TAIL failed "
                                        f"({failed_gates}); rubric.enforce_per_class_farther_tail=true "
                                        f"so apparatus caps score at {cap} "
                                        f"(was {pre_cap}). The thesis fits visible data "
                                        f"but does not generalize across classes — that's "
                                        f"either a pre-committed null finding or a refinement "
                                        f"target, but it cannot earn a Newton-step score."
                                    )
                                    print(
                                        f"🚫 Holdout hard-gate: HOLDOUT passed but FARTHER_TAIL "
                                        f"failed AND rubric.enforce_per_class_farther_tail=true. "
                                        f"Score {pre_cap} → {cap} (apparatus cap)."
                                    )
                                else:
                                    evaluation["holdout_hard_gate_fired"] = False
                                    print(
                                        f"⚠️  Holdout hard-gate: FARTHER_TAIL failed but judge "
                                        f"score {pre_cap} already at/below cap {cap}; no override."
                                    )
                            else:
                                # Legacy soft path (rubric did not opt into hard ftail enforcement)
                                evaluation["holdout_hard_gate_fired"] = False
                                evaluation["holdout_hard_gate_detail"] = (
                                    f"HOLDOUT passed; non-blocking gate(s) failed: "
                                    f"{failed_gates}. Judge score kept "
                                    f"(rubric did not set enforce_per_class_farther_tail=true)."
                                )
                                print(
                                    f"⚠️  Holdout hard-gate: HOLDOUT passed but "
                                    f"{failed_gates} failed (non-blocking, no rubric enforcement). "
                                    f"Score {evaluation.get('score')} kept."
                                )
                        else:
                            evaluation["holdout_hard_gate_fired"] = False
                            print(f"✅ Holdout hard-gate passed: all {len(gate_iter)} gate(s) OK")
                    else:
                        evaluation["holdout_hard_gate_fired"] = True
                        pre_cap_score = evaluation.get("score", 0)
                        evaluation["score"] = 0
                        evaluation["holdout_hard_gate_detail"] = (
                            f"gate_harness.py returned non-zero ({holdout_res.returncode}). "
                            f"Fail-closed: score {pre_cap_score} → 0. "
                            f"stderr: {holdout_res.stderr[:200]}"
                        )
                        print(
                            f"🚫 Holdout hard-gate FIRED (harness error): "
                            f"score {pre_cap_score} → 0"
                        )
                except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as exc:
                    evaluation["holdout_hard_gate_fired"] = True
                    pre_cap_score = evaluation.get("score", 0)
                    evaluation["score"] = 0
                    # GP-135 diagnostic (2026-04-23): print full exception
                    # details so the operator can see WHAT exception fired.
                    # The silent "score → 0" message was masking all downstream
                    # investigation; we now always name the exception class and
                    # dump enough context to diagnose in-flight.
                    import traceback as _tb
                    _exc_type = type(exc).__name__
                    _exc_msg = str(exc)[:400]
                    _tb_str = _tb.format_exc()[:800]
                    evaluation["holdout_hard_gate_detail"] = (
                        f"Holdout gate exception: {_exc_type}: {_exc_msg}. "
                        f"Fail-closed: score {pre_cap_score} → 0. "
                        f"Traceback (last 800 chars):\n{_tb_str}"
                    )
                    print(f"🚫 Holdout hard-gate FIRED (exception: {_exc_type}: {_exc_msg[:120]}): score → 0")
                    print(f"   holdout_res.returncode: {getattr(holdout_res, 'returncode', 'N/A') if 'holdout_res' in dir() else 'subprocess_never_ran'}")
                    if 'holdout_res' in dir():
                        print(f"   holdout_res.stdout[:400]: {holdout_res.stdout[:400]!r}")
                        print(f"   holdout_res.stderr[:400]: {holdout_res.stderr[:400]!r}")

        # P1 fix (deep audit, 2026-04-26): deferred finalize. Now that the
        # holdout-hard-gate dispatch above has set evaluation["holdout_hard_gate_fired"]
        # (when applicable), finalize_deterministic_score can read it and
        # apply the Bug B fix (demote test_suite_status fail_other to soft
        # cap when gate_harness_ran). Holdout gate's score=0 is preserved
        # because finalize re-zeroes when holdout_hard_gate_fired is True.
        if _defer_deterministic_finalize:
            evaluation = finalize_deterministic_score(
                evaluation, main_rubric, test_suite_status
            )

        evaluation = attach_evidence_gap_metadata(evaluation)
        evaluation = attach_constraint_proposal_metadata(evaluation)
        evaluation = apply_evidence_gap_score_caps(evaluation, main_rubric)
        evaluation = attach_score_regime_metadata(evaluation, main_rubric, test_suite_status)
        persist_evidence_gap_artifact(evaluation)
        persist_constraint_proposal_artifact(evaluation)
        log.write(f"# Final Score: {evaluation.get('score', 0)}\n")
        log.write(f"**Weakest Point:** {evaluation.get('weakest_point', 'Score missing from judge response')}\n")
        log.write(f"**Rationale:** {evaluation.get('debate_summary', 'N/A')}\n")
        if evaluation.get("crux_analysis"):
            log.write("**Crux Analysis:**\n")
            log.write("```json\n")
            log.write(json.dumps(evaluation["crux_analysis"], indent=2))
            log.write("\n```\n")

        print("\n" + "█" * 60)
        print(f"⭐ FINAL VERDICT SCORE: {evaluation.get('score', 0)}")
        # GP-156 fix (2026-04-25): hardened against malformed judge JSON
        # missing 'weakest_point' field — was crashing the auditor
        # subprocess and triggering a KeyError that the loop recorded as
        # stagnation_count++ instead of as a recoverable judge-format
        # error.
        print(f"🛑 WEAKEST POINT: {evaluation.get('weakest_point', '(judge response missing weakest_point field)')}")
        print(f"🧠 RATIONALE: {evaluation.get('debate_summary', 'N/A')}")
        print(f"📝 FULL LOG SAVED TO: {log_path}")
        print("█" * 60 + "\n")

    evaluation["usage_telemetry"] = dict(JUDGE_USAGE)
    evaluation["worker_dispatch_receipts"] = list(JUDGE_WORKER_DISPATCH_RECEIPTS)
    latest_eval_payload = _evaluation_artifact_payload(evaluation, artifact_role="latest")
    eval_results_path = Path(args.eval_results_path)
    eval_results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(eval_results_path, "w") as f:
        json.dump(latest_eval_payload, f, indent=2)

    latest_eval_path = Path(LATEST_EVAL_RESULTS_PATH)
    if latest_eval_path.resolve() != eval_results_path.resolve():
        latest_eval_path.parent.mkdir(parents=True, exist_ok=True)
        latest_eval_path.write_text(json.dumps(latest_eval_payload, indent=2), encoding="utf-8")

    if "probability_dag" in evaluation:
        latest_probability_dag_path = Path(LATEST_PROBABILITY_DAG_PATH)
        latest_probability_dag_path.parent.mkdir(parents=True, exist_ok=True)
        with open(latest_probability_dag_path, "w") as f:
            json.dump(evaluation["probability_dag"], f, indent=2)
        print(f"📊 Probability DAG saved to: {LATEST_PROBABILITY_DAG_PATH}")
