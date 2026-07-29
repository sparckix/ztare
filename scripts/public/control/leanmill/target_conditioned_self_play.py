#!/usr/bin/env python3
"""Run a resumable result-card replay and target-conditioned conjecture wave."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping


REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.common import read_json, write_json_atomic  # noqa: E402
from ztare.leanmill.eigenquestion_review import run_eigenquestion_review  # noqa: E402
from ztare.leanmill.frontier_agent_runtime import (  # noqa: E402
    FrontierAgentConfig,
    SubscriptionJSONRole,
)
from ztare.leanmill.lean_source import (  # noqa: E402
    has_sorry,
    replace_decl_proof,
)
from ztare.leanmill.result_cards import (  # noqa: E402
    resolve_hidden_proof,
    sha256_file,
    validate_result_card_deck,
)
from ztare.leanmill.result_card_replay import (  # noqa: E402
    carry_hidden_replay,
    hidden_replay_config,
    hidden_replay_probe,
    validate_hidden_replay,
)
from ztare.leanmill.target_curriculum import (  # noqa: E402
    build_target_conjecture_admission,
    build_target_conjecture_wave,
    build_target_statement_revision_feedback,
    guide_questions,
    normalize_conjecturer_output,
    preflight_target_conjecture_wave,
    render_target_conjecture_prompt,
    target_conjecture_output_schema,
)
from ztare.leanmill.target_curriculum_adjudication import (  # noqa: E402
    continue_target_conjecture_admission,
)
from ztare.leanmill.theory_ir import content_hash  # noqa: E402


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")[-100:]


def _proof_attempt_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["proof", "attempt_summary"],
        "properties": {
            "proof": {"type": "string"},
            "attempt_summary": {"type": "string", "minLength": 1},
        },
    }


def _compile_attempt(
    hidden_probe: str,
    target: str,
    proof: str,
    lean_root: Path,
    timeout: int,
) -> tuple[bool, str]:
    if not proof.strip() or has_sorry(proof) or re.search(
        r"(?<![A-Za-z0-9_])admit(?![A-Za-z0-9_])", proof
    ):
        return False, "empty_or_forbidden_proof"
    closed = replace_decl_proof(hidden_probe, target, proof)
    from ztare.formal.repl_compile import compile_probe_via_repl

    result = compile_probe_via_repl(
        closed,
        lean_root,
        timeout=timeout,
        reject_sorry=True,
    )
    if not isinstance(result, tuple):
        return False, "malformed_compile_result"
    return bool(result[0]), str(result[1] if len(result) > 1 else "")


def run_hidden_replay(
    *,
    deck: Mapping[str, Any],
    artifact_dir: Path,
    repo: Path,
    lean_root: Path,
    attempts_per_card: int,
    model: str,
    reasoning_effort: str,
    agent_timeout: int,
    compile_timeout: int,
    run_tag: str,
) -> dict[str, Any]:
    aggregate_path = artifact_dir / "hidden_replay.json"
    prior = read_json(aggregate_path, None)
    replay_config = hidden_replay_config(
        deck,
        attempts_per_card=attempts_per_card,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    if isinstance(prior, Mapping):
        indexed = validate_hidden_replay(deck, prior)
        if (
            prior.get("config_sha256") == content_hash(replay_config)
            and all(row.get("outcome") != "runtime_unavailable" for row in indexed.values())
        ):
            return dict(prior)
    rows: list[dict[str, Any]] = []
    for card in deck["cards"]:
        hidden = hidden_replay_probe(deck, card)
        target = str(card["target_identity"])
        for attempt in range(attempts_per_card):
            attempt_dir = artifact_dir / "hidden_replay" / _slug(target) / f"attempt_{attempt}"
            receipt_path = attempt_dir / "attempt_receipt.json"
            existing = read_json(receipt_path, None)
            identity = {
                **replay_config,
                "card_id": card["card_id"],
                "attempt": attempt,
                "hidden_probe_sha256": hashlib.sha256(hidden.encode()).hexdigest(),
            }
            if (
                isinstance(existing, Mapping)
                and existing.get("identity_sha256") == content_hash(identity)
                and existing.get("outcome") != "runtime_unavailable"
            ):
                rows.append(dict(existing))
                print(f"[target-self-play] replay {target} {attempt + 1}/{attempts_per_card}: cached", flush=True)
                continue
            role = SubscriptionJSONRole(
                role="result_card_prover",
                agent_id=f"{run_tag}-card-{_slug(target)}-attempt-{attempt}",
                repo=repo,
                artifact_dir=attempt_dir / "agent",
                config=FrontierAgentConfig(
                    runtime="codex",
                    model=model,
                    reasoning_effort=reasoning_effort,
                    timeout_seconds=agent_timeout,
                    visible_workbench=False,
                    web_research=False,
                ),
                output_schema=_proof_attempt_schema(),
            )
            prompt = (
                "Prove the target theorem in this self-contained Lean 4 source. Return a proof term beginning "
                "with `by` (or another complete Lean term) and a short attempt summary. Do not use `sorry`, "
                "`admit`, `exact?`, `apply?`, native code execution, or alter any statement or definition. "
                "Return only the requested JSON object.\n\nLEAN SOURCE:\n" + hidden
            )
            proof = ""
            summary = ""
            infrastructure_error = ""
            try:
                response = role(prompt)
                proof = str(response.get("proof") or "").strip()
                summary = str(response.get("attempt_summary") or "").strip()
                compiled, error = _compile_attempt(
                    hidden, target, proof, lean_root, compile_timeout
                )
            except Exception as exc:  # noqa: BLE001 — typed calibration outcome, never proof credit
                compiled, error = False, repr(exc)
                infrastructure_error = type(exc).__name__
            call = dict(role.calls[-1]) if role.calls else {}
            core = {
                "schema": "leanmill.result_card_replay_attempt.v1",
                "identity_sha256": content_hash(identity),
                "deck_sha256": deck["deck_sha256"],
                "card_id": card["card_id"],
                "target_identity": target,
                "attempt": attempt,
                "hidden_probe_sha256": identity["hidden_probe_sha256"],
                "model": model,
                "reasoning_effort": reasoning_effort,
                "outcome": (
                    "kernel_closed"
                    if compiled
                    else "runtime_unavailable"
                    if infrastructure_error
                    else "not_closed"
                ),
                "proof_sha256": hashlib.sha256(proof.encode()).hexdigest() if proof else "",
                "compile_error_sha256": hashlib.sha256(error.encode()).hexdigest() if error else "",
                "attempt_summary": summary,
                "provider_call_charge": int(call.get("provider_call_charge", 0)),
                "call_receipt_sha256": content_hash(call) if call else "",
                "infrastructure_error": infrastructure_error,
                "authority": "difficulty_measurement_only",
            }
            receipt = {**core, "receipt_sha256": content_hash(core)}
            write_json_atomic(receipt_path, receipt)
            rows.append(receipt)
            print(
                f"[target-self-play] replay {target} {attempt + 1}/{attempts_per_card}: {receipt['outcome']}",
                flush=True,
            )
    core = {
        "schema": "leanmill.result_card_replay.v1",
        "config": replay_config,
        "config_sha256": content_hash(replay_config),
        "attempts": rows,
        "kernel_closed": sum(row["outcome"] == "kernel_closed" for row in rows),
        "provider_calls": sum(int(row.get("provider_call_charge", 0)) for row in rows),
        "authority": "calibration_only_no_theorem_interest_credit",
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(aggregate_path, receipt)
    return receipt


def _call_receipt(role: SubscriptionJSONRole, index: int) -> dict[str, Any]:
    call_path = role.artifact_dir / f"{index:03d}.call.json"
    return {
        "call_ref": str(call_path),
        "call_sha256": sha256_file(call_path),
        "provider_call_charge": int(role.calls[-1].get("provider_call_charge", 0)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deck", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--lean-root", type=Path, default=REPO / "ztare_proofs")
    parser.add_argument("--replay-k", type=int, default=4)
    parser.add_argument("--replay-model", default="gpt-5.4-mini")
    parser.add_argument("--replay-effort", default="low")
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--effort", default="ultra")
    parser.add_argument("--agent-timeout", type=int, default=900)
    parser.add_argument("--compile-timeout", type=int, default=180)
    parser.add_argument("--adjudication-timeout", type=int, default=500)
    parser.add_argument("--provider-call-cap", type=int, default=30)
    parser.add_argument("--carry-replay-deck", type=Path)
    parser.add_argument("--carry-replay-receipt", type=Path)
    args = parser.parse_args(argv)
    if args.replay_k < 1 or args.provider_call_cap < args.replay_k:
        raise ValueError("invalid target-conditioned replay budget")
    deck = json.loads(args.deck.read_text(encoding="utf-8"))
    validate_result_card_deck(deck)
    args.artifacts.mkdir(parents=True, exist_ok=True)
    run_tag = args.run_tag or f"target_selfplay_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    os.environ["ZTARE_SOLVER_RUN_TAG"] = run_tag

    if bool(args.carry_replay_deck) != bool(args.carry_replay_receipt):
        raise ValueError("replay carry requires both its source deck and source receipt")
    if args.carry_replay_deck:
        source_deck = json.loads(args.carry_replay_deck.read_text(encoding="utf-8"))
        source_receipt = json.loads(args.carry_replay_receipt.read_text(encoding="utf-8"))
        carry_hidden_replay(
            source_deck=source_deck,
            source_receipt=source_receipt,
            successor_deck=deck,
            artifact_dir=args.artifacts,
            attempts_per_card=args.replay_k,
            model=args.replay_model,
            reasoning_effort=args.replay_effort,
        )

    replay = run_hidden_replay(
        deck=deck,
        artifact_dir=args.artifacts,
        repo=REPO,
        lean_root=args.lean_root,
        attempts_per_card=args.replay_k,
        model=args.replay_model,
        reasoning_effort=args.replay_effort,
        agent_timeout=args.agent_timeout,
        compile_timeout=args.compile_timeout,
        run_tag=run_tag,
    )
    if replay["provider_calls"] + len(deck["cards"]) + 1 > args.provider_call_cap:
        raise RuntimeError("target-conditioned wave would exceed its frozen provider-call cap")

    dependencies = [row["target_identity"] for row in deck["cards"]]
    role = SubscriptionJSONRole(
        role="target_conditioned_conjecturer",
        agent_id=f"{run_tag}-conjecturer",
        repo=REPO,
        artifact_dir=args.artifacts / "conjecturer",
        config=FrontierAgentConfig(
            runtime="codex",
            model=args.model,
            reasoning_effort=args.effort,
            timeout_seconds=args.agent_timeout,
            visible_workbench=False,
            web_research=False,
        ),
        output_schema=target_conjecture_output_schema(dependencies),
    )
    candidates_by_card: list[list[dict[str, Any]]] = []
    call_receipts: list[dict[str, Any]] = []
    for index, card in enumerate(deck["cards"]):
        proof = resolve_hidden_proof(deck, card["card_id"])
        response = role(render_target_conjecture_prompt(deck, card, seed_proof=proof))
        candidates = normalize_conjecturer_output(deck, card, response)
        candidates_by_card.append(candidates)
        call_receipts.append(_call_receipt(role, index))
        print(
            f"[target-self-play] conjecturer {index + 1}/{len(deck['cards'])}: {len(candidates)} candidates",
            flush=True,
        )
    wave = build_target_conjecture_wave(
        deck,
        candidates_by_card,
        call_receipts=call_receipts,
    )
    write_json_atomic(args.artifacts / "proposal_wave.json", wave)

    statement_elaboration = preflight_target_conjecture_wave(
        wave,
        lean_root=args.lean_root,
    )
    write_json_atomic(
        args.artifacts / "statement_elaboration.json", statement_elaboration
    )
    statement_feedback = build_target_statement_revision_feedback(
        wave,
        statement_elaboration,
        lean_root=args.lean_root,
        successor_revision_epoch=1,
    )
    write_json_atomic(
        args.artifacts / "statement_revision_feedback.json", statement_feedback
    )
    questions = guide_questions(wave, statement_elaboration)
    guide_receipt = None
    if questions:
        guide_receipt = run_eigenquestion_review(
            questions,
            context={
                "objective": deck["objective"],
                "objective_sha256": deck["objective_sha256"],
                "deck_sha256": deck["deck_sha256"],
                "wave_sha256": wave["wave_sha256"],
                "success_criterion": (
                    "direct objective use, changed matched objective residual, or certified elimination of "
                    "a declared characterization branch"
                ),
                "non_credit": "card replay, proof golf, transfer variants, or recurrence",
            },
            artifact_dir=args.artifacts / "guide",
            repo=REPO,
            model=args.model,
            reasoning_effort=args.effort,
            timeout_seconds=args.agent_timeout,
        )
        sequence = list(guide_receipt["review"]["portfolio_sequence"])
        selected = sequence[:6]
    else:
        selected = []
    admission = build_target_conjecture_admission(
        wave,
        statement_elaboration,
        run_tag=run_tag,
        deck_sha256=deck["deck_sha256"],
        replay_receipt_sha256=replay["receipt_sha256"],
        guide_receipt=guide_receipt,
        selected_candidate_ids=selected,
    )
    write_json_atomic(args.artifacts / "admission.json", admission)
    continuation = continue_target_conjecture_admission(
        wave,
        statement_elaboration,
        guide_receipt,
        admission,
        lean_root=args.lean_root,
        artifact_dir=args.artifacts / "adjudication",
        timeout_s=args.adjudication_timeout,
        prior_continuation=read_json(
            args.artifacts / "adjudication" / "continuation.json", None
        ),
    )
    print(json.dumps({
        "run_tag": run_tag,
        "deck_sha256": deck["deck_sha256"],
        "hidden_replay": {
            "attempts": len(replay["attempts"]),
            "kernel_closed": replay["kernel_closed"],
            "provider_calls": replay["provider_calls"],
        },
        "proposed_candidates": wave["candidate_count"],
        "statement_elaborated_candidates": len(
            statement_elaboration["guide_eligible_candidate_ids"]
        ),
        "statement_rejected_candidates": len(
            statement_elaboration["rejected_candidate_ids"]
        ),
        "selected_candidates": len(selected),
        "adjudication_status": continuation["status"],
        "proved_candidates": len(continuation["proved_candidate_ids"]),
        "refuted_candidates": len(continuation["refuted_candidate_ids"]),
        "resumable_candidates": len(continuation["resumable_candidate_ids"]),
        "admission": str(args.artifacts / "admission.json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
