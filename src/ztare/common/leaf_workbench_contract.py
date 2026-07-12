from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


SecretPolicy = Literal["public_only", "derived_no_raw_secret", "sealed_aggregate_only"]
Authority = Literal["reader", "pure_diagnostic", "bounded_world_probe", "scorer", "proposal_only"]


@dataclass(frozen=True)
class LeafWorkbenchCapability:
    """A bounded observation/action surface for an in-loop leaf worker."""

    capability_id: str
    purpose: str
    authority: Authority
    secret_policy: SecretPolicy
    input_contract: list[str]
    output_contract: list[str]
    version: str = "v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LeafWorkbenchContract:
    capabilities: tuple[LeafWorkbenchCapability, ...] = field(default_factory=tuple)
    schema: str = "ztare-leaf-workbench-contract-v1"

    def registry(self) -> dict[str, LeafWorkbenchCapability]:
        return {cap.capability_id: cap for cap in self.capabilities}

    def resolve_capability_ref(self, value: str) -> str:
        """Resolve either a bare ID or its canonical versioned reference."""

        raw = str(value).strip()
        for capability in self.capabilities:
            if raw in {
                capability.capability_id,
                f"{capability.capability_id}@{capability.version}",
            }:
                return capability.capability_id
        raise ValueError(f"unknown workbench capability reference: {raw!r}")

    def fingerprint(self) -> str:
        rows = [cap.to_dict() for cap in self.capabilities]
        blob = json.dumps(
            {"schema": self.schema, "capabilities": rows},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()


@dataclass(frozen=True)
class LeafWorkbenchRegistryParity:
    """Static check that a workbench contract has one execution registry."""

    missing_execution_surface: tuple[str, ...] = ()
    dangling_action_handlers: tuple[str, ...] = ()
    dangling_stateless_actions: tuple[str, ...] = ()
    dangling_record_only_capabilities: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not (
            self.missing_execution_surface
            or self.dangling_action_handlers
            or self.dangling_stateless_actions
            or self.dangling_record_only_capabilities
        )

    def raise_for_errors(self) -> None:
        if self.ok:
            return
        parts: list[str] = []
        if self.missing_execution_surface:
            parts.append(
                "missing_execution_surface="
                + ",".join(self.missing_execution_surface)
            )
        if self.dangling_action_handlers:
            parts.append("dangling_action_handlers=" + ",".join(self.dangling_action_handlers))
        if self.dangling_stateless_actions:
            parts.append("dangling_stateless_actions=" + ",".join(self.dangling_stateless_actions))
        if self.dangling_record_only_capabilities:
            parts.append(
                "dangling_record_only_capabilities="
                + ",".join(self.dangling_record_only_capabilities)
            )
        raise ValueError("leaf workbench registry parity failed: " + "; ".join(parts))


def validate_leaf_workbench_registry_parity(
    *,
    contract: LeafWorkbenchContract,
    action_handlers: Mapping[str, Any] | None = None,
    local_action_ids: Iterable[str] = (),
    record_only_capability_ids: Iterable[str] = (),
    stateless_action_ids: Iterable[str] = (),
) -> LeafWorkbenchRegistryParity:
    """Check that contract capabilities are projected through one registry door.

    A capability in the contract is either executable in-turn, executable by the
    parent kernel, or explicitly record-only. This catches the failure mode where
    a capability appears in worker context but cannot be invoked.
    """

    registry = set(contract.registry())
    handler_ids = set((action_handlers or {}).keys())
    local_ids = {str(item) for item in local_action_ids if str(item)}
    record_only_ids = {str(item) for item in record_only_capability_ids if str(item)}
    stateless_ids = {str(item) for item in stateless_action_ids if str(item)}
    executable_or_readable = handler_ids | local_ids | record_only_ids
    return LeafWorkbenchRegistryParity(
        missing_execution_surface=tuple(sorted(registry - executable_or_readable)),
        dangling_action_handlers=tuple(sorted(handler_ids - registry)),
        dangling_stateless_actions=tuple(sorted(stateless_ids - registry)),
        dangling_record_only_capabilities=tuple(sorted(record_only_ids - registry)),
    )


DEFAULT_LEAF_WORKBENCH_CONTRACT = LeafWorkbenchContract(
    capabilities=(
        LeafWorkbenchCapability(
            capability_id="inspect_authoritative_artifact",
            purpose="Read a named authoritative artifact or bounded excerpt already exposed to the worker.",
            authority="reader",
            secret_policy="public_only",
            input_contract=["artifact_ref", "artifact_sha256"],
            output_contract=["excerpt_ref_or_summary", "observed_schema_or_fields"],
        ),
        LeafWorkbenchCapability(
            capability_id="compute_residual_quotient",
            purpose="Collapse repeated failures into behaviorally equivalent residue classes.",
            authority="pure_diagnostic",
            secret_policy="derived_no_raw_secret",
            input_contract=["candidate_ref", "evidence_ref", "quotient_axis"],
            output_contract=["class_count", "class_summaries", "representative_refs"],
        ),
        LeafWorkbenchCapability(
            capability_id="run_deterministic_probe",
            purpose="Run a cheap deterministic diagnostic on frozen evidence without spending world actions.",
            authority="pure_diagnostic",
            secret_policy="derived_no_raw_secret",
            input_contract=["probe_id", "candidate_ref", "evidence_ref"],
            output_contract=["pass_fail_or_metric", "failure_mode", "artifact_ref"],
        ),
        LeafWorkbenchCapability(
            capability_id="run_visible_json_probe",
            purpose=(
                "Run bounded pure Python over explicitly named visible JSON artifacts; "
                "the program receives ARTIFACTS and must assign JSON-serializable RESULT."
            ),
            authority="pure_diagnostic",
            secret_policy="public_only",
            input_contract=["probe_py", "artifact_refs"],
            output_contract=["result_summary", "artifact_hashes", "probe_sha256"],
        ),
        LeafWorkbenchCapability(
            capability_id="validate_receipt_spine",
            purpose="Check that required governance receipts bind to the current card/spec hashes.",
            authority="pure_diagnostic",
            secret_policy="public_only",
            input_contract=["required_receipts_ref", "candidate_receipts_ref"],
            output_contract=["missing", "malformed", "matched"],
        ),
        LeafWorkbenchCapability(
            capability_id="check_receipt_compatibility",
            purpose=(
                "Check visible receipt or typed-payload shape before final submission; "
                "reports missing fields and repair hints without running truth gates."
            ),
            authority="pure_diagnostic",
            secret_policy="public_only",
            input_contract=["source_ref_or_stdin", "receipt_kind"],
            output_contract=["errors", "repair_hints", "normalized_summary"],
        ),
        LeafWorkbenchCapability(
            capability_id="score_candidate_delta",
            purpose="Compare candidate against incumbent on a declared frozen evaluator.",
            authority="scorer",
            secret_policy="sealed_aggregate_only",
            input_contract=["candidate_ref", "incumbent_ref", "evaluator_ref", "evaluator_sha256"],
            output_contract=["delta_summary", "regressions", "artifact_ref"],
        ),
    )
)


def render_leaf_workbench_contract_prompt(
    contract: LeafWorkbenchContract = DEFAULT_LEAF_WORKBENCH_CONTRACT,
) -> str:
    lines = [
        "LEAF WORKBENCH CONTRACT:",
        f"- schema: {contract.schema}",
        f"- contract_sha256: {contract.fingerprint()}",
        "- The Python carrier is sovereign: any law expressible in the carrier contract is in-bounds.",
        "- Registered tools are conveniences for a bounded carrier, not the boundary of the action space.",
        "- A workbench receipt may support a claim when `capability_id` is listed below.",
        "- If the needed capability is missing or defective, do not fake an action receipt.",
        "  In science mode, report the missing sensor/morphism inside `LOWERABILITY_BLOCKED`; "
        "capability proposals are optional meta evidence only.",
        "  Optional meta evidence uses `LEAF_WORKBENCH_CAPABILITY_PROPOSAL`; proposals are not evidence for a candidate and never satisfy the science turn by themselves.",
        "  Capability proposals should be morphism-shaped: current_state, desired_state, admissibility_witness.",
        "  If the proposal names an allowed mutable-sensor `target_artifact`, the kernel queues a `tool_synthesis` Strategy card.",
        "- To ask the kernel to run a registered capability, submit `LEAF_WORKBENCH_ACTION_REQUEST`.",
        "  The current candidate will not be evaluated; the kernel returns a receipt on a free retry.",
        "- `LEAF_WORKBENCH_RECEIPT` is a kernel output. Copy returned receipt objects unchanged; do not author them from prose.",
        "- Receipts must cite input hashes/refs and bind each claim they support.",
        "- Sealed or hidden data may appear only through declared aggregate outputs.",
        "- Structured exits remain available through the stopping contract: continue(query, mode=None), commit(candidate), stuck(diagnosis, friction).",
        "- Optional continue modes: repair, re_represent, analogy_query.",
        "- Available capabilities:",
    ]
    for cap in contract.capabilities:
        lines.append(
            f"  - {cap.capability_id}@{cap.version}: authority={cap.authority}; "
            f"secret_policy={cap.secret_policy}; inputs={','.join(cap.input_contract)}; "
            f"outputs={','.join(cap.output_contract)}; purpose={cap.purpose}"
        )
    return "\n".join(lines)


def leaf_workbench_action_request_object(
    *,
    capability_id: str,
    input_refs: dict[str, Any] | None = None,
    claim_bindings: list[str] | None = None,
    required_input_refs: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the canonical typed action-request object shown to workers."""

    payload: dict[str, Any] = {
        "capability_id": capability_id,
        "input_refs": input_refs or {},
        "claim_bindings": claim_bindings or [capability_id],
    }
    if required_input_refs:
        payload["required_input_refs"] = required_input_refs
    return {"type": "LEAF_WORKBENCH_ACTION_REQUEST", "payload": payload}


def leaf_workbench_capability_proposal_object() -> dict[str, Any]:
    """Return the canonical proposal skeleton for missing workbench actions."""

    return {
        "type": "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
        "payload": {
            "proposed_capability_id": "<new_capability_id>",
            "gap_statement": "<what observation/action the current contract cannot express>",
            "input_contract": {"required_fields": ["<field>"]},
            "output_contract": {"required_fields": ["<field>"]},
            "evaluator": {"type": "deterministic_probe"},
            "current_state": "<current boundary state>",
            "desired_state": "<new observable state>",
            "admissibility_witness": "<fixture or receipt proving the tool is needed>",
            "secret_policy": {"policy": "public_only"},
            "safety_invariant": "<what this tool may not weaken>",
            "rollback_condition": "<when to discard this tool>",
            "target_artifact": "<optional mutable-sensor path>",
        },
    }


def render_leaf_workbench_capability_proposal_shape() -> str:
    return (
        "- capability-proposal shape: "
        + json.dumps(
            leaf_workbench_capability_proposal_object(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        + ". This queues future tool work only; it is not evidence for the current candidate."
    )


def render_leaf_workbench_control_rules(
    *,
    action_request: dict[str, Any] | None = None,
    include_capability_proposal_rule: bool = True,
) -> str:
    """Render the shared prompt boundary for action requests and receipts.

    Keep this as the single textual source for workbench receipt semantics.
    Substrates may pass a concrete action request, but they should not render
    their own receipt examples.
    """

    lines = [
        "LEAF WORKBENCH CONTROL RULES:",
        "- `LEAF_WORKBENCH_RECEIPT` is produced by the kernel executor only.",
        "- Do not author or recreate workbench receipts; cite kernel receipt refs/facts when writing a candidate.",
        "- If no receipt exists for a needed observation, submit `LEAF_WORKBENCH_ACTION_REQUEST` instead of authoring a receipt.",
        "- Structured exits remain available through the stopping contract: continue(query, mode=None), commit(candidate), stuck(diagnosis, friction).",
    ]
    if action_request is not None:
        lines.append(
            "- admissible action-request object: "
            + json.dumps(action_request, sort_keys=True, separators=(",", ":"), default=str)
        )
    if include_capability_proposal_rule:
        lines.append(
            "- If no registered action can expose the needed distinction in science mode, "
            "report the missing sensor/morphism inside `LOWERABILITY_BLOCKED`. A "
            "`LEAF_WORKBENCH_CAPABILITY_PROPOSAL` may be attached as optional meta "
            "evidence only; it is not current-candidate evidence."
        )
    return "\n".join(lines)


def render_leaf_workbench_mutator_surface(
    *,
    query_rounds_left: int,
    query_menu: str,
    query_menu_json: str,
    scratchpad_text: str,
    investigated_rounds_left: int | None = None,
) -> str:
    from ztare.common.science_output_policy import SCIENCE_OUTPUT_POLICY

    lines = [
        "LEAF MUTATOR SURFACE:",
        "- The Python carrier is sovereign: if the carrier contract can say it, the surface may do it.",
        "- Registered tools are conveniences, not the limits of the action space.",
        "- Structured exits remain available through the stopping contract:",
        "  continue(query, mode=None), commit(candidate), stuck(diagnosis, friction).",
        "- Optional continue modes: repair, re_represent, analogy_query.",
        f"- Remaining query budget: {query_rounds_left}",
        # Salience: the leaf is REWARDED for INVESTIGATED, so it must see the
        # option and its remaining budget the way carrier strikes are surfaced.
        "- INVESTIGATED is a first-class positive close: " + SCIENCE_OUTPUT_POLICY.investigated_text(),
    ]
    if investigated_rounds_left is not None:
        lines.append(
            f"- Remaining investigated-only budget before a carrier is expected: "
            f"{investigated_rounds_left}"
        )
    return "\n".join(
        lines
        + [
            "- The leaf-owned scratchpad is re-fed verbatim below and must be carried forward unchanged unless the leaf explicitly updates it.",
            "- Bounded query menu:",
            query_menu,
            "- Query menu JSON:",
            query_menu_json,
            "- Scratchpad, verbatim:",
            scratchpad_text,
        ]
    )


def validate_leaf_workbench_receipt(
    payload: object,
    contract: LeafWorkbenchContract = DEFAULT_LEAF_WORKBENCH_CONTRACT,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("LEAF_WORKBENCH_RECEIPT requires object `payload`.")
    payload = _normalize_leaf_workbench_receipt_payload(payload)
    capability_id = str(payload.get("capability_id") or "").strip()
    if not capability_id:
        raise ValueError("LEAF_WORKBENCH_RECEIPT requires `capability_id`.")
    registry = contract.registry()
    version_suffix = ""
    if capability_id not in registry and "@" in capability_id:
        base_id, suffix = capability_id.rsplit("@", 1)
        cap = registry.get(base_id)
        if cap is not None and suffix == cap.version:
            capability_id = base_id
            version_suffix = suffix
    if capability_id not in registry:
        raise ValueError(
            "LEAF_WORKBENCH_RECEIPT references unknown capability_id "
            f"{capability_id!r}. Use a registered capability; in science mode, "
            "report missing tools inside LOWERABILITY_BLOCKED."
        )
    if payload.get("contract_sha256") not in {contract.fingerprint(), None}:
        raise ValueError("LEAF_WORKBENCH_RECEIPT contract_sha256 does not match active contract.")
    input_hashes = payload.get("input_hashes")
    if not isinstance(input_hashes, dict) or not input_hashes:
        raise ValueError("LEAF_WORKBENCH_RECEIPT requires non-empty `input_hashes` object.")
    claim_bindings = payload.get("claim_bindings")
    if not isinstance(claim_bindings, list) or not claim_bindings:
        raise ValueError("LEAF_WORKBENCH_RECEIPT requires non-empty `claim_bindings` list.")
    output_ref = str(payload.get("output_ref") or "").strip()
    output_summary = str(payload.get("output_summary") or "").strip()
    if not output_ref and not output_summary:
        raise ValueError("LEAF_WORKBENCH_RECEIPT requires `output_ref` or `output_summary`.")
    normalized = dict(payload)
    normalized["capability_id"] = capability_id
    if version_suffix:
        normalized.setdefault("capability_version", version_suffix)
    normalized.setdefault("contract_sha256", contract.fingerprint())
    return normalized


def _normalize_leaf_workbench_receipt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "capability_id" not in normalized:
        for key in ("capability", "capability_name", "tool_id"):
            if _non_empty_contract_value(normalized.get(key)):
                normalized["capability_id"] = normalized.get(key)
                break
    if "input_hashes" not in normalized:
        for key in ("input_refs", "input_artifacts", "inputs", "provenance"):
            value = normalized.get(key)
            if isinstance(value, dict) and value:
                normalized["input_hashes"] = value
                break
    if "claim_bindings" not in normalized:
        for key in ("claims", "claim_binding", "supports", "supported_claims"):
            value = normalized.get(key)
            if isinstance(value, str) and value.strip():
                normalized["claim_bindings"] = [value]
                break
            if isinstance(value, (list, tuple)) and value:
                normalized["claim_bindings"] = list(value)
                break
    if "output_ref" not in normalized:
        for key in ("artifact_ref", "result_ref", "receipt_ref"):
            if _non_empty_contract_value(normalized.get(key)):
                normalized["output_ref"] = normalized.get(key)
                break
    if "output_summary" not in normalized:
        for key in ("result_summary", "summary", "output", "result"):
            value = normalized.get(key)
            if isinstance(value, str) and value.strip():
                normalized["output_summary"] = value
                break
            if isinstance(value, (dict, list, tuple)) and value:
                normalized["output_summary"] = json.dumps(value, sort_keys=True, default=str)
                break
    return normalized


def _non_empty_contract_value(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return False


def _normalize_secret_policy(value: object) -> str:
    if isinstance(value, dict):
        policy = str(value.get("policy") or "").strip()
        if policy in {"public_only", "derived_no_raw_secret", "sealed_aggregate_only"}:
            return policy
        allowed_blob = json.dumps(
            value.get("allowed_data")
            or value.get("allowed_inputs")
            or value.get("allowed_sources")
            or value.get("allowed")
            or "",
            sort_keys=True,
            default=str,
        ).lower()
        forbidden_blob = json.dumps(
            value.get("forbidden_data")
            or value.get("forbidden_inputs")
            or value.get("disallowed_sources")
            or value.get("forbidden_sources")
            or value.get("forbidden")
            or "",
            sort_keys=True,
            default=str,
        ).lower()
        if "aggregate" in allowed_blob and ("sealed" in allowed_blob or "hidden" in allowed_blob):
            return "sealed_aggregate_only"
        hidden_terms = ("secret", "hidden", "holdout", "sealed", "private evaluator")
        if forbidden_blob and any(term in forbidden_blob for term in hidden_terms):
            return "public_only"
        if value.get("uses_secret_data") is False:
            return "public_only"
        secret_flags = [
            flag
            for key, flag in value.items()
            if str(key).startswith("uses_secret")
        ]
        if secret_flags and all(flag is False for flag in secret_flags):
            return "public_only"
        value = policy
    policy = str(value or "").strip()
    if policy in {"public_only", "derived_no_raw_secret", "sealed_aggregate_only"}:
        return policy
    lower = policy.lower().replace("_", " ").replace("-", " ")
    if (
        ("derived" in lower and "raw" in lower and "secret" in lower)
        or ("aggregate" in lower and ("sealed" in lower or "hidden" in lower))
    ):
        return "sealed_aggregate_only" if "aggregate" in lower else "derived_no_raw_secret"
    secret_denial_terms = ("no ", "without ", "none", "never ")
    secret_terms = ("secret", "hidden", "holdout", "external files", "external data")
    public_terms = (
        "public",
        "visible",
        "workspace artifacts",
        "kernel receipts",
        "gate-reported",
        "declared inputs",
    )
    has_public_scope = any(term in lower for term in public_terms)
    has_secret_scope = any(term in lower for term in secret_terms)
    if has_public_scope and "only" in lower and not has_secret_scope:
        return "public_only"
    if has_public_scope and has_secret_scope and any(term in lower for term in secret_denial_terms):
        return "public_only"
    return policy


def validate_leaf_workbench_capability_proposal(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("LEAF_WORKBENCH_CAPABILITY_PROPOSAL requires object `payload`.")
    payload = _normalize_capability_proposal_payload(payload)
    required = [
        "proposed_capability_id",
        "gap_statement",
        "input_contract",
        "output_contract",
        "evaluator",
        "secret_policy",
        "safety_invariant",
        "rollback_condition",
    ]
    missing = [key for key in required if not _non_empty_contract_value(payload.get(key))]
    if missing:
        raise ValueError(
            "LEAF_WORKBENCH_CAPABILITY_PROPOSAL missing required fields: "
            + ", ".join(missing)
        )
    normalized = dict(payload)
    normalized["secret_policy"] = _normalize_secret_policy(payload.get("secret_policy"))
    if normalized["secret_policy"] not in {"public_only", "derived_no_raw_secret", "sealed_aggregate_only"}:
        raise ValueError("LEAF_WORKBENCH_CAPABILITY_PROPOSAL has invalid secret_policy.")
    normalized.setdefault("current_state", str(payload.get("gap_statement") or "capability absent"))
    normalized.setdefault("desired_state", str(payload.get("output_contract") or "declared capability output"))
    normalized.setdefault("admissibility_witness", str(payload.get("evaluator") or "deterministic evaluator"))
    for morphism_key in ("current_state", "desired_state", "admissibility_witness"):
        if not _non_empty_contract_value(normalized.get(morphism_key)):
            raise ValueError(
                "LEAF_WORKBENCH_CAPABILITY_PROPOSAL missing morphism field: "
                + morphism_key
            )
    return normalized


def _normalize_capability_proposal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize unambiguous proposal aliases before validation.

    Proposal receipts are second-order: they queue missing instruments; they do
    not certify an object-level candidate. The boundary should therefore be
    strict about semantic slots, but tolerant of a leaf placing those slots under
    common morphism names such as capability_id/motivation/required_inputs.
    """

    normalized = dict(payload)
    nested = normalized.get("proposal")
    nested_proposal = nested if isinstance(nested, dict) else {}
    if "proposed_capability_id" not in normalized:
        for key in ("proposed_capability_id", "requested_capability", "capability_id"):
            if _non_empty_contract_value(nested_proposal.get(key)):
                normalized["proposed_capability_id"] = nested_proposal.get(key)
                break
    if "proposed_capability_id" not in normalized and normalized.get("capability_id"):
        normalized["proposed_capability_id"] = normalized.get("capability_id")
    if "gap_statement" not in normalized:
        for key in (
            "gap",
            "motivation",
            "need",
            "needed_observation",
            "problem_statement",
            "purpose",
            "reason",
        ):
            if _non_empty_contract_value(normalized.get(key)):
                normalized["gap_statement"] = normalized.get(key)
                break
    if "gap_statement" not in normalized:
        for key in ("gap_statement", "purpose", "success_condition", "reason"):
            if _non_empty_contract_value(nested_proposal.get(key)):
                normalized["gap_statement"] = nested_proposal.get(key)
                break
    if "gap_statement" not in normalized and _non_empty_contract_value(normalized.get("blocked_by")):
        normalized["gap_statement"] = (
            "blocked_by: " + json.dumps(normalized.get("blocked_by"), sort_keys=True, default=str)
        )
    if "gap_statement" not in normalized and _non_empty_contract_value(normalized.get("claim_bindings")):
        bindings = normalized.get("claim_bindings")
        if isinstance(bindings, (list, tuple)):
            normalized["gap_statement"] = "; ".join(str(item) for item in bindings if str(item).strip())
        else:
            normalized["gap_statement"] = str(bindings)
    if "input_contract" not in normalized:
        for key in ("required_inputs", "inputs", "input_schema"):
            if _non_empty_contract_value(normalized.get(key)):
                normalized["input_contract"] = normalized.get(key)
                break
    if "input_contract" not in normalized:
        for key in ("input_contract", "required_inputs", "inputs", "input_schema"):
            if _non_empty_contract_value(nested_proposal.get(key)):
                normalized["input_contract"] = nested_proposal.get(key)
                break
    if "output_contract" not in normalized:
        for key in ("required_outputs", "outputs", "output_schema", "required_output_schema"):
            if _non_empty_contract_value(normalized.get(key)):
                normalized["output_contract"] = normalized.get(key)
                break
    if "output_contract" not in normalized:
        for key in (
            "output_contract",
            "required_outputs",
            "outputs",
            "output_schema",
            "required_output_schema",
            "desired_output_schema",
        ):
            if _non_empty_contract_value(nested_proposal.get(key)):
                normalized["output_contract"] = nested_proposal.get(key)
                break
    if "input_contract" not in normalized and _non_empty_contract_value(normalized.get("claim_bindings")):
        normalized["input_contract"] = {
            "required_fields": ["declared_visible_input_refs"],
            "source": "proposal claim_bindings",
        }
    if "output_contract" not in normalized and _non_empty_contract_value(normalized.get("claim_bindings")):
        normalized["output_contract"] = {
            "required_fields": ["typed_receipt"],
            "source": "proposal claim_bindings",
        }
    if "evaluator" not in normalized:
        if _non_empty_contract_value(normalized.get("admissibility_witness")):
            normalized["evaluator"] = normalized.get("admissibility_witness")
        elif _non_empty_contract_value(nested_proposal.get("success_condition")):
            normalized["evaluator"] = {
                "type": "deterministic_receipt_probe",
                "pass_condition": nested_proposal.get("success_condition"),
            }
        elif _non_empty_contract_value(normalized.get("output_contract")):
            normalized["evaluator"] = {
                "type": "deterministic_receipt_probe",
                "pass_condition": "declared output contract is produced from declared inputs",
            }
    if "secret_policy" not in normalized:
        forbidden = (
            normalized.get("forbidden_feature_audit")
            or normalized.get("forbidden_features")
            or normalized.get("must_exclude_feature_classes")
            or nested_proposal.get("must_exclude_feature_classes")
        )
        if _non_empty_contract_value(forbidden):
            normalized["secret_policy"] = {
                "policy": "public_only",
                "forbidden_inputs": forbidden,
            }
        elif _non_empty_contract_value(normalized.get("claim_bindings")):
            normalized["secret_policy"] = {"policy": "public_only"}
    if "safety_invariant" not in normalized:
        forbidden = (
            normalized.get("forbidden_feature_audit")
            or normalized.get("forbidden_features")
            or normalized.get("must_exclude_feature_classes")
            or nested_proposal.get("must_exclude_feature_classes")
        )
        if _non_empty_contract_value(forbidden):
            normalized["safety_invariant"] = (
                "proposal must not depend on forbidden feature classes: "
                + json.dumps(forbidden, sort_keys=True, default=str)
            )
        elif _non_empty_contract_value(normalized.get("claim_bindings")):
            normalized["safety_invariant"] = (
                "proposal queues an observation/action capability only; it cannot "
                "weaken evaluators or certify the current candidate"
            )
    if "rollback_condition" not in normalized:
        normalized["rollback_condition"] = (
            "discard if declared evaluator cannot produce the output contract "
            "or if any candidate using the capability regresses a deterministic gate"
        )
    return normalized


def validate_leaf_workbench_action_request(
    payload: object,
    contract: LeafWorkbenchContract = DEFAULT_LEAF_WORKBENCH_CONTRACT,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("LEAF_WORKBENCH_ACTION_REQUEST requires object `payload`.")
    if str(payload.get("type") or "").strip() == "LEAF_WORKBENCH_ACTION_REQUEST":
        nested = payload.get("payload")
        if not isinstance(nested, dict):
            raise ValueError("LEAF_WORKBENCH_ACTION_REQUEST requires object `payload`.")
        payload = nested
    capability_id = str(payload.get("capability_id") or "").strip()
    if not capability_id:
        raise ValueError("LEAF_WORKBENCH_ACTION_REQUEST requires `capability_id`.")
    registry = contract.registry()
    if capability_id not in registry and "@" in capability_id:
        base_id, suffix = capability_id.rsplit("@", 1)
        cap = registry.get(base_id)
        if cap is not None and suffix == cap.version:
            capability_id = base_id
    if capability_id not in registry:
        raise ValueError(
            "LEAF_WORKBENCH_ACTION_REQUEST references unknown capability_id "
            f"{capability_id!r}. Use a registered capability; in science mode, "
            "report missing tools inside LOWERABILITY_BLOCKED."
        )
    input_refs = payload.get("input_refs", {})
    if not isinstance(input_refs, dict):
        raise ValueError("LEAF_WORKBENCH_ACTION_REQUEST `input_refs` must be an object.")
    claim_bindings = payload.get("claim_bindings", [])
    if claim_bindings is not None and not isinstance(claim_bindings, list):
        raise ValueError("LEAF_WORKBENCH_ACTION_REQUEST `claim_bindings` must be a list.")
    normalized = dict(payload)
    normalized["capability_id"] = capability_id
    normalized["input_refs"] = input_refs
    normalized["claim_bindings"] = claim_bindings or [f"requested {capability_id}"]
    normalized.setdefault("contract_sha256", contract.fingerprint())
    return normalized
