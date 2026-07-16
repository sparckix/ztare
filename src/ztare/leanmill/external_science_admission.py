"""Crash-recovery admission for externally completed LeanMill science.

The admitted object is a reviewed semantic context owned by one frozen theory
lineage.  It is distinct from post-freeze interpretation and has no authority
to discharge a theory task, earn outer-objective credit, or close a campaign.

Formal and finite identities remain in the admission audit.  Navigation sees
only a reviewer-authored semantic projection, its formal-statement digest, and
the frozen campaign branch identity.  The campaign runner alone may emit the
first-fire route event after inserting that projection into its causal trace.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import re
from typing import Any

from ztare.leanmill.common import read_json, sha256_file, write_json_atomic
from ztare.leanmill.finite_theory_context import load_formal_theory_context
from ztare.leanmill.frontier_blueprint import FrontierTheoryBlueprint
from ztare.leanmill.frontier_campaign import (
    validate_campaign_artifact_binding,
    verify_campaign_artifact_signature,
)
from ztare.leanmill.axiompack_leaf_workbench import (
    reviewed_axiompack_workbench_successor,
)
from ztare.leanmill.lean_source import (
    decl_spans,
    open_decl_for_ratification,
    resolve_theorem_target,
    source_through_target,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_program import TheoryProgram


EXTERNAL_SCIENCE_REQUEST_SCHEMA = "leanmill.external_science_recovery_request.v1"
EXTERNAL_SCIENCE_FORMAL_EVIDENCE_SCHEMA = (
    "leanmill.external_science_formal_evidence.v1"
)
EXTERNAL_REVIEW_SCHEMA = "leanmill.external_science_independent_review.v1"
EXTERNAL_SEMANTIC_PROJECTION_SCHEMA = (
    "leanmill.external_science_semantic_projection.v1"
)
EXTERNAL_SCIENCE_ADMISSION_SCHEMA = "leanmill.external_science_resume_admission.v1"
EXTERNAL_SCIENCE_RESUME_CONTEXT_SCHEMA = "leanmill.external_science_resume_context.v1"
EXTERNAL_SCIENCE_NEGATIVE_DISPOSITION_SCHEMA = (
    "leanmill.external_science_negative_disposition.v1"
)
EXTERNAL_SCIENCE_REVIEW_EXECUTION_SCHEMA = (
    "leanmill.external_science_review_execution.v1"
)
EXTERNAL_SCIENCE_REVIEW_SUPERSESSION_SCHEMA = (
    "leanmill.external_science_review_supersession.v2"
)

_AUTHORITY = "resume_context_only"
_NO_CREDIT = "withheld_requires_campaign_owned_discharge"
_FORBIDDEN = "forbidden"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_QUALIFIED_NAME = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*$"
)
_PATHLIKE_TOKEN = re.compile(
    r"(?i)(?:https?|file)://[^\s\"']+"
    r"|(?:^|[\s\"'(:=])(?:/|~[/\\]|\.\.?[/\\]|[a-z]:[/\\])[^\s\"']+"
    r"|(?<![a-z0-9_.-])(?:[a-z0-9_.-]+[/\\]){2,}[a-z0-9_.-]+"
)
_REQUEST_FIELDS = {
    "schema",
    "attempt_id",
    "campaign_id",
    "campaign_packet_digest",
    "run_digest",
    "context_hash",
    "context_epoch",
    "lineage_id",
    "theory_program_id",
    "reviewed_presentation_formula_ids",
    "finite_witness",
    "formal_artifact",
    "literature_audit",
    "submitted_by",
    "reviewer_ref",
    "independent_review",
    "independent_review_execution",
    "request_sha256",
}
_REQUEST_CORE_FIELDS = _REQUEST_FIELDS - {
    "independent_review",
    "independent_review_execution",
    "request_sha256",
}
_SEMANTIC_PROJECTION_FIELDS = {
    "schema",
    "result_shape",
    "abstract_summary",
    "hypothesis_shape",
    "conclusion_shape",
    "open_residuals",
    "next_discriminator",
    "claim_boundary",
}
_REVIEW_FIELDS = {
    "schema",
    "author_ref",
    "decision",
    "scope",
    "reviewed_request_core_sha256",
    "formal_statement_sha256",
    "reviewed_audit_context_sha256",
    "finite_witness_relevance",
    "claim_boundary_acknowledged",
    "semantic_projection",
}
_ADMISSION_FIELDS = {
    "schema",
    "request_sha256",
    "attempt_id",
    "campaign_id",
    "campaign_packet_digest",
    "run_digest",
    "context_hash",
    "context_epoch",
    "lineage_id",
    "theory_program_id",
    "reviewed_presentation_formula_ids",
    "finite_witness_model_id",
    "theorem_target",
    "formal_statement",
    "formal_statement_sha256",
    "semantic_projection",
    "semantic_projection_sha256",
    "evidence_bindings",
    "reviewer_ref",
    "authority",
    "outer_objective_credit",
    "campaign_closure",
    "theory_task_discharge",
    "post_freeze_interpretation_identity",
    "source_identity_visibility",
    "admission_sha256",
}
_NEGATIVE_DISPOSITION_FIELDS = {
    "schema",
    "outcome",
    "context_hash",
    "context_epoch",
    "lineage_id",
    "theory_program_id",
    "reviewed_presentation_formula_ids",
    "audit_binding_sha256",
    "audit_binding_kind",
    "semantic_projection",
    "semantic_projection_sha256",
    "projection_authority",
    "typed_residual",
    "next_action",
    "authority",
    "outer_objective_credit",
    "campaign_closure",
    "theory_task_discharge",
    "source_identity_visibility",
    "receipt_sha256",
}
_REVIEW_EXECUTION_FIELDS = {
    "schema",
    "attempt_id",
    "request_core_sha256",
    "reviewer_ref",
    "prompt_digest",
    "action_id",
    "outcome",
    "role_call",
    "owned_dispatch",
    "transport_provenance",
    "budget_reservation_id",
    "budget_event_sha256s",
    "execution_sha256",
}
_REVIEW_PROMPT_PREFIX = (
    "You are the independent crash-recovery reviewer for one interrupted "
    "LeanMill theory lineage. Use the mapping audit to check that the frozen "
    "campaign equations, anonymous witness, and carried formal declaration "
    "support the claimed correspondence. Reject if that mapping is missing. "
    "Set author_ref to the packet's reviewer_ref and echo the mapping audit "
    "digest in reviewed_audit_context_sha256. "
    "Return a source-free semantic projection: do not copy theorem, namespace, "
    "file, model, artifact, or literature identifiers. Admission resumes search "
    "only. It does not discharge the campaign task, award outer-objective "
    "credit, establish novelty, or close the campaign. Return only the requested "
    "JSON object.\n\nFROZEN REVIEW INPUT:\n"
)


def _exact_fields(value: Any, fields: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{label} fields do not match the frozen schema")
    return value


def _text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text or value != text:
        raise ValueError(f"{label} must be a non-empty canonical string")
    return text


def _sha(value: Any, label: str) -> str:
    digest = str(value or "")
    if not _HEX64.fullmatch(digest):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def _content_bound(value: Mapping[str, Any], field: str, label: str) -> None:
    digest = _sha(value.get(field), f"{label}.{field}")
    core = {key: item for key, item in value.items() if key != field}
    if digest != content_hash(core):
        raise ValueError(f"{label} digest mismatch")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_rooted_path(
    ref: Mapping[str, Any],
    *,
    attempt_dir: Path,
    repo_root: Path,
    label: str,
) -> Path:
    roots = {"attempt": attempt_dir.resolve(), "repo": repo_root.resolve()}
    root_name = str(ref.get("root") or "")
    if root_name not in roots:
        raise ValueError(f"{label}.root must be attempt or repo")
    relative = Path(_text(ref.get("path"), f"{label}.path"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label}.path must remain under its declared root")
    root = roots[root_name]
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label}.path escapes its declared root") from exc
    if not path.is_file():
        raise ValueError(f"{label} artifact is unavailable")
    return path


def _resolve_artifact_ref(
    ref: Any,
    *,
    attempt_dir: Path,
    repo_root: Path,
    label: str,
) -> Path:
    row = _exact_fields(ref, {"root", "path", "sha256"}, label)
    path = _resolve_rooted_path(
        row, attempt_dir=attempt_dir, repo_root=repo_root, label=label
    )
    if sha256_file(path) != _sha(row.get("sha256"), f"{label}.sha256"):
        raise ValueError(f"{label} artifact digest mismatch")
    return path


def _path_ref(path: Path, *, attempt_dir: Path, repo_root: Path) -> dict[str, str]:
    resolved = path.resolve()
    for name, root in (("attempt", attempt_dir.resolve()), ("repo", repo_root.resolve())):
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            continue
        return {"root": name, "path": relative.as_posix()}
    raise ValueError("formal evidence path is outside the attempt and repository")


def _artifact_ref(path: Path, *, attempt_dir: Path, repo_root: Path) -> dict[str, str]:
    row = _path_ref(path, attempt_dir=attempt_dir, repo_root=repo_root)
    digest = sha256_file(path)
    if digest is None:
        raise ValueError("formal evidence artifact is unavailable")
    return {**row, "sha256": digest}


def _read_jsonl(path: Path) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, Mapping):
            raise ValueError("canonical JSONL evidence contains a non-object row")
        rows.append(value)
    return tuple(rows)


def _record_from_ref(
    value: Any,
    *,
    attempt_dir: Path,
    repo_root: Path,
    label: str,
) -> Mapping[str, Any]:
    row = _exact_fields(value, {"root", "path", "record_sha256"}, label)
    path = _resolve_rooted_path(
        row, attempt_dir=attempt_dir, repo_root=repo_root, label=label
    )
    record_sha = _sha(row.get("record_sha256"), f"{label}.record_sha256")
    matches = [record for record in _read_jsonl(path) if content_hash(record) == record_sha]
    if len(matches) != 1:
        raise ValueError(f"{label} does not identify one canonical record")
    return matches[0]


def _record_ref(
    path: Path,
    record: Mapping[str, Any],
    *,
    attempt_dir: Path,
    repo_root: Path,
) -> dict[str, str]:
    return {
        **_path_ref(path, attempt_dir=attempt_dir, repo_root=repo_root),
        "record_sha256": content_hash(record),
    }


def _formal_statement(source: str, target: str) -> str:
    identity = resolve_theorem_target(source, target)
    if identity is None:
        raise ValueError("formal source does not identify exactly one target")
    open_decl_for_ratification(source, target)
    body = source[identity.name_end : identity.decl_end]
    from ztare.leanmill.lean_source import split_at_proof
    from ztare.leanmill.solver.statement_integrity import _norm

    statement, assigned = split_at_proof(body)
    if not assigned.startswith(":="):
        raise ValueError("formal target has no proof assignment")
    normalized = _norm(statement)
    if not normalized or normalized in {": True", ": Prop"}:
        raise ValueError("formal target statement is degenerate")
    return normalized


def _receipt_passed(receipt: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(receipt, Mapping) or receipt.get("passed") is not True:
        raise ValueError(f"closure certificate {label} did not pass")
    tail = str(receipt.get("tail") or "").lower()
    if any(word in tail for word in ("fail-open", "error", "skipped", "inconclusive")):
        raise ValueError(f"closure certificate {label} is not a positive receipt")
    return receipt


def _validate_closure_record(
    record: Mapping[str, Any], *, target: str, statement: str
) -> None:
    governance = record.get("governance")
    governance = governance if isinstance(governance, Mapping) else {}
    kernel = governance.get("governance_kernel")
    kernel = kernel if isinstance(kernel, Mapping) else {}
    integrity = governance.get("statement_integrity")
    integrity = integrity if isinstance(integrity, Mapping) else {}
    discrimination = (
        (((governance.get("margin_of_safety") or {}).get("tests") or {}).get(
            "conclusion_discrimination"
        ) or {})
        if isinstance(governance.get("margin_of_safety"), Mapping)
        else {}
    )
    detail = discrimination.get("detail")
    detail = detail if isinstance(detail, Mapping) else {}
    mnc = record.get("matched_negative_control")
    mnc = mnc if isinstance(mnc, Mapping) else {}
    validation = record.get("solver_validation")
    validation = validation if isinstance(validation, Mapping) else {}
    receipts = validation.get("receipts")
    receipts = receipts if isinstance(receipts, Mapping) else {}
    probe = str(record.get("recompilable_probe") or "")
    if (
        record.get("target") != target
        or record.get("outcome") != "closed"
        or record.get("checker") != "lean_lake"
        or record.get("ratification_only") is not True
        or kernel.get("passed") is not True
        or integrity.get("ok") is not True
        or governance.get("integrity_unverified") is True
        or detail.get("differential") != "confirmed"
        or mnc.get("passed") is not True
        or validation.get("credit_ready_at_solver_layer") is not True
        or validation.get("positive_axiom_receipt_required") is not True
        or validation.get("axiom_tier") != "kernel_pure"
        or not probe
        or not str(record.get("closure_lean") or "")
    ):
        raise ValueError("closure certificate is not a governed ratification-only record")
    for name in (
        "kernel_compile_receipt",
        "matched_negative_control_receipt",
        "governance_kernel_receipt",
        "axiom_allowlist_receipt",
    ):
        _receipt_passed(receipts.get(name), name)
    if _formal_statement(probe, target) != statement:
        raise ValueError("closure certificate proves a different statement")


def _validate_kernel_parity_record(record: Mapping[str, Any], *, target: str) -> None:
    hand = record.get("hand_wired")
    hand = hand if isinstance(hand, Mapping) else {}
    kernel = record.get("kernel")
    kernel = kernel if isinstance(kernel, Mapping) else {}
    if (
        record.get("target") != target
        or hand.get("kc") is not True
        or hand.get("mnc") is not True
        or kernel.get("passed") is not True
        or record.get("kernel_blocked") is not False
    ):
        raise ValueError("kernel parity record does not clear the target")


def _attempt_lease(directory: Path, action: str):
    from ztare.leanmill.frontier_campaign_runner import frontier_attempt_lease

    return frontier_attempt_lease(directory, action=action)


def materialize_external_science_formal_evidence(
    attempt_dir: str | Path,
    *,
    source_path: str | Path,
    theorem_target: str,
    closure_ledger_path: str | Path,
    kernel_parity_ledger_path: str | Path,
    repo_root: str | Path | None = None,
    _attempt_lease_token: Any = None,
) -> dict[str, str]:
    """Export exact canonical ratification records into an immutable request ref."""

    directory = Path(attempt_dir).resolve()
    if _attempt_lease_token is None:
        with _attempt_lease(directory, "external_science_formal_evidence") as lease:
            return materialize_external_science_formal_evidence(
                directory,
                source_path=source_path,
                theorem_target=theorem_target,
                closure_ledger_path=closure_ledger_path,
                kernel_parity_ledger_path=kernel_parity_ledger_path,
                repo_root=repo_root,
                _attempt_lease_token=lease,
            )
    repo = _repo_root() if repo_root is None else Path(repo_root).resolve()
    source = Path(source_path).resolve()
    closure_path = Path(closure_ledger_path).resolve()
    parity_path = Path(kernel_parity_ledger_path).resolve()
    target = _text(theorem_target, "theorem_target")
    if not _QUALIFIED_NAME.fullmatch(target):
        raise ValueError("theorem_target must be a qualified Lean identifier")
    if not source.is_file() or not closure_path.is_file() or not parity_path.is_file():
        raise ValueError("formal evidence materializer requires existing canonical artifacts")
    statement = _formal_statement(source.read_text(encoding="utf-8"), target)
    closure_matches: list[Mapping[str, Any]] = []
    for record in _read_jsonl(closure_path):
        try:
            _validate_closure_record(record, target=target, statement=statement)
        except ValueError:
            continue
        closure_matches.append(record)
    if not closure_matches:
        raise ValueError("no governed ratification-only closure matches the formal source")
    parity_matches: list[Mapping[str, Any]] = []
    for record in _read_jsonl(parity_path):
        try:
            _validate_kernel_parity_record(record, target=target)
        except ValueError:
            continue
        parity_matches.append(record)
    if not parity_matches:
        raise ValueError("no canonical kernel parity record matches the formal target")
    core = {
        "schema": EXTERNAL_SCIENCE_FORMAL_EVIDENCE_SCHEMA,
        "source": _artifact_ref(source, attempt_dir=directory, repo_root=repo),
        "theorem_target": target,
        "formal_statement_sha256": content_hash({"formal_statement": statement}),
        "closure_certificate": _record_ref(
            closure_path,
            closure_matches[-1],
            attempt_dir=directory,
            repo_root=repo,
        ),
        "kernel_parity": _record_ref(
            parity_path,
            parity_matches[-1],
            attempt_dir=directory,
            repo_root=repo,
        ),
    }
    evidence = {**core, "evidence_sha256": content_hash(core)}
    path = directory / f"external_science_formal_evidence.{evidence['evidence_sha256'][:16]}.json"
    prior = read_json(path, None)
    if isinstance(prior, Mapping) and dict(prior) != evidence:
        raise ValueError("formal evidence export conflicts with its content address")
    if prior is None:
        write_json_atomic(path, evidence)
    return _artifact_ref(path, attempt_dir=directory, repo_root=repo)


def external_science_review_output_schema() -> dict[str, Any]:
    text = {"type": "string", "minLength": 1, "maxLength": 1200}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(_REVIEW_FIELDS),
        "properties": {
            "schema": {"type": "string", "const": EXTERNAL_REVIEW_SCHEMA},
            "author_ref": {"type": "string", "minLength": 1},
            "decision": {"type": "string", "enum": ["admit_for_resume_context", "reject"]},
            "scope": {
                "type": "string",
                "const": "resume_context_only_no_objective_or_closure_credit",
            },
            "reviewed_request_core_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "formal_statement_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "reviewed_audit_context_sha256": {
                "type": "string",
                "pattern": "^[0-9a-f]{64}$",
            },
            "finite_witness_relevance": {
                "type": "string",
                "enum": ["statement_reviewed_against_preserved_witness", "not_established"],
            },
            "claim_boundary_acknowledged": {"type": "boolean"},
            "semantic_projection": {
                "type": "object",
                "additionalProperties": False,
                "required": sorted(_SEMANTIC_PROJECTION_FIELDS),
                "properties": {
                    "schema": {"type": "string", "const": EXTERNAL_SEMANTIC_PROJECTION_SCHEMA},
                    "result_shape": text,
                    "abstract_summary": text,
                    "hypothesis_shape": {"type": "array", "minItems": 1, "maxItems": 12, "items": text},
                    "conclusion_shape": text,
                    "open_residuals": {"type": "array", "minItems": 1, "maxItems": 12, "items": text},
                    "next_discriminator": text,
                    "claim_boundary": {
                        "type": "string",
                        "const": "resume_context_only_pending_campaign_owned_discharge",
                    },
                },
            },
        },
}


def _mapping_audit_context(
    *,
    context: Any,
    reviewed_presentation_formula_ids: list[str],
    source_text: str,
    theorem_target: str,
    formal_statement: str,
) -> dict[str, Any]:
    profiles = {row.formula_id: row for row in context.formula_profiles}
    presentation_semantics = []
    for formula_id in reviewed_presentation_formula_ids:
        profile = profiles.get(formula_id)
        if profile is None:
            raise ValueError("mapping audit references an unknown campaign formula")
        presentation_semantics.append(
            {
                "formula_id": formula_id,
                "semantic_sha256": profile.axiom.semantic_hash,
                "axiom": profile.axiom.to_json(),
            }
        )
    inherited_source = source_through_target(source_text, theorem_target)
    if not inherited_source or len(inherited_source.encode("utf-8")) > 250_000:
        raise ValueError("formal declaration context is empty or exceeds the audit bound")
    core = {
        "schema": "leanmill.external_science_mapping_audit_context.v1",
        "campaign_law_semantics": {
            "signature_sha256": context.signature.content_hash,
            "signature": context.signature.to_json(),
            "base_axioms": [
                {
                    "semantic_sha256": axiom.semantic_hash,
                    "axiom": axiom.to_json(),
                }
                for axiom in context.base_axioms
            ],
            "presentation_axioms": presentation_semantics,
        },
        "formal_declaration_context": {
            "theorem_target": theorem_target,
            "formal_statement": formal_statement,
            "source_through_target_sha256": content_hash(
                {"source_through_target": inherited_source}
            ),
            "source_through_target": inherited_source,
        },
    }
    return {**core, "audit_context_sha256": content_hash(core)}


def external_science_review_prompt(
    *,
    request_core_sha256: str,
    formal_statement: str,
    formal_statement_sha256: str,
    reviewed_presentation_formula_ids: list[str],
    anonymous_witness: Mapping[str, Any],
    submitted_by: str,
    reviewer_ref: str,
    mapping_audit_context: Mapping[str, Any],
) -> str:
    audit = dict(mapping_audit_context)
    audit_core = {
        key: value for key, value in audit.items() if key != "audit_context_sha256"
    }
    if (
        audit.get("schema")
        != "leanmill.external_science_mapping_audit_context.v1"
        or audit.get("audit_context_sha256") != content_hash(audit_core)
    ):
        raise ValueError("mapping audit context is not content-bound")
    packet = {
        "schema": "leanmill.external_science_review_packet.v1",
        "request_core_sha256": _sha(request_core_sha256, "request_core_sha256"),
        "formal_statement": _text(formal_statement, "formal_statement"),
        "formal_statement_sha256": _sha(
            formal_statement_sha256, "formal_statement_sha256"
        ),
        "reviewed_presentation_formula_ids": list(reviewed_presentation_formula_ids),
        "anonymous_witness": dict(anonymous_witness),
        "submitted_by": _text(submitted_by, "submitted_by"),
        "reviewer_ref": _text(reviewer_ref, "reviewer_ref"),
        "mapping_audit_context": audit,
        "claim_boundary": "resume_context_only_no_objective_task_or_closure_credit",
    }
    return _REVIEW_PROMPT_PREFIX + json.dumps(
        packet, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _active_campaign(directory: Path) -> Mapping[str, Any]:
    active = read_json(directory / "campaign.json", None)
    if isinstance(active, Mapping):
        return active
    root = read_json(directory / "campaign.epoch-000.json", None)
    if isinstance(root, Mapping):
        return root
    raise ValueError("external science admission requires a signed campaign artifact")


def _campaign_packet_for_request(
    directory: Path,
    *,
    blueprint_id: str,
    context_hash: str,
    expected_packet_digest: str,
) -> Mapping[str, Any]:
    """Replay a request packet through signed workbench-successor transitions."""

    active = _active_campaign(directory)
    public_key_path = directory / "campaign_signer_public.pem"
    if not public_key_path.is_file():
        raise ValueError("campaign signer public key is unavailable")
    public_key = public_key_path.read_text(encoding="utf-8")

    artifacts: dict[str, Mapping[str, Any]] = {}
    for path in [directory / "campaign.json", *sorted(directory.glob("campaign.epoch-*.json"))]:
        row = read_json(path, None)
        if not isinstance(row, Mapping) or not isinstance(row.get("packet"), Mapping):
            continue
        digest = str(row.get("packet_digest") or "")
        validate_campaign_artifact_binding(
            row,
            blueprint_id=blueprint_id,
            context_hash=context_hash,
            expected_packet_digest=digest,
        )
        if not verify_campaign_artifact_signature(
            row,
            public_key_pem=public_key,
            expected_signer_ref=str(row.get("signer_ref") or ""),
        ):
            raise ValueError("campaign signature does not verify")
        prior = artifacts.get(digest)
        if prior is not None and dict(prior) != dict(row):
            raise ValueError("campaign packet digest has conflicting signed artifacts")
        artifacts[digest] = row

    active_digest = str(active.get("packet_digest") or "")
    source = artifacts.get(expected_packet_digest)
    if source is None or active_digest not in artifacts:
        raise ValueError("external science request packet is not in the signed campaign lineage")
    if expected_packet_digest == active_digest:
        return source["packet"]

    transitions: dict[str, Mapping[str, Any]] = {}
    for path in sorted(directory.glob("campaign_workbench_successor.*.json")):
        row = read_json(path, None)
        if not isinstance(row, Mapping):
            continue
        core = {key: value for key, value in row.items() if key != "receipt_sha256"}
        if (
            row.get("schema")
            != "leanmill.campaign_workbench_successor_transition.v1"
            or row.get("receipt_sha256") != content_hash(core)
            or not str(row.get("authority_ref") or "").strip()
        ):
            raise ValueError("campaign workbench successor transition is malformed")
        source_digest = str(row.get("source_packet_digest") or "")
        if source_digest in transitions and dict(transitions[source_digest]) != dict(row):
            raise ValueError("campaign workbench successor transition forks")
        transitions[source_digest] = row

    current = expected_packet_digest
    visited: set[str] = set()
    while current != active_digest:
        if current in visited:
            raise ValueError("campaign workbench successor transition cycles")
        visited.add(current)
        transition = transitions.get(current)
        if not isinstance(transition, Mapping):
            raise ValueError("campaign request packet has no signed successor path")
        target_digest = str(transition.get("target_packet_digest") or "")
        source_artifact = artifacts.get(current)
        target_artifact = artifacts.get(target_digest)
        if source_artifact is None or target_artifact is None:
            raise ValueError("campaign workbench successor lost a signed endpoint")
        source_packet = source_artifact["packet"]
        target_packet = target_artifact["packet"]
        source_invariant = {
            key: value for key, value in source_packet.items()
            if key != "navigator_contract"
        }
        target_invariant = {
            key: value for key, value in target_packet.items()
            if key != "navigator_contract"
        }
        if source_invariant != target_invariant:
            raise ValueError("campaign workbench successor changed semantic identity")
        policy = reviewed_axiompack_workbench_successor(
            source_packet["navigator_contract"],
            target_packet["navigator_contract"],
        )
        if (
            transition.get("policy") != policy
            or transition.get("campaign_id") != source_packet.get("campaign_id")
            or transition.get("context_hash") != context_hash
        ):
            raise ValueError("campaign workbench successor policy does not replay")
        current = target_digest
    return source["packet"]


def _validated_run(directory: Path) -> Mapping[str, Any]:
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("external science admission requires a campaign run")
    core = {key: value for key, value in run.items() if key != "run_digest"}
    if run.get("run_digest") != content_hash(core):
        raise ValueError("campaign run digest mismatch")
    if run.get("status") in {"frontier_objective_discharged", "campaign_complete"}:
        raise ValueError("a terminal campaign cannot receive resume-only evidence")
    if not isinstance(run.get("navigation"), Mapping):
        raise ValueError("campaign run has no navigation state")
    return run


def _current_programs_by_lineage(run: Mapping[str, Any]) -> dict[str, TheoryProgram]:
    navigation = run["navigation"]
    programs: dict[str, TheoryProgram] = {}
    for collection in ("finalists", "objective_survivors"):
        for candidate in navigation.get(collection) or ():
            if not isinstance(candidate, Mapping):
                continue
            try:
                program = TheoryProgram.from_json(candidate.get("theory_program"))
            except (TypeError, ValueError):
                continue
            programs[program.lineage_id] = program
    return programs


def _current_context_epoch(run: Mapping[str, Any]) -> int:
    navigation = run["navigation"]
    summary = run.get("context_summary")
    summary = summary if isinstance(summary, Mapping) else {}
    return int(navigation.get("context_epoch", summary.get("context_epoch", 0)))


def _formal_evidence(
    value: Any, *, directory: Path, repo: Path
) -> tuple[Mapping[str, Any], str, str, Mapping[str, Any], Mapping[str, Any]]:
    path = _resolve_artifact_ref(
        value,
        attempt_dir=directory,
        repo_root=repo,
        label="formal artifact",
    )
    evidence = read_json(path, None)
    fields = {
        "schema",
        "source",
        "theorem_target",
        "formal_statement_sha256",
        "closure_certificate",
        "kernel_parity",
        "evidence_sha256",
    }
    evidence = _exact_fields(evidence, fields, "formal evidence")
    if evidence.get("schema") != EXTERNAL_SCIENCE_FORMAL_EVIDENCE_SCHEMA:
        raise ValueError("formal evidence has the wrong schema")
    _content_bound(evidence, "evidence_sha256", "formal evidence")
    source_path = _resolve_artifact_ref(
        evidence.get("source"),
        attempt_dir=directory,
        repo_root=repo,
        label="formal evidence.source",
    )
    target = _text(evidence.get("theorem_target"), "theorem_target")
    if not _QUALIFIED_NAME.fullmatch(target):
        raise ValueError("theorem_target must be a qualified Lean identifier")
    statement = _formal_statement(source_path.read_text(encoding="utf-8"), target)
    if evidence.get("formal_statement_sha256") != content_hash(
        {"formal_statement": statement}
    ):
        raise ValueError("formal evidence statement digest mismatch")
    closure = _record_from_ref(
        evidence.get("closure_certificate"),
        attempt_dir=directory,
        repo_root=repo,
        label="formal evidence.closure_certificate",
    )
    _validate_closure_record(closure, target=target, statement=statement)
    parity = _record_from_ref(
        evidence.get("kernel_parity"),
        attempt_dir=directory,
        repo_root=repo,
        label="formal evidence.kernel_parity",
    )
    _validate_kernel_parity_record(parity, target=target)
    return evidence, target, statement, closure, parity


def _companion_path(call_path: Path, suffix: str) -> Path:
    if not call_path.name.endswith(".call.json"):
        raise ValueError("independent review ref must identify a durable role call")
    return call_path.parent / (call_path.name[: -len(".call.json")] + suffix)


def _review_request_core_path(directory: Path, digest: str) -> Path:
    return directory / f"external_science_review_request_core.{digest[:16]}.json"


def _review_execution_path(directory: Path, digest: str) -> Path:
    return directory / f"external_science_review_execution.{digest[:16]}.json"


def _budget_events(directory: Path) -> tuple[Mapping[str, Any], ...]:
    path = directory / "budget.events.jsonl"
    if not path.is_file():
        return ()
    rows = _read_jsonl(path)
    for row in rows:
        event_sha = str(row.get("event_sha256") or "")
        core = {key: value for key, value in row.items() if key != "event_sha256"}
        if not _HEX64.fullmatch(event_sha) or event_sha != content_hash(core):
            raise ValueError("external science budget evidence is not content-bound")
    return rows


def _persist_review_request_core(
    directory: Path, request_core: Mapping[str, Any]
) -> str:
    core = dict(
        _exact_fields(
            request_core,
            _REQUEST_CORE_FIELDS,
            "external science review request core",
        )
    )
    digest = content_hash(core)
    path = _review_request_core_path(directory, digest)
    prior = read_json(path, None)
    if isinstance(prior, Mapping) and dict(prior) != core:
        raise ValueError("external science review request core changed identity")
    if prior is None:
        write_json_atomic(path, core)
    return digest


def persist_external_science_review_request_core(
    attempt_dir: str | Path, request_core: Mapping[str, Any]
) -> str:
    """Freeze the source-bearing reviewer plan before any budget reservation."""

    return _persist_review_request_core(Path(attempt_dir).resolve(), request_core)


def _validate_interrupted_owned_dispatch(
    path: Path, *, expected_parent: Path
) -> Mapping[str, Any]:
    row = read_json(path, None)
    required = {
        "schema",
        "call_id",
        "leader_pid",
        "pgid",
        "sid",
        "parent_pgid",
        "command_sha256",
        "stdin_sha256",
        "stdout_path",
        "stderr_path",
        "started_at_epoch",
        "status",
        "returncode",
        "updated_at_epoch",
    }
    stdout_path = Path(str((row or {}).get("stdout_path") or "")).resolve()
    stderr_path = Path(str((row or {}).get("stderr_path") or "")).resolve()
    if (
        not isinstance(row, Mapping)
        or set(row) != required
        or row.get("schema") != "ztare.owned_dispatch.v1"
        or row.get("status") not in {"running", "completed"}
        or row.get("status") == "running" and row.get("returncode") is not None
        or row.get("status") == "completed" and type(row.get("returncode")) is not int
        or stdout_path.parent != expected_parent
        or stderr_path.parent != expected_parent
        or stdout_path.stem != stderr_path.stem
        or any(type(row.get(field)) is not int or int(row[field]) <= 0 for field in (
            "leader_pid", "pgid", "sid", "parent_pgid"
        ))
        or row.get("leader_pid") != row.get("pgid")
        or row.get("leader_pid") != row.get("sid")
        or row.get("pgid") == row.get("parent_pgid")
        or not str(row.get("call_id") or "")
        or not str(row.get("command_sha256") or "").startswith("sha256:")
    ):
        raise ValueError("interrupted external science dispatch is invalid")
    return row


def _validate_owned_dispatch(
    path: Path,
    *,
    call_path: Path,
    call: Mapping[str, Any],
) -> Mapping[str, Any]:
    row = read_json(path, None)
    required = {
        "schema",
        "call_id",
        "leader_pid",
        "pgid",
        "sid",
        "parent_pgid",
        "command_sha256",
        "stdin_sha256",
        "stdout_path",
        "stderr_path",
        "started_at_epoch",
        "status",
        "returncode",
        "updated_at_epoch",
    }
    stdout_path = _companion_path(call_path, ".stdout.txt").resolve()
    stderr_path = _companion_path(call_path, ".stderr.txt").resolve()
    if (
        not isinstance(row, Mapping)
        or set(row) != required
        or row.get("schema") != "ztare.owned_dispatch.v1"
        or row.get("status") != "completed"
        or row.get("returncode") != call.get("returncode")
        or str(row.get("stdout_path") or "") != str(stdout_path)
        or str(row.get("stderr_path") or "") != str(stderr_path)
        or any(type(row.get(field)) is not int or int(row[field]) <= 0 for field in (
            "leader_pid", "pgid", "sid", "parent_pgid"
        ))
        or row.get("leader_pid") != row.get("pgid")
        or row.get("leader_pid") != row.get("sid")
        or row.get("pgid") == row.get("parent_pgid")
        or not str(row.get("call_id") or "")
        or not str(row.get("command_sha256") or "").startswith("sha256:")
    ):
        raise ValueError("external science reviewer owned dispatch is invalid")
    return row


def materialize_external_science_review_execution(
    attempt_dir: str | Path,
    *,
    request_core: Mapping[str, Any],
    reviewer_ref: str,
    prompt_digest: str,
    action_id: str,
    outcome: str,
    role_call_path: str | Path | None,
    owned_dispatch_path: str | Path | None,
    transport_provenance_path: str | Path | None,
    budget_reservation_id: str,
    budget_event_sha256s: list[str],
) -> dict[str, Any]:
    """Bind a review outcome to its role process and budget journal events."""

    directory = Path(attempt_dir).resolve()
    request_core_sha = _persist_review_request_core(directory, request_core)
    if outcome not in {
        "review_completed",
        "reviewer_transport_unavailable",
        "reviewer_budget_unavailable",
    }:
        raise ValueError("external science review execution has an unknown outcome")

    def local_ref(value: str | Path | None) -> dict[str, str]:
        if value is None:
            return {}
        path = Path(value).resolve()
        try:
            path.relative_to(directory)
        except ValueError as exc:
            raise ValueError("external science review evidence escaped the attempt") from exc
        return _artifact_ref(path, attempt_dir=directory, repo_root=_repo_root())

    core = {
        "schema": EXTERNAL_SCIENCE_REVIEW_EXECUTION_SCHEMA,
        "attempt_id": directory.name,
        "request_core_sha256": request_core_sha,
        "reviewer_ref": _text(reviewer_ref, "review execution reviewer_ref"),
        "prompt_digest": _sha(prompt_digest, "review execution prompt_digest"),
        "action_id": _text(action_id, "review execution action_id"),
        "outcome": outcome,
        "role_call": local_ref(role_call_path),
        "owned_dispatch": local_ref(owned_dispatch_path),
        "transport_provenance": local_ref(transport_provenance_path),
        "budget_reservation_id": str(budget_reservation_id or ""),
        "budget_event_sha256s": [
            _sha(value, "review execution budget event")
            for value in budget_event_sha256s
        ],
    }
    execution = {**core, "execution_sha256": content_hash(core)}
    path = _review_execution_path(directory, execution["execution_sha256"])
    prior = read_json(path, None)
    if isinstance(prior, Mapping) and dict(prior) != execution:
        raise ValueError("external science review execution changed identity")
    if prior is None:
        write_json_atomic(path, execution)
    _validate_review_execution(directory, execution)
    return _artifact_ref(path, attempt_dir=directory, repo_root=_repo_root())


def _validate_review_execution(
    directory: Path,
    execution: Mapping[str, Any],
    *,
    expected_request_core_sha: str | None = None,
    expected_reviewer_ref: str | None = None,
    expected_prompt_digest: str | None = None,
    expected_role_call_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = dict(
        _exact_fields(
            execution,
            _REVIEW_EXECUTION_FIELDS,
            "external science review execution",
        )
    )
    if (
        row.get("schema") != EXTERNAL_SCIENCE_REVIEW_EXECUTION_SCHEMA
        or row.get("attempt_id") != directory.name
    ):
        raise ValueError("external science review execution targets another attempt")
    _content_bound(row, "execution_sha256", "external science review execution")
    digest = str(row["execution_sha256"])
    if read_json(_review_execution_path(directory, digest), None) != row:
        raise ValueError("external science review execution is not persisted")
    request_core_sha = _sha(
        row.get("request_core_sha256"), "review execution request_core_sha256"
    )
    request_core = read_json(_review_request_core_path(directory, request_core_sha), None)
    if (
        not isinstance(request_core, Mapping)
        or content_hash(dict(request_core)) != request_core_sha
        or set(request_core) != _REQUEST_CORE_FIELDS
    ):
        raise ValueError("external science review execution lost its request core")
    if expected_request_core_sha is not None and request_core_sha != expected_request_core_sha:
        raise ValueError("external science review execution targets another request")
    if expected_reviewer_ref is not None and row.get("reviewer_ref") != expected_reviewer_ref:
        raise ValueError("external science review execution targets another reviewer")
    if expected_prompt_digest is not None and row.get("prompt_digest") != expected_prompt_digest:
        raise ValueError("external science review execution targets another prompt")

    event_shas = row.get("budget_event_sha256s")
    if not isinstance(event_shas, list) or not event_shas:
        raise ValueError("external science review execution lacks budget evidence")
    all_events = _budget_events(directory)
    events: list[Mapping[str, Any]] = []
    for event_sha in event_shas:
        digest_value = _sha(event_sha, "review execution budget event")
        matches = [event for event in all_events if event.get("event_sha256") == digest_value]
        if len(matches) != 1:
            raise ValueError("external science review budget event is unavailable")
        events.append(matches[0])
    action_id = _text(row.get("action_id"), "review execution action_id")
    reservation_id = str(row.get("budget_reservation_id") or "")
    reserves = [
        event for event in events
        if event.get("event_type") == "resources_reserved"
        and event.get("action_id") == action_id
        and event.get("reservation_id") == reservation_id
    ]
    terminals = [
        event for event in events
        if event.get("reservation_id") == reservation_id
        and event.get("event_type") in {"reservation_committed", "reservation_released"}
    ]
    stops = [event for event in events if event.get("event_type") == "budget_stopped"]
    outcome = str(row.get("outcome") or "")
    role_call_ref = row.get("role_call")
    dispatch_ref = row.get("owned_dispatch")
    provenance_ref = row.get("transport_provenance")
    call: Mapping[str, Any] | None = None
    call_path: Path | None = None
    dispatch: Mapping[str, Any] | None = None
    provenance: Mapping[str, Any] | None = None
    if outcome == "review_completed" or (
        outcome == "reviewer_transport_unavailable" and bool(role_call_ref)
    ):
        call_path = _resolve_artifact_ref(
            role_call_ref,
            attempt_dir=directory,
            repo_root=_repo_root(),
            label="review execution role_call",
        )
        expected_parent = (directory / "agent_calls" / "external_science_reviewer").resolve()
        if call_path.parent != expected_parent:
            raise ValueError("external science review call escaped its assigned role directory")
        call = read_json(call_path, None)
        if (
            not isinstance(call, Mapping)
            or call.get("schema") != "leanmill.frontier_subscription_role_call.v1"
            or call.get("role") != "external_science_reviewer"
            or call.get("agent_id") != row.get("reviewer_ref")
            or call.get("prompt_digest") != row.get("prompt_digest")
        ):
            raise ValueError("external science review call does not match its execution")
        dispatch_path = _resolve_artifact_ref(
            dispatch_ref,
            attempt_dir=directory,
            repo_root=_repo_root(),
            label="review execution owned_dispatch",
        )
        if dispatch_path != _companion_path(call_path, ".dispatch.json"):
            raise ValueError("external science review dispatch does not match its role call")
        dispatch = _validate_owned_dispatch(dispatch_path, call_path=call_path, call=call)
        provenance_path = _resolve_artifact_ref(
            provenance_ref,
            attempt_dir=directory,
            repo_root=_repo_root(),
            label="review execution transport_provenance",
        )
        provenance = read_json(provenance_path, None)
        if not isinstance(provenance, Mapping):
            raise ValueError("external science review transport provenance is malformed")
        provenance_core = {
            key: value for key, value in provenance.items() if key != "receipt_sha256"
        }
        prompt_text = _companion_path(call_path, ".prompt.txt").read_text(
            encoding="utf-8"
        )
        stdout_text = _companion_path(call_path, ".stdout.txt").read_text(
            encoding="utf-8"
        )
        stderr_text = _companion_path(call_path, ".stderr.txt").read_text(
            encoding="utf-8"
        )

        def raw_sha(value: str) -> str:
            import hashlib

            return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()

        if (
            provenance.get("schema")
            != "ztare.subscription_dispatch_provenance.v1"
            or provenance.get("receipt_sha256") != content_hash(provenance_core)
            or provenance.get("role") != "external_science_reviewer"
            or provenance.get("agent_id") != row.get("reviewer_ref")
            or provenance.get("transport_agent_id") != row.get("reviewer_ref")
            or provenance.get("runtime") != call.get("runtime")
            or provenance.get("model") != call.get("model")
            or provenance.get("prompt_sha256") != raw_sha(prompt_text)
            or provenance.get("stdout_sha256") != raw_sha(stdout_text)
            or provenance.get("stderr_sha256") != raw_sha(stderr_text)
            or provenance.get("result_sha256")
            != raw_sha(
                f"{int(call.get('returncode', -1))}\n{stdout_text}\n{stderr_text}"
            )
            or provenance.get("returncode") != call.get("returncode")
            or provenance.get("reservation_id") != reservation_id
            or provenance.get("reservation_action_id") != action_id
            or provenance.get("reservation_phase") != "interpretation"
        ):
            raise ValueError("external science review transport provenance is invalid")
        if len(reserves) != 1 or len(terminals) != 1 or stops:
            raise ValueError("external science review execution has invalid budget lifecycle")
        reserved = dict(reserves[0].get("resources") or {})
        if (
            reserves[0].get("phase") != "interpretation"
            or int(reserved.get("provider_calls", 0)) < 1
            or int(reserved.get("agent_turns", 0)) < 1
        ):
            raise ValueError("external science review reservation is invalid")
        charged = int(call.get("provider_call_charge", 1)) >= 1
        terminal = terminals[0]
        if charged:
            actual = dict(terminal.get("actual_resources") or {})
            if (
                terminal.get("event_type") != "reservation_committed"
                or int(actual.get("provider_calls", 0)) < 1
                or int(actual.get("agent_turns", 0)) < 1
            ):
                raise ValueError("external science review call lacks a budget commit")
            if provenance.get("charged_reservation") is not True:
                raise ValueError("charged external science review lost transport authority")
        elif terminal.get("event_type") != "reservation_released":
            raise ValueError("provider-free review failure was not released")
        elif provenance.get("charged_reservation") is not False:
            raise ValueError("provider-free review failure was marked as charged")
    elif outcome == "reviewer_transport_unavailable":
        if role_call_ref or provenance_ref or not dispatch_ref or not reservation_id:
            raise ValueError("interrupted review execution has invalid evidence shape")
        dispatch_path = _resolve_artifact_ref(
            dispatch_ref,
            attempt_dir=directory,
            repo_root=_repo_root(),
            label="review execution interrupted owned_dispatch",
        )
        expected_parent = (
            directory / "agent_calls" / "external_science_reviewer"
        ).resolve()
        dispatch = _validate_interrupted_owned_dispatch(
            dispatch_path, expected_parent=expected_parent
        )
        if len(reserves) != 1 or len(terminals) != 1 or stops:
            raise ValueError("interrupted review has an invalid budget lifecycle")
        actual = dict(terminals[0].get("actual_resources") or {})
        if (
            reserves[0].get("phase") != "interpretation"
            or terminals[0].get("event_type") != "reservation_committed"
            or int(actual.get("provider_calls", 0)) < 1
            or int(actual.get("agent_turns", 0)) < 1
        ):
            raise ValueError("interrupted owned dispatch was not conservatively charged")
    elif outcome == "reviewer_budget_unavailable":
        if role_call_ref or dispatch_ref or provenance_ref or reservation_id:
            raise ValueError("budget-unavailable review cannot claim a dispatch")
        if reserves or terminals or len(stops) != 1:
            raise ValueError("budget-unavailable review lacks a canonical stop receipt")
        receipt = stops[0].get("receipt")
        if (
            not isinstance(receipt, Mapping)
            or receipt.get("attempt_id") != directory.name
            or not str(receipt.get("reason") or "").startswith(
                ("blocked_before_action:", "hard_cap_reached:")
            )
        ):
            raise ValueError("budget-unavailable review stop receipt is invalid")
    else:
        raise ValueError("external science review execution outcome is invalid")
    if expected_role_call_ref is not None and dict(role_call_ref or {}) != dict(expected_role_call_ref):
        raise ValueError("external science request changed its executed role call")
    return {
        "execution": row,
        "request_core": dict(request_core),
        "events": events,
        "call": call,
        "dispatch": dispatch,
        "provenance": provenance,
    }


def _validate_review_execution_ref(
    ref: Any,
    *,
    directory: Path,
    expected_request_core_sha: str | None = None,
    expected_reviewer_ref: str | None = None,
    expected_prompt_digest: str | None = None,
    expected_role_call_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    path = _resolve_artifact_ref(
        ref,
        attempt_dir=directory,
        repo_root=_repo_root(),
        label="independent review execution",
    )
    if path.parent != directory or not path.name.startswith(
        "external_science_review_execution."
    ):
        raise ValueError("independent review execution escaped its canonical store")
    execution = read_json(path, None)
    if not isinstance(execution, Mapping):
        raise ValueError("independent review execution is malformed")
    return _validate_review_execution(
        directory,
        execution,
        expected_request_core_sha=expected_request_core_sha,
        expected_reviewer_ref=expected_reviewer_ref,
        expected_prompt_digest=expected_prompt_digest,
        expected_role_call_ref=expected_role_call_ref,
    )


def _validate_source_free_projection(
    projection: Mapping[str, Any], *, forbidden_values: tuple[str, ...]
) -> None:
    rendered = json.dumps(
        dict(projection), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).lower()

    projected_strings: list[str] = []

    def collect_strings(value: Any) -> None:
        if isinstance(value, str):
            projected_strings.append(value.lower())
        elif isinstance(value, Mapping):
            for item in value.values():
                collect_strings(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                collect_strings(item)

    collect_strings(projection)

    def whitespace_normalized(value: str) -> str:
        return " ".join(value.split())

    def compact_serialization(value: str) -> str:
        return re.sub(r"\s+", "", value)

    if (
        re.search(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", rendered)
        or ".lean" in rendered
        or _PATHLIKE_TOKEN.search(rendered)
    ):
        raise ValueError("independent review projection contains an audit identity")
    identities = {
        value.strip().lower()
        for value in forbidden_values
        if value.strip() and not _HEX64.fullmatch(value.strip().lower())
    }
    for identity in identities:
        normalized_identity = whitespace_normalized(identity)
        compact_identity = compact_serialization(identity)
        for projected in projected_strings:
            normalized_projected = whitespace_normalized(projected)
            compact_projected = compact_serialization(projected)
            if (
                normalized_identity
                and normalized_identity in normalized_projected
                or len(compact_identity) >= 8
                and compact_identity in compact_projected
            ):
                raise ValueError(
                    "independent review projection contains a bound source identity"
                )
        # Short identifiers must not escape merely because substring matching
        # would be noisy.  Match them as complete identifier tokens instead.
        if len(identity) < 8 and re.search(
            rf"(?<![A-Za-z0-9_.-]){re.escape(identity)}(?![A-Za-z0-9_.-])",
            rendered,
        ):
            raise ValueError(
                "independent review projection contains a bound source identity"
            )


def _validate_review_call(
    ref: Any,
    *,
    execution_ref: Any,
    directory: Path,
    repo: Path,
    expected_prompt: str,
    request_core_sha: str,
    statement_sha: str,
    submitted_by: str,
    expected_reviewer_ref: str,
    expected_audit_context_sha: str,
    forbidden_values: tuple[str, ...],
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    call_path = _resolve_artifact_ref(
        ref,
        attempt_dir=directory,
        repo_root=repo,
        label="independent review",
    )
    call = read_json(call_path, None)
    if not isinstance(call, Mapping):
        raise ValueError("independent review durable call is malformed")
    prompt_path = _companion_path(call_path, ".prompt.txt")
    result_path = _companion_path(call_path, ".result.json")
    schema_path = _companion_path(call_path, ".schema.json")
    if not prompt_path.is_file() or not result_path.is_file() or not schema_path.is_file():
        raise ValueError("independent review durable call is incomplete")
    prompt = prompt_path.read_text(encoding="utf-8")
    result_text = result_path.read_text(encoding="utf-8")
    schema = read_json(schema_path, None)
    if (
        call.get("schema") != "leanmill.frontier_subscription_role_call.v1"
        or call.get("role") != "external_science_reviewer"
        or call.get("returncode") != 0
        or type(call.get("provider_call_charge")) is not int
        or call.get("provider_call_charge") < 1
        or prompt != expected_prompt
        or call.get("prompt_digest") != content_hash({"prompt": prompt})
        or call.get("result_digest") != content_hash({"result": result_text})
        or not isinstance(schema, Mapping)
        or call.get("output_schema_digest") != content_hash(dict(schema))
        or dict(schema) != external_science_review_output_schema()
    ):
        raise ValueError("independent review durable call provenance is invalid")
    execution = _validate_review_execution_ref(
        execution_ref,
        directory=directory,
        expected_request_core_sha=request_core_sha,
        expected_reviewer_ref=expected_reviewer_ref,
        expected_prompt_digest=content_hash({"prompt": expected_prompt}),
        expected_role_call_ref=(ref if isinstance(ref, Mapping) else None),
    )
    if (
        execution["execution"].get("outcome") != "review_completed"
        or execution.get("call") != call
    ):
        raise ValueError("independent review lacks a completed execution receipt")
    try:
        review = json.loads(result_text)
    except json.JSONDecodeError as exc:
        raise ValueError("independent review result is not JSON") from exc
    review = _exact_fields(review, _REVIEW_FIELDS, "independent review")
    projection = _exact_fields(
        review.get("semantic_projection"),
        _SEMANTIC_PROJECTION_FIELDS,
        "independent review semantic projection",
    )
    reviewer = _text(call.get("agent_id"), "independent review agent_id")
    if (
        review.get("schema") != EXTERNAL_REVIEW_SCHEMA
        or reviewer != expected_reviewer_ref
        or review.get("author_ref") != expected_reviewer_ref
        or reviewer == submitted_by
        or review.get("decision") not in {"admit_for_resume_context", "reject"}
        or review.get("scope")
        != "resume_context_only_no_objective_or_closure_credit"
        or review.get("reviewed_request_core_sha256") != request_core_sha
        or review.get("formal_statement_sha256") != statement_sha
        or review.get("reviewed_audit_context_sha256")
        != expected_audit_context_sha
        or review.get("finite_witness_relevance") not in {
            "statement_reviewed_against_preserved_witness",
            "not_established",
        }
        or review.get("claim_boundary_acknowledged") is not True
        or projection.get("schema") != EXTERNAL_SEMANTIC_PROJECTION_SCHEMA
        or projection.get("claim_boundary")
        != "resume_context_only_pending_campaign_owned_discharge"
    ):
        raise ValueError("independent review provenance or binding is invalid")
    for field in (
        "result_shape",
        "abstract_summary",
        "conclusion_shape",
        "next_discriminator",
    ):
        value = _text(projection.get(field), f"semantic_projection.{field}")
        if len(value) > 1200:
            raise ValueError(f"semantic_projection.{field} exceeds its schema bound")
    for field in ("hypothesis_shape", "open_residuals"):
        values = projection.get(field)
        if (
            not isinstance(values, list)
            or not 1 <= len(values) <= 12
            or any(
                not isinstance(item, str)
                or not item.strip()
                or item != item.strip()
                or len(item) > 1200
                for item in values
            )
        ):
            raise ValueError(f"semantic_projection.{field} must be a non-empty string array")
    _validate_source_free_projection(projection, forbidden_values=forbidden_values)
    return call, review, projection


def _request_path(directory: Path, digest: str) -> Path:
    return directory / f"external_science_recovery_request.{digest[:16]}.json"


def _admission_path(directory: Path, digest: str) -> Path:
    return directory / f"external_science_resume_admission.{digest[:16]}.json"


def _resume_path(directory: Path, digest: str) -> Path:
    return directory / f"external_science_resume_context.{digest[:16]}.json"


def _validate_request(
    directory: Path,
    request: Mapping[str, Any],
    *,
    repo: Path,
    require_run_digest: bool,
    require_current_lineage: bool = True,
) -> dict[str, Any]:
    row = _exact_fields(request, _REQUEST_FIELDS, "external science request")
    if row.get("schema") != EXTERNAL_SCIENCE_REQUEST_SCHEMA:
        raise ValueError("external science request has the wrong schema")
    _content_bound(row, "request_sha256", "external science request")
    if _text(row.get("attempt_id"), "attempt_id") != directory.name:
        raise ValueError("external science request targets another attempt")
    run = _validated_run(directory)
    run_digest = _sha(run.get("run_digest"), "run.run_digest")
    _sha(row.get("run_digest"), "request.run_digest")
    if require_run_digest and row.get("run_digest") != run_digest:
        raise ValueError("external science request does not match the current run")

    blueprint = FrontierTheoryBlueprint.from_json(read_json(directory / "blueprint.json", {}))
    context = load_formal_theory_context(directory / "formal_context.json")
    context_hash = _text(row.get("context_hash"), "context_hash")
    context_epoch = row.get("context_epoch")
    if (
        type(context_epoch) is not int
        or context_epoch < 0
        or context_epoch != _current_context_epoch(run)
        or context_hash != context.context_hash
        or context_hash != run.get("context_hash")
    ):
        raise ValueError("external science request targets another context epoch")

    packet = _campaign_packet_for_request(
        directory,
        blueprint_id=blueprint.blueprint_id,
        context_hash=context_hash,
        expected_packet_digest=_text(
            row.get("campaign_packet_digest"), "campaign_packet_digest"
        ),
    )
    campaign_id = _text(row.get("campaign_id"), "campaign_id")
    if campaign_id != packet.get("campaign_id"):
        raise ValueError("external science request targets another campaign")

    lineage_id = _text(row.get("lineage_id"), "lineage_id")
    program = _current_programs_by_lineage(run).get(lineage_id)
    theory_program_id = _text(row.get("theory_program_id"), "theory_program_id")
    presentation = row.get("reviewed_presentation_formula_ids")
    if not isinstance(presentation, list) or not presentation or any(
        not isinstance(item, str) or not item for item in presentation
    ):
        raise ValueError("reviewed presentation IDs must be a non-empty string array")
    if require_current_lineage and (
        program is None
        or theory_program_id != program.program_id
        or program.campaign_id != campaign_id
        or program.context_hash != context_hash
        or program.context_epoch != context_epoch
        or tuple(presentation) != program.presentation_formula_ids
    ):
        raise ValueError("external science request is not bound to the current lineage")

    witness = _exact_fields(
        row.get("finite_witness"),
        {"model_id", "model_table_sha256"},
        "finite witness",
    )
    model_id = _text(witness.get("model_id"), "finite witness.model_id")
    models = {item.model_id: item for item in context.universe.models}
    model_record = models.get(model_id)
    model_digest = _sha(
        witness.get("model_table_sha256"), "finite witness.model_table_sha256"
    )
    if (
        model_record is None
        or model_digest != content_hash(model_record.model.to_json())
        or model_id not in context.extent_model_ids(presentation)
    ):
        raise ValueError("finite witness does not replay the reviewed presentation")

    evidence, target, statement, closure, parity = _formal_evidence(
        row.get("formal_artifact"), directory=directory, repo=repo
    )
    statement_sha = content_hash({"formal_statement": statement})
    literature_path = _resolve_artifact_ref(
        row.get("literature_audit"),
        attempt_dir=directory,
        repo_root=repo,
        label="literature audit",
    )
    if literature_path.stat().st_size == 0:
        raise ValueError("literature audit must be non-empty")

    submitted_by = _text(row.get("submitted_by"), "submitted_by")
    reviewer_ref = _text(row.get("reviewer_ref"), "reviewer_ref")
    if reviewer_ref == submitted_by:
        raise ValueError("independent reviewer must differ from the recovery submitter")
    request_core = {
        key: value
        for key, value in row.items()
        if key
        not in {
            "independent_review",
            "independent_review_execution",
            "request_sha256",
        }
    }
    source_path = _resolve_artifact_ref(
        evidence.get("source"),
        attempt_dir=directory,
        repo_root=repo,
        label="formal evidence.source",
    )
    mapping_audit = _mapping_audit_context(
        context=context,
        reviewed_presentation_formula_ids=list(presentation),
        source_text=source_path.read_text(encoding="utf-8"),
        theorem_target=target,
        formal_statement=statement,
    )
    prompt = external_science_review_prompt(
        request_core_sha256=content_hash(request_core),
        formal_statement=statement,
        formal_statement_sha256=statement_sha,
        reviewed_presentation_formula_ids=list(presentation),
        anonymous_witness=model_record.model.to_json(),
        submitted_by=submitted_by,
        reviewer_ref=reviewer_ref,
        mapping_audit_context=mapping_audit,
    )
    source_ref = evidence.get("source") or {}
    artifact_paths = tuple(
        str(value or "")
        for value in (
            source_ref.get("path"),
            (row.get("formal_artifact") or {}).get("path"),
            (row.get("literature_audit") or {}).get("path"),
            (evidence.get("closure_certificate") or {}).get("path"),
            (evidence.get("kernel_parity") or {}).get("path"),
        )
    )
    artifact_identities = tuple(
        identity
        for value in artifact_paths
        if value
        for identity in (value, Path(value).name, Path(value).stem)
        if identity and (identity != Path(value).stem or len(identity) >= 8)
    )
    declaration_names = tuple(
        name for name, _start, _end in decl_spans(source_path.read_text(encoding="utf-8"))
        if name
    )
    target_namespace = target.rsplit(".", 1)[0] if "." in target else ""
    forbidden_values = (
        model_id,
        target,
        target.rsplit(".", 1)[-1],
        target_namespace,
        statement,
        json.dumps(
            model_record.model.to_json(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
        *artifact_identities,
        model_digest,
        statement_sha,
        str(evidence.get("evidence_sha256") or ""),
        str((row.get("literature_audit") or {}).get("sha256") or ""),
        submitted_by,
        reviewer_ref,
        *tuple(presentation),
        *declaration_names,
    )
    review_call, review, projection = _validate_review_call(
        row.get("independent_review"),
        execution_ref=row.get("independent_review_execution"),
        directory=directory,
        repo=repo,
        expected_prompt=prompt,
        request_core_sha=content_hash(request_core),
        statement_sha=statement_sha,
        submitted_by=submitted_by,
        expected_reviewer_ref=reviewer_ref,
        expected_audit_context_sha=str(mapping_audit["audit_context_sha256"]),
        forbidden_values=forbidden_values,
    )
    return {
        "request": dict(row),
        "run": run,
        "campaign_id": campaign_id,
        "context_hash": context_hash,
        "context_epoch": context_epoch,
        "lineage_id": lineage_id,
        "theory_program_id": theory_program_id,
        "program": program,
        "presentation": list(presentation),
        "model_id": model_id,
        "model_digest": model_digest,
        "formal_evidence": evidence,
        "target": target,
        "statement": statement,
        "statement_sha": statement_sha,
        "mapping_audit": mapping_audit,
        "closure": closure,
        "parity": parity,
        "review_call": review_call,
        "review": review,
        "projection": dict(projection),
    }


def _admission_core(validated: Mapping[str, Any]) -> dict[str, Any]:
    request = validated["request"]
    evidence = validated["formal_evidence"]
    review_ref = request.get("independent_review") or {}
    execution_ref = request.get("independent_review_execution") or {}
    literature_ref = request.get("literature_audit") or {}
    projection = dict(validated["projection"])
    return {
        "schema": EXTERNAL_SCIENCE_ADMISSION_SCHEMA,
        "request_sha256": str(request["request_sha256"]),
        "attempt_id": str(request["attempt_id"]),
        "campaign_id": str(validated["campaign_id"]),
        "campaign_packet_digest": str(request["campaign_packet_digest"]),
        "run_digest": str(request["run_digest"]),
        "context_hash": str(validated["context_hash"]),
        "context_epoch": int(validated["context_epoch"]),
        "lineage_id": str(validated["lineage_id"]),
        "theory_program_id": str(validated["theory_program_id"]),
        "reviewed_presentation_formula_ids": list(validated["presentation"]),
        "finite_witness_model_id": str(validated["model_id"]),
        "theorem_target": str(validated["target"]),
        "formal_statement": str(validated["statement"]),
        "formal_statement_sha256": str(validated["statement_sha"]),
        "semantic_projection": projection,
        "semantic_projection_sha256": content_hash(projection),
        "evidence_bindings": {
            "finite_model_table_sha256": str(validated["model_digest"]),
            "formal_evidence_sha256": str(evidence["evidence_sha256"]),
            "closure_certificate_record_sha256": content_hash(validated["closure"]),
            "kernel_parity_record_sha256": content_hash(validated["parity"]),
            "literature_audit_sha256": str(literature_ref.get("sha256") or ""),
            "independent_review_call_sha256": str(review_ref.get("sha256") or ""),
            "independent_review_execution_sha256": str(
                execution_ref.get("sha256") or ""
            ),
            "mapping_audit_context_sha256": str(
                validated["mapping_audit"]["audit_context_sha256"]
            ),
        },
        "reviewer_ref": str(validated["review_call"].get("agent_id") or ""),
        "authority": _AUTHORITY,
        "outer_objective_credit": _NO_CREDIT,
        "campaign_closure": _FORBIDDEN,
        "theory_task_discharge": _FORBIDDEN,
        "post_freeze_interpretation_identity": "distinct_not_interchangeable",
        "source_identity_visibility": "admission_audit_only",
    }


def admit_external_science_recovery(
    attempt_dir: str | Path,
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    _attempt_lease_token: Any = None,
) -> dict[str, Any]:
    """Validate and persist one resume-only external-science admission."""

    directory = Path(attempt_dir).resolve()
    if _attempt_lease_token is None:
        with _attempt_lease(directory, "external_science_admission") as lease:
            return admit_external_science_recovery(
                directory,
                request,
                repo_root=repo_root,
                _attempt_lease_token=lease,
            )
    repo = _repo_root() if repo_root is None else Path(repo_root).resolve()
    validated = _validate_request(
        directory, request, repo=repo, require_run_digest=True
    )
    if (
        validated["review"].get("decision") != "admit_for_resume_context"
        or validated["review"].get("finite_witness_relevance")
        != "statement_reviewed_against_preserved_witness"
    ):
        raise ValueError("external science review did not authorize admission")
    core = _admission_core(validated)
    admission = {**core, "admission_sha256": content_hash(core)}
    request_path = _request_path(directory, str(request["request_sha256"]))
    prior_request = read_json(request_path, None)
    if isinstance(prior_request, Mapping) and dict(prior_request) != dict(request):
        raise ValueError("external science request conflicts with persisted evidence")
    if prior_request is None:
        write_json_atomic(request_path, dict(request))
    request_core_sha = content_hash(
        {
            key: value
            for key, value in request.items()
            if key
            not in {
                "independent_review",
                "independent_review_execution",
                "request_sha256",
            }
        }
    )
    _persist_review_supersession(
        directory,
        request_core_sha256=request_core_sha,
        replacement_request_sha256=str(request["request_sha256"]),
    )
    path = _admission_path(directory, admission["admission_sha256"])
    prior = read_json(path, None)
    if isinstance(prior, Mapping) and dict(prior) != admission:
        raise ValueError("external science admission conflicts with persisted evidence")
    if prior is None:
        write_json_atomic(path, admission)
    from ztare.common.schema_routes import append_schema_route_event

    append_schema_route_event(
        directory,
        schema_id=EXTERNAL_SCIENCE_ADMISSION_SCHEMA,
        event="admitted",
        join_values={
            "context_hash": admission["context_hash"],
            "admission_sha256": admission["admission_sha256"],
        },
        payload={"request_sha256": admission["request_sha256"]},
    )
    return admission


def _negative_disposition_path(directory: Path, digest: str) -> Path:
    return directory / f"external_science_negative_disposition.{digest[:16]}.json"


def _review_supersession_path(directory: Path, review_subject_sha256: str) -> Path:
    return directory / (
        f"external_science_review_supersession.{review_subject_sha256[:16]}.json"
    )


_REVIEW_SUBJECT_FIELDS = {
    "attempt_id",
    "campaign_id",
    "context_hash",
    "context_epoch",
    "lineage_id",
    "theory_program_id",
    "reviewed_presentation_formula_ids",
    "finite_witness",
    "formal_artifact",
    "literature_audit",
}


def _review_subject_sha(request_core: Mapping[str, Any]) -> str:
    """Identify the scientific review subject independently of retry state."""

    if set(request_core) != _REQUEST_CORE_FIELDS:
        raise ValueError("external science review subject has a malformed request core")
    return content_hash(
        {key: request_core[key] for key in sorted(_REVIEW_SUBJECT_FIELDS)}
    )


def _unavailability_request_core_sha(
    directory: Path, disposition: Mapping[str, Any]
) -> str:
    if disposition.get("outcome") not in {
        "reviewer_budget_unavailable",
        "reviewer_transport_unavailable",
    }:
        return ""
    execution_sha = _sha(
        disposition.get("audit_binding_sha256"), "review unavailability execution"
    )
    execution = read_json(_review_execution_path(directory, execution_sha), None)
    if not isinstance(execution, Mapping):
        raise ValueError("reviewer unavailability lost its execution evidence")
    validated = _validate_review_execution(directory, execution)
    return str(validated["execution"]["request_core_sha256"])


def _unavailability_review_subject_sha(
    directory: Path, disposition: Mapping[str, Any]
) -> str:
    request_core_sha = _unavailability_request_core_sha(directory, disposition)
    if not request_core_sha:
        return ""
    request_core = read_json(
        _review_request_core_path(directory, request_core_sha), None
    )
    if not isinstance(request_core, Mapping):
        raise ValueError("reviewer unavailability lost its request core")
    return _review_subject_sha(request_core)


def external_science_negative_disposition_is_superseded(
    attempt_dir: str | Path, disposition: Mapping[str, Any]
) -> bool:
    directory = Path(attempt_dir).resolve()
    review_subject_sha = _unavailability_review_subject_sha(
        directory, disposition
    )
    if not review_subject_sha:
        return False
    row = read_json(
        _review_supersession_path(directory, review_subject_sha), None
    )
    if not isinstance(row, Mapping):
        return False
    core = {key: value for key, value in row.items() if key != "receipt_sha256"}
    if (
        row.get("schema") != EXTERNAL_SCIENCE_REVIEW_SUPERSESSION_SCHEMA
        or row.get("review_subject_sha256") != review_subject_sha
        or row.get("receipt_sha256") != content_hash(core)
        or disposition.get("receipt_sha256")
        not in (row.get("superseded_disposition_sha256s") or ())
    ):
        raise ValueError("external science review supersession is malformed")
    request_sha = _sha(
        row.get("replacement_request_sha256"),
        "review supersession replacement request",
    )
    request = read_json(_request_path(directory, request_sha), None)
    if not isinstance(request, Mapping) or request.get("request_sha256") != request_sha:
        raise ValueError("external science review supersession lost its reviewed request")
    replacement_core = {
        key: value
        for key, value in request.items()
        if key
        not in {
            "independent_review",
            "independent_review_execution",
            "request_sha256",
        }
    }
    if _review_subject_sha(replacement_core) != review_subject_sha:
        raise ValueError("external science review supersession changed review subject")
    return True


def _persist_review_supersession(
    directory: Path,
    *,
    request_core_sha256: str,
    replacement_request_sha256: str,
) -> None:
    replacement_core = read_json(
        _review_request_core_path(directory, request_core_sha256), None
    )
    if not isinstance(replacement_core, Mapping):
        raise ValueError("review supersession lost its replacement request core")
    review_subject_sha = _review_subject_sha(replacement_core)
    superseded: list[str] = []
    for path in sorted(directory.glob("external_science_negative_disposition.*.json")):
        disposition = read_json(path, None)
        if not isinstance(disposition, Mapping):
            continue
        if (
            _unavailability_review_subject_sha(directory, disposition)
            == review_subject_sha
        ):
            superseded.append(
                _sha(disposition.get("receipt_sha256"), "superseded disposition")
            )
    if not superseded:
        return
    core = {
        "schema": EXTERNAL_SCIENCE_REVIEW_SUPERSESSION_SCHEMA,
        "review_subject_sha256": _sha(
            review_subject_sha, "review supersession subject"
        ),
        "replacement_request_core_sha256": _sha(
            request_core_sha256, "review supersession replacement request core"
        ),
        "replacement_request_sha256": _sha(
            replacement_request_sha256, "review supersession replacement request"
        ),
        "superseded_disposition_sha256s": sorted(set(superseded)),
    }
    row = {**core, "receipt_sha256": content_hash(core)}
    path = _review_supersession_path(directory, review_subject_sha)
    prior = read_json(path, None)
    if isinstance(prior, Mapping) and dict(prior) != row:
        raise ValueError("external science review supersession changed identity")
    if prior is None:
        write_json_atomic(path, row)


def reconcile_external_science_review_supersessions(
    attempt_dir: str | Path,
) -> tuple[dict[str, Any], ...]:
    """Materialize retry supersessions for admissions created by older runners."""

    directory = Path(attempt_dir).resolve()
    for path in sorted(directory.glob("external_science_resume_admission.*.json")):
        admission = read_json(path, None)
        if not isinstance(admission, Mapping):
            continue
        if admission.get("schema") != EXTERNAL_SCIENCE_ADMISSION_SCHEMA:
            continue
        admission_core = {
            key: value for key, value in admission.items()
            if key != "admission_sha256"
        }
        if admission.get("admission_sha256") != content_hash(admission_core):
            raise ValueError("external science admission changed before supersession repair")
        request_sha = _sha(
            admission.get("request_sha256"), "admission reviewed request"
        )
        request = read_json(_request_path(directory, request_sha), None)
        if not isinstance(request, Mapping) or request.get("request_sha256") != request_sha:
            raise ValueError("external science admission lost its reviewed request")
        request_core = {
            key: value
            for key, value in request.items()
            if key
            not in {
                "independent_review",
                "independent_review_execution",
                "request_sha256",
            }
        }
        request_core_sha = content_hash(request_core)
        persisted_core = read_json(
            _review_request_core_path(directory, request_core_sha), None
        )
        if persisted_core != request_core:
            raise ValueError("external science admission lost its frozen request core")
        _persist_review_supersession(
            directory,
            request_core_sha256=request_core_sha,
            replacement_request_sha256=request_sha,
        )
    rows = []
    for path in sorted(directory.glob("external_science_review_supersession.*.json")):
        row = read_json(path, None)
        if isinstance(row, Mapping):
            rows.append(dict(row))
    return tuple(rows)


def _negative_disposition_core(
    *,
    outcome: str,
    context_hash: str,
    context_epoch: int,
    lineage_id: str,
    program: TheoryProgram,
    presentation: list[str],
    audit_binding_sha256: str,
    audit_binding_kind: str,
    semantic_projection: Mapping[str, Any],
) -> dict[str, Any]:
    projection = dict(semantic_projection)
    rejected = outcome == "review_rejected"
    return {
        "schema": EXTERNAL_SCIENCE_NEGATIVE_DISPOSITION_SCHEMA,
        "outcome": outcome,
        "context_hash": context_hash,
        "context_epoch": int(context_epoch),
        "lineage_id": lineage_id,
        "theory_program_id": program.program_id,
        "reviewed_presentation_formula_ids": list(presentation),
        "audit_binding_sha256": audit_binding_sha256,
        "audit_binding_kind": audit_binding_kind,
        "semantic_projection": projection,
        "semantic_projection_sha256": content_hash(projection),
        "projection_authority": (
            "independent_reviewer" if rejected else "none_reviewer_unavailable"
        ),
        "typed_residual": (
            "external_science_mapping_not_admitted"
            if rejected
            else outcome
        ),
        "next_action": (
            "revise_or_replace_the_mapping_before_requesting_admission"
            if rejected
            else "retry_or_reroute_the_independent_reviewer"
        ),
        "authority": _AUTHORITY,
        "outer_objective_credit": _NO_CREDIT,
        "campaign_closure": _FORBIDDEN,
        "theory_task_discharge": _FORBIDDEN,
        "source_identity_visibility": "audit_only_excluded_from_navigation_projection",
    }


def _persist_negative_disposition(
    directory: Path, core: Mapping[str, Any]
) -> dict[str, Any]:
    disposition = {**dict(core), "receipt_sha256": content_hash(dict(core))}
    path = _negative_disposition_path(directory, disposition["receipt_sha256"])
    prior = read_json(path, None)
    if isinstance(prior, Mapping) and dict(prior) != disposition:
        raise ValueError("external science negative disposition changed identity")
    if prior is None:
        write_json_atomic(path, disposition)
    from ztare.common.schema_routes import append_schema_route_event

    append_schema_route_event(
        directory,
        schema_id=EXTERNAL_SCIENCE_NEGATIVE_DISPOSITION_SCHEMA,
        event="materialized",
        join_values={
            "context_hash": disposition["context_hash"],
            "receipt_sha256": disposition["receipt_sha256"],
        },
        payload={"outcome": disposition["outcome"]},
    )
    return disposition


def record_external_science_review_rejection(
    attempt_dir: str | Path,
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    _attempt_lease_token: Any = None,
) -> dict[str, Any]:
    """Persist a reviewed non-admission as source-free navigation input."""

    directory = Path(attempt_dir).resolve()
    if _attempt_lease_token is None:
        with _attempt_lease(directory, "external_science_review_rejection") as lease:
            return record_external_science_review_rejection(
                directory,
                request,
                repo_root=repo_root,
                _attempt_lease_token=lease,
            )
    repo = _repo_root() if repo_root is None else Path(repo_root).resolve()
    validated = _validate_request(
        directory, request, repo=repo, require_run_digest=True
    )
    if (
        validated["review"].get("decision") == "admit_for_resume_context"
        and validated["review"].get("finite_witness_relevance")
        == "statement_reviewed_against_preserved_witness"
    ):
        raise ValueError("an admitting review cannot become a negative disposition")
    request_path = _request_path(directory, str(request["request_sha256"]))
    prior_request = read_json(request_path, None)
    if isinstance(prior_request, Mapping) and dict(prior_request) != dict(request):
        raise ValueError("external science request conflicts with persisted evidence")
    if prior_request is None:
        write_json_atomic(request_path, dict(request))
    request_core_sha = content_hash(
        {
            key: value
            for key, value in request.items()
            if key
            not in {
                "independent_review",
                "independent_review_execution",
                "request_sha256",
            }
        }
    )
    _persist_review_supersession(
        directory,
        request_core_sha256=request_core_sha,
        replacement_request_sha256=str(request["request_sha256"]),
    )
    core = _negative_disposition_core(
        outcome="review_rejected",
        context_hash=str(validated["context_hash"]),
        context_epoch=int(validated["context_epoch"]),
        lineage_id=str(validated["lineage_id"]),
        program=validated["program"],
        presentation=list(validated["presentation"]),
        audit_binding_sha256=str(request["request_sha256"]),
        audit_binding_kind="reviewed_request",
        semantic_projection=validated["projection"],
    )
    return _persist_negative_disposition(directory, core)


def record_external_science_reviewer_unavailability(
    attempt_dir: str | Path,
    *,
    review_execution: Mapping[str, Any],
    _attempt_lease_token: Any = None,
) -> dict[str, Any]:
    """Persist an evidence-bound reviewer outage without a scientific verdict."""

    directory = Path(attempt_dir).resolve()
    if _attempt_lease_token is None:
        with _attempt_lease(directory, "external_science_review_unavailable") as lease:
            return record_external_science_reviewer_unavailability(
                directory,
                review_execution=review_execution,
                _attempt_lease_token=lease,
            )
    evidence = _validate_review_execution_ref(
        review_execution,
        directory=directory,
    )
    execution = evidence["execution"]
    request_core = evidence["request_core"]
    outcome = str(execution.get("outcome") or "")
    if outcome not in {
        "reviewer_budget_unavailable",
        "reviewer_transport_unavailable",
    }:
        raise ValueError("unknown external science reviewer unavailability")
    run = _validated_run(directory)
    lineage_id = str(request_core.get("lineage_id") or "")
    program = _current_programs_by_lineage(run).get(lineage_id)
    presentation = request_core.get("reviewed_presentation_formula_ids")
    if (
        request_core.get("attempt_id") != directory.name
        or request_core.get("run_digest") != run.get("run_digest")
        or request_core.get("context_hash") != run.get("context_hash")
        or request_core.get("context_epoch") != _current_context_epoch(run)
        or program is None
        or program.program_id != request_core.get("theory_program_id")
        or not isinstance(presentation, list)
        or tuple(presentation) != program.presentation_formula_ids
        or request_core.get("reviewer_ref") != execution.get("reviewer_ref")
    ):
        raise ValueError("reviewer unavailability targets stale campaign state")
    core = _negative_disposition_core(
        outcome=outcome,
        context_hash=str(request_core["context_hash"]),
        context_epoch=int(request_core["context_epoch"]),
        lineage_id=lineage_id,
        program=program,
        presentation=list(presentation),
        audit_binding_sha256=str(execution["execution_sha256"]),
        audit_binding_kind="review_execution_evidence",
        semantic_projection={},
    )
    return _persist_negative_disposition(directory, core)


def validate_external_science_negative_disposition(
    attempt_dir: str | Path,
    disposition: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Revalidate one typed negative recovery input against current lineage state."""

    directory = Path(attempt_dir).resolve()
    _exact_fields(
        disposition,
        _NEGATIVE_DISPOSITION_FIELDS,
        "external science negative disposition",
    )
    if disposition.get("schema") != EXTERNAL_SCIENCE_NEGATIVE_DISPOSITION_SCHEMA:
        raise ValueError("external science negative disposition has the wrong schema")
    _content_bound(
        disposition, "receipt_sha256", "external science negative disposition"
    )
    if read_json(
        _negative_disposition_path(directory, str(disposition["receipt_sha256"])),
        None,
    ) != dict(disposition):
        raise ValueError("external science negative disposition is not persisted")
    run = _validated_run(directory)
    lineage_id = str(disposition.get("lineage_id") or "")
    program = _current_programs_by_lineage(run).get(lineage_id)
    if (
        disposition.get("context_hash") != run.get("context_hash")
        or disposition.get("context_epoch") != _current_context_epoch(run)
        or program is None
        or disposition.get("theory_program_id") != program.program_id
        or tuple(disposition.get("reviewed_presentation_formula_ids") or ())
        != program.presentation_formula_ids
        or disposition.get("authority") != _AUTHORITY
        or disposition.get("outer_objective_credit") != _NO_CREDIT
        or disposition.get("campaign_closure") != _FORBIDDEN
        or disposition.get("theory_task_discharge") != _FORBIDDEN
    ):
        raise ValueError("external science negative disposition is stale or widened")
    outcome = str(disposition.get("outcome") or "")
    if outcome == "review_rejected":
        request = read_json(
            _request_path(
                directory,
                _sha(disposition.get("audit_binding_sha256"), "audit binding"),
            ),
            None,
        )
        if not isinstance(request, Mapping):
            raise ValueError("review rejection lost its reviewed request")
        validated = _validate_request(
            directory, request, repo=_repo_root(), require_run_digest=False
        )
        expected = _negative_disposition_core(
            outcome="review_rejected",
            context_hash=str(validated["context_hash"]),
            context_epoch=int(validated["context_epoch"]),
            lineage_id=str(validated["lineage_id"]),
            program=validated["program"],
            presentation=list(validated["presentation"]),
            audit_binding_sha256=str(request["request_sha256"]),
            audit_binding_kind="reviewed_request",
            semantic_projection=validated["projection"],
        )
        if (
            validated["review"].get("decision") == "admit_for_resume_context"
            and validated["review"].get("finite_witness_relevance")
            == "statement_reviewed_against_preserved_witness"
        ):
            raise ValueError("admitting review was mislabeled as rejected")
        actual = {
            key: value for key, value in disposition.items()
            if key != "receipt_sha256"
        }
        if expected != actual:
            raise ValueError("review rejection changed after validation")
    elif outcome in {
        "reviewer_budget_unavailable",
        "reviewer_transport_unavailable",
    }:
        if external_science_negative_disposition_is_superseded(
            directory, disposition
        ):
            raise ValueError("reviewer unavailability was superseded by a later review")
        execution_sha = _sha(
            disposition.get("audit_binding_sha256"), "audit binding"
        )
        execution = read_json(_review_execution_path(directory, execution_sha), None)
        if not isinstance(execution, Mapping):
            raise ValueError("reviewer unavailability lost its execution evidence")
        evidence = _validate_review_execution(directory, execution)
        request_core = evidence["request_core"]
        if (
            evidence["execution"].get("outcome") != outcome
            or request_core.get("lineage_id") != lineage_id
            or request_core.get("theory_program_id") != program.program_id
            or request_core.get("context_hash") != disposition.get("context_hash")
            or request_core.get("context_epoch") != disposition.get("context_epoch")
        ):
            raise ValueError("reviewer unavailability execution targets another branch")
        expected = _negative_disposition_core(
            outcome=outcome,
            context_hash=str(disposition["context_hash"]),
            context_epoch=int(disposition["context_epoch"]),
            lineage_id=lineage_id,
            program=program,
            presentation=list(program.presentation_formula_ids),
            audit_binding_sha256=execution_sha,
            audit_binding_kind="review_execution_evidence",
            semantic_projection={},
        )
        actual = {
            key: value for key, value in disposition.items()
            if key != "receipt_sha256"
        }
        if expected != actual:
            raise ValueError("reviewer unavailability changed after validation")
    else:
        raise ValueError("external science negative outcome is invalid")
    return run


def mark_external_science_negative_disposition_first_fire(
    attempt_dir: str | Path,
    disposition: Mapping[str, Any],
) -> None:
    directory = Path(attempt_dir)
    run = validate_external_science_negative_disposition(directory, disposition)
    navigation = run.get("navigation")
    delivered = (
        navigation.get("external_science_negative_dispositions")
        if isinstance(navigation, Mapping)
        else None
    )
    if not any(
        isinstance(row, Mapping) and dict(row) == dict(disposition)
        for row in delivered or ()
    ):
        raise ValueError(
            "external science negative disposition was not written to navigation"
        )
    checkpoint = read_json(directory / "navigation_epoch_checkpoint.json", None)
    if not isinstance(checkpoint, Mapping) or not any(
        isinstance(row, Mapping)
        and row.get("decision") == "external_science_negative_disposition"
        and row.get("receipt") == disposition
        for row in checkpoint.get("trace") or ()
    ):
        raise ValueError(
            "external science negative disposition was not written to the checkpoint"
        )
    from ztare.common.schema_routes import append_schema_route_event

    append_schema_route_event(
        directory,
        schema_id=EXTERNAL_SCIENCE_NEGATIVE_DISPOSITION_SCHEMA,
        event="first_fire",
        join_values={
            "context_hash": disposition["context_hash"],
            "receipt_sha256": disposition["receipt_sha256"],
        },
        payload={"outcome": disposition["outcome"]},
    )


def _revalidate_current_binding(
    directory: Path,
    admission: Mapping[str, Any],
    *,
    require_run_digest: bool,
    require_current_lineage: bool = True,
) -> Mapping[str, Any]:
    _exact_fields(admission, _ADMISSION_FIELDS, "external science admission")
    if admission.get("schema") != EXTERNAL_SCIENCE_ADMISSION_SCHEMA:
        raise ValueError("resume context requires an external science admission")
    _content_bound(admission, "admission_sha256", "external science admission")
    digest = str(admission["admission_sha256"])
    if read_json(_admission_path(directory, digest), None) != dict(admission):
        raise ValueError("external science admission does not match persisted evidence")
    request = read_json(
        _request_path(directory, _sha(admission.get("request_sha256"), "request_sha256")),
        None,
    )
    if not isinstance(request, Mapping):
        raise ValueError("external science admission lost its frozen request")
    validated = _validate_request(
        directory,
        request,
        repo=_repo_root(),
        require_run_digest=require_run_digest,
        require_current_lineage=require_current_lineage,
    )
    if (
        validated["review"].get("decision") != "admit_for_resume_context"
        or validated["review"].get("finite_witness_relevance")
        != "statement_reviewed_against_preserved_witness"
    ):
        raise ValueError("persisted admission is not backed by an admitting review")
    expected = _admission_core(validated)
    actual = {key: value for key, value in admission.items() if key != "admission_sha256"}
    if expected != actual:
        raise ValueError("external science admission no longer matches governed evidence")
    if (
        admission.get("authority") != _AUTHORITY
        or admission.get("outer_objective_credit") != _NO_CREDIT
        or admission.get("campaign_closure") != _FORBIDDEN
        or admission.get("theory_task_discharge") != _FORBIDDEN
    ):
        raise ValueError("external science admission authority was widened")
    return validated["run"]


def _safe_resume_context(admission: Mapping[str, Any]) -> dict[str, Any]:
    safe_core = {
        "schema": EXTERNAL_SCIENCE_RESUME_CONTEXT_SCHEMA,
        "context_hash": str(admission["context_hash"]),
        "context_epoch": int(admission["context_epoch"]),
        "lineage_id": str(admission["lineage_id"]),
        "theory_program_id": str(admission["theory_program_id"]),
        "reviewed_presentation_formula_ids": list(
            admission["reviewed_presentation_formula_ids"]
        ),
        "formal_statement_sha256": str(admission["formal_statement_sha256"]),
        "semantic_projection": dict(admission["semantic_projection"]),
        "semantic_projection_sha256": str(admission["semantic_projection_sha256"]),
        "typed_residual": "campaign_task_discharge_required_for_recovered_result",
        "authority": _AUTHORITY,
        "outer_objective_credit": _NO_CREDIT,
        "campaign_closure": _FORBIDDEN,
        "theory_task_discharge": _FORBIDDEN,
        "visibility": "reviewed_semantics_and_campaign_branch_only",
    }
    resume_id = "external-resume-context:" + content_hash(safe_core)
    return {
        **safe_core,
        "resume_context_id": resume_id,
        "receipt_sha256": content_hash({**safe_core, "resume_context_id": resume_id}),
    }


def materialize_external_science_resume_context(
    attempt_dir: str | Path,
    admission: Mapping[str, Any],
    *,
    _attempt_lease_token: Any = None,
) -> dict[str, Any]:
    """Persist the source-free, lineage-scoped navigator projection."""

    directory = Path(attempt_dir).resolve()
    if _attempt_lease_token is None:
        with _attempt_lease(directory, "external_science_projection") as lease:
            return materialize_external_science_resume_context(
                directory, admission, _attempt_lease_token=lease
            )
    _revalidate_current_binding(directory, admission, require_run_digest=True)
    resume = _safe_resume_context(admission)
    admission_sha = str(admission["admission_sha256"])
    path = _resume_path(directory, admission_sha)
    prior = read_json(path, None)
    if isinstance(prior, Mapping) and dict(prior) != resume:
        raise ValueError("external science resume context changed after admission")
    if prior is None:
        write_json_atomic(path, resume)
    from ztare.common.schema_routes import append_schema_route_event

    joins = {"context_hash": resume["context_hash"], "admission_sha256": admission_sha}
    append_schema_route_event(
        directory,
        schema_id=EXTERNAL_SCIENCE_ADMISSION_SCHEMA,
        event="projected",
        join_values=joins,
        payload={"resume_context_id": resume["resume_context_id"]},
    )
    append_schema_route_event(
        directory,
        schema_id=EXTERNAL_SCIENCE_RESUME_CONTEXT_SCHEMA,
        event="materialized",
        join_values=joins,
        payload={"resume_context_id": resume["resume_context_id"]},
    )
    return resume


def validate_delivered_external_science_resume_context(
    attempt_dir: str | Path,
    *,
    admission: Mapping[str, Any],
    resume_context: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Recheck an already delivered projection against current lineage state."""

    directory = Path(attempt_dir).resolve()
    run = _revalidate_current_binding(
        directory, admission, require_run_digest=False
    )
    expected = _safe_resume_context(admission)
    if dict(resume_context) != expected:
        raise ValueError("delivered external science context changed after review")
    if read_json(_resume_path(directory, str(admission["admission_sha256"])), None) != expected:
        raise ValueError("delivered external science context lost its materialized artifact")
    return run


def validate_consumed_external_science_resume_context(
    attempt_dir: str | Path,
    *,
    admission: Mapping[str, Any],
    resume_context: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Replay a one-shot context after its reviewed lineage has advanced.

    First fire consumes the admission's navigation authority.  Later lifecycle
    checks therefore replay the frozen evidence and projection, while the
    current-lineage check remains mandatory at materialization and delivery.
    """

    directory = Path(attempt_dir).resolve()
    run = _revalidate_current_binding(
        directory,
        admission,
        require_run_digest=False,
        require_current_lineage=False,
    )
    expected = _safe_resume_context(admission)
    if dict(resume_context) != expected:
        raise ValueError("consumed external science context changed after first fire")
    if read_json(_resume_path(directory, str(admission["admission_sha256"])), None) != expected:
        raise ValueError("consumed external science context lost its materialized artifact")
    return run


def mark_external_science_resume_context_first_fire(
    attempt_dir: str | Path,
    *,
    admission_sha256: str,
    resume_context: Mapping[str, Any],
) -> None:
    """Runner-only route event after checkpoint insertion into navigation."""

    directory = Path(attempt_dir)
    resume_core = {
        key: value for key, value in resume_context.items() if key != "receipt_sha256"
    }
    admission_digest = _sha(admission_sha256, "admission_sha256")
    admission = read_json(_admission_path(directory, admission_digest), None)
    if not isinstance(admission, Mapping):
        raise ValueError("external science admission is unavailable at first fire")
    run = validate_delivered_external_science_resume_context(
        directory,
        admission=admission,
        resume_context=resume_context,
    )
    navigation = run.get("navigation")
    delivered = (
        navigation.get("external_science_resume_context_by_lineage")
        if isinstance(navigation, Mapping)
        else None
    )
    checkpoint = read_json(directory / "navigation_epoch_checkpoint.json", None)
    if (
        resume_context.get("schema") != EXTERNAL_SCIENCE_RESUME_CONTEXT_SCHEMA
        or resume_context.get("receipt_sha256") != content_hash(resume_core)
        or read_json(
            _resume_path(directory, admission_digest),
            None,
        )
        != dict(resume_context)
        or not isinstance(delivered, Mapping)
        or delivered.get(resume_context.get("lineage_id")) != resume_context
        or not isinstance(checkpoint, Mapping)
        or not any(
            isinstance(row, Mapping)
            and row.get("decision") == "external_science_resume_context"
            and row.get("receipt") == resume_context
            for row in checkpoint.get("trace") or ()
        )
    ):
        raise ValueError("external science resume context does not replay at first fire")
    from ztare.common.schema_routes import append_schema_route_event

    append_schema_route_event(
        directory,
        schema_id=EXTERNAL_SCIENCE_RESUME_CONTEXT_SCHEMA,
        event="first_fire",
        join_values={
            "context_hash": resume_context["context_hash"],
            "admission_sha256": admission_sha256,
        },
        payload={"resume_context_id": resume_context["resume_context_id"]},
    )


__all__ = [
    "EXTERNAL_REVIEW_SCHEMA",
    "EXTERNAL_SEMANTIC_PROJECTION_SCHEMA",
    "EXTERNAL_SCIENCE_ADMISSION_SCHEMA",
    "EXTERNAL_SCIENCE_FORMAL_EVIDENCE_SCHEMA",
    "EXTERNAL_SCIENCE_NEGATIVE_DISPOSITION_SCHEMA",
    "EXTERNAL_SCIENCE_REQUEST_SCHEMA",
    "EXTERNAL_SCIENCE_RESUME_CONTEXT_SCHEMA",
    "admit_external_science_recovery",
    "external_science_review_output_schema",
    "external_science_review_prompt",
    "mark_external_science_resume_context_first_fire",
    "mark_external_science_negative_disposition_first_fire",
    "materialize_external_science_formal_evidence",
    "materialize_external_science_resume_context",
    "reconcile_external_science_review_supersessions",
    "record_external_science_review_rejection",
    "record_external_science_reviewer_unavailability",
    "validate_delivered_external_science_resume_context",
    "validate_consumed_external_science_resume_context",
    "validate_external_science_negative_disposition",
]
