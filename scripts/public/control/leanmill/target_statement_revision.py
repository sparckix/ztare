#!/usr/bin/env python3
"""Run one bounded author revision epoch for rejected target conjectures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.common import read_json, write_json_atomic  # noqa: E402
from ztare.leanmill.eigenquestion_review import run_eigenquestion_review  # noqa: E402
from ztare.leanmill.frontier_agent_runtime import (  # noqa: E402
    FrontierAgentConfig,
    SubscriptionJSONRole,
)
from ztare.leanmill.result_cards import sha256_file  # noqa: E402
from ztare.leanmill.target_curriculum import (  # noqa: E402
    build_target_conjecture_admission,
    build_target_statement_revision_feedback,
    guide_questions,
    preflight_target_conjecture_wave,
    revise_target_conjecture_wave,
    target_statement_revision_output_schema,
)
from ztare.leanmill.target_curriculum_adjudication import (  # noqa: E402
    continue_target_conjecture_admission,
)
from ztare.leanmill.theory_ir import content_hash  # noqa: E402


def _revision_prompt(wave: dict, feedback: dict) -> str:
    candidates = {
        row["candidate_id"]: {
            "candidate_id": row["candidate_id"],
            "candidate_sha256": row["candidate_sha256"],
            "mathematical_statement": row["mathematical_statement"],
            "lean_signature": row["lean_signature"],
            "required_imports": row["required_imports"],
            "formal_context": row.get("formal_context"),
            "scope_limits": row["scope_limits"],
        }
        for row in wave.get("candidates") or ()
    }
    payload = {
        "source_wave_sha256": wave["wave_sha256"],
        "successor_revision_epoch": feedback["successor_revision_epoch"],
        "rejected_candidates": [
            {
                **candidates[row["candidate_id"]],
                "diagnostic_category": row["diagnostic_category"],
                "diagnostic_sha256": row["diagnostic_sha256"],
                "diagnostic_excerpt": row["diagnostic_excerpt"],
            }
            for row in feedback["candidate_feedback"]
        ],
    }
    return (
        "You are the target-conjecture author revising one frozen rejected wave. "
        "Repair only Lean signature, declared imports, and explicit formal context. "
        "Preserve each mathematical statement and scope. Never guess that an import module is also a "
        "namespace: declare exact open namespaces or an enclosing namespace only when source context "
        "supports it. Return one revision or one abandonment for every predecessor exactly once. "
        "A revision is a proof-free theorem signature with no name, proof, sorry, admit, or axiom. "
        "Prior candidate bytes remain immutable; this output mints successor identities. Return JSON only.\n\n"
        + json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wave", type=Path, required=True)
    parser.add_argument("--elaboration", type=Path, required=True)
    parser.add_argument("--predecessor-admission", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--feedback", type=Path)
    parser.add_argument("--lean-root", type=Path, default=REPO / "ztare_proofs")
    parser.add_argument("--successor-revision-epoch", type=int, default=1)
    parser.add_argument("--provider-calls-used", type=int, required=True)
    parser.add_argument("--provider-call-cap", type=int, required=True)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--effort", default="ultra")
    parser.add_argument("--agent-timeout", type=int, default=900)
    parser.add_argument("--adjudication-timeout", type=int, default=500)
    parser.add_argument(
        "--resume-after-guide",
        action="store_true",
        help=(
            "reuse the immutable successor, preflight, Guide, and admission "
            "already persisted in --artifacts"
        ),
    )
    parser.add_argument(
        "--unmetered-dispatch-incident",
        type=Path,
        help="bind an interrupted pre-fence dispatch record into accounting",
    )
    args = parser.parse_args(argv)
    if (
        args.provider_calls_used < 0
        or args.provider_call_cap - args.provider_calls_used < 2
    ):
        raise ValueError("revision epoch requires capacity for one author and one Guide call")
    wave = read_json(args.wave, None)
    elaboration = read_json(args.elaboration, None)
    predecessor_admission = read_json(args.predecessor_admission, None)
    if not all(isinstance(value, dict) for value in (
        wave, elaboration, predecessor_admission
    )):
        raise ValueError("revision inputs must be JSON objects")
    args.artifacts.mkdir(parents=True, exist_ok=True)
    feedback = (
        read_json(args.feedback, None)
        if args.feedback is not None
        else build_target_statement_revision_feedback(
            wave,
            elaboration,
            lean_root=args.lean_root,
            successor_revision_epoch=args.successor_revision_epoch,
        )
    )
    if not isinstance(feedback, dict) or not feedback.get("candidate_feedback"):
        raise ValueError("revision epoch has no rejected candidate feedback")
    write_json_atomic(args.artifacts / "revision_feedback.json", feedback)
    rejected_ids = [
        str(row["candidate_id"]) for row in feedback["candidate_feedback"]
    ]
    if args.resume_after_guide:
        successor = read_json(args.artifacts / "successor_wave.json", None)
        successor_elaboration = read_json(
            args.artifacts / "successor_statement_elaboration.json", None
        )
        guide_receipt = read_json(args.artifacts / "guide" / "review.json", None)
        admission = read_json(args.artifacts / "successor_admission.json", None)
        if not all(isinstance(value, dict) for value in (
            successor, successor_elaboration, guide_receipt, admission
        )):
            raise ValueError("resume-after-guide artifacts are incomplete")
        author_call = read_json(args.artifacts / "author" / "000.call.json", {})
        guide_call = read_json(args.artifacts / "guide" / "000.call.json", {})
        author_charge = int(author_call.get("provider_call_charge", 0))
        guide_charge = int(guide_call.get("provider_call_charge", 0))
        selected = list(admission.get("selected_candidate_ids") or ())
    else:
        role = SubscriptionJSONRole(
            role="target_conjecture_statement_reviser",
            agent_id=(
                f"target-revision-{wave['wave_sha256'][:12]}-"
                f"epoch-{feedback['successor_revision_epoch']}"
            ),
            repo=REPO,
            artifact_dir=args.artifacts / "author",
            config=FrontierAgentConfig(
                runtime="codex",
                model=args.model,
                reasoning_effort=args.effort,
                timeout_seconds=args.agent_timeout,
                visible_workbench=False,
                web_research=False,
            ),
            output_schema=target_statement_revision_output_schema(rejected_ids),
        )
        author_output = role(_revision_prompt(wave, feedback))
        call_path = role.artifact_dir / "000.call.json"
        author_charge = int(role.calls[-1].get("provider_call_charge", 0))
        author_call_receipt = {
            "call_ref": str(call_path),
            "call_sha256": sha256_file(call_path),
            "provider_call_charge": author_charge,
        }
        successor = revise_target_conjecture_wave(
            wave,
            elaboration,
            feedback,
            author_output,
            call_receipt=author_call_receipt,
        )
        write_json_atomic(args.artifacts / "successor_wave.json", successor)
        successor_elaboration = preflight_target_conjecture_wave(
            successor, lean_root=args.lean_root
        )
        write_json_atomic(
            args.artifacts / "successor_statement_elaboration.json",
            successor_elaboration,
        )
        questions = guide_questions(successor, successor_elaboration)
        guide_receipt = None
        guide_charge = 0
        used_after_author = args.provider_calls_used + author_charge
        if questions:
            if used_after_author + 1 > args.provider_call_cap:
                raise RuntimeError("successor Guide call would exceed cumulative provider cap")
            guide_receipt = run_eigenquestion_review(
                questions,
                context={
                    "objective_sha256": successor["objective_sha256"],
                    "deck_sha256": successor["deck_sha256"],
                    "wave_sha256": successor["wave_sha256"],
                    "revision_epoch": successor["revision_epoch"],
                    "success_criterion": "changed target residual with executable proof or refutation",
                    "non_credit": "syntax repair alone, recurrence, or predecessor restatement",
                },
                artifact_dir=args.artifacts / "guide",
                repo=REPO,
                model=args.model,
                reasoning_effort=args.effort,
                timeout_seconds=args.agent_timeout,
            )
            guide_call = read_json(args.artifacts / "guide" / "000.call.json", {})
            guide_charge = int(guide_call.get("provider_call_charge", 1))
            if used_after_author + guide_charge > args.provider_call_cap:
                raise RuntimeError("Guide receipt exceeded cumulative provider cap")
            selected = list(guide_receipt["review"]["portfolio_sequence"])[:6]
        else:
            selected = []
        admission = build_target_conjecture_admission(
            successor,
            successor_elaboration,
            run_tag=(
                str(predecessor_admission["run_tag"])
                + f"-revision-{successor['revision_epoch']}"
            ),
            deck_sha256=str(successor["deck_sha256"]),
            replay_receipt_sha256=str(
                predecessor_admission["replay_receipt_sha256"]
            ),
            guide_receipt=guide_receipt,
            selected_candidate_ids=selected,
        )
        write_json_atomic(args.artifacts / "successor_admission.json", admission)
    used_after_author = args.provider_calls_used + author_charge
    if used_after_author + guide_charge > args.provider_call_cap:
        raise RuntimeError("persisted revision calls exceed cumulative provider cap")
    incident = (
        read_json(args.unmetered_dispatch_incident, None)
        if args.unmetered_dispatch_incident is not None
        else None
    )
    if args.unmetered_dispatch_incident is not None and not isinstance(
        incident, dict
    ):
        raise ValueError("unmetered dispatch incident must be a JSON object")
    interrupted_dispatches = int(
        (incident or {}).get("host_dispatch_attempt_count", 0)
    )
    accounting_core = {
        "schema": "leanmill.target_revision_provider_accounting.v1",
        "source_wave_sha256": str(wave["wave_sha256"]),
        "successor_wave_sha256": str(successor["wave_sha256"]),
        "provider_call_cap": args.provider_call_cap,
        "provider_calls_before": args.provider_calls_used,
        "author_revision_charge": author_charge,
        "guide_charge": guide_charge,
        "adjudication_provider_charge": 0,
        "provider_calls_after": used_after_author + guide_charge,
        "provider_calls_after_scope": "receipt_bound_revision_and_guide_roles",
        "interrupted_unmetered_dispatch_attempt_count": interrupted_dispatches,
        "host_dispatch_attempts_after": (
            used_after_author + guide_charge + interrupted_dispatches
        ),
        "exact_billed_provider_call_count_available": not bool(incident),
        "unmetered_dispatch_incident_sha256": (
            sha256_file(args.unmetered_dispatch_incident)
            if args.unmetered_dispatch_incident is not None
            else ""
        ),
        "remaining_provider_calls": (
            args.provider_call_cap - used_after_author - guide_charge
        ),
        "remaining_cap_by_host_dispatch_attempts": (
            args.provider_call_cap
            - used_after_author
            - guide_charge
            - interrupted_dispatches
        ),
        "adjudication_mode": "provider_free_native_then_preverified_ratification",
        "authority": "cumulative_target_wave_provider_accounting",
    }
    accounting = {**accounting_core, "receipt_sha256": content_hash(accounting_core)}
    write_json_atomic(args.artifacts / "provider_accounting.json", accounting)
    prior_continuation = (
        read_json(args.artifacts / "adjudication" / "continuation.json", None)
        if args.resume_after_guide
        else None
    )
    if prior_continuation is not None and not isinstance(
        prior_continuation, dict
    ):
        raise ValueError("persisted adjudication continuation is not an object")
    continuation = continue_target_conjecture_admission(
        successor,
        successor_elaboration,
        guide_receipt,
        admission,
        lean_root=args.lean_root,
        artifact_dir=args.artifacts / "adjudication",
        timeout_s=args.adjudication_timeout,
        provider_mode="provider_free_native",
        provider_call_budget_delegated=False,
        prior_continuation=prior_continuation,
    )
    print(json.dumps({
        "successor_wave_sha256": successor["wave_sha256"],
        "revisions": successor["candidate_count"],
        "elaborated": len(successor_elaboration["guide_eligible_candidate_ids"]),
        "selected": len(selected),
        "next_authority": admission["next_authority"],
        "continuation_status": continuation["status"],
        "continuation_next_authority": continuation["next_authority"],
        "proved": len(continuation["proved_candidate_ids"]),
        "refuted": len(continuation["refuted_candidate_ids"]),
        "resumable": len(continuation["resumable_candidate_ids"]),
        "provider_calls_after": accounting["provider_calls_after"],
        "remaining_provider_calls": accounting["remaining_provider_calls"],
        "host_dispatch_attempts_after": accounting[
            "host_dispatch_attempts_after"
        ],
        "remaining_cap_by_host_dispatch_attempts": accounting[
            "remaining_cap_by_host_dispatch_attempts"
        ],
        "exact_billed_provider_call_count_available": accounting[
            "exact_billed_provider_call_count_available"
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
