from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Mapping


ActionRoute = Literal[
    "in_turn_cli",
    "parent_kernel",
    "capability_proposal",
    "invalid_action_request",
]


@dataclass(frozen=True)
class VisibleWorkbenchActionRoute:
    capability_id: str
    route: ActionRoute
    reason: str
    authority: str
    secret_policy: str
    suggested_command: list[str] = ()
    parameter_domains: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["suggested_command"] = list(self.suggested_command)
        if self.parameter_domains:
            payload["parameter_domains"] = {
                path: list(values) for path, values in self.parameter_domains.items()
            }
        else:
            payload.pop("parameter_domains", None)
        return payload


_IN_TURN_CLI_ROUTES: dict[str, VisibleWorkbenchActionRoute] = {
    "run_visible_json_probe": VisibleWorkbenchActionRoute(
        capability_id="run_visible_json_probe",
        route="in_turn_cli",
        reason="pure visible diagnostic over staged JSON artifacts",
        authority="pure_diagnostic",
        secret_policy="public_only",
        suggested_command=[
            "python3",
            "-m",
            "ztare.common.visible_workbench_cli",
            "probe-json",
            "--artifact",
            "<visible-json-ref>",
        ],
    ),
    "check_worldmodel_carrier_contract": VisibleWorkbenchActionRoute(
        capability_id="check_worldmodel_carrier_contract",
        route="in_turn_cli",
        reason="pure syntax and transition-contract preflight over candidate text",
        authority="pure_diagnostic",
        secret_policy="public_only",
        suggested_command=[
            "python3",
            "-m",
            "ztare.common.visible_workbench_cli",
            "check-worldmodel-carrier",
            "--source",
            "-",
        ],
    ),
    "check_receipt_compatibility": VisibleWorkbenchActionRoute(
        capability_id="check_receipt_compatibility",
        route="in_turn_cli",
        reason="pure receipt and typed-payload compatibility preflight",
        authority="pure_diagnostic",
        secret_policy="public_only",
        suggested_command=[
            "python3",
            "-m",
            "ztare.common.visible_workbench_cli",
            "check-receipt",
            "--kind",
            "auto",
            "--source",
            "-",
        ],
    ),
    "score_worldmodel_candidate_delta": VisibleWorkbenchActionRoute(
        capability_id="score_worldmodel_candidate_delta",
        route="in_turn_cli",
        reason="aggregate candidate-delta scorer bound to the authority project manifest",
        authority="scorer",
        secret_policy="sealed_aggregate_only",
        suggested_command=[
            "python3",
            "-m",
            "ztare.common.visible_workbench_cli",
            "score-worldmodel-candidate",
            "--source",
            "-",
        ],
    ),
    "join_lowerable_selectors": VisibleWorkbenchActionRoute(
        capability_id="join_lowerable_selectors",
        route="in_turn_cli",
        reason="compose partial selector receipts by partial-function coproduct",
        authority="pure_diagnostic",
        secret_policy="public_only",
        suggested_command=[
            "python3",
            "-m",
            "ztare.common.visible_workbench_cli",
            "run-action",
            "--source",
            "-",
        ],
    ),
}

_LOCAL_DIAGNOSTIC_RECEIPT_CAPABILITIES = frozenset(
    {*_IN_TURN_CLI_ROUTES.keys(), "route_action", "rank_next_morphisms"}
)
VISIBLE_WORKBENCH_COMMAND_ALIASES: dict[str, str] = {
    "probe-json": "run_visible_json_probe",
    "check-worldmodel-carrier": "check_worldmodel_carrier_contract",
    "score-worldmodel-candidate": "score_worldmodel_candidate_delta",
    "check-receipt": "check_receipt_compatibility",
    "join-lowerable-selectors": "join_lowerable_selectors",
    "route-action": "route_action",
    "run-action": "run_action",
    "rank-next-morphisms": "rank_next_morphisms",
}
def visible_workbench_action_routes() -> dict[str, dict[str, Any]]:
    return visible_workbench_capability_routes(route_filter="in_turn_cli")


def visible_workbench_capability_routes(
    *, route_filter: ActionRoute | None = None
) -> dict[str, dict[str, Any]]:
    """Return the canonical capability route registry for visible workbenches."""

    routes = dict(_IN_TURN_CLI_ROUTES)
    routes.update(_adapter_registered_routes())
    if route_filter is not None:
        routes = {key: route for key, route in routes.items() if route.route == route_filter}
    return {key: route.to_dict() for key, route in sorted(routes.items())}


def visible_workbench_parent_kernel_routes() -> dict[str, dict[str, Any]]:
    return visible_workbench_capability_routes(route_filter="parent_kernel")


def visible_workbench_in_turn_routes() -> dict[str, dict[str, Any]]:
    return visible_workbench_capability_routes(route_filter="in_turn_cli")


def visible_workbench_local_action_ids() -> frozenset[str]:
    return frozenset(_IN_TURN_CLI_ROUTES)


def visible_workbench_attempt_claim_ids() -> frozenset[str]:
    """Vocabulary that denotes a visible workbench command/capability attempt."""

    return frozenset(
        {
            *visible_workbench_capability_routes().keys(),
            *VISIBLE_WORKBENCH_COMMAND_ALIASES.keys(),
            *VISIBLE_WORKBENCH_COMMAND_ALIASES.values(),
        }
    )


def visible_workbench_local_adapter_action_ids() -> frozenset[str]:
    try:
        from ztare.worldmodel.leaf_workbench import worldmodel_leaf_workbench_action_environment

        env = worldmodel_leaf_workbench_action_environment()
        return frozenset(str(item) for item in (env.get("local_cli_actions") or ()) if str(item))
    except Exception:  # noqa: BLE001
        return frozenset()


def is_visible_workbench_local_diagnostic_receipt(payload: object) -> bool:
    """Return True for copied visible-workbench diagnostics.

    These receipts are leaf-local breadcrumbs, not parent-owned authority
    receipts.  The authority boundary is the capability route: in-turn tools may
    inform the candidate the leaf submits, but replay/holdout gates still decide
    whether the candidate is admissible.
    """

    if not isinstance(payload, Mapping):
        return False
    if str(payload.get("schema") or "") == "ztare-visible-workbench-cli-receipt-v1":
        return str(payload.get("authority") or "") in {"pure_diagnostic", "scorer"}
    capability_id = str(payload.get("capability_id") or "").strip()
    input_hashes = payload.get("input_hashes")
    if not isinstance(input_hashes, Mapping):
        return False
    receipt_ref = str(input_hashes.get("receipt_ref") or payload.get("output_ref") or "").strip()
    if receipt_ref.startswith("workspace/visible_cli_receipts/"):
        return True
    if capability_id in visible_workbench_local_adapter_action_ids() and _looks_visible_local_action_copy(
        payload, input_hashes
    ):
        return True
    if capability_id not in _LOCAL_DIAGNOSTIC_RECEIPT_CAPABILITIES:
        return False
    if capability_id in _LOCAL_DIAGNOSTIC_RECEIPT_CAPABILITIES:
        return True
    return False


def _looks_visible_local_action_copy(payload: Mapping[str, Any], input_hashes: Mapping[str, Any]) -> bool:
    if str(input_hashes.get("request") or "").strip():
        return True
    for binding in payload.get("claim_bindings") or ():
        if str(binding or "").strip().startswith("visible local action "):
            return True
    return False


def route_visible_workbench_action_request(request: Mapping[str, Any]) -> dict[str, Any]:
    payload = _action_request_payload(request)
    capability_id = str(payload.get("capability_id") or "").strip()
    if not capability_id:
        raise ValueError("LEAF_WORKBENCH_ACTION_REQUEST requires payload.capability_id.")
    next_gate = payload.get("required_next_gate")
    next_gate_command = (
        str(next_gate.get("command") or "").strip()
        if isinstance(next_gate, Mapping)
        else ""
    )
    if capability_id == "tool_synthesis" or next_gate_command == "tool_synthesis_gate":
        return VisibleWorkbenchActionRoute(
            capability_id=capability_id,
            route="capability_proposal",
            reason=(
                "tool synthesis is a Strategy/meta-work item, not a registered "
                "leaf workbench action; in science mode submit an executable "
                "candidate or LOWERABILITY_BLOCKED with the tool gap named inside it, "
                "not LEAF_WORKBENCH_ACTION_REQUEST"
            ),
            authority="proposal_only",
            secret_policy="contract_declared",
        ).to_dict() | {"status": "ok"}
    route = _IN_TURN_CLI_ROUTES.get(capability_id) or _adapter_registered_route(capability_id)
    if route is not None:
        parameter_error = _action_parameter_error(route, payload)
        if parameter_error:
            return VisibleWorkbenchActionRoute(
                capability_id=capability_id,
                route="invalid_action_request",
                reason=parameter_error,
                authority="none",
                secret_policy="public_only",
            ).to_dict() | {"status": "fail"}
        return route.to_dict() | {"status": "ok"}
    if next_gate_command:
        reason = (
            "required_next_gate.command is a gate command, not a capability_id; "
            "use capability_id=run_strategy_required_gate with the gate command "
            "inside the payload"
        )
    else:
        reason = (
            "unknown capability_id; use a registered workbench capability or "
            "report the missing sensor/morphism inside LOWERABILITY_BLOCKED"
        )
    return VisibleWorkbenchActionRoute(
        capability_id=capability_id,
        route="invalid_action_request",
        reason=reason,
        authority="none",
        secret_policy="public_only",
    ).to_dict() | {"status": "fail"}


def _adapter_registered_route(capability_id: str) -> VisibleWorkbenchActionRoute | None:
    """Route capabilities registered by the staged substrate workbench adapter."""

    return _adapter_registered_routes().get(capability_id)


def _adapter_registered_routes() -> dict[str, VisibleWorkbenchActionRoute]:
    try:
        from ztare.worldmodel.leaf_workbench import worldmodel_leaf_workbench_action_environment
    except ModuleNotFoundError as exc:
        # An installation without the worldmodel adapter legitimately has only
        # the common routes.  A missing dependency *inside* an installed
        # adapter is an apparatus failure and must retain its causal exception;
        # coercing it to an empty registry fabricates "unknown capability".
        if exc.name == "ztare.worldmodel.leaf_workbench":
            return {}
        raise
    env = worldmodel_leaf_workbench_action_environment()
    contract = env.get("contract")
    handlers = env.get("action_handlers") if isinstance(env, Mapping) else {}
    parameter_domains = env.get("action_parameter_domains") if isinstance(env, Mapping) else {}
    local_cli_actions = {str(item) for item in (env.get("local_cli_actions") or ()) if str(item)}
    registry = contract.registry() if contract is not None else {}
    routes: dict[str, VisibleWorkbenchActionRoute] = {}
    for capability_id in sorted(str(item) for item in (handlers or {}) if str(item)):
        if capability_id in _IN_TURN_CLI_ROUTES:
            continue
        cap = registry.get(capability_id)
        authority = str(getattr(cap, "authority", "") or "kernel_registered")
        secret_policy = str(getattr(cap, "secret_policy", "") or "contract_declared")
        raw_domains = parameter_domains.get(capability_id, {}) if isinstance(parameter_domains, Mapping) else {}
        domains = {
            str(path): tuple(sorted({str(value) for value in values if str(value)}))
            for path, values in raw_domains.items()
        } if isinstance(raw_domains, Mapping) else {}
        if capability_id in local_cli_actions:
            routes[capability_id] = VisibleWorkbenchActionRoute(
                capability_id=capability_id,
                route="in_turn_cli",
                reason="registered adapter action declared safe for staged local execution",
                authority=authority,
                secret_policy=secret_policy,
                parameter_domains=domains,
                suggested_command=[
                    "python3",
                    "-m",
                    "ztare.common.visible_workbench_cli",
                    "run-action",
                    "--source",
                    "-",
                ],
            )
        else:
            routes[capability_id] = VisibleWorkbenchActionRoute(
                capability_id=capability_id,
                route="parent_kernel",
                reason="registered by staged substrate workbench adapter",
                authority=authority,
                secret_policy=secret_policy,
                parameter_domains=domains,
            )
    return routes


def _action_parameter_error(
    route: VisibleWorkbenchActionRoute, payload: Mapping[str, Any]
) -> str:
    for path, allowed in route.parameter_domains.items():
        value = _mapping_path_value(payload, path)
        if value in (None, ""):
            continue
        if str(value) not in allowed:
            return (
                f"{path}={value!r} is outside the registered executable domain "
                f"{list(allowed)!r} for {route.capability_id!r}; a verification obligation "
                "without a registered action remains candidate-bound"
            )
    return ""


def _mapping_path_value(payload: Mapping[str, Any], path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def _action_request_payload(request: Mapping[str, Any]) -> Mapping[str, Any]:
    request_type = str(request.get("type") or "").strip()
    if request_type == "LEAF_WORKBENCH_ACTION_REQUEST":
        payload = request.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("LEAF_WORKBENCH_ACTION_REQUEST requires object payload.")
        return payload
    return request
