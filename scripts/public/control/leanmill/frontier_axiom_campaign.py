"""Build and replay a frozen anonymous finite-theory campaign without a provider."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import uuid
from typing import Any

from ztare.leanmill.common import read_json, write_json_atomic, write_text_atomic
from ztare.leanmill.deterministic_frontier_campaign import run_deterministic_frontier_campaign
from ztare.leanmill.explore_axiom_space import explore_axiom_space
from ztare.leanmill.explore_axiom_space import execute_frontier_boundaries
from ztare.leanmill.finite_theory_context import load_formal_theory_context
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_blueprint import FrontierExplorationBrief
from ztare.leanmill.frontier_campaign import sign_frontier_campaign
from ztare.leanmill.frontier_campaign_actions import (
    frontier_campaign_status,
    inspect_frontier_campaign,
    replay_frontier_campaign,
    request_frontier_campaign_stop,
    retire_frontier_campaign,
)
from ztare.leanmill.frontier_campaign_definition import (
    FrontierCampaignDefinition,
    load_frontier_campaign_definition,
)
from ztare.leanmill.frontier_campaign_runner import (
    execute_frontier_campaign_verification,
    run_frontier_campaign_definition as run_campaign_definition,
)
from ztare.leanmill.magma_law_universe import anonymous_magma_signature
from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal
from ztare.leanmill.theory_ir import content_hash


def _secret(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def build_campaign(
    *,
    output_root: Path,
    max_order: int,
    carrier_sizes: tuple[int, ...],
    max_finalists: int,
) -> Path:
    attempt_id = "attempt-" + uuid.uuid4().hex
    directory = output_root / attempt_id
    signature = anonymous_magma_signature()
    private, public = generate_keypair()
    sealed_digest = "sha256:" + hashlib.sha256(
        b"reserved sealed post-freeze interpretation stratum"
    ).hexdigest()
    draft = {
        "mode": "anonymous_signature_census",
        "eigenquestion": (
            "Which anonymous two-law theory regions have conjunction-specific consequences "
            "that survive larger-model and conditional proof checks?"
        ),
        "signature": signature.to_json(),
        "primitive_semantics": {
            "operation_bindings": {"op0": "total finite binary operation table"},
            "relation_bindings": {},
        },
        "base_axioms": (),
        "base_theory_status": "explicit_empty",
        "adapter_id": "magma_equational.v1",
        "adapter_config": {"max_total_operation_order": max_order},
        "formula_grammar": {
            "schema": "leanmill.magma_law_universe.v1",
            "max_total_operation_order": max_order,
            "variable_renaming_quotient": True,
            "equation_side_quotient": True,
        },
        "model_or_observation_strata": tuple(
            {"carrier_size": size} for size in carrier_sizes
        ),
        "pack_arity": 2,
        "collapse_controls": (),
        "visible_evidence_manifest": {"interpretation_labels": []},
        "sealed_evidence_manifest_digest": sealed_digest,
        "deanchoring_policy": {"cold_after_signature_compilation": True},
        "navigator_contract": {
            "adapter_id": "axiompack",
            "selection_mode": "compact_axiom_pack",
        },
        "query_budget": {
            "max_finalists": max_finalists,
            "max_ranked_queries": max_finalists * 2,
            "larger_model_queries": max_finalists * 2,
            "conditional_lean_queries": max_finalists,
        },
        "stop_rule": {
            "freeze_after_finalists": max_finalists,
            "freeze_before_interpretation": True,
            "stop_on_no_eligible_independent_synergistic_nodes": True,
        },
        "verification_plan": {
            "larger_carriers": [4, 5],
            "conditional_lean": True,
            "post_freeze_interpretation": True,
        },
        "codec_versions": {"formula": "magma-postfix-v1", "model": "finite-table-v1"},
        "authority_refs": ("deterministic-census", "campaign-signer"),
    }
    run = explore_axiom_space(
        FrontierExplorationBrief(
            direction=(
                "Explore anonymous short two-law theories over one binary operation; "
                "do not seed named axiom systems."
            ),
            source_mode="structure_first",
        ),
        attempt_dir=directory,
        typed_draft=draft,
        packet_signer=lambda packet: sign_frontier_campaign(
            packet,
            private_key_pem=private,
            signer_ref="axiompack-campaign-authority",
        ),
    )
    _secret(directory / "private" / "campaign_signer.pem", private)
    write_text_atomic(directory / "campaign_signer_public.pem", public)
    campaign = read_json(directory / "campaign.json", {})
    campaign_id = str(campaign.get("packet", {}).get("campaign_id") or "")
    summary = dict(run.context_summary or {})
    result = {
        "schema": "leanmill.frontier_campaign_build_result.v1",
        "attempt_id": attempt_id,
        "campaign_id": campaign_id,
        "packet_digest": run.packet_digest,
        "context_hash": run.context_hash,
        "context_snapshot_ref": "formal_context.json",
        "formula_count": summary["formula_count"],
        "semantic_formula_profile_count": summary["semantic_formula_profile_count"],
        "labeled_model_count": summary["labeled_model_count"],
        "canonical_model_count": summary["accepted_model_count"],
        "generated_pair_theory_node_count": summary["generated_theory_node_count"],
        "unordered_formula_pair_count": summary["unordered_formula_pair_count"],
        "navigation": dict(run.navigation or {}),
        "scientific_status": "frozen_exact_context_control_no_discovery_claim",
        "provider_calls": 0,
    }
    result["result_digest"] = content_hash(result)
    write_json_atomic(directory / "result.json", result)
    return directory


def replay_campaign(directory: Path) -> dict[str, Any]:
    prior = read_json(directory / "result.json", {})
    if not isinstance(prior, dict) or not prior:
        raise ValueError("campaign result missing")
    context = load_formal_theory_context(directory / str(prior["context_snapshot_ref"]))
    journal_path = directory / "replay.events.jsonl"
    if journal_path.exists():
        raise ValueError("replay artifact already exists; use a new immutable attempt")
    navigation = run_deterministic_frontier_campaign(
        context,
        campaign_id=str(prior["campaign_id"]),
        attempt_id=str(prior["attempt_id"]) + "-replay",
        journal=TheoryCampaignJournal(journal_path),
        max_finalists=len(prior["navigation"]["finalist_node_ids"]),
        max_ranked_queries=len(prior["navigation"]["ranked_queries"]),
    )
    replayed = navigation.to_json()
    ok = replayed == prior["navigation"]
    receipt = {
        "schema": "leanmill.frontier_campaign_replay.v1",
        "ok": ok,
        "context_hash": context.context_hash,
        "prior_navigation_digest": content_hash(prior["navigation"]),
        "replayed_navigation_digest": content_hash(replayed),
        "provider_calls": 0,
    }
    write_json_atomic(directory / "replay.json", receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build-context")
    build.add_argument("--output-root", default="/tmp/axiompack_frontier_campaign")
    build.add_argument("--max-order", type=int, default=3)
    build.add_argument("--carrier-sizes", type=int, nargs="+", default=[2, 3])
    build.add_argument("--max-finalists", type=int, default=8)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--campaign-yaml", required=True)
    prepare.add_argument("--output", required=True)
    run = commands.add_parser("run")
    run.add_argument("--campaign-yaml", required=True)
    run.add_argument("--output-root", default="/tmp/axiompack_campaigns")
    run.add_argument("--typed-draft-json", default="")
    replay = commands.add_parser("replay")
    replay.add_argument("--attempt-dir", required=True)
    status = commands.add_parser("status")
    status.add_argument("--attempt-dir", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--attempt-dir", required=True)
    boundary = commands.add_parser("boundary-approve")
    boundary.add_argument("--attempt-dir", required=True)
    boundary.add_argument("--with-isabelle", action="store_true")
    boundary.add_argument("--with-lean", action="store_true")
    boundary.add_argument("--lean-root", default="")
    stop = commands.add_parser("stop")
    stop.add_argument("--attempt-dir", required=True)
    stop.add_argument("--authority-ref", required=True)
    retire = commands.add_parser("retire")
    retire.add_argument("--attempt-dir", required=True)
    retire.add_argument("--authority-ref", required=True)
    retire.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    if args.command == "build-context":
        directory = build_campaign(
            output_root=Path(args.output_root),
            max_order=args.max_order,
            carrier_sizes=tuple(args.carrier_sizes),
            max_finalists=args.max_finalists,
        )
        payload = read_json(directory / "result.json", {})
        print(json.dumps({"attempt_dir": str(directory), **payload}, sort_keys=True))
        return 0
    if args.command == "prepare":
        definition = load_frontier_campaign_definition(Path(args.campaign_yaml))
        output = Path(args.output)
        if output.exists():
            raise ValueError("prepared campaign output already exists")
        write_text_atomic(output, definition.to_yaml())
        print(json.dumps({
            "status": "campaign_definition_prepared_awaiting_run_approval",
            "campaign_definition": str(output),
            "definition_id": definition.definition_id,
        }, sort_keys=True))
        return 0
    if args.command == "run":
        definition = load_frontier_campaign_definition(Path(args.campaign_yaml))
        typed = read_json(args.typed_draft_json, None) if args.typed_draft_json else None
        if definition.source_mode == "structure_first" and not isinstance(typed, dict):
            raise ValueError("structure-first campaign run requires --typed-draft-json")
        directory = run_campaign_definition(
            definition,
            output_root=Path(args.output_root),
            typed_draft=typed,
        )
        print(json.dumps(frontier_campaign_status(directory), sort_keys=True))
        return 0
    if args.command == "replay":
        receipt = replay_frontier_campaign(Path(args.attempt_dir))
        print(json.dumps(receipt, sort_keys=True))
        return 0 if receipt["ok"] else 1
    if args.command == "status":
        print(json.dumps(frontier_campaign_status(args.attempt_dir), sort_keys=True))
        return 0
    if args.command == "inspect":
        print(json.dumps(inspect_frontier_campaign(args.attempt_dir), sort_keys=True))
        return 0
    if args.command == "boundary-approve":
        completion = execute_frontier_campaign_verification(
            args.attempt_dir,
            with_isabelle=args.with_isabelle,
            with_lean=args.with_lean,
            lean_root=args.lean_root or None,
        )
        print(json.dumps(completion, sort_keys=True))
        return 0
    if args.command == "stop":
        print(json.dumps(request_frontier_campaign_stop(
            args.attempt_dir, authority_ref=args.authority_ref
        ), sort_keys=True))
        return 0
    print(json.dumps(retire_frontier_campaign(
        args.attempt_dir,
        authority_ref=args.authority_ref,
        reason=args.reason,
    ), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
