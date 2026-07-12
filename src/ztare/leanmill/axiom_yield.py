"""Matched shadow evaluation for quarantined AxiomPacks.

This module adapts AxiomPack proof-task outcomes to the repository's existing
information-yield and compression-progress primitives.  It does not execute a
prover and it cannot grant proof credit.  Callers supply content-bound outcomes
from two matched arms: the current theory and the current theory plus a
candidate pack. Manifest signatures freeze task bytes and split assignments;
deployment must establish pre-discovery timing through an append-only log.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Callable, Hashable, Iterable, Mapping, Sequence

from ztare.research_signals import (
    CompressionObservation,
    IterationSignal,
    evaluate_compression_progress,
    evaluate_information_yield,
    price_experiment,
)
from ztare.leanmill.formal_verification_provider import (
    attach_signature,
    build_payload,
    sha256_ref,
    verify_payload_signature,
)


SHADOW_TASK_SCHEMA = "leanmill.axiom_shadow_task.v1"
SHADOW_TASK_MANIFEST_SCHEMA = "leanmill.axiom_shadow_task_manifest.v1"
SHADOW_ATTEMPT_SCHEMA = "leanmill.axiom_shadow_attempt.v1"
SHADOW_YIELD_SCHEMA = "leanmill.axiom_pack_shadow_yield.v1"
CANDIDATE_DEPENDENCY_SCHEMA = "leanmill.axiom_candidate_dependency.v1"
MIN_PROMOTION_EVAL_TASKS = 2


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_sha256_ref(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


def _is_digest(value: object) -> bool:
    if not isinstance(value, str):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


@dataclass(frozen=True)
class ShadowTask:
    task_id: str
    input_digest: str
    budget_units: int
    budget_kind: str = "tokens"
    split: str = "eval"
    schema: str = SHADOW_TASK_SCHEMA

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def content_digest(self) -> str:
        return _digest(self.to_json())

    @classmethod
    def from_json(cls, row: Mapping[str, Any]) -> "ShadowTask":
        return cls(
            task_id=str(row.get("task_id") or ""),
            input_digest=str(row.get("input_digest") or ""),
            budget_units=int(row.get("budget_units") or 0),
            budget_kind=str(row.get("budget_kind") or "tokens"),
            split=str(row.get("split") or "eval"),
            schema=str(row.get("schema") or SHADOW_TASK_SCHEMA),
        )


@dataclass(frozen=True)
class ShadowAttempt:
    task_id: str
    task_digest: str
    arm: str
    budget_units: int
    budget_kind: str
    status: str
    admission_digest: str = ""
    environment_ref: str = ""
    transcript_ref: str = ""
    kernel_checked: bool = False
    proof_digest: str = ""
    proof_size: int | None = None
    used_axiom_hashes: tuple[str, ...] = field(default_factory=tuple)
    novel_residue_ids: tuple[str, ...] = field(default_factory=tuple)
    failure_class: str = ""
    verification_payload: dict[str, Any] = field(default_factory=dict)
    schema: str = SHADOW_ATTEMPT_SCHEMA

    def to_json(self) -> dict[str, Any]:
        row = asdict(self)
        row["used_axiom_hashes"] = list(self.used_axiom_hashes)
        row["novel_residue_ids"] = list(self.novel_residue_ids)
        return row

    @classmethod
    def from_json(cls, row: Mapping[str, Any]) -> "ShadowAttempt":
        proof_size = row.get("proof_size")
        return cls(
            task_id=str(row.get("task_id") or ""),
            task_digest=str(row.get("task_digest") or ""),
            arm=str(row.get("arm") or ""),
            budget_units=int(row.get("budget_units") or 0),
            budget_kind=str(row.get("budget_kind") or ""),
            status=str(row.get("status") or ""),
            admission_digest=str(row.get("admission_digest") or ""),
            environment_ref=str(row.get("environment_ref") or ""),
            transcript_ref=str(row.get("transcript_ref") or ""),
            kernel_checked=bool(row.get("kernel_checked")),
            proof_digest=str(row.get("proof_digest") or ""),
            proof_size=int(proof_size) if proof_size is not None else None,
            used_axiom_hashes=tuple(str(x) for x in row.get("used_axiom_hashes") or []),
            novel_residue_ids=tuple(str(x) for x in row.get("novel_residue_ids") or []),
            failure_class=str(row.get("failure_class") or ""),
            verification_payload=(
                dict(row.get("verification_payload"))
                if isinstance(row.get("verification_payload"), Mapping)
                else {}
            ),
            schema=str(row.get("schema") or SHADOW_ATTEMPT_SCHEMA),
        )


def _task(value: ShadowTask | Mapping[str, Any]) -> ShadowTask:
    return value if isinstance(value, ShadowTask) else ShadowTask.from_json(value)


def _attempt(value: ShadowAttempt | Mapping[str, Any]) -> ShadowAttempt:
    return value if isinstance(value, ShadowAttempt) else ShadowAttempt.from_json(value)


def _task_shape_failures(task: ShadowTask) -> list[str]:
    failures: list[str] = []
    if task.schema != SHADOW_TASK_SCHEMA:
        failures.append("schema")
    if not task.task_id:
        failures.append("task_id")
    if not _is_sha256_ref(task.input_digest):
        failures.append("input_digest")
    if task.budget_units < 1:
        failures.append("budget_units")
    if not task.budget_kind:
        failures.append("budget_kind")
    if task.split not in {"discovery", "eval"}:
        failures.append("split")
    return failures


def build_shadow_task_manifest(
    *,
    tasks: Iterable[ShadowTask | Mapping[str, Any]],
    base_theory_digest: str,
    admission_digests: Mapping[str, str],
    private_key_pem: str,
    verifier_ref: str,
    manifest_evidence_ref: str,
) -> dict[str, Any]:
    """Freeze task/split/admission bindings before a candidate pack exists.

    The later arm receipts bind the candidate pack. Append-only publication
    timing is a deployment responsibility, not something a signature proves.
    """

    if not verifier_ref:
        raise ValueError("verifier_ref is required")
    for name, value in (("base_theory_digest", base_theory_digest),):
        if not _is_digest(value):
            raise ValueError(f"{name} must be a canonical digest")
    if not _is_sha256_ref(manifest_evidence_ref):
        raise ValueError("manifest_evidence_ref must be a sha256 content reference")
    normalized = sorted((_task(row) for row in tasks), key=lambda row: row.task_id)
    if not normalized:
        raise ValueError("task manifest requires at least one task")
    seen: set[str] = set()
    for task in normalized:
        failures = _task_shape_failures(task)
        if failures:
            raise ValueError(f"malformed shadow task {task.task_id!r}: {failures}")
        if task.task_id in seen:
            raise ValueError(f"duplicate shadow task id: {task.task_id}")
        seen.add(task.task_id)
    if len({task.input_digest for task in normalized}) != len(normalized):
        raise ValueError("shadow tasks must have distinct input digests")
    normalized_admissions = {
        str(task_id): str(digest) for task_id, digest in sorted(admission_digests.items())
    }
    if set(normalized_admissions) != seen:
        raise ValueError("admission_digests must match the frozen task ids exactly")
    if not all(_is_digest(value) for value in normalized_admissions.values()):
        raise ValueError("every admission digest must be canonical")
    if len(set(normalized_admissions.values())) != len(normalized_admissions):
        raise ValueError("shadow tasks must have distinct admission digests")
    core = {
        "schema": SHADOW_TASK_MANIFEST_SCHEMA,
        "frozen": True,
        "base_theory_digest": base_theory_digest,
        "admission_digests": normalized_admissions,
        "tasks": [task.to_json() for task in normalized],
    }
    manifest_digest = _digest(core)
    payload = build_payload(
        formal_system="lean",
        property_class="math",
        verdict="verified",
        subject_ref=f"axiom-shadow-manifest:{manifest_digest}",
        subject_text=json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
        claim_ref="axiom-shadow-task-splits:frozen",
        certificate_ref=manifest_evidence_ref,
        certificate_text=manifest_digest,
        verifier_ref=verifier_ref,
        verification_summary="Shadow task bytes, split assignments, and per-task admissions were frozen.",
        faithfulness_refs=[
            *[normalized_admissions[task.task_id] for task in normalized],
            *[task.input_digest for task in normalized],
        ],
        checker_evidence_refs=[manifest_evidence_ref],
        input_refs=[
            base_theory_digest,
            *[normalized_admissions[task.task_id] for task in normalized],
        ],
        output_refs=[manifest_digest],
        extra_metadata={
            "purpose": "axiom_pack_shadow_task_manifest",
            "manifest_digest": manifest_digest,
            "manifest": core,
        },
    )
    attach_signature(payload, private_key_pem)
    return payload


def _validate_shadow_task_manifest(
    manifest: Mapping[str, Any],
    *,
    base_theory_digest: str,
    trusted_public_key_pem: str | None,
) -> tuple[list[ShadowTask], str, dict[str, str], list[str]]:
    failures: list[str] = []
    metadata = manifest.get("metadata") if isinstance(manifest.get("metadata"), Mapping) else {}
    raw_core = metadata.get("manifest")
    if not isinstance(raw_core, Mapping):
        return [], "", {}, ["manifest_shape"]
    expected_core_keys = {
        "schema", "frozen", "base_theory_digest", "admission_digests", "tasks",
    }
    if set(raw_core) != expected_core_keys:
        failures.append("manifest_fields")
    raw_tasks = raw_core.get("tasks")
    tasks: list[ShadowTask] = []
    if not isinstance(raw_tasks, list):
        failures.append("tasks_shape")
    else:
        expected_task_keys = {
            "task_id", "input_digest", "budget_units", "budget_kind", "split", "schema",
        }
        seen: set[str] = set()
        for index, raw_task in enumerate(raw_tasks):
            if not isinstance(raw_task, Mapping) or set(raw_task) != expected_task_keys:
                failures.append(f"task.{index}.fields")
                continue
            try:
                task = ShadowTask.from_json(raw_task)
            except (TypeError, ValueError):
                failures.append(f"task.{index}.shape")
                continue
            failures.extend(f"task.{index}.{item}" for item in _task_shape_failures(task))
            if task.task_id in seen:
                failures.append(f"task.{index}.duplicate_id")
            seen.add(task.task_id)
            tasks.append(task)
    if raw_core.get("schema") != SHADOW_TASK_MANIFEST_SCHEMA:
        failures.append("schema")
    if raw_core.get("frozen") is not True:
        failures.append("frozen")
    if raw_core.get("base_theory_digest") != base_theory_digest:
        failures.append("base_theory_digest")
    raw_admissions = raw_core.get("admission_digests")
    admission_digests = (
        {str(key): str(value) for key, value in raw_admissions.items()}
        if isinstance(raw_admissions, Mapping)
        else {}
    )
    if set(admission_digests) != {task.task_id for task in tasks}:
        failures.append("admission_task_ids")
    if not admission_digests or not all(_is_digest(value) for value in admission_digests.values()):
        failures.append("admission_digests")
    if len({task.input_digest for task in tasks}) != len(tasks):
        failures.append("duplicate_task_inputs")
    if len(set(admission_digests.values())) != len(admission_digests):
        failures.append("duplicate_admissions")
    try:
        manifest_digest = _digest(dict(raw_core))
    except (TypeError, ValueError):
        manifest_digest = ""
        failures.append("manifest_digest")
    if metadata.get("purpose") != "axiom_pack_shadow_task_manifest":
        failures.append("purpose")
    if metadata.get("manifest_digest") != manifest_digest:
        failures.append("metadata_manifest_digest")
    expected_provider = {
        "schema_version": "formal-verification-provider/v1",
        "provider": "leanmill",
        "formal_system": "lean",
        "property_class": "math",
        "verdict": "verified",
        "subject_ref": f"axiom-shadow-manifest:{manifest_digest}",
        "subject_digest": manifest_digest,
        "claim_ref": "axiom-shadow-task-splits:frozen",
        "certificate_digest": sha256_ref(manifest_digest),
        "faithfulness_refs": [
            *[admission_digests.get(task.task_id, "") for task in tasks],
            *[task.input_digest for task in tasks],
        ],
        "input_refs": [
            base_theory_digest,
            *[admission_digests.get(task.task_id, "") for task in tasks],
        ],
        "output_refs": [manifest_digest],
    }
    failures.extend(
        f"provider_{name}" for name, value in expected_provider.items() if manifest.get(name) != value
    )
    evidence_refs = manifest.get("checker_evidence_refs")
    if (
        not isinstance(evidence_refs, list)
        or len(evidence_refs) != 1
        or not _is_sha256_ref(evidence_refs[0])
        or manifest.get("certificate_ref") != evidence_refs[0]
    ):
        failures.append("manifest_evidence_ref")
    if not trusted_public_key_pem:
        failures.append("trusted_manifest_key_missing")
    else:
        try:
            signature_ok = verify_payload_signature(dict(manifest), trusted_public_key_pem)
        except (TypeError, ValueError):
            signature_ok = False
        if not signature_ok:
            failures.append("provider_signature")
    return tasks, manifest_digest, admission_digests, failures


def verify_shadow_task_manifest(
    manifest: Mapping[str, Any],
    *,
    base_theory_digest: str,
    trusted_public_key_pem: str | None,
) -> tuple[bool, list[str]]:
    """Verify manifest authority and its exact base/task/admissions bindings."""

    _tasks, _digest_value, _admissions, failures = _validate_shadow_task_manifest(
        manifest,
        base_theory_digest=base_theory_digest,
        trusted_public_key_pem=trusted_public_key_pem,
    )
    return not failures, failures


def evaluate_candidate_dependency(
    *,
    task_digest: str,
    proof_digest: str,
    pack_digest: str,
    base_theory_digest: str,
    candidate_axiom_hashes: Iterable[str],
    replay_fn: Callable[[tuple[str, ...]], bool],
) -> dict[str, Any]:
    """Attribute a checked treatment proof through exact pack ablations.

    ``replay_fn`` receives the candidate hashes retained in the conditional
    theory.  A usable receipt requires the full pack to compile, the empty
    pack to fail, and every replay to complete. Leave-one-out failures identify
    indispensable candidates; an empty indispensable set is allowed when
    several laws are redundant.
    """

    candidates = tuple(sorted({str(value) for value in candidate_axiom_hashes}))
    if not candidates:
        raise ValueError("candidate dependency requires at least one axiom hash")
    replays: list[dict[str, Any]] = []

    def run(label: str, retained: tuple[str, ...]) -> bool:
        try:
            compiled = replay_fn(retained) is True
            error = ""
        except Exception as exc:  # noqa: BLE001 - a failed replay is recorded
            compiled = False
            error = f"{type(exc).__name__}: {exc}"[:300]
        replays.append({
            "label": label,
            "retained_axiom_hashes": list(retained),
            "compiled": compiled,
            "error": error,
        })
        return compiled

    full_compiles = run("full_pack", candidates)
    empty_compiles = run("whole_pack_removed", ())
    indispensable = []
    for candidate in candidates:
        retained = tuple(value for value in candidates if value != candidate)
        if not run(f"without:{candidate}", retained):
            indispensable.append(candidate)
    replay_complete = not any(row["error"] for row in replays)
    core = {
        "schema": CANDIDATE_DEPENDENCY_SCHEMA,
        "status": (
            "pass"
            if full_compiles and not empty_compiles and replay_complete
            else "inconclusive"
            if not replay_complete
            else "fail"
        ),
        "task_digest": task_digest,
        "proof_digest": proof_digest,
        "pack_digest": pack_digest,
        "base_theory_digest": base_theory_digest,
        "candidate_axiom_hashes": list(candidates),
        "pack_required": full_compiles and not empty_compiles,
        "replay_complete": replay_complete,
        "indispensable_axiom_hashes": indispensable,
        "replays": replays,
    }
    return {**core, "receipt_digest": _digest(core)}


def verify_candidate_dependency_receipt(
    receipt: Mapping[str, Any],
    *,
    task_digest: str,
    proof_digest: str,
    pack_digest: str,
    base_theory_digest: str,
    candidate_axiom_hashes: Iterable[str],
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    unsigned = dict(receipt)
    expected_digest = unsigned.pop("receipt_digest", None)
    if expected_digest != _digest(unsigned):
        failures.append("receipt_digest")
    expected_candidates = sorted({str(value) for value in candidate_axiom_hashes})
    expected = {
        "schema": CANDIDATE_DEPENDENCY_SCHEMA,
        "status": "pass",
        "task_digest": task_digest,
        "proof_digest": proof_digest,
        "pack_digest": pack_digest,
        "base_theory_digest": base_theory_digest,
        "candidate_axiom_hashes": expected_candidates,
        "pack_required": True,
        "replay_complete": True,
    }
    failures.extend(name for name, value in expected.items() if receipt.get(name) != value)
    indispensable = receipt.get("indispensable_axiom_hashes")
    if not isinstance(indispensable, list) or not set(indispensable) <= set(expected_candidates):
        failures.append("indispensable_axiom_hashes")
    replays = receipt.get("replays")
    expected_replays = [
        {
            "label": "full_pack",
            "retained_axiom_hashes": expected_candidates,
            "compiled": True,
        },
        {
            "label": "whole_pack_removed",
            "retained_axiom_hashes": [],
            "compiled": False,
        },
        *[
            {
                "label": f"without:{candidate}",
                "retained_axiom_hashes": [
                    value for value in expected_candidates if value != candidate
                ],
                "compiled": candidate not in set(indispensable or []),
            }
            for candidate in expected_candidates
        ],
    ]
    if not isinstance(replays, list) or len(replays) != len(expected_replays):
        failures.append("replay_count")
    else:
        for index, (actual, replay_expected) in enumerate(zip(replays, expected_replays)):
            if not isinstance(actual, Mapping):
                failures.append(f"replay.{index}.shape")
                continue
            for name, value in replay_expected.items():
                if actual.get(name) != value:
                    failures.append(f"replay.{index}.{name}")
            if actual.get("error") not in {"", None}:
                failures.append(f"replay.{index}.error")
    return not failures, failures


def _attempt_index(
    attempts: Iterable[ShadowAttempt | Mapping[str, Any]],
    *,
    arm: str,
    violations: list[dict[str, Any]],
) -> dict[str, ShadowAttempt]:
    out: dict[str, ShadowAttempt] = {}
    for raw in attempts:
        item = _attempt(raw)
        if item.task_id in out:
            violations.append({"type": "duplicate_attempt", "arm": arm, "task_id": item.task_id})
        out[item.task_id] = item
        if item.schema != SHADOW_ATTEMPT_SCHEMA:
            violations.append({"type": "attempt_schema", "arm": arm, "task_id": item.task_id})
        if item.arm != arm:
            violations.append({
                "type": "attempt_arm_mismatch",
                "expected": arm,
                "actual": item.arm,
                "task_id": item.task_id,
            })
        if item.status not in {"solved", "failed", "timeout"}:
            violations.append({"type": "attempt_status", "arm": arm, "task_id": item.task_id})
        if not _is_digest(item.admission_digest):
            violations.append({"type": "attempt_admission_digest", "arm": arm, "task_id": item.task_id})
        if not _is_sha256_ref(item.environment_ref):
            violations.append({"type": "attempt_environment_ref", "arm": arm, "task_id": item.task_id})
        if not _is_sha256_ref(item.transcript_ref):
            violations.append({"type": "attempt_transcript_ref", "arm": arm, "task_id": item.task_id})
        if item.status == "solved" and (
            not item.kernel_checked
            or not _is_sha256_ref(item.proof_digest)
            or not item.proof_size
            or item.proof_size < 1
        ):
            violations.append({
                "type": "uncertified_solve",
                "arm": arm,
                "task_id": item.task_id,
            })
        if item.status in {"failed", "timeout"} and (
            item.kernel_checked
            or item.proof_digest
            or item.proof_size is not None
            or item.used_axiom_hashes
            or not item.failure_class
        ):
            violations.append({
                "type": "malformed_unsolved_outcome",
                "arm": arm,
                "task_id": item.task_id,
            })
    return out


def _loop_decision(attempts: list[ShadowAttempt]) -> dict[str, Any]:
    history: list[IterationSignal] = []
    score = 0
    seen_residues: set[str] = set()
    for index, item in enumerate(attempts):
        improved = item.status == "solved"
        if improved:
            score += 1
        novel = tuple(x for x in item.novel_residue_ids if x not in seen_residues)
        seen_residues.update(novel)
        history.append(
            IterationSignal(
                iteration_index=index,
                score=score,
                weakest_point=item.failure_class,
                score_improved=improved,
                runtime_failure=item.status == "timeout",
                novel_attack_ids=novel,
                verified_axioms_added=len(item.used_axiom_hashes) if item.kernel_checked else 0,
                weakest_class=item.failure_class,
            )
        )
    decision = evaluate_information_yield(history)
    return {
        "canonical_engine": "ztare.validator.core.information_yield.evaluate_information_yield",
        "action": decision.action.value,
        "stagnant_window": decision.stagnant_window,
        "rationale": decision.rationale,
    }


def _attempt_outcome_core(
    *,
    task: ShadowTask,
    attempt: ShadowAttempt,
    task_manifest_digest: str,
    pack_digest: str,
    base_theory_digest: str,
    candidate_axiom_hashes: Iterable[str],
    dependency_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "task_digest": task.content_digest,
        "task_input_digest": task.input_digest,
        "task_manifest_digest": task_manifest_digest,
        "arm": attempt.arm,
        "status": attempt.status,
        "budget_units": attempt.budget_units,
        "budget_kind": attempt.budget_kind,
        "pack_digest": pack_digest,
        "base_theory_digest": base_theory_digest,
        "admission_digest": attempt.admission_digest,
        "environment_ref": attempt.environment_ref,
        "transcript_ref": attempt.transcript_ref,
        "kernel_checked": attempt.kernel_checked,
        "proof_digest": attempt.proof_digest,
        "proof_size": attempt.proof_size,
        "used_axiom_hashes": list(attempt.used_axiom_hashes),
        "novel_residue_ids": list(attempt.novel_residue_ids),
        "failure_class": attempt.failure_class,
        "allowed_axiom_hashes": sorted({str(value) for value in candidate_axiom_hashes}),
        "candidate_dependency": dict(dependency_receipt or {}),
    }


def build_shadow_attempt_verification(
    *,
    task: ShadowTask,
    attempt: ShadowAttempt,
    private_key_pem: str,
    verifier_ref: str,
    task_manifest_digest: str,
    pack_digest: str,
    base_theory_digest: str,
    candidate_axiom_hashes: Iterable[str],
    dependency_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Sign the observed outcome of one arm, including failures and timeouts."""

    if not verifier_ref:
        raise ValueError("verifier_ref is required")
    if attempt.task_id != task.task_id or attempt.task_digest != task.content_digest:
        raise ValueError("attempt must bind the exact shadow task")
    if attempt.arm not in {"baseline", "treatment"}:
        raise ValueError("attempt arm must be baseline or treatment")
    if attempt.budget_units != task.budget_units or attempt.budget_kind != task.budget_kind:
        raise ValueError("attempt budget must equal the frozen task budget")
    for name, value in (
        ("task_manifest_digest", task_manifest_digest),
        ("pack_digest", pack_digest),
        ("base_theory_digest", base_theory_digest),
        ("admission_digest", attempt.admission_digest),
    ):
        if not _is_digest(value):
            raise ValueError(f"{name} must be a canonical digest")
    for name, value in (
        ("environment_ref", attempt.environment_ref),
        ("transcript_ref", attempt.transcript_ref),
    ):
        if not _is_sha256_ref(value):
            raise ValueError(f"{name} must be a sha256 content reference")
    if attempt.status == "solved":
        if not attempt.kernel_checked or not _is_sha256_ref(attempt.proof_digest):
            raise ValueError("a solved attempt requires a kernel-checked proof digest")
        if attempt.proof_size is None or attempt.proof_size < 1:
            raise ValueError("a solved attempt requires a positive proof size")
    elif attempt.status in {"failed", "timeout"}:
        if (
            attempt.kernel_checked
            or attempt.proof_digest
            or attempt.proof_size is not None
            or attempt.used_axiom_hashes
            or not attempt.failure_class
        ):
            raise ValueError("an unsolved outcome must carry only a failure class")
    else:
        raise ValueError("attempt status must be solved, failed, or timeout")
    allowed = sorted({str(value) for value in candidate_axiom_hashes})
    dependency = dict(dependency_receipt or {})
    if attempt.arm == "treatment" and attempt.status == "solved":
        valid, failures = verify_candidate_dependency_receipt(
            dependency,
            task_digest=task.content_digest,
            proof_digest=attempt.proof_digest,
            pack_digest=pack_digest,
            base_theory_digest=base_theory_digest,
            candidate_axiom_hashes=allowed,
        )
        if not valid:
            raise ValueError(f"candidate dependency receipt failed: {failures}")
        indispensable = tuple(sorted(dependency.get("indispensable_axiom_hashes") or []))
        if tuple(sorted(attempt.used_axiom_hashes)) != indispensable:
            raise ValueError("used_axiom_hashes must equal the indispensable ablation result")
    elif attempt.used_axiom_hashes or dependency:
        raise ValueError("only a treatment solve can claim candidate dependency")
    outcome = _attempt_outcome_core(
        task=task,
        attempt=attempt,
        task_manifest_digest=task_manifest_digest,
        pack_digest=pack_digest,
        base_theory_digest=base_theory_digest,
        candidate_axiom_hashes=allowed,
        dependency_receipt=dependency,
    )
    certificate_text = json.dumps(
        outcome, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    payload = build_payload(
        formal_system="lean",
        property_class="math",
        verdict="verified",
        subject_ref=f"axiom-shadow-task:{task.content_digest}",
        subject_text=json.dumps(task.to_json(), sort_keys=True, separators=(",", ":"), ensure_ascii=True),
        claim_ref=f"axiom-shadow-outcome:{attempt.arm}:{attempt.status}:{task.task_id}",
        certificate_ref=attempt.transcript_ref,
        certificate_text=certificate_text,
        verifier_ref=verifier_ref,
        verification_summary="Shadow arm outcome was checked against the frozen task, admission, and budget.",
        faithfulness_refs=[task.input_digest, attempt.environment_ref, attempt.admission_digest],
        checker_evidence_refs=[
            attempt.transcript_ref,
            *([attempt.proof_digest] if attempt.status == "solved" else []),
        ],
        input_refs=[
            task.content_digest,
            task_manifest_digest,
            pack_digest,
            base_theory_digest,
            attempt.admission_digest,
            attempt.environment_ref,
        ],
        output_refs=[attempt.proof_digest] if attempt.status == "solved" else [],
        extra_metadata={
            "purpose": "axiom_pack_shadow_attempt",
            "outcome": outcome,
        },
    )
    attach_signature(payload, private_key_pem)
    return payload


def _verify_attempt(
    task: ShadowTask,
    attempt: ShadowAttempt,
    trusted_checker_public_key_pem: str | None,
    *,
    task_manifest_digest: str,
    admission_digest: str,
    pack_digest: str,
    base_theory_digest: str,
    candidate_axiom_hashes: Iterable[str],
) -> tuple[list[str], bool]:
    payload = attempt.verification_payload
    if not trusted_checker_public_key_pem:
        return ["trusted_shadow_checker_key_missing"], False
    if not payload:
        return ["shadow_attempt_verification_missing"], False
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
    outcome = metadata.get("outcome")
    if not isinstance(outcome, Mapping):
        outcome = {}
    dependency = outcome.get("candidate_dependency")
    if not isinstance(dependency, Mapping):
        dependency = {}
    expected_outcome = _attempt_outcome_core(
        task=task,
        attempt=attempt,
        task_manifest_digest=task_manifest_digest,
        pack_digest=pack_digest,
        base_theory_digest=base_theory_digest,
        candidate_axiom_hashes=candidate_axiom_hashes,
        dependency_receipt=dependency,
    )
    failures = [] if dict(outcome) == expected_outcome else ["provider_outcome_binding"]
    if metadata.get("purpose") != "axiom_pack_shadow_attempt":
        failures.append("provider_purpose")
    if attempt.admission_digest != admission_digest:
        failures.append("admission_digest")
    expected_provider_identity = {
        "schema_version": "formal-verification-provider/v1",
        "provider": "leanmill",
        "formal_system": "lean",
        "property_class": "math",
        "verdict": "verified",
    }
    failures.extend(
        f"provider_{name}"
        for name, value in expected_provider_identity.items()
        if payload.get(name) != value
    )
    if payload.get("subject_ref") != f"axiom-shadow-task:{task.content_digest}":
        failures.append("provider_subject_ref")
    if payload.get("subject_digest") != task.content_digest:
        failures.append("provider_subject_digest")
    if payload.get("claim_ref") != (
        f"axiom-shadow-outcome:{attempt.arm}:{attempt.status}:{task.task_id}"
    ):
        failures.append("provider_claim_ref")
    certificate_text = json.dumps(
        expected_outcome, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    if payload.get("certificate_ref") != attempt.transcript_ref:
        failures.append("provider_certificate_ref")
    if payload.get("certificate_digest") != sha256_ref(certificate_text):
        failures.append("provider_certificate_digest")
    expected_provider_refs = {
        "faithfulness_refs": [task.input_digest, attempt.environment_ref, attempt.admission_digest],
        "checker_evidence_refs": [
            attempt.transcript_ref,
            *([attempt.proof_digest] if attempt.status == "solved" else []),
        ],
        "input_refs": [
            task.content_digest,
            task_manifest_digest,
            pack_digest,
            base_theory_digest,
            attempt.admission_digest,
            attempt.environment_ref,
        ],
        "output_refs": [attempt.proof_digest] if attempt.status == "solved" else [],
    }
    failures.extend(
        f"provider_{name}" for name, value in expected_provider_refs.items() if payload.get(name) != value
    )
    try:
        signature_ok = verify_payload_signature(payload, trusted_checker_public_key_pem)
    except (TypeError, ValueError):
        signature_ok = False
    if not signature_ok:
        failures.append("provider_signature")
    dependency_verified = False
    if attempt.arm == "treatment" and attempt.status == "solved":
        dependency_verified, dependency_failures = verify_candidate_dependency_receipt(
            dependency,
            task_digest=task.content_digest,
            proof_digest=attempt.proof_digest,
            pack_digest=pack_digest,
            base_theory_digest=base_theory_digest,
            candidate_axiom_hashes=candidate_axiom_hashes,
        )
        failures.extend(f"candidate_dependency.{item}" for item in dependency_failures)
        if dependency_verified and sorted(attempt.used_axiom_hashes) != sorted(
            dependency.get("indispensable_axiom_hashes") or []
        ):
            failures.append("candidate_dependency.used_axiom_hashes")
            dependency_verified = False
    elif attempt.used_axiom_hashes or dependency:
        failures.append("unexpected_candidate_dependency")
    return failures, dependency_verified and not failures


def rank_shadow_tasks(
    *,
    committee: Sequence[Any],
    tasks: Iterable[ShadowTask | Mapping[str, Any]],
    predict: Callable[[Any, ShadowTask], Hashable],
    size_fn: Callable[[Any], int],
    previously_observed_task_ids: Iterable[str] = (),
    weights: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> dict[str, Any]:
    """Rank expensive shadow tasks through the canonical experiment pricer.

    The caller owns the committee, predictions, description length, and policy
    weights.  This adapter only binds those values to exact task digests.
    """

    if not committee:
        raise ValueError("experiment pricing requires a nonempty committee")
    if len(weights) != 3 or any(weight < 0 for weight in weights):
        raise ValueError("weights must be three nonnegative values")
    observed = {str(item) for item in previously_observed_task_ids}
    rows: list[dict[str, Any]] = []
    for raw in tasks:
        task = _task(raw)
        components = price_experiment(
            committee,
            lambda member, task=task: predict(member, task),
            size_fn,
            task.task_id not in observed,
        )
        score = components.score(*weights)
        rows.append({
            "task_id": task.task_id,
            "task_digest": task.content_digest,
            "score": score,
            "identification": components.identification,
            "compression_gain": components.compression_gain,
            "novelty": components.novelty,
        })
    rows.sort(key=lambda row: (-row["score"], row["task_digest"]))
    return {
        "schema": "leanmill.axiom_shadow_task_ranking.v1",
        "canonical_engine": "ztare.common.information_yield_pricing.price_experiment",
        "weights": {
            "identification": weights[0],
            "compression_gain": weights[1],
            "novelty": weights[2],
        },
        "ranked_tasks": rows,
    }


def evaluate_shadow_ab(
    *,
    pack_digest: str,
    base_theory_digest: str,
    allowed_axiom_hashes: Iterable[str],
    task_manifest: Mapping[str, Any],
    baseline_attempts: Iterable[ShadowAttempt | Mapping[str, Any]],
    treatment_attempts: Iterable[ShadowAttempt | Mapping[str, Any]],
    trusted_checker_public_key_pem: str | None,
    trusted_manifest_public_key_pem: str | None,
) -> dict[str, Any]:
    """Evaluate a content-bound, budget-matched shadow A/B.

    A positive result requires at least one kernel-checked treatment improvement
    with verified whole-pack dependency, no lost baseline solve, and at least
    two distinct eval tasks from a trusted frozen split manifest.
    """

    violations: list[dict[str, Any]] = []
    if (
        trusted_checker_public_key_pem
        and trusted_manifest_public_key_pem
        and trusted_checker_public_key_pem.strip() == trusted_manifest_public_key_pem.strip()
    ):
        violations.append({"type": "authority_role_collapse"})
    all_tasks, manifest_digest, admission_digests, manifest_failures = (
        _validate_shadow_task_manifest(
            task_manifest,
            base_theory_digest=base_theory_digest,
            trusted_public_key_pem=trusted_manifest_public_key_pem,
        )
    )
    violations.extend(
        {"type": f"task_manifest.{failure}"} for failure in manifest_failures
    )
    task_list = [task for task in all_tasks if task.split == "eval"]
    discovery = {task.task_id for task in all_tasks if task.split == "discovery"}
    task_by_id: dict[str, ShadowTask] = {}
    for task in task_list:
        if task.task_id in task_by_id:
            violations.append({"type": "duplicate_task", "task_id": task.task_id})
        task_by_id[task.task_id] = task
    if len(task_list) < MIN_PROMOTION_EVAL_TASKS:
        violations.append({
            "type": "insufficient_eval_tasks",
            "count": len(task_list),
            "minimum": MIN_PROMOTION_EVAL_TASKS,
        })

    baseline = _attempt_index(baseline_attempts, arm="baseline", violations=violations)
    treatment = _attempt_index(treatment_attempts, arm="treatment", violations=violations)
    transcript_owners: dict[str, str] = {}
    for arm, rows in (("baseline", baseline), ("treatment", treatment)):
        for task_id, attempt in rows.items():
            owner = f"{arm}:{task_id}"
            prior = transcript_owners.setdefault(attempt.transcript_ref, owner)
            if prior != owner:
                violations.append({
                    "type": "reused_transcript_ref",
                    "first": prior,
                    "second": owner,
                })
    expected_ids = set(task_by_id)
    for arm, rows in (("baseline", baseline), ("treatment", treatment)):
        missing = sorted(expected_ids - set(rows))
        extra = sorted(set(rows) - expected_ids)
        if missing:
            violations.append({"type": "missing_attempts", "arm": arm, "task_ids": missing})
        if extra:
            violations.append({"type": "unknown_attempts", "arm": arm, "task_ids": extra})

    allowed = {str(x) for x in allowed_axiom_hashes}
    paired: list[dict[str, Any]] = []
    attributable = 0
    regressions = 0
    proof_size_gain = 0
    compression_rows: list[dict[str, Any]] = []
    ordered_baseline: list[ShadowAttempt] = []
    ordered_treatment: list[ShadowAttempt] = []
    for task in task_list:
        left = baseline.get(task.task_id)
        right = treatment.get(task.task_id)
        if left is None or right is None:
            continue
        ordered_baseline.append(left)
        ordered_treatment.append(right)
        treatment_dependency_verified = False
        for arm, attempt in (("baseline", left), ("treatment", right)):
            if attempt.task_digest != task.content_digest:
                violations.append({"type": "task_digest_mismatch", "arm": arm, "task_id": task.task_id})
            if attempt.budget_units != task.budget_units or attempt.budget_kind != task.budget_kind:
                violations.append({"type": "budget_mismatch", "arm": arm, "task_id": task.task_id})
            attempt_failures, dependency_verified = _verify_attempt(
                task,
                attempt,
                trusted_checker_public_key_pem,
                task_manifest_digest=manifest_digest,
                admission_digest=admission_digests.get(task.task_id, ""),
                pack_digest=pack_digest,
                base_theory_digest=base_theory_digest,
                candidate_axiom_hashes=allowed,
            )
            if arm == "treatment":
                treatment_dependency_verified = dependency_verified
            for failure in attempt_failures:
                violations.append({
                    "type": failure,
                    "arm": arm,
                    "task_id": task.task_id,
                })
        if left.used_axiom_hashes:
            violations.append({"type": "baseline_used_candidate_axiom", "task_id": task.task_id})
        if left.admission_digest != right.admission_digest:
            violations.append({"type": "arm_admission_mismatch", "task_id": task.task_id})
        if left.environment_ref != right.environment_ref:
            violations.append({"type": "arm_environment_mismatch", "task_id": task.task_id})
        unknown_hashes = sorted(set(right.used_axiom_hashes) - allowed)
        if unknown_hashes:
            violations.append({
                "type": "unknown_axiom_hash",
                "task_id": task.task_id,
                "axiom_hashes": unknown_hashes,
            })

        baseline_solved = left.status == "solved"
        treatment_solved = right.status == "solved"
        treatment_only = treatment_solved and not baseline_solved
        shorter = bool(
            baseline_solved
            and treatment_solved
            and left.proof_size is not None
            and right.proof_size is not None
            and right.proof_size < left.proof_size
        )
        cites_pack = treatment_dependency_verified and not unknown_hashes
        attributed = (treatment_only or shorter) and cites_pack
        attributable += int(attributed)
        regressions += int(baseline_solved and not treatment_solved)
        if shorter and left.proof_size is not None and right.proof_size is not None:
            proof_size_gain += left.proof_size - right.proof_size
            compression = evaluate_compression_progress([
                CompressionObservation(0, float(left.proof_size), family=task.task_id),
                CompressionObservation(1, float(right.proof_size), novelty=cites_pack, family=task.task_id),
            ])
            compression_rows.append({
                "task_id": task.task_id,
                "recommendation": compression.recommendation,
                "best_complexity": compression.best_complexity,
                "latest_complexity": compression.latest_complexity,
                "compression_drop_count": compression.compression_drop_count,
            })
        paired.append({
            "task_id": task.task_id,
            "baseline_status": left.status,
            "treatment_status": right.status,
            "treatment_only_solve": treatment_only,
            "shorter_checked_proof": shorter,
            "cites_allowed_axiom": cites_pack,
            "pack_dependency_verified": treatment_dependency_verified,
            "attributable_improvement": attributed,
        })

    baseline_solved = sum(row.status == "solved" for row in ordered_baseline)
    treatment_solved = sum(row.status == "solved" for row in ordered_treatment)
    measured_positive = attributable > 0 and regressions == 0
    status = "pass" if not violations and measured_positive else "fail" if violations else "no_measured_gain"
    report_core = {
        "schema": SHADOW_YIELD_SCHEMA,
        "dimension": "downstream_yield",
        "status": status,
        "pack_digest": pack_digest,
        "base_theory_digest": base_theory_digest,
        "admission_digests": admission_digests,
        "task_manifest_digest": manifest_digest,
        "allowed_axiom_hashes": sorted(allowed),
        "discovery_task_ids": sorted(discovery),
        "task_count": len(task_list),
        "baseline_solved": baseline_solved,
        "treatment_solved": treatment_solved,
        "solve_delta": treatment_solved - baseline_solved,
        "attributable_improvements": attributable,
        "regressions": regressions,
        "proof_size_gain": proof_size_gain,
        "paired_results": paired,
        "compression": {
            "canonical_engine": "ztare.validator.core.compression_progress.evaluate_compression_progress",
            "rows": compression_rows,
        },
        "loop_control": {
            "baseline": _loop_decision(ordered_baseline),
            "treatment": _loop_decision(ordered_treatment),
        },
        "violations": violations,
        "task_manifest": dict(task_manifest),
        "tasks": [task.to_json() for task in task_list],
        "attempts": {
            "baseline": [item.to_json() for item in ordered_baseline],
            "treatment": [item.to_json() for item in ordered_treatment],
        },
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
        "can_feed_solver": False,
    }
    return {**report_core, "receipt_digest": _digest(report_core), "ok": status == "pass"}


def verify_shadow_yield_receipt(
    receipt: Mapping[str, Any],
    *,
    trusted_checker_public_key_pem: str | None,
    trusted_manifest_public_key_pem: str | None,
) -> bool:
    """Replay a shadow receipt and every embedded checker signature."""

    task_manifest = receipt.get("task_manifest")
    tasks = receipt.get("tasks")
    attempts = receipt.get("attempts")
    if (
        not isinstance(task_manifest, Mapping)
        or not isinstance(tasks, list)
        or not isinstance(attempts, Mapping)
    ):
        return False
    baseline = attempts.get("baseline")
    treatment = attempts.get("treatment")
    if not isinstance(baseline, list) or not isinstance(treatment, list):
        return False
    raw_allowed = receipt.get("allowed_axiom_hashes")
    if not isinstance(raw_allowed, list):
        return False
    allowed = {str(value) for value in raw_allowed}
    replay = evaluate_shadow_ab(
        pack_digest=str(receipt.get("pack_digest") or ""),
        base_theory_digest=str(receipt.get("base_theory_digest") or ""),
        allowed_axiom_hashes=allowed,
        task_manifest=task_manifest,
        baseline_attempts=baseline,
        treatment_attempts=treatment,
        trusted_checker_public_key_pem=trusted_checker_public_key_pem,
        trusted_manifest_public_key_pem=trusted_manifest_public_key_pem,
    )
    return (
        replay.get("ok") is True
        and replay.get("receipt_digest") == receipt.get("receipt_digest")
        and json.dumps(replay, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        == json.dumps(dict(receipt), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    )


__all__ = [
    "CANDIDATE_DEPENDENCY_SCHEMA",
    "MIN_PROMOTION_EVAL_TASKS",
    "SHADOW_ATTEMPT_SCHEMA",
    "SHADOW_TASK_MANIFEST_SCHEMA",
    "SHADOW_TASK_SCHEMA",
    "SHADOW_YIELD_SCHEMA",
    "ShadowAttempt",
    "ShadowTask",
    "build_shadow_attempt_verification",
    "build_shadow_task_manifest",
    "evaluate_candidate_dependency",
    "evaluate_shadow_ab",
    "rank_shadow_tasks",
    "verify_shadow_yield_receipt",
    "verify_shadow_task_manifest",
    "verify_candidate_dependency_receipt",
]
