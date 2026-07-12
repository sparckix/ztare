from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ztare.common.control_state_machine import (
    ControlMorphism,
    control_receipt_rows,
    executed_morphism_ids_from_receipts,
)
from ztare.common.leaf_workbench_contract import (
    leaf_workbench_action_request_object,
    render_leaf_workbench_control_rules,
)
from ztare.common.retry_prompt_assembly import (
    candidate_memory_refs_for_retry,
    packed_control_receipts,
    render_retry_pack_lines,
)
from ztare.common.science_output_policy import SCIENCE_OUTPUT_POLICY
from ztare.common.sealed_boundary_cegar import (
    boundary_cegar_candidate_delta_lowerability,
    render_boundary_cegar_retry_surface,
)
from ztare.common.strategy_card_roles import (
    META_HARDENING_LANE,
    SKILL_ACQUISITION_LANE,
    strategy_card_blocks_context,
    strategy_card_role,
)
from ztare.orchestrator.retry_contract import (
    RetryContractSurface,
    render_retry_contract_surface,
)
from ztare.validator.core.strategy_card_gate import admissible_no_attempt_blocker_kinds
from ztare.worldmodel.patch_carrier_contract import (
    patch_base_declaration,
    patch_carrier_brief_line,
    patch_delta_signature,
)


_CANDIDATE_BOUND_RECEIPT_RE = re.compile(
    r"candidate-bearing\s+receipt\s+`([^`]+)`"
)


def _patch_base_context_for_retry(
    project_dir: str | Path | None,
    *,
    max_chars: int = 30000,
) -> str:
    """Attach the authoritative patch-base reference for retry composition."""
    if project_dir is None:
        return ""
    project = Path(project_dir)
    try:
        payload = json.loads(
            (project / "workspace" / "candidate_memory.json").read_text(
                encoding="utf-8",
            )
        )
    except Exception:
        return ""
    if not isinstance(payload, dict):
        return ""
    records = [
        rec
        for rec in (payload.get("records") or [])
        if isinstance(rec, dict) and str(rec.get("submission") or "").strip().startswith("workspace/submissions/")
    ]
    if not records:
        return ""
    def _rank(rec: dict[str, Any]) -> tuple[int, int, int, float, int]:
        return (
            1 if rec.get("source_type") == "full_survivor" else 0,
            int(rec.get("visible_exact_rows") or 0),
            int(rec.get("holdout_depth") or 0),
            float(rec.get("gate_score") or 0.0),
            -int(rec.get("visible_wrong_cells") or 0),
        )
    best = max(records, key=_rank)
    refs = candidate_memory_refs_for_retry(project)
    source_ref = refs[0] if refs else str(best.get("submission") or "").strip()
    source_path = (project / source_ref).resolve()
    if not source_path.exists() or not source_path.is_file():
        return ""
    sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    patch_base_decl = patch_base_declaration(source_ref, sha)
    return (
        "\nAUTHORITATIVE PATCH BASE REFERENCE (compose by hash; do not copy "
        "or reconstruct the carrier source):\n"
        f"- patch_base_ref: {source_ref}\n"
        f"- patch_base_sha: {sha}\n"
        f"- visible_exact_rows: {best.get('visible_exact_rows')}/{best.get('visible_checked_rows')}\n"
        "- use this exact declaration in `test_model_py`, then define only "
        f"the minimal `{patch_delta_signature()}`:\n"
        f"  `{patch_base_decl}`\n"
    )


def _counterexample_context_for_retry(project_dir: str | Path | None) -> str:
    """Return compact context from the latest producer-issued quotient receipt."""
    if project_dir is None:
        return ""
    try:
        from ztare.worldmodel.leaf_workbench import (
            run_worldmodel_counterexample_context_probe,
        )

        summary = run_worldmodel_counterexample_context_probe(project_dir)
    except Exception:
        return ""
    if not summary.strip():
        return ""
    return (
        "\nFRESH COUNTEREXAMPLE CONTEXT (from latest patch-base regression receipt; "
        "use as typed evidence, not as authority over the gate):\n"
        f"{summary.strip()}\n\n"
    )


def _latest_workbench_task_morphism(
    project_dir: str | Path | None,
    *,
    executed_caps: list[str] | None = None,
    allow_candidate_rebind: bool = False,
    allow_input_rebind_caps: set[str] | None = None,
) -> ControlMorphism | None:
    """Return the next workbench action named by the latest weakness receipt."""
    if project_dir is None:
        return None
    try:
        payload = json.loads(
            (Path(project_dir) / "workspace" / "latest_harness_weakness.json").read_text(
                encoding="utf-8",
            )
        )
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    task = payload.get("workbench_task")
    task = task if isinstance(task, dict) else {}
    caps = task.get("admissible_capability_ids")
    if not isinstance(caps, list):
        caps = []
    recommended = str(payload.get("recommended_capability_id") or "").strip()
    ordered = [str(cap).strip() for cap in caps if str(cap).strip()]
    if recommended and recommended not in ordered:
        ordered.insert(0, recommended)
    executed = set(executed_caps or [])
    allow_input_rebind_caps = allow_input_rebind_caps or set()
    cap = next(
        (
            row
            for row in ordered
            if row and (
                row not in executed
                or (allow_candidate_rebind and row == "run_strategy_required_gate")
                or row in allow_input_rebind_caps
            )
        ),
        "",
    )
    if not cap:
        return None
    artifacts = [
        str(ref)
        for ref in (task.get("visible_artifact_refs") or [])
        if str(ref).strip()
    ]
    input_refs = _workbench_input_refs_for_capability(cap, artifacts, project_dir=project_dir)
    return ControlMorphism(
        capability_id=cap,
        input_refs=input_refs,
        claim_bindings=[
            str(task.get("objective") or payload.get("recommended_route") or cap).strip()
            or cap
        ],
    )


def _open_strategy_receipt_morphism(
    project_dir: str | Path | None,
    *,
    executed_caps: list[str] | None = None,
    allow_input_rebind_caps: set[str] | None = None,
) -> ControlMorphism | None:
    """Return a producer-receipt diagnostic selected by an open Strategy card."""

    if project_dir is None:
        return None
    cap = "mine_worldmodel_global_carrier_selectors_from_observable_context"
    executed = set(executed_caps or [])
    allow_input_rebind_caps = allow_input_rebind_caps or set()
    if cap in executed and cap not in allow_input_rebind_caps:
        return None
    project = Path(project_dir)
    if not (project / "workspace" / "latest_level_transfer_probe.json").exists():
        return None
    try:
        from ztare.common.operator_proposal_contract import open_cards

        cards = open_cards(project / "workspace" / "strategy_experiments.jsonl")
    except Exception:  # noqa: BLE001
        return None
    for card in cards:
        if not isinstance(card, dict):
            continue
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        if str(plan.get("source_receipt") or "") != "workspace/latest_level_transfer_probe.json":
            continue
        return ControlMorphism(
            capability_id=cap,
            input_refs={
                "strategy_gate_receipt_ref": "workspace/latest_level_transfer_probe.json",
                "source_card_sha": str(card.get("failure_family_sha") or ""),
            },
            claim_bindings=[
                "mine lowerable carrier selectors for the open Strategy repair residue",
            ],
        )
    return None


def _workbench_input_refs_for_capability(
    capability_id: str,
    artifact_refs: list[str],
    *,
    project_dir: str | Path | None = None,
) -> dict[str, Any]:
    from ztare.worldmodel.leaf_workbench import (
        worldmodel_workbench_input_refs_for_capability,
    )

    return worldmodel_workbench_input_refs_for_capability(
        capability_id,
        artifact_refs,
        project_dir=project_dir,
    )


def _candidate_bound_capability_from_r1_error(r1_error: str) -> str:
    text = str(r1_error or "")
    if "LEAF_WORKBENCH_RECEIPT_PROVENANCE_PRECHECK" not in text:
        return ""
    match = _CANDIDATE_BOUND_RECEIPT_RE.search(text)
    if not match:
        return ""
    return str(match.group(1) or "").strip()


def _candidate_bound_retry_morphism(capability_id: str) -> ControlMorphism:
    return ControlMorphism(
        capability_id=capability_id,
        input_refs=_workbench_input_refs_for_capability(capability_id, []),
        claim_bindings=[f"bind {capability_id} to current candidate"],
    )


def _current_artifact_hashes(
    project_dir: str | Path | None,
    artifact_refs: list[str],
) -> dict[str, str]:
    if project_dir is None:
        return {}
    project = Path(project_dir)
    hashes: dict[str, str] = {}
    for ref in artifact_refs:
        ref = str(ref or "").strip()
        if not ref or ":" in ref:
            continue
        path = project / ref
        try:
            if path.is_file():
                hashes[ref] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
    return hashes


def _workbench_receipt_artifact_hashes(
    retry_state_text: str,
    *,
    capability_id: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in _workbench_receipt_rows_for_retry(retry_state_text):
        payload = row.get("payload") if isinstance(row, dict) else None
        if not isinstance(payload, dict):
            continue
        if str(payload.get("capability_id") or "").strip() != capability_id:
            continue
        input_hashes = payload.get("input_hashes")
        if not isinstance(input_hashes, dict):
            continue
        artifact_hashes = input_hashes.get("artifact_hashes")
        if not isinstance(artifact_hashes, dict):
            continue
        normalized = {
            str(ref): str(digest)
            for ref, digest in artifact_hashes.items()
            if str(ref).strip() and str(digest).strip()
        }
        if normalized:
            rows.append(normalized)
    return rows


def _workbench_inputs_changed_since_receipt(
    project_dir: str | Path | None,
    retry_state_text: str,
    *,
    capability_id: str,
    artifact_refs: list[str],
) -> bool:
    current = _current_artifact_hashes(project_dir, artifact_refs)
    if not current:
        return False
    prior_rows = _workbench_receipt_artifact_hashes(
        retry_state_text,
        capability_id=capability_id,
    )
    if not prior_rows:
        return False
    for prior in prior_rows:
        for ref, digest in current.items():
            if prior.get(ref) != digest:
                return True
    return False


def _ready_receipts_json_for_retry(
    retry_state_text: str,
    *,
    exclude_candidate_bound_capability: str = "",
) -> str:
    rows = _workbench_receipt_rows_for_retry(retry_state_text)
    if exclude_candidate_bound_capability:
        rows = [
            row
            for row in rows
            if not (
                isinstance(row.get("payload"), dict)
                and str(row["payload"].get("capability_id") or "").strip()
                == exclude_candidate_bound_capability
            )
        ]
    return json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str) if rows else ""


def _workbench_receipt_rows_for_retry(retry_state_text: str) -> list[dict[str, Any]]:
    return [
        row for row in control_receipt_rows(retry_state_text or "")
        if str(row.get("type") or "") in {"LEAF_WORKBENCH_RECEIPT", "VISIBLE_WORKBENCH_DIAGNOSTIC"}
    ]


def _ready_receipt_facts_for_retry(
    retry_state_text: str,
    *,
    exclude_candidate_bound_capability: str = "",
    max_predicates: int = 4,
) -> str:
    rows = _workbench_receipt_rows_for_retry(retry_state_text)
    facts: list[dict[str, object]] = []
    for row in rows:
        payload = row.get("payload") if isinstance(row, dict) else None
        if not isinstance(payload, dict):
            continue
        cap = str(payload.get("capability_id") or "").strip()
        if exclude_candidate_bound_capability and cap == exclude_candidate_bound_capability:
            continue
        input_hashes = payload.get("input_hashes") if isinstance(payload.get("input_hashes"), dict) else {}
        summary = _parse_jsonish(payload.get("output_summary"))
        fact: dict[str, object] = {
            "capability_id": cap,
            "output_ref": payload.get("output_ref") or input_hashes.get("receipt_ref") or "",
            "kernel_receipt_ref": input_hashes.get("kernel_receipt_ref") or "",
            "source_ref": (
                input_hashes.get("strategy_gate_receipt_ref")
                or input_hashes.get("source_ref")
                or input_hashes.get("receipt_ref")
                or ""
            ),
        }
        if isinstance(summary, dict):
            for key in (
                "status",
                "command",
                "exact_steps",
                "steps_tested",
                "local_residue_status",
                "local_residue_class_count",
                "lowerability_status",
                "candidate_delta_admissible",
                "candidate_label_coverage",
                "forbidden_feature_classes",
                "executable_delta_hint",
                "top_local_residue_class",
            ):
                if key in summary:
                    fact[key] = summary[key]
            predicates = summary.get("candidate_predicates")
            if isinstance(predicates, list) and predicates:
                fact["candidate_predicates"] = predicates[:max_predicates]
            near = summary.get("near_miss_predicates")
            if isinstance(near, list) and near:
                fact["near_miss_predicates"] = near[:2]
        else:
            text = str(payload.get("output_summary") or "").strip()
            if text:
                fact["output_summary"] = text[:900]
        facts.append({k: v for k, v in fact.items() if v not in ("", None, [], {})})
    if not facts:
        return ""
    return (
        "CARRIED RECEIPT FACTS (compressed; not receipt objects to copy):\n"
        + json.dumps(facts, sort_keys=True, separators=(",", ":"), default=str)
        + "\n\n"
    )


def _parse_jsonish(value: object) -> object | None:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return json.loads(value, strict=False)
    except json.JSONDecodeError:
        return None


def _outstanding_obligation_context_for_retry(
    project_dir: str | Path | None,
    *,
    max_cards: int = 4,
    action_request_already_executed: bool = False,
    suppress_action_request_skeleton: bool = False,
) -> str:
    """Return compact obligations that must survive every same-iter retry.

    R1 fixes are local compiler/contract repairs. They must not erase other
    open control obligations from the payload while fixing the latest error.
    This function is a substrate adapter surface: today it harvests Strategy
    Office cards from the standard ledger, and future substrates can add their
    own typed obligation rows here without changing the retry loop.
    """
    if project_dir is None:
        return ""
    project = Path(project_dir)
    try:
        from ztare.common.operator_proposal_contract import open_cards

        cards = open_cards(project / "workspace" / "strategy_experiments.jsonl")
    except Exception:
        cards = []
    if not cards:
        return ""
    skill_cards = [card for card in cards if strategy_card_blocks_context(card)]
    meta_cards = [card for card in cards if strategy_card_role(card).lane == META_HARDENING_LANE]
    lines = [
        "OPEN STRATEGY CARD REFS:",
        "- Skill-acquisition cards are active evidence refs and gateable obligations.",
        "- Meta-hardening cards are queued apparatus work; do not let them block an executable candidate unless this task is explicitly meta-hardening.",
        "- If the retry is a control move, discharge/block each listed skill-acquisition card with STRATEGY_CARD_DISCHARGE.",
        "- If the retry submits executable code, cite the relevant card refs in thesis_markdown; gates still decide.",
    ]
    for card in skill_cards[:max_cards]:
        if not isinstance(card, dict):
            continue
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
        residue = plan.get("residue_quotient") if isinstance(plan.get("residue_quotient"), dict) else {}
        seed = plan.get("seed_prerequisite") if isinstance(plan.get("seed_prerequisite"), dict) else {}
        sha = str(card.get("failure_family_sha") or "").strip()
        kind = str(card.get("kind") or "").strip()
        no_attempt = admissible_no_attempt_blocker_kinds(card)
        lines.append(
            "- "
            + json.dumps(
                {
                    "failure_family_sha": sha,
                    "kind": kind,
                    "lane": SKILL_ACQUISITION_LANE,
                    "residue": residue.get("residue_class") or "",
                    "seed": seed.get("seed_path") or seed.get("status") or "",
                    "next_gate": {
                        "command": gate.get("command") or "",
                        "success_status": gate.get("success_status") or "",
                    },
                    "admissible_no_attempt_blockers": no_attempt,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        if (
            sha
            and gate.get("command")
            and not action_request_already_executed
            and not suppress_action_request_skeleton
        ):
            request = leaf_workbench_action_request_object(
                capability_id="run_strategy_required_gate",
                input_refs={
                    "failure_family_sha": sha,
                    "command": gate.get("command"),
                    "candidate_path": "test_model.py",
                },
                claim_bindings=[f"run required Strategy gate {gate.get('command')}"],
            )
            lines.append(
                "- optional action_request skeleton when the declared gate is the next "
                "needed discriminator: "
                + json.dumps(request, sort_keys=True, separators=(",", ":"), default=str)
            )
    if meta_cards:
        lines.append("- queued_meta_hardening_cards:")
        for card in meta_cards[: max(1, max_cards - len(skill_cards[:max_cards]))]:
            if not isinstance(card, dict):
                continue
            plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
            gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
            lines.append(
                "- "
                + json.dumps(
                    {
                        "failure_family_sha": str(card.get("failure_family_sha") or "").strip(),
                        "kind": str(card.get("kind") or "").strip(),
                        "lane": META_HARDENING_LANE,
                        "target_artifact": plan.get("target_artifact") or "",
                        "next_gate": {
                            "command": gate.get("command") or "",
                            "success_status": gate.get("success_status") or "",
                        },
                        "candidate_blocking": False,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
    return "\n".join(lines) + "\n\n"


def _compact_worldmodel_r1_error(text: str, *, limit: int = 900) -> str:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return ""
    receipt_idx = cleaned.find("LEAF_WORKBENCH_RECEIPT:")
    if receipt_idx >= 0:
        cleaned = cleaned[:receipt_idx].rstrip() + " [receipt objects elided; use compact receipt facts/artifact refs below]"
    if len(cleaned) > limit:
        cleaned = cleaned[:limit].rstrip() + "..."
    return cleaned


def _compact_worldmodel_prior_submission(text: str, *, max_code_chars: int = 6000) -> str:
    raw = str(text or "").strip()
    if not raw:
        return "<empty prior submission>"
    try:
        payload = json.loads(raw)
    except Exception:
        payload = None
    if isinstance(payload, dict):
        code = ""
        for key in ("test_model_py", "python_code", "code", "source"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                code = value
                break
        thesis = payload.get("thesis_markdown")
        receipts = payload.get("control_receipts")
        lines = [
            "prior_payload_summary:",
            f"- control_receipts_count: {len(receipts) if isinstance(receipts, list) else 0}",
        ]
        if isinstance(thesis, str) and thesis.strip():
            excerpt = " ".join(thesis.split())[:1000]
            lines.append(f"- thesis_excerpt: {excerpt}")
        if code.strip():
            lines.append("- test_model_py_excerpt:")
            lines.append("```python")
            lines.append(code[:max_code_chars])
            lines.append("```")
        else:
            lines.append("- test_model_py_excerpt: <empty>")
        return "\n".join(lines)
    if len(raw) > max_code_chars:
        return raw[:max_code_chars].rstrip() + "\n...[prior submission elided]"
    return raw


def format_worldmodel_retry_skeleton(
    r1_error: str,
    prior_content: str,
    *,
    max_prior_chars: int,
    retry_error_history: list[str] | None = None,
    project_dir: str | Path | None = None,
) -> str:
    retry_state_text = "\n".join(
        [str(r1_error or "")]
        + [str(row or "") for row in (retry_error_history or [])]
    )
    action_request_already_executed = (
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed" in retry_state_text
    )
    current_candidate_bound_capability = _candidate_bound_capability_from_r1_error(
        r1_error or ""
    )
    current_requests_counterexample_context = (
        "`inspect_worldmodel_counterexample_context`" in (r1_error or "")
    )
    current_requests_visible_probe = "`run_visible_json_probe`" in (r1_error or "")
    current_requests_feature_miner = (
        "`mine_worldmodel_separating_features`" in (r1_error or "")
    )
    named_current_morphism = (
        current_candidate_bound_capability
        or ("inspect_worldmodel_counterexample_context" if current_requests_counterexample_context else "")
        or ("run_visible_json_probe" if current_requests_visible_probe else "")
        or ("mine_worldmodel_separating_features" if current_requests_feature_miner else "")
    )
    initial_next_morphism: ControlMorphism | None = None
    if not action_request_already_executed and not current_candidate_bound_capability:
        initial_next_morphism = _latest_workbench_task_morphism(
            project_dir,
            executed_caps=[],
        )
        if not named_current_morphism and initial_next_morphism is not None:
            named_current_morphism = initial_next_morphism.capability_id
    candidate_binding_refresh = (
        "predates content-addressed candidate binding" in (r1_error or "")
    )
    no_delta_no_improvement = _is_no_delta_patch_base_no_improvement(r1_error or "")
    patch_base_context = (
        _patch_base_context_for_retry(project_dir)
        if (
            not no_delta_no_improvement
            and (
                "PATCH_BASE_REGRESSION_PRECHECK" in (r1_error or "")
                or "PATCH_BASE_IMPROVEMENT_PRECHECK" in (r1_error or "")
            )
        )
        else ""
    )
    counterexample_context = (
        _counterexample_context_for_retry(project_dir)
        if (
            "PATCH_BASE_IMPROVEMENT_PRECHECK" in (r1_error or "")
            and not no_delta_no_improvement
        )
        else ""
    )
    obligation_context = _outstanding_obligation_context_for_retry(
        project_dir,
        action_request_already_executed=action_request_already_executed,
        suppress_action_request_skeleton=(
            bool(named_current_morphism)
            and named_current_morphism != "run_strategy_required_gate"
        ),
    )
    action_request_section = ""
    executed_caps: list[str] = []
    input_rebind_caps: set[str] = set()
    candidate_delta_lowerability: bool | None = None
    suppress_candidate_carrier_surface = False
    if action_request_already_executed:
        ready_receipts = _ready_receipts_json_for_retry(
            retry_state_text,
            exclude_candidate_bound_capability=(
                current_candidate_bound_capability
                if candidate_binding_refresh
                else ""
            ),
        )
        ready_receipt_facts_section = _ready_receipt_facts_for_retry(
            retry_state_text,
            exclude_candidate_bound_capability=(
                current_candidate_bound_capability
                if candidate_binding_refresh
                else ""
            ),
        )
        executed_caps = executed_morphism_ids_from_receipts(retry_state_text)
        if _workbench_inputs_changed_since_receipt(
            project_dir,
            retry_state_text,
            capability_id="run_visible_json_probe",
            artifact_refs=["workspace/latest_patch_base_regression.json"],
        ):
            input_rebind_caps.add("run_visible_json_probe")
        if _workbench_inputs_changed_since_receipt(
            project_dir,
            retry_state_text,
            capability_id="mine_worldmodel_separating_features",
            artifact_refs=["workspace/latest_patch_base_regression.json"],
        ):
            input_rebind_caps.add("mine_worldmodel_separating_features")
        if _workbench_inputs_changed_since_receipt(
            project_dir,
            retry_state_text,
            capability_id="mine_worldmodel_lowerable_selectors",
            artifact_refs=["workspace/latest_patch_base_regression.json"],
        ):
            input_rebind_caps.add("mine_worldmodel_lowerable_selectors")
        if _workbench_inputs_changed_since_receipt(
            project_dir,
            retry_state_text,
            capability_id="mine_worldmodel_global_carrier_selectors_from_observable_context",
            artifact_refs=["workspace/latest_level_transfer_probe.json"],
        ):
            input_rebind_caps.add("mine_worldmodel_global_carrier_selectors_from_observable_context")
        if _workbench_inputs_changed_since_receipt(
            project_dir,
            retry_state_text,
            capability_id="cell_local_lowerable_carrier_selector_miner",
            artifact_refs=["workspace/latest_level_transfer_probe.json"],
        ):
            input_rebind_caps.add("cell_local_lowerable_carrier_selector_miner")
        candidate_delta_lowerability = boundary_cegar_candidate_delta_lowerability(
            ready_receipts
        )
        needs_lowerable_selector = (
            candidate_delta_lowerability is False
            and "mine_worldmodel_separating_features" in executed_caps
            and (
                "mine_worldmodel_lowerable_selectors" not in executed_caps
                or "mine_worldmodel_lowerable_selectors" in input_rebind_caps
            )
        )
        needs_feature_miner = (
            candidate_delta_lowerability is False
            and "inspect_worldmodel_counterexample_context" in executed_caps
            and "mine_worldmodel_separating_features" not in executed_caps
        )
        needs_cell_local_selector = (
            candidate_delta_lowerability is False
            and "mine_worldmodel_global_carrier_selectors_from_observable_context" in executed_caps
            and (
                "cell_local_lowerable_carrier_selector_miner" not in executed_caps
                or "cell_local_lowerable_carrier_selector_miner" in input_rebind_caps
            )
        )
        if current_candidate_bound_capability:
            action_request_section = render_boundary_cegar_retry_surface(
                state="candidate_binding_open",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    _candidate_bound_retry_morphism(current_candidate_bound_capability)
                ],
            )
        elif (
            current_requests_counterexample_context
            and "inspect_worldmodel_counterexample_context" not in executed_caps
        ):
            action_request_section = render_boundary_cegar_retry_surface(
                state="counterexample_open",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    ControlMorphism(
                        capability_id="inspect_worldmodel_counterexample_context",
                        input_refs=_workbench_input_refs_for_capability(
                            "inspect_worldmodel_counterexample_context",
                            [],
                            project_dir=project_dir,
                        ),
                        claim_bindings=["separate latest counterexample quotient by typed context"],
                    )
                ],
            )
        elif needs_feature_miner:
            action_request_section = render_boundary_cegar_retry_surface(
                state="observation_receipt_available",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    ControlMorphism(
                        capability_id="mine_worldmodel_separating_features",
                        input_refs=_workbench_input_refs_for_capability(
                            "mine_worldmodel_separating_features",
                            ["workspace/latest_patch_base_regression.json"],
                            project_dir=project_dir,
                        ),
                        claim_bindings=[
                            "mine visible alpha features after context-only receipt",
                        ],
                    )
                ],
            )
        elif current_requests_feature_miner and (
            "mine_worldmodel_separating_features" not in executed_caps
            or "mine_worldmodel_separating_features" in input_rebind_caps
        ):
            action_request_section = render_boundary_cegar_retry_surface(
                state="counterexample_open",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    ControlMorphism(
                        capability_id="mine_worldmodel_separating_features",
                        input_refs=_workbench_input_refs_for_capability(
                            "mine_worldmodel_separating_features",
                            ["workspace/latest_patch_base_regression.json"],
                            project_dir=project_dir,
                        ),
                        claim_bindings=["mine visible alpha features for latest counterexample"],
                    )
                ],
            )
        elif needs_lowerable_selector:
            action_request_section = render_boundary_cegar_retry_surface(
                state="observation_receipt_available",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    ControlMorphism(
                        capability_id="mine_worldmodel_lowerable_selectors",
                        input_refs=_workbench_input_refs_for_capability(
                            "mine_worldmodel_lowerable_selectors",
                            ["workspace/latest_patch_base_regression.json"],
                            project_dir=project_dir,
                        ),
                        claim_bindings=[
                            "try to lower the chart-only counterexample separator into a visible carrier selector",
                        ],
                    )
                ],
            )
        elif needs_cell_local_selector:
            action_request_section = render_boundary_cegar_retry_surface(
                state="observation_receipt_available",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    ControlMorphism(
                        capability_id="cell_local_lowerable_carrier_selector_miner",
                        input_refs={
                            "strategy_gate_receipt_ref": "workspace/latest_level_transfer_probe.json",
                        },
                        claim_bindings=[
                            "refine the no-lowerable selector receipt with per-cell component topology",
                        ],
                    )
                ],
            )
        elif (
            candidate_delta_lowerability is False
            and (
                "mine_worldmodel_lowerable_selectors" in executed_caps
                or "cell_local_lowerable_carrier_selector_miner" in executed_caps
            )
        ):
            action_request_section = render_boundary_cegar_retry_surface(
                state="observation_receipt_available",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=None,
            )
        elif candidate_delta_lowerability is True:
            action_request_section = render_boundary_cegar_retry_surface(
                state="observation_receipt_available",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=None,
                no_next_morphism_policy=(
                    "submit a candidate delta that cites the lowerability "
                    "receipt, or block/refute the card with a typed reason."
                ),
            )
        elif current_requests_visible_probe and (
            "run_visible_json_probe" not in executed_caps
            or "run_visible_json_probe" in input_rebind_caps
        ):
            action_request_section = render_boundary_cegar_retry_surface(
                state="counterexample_open",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    ControlMorphism(
                        capability_id="run_visible_json_probe",
                        input_refs={
                            "artifact_refs": ["workspace/latest_patch_base_regression.json"],
                        },
                        claim_bindings=["separate latest counterexample quotient"],
                    )
                ],
            )
        else:
            next_morphism = _latest_workbench_task_morphism(
                project_dir,
                executed_caps=executed_caps,
                allow_candidate_rebind=candidate_binding_refresh,
                allow_input_rebind_caps=input_rebind_caps,
            )
            next_morphism = (
                _open_strategy_receipt_morphism(
                    project_dir,
                    executed_caps=executed_caps,
                    allow_input_rebind_caps=input_rebind_caps,
                )
                or next_morphism
            )
            action_request_section = render_boundary_cegar_retry_surface(
                state=(
                    "counterexample_open"
                    if candidate_binding_refresh or input_rebind_caps
                    else ("observation_receipt_available" if executed_caps else "counterexample_open")
                ),
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[next_morphism] if next_morphism is not None else None,
            )
    else:
        ready_receipt_facts_section = ""
        next_morphism = (
            _candidate_bound_retry_morphism(current_candidate_bound_capability)
            if current_candidate_bound_capability
            else (
                _open_strategy_receipt_morphism(project_dir, executed_caps=[])
                or initial_next_morphism
            )
        )
        action_request_section = render_leaf_workbench_control_rules(
            action_request=(
                next_morphism.request_object() if next_morphism is not None else None
            )
        ) + "\n\n"
        if next_morphism is not None:
            action_request_section += render_boundary_cegar_retry_surface(
                state="counterexample_open",
                executed_morphisms=[],
                admissible_next=[next_morphism],
            )
        else:
            action_request_section += (
                "Submit `control_receipts: []` when no workbench action is needed.\n\n"
            )
    if suppress_candidate_carrier_surface:
        patch_base_context = ""
    carrier_guidance_section = (
        "Current receipts do not yet expose a lowerability witness. If visible "
        "evidence still lets you express a transportable law, submit the candidate "
        "and let the gate decide. Otherwise submit LOWERABILITY_BLOCKED with "
        "attempted tools, candidate family, evidence refs, and evidence_statuses. "
        + SCIENCE_OUTPUT_POLICY.tool_gap_text()
        + "\n\n"
        if candidate_delta_lowerability is False
        else (
            "A typed observation is available as a useful option, but it does not "
            "forbid candidate code. Submit an executable carrier when visible "
            "evidence permits; otherwise request the registered observation or "
            "submit LOWERABILITY_BLOCKED.\n\n"
            if suppress_candidate_carrier_surface
            else (
                "If this retry submits a candidate delta, choose the narrowest carrier "
                "that expresses your law:\n"
                "  - Direct executable carrier: define `step(grid, action, t)`, "
                "`PROGRAM = ...`, or another accepted predictor surface.\n"
                "  - Patch-base carrier only when an authoritative patch_base_ref "
                "and full patch_base_sha are shown in this prompt; never invent "
                f"base identity: {patch_carrier_brief_line()}\n"
                "  - Catalog spec only if lowerable: `WORLD_MODEL_SPEC = {\"actions\":{\"0\":[{\"op\":\"identity\"}]}}`\n"
                "  - Sealed grid_dsl AST: `PROGRAM = [...]`\n"
                "Do not include identity fallback code for a control-only move.\n\n"
            )
        )
    )
    control_rules_section = (
        render_leaf_workbench_control_rules()
        + "\n"
        if action_request_already_executed
        else ""
    )
    body = (
        "This substrate is evaluated by deterministic grid replay and held-out "
        "rollout. Thesis prose and assertion tests are advisory only. Candidate "
        "submissions need an executable transition carrier. Omit carrier code "
        "only for a registered workbench action request that can add runtime "
        "information or `LOWERABILITY_BLOCKED` carrying evidence that no "
        "gamma-lowerable candidate is currently justified. "
        + SCIENCE_OUTPUT_POLICY.blocker_text()
        + "\n\n"
        f"{SCIENCE_OUTPUT_POLICY.final_contract_text()}\n"
        "Put new Strategy discharges, workbench action requests, tool-gap "
        "observations, or LOWERABILITY_BLOCKED in `control_receipts`. "
        "Kernel-produced observation receipts are not authored by the model; when "
        "compact receipt facts are shown, cite their refs/facts instead of pasting "
        "summaries as new receipts.\n\n"
        f"{render_retry_pack_lines(
            receipts_text=retry_state_text,
            candidate_memory_refs=candidate_memory_refs_for_retry(project_dir) if project_dir else (),
            heading='CARRIED RECEIPT FACTS',
        )}"
        f"{control_rules_section}"
        f"{action_request_section}"
        f"{ready_receipt_facts_section}"
        f"{carrier_guidance_section}"
        "Rules:\n"
        "  - do not put `control_receipts`, `LEAF_WORKBENCH_RECEIPT`, or "
        "`STRATEGY_CARD_DISCHARGE` inside `test_model_py`\n"
        "  - do not submit only qualitative tests; they cannot satisfy replay/rollout\n"
        "  - do not declare PARAMETRIC_FORM, LAGRANGIAN, MODEL_PARAMS, PARAMETER_NAMES, or INIT_RANGE\n"
        "  - keep imports stdlib-only and keep module import side-effect free\n"
        "  - if proposing a new operator, use EXTENSIONS_SRC plus a PROGRAM that calls it\n\n"
        f"{obligation_context}"
        f"{counterexample_context}"
        f"{patch_base_context}"
    )
    missing_block_note = ""
    try:
        from ztare.fit.mutation_suite_guard import is_missing_block_error as _imb
        if _imb(r1_error or ""):
            missing_block_note = (
                "VIOLATED REQUIREMENT (verbatim): \"Missing required Python "
                "falsification suite block; reject candidate before evaluation.\"\n"
                "Your response MUST carry the complete falsification suite as "
                "runnable Python: either a non-empty `test_model_py` field in the "
                "JSON payload containing the FULL contents of test_model.py, or a "
                "fenced ```python code block with that full suite. Prose, receipts, "
                "or a suite left only in the workbench without either carrier does "
                "not satisfy the extractor.\n\n"
            )
    except Exception:
        pass
    return render_retry_contract_surface(
        RetryContractSurface(
            rejected_subject="ARC/world-model submission",
            scientific_failure_phrase=(
                "rejected by the R1 or pre-judge gate contract"
            ),
            error_text=_compact_worldmodel_r1_error(r1_error),
            error_history=format_retry_error_history(retry_error_history),
            body=missing_block_note + body,
            resubmit_instruction="RESUBMIT THE COMPLETE RAW JSON PAYLOAD.",
            prior_heading="Prior submission summary:",
            prior_content=_compact_worldmodel_prior_submission(
                prior_content,
                max_code_chars=min(max_prior_chars, 5000),
            ),
            prior_mode="summary",
        )
    )


def _ready_worldmodel_control_receipts_json(retry_state_text: str) -> str:
    return packed_control_receipts(retry_state_text)


def _executed_workbench_capabilities(retry_state_text: str) -> list[str]:
    return executed_morphism_ids_from_receipts(retry_state_text)


def _is_no_delta_patch_base_no_improvement(r1_error: str) -> bool:
    text = str(r1_error or "")
    return (
        "PATCH_BASE_IMPROVEMENT_PRECHECK" in text
        and "relation=no_strict_improvement" in text
        and "wrong_cells 0 vs 0" in text
        and "quotient_relation=unclassified" in text
        and "candidate_top={'bbox': []" in text
        and "best_prior_top={'bbox': []" in text
    )


def format_retry_error_history(errors: list[str] | None) -> str:
    if not errors:
        return ""
    cleaned: list[str] = []
    for raw in errors:
        text = " ".join(str(raw or "").split())
        if not text:
            continue
        if cleaned and cleaned[-1] == text:
            continue
        cleaned.append(text)
    if len(cleaned) <= 1:
        return ""
    lines = [
        "Same-iteration R1 strike history:",
    ]
    for idx, err in enumerate(cleaned[-3:], start=max(1, len(cleaned) - 2)):
        tail = _compact_worldmodel_r1_error(err, limit=260)
        lines.append(f"  {idx}. {tail}")
    lines.extend(
        [
            "",
            "The next submission must satisfy the current error without reintroducing",
            "any earlier strike in this list.",
            "",
        ]
    )
    return "\n".join(lines)
