"""Prepare and execute the quarantined finite-band AxiomPack calibration.

The model sees a shallow constrained wire format.  LeanMill resolves the
frozen source reference, parses the typed IR, and applies the registered band
grammar before any semantic review or finite-model screen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from typing import Any, Mapping

from ztare.common.subscription_agent_runtime import (
    CODEX_SANDBOX_SEALED_COMPLETION,
    cancel_owned_dispatch_receipt,
    owned_dispatch_receipt_status,
    run_subscription_agent_with_recovery,
)
from ztare.leanmill.common import write_json_atomic, write_text_atomic
from ztare.leanmill.axiom_pack import (
    blueprint_from_agent_isomorphism_receipt,
    generate_candidate_axiom_pack,
)
from ztare.leanmill.axiom_pack_band import (
    build_band_preregistration,
    finite_band_pilot_design,
    validate_band_candidate_axiom,
)
from ztare.leanmill.axiom_pack_orchestration import (
    make_contract_proposer,
    make_signed_semantic_checker,
    orchestrate_typed_axiom_proposals,
    recover_valid_quarantined_rows,
    render_typed_proposer_prompt,
)
from ztare.leanmill.contracts.axiom_pack_transport import (
    AxiomPackTransportContract,
    band_word_output_schema,
    sign_transport_contract,
    verify_transport_contract,
)
from ztare.leanmill.finite_model import FiniteModel, certify_joint_satisfiability, evaluate_axiom
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.axiom_yield import verify_shadow_task_manifest


EXECUTION_SCHEMA = "leanmill.axiom_pack_band_execution.v1"
CHECKER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["faithful", "rationale", "evidence_refs"],
    "properties": {
        "faithful": {"type": "boolean"},
        "rationale": {"type": "string", "minLength": 1},
        "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
    },
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _sha(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    write_json_atomic(path, value)


def _write_secret(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


class _CodexSubscriptionCall:
    def __init__(self, *, model: str, reasoning_effort: str, role: str, provider_call_timeout_s: int,
                 output_schema: Path, agent_id: str, artifact_dir: Path) -> None:
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.role = role
        self.provider_call_timeout_s = provider_call_timeout_s
        self.output_schema = output_schema
        self.agent_id = agent_id
        self.artifact_dir = artifact_dir
        self.metadata: dict[str, Any] = {
            "runtime": "codex_subscription",
            "model": model,
            "reasoning_effort": reasoning_effort,
            "role": role,
            "agent_id": agent_id,
            "output_schema_sha256": _sha(_read_json(output_schema)),
            "calls": [],
        }

    def __call__(self, prompt: str) -> str:
        stdout_path = self.artifact_dir / f"{self.role}.stdout.txt"
        stderr_path = self.artifact_dir / f"{self.role}.stderr.txt"
        call_path = self.artifact_dir / f"{self.role}.call.json"
        prompt_digest = _sha(prompt)
        if stdout_path.is_file() and call_path.is_file():
            prior = _read_json(call_path)
            if prior.get("prompt_sha256") != prompt_digest or prior.get("returncode") != 0:
                raise RuntimeError(f"{self.role}_immutable_attempt_mismatch")
            stdout = stdout_path.read_text(encoding="utf-8")
            if not stdout.strip():
                raise RuntimeError(f"{self.role}_empty_durable_response")
            replay = {**prior, "replayed_durable_bytes": True, "wallclock_s": 0.0}
            calls = self.metadata["calls"]
            assert isinstance(calls, list)
            calls.append(replay)
            self.metadata.update({**replay, "call_count": 0, "total_wallclock_s": 0.0})
            return stdout
        previous_effort = os.environ.get("ZTARE_CODEX_AGENT_REASONING_EFFORT")
        os.environ["ZTARE_CODEX_AGENT_REASONING_EFFORT"] = self.reasoning_effort
        started = time.monotonic()
        try:
            run = run_subscription_agent_with_recovery(
                runtime="codex",
                prompt=prompt,
                agent_id=self.agent_id,
                repo=Path("/tmp"),
                session_state=None,
                timeout_seconds=self.provider_call_timeout_s,
                default_codex_model=self.model,
                codex_sandbox=CODEX_SANDBOX_SEALED_COMPLETION,
                output_schema=self.output_schema,
                dispatch_receipt_path=self.artifact_dir / f"{self.role}.dispatch.json",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
            )
        finally:
            if previous_effort is None:
                os.environ.pop("ZTARE_CODEX_AGENT_REASONING_EFFORT", None)
            else:
                os.environ["ZTARE_CODEX_AGENT_REASONING_EFFORT"] = previous_effort
        completed = run.result
        stdout = str(completed.stdout or "")
        stderr = str(completed.stderr or "")
        # Preserve full provider bytes before parsing or downstream checking.
        write_text_atomic(stdout_path, stdout)
        write_text_atomic(stderr_path, stderr)
        call_record = {
            "prompt_sha256": prompt_digest,
            "returncode": int(completed.returncode),
            "wallclock_s": round(time.monotonic() - started, 2),
            "output_sha256": _sha(stdout),
            "output_chars": len(stdout),
            "output_excerpt": stdout[:5000],
            "stderr_excerpt": stderr[-1000:],
        }
        calls = self.metadata["calls"]
        assert isinstance(calls, list)
        calls.append(call_record)
        self.metadata.update({
            **call_record,
            "call_count": len(calls),
            "total_wallclock_s": round(sum(float(row["wallclock_s"]) for row in calls), 2),
        })
        _write_json(call_path, call_record)
        if completed.returncode != 0 or not stdout.strip():
            raise RuntimeError(f"{self.role}_provider_failed:{completed.returncode}:{stderr[-240:]}")
        return stdout


class _RecoveredResponseCall:
    """Replay already-captured provider bytes without dispatching a provider."""

    def __init__(self, *, role: str, output: str, source: str) -> None:
        self.output = output
        self.metadata: dict[str, Any] = {
            "runtime": "recovered_response_bytes",
            "role": role,
            "recovery_source": source,
            "calls": [],
        }

    def __call__(self, _prompt: str) -> str:
        record = {
            "returncode": 0,
            "wallclock_s": 0.0,
            "output_sha256": _sha(self.output),
            "output_chars": len(self.output),
            "output_excerpt": self.output[:5000],
            "stderr_excerpt": "",
        }
        calls = self.metadata["calls"]
        assert isinstance(calls, list)
        calls.append(record)
        self.metadata.update({**record, "call_count": len(calls), "total_wallclock_s": 0.0})
        return self.output


def _finite_screen(design: Any, pack: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in pack.candidate_axioms:
        from ztare.leanmill.theory_ir import AxiomFormula, Formula

        axiom = AxiomFormula.from_json({
            "name": candidate["name"],
            "formula": candidate["formula"],
        })
        probe = AxiomFormula(
            f"pilot_retained_{axiom.name}",
            Formula.conjunction(axiom.formula, *(item.formula for item in design.retained_model_constraints)),
        )
        receipt = certify_joint_satisfiability(
            design.signature, (*design.base_axioms, probe), design.retained_model_bounds
        )
        row: dict[str, Any] = {
            "candidate": axiom.name,
            "status": receipt.status,
            "receipt": receipt.to_json(),
            "retained_model_outside_controls": False,
        }
        if receipt.witness is not None:
            model = FiniteModel.from_json(receipt.witness["model"])
            row["retained_model_outside_controls"] = all(
                evaluate_axiom(design.signature, control, model) is False
                for control in design.collapse_controls
            )
        rows.append(row)
    return rows


def prepare(*, state_dir: Path, model: str, reasoning_effort: str) -> Path:
    """Freeze, sign, and persist one execution packet before any model dispatch."""

    design = finite_band_pilot_design()
    manifest_private, manifest_public = generate_keypair()
    semantic_private, semantic_public = generate_keypair()
    admission_digests = {task.task_id: _sha(f"band-calibration-admission:{task.task_id}") for task in design.heldout_tasks}
    preregistration = build_band_preregistration(
        design=design,
        admission_digests=admission_digests,
        private_key_pem=manifest_private,
        verifier_ref="band-calibration-manifest-checker",
        manifest_evidence_ref=_sha("band-calibration-preregistration"),
    )
    proposer_view = preregistration["proposer_view"]
    transport = AxiomPackTransportContract(
        proposer_view_digest=_sha(proposer_view), source_catalog=design.source_catalog()
    )
    proposer_schema = band_word_output_schema()
    proposer_prompt = transport.render_prompt(proposer_view)
    core = {
        "schema": EXECUTION_SCHEMA,
        "frozen": True,
        "scientific_status": "calibration_only_no_discovery_claim",
        "manifest_digest": preregistration["manifest"]["metadata"]["manifest_digest"],
        "proposer_view_digest": _sha(proposer_view),
        "transport_contract_digest": transport.digest,
        "proposer_prompt_sha256": _sha(proposer_prompt),
        "proposer_output_schema_sha256": _sha(proposer_schema),
        "checker_output_schema_sha256": _sha(CHECKER_SCHEMA),
        "runtime": "codex_subscription",
        "model": model,
        "reasoning_effort": reasoning_effort,
    }
    signature = sign_transport_contract(core, manifest_private)
    prepared_dir = state_dir / f"prepared-{uuid.uuid4().hex[:16]}"
    prepared_dir.mkdir(parents=True, exist_ok=False)
    _write_json(prepared_dir / "proposer_output.schema.json", proposer_schema)
    _write_json(prepared_dir / "checker_output.schema.json", CHECKER_SCHEMA)
    _write_secret(prepared_dir / "private" / "manifest.pem", manifest_private)
    _write_secret(prepared_dir / "private" / "semantic_fidelity.pem", semantic_private)
    _write_json(prepared_dir / "prepared.json", {
        "execution_contract": core,
        "execution_contract_signature": signature,
        "manifest_public_key_pem": manifest_public,
        "semantic_fidelity_public_key_pem": semantic_public,
        "preregistration": preregistration,
        "transport_contract": transport.to_json(),
        "scientific_status": "calibration_only_no_discovery_claim",
    })
    return prepared_dir


def _load_prepared(prepared_dir: Path) -> tuple[dict[str, Any], AxiomPackTransportContract]:
    prepared = _read_json(prepared_dir / "prepared.json")
    core = prepared.get("execution_contract")
    if not isinstance(core, Mapping) or core.get("schema") != EXECUTION_SCHEMA:
        raise ValueError("prepared execution contract missing")
    if not verify_transport_contract(
        core,
        str(prepared.get("execution_contract_signature") or ""),
        str(prepared.get("manifest_public_key_pem") or ""),
    ):
        raise ValueError("prepared execution contract signature")
    preregistration = prepared.get("preregistration")
    transport_row = prepared.get("transport_contract")
    if not isinstance(preregistration, Mapping) or not isinstance(transport_row, Mapping):
        raise ValueError("prepared contract content missing")
    proposer_view = preregistration.get("proposer_view")
    manifest = preregistration.get("manifest")
    if not isinstance(proposer_view, Mapping) or not isinstance(manifest, Mapping):
        raise ValueError("prepared proposer view or manifest missing")
    if core.get("proposer_view_digest") != _sha(proposer_view):
        raise ValueError("prepared proposer view digest")
    # The prompt is owned by the signed transport codec, not the generic proposer.
    if core.get("proposer_output_schema_sha256") != _sha(_read_json(prepared_dir / "proposer_output.schema.json")):
        raise ValueError("prepared proposer schema digest")
    if core.get("checker_output_schema_sha256") != _sha(_read_json(prepared_dir / "checker_output.schema.json")):
        raise ValueError("prepared checker schema digest")
    if core.get("manifest_digest") != manifest.get("metadata", {}).get("manifest_digest"):
        raise ValueError("prepared manifest digest")
    source_catalog = transport_row.get("source_catalog")
    if not isinstance(source_catalog, Mapping):
        raise ValueError("prepared source catalog missing")
    transport = AxiomPackTransportContract(
        proposer_view_digest=str(transport_row.get("proposer_view_digest") or ""),
        source_catalog={str(key): dict(value) for key, value in source_catalog.items() if isinstance(value, Mapping)},
    )
    if core.get("transport_contract_digest") != transport.digest:
        raise ValueError("prepared transport contract digest")
    if core.get("proposer_prompt_sha256") != _sha(transport.render_prompt(proposer_view)):
        raise ValueError("prepared proposer prompt digest")
    return prepared, transport


def _load_completed_historical_evidence(
    prepared_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify frozen completed bytes without rebuilding their historical codec."""

    prepared = _read_json(prepared_dir / "prepared.json")
    core = prepared.get("execution_contract")
    if not isinstance(core, Mapping) or core.get("schema") != EXECUTION_SCHEMA:
        raise ValueError("prepared execution contract missing")
    if not verify_transport_contract(
        core,
        str(prepared.get("execution_contract_signature") or ""),
        str(prepared.get("manifest_public_key_pem") or ""),
    ):
        raise ValueError("prepared execution contract signature")

    preregistration = prepared.get("preregistration")
    transport = prepared.get("transport_contract")
    if not isinstance(preregistration, Mapping) or not isinstance(transport, Mapping):
        raise ValueError("prepared contract content missing")
    proposer_view = preregistration.get("proposer_view")
    manifest = preregistration.get("manifest")
    if not isinstance(proposer_view, Mapping) or not isinstance(manifest, Mapping):
        raise ValueError("prepared proposer view or manifest missing")
    if core.get("proposer_view_digest") != _sha(proposer_view):
        raise ValueError("prepared proposer view digest")

    proposer_schema = _read_json(prepared_dir / "proposer_output.schema.json")
    checker_schema = _read_json(prepared_dir / "checker_output.schema.json")
    if core.get("proposer_output_schema_sha256") != _sha(proposer_schema):
        raise ValueError("prepared proposer schema digest")
    if core.get("checker_output_schema_sha256") != _sha(checker_schema):
        raise ValueError("prepared checker schema digest")
    if transport.get("output_schema") != proposer_schema:
        raise ValueError("prepared transport schema bytes")
    if transport.get("output_schema_digest") != _sha(proposer_schema):
        raise ValueError("prepared transport schema digest")
    if transport.get("proposer_view_digest") != core.get("proposer_view_digest"):
        raise ValueError("prepared transport proposer view digest")
    if core.get("transport_contract_digest") != _sha(transport):
        raise ValueError("prepared historical transport digest")

    manifest_digest = manifest.get("metadata", {}).get("manifest_digest")
    if core.get("manifest_digest") != manifest_digest:
        raise ValueError("prepared manifest digest")
    base_digest = manifest.get("metadata", {}).get("manifest", {}).get("base_theory_digest")
    manifest_ok, manifest_failures = verify_shadow_task_manifest(
        manifest,
        base_theory_digest=str(base_digest or ""),
        trusted_public_key_pem=str(prepared.get("manifest_public_key_pem") or ""),
    )
    if not manifest_ok:
        raise ValueError(f"prepared manifest verification: {manifest_failures}")

    completed = _read_json(prepared_dir / "run_result.json")
    if completed.get("execution_contract_digest") != _sha(core):
        raise ValueError("completed result does not match prepared execution contract")
    return prepared, completed


def execute(
    *,
    prepared_dir: Path,
    provider_call_timeout_s: int,
    recovered_outputs: Mapping[str, str] | None = None,
    recovery_source: str = "",
) -> dict[str, Any]:
    """Verify a frozen packet, then run the constrained proposer and checker."""

    prepared, transport = _load_prepared(prepared_dir)
    core = prepared["execution_contract"]
    completed_path = prepared_dir / "run_result.json"
    if completed_path.is_file():
        completed = _read_json(completed_path)
        if completed.get("execution_contract_digest") != _sha(core):
            raise ValueError("completed result does not match prepared execution contract")
        return completed
    preregistration = prepared["preregistration"]
    proposer_view = preregistration["proposer_view"]
    manifest = preregistration["manifest"]
    manifest_ok, manifest_failures = verify_shadow_task_manifest(
        manifest,
        base_theory_digest=str(manifest.get("metadata", {}).get("manifest", {}).get("base_theory_digest") or ""),
        trusted_public_key_pem=str(prepared["manifest_public_key_pem"]),
    )
    if not manifest_ok:
        raise ValueError(f"prepared manifest verification: {manifest_failures}")
    design = finite_band_pilot_design()
    if recovered_outputs is None:
        proposer_call = _CodexSubscriptionCall(
            model=str(core["model"]), reasoning_effort=str(core["reasoning_effort"]), role="proposer",
            provider_call_timeout_s=provider_call_timeout_s,
            output_schema=prepared_dir / "proposer_output.schema.json",
            agent_id=f"leanmill::axiom_pack_band::proposer::{core['transport_contract_digest'][-12:]}",
            artifact_dir=prepared_dir / "calls",
        )
        checker_call = _CodexSubscriptionCall(
            model=str(core["model"]), reasoning_effort=str(core["reasoning_effort"]), role="semantic_checker",
            provider_call_timeout_s=provider_call_timeout_s,
            output_schema=prepared_dir / "checker_output.schema.json",
            agent_id=f"leanmill::axiom_pack_band::semantic_checker::{core['transport_contract_digest'][-12:]}",
            artifact_dir=prepared_dir / "calls",
        )
    else:
        if set(recovered_outputs) != {"proposer", "semantic_checker"}:
            raise ValueError("recovery requires proposer and semantic_checker response bytes")
        proposer_call = _RecoveredResponseCall(
            role="proposer", output=str(recovered_outputs["proposer"]), source=recovery_source,
        )
        checker_call = _RecoveredResponseCall(
            role="semantic_checker", output=str(recovered_outputs["semantic_checker"]), source=recovery_source,
        )
    orchestration = orchestrate_typed_axiom_proposals(
        escalation=None,
        calibration_only=True,
        proposer_view=proposer_view,
        task_manifest=manifest,
        trusted_manifest_public_key_pem=str(prepared["manifest_public_key_pem"]),
        trusted_semantic_fidelity_public_key_pem=str(prepared["semantic_fidelity_public_key_pem"]),
        expected_semantic_fidelity_verifier_ref="band-calibration-semantic-checker",
        proposer_fn=make_contract_proposer(proposer_call, transport_contract=transport),
        semantic_checker_fn=make_signed_semantic_checker(
            checker_call,
            private_key_pem=(prepared_dir / "private" / "semantic_fidelity.pem").read_text(encoding="utf-8"),
            verifier_ref="band-calibration-semantic-checker",
        ),
        proposal_validator=lambda proposal: validate_band_candidate_axiom(proposal["axiom"], design=design),
    )
    result: dict[str, Any] = {
        "schema": "leanmill.axiom_pack_band_pilot_result.v2",
        "scientific_status": "calibration_only_no_discovery_claim",
        "execution_contract_digest": _sha(core),
        "prepared_dir": str(prepared_dir),
        "recovered_from_response_bytes": recovered_outputs is not None,
        "orchestration": orchestration,
        "provider_calls": {"proposer": proposer_call.metadata, "semantic_checker": checker_call.metadata},
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }
    result["post_orchestration_ok"] = True
    try:
        if orchestration.get("ok"):
            trial = blueprint_from_agent_isomorphism_receipt(
                design.blueprints[0], orchestration["receipt"],
                trusted_semantic_fidelity_public_key_pem=str(prepared["semantic_fidelity_public_key_pem"]),
                expected_semantic_fidelity_verifier_ref="band-calibration-semantic-checker",
            )
            result["agent_blueprint_trial"] = trial
            if trial.get("construction_ready"):
                from ztare.leanmill.axiom_pack import AxiomPackBlueprint
                pack, generation = generate_candidate_axiom_pack(
                    AxiomPackBlueprint.from_json(trial["blueprint"]),
                    isomorphism_receipt=orchestration["receipt"],
                    trusted_semantic_fidelity_public_key_pem=str(prepared["semantic_fidelity_public_key_pem"]),
                )
                result.update({"generation": generation, "pack": pack.to_json(), "finite_screen": _finite_screen(design, pack)})
    except Exception as exc:  # noqa: BLE001 - preserve the completed provider evidence for diagnosis.
        result["post_orchestration_ok"] = False
        result["post_orchestration_error"] = f"{type(exc).__name__}:{exc}"
    finally:
        _write_json(prepared_dir / "run_result.json", result)
    return result


def salvage_checked_rows(*, prepared_dir: Path) -> dict[str, Any]:
    """Recover individually valid checked rows from a rejected completed batch."""
    output = prepared_dir / "row_recovery.json"
    if output.is_file():
        return _read_json(output)
    prepared, completed = _load_completed_historical_evidence(prepared_dir)
    orchestration = completed.get("orchestration")
    if not isinstance(orchestration, Mapping):
        raise ValueError("completed pilot has no typed orchestration")
    design = finite_band_pilot_design()
    recovery = recover_valid_quarantined_rows(
        orchestration,
        trusted_semantic_fidelity_public_key_pem=str(
            prepared["semantic_fidelity_public_key_pem"]
        ),
        expected_semantic_fidelity_verifier_ref="band-calibration-semantic-checker",
        proposal_validator=lambda proposal: validate_band_candidate_axiom(
            proposal["axiom"], design=design
        ),
    )
    _write_json(output, recovery)
    return recovery


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or execute the finite-band AxiomPack calibration")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--state-dir", default="/tmp/leanmill_axiom_pack_band")
    prepare_parser.add_argument("--model", default="gpt-5.5")
    prepare_parser.add_argument(
        "--reasoning-effort", choices=("low", "medium", "high", "ultra"), default="low"
    )
    execute_parser = commands.add_parser("execute")
    execute_parser.add_argument("--prepared-dir", required=True)
    execute_parser.add_argument("--provider-call-timeout-s", "--timeout-s", dest="provider_call_timeout_s", type=int, default=180)
    recover_parser = commands.add_parser("recover")
    recover_parser.add_argument("--prepared-dir", required=True)
    recover_parser.add_argument("--proposer-output-file", required=True)
    recover_parser.add_argument("--checker-output-file", required=True)
    recover_parser.add_argument("--recovery-source", required=True)
    salvage_parser = commands.add_parser("salvage-checked-rows")
    salvage_parser.add_argument("--prepared-dir", required=True)
    status_parser = commands.add_parser("status")
    status_parser.add_argument("--prepared-dir", required=True)
    cancel_parser = commands.add_parser("cancel")
    cancel_parser.add_argument("--prepared-dir", required=True)
    cancel_parser.add_argument("--role", choices=("proposer", "semantic_checker"), required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        prepared_dir = prepare(state_dir=Path(args.state_dir), model=args.model, reasoning_effort=args.reasoning_effort)
        print(json.dumps({"prepared_dir": str(prepared_dir), "scientific_status": "calibration_only_no_discovery_claim"}))
        return 0
    if args.command == "status":
        directory = Path(args.prepared_dir)
        roles = {}
        for role in ("proposer", "semantic_checker"):
            receipt = directory / "calls" / f"{role}.dispatch.json"
            roles[role] = (
                owned_dispatch_receipt_status(receipt) if receipt.exists() else "not_started"
            )
        payload = {
            "attempt_status": "completed" if (directory / "run_result.json").is_file() else "incomplete",
            "roles": roles,
            "result": str(directory / "run_result.json"),
        }
        print(json.dumps(payload, sort_keys=True))
        return 0
    if args.command == "cancel":
        receipt = Path(args.prepared_dir) / "calls" / f"{args.role}.dispatch.json"
        cancelled = cancel_owned_dispatch_receipt(receipt) if receipt.exists() else False
        print(json.dumps({"cancelled": cancelled, "role": args.role, "receipt": str(receipt)}))
        return 0 if cancelled else 1
    if args.command == "salvage-checked-rows":
        recovery = salvage_checked_rows(prepared_dir=Path(args.prepared_dir))
        print(json.dumps({
            "status": recovery["status"],
            "accepted_count": recovery["accepted_count"],
            "rejected_count": recovery["rejected_count"],
            "provider_calls": 0,
            "result": str(Path(args.prepared_dir) / "row_recovery.json"),
        }, sort_keys=True))
        return 0 if recovery["accepted_count"] else 1
    if args.command == "recover":
        result = execute(
            prepared_dir=Path(args.prepared_dir),
            provider_call_timeout_s=0,
            recovered_outputs={
                "proposer": Path(args.proposer_output_file).read_text(encoding="utf-8"),
                "semantic_checker": Path(args.checker_output_file).read_text(encoding="utf-8"),
            },
            recovery_source=args.recovery_source,
        )
    else:
        result = execute(
            prepared_dir=Path(args.prepared_dir),
            provider_call_timeout_s=args.provider_call_timeout_s,
        )
    execution_ok = result["orchestration"].get("ok") and result.get("post_orchestration_ok") is True
    print(json.dumps({"execution_ok": execution_ok, "orchestration_ok": result["orchestration"].get("ok"), "result": str(Path(args.prepared_dir) / "run_result.json")}))
    return 0 if execution_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
