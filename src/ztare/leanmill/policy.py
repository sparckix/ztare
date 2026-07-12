"""Shared LeanMill factory-policy loader.

Operational tuning belongs in the folder-local policy artifact, not
scattered across daemon launch commands. Scripts still keep conservative
parser defaults for test isolation, but live profiles override them via
``apply_profile_section``.

Phase A migration (2026-05-23): canonical home moved here from
``scripts/public/control/leanmill/factory_config.py``. That script keeps a
thin shim re-export so existing imports continue to work.

The original filename ``leanmill_factory_config`` is misleading — this
module reads policy, not "config" in the build/install sense — but the
shim preserves the name to avoid a cascade of import changes. New code
should import ``ztare.leanmill.policy`` instead.
"""
from __future__ import annotations

import argparse
import json
import os
from argparse import Namespace
from pathlib import Path
from typing import Any

from ztare.leanmill.paths import FACTORY_POLICY


def read_policy(path: str | Path = FACTORY_POLICY) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def apply_profile_section(
    args: Namespace,
    *,
    section: str,
    profile_attr: str = "policy_profile",
    policy_attr: str = "factory_policy",
) -> dict[str, Any]:
    profile_name = str(getattr(args, profile_attr, "") or "")
    if not profile_name:
        return {"name": "", "path": str(getattr(args, policy_attr, FACTORY_POLICY)), "key_count": 0, "keys": []}
    policy_path = Path(str(getattr(args, policy_attr, FACTORY_POLICY)))
    profile = ((read_policy(policy_path).get("profiles") or {}).get(profile_name) or {})
    values = profile.get(section) or {}
    if not isinstance(values, dict):
        values = {}
    applied: dict[str, Any] = {}
    for key, value in values.items():
        if hasattr(args, key):
            setattr(args, key, value)
            applied[key] = value
    receipt = {
        "name": profile_name,
        "path": str(policy_path),
        "section": section,
        "key_count": len(applied),
        "keys": sorted(applied),
    }
    setattr(args, f"_policy_profile_{section}_applied", receipt)
    return receipt


def _int_value(obj: dict[str, Any], key: str, fallback: int) -> int:
    try:
        return int(obj.get(key) if obj.get(key) is not None else fallback)
    except (TypeError, ValueError):
        return fallback


def priority_policy_from_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return the global LeanMill priority policy stanza.

    Work-queue and dashboard priority numbers are operational policy. The
    queue itself enforces ordering, while this helper gives scripts one place
    to read named priority constants without parsing policy structure locally.
    """
    if not isinstance(policy, dict):
        policy = {}
    operations = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    obj = operations.get("priority_policy") if isinstance(operations.get("priority_policy"), dict) else {}
    return obj if isinstance(obj, dict) else {}


def priority_value_from_policy(
    policy: dict[str, Any] | None,
    *,
    namespace: str,
    key: str,
    fallback: int,
) -> int:
    obj = priority_policy_from_policy(policy)
    values = obj.get(namespace) if isinstance(obj.get(namespace), dict) else {}
    try:
        value = values.get(key) if isinstance(values, dict) else None
        return int(value if value is not None else fallback)
    except (TypeError, ValueError):
        return int(fallback)


def priority_value(
    *,
    path: str | Path = FACTORY_POLICY,
    namespace: str,
    key: str,
    fallback: int,
) -> int:
    return priority_value_from_policy(read_policy(path), namespace=namespace, key=key, fallback=fallback)


def semantic_reference_threshold(*, path: str | Path = FACTORY_POLICY, fallback: float = 0.70) -> float:
    """Policy-owned cosine floor for `FaithfulnessStore` semantic reference-reuse (the reuse-churn fix — a
    paraphrased/agnostic-decomposed sub-lemma NL still recalls its CONFIRMED rendering instead of re-formalizing).
    Resolution order (highest first): the env override `ZTARE_LEANMILL_SEMANTIC_REFERENCE_THRESHOLD`; the factory
    policy `operations.faithfulness.semantic_reference_threshold`; else the calibrated `fallback`. Calibrated on
    all-MiniLM-L6-v2 over real CLOB NLs: correct paraphrase→lemma ≈ 0.76, wrong same-domain lemma ≈ 0.50, unrelated
    ≈ 0.12 ⇒ 0.70 separates cleanly. Only trades recall vs a cheap firewall check (a mis-retrieval is re-gated and
    rejected downstream — the kernel is the sole arbiter, this number is an affordance knob, never a soundness one."""
    env = os.environ.get("ZTARE_LEANMILL_SEMANTIC_REFERENCE_THRESHOLD")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    operations = read_policy(path).get("operations") if isinstance(read_policy(path).get("operations"), dict) else {}
    obj = operations.get("faithfulness") if isinstance(operations.get("faithfulness"), dict) else {}
    try:
        v = obj.get("semantic_reference_threshold")
        return float(v) if v is not None else float(fallback)
    except (TypeError, ValueError):
        return float(fallback)


def prompt_transport_policy(*, path: str | Path = FACTORY_POLICY) -> dict[str, Any]:
    """Return the shared prompt-size policy used by subscription leaves.

    The factory policy owns the limits; callers receive a conservative
    platform-derived fallback only when an isolated test has no policy file.
    """

    policy = read_policy(path)
    operations = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    raw = operations.get("prompt_transport") if isinstance(operations.get("prompt_transport"), dict) else {}
    try:
        platform_arg_max = int(os.sysconf("SC_ARG_MAX"))
    except (AttributeError, OSError, ValueError):
        platform_arg_max = 0
    derived_inline = max(1, platform_arg_max // 4)
    try:
        inline = int(raw.get("inline_prompt_max_bytes"))
    except (TypeError, ValueError):
        inline = derived_inline
    try:
        trace = int(raw.get("navigator_trace_max_bytes"))
    except (TypeError, ValueError):
        trace = max(1, inline // 2)
    return {
        "schema": str(raw.get("schema") or "leanmill-prompt-transport-policy-v1"),
        "inline_prompt_max_bytes": max(1, inline),
        "navigator_trace_max_bytes": max(1, trace),
        "source": "factory_policy" if raw else "platform_fallback",
        "policy_path": str(path),
    }


def faithfulness_promotion_policy_from_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return publication-staging policy for modeling-faithfulness receipts.

    This does not decide theorem closure. It only controls whether a closed
    campaign may auto-stage a public-review artifact when its theory-first
    modeling receipts are missing or expose unpinned definitions.
    """
    if not isinstance(policy, dict):
        policy = {}
    operations = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    obj = operations.get("faithfulness") if isinstance(operations.get("faithfulness"), dict) else {}

    def bool_value(key: str, fallback: bool) -> bool:
        value = obj.get(key)
        if value is None:
            return bool(fallback)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    return {
        "schema": str(obj.get("schema") or "leanmill-faithfulness-policy-v1"),
        "source": "factory_policy" if obj else "kernel_default",
        "require_def_denotation_receipt_for_auto_promote": bool_value(
            "require_def_denotation_receipt_for_auto_promote", True),
        "require_pinned_def_denotation_for_auto_promote": bool_value(
            "require_pinned_def_denotation_for_auto_promote", True),
        "block_refuted_def_denotation_auto_promote": bool_value(
            "block_refuted_def_denotation_auto_promote", True),
        "block_vacuity_exposed_auto_promote": bool_value(
            "block_vacuity_exposed_auto_promote", False),
    }


def faithfulness_promotion_policy(*, path: str | Path = FACTORY_POLICY) -> dict[str, Any]:
    return faithfulness_promotion_policy_from_policy(read_policy(path))


def definition_api_contract_policy_from_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return policy for definition/API receipt generation and review routing."""
    if not isinstance(policy, dict):
        policy = {}
    operations = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    obj = operations.get("definition_api_contract") if isinstance(
        operations.get("definition_api_contract"), dict) else {}

    def bool_value(key: str, fallback: bool) -> bool:
        value = obj.get(key)
        if value is None:
            return bool(fallback)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    return {
        "schema": str(obj.get("schema") or "leanmill-definition-api-contract-policy-v1"),
        "source": "factory_policy" if obj else "kernel_default",
        "mode": str(obj.get("mode") or "diagnostic"),
        "require_receipt_for_public_review": bool_value("require_receipt_for_public_review", False),
        "warn_on_target_definition_without_named_api": bool_value(
            "warn_on_target_definition_without_named_api", True),
        "warn_on_noncomputable_definition": bool_value("warn_on_noncomputable_definition", True),
        "warn_on_structure_without_visible_invariant": bool_value(
            "warn_on_structure_without_visible_invariant", True),
    }


def definition_api_contract_policy(*, path: str | Path = FACTORY_POLICY) -> dict[str, Any]:
    return definition_api_contract_policy_from_policy(read_policy(path))


def c_supply_breadth_policy_from_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return the strict C-supply breadth policy stanza.

    The policy is a routing and read-model contract. It says how to diagnose
    concentration in credit-ready C supply; it does not grant C credit.
    """
    if not isinstance(policy, dict):
        policy = {}
    operations = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    obj = operations.get("c_supply_breadth_policy") if isinstance(operations.get("c_supply_breadth_policy"), dict) else {}

    def int_value(key: str, fallback: int) -> int:
        try:
            return int(obj.get(key) if obj.get(key) is not None else fallback)
        except (TypeError, ValueError):
            return fallback

    def bool_value(key: str, fallback: bool) -> bool:
        value = obj.get(key)
        if value is None:
            return bool(fallback)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    minimum_rows = max(1, int_value("minimum_credit_ready_rows", int_value("target_credit_ready_rows", 20)))
    growth_goal_rows = max(minimum_rows, int_value("growth_goal_credit_ready_rows", minimum_rows))
    return {
        "schema": str(obj.get("schema") or "leanmill-c-supply-breadth-policy-v1"),
        "source": "factory_policy" if obj else "kernel_default",
        "target_credit_ready_rows": max(1, int_value("target_credit_ready_rows", minimum_rows)),
        "minimum_credit_ready_rows": minimum_rows,
        "growth_goal_credit_ready_rows": growth_goal_rows,
        "continue_after_minimum_floor": bool_value("continue_after_minimum_floor", True),
        "target_credit_ready_family_count": max(1, int_value("target_credit_ready_family_count", 8)),
        "target_credit_ready_source_file_count": max(1, int_value("target_credit_ready_source_file_count", 10)),
        "target_credit_ready_source_root_count": max(1, int_value("target_credit_ready_source_root_count", 3)),
        "max_credit_ready_rows_per_family_before_warning": max(
            1,
            int_value("max_credit_ready_rows_per_family_before_warning", 4),
        ),
        "target_upstream_source_demand_family_count": max(
            1,
            int_value("target_upstream_source_demand_family_count", 6),
        ),
        "source_growth_trigger_mode": str(obj.get("source_growth_trigger_mode") or "breadth_or_count_gap"),
        "source_growth_trigger_rule": str(
            obj.get("source_growth_trigger_rule")
            or (
                "Run upstream source growth whenever strict C row, family, source-file, source-root, "
                "or upstream demand-family targets are short; do not wait for current static/probe "
                "owed work to drain."
            )
        ),
        "outside_source_rule": str(
            obj.get("outside_source_rule")
            or (
                "Outside source scouts may use public Lean/mathlib lookup and the local mathlib lemma index, "
                "but they emit typed source_request inventory only; downstream static, binding, template, "
                "and probe gates decide all credit."
            )
        ),
        "source_bucket_rule": str(
            obj.get("source_bucket_rule")
            or "Count distinct source files and normalized source roots separately; both are diagnostics only."
        ),
        "credit_boundary": str(
            obj.get("credit_boundary")
            or "Breadth metrics diagnose C-supply concentration and sourcing coverage only; they do not grant proof, benchmark, or C credit."
        ),
        "rationale": str(
            obj.get("rationale")
            or "A strict C count concentrated in one family or one source path is fragile and easy to overfit."
        ),
    }


def c_supply_breadth_policy(
    *,
    path: str | Path = FACTORY_POLICY,
) -> dict[str, Any]:
    return c_supply_breadth_policy_from_policy(read_policy(path))


def _heavy_lean_slot_count(runner: dict[str, Any], *, node_id: str) -> int:
    configured: Any = runner.get("heavy_lean_slot_count")
    per_node = runner.get("heavy_lean_slot_count_by_node")
    if isinstance(per_node, dict) and node_id:
        configured = per_node.get(node_id, configured)
    try:
        return max(1, int(configured or 1))
    except (TypeError, ValueError):
        return 1


def lane_budget_plan(
    *,
    path: str | Path = FACTORY_POLICY,
    profile_name: str = "",
    node_id: str | None = None,
) -> dict[str, Any]:
    """Return the policy-owned operational lane budget.

    LeanMill uses one durable queue/event ledger, but scaling decisions must be
    made by named lanes rather than by ad hoc worker flags. This receipt is the
    small contract between policy, watchdog launch, and factory intelligence:
    lane names, worker counts, claim filters, and proof-credit boundaries are
    inspectable before any workers are started.
    """
    policy_path = Path(path)
    policy = read_policy(policy_path)
    profile = ((policy.get("profiles") or {}).get(profile_name) or {}) if profile_name else {}
    runner = profile.get("runner") if isinstance(profile, dict) else {}
    runner = runner if isinstance(runner, dict) else {}
    node = node_id if node_id is not None else os.environ.get("LEANMILL_NODE_ID", "")
    claim_patch_modes = runner.get("agent_worker_claim_patch_modes", "")
    if isinstance(claim_patch_modes, str):
        patch_modes = [part.strip() for part in claim_patch_modes.split(",") if part.strip()]
    elif isinstance(claim_patch_modes, list):
        patch_modes = [str(part).strip() for part in claim_patch_modes if str(part).strip()]
    else:
        patch_modes = []
    heavy_slots = _heavy_lean_slot_count(runner, node_id=node)
    lanes = [
        {
            "lane": "agent_repair",
            "role": "general_subscription_agent",
            "worker_count": max(1, _int_value(runner, "repair_agent_workers", 1)),
            "claim_kinds": ["agent_repair_task", "subscription_agent_task", "agent_task", "agent_repair"],
            "claim_patch_modes": patch_modes,
            "runtime": "codex",
            "max_wall_time_s": _int_value(runner, "agent_max_wall_time_s", 1200),
            "max_iterations": _int_value(runner, "agent_max_iterations", 3),
            "proof_credit_authority": "governance_gate",
        },
        {
            "lane": "source_scout",
            "role": "source_subscription_agent",
            "worker_count": max(0, _int_value(runner, "source_agent_workers", 1)),
            "claim_kinds": ["source_scout_task"],
            "runtime": "codex",
            "proof_credit_authority": "governance_gate",
        },
        {
            "lane": "source_review",
            "role": "upstream_source_request_review",
            "worker_count": max(0, _int_value(runner, "source_review_worker_passes", 0)),
            "claim_kinds": ["llm_proposal_validate"],
            "payload_filter": {"expected_outcome": "source_request"},
            "rule": (
                "Review source-scout transcripts before generic proposal/decomposition work "
                "so upstream sourcing breadth cannot be starved by downstream backlog."
            ),
            "proof_credit_authority": "governance_gate",
        },
        {
            "lane": "source_search",
            "role": "source_retrieval_and_static_filter",
            "worker_count": max(0, _int_value(runner, "source_search_worker_passes", 0)),
            "claim_kinds": ["source_search_task"],
            "rule": (
                "Resolve reviewed source requests into concrete LeanSearch/static-filter "
                "candidate inventory. This is upstream evidence only."
            ),
            "proof_credit_authority": "governance_gate",
        },
        {
            "lane": "source_search_integrator",
            "role": "source_binding_task_integrator",
            "worker_count": max(0, _int_value(runner, "source_search_integrator_passes", 1)),
            "claim_kinds": ["source_search_task"],
            "payload_filter": {"status": "done", "source_search_integrated_at_epoch": None},
            "rule": (
                "Turn qualified source-search artifacts into bounded source-binding work. "
                "Integration produces typed work orders, not proof credit."
            ),
            "proof_credit_authority": "governance_gate",
        },
        {
            "lane": "source_binding_probe",
            "role": "source_bound_canary_probe",
            "worker_count": max(0, _int_value(runner, "source_binding_probe_worker_passes", 0)),
            "claim_kinds": ["repair_canary_probe"],
            "payload_filter": {"probe_lane": "source_binding"},
            "heavy_lean": True,
            "heavy_lean_slot_count": heavy_slots,
            "rule": (
                "Execute only source-bound canary probes created by source binding. "
                "This lane converts source inventory into governed probe evidence; "
                "it does not grant proof credit by itself."
            ),
            "proof_credit_authority": "governance_gate",
        },
        {
            "lane": "probe_family_spec",
            "role": "family_spec_probe",
            "worker_count": max(1, _int_value(runner, "family_spec_probe_workers", 1)),
            "claim_kinds": ["repair_canary_probe"],
            "payload_filter": {"probe_lane": "family_spec"},
            "heavy_lean": True,
            "heavy_lean_slot_count": heavy_slots,
            "proof_credit_authority": "governance_gate",
        },
        {
            "lane": "probe_non_family",
            "role": "non_family_probe",
            "worker_count": max(0, _int_value(runner, "non_family_probe_workers", 1)),
            "claim_kinds": ["repair_canary_probe"],
            "payload_exclude": {"probe_lane": "family_spec"},
            "heavy_lean": True,
            "heavy_lean_slot_count": heavy_slots,
            "proof_credit_authority": "governance_gate",
        },
    ]
    return {
        "schema": "leanmill-lane-budget-plan-v1",
        "profile": profile_name,
        "policy_path": str(policy_path),
        "node_id": node,
        "queue_model": "single_durable_queue_with_policy_lane_budgets",
        "proof_credit_authority": "governance_gate",
        "lane_count": len(lanes),
        "lanes": lanes,
    }


def multi_node_routing_plan(
    *,
    path: str | Path = FACTORY_POLICY,
    profile_name: str = "",
    node_id: str | None = None,
) -> dict[str, Any]:
    """Return the existing deterministic multi-node routing receipt.

    This does not create a second queue or scheduler. It projects the policy's
    multi-node control-plane stanza into the CLI contract already supported by
    ``leanmill_learning_work_seeder.py``: ``--node-id`` plus weighted
    ``--routing-nodes``. If a node id is not supplied by env or caller, routing
    stays disabled so live launchers do not accidentally drop all jobs.
    """
    policy_path = Path(path)
    policy = read_policy(policy_path)
    operations = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    control = operations.get("multi_node_control_plane") if isinstance(operations.get("multi_node_control_plane"), dict) else {}
    routing = control.get("routing") if isinstance(control.get("routing"), dict) else {}
    node = str(node_id if node_id is not None else os.environ.get("LEANMILL_NODE_ID", "")).strip()
    weighted = routing.get("default_weighted_nodes") or routing.get("weighted_nodes") or []
    if isinstance(weighted, str):
        weighted_nodes = [part.strip() for part in weighted.split(",") if part.strip()]
    elif isinstance(weighted, list):
        weighted_nodes = [str(part).strip() for part in weighted if str(part).strip()]
    else:
        weighted_nodes = []
    unique_nodes: list[str] = []
    for item in weighted_nodes:
        base = item.rsplit(":", 1)[0] if ":" in item else item
        if base and base not in unique_nodes:
            unique_nodes.append(base)
    enabled = bool(node and weighted_nodes and node in unique_nodes)
    reason = "ready" if enabled else (
        "missing_node_id" if not node else
        "no_weighted_nodes_configured" if not weighted_nodes else
        "node_id_not_in_policy_routing_nodes"
    )
    return {
        "schema": "leanmill-multi-node-routing-plan-v1",
        "profile": profile_name,
        "policy_path": str(policy_path),
        "enabled": enabled,
        "reason": reason,
        "node_id": node,
        "mode": str(routing.get("mode") or "deterministic_weighted_hash"),
        "routing_nodes": unique_nodes,
        "weighted_routing_nodes": weighted_nodes,
        "routing_nodes_arg": ",".join(weighted_nodes),
        "queue_model": "single_durable_queue_with_policy_node_filtering",
        "proof_credit_authority": "governance_gate",
    }


__all__ = [
    "read_policy",
    "apply_profile_section",
    "c_supply_breadth_policy",
    "c_supply_breadth_policy_from_policy",
    "lane_budget_plan",
    "multi_node_routing_plan",
    "priority_policy_from_policy",
    "priority_value_from_policy",
    "priority_value",
    "semantic_reference_threshold",
    "prompt_transport_policy",
    "FACTORY_POLICY",
]


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        policy = Path(td) / "policy.json"
        policy.write_text(json.dumps({
            "schema": "leanmill-factory-policy-v1",
            "profiles": {
                "p": {
                    "runner": {
                        "sleep_s": 7,
                        "unknown_key": "ignored",
                    }
                }
            },
        }) + "\n")
        ns = Namespace(factory_policy=str(policy), policy_profile="p", sleep_s=1)
        receipt = apply_profile_section(ns, section="runner")
        assert ns.sleep_s == 7
        assert receipt["key_count"] == 1
        assert receipt["keys"] == ["sleep_s"]
        plan = lane_budget_plan(path=policy, profile_name="p", node_id="node-a")
        assert plan["schema"] == "leanmill-lane-budget-plan-v1"
        assert plan["queue_model"] == "single_durable_queue_with_policy_lane_budgets"
        assert {lane["lane"] for lane in plan["lanes"]} == {
            "agent_repair",
            "source_scout",
            "source_review",
            "source_search",
            "source_search_integrator",
            "source_binding_probe",
            "probe_family_spec",
            "probe_non_family",
        }
        assert next(lane for lane in plan["lanes"] if lane["lane"] == "source_review")["worker_count"] == 0
        policy.write_text(json.dumps({
            "operations": {
                "multi_node_control_plane": {
                    "routing": {"default_weighted_nodes": ["node-a:1", "node-b:2"]}
                }
            }
        }) + "\n")
        route = multi_node_routing_plan(path=policy, profile_name="p", node_id="node-b")
        assert route["enabled"] is True and route["routing_nodes_arg"] == "node-a:1,node-b:2", route
        missing = multi_node_routing_plan(path=policy, profile_name="p", node_id="")
        assert missing["enabled"] is False and missing["reason"] == "missing_node_id", missing
        policy.write_text(json.dumps({
            "operations": {
                "priority_policy": {
                    "schema": "leanmill-priority-policy-v1",
                    "ordering_rule": "higher_integer_priority_claims_first",
                    "work_queue": {"source_search_from_llm_proposal": 92},
                    "recommendations": {"evaluation_harness_ready_for_credited_run": 145},
                }
            }
        }) + "\n")
        parsed = read_policy(policy)
        assert priority_policy_from_policy(parsed)["ordering_rule"] == "higher_integer_priority_claims_first"
        assert priority_value_from_policy(
            parsed,
            namespace="recommendations",
            key="evaluation_harness_ready_for_credited_run",
            fallback=1,
        ) == 145
        assert priority_value(path=policy, namespace="work_queue", key="missing", fallback=7) == 7
        policy.write_text(json.dumps({
            "operations": {
                "faithfulness": {
                    "require_pinned_def_denotation_for_auto_promote": False,
                    "block_vacuity_exposed_auto_promote": True,
                }
            }
        }) + "\n")
        fp = faithfulness_promotion_policy(path=policy)
        assert fp["require_pinned_def_denotation_for_auto_promote"] is False
        assert fp["block_vacuity_exposed_auto_promote"] is True
    print("ztare.leanmill.policy self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps({"policy": FACTORY_POLICY, "status": "ready"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
