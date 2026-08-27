#!/usr/bin/env python3
"""Run a direct GPT-5.6 Responses agent against one ARC-AGI-3 game.

This is a baseline harness, separate from the compiled world-model controller.
The model sees every settled frame, chooses every charged action, and continues
through one ``previous_response_id`` chain with explicit persisted reasoning.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

from PIL import Image

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.common.llm_runtime import bootstrap_dotenv_from_repo_root  # noqa: E402
from ztare.common.persistent_reasoning_controller import (  # noqa: E402
    PersistentResponsesToolThread,
)
from ztare.common.wake_sleep_credit_router import (  # noqa: E402
    MemoryCandidate,
    MemoryScope,
    WakeSleepCreditState,
    select_sparse_memories,
)
from ztare.substrates.arc_agi3 import (  # noqa: E402
    ArcAgi3Adapter,
    list_games,
)


_ARC_PALETTE = (
    (0, 0, 0),
    (0, 116, 217),
    (255, 65, 54),
    (46, 204, 64),
    (255, 220, 0),
    (170, 170, 170),
    (240, 18, 190),
    (255, 133, 27),
    (127, 219, 255),
    (135, 12, 37),
    (255, 255, 255),
    (100, 100, 100),
    (180, 180, 180),
    (80, 80, 80),
    (210, 210, 210),
    (40, 40, 40),
)
_ACTION_SCHEMA = (
    REPO
    / "scripts/public/control/schemas/arc3_subscription_action.schema.json"
)
_PROPOSAL_SCHEMA = (
    REPO
    / "scripts/public/control/schemas/arc3_subscription_proposal.schema.json"
)
_OBJECT_LINKED_PROPOSAL_SCHEMA = (
    REPO
    / "scripts/public/control/schemas/"
    "arc3_subscription_object_linked_proposal.schema.json"
)
_CATALOG_SCOPED_PROPOSAL_SCHEMA = (
    REPO
    / "scripts/public/control/schemas/"
    "arc3_subscription_catalog_scoped_proposal.schema.json"
)
_SLEEP_SCHEMA = (
    REPO
    / "scripts/public/control/schemas/arc3_subscription_sleep.schema.json"
)


def _resolve_game_id(game: str) -> str:
    value = str(game or "").strip()
    if "-" in value:
        return value
    match = next((item for item in list_games() if item.startswith(value)), None)
    if match is None:
        raise ValueError(f"game {game!r} not found")
    return str(match)


def _row_runs(row: Sequence[int]) -> str:
    if not row:
        return ""
    runs: list[str] = []
    start = int(row[0])
    count = 1
    for raw in row[1:]:
        value = int(raw)
        if value == start:
            count += 1
        else:
            runs.append(f"{start}x{count}")
            start = value
            count = 1
    runs.append(f"{start}x{count}")
    return ",".join(runs)


def grid_rle(grid: Sequence[Sequence[int]]) -> list[str]:
    return [_row_runs(row) for row in grid]


def grid_png_data_url(
    grid: Sequence[Sequence[int]],
    *,
    scale: int = 8,
) -> str:
    height = len(grid)
    width = len(grid[0]) if height else 0
    if height == 0 or width == 0:
        raise ValueError("grid must be non-empty")
    if any(len(row) != width for row in grid):
        raise ValueError("grid must be rectangular")
    image = Image.new("RGB", (width, height))
    image.putdata([
        _ARC_PALETTE[int(cell) % len(_ARC_PALETTE)]
        for row in grid
        for cell in row
    ])
    image = image.resize(
        (width * int(scale), height * int(scale)),
        resample=Image.Resampling.NEAREST,
    )
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _sha_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def settled_observation_receipt(
    grid: Sequence[Sequence[int]],
    *,
    observation_index: int,
    action_count: int,
    levels_completed: int,
    adapter_epoch: int,
    available_action_indices: Sequence[int],
) -> dict[str, Any]:
    payload = {
        "schema": "ztare-arc3-settled-observation-v1",
        "observation_index": int(observation_index),
        "action_count": int(action_count),
        "levels_completed": int(levels_completed),
        "adapter_epoch": int(adapter_epoch),
        "available_action_indices": list(available_action_indices),
        "grid_shape": [len(grid), len(grid[0]) if grid else 0],
        "grid_rle_rows": grid_rle(grid),
    }
    return {
        **payload,
        "sha256": _sha_payload(payload),
    }


def _transition_identity_receipt(adapter: Any) -> dict[str, Any] | None:
    identity = getattr(adapter, "last_transition_identity", None)
    if identity is None:
        return None
    to_dict = getattr(identity, "to_dict", None)
    if not callable(to_dict):
        return None
    payload = to_dict()
    return dict(payload) if isinstance(payload, dict) else None


def subscription_arc_instructions(
    *,
    budget: int,
    action_arity: int,
) -> str:
    """Controller instructions shared by ordinary and instrumented probes."""

    return (
        "You are controlling an unknown interactive 2D grid game. Infer its "
        "rules only from the observation/action chronology in this continuing "
        "session. Complete as many levels as possible within "
        f"{int(budget)} charged actions. Test uncertain hypotheses with "
        "discriminating actions, avoid repeating disproven actions in an "
        "unchanged visible context, and return exactly one action per turn. "
        "Action -1 resets. Other action indices are stable integers "
        f"0 through {int(action_arity) - 1}. Do not assume puzzle-specific "
        "knowledge."
    )


def observation_content(
    grid: Sequence[Sequence[int]],
    *,
    action_count: int,
    levels_completed: int,
    available_action_indices: Sequence[int],
) -> list[dict[str, Any]]:
    metadata = {
        "schema": "ztare-arc3-direct-observation-v1",
        "action_count": int(action_count),
        "levels_completed": int(levels_completed),
        "available_action_indices": list(available_action_indices),
        "grid_shape": [len(grid), len(grid[0]) if grid else 0],
        "grid_rle_rows": grid_rle(grid),
    }
    return [
        {
            "type": "input_text",
            "text": json.dumps(metadata, separators=(",", ":")),
        },
        {
            "type": "input_image",
            "image_url": grid_png_data_url(grid),
            "detail": "high",
        },
    ]


def action_tool(action_arity: int) -> dict[str, Any]:
    return {
        "type": "function",
        "name": "take_arc_action",
        "description": (
            "Execute exactly one charged environment action. "
            "Use -1 only to reset; indices 0 through action_arity-1 map "
            "stably to the environment's listed actions."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "integer",
                    "enum": [-1, *range(action_arity)],
                },
                "prediction": {
                    "type": "string",
                    "description": (
                        "A short falsifiable prediction of the next visible "
                        "change; this is recorded but not scored as an action."
                    ),
                },
            },
            "required": ["action", "prediction"],
            "additionalProperties": False,
        },
    }


class CodexSubscriptionArcThread:
    """One resumed, tool-sealed Codex subscription conversation."""

    def __init__(
        self,
        *,
        model_id: str,
        reasoning_effort: str,
        instructions: str,
        timeout_seconds: float,
        resume_session: bool = True,
        exchange_observer: (
            Callable[[Mapping[str, Any]], None] | None
        ) = None,
        runner=None,
    ) -> None:
        self.model_id = model_id
        self.reasoning_effort = reasoning_effort
        self.instructions = instructions
        self.timeout_seconds = int(timeout_seconds)
        self.resume_session = bool(resume_session)
        self.exchange_observer = exchange_observer
        self.session_state: dict[str, Any] | None = None
        self._runner = runner
        self._turn_index = 0
        # Compatibility name retained for historical H86 receipts.  The
        # value now authorizes exactly the next decision prompt and is burned
        # before that inference is attempted.
        self.active_sleep_digest: dict[str, Any] | None = None
        self.active_recall_consumption_receipt: (
            dict[str, Any] | None
        ) = None

    def queue_recall_digest(
        self,
        digest: Mapping[str, Any],
        *,
        consumption_receipt: Mapping[str, Any] | None = None,
    ) -> None:
        """Authorize one direct memory injection on the next decision."""

        if self.active_sleep_digest is not None:
            raise RuntimeError("a recall injection is already pending")
        self.active_sleep_digest = dict(digest)
        self.active_recall_consumption_receipt = (
            dict(consumption_receipt)
            if consumption_receipt is not None
            else None
        )

    def _run_json(
        self,
        *,
        prompt: str,
        output_schema: Path,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        from ztare.common.subscription_agent_runtime import (
            CODEX_SANDBOX_SEALED_COMPLETION,
            run_subscription_agent_with_recovery,
        )

        runner = self._runner or run_subscription_agent_with_recovery
        previous_effort = os.environ.get(
            "ZTARE_CODEX_AGENT_REASONING_EFFORT"
        )
        os.environ["ZTARE_CODEX_AGENT_REASONING_EFFORT"] = (
            self.reasoning_effort
        )
        try:
            run = runner(
                runtime="codex",
                prompt=prompt,
                agent_id="arc3::persistent_subscription_actor",
                repo=REPO,
                session_state=(
                    self.session_state if self.resume_session else None
                ),
                timeout_seconds=self.timeout_seconds,
                default_codex_model=self.model_id,
                codex_sandbox=CODEX_SANDBOX_SEALED_COMPLETION,
                output_schema=output_schema,
            )
        finally:
            if previous_effort is None:
                os.environ.pop(
                    "ZTARE_CODEX_AGENT_REASONING_EFFORT",
                    None,
                )
            else:
                os.environ["ZTARE_CODEX_AGENT_REASONING_EFFORT"] = (
                    previous_effort
                )
        result = run.result
        if self.exchange_observer is not None:
            self.exchange_observer({
                "schema": "ztare-codex-subscription-exchange-v1",
                "turn_index": self._turn_index,
                "prompt": prompt,
                "output_schema": str(output_schema),
                "returncode": int(result.returncode),
                "stdout": str(result.stdout or ""),
                "stderr": str(result.stderr or ""),
                "final_session_state": dict(
                    run.final_session_state or {}
                ),
            })
        if result.returncode != 0:
            raise RuntimeError(
                "Codex subscription action turn failed "
                f"(rc={result.returncode}): {(result.stderr or '')[-800:]}"
            )
        try:
            payload = json.loads((result.stdout or "").strip())
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Codex subscription turn returned non-JSON output"
            ) from exc
        if not isinstance(payload, dict):
            raise RuntimeError(
                "Codex subscription turn returned a non-object"
            )
        self.session_state = run.final_session_state
        if not self.session_state or not self.session_state.get("session_id"):
            raise RuntimeError(
                "Codex subscription action turn omitted session identity"
            )
        return payload, dict(self.session_state)

    def _burn_recall_for_observation(
        self,
        observation: Mapping[str, Any],
    ) -> tuple[
        dict[str, Any] | None,
        dict[str, Any] | None,
        str,
    ]:
        """Consume one queued recall before an inference attempt."""

        injected_digest = self.active_sleep_digest
        consumption_receipt = self.active_recall_consumption_receipt
        recall_block = ""
        if injected_digest:
            if consumption_receipt is not None:
                if consumption_receipt.get("status") != "consumed":
                    raise RuntimeError(
                        "recall injection lacks a consumed authorization"
                    )
                if (
                    str(consumption_receipt.get("observation_sha256") or "")
                    != str(observation.get("sha256") or "")
                ):
                    raise RuntimeError(
                        "recall injection observation identity drifted"
                    )
            recall_block = (
                "\n\nRECALLED CONSOLIDATED MEMORY "
                "(evidence-derived, advisory, preserve its guards):\n"
                f"{json.dumps(injected_digest, separators=(',', ':'))}"
            )
        # Burn before the external inference call.  An ambiguous transport
        # failure must not cause the same direct authorization to be replayed.
        self.active_sleep_digest = None
        self.active_recall_consumption_receipt = None
        return injected_digest, consumption_receipt, recall_block

    @staticmethod
    def _recall_receipt(
        injected_digest: Mapping[str, Any] | None,
        consumption_receipt: Mapping[str, Any] | None,
    ) -> dict[str, Any] | None:
        if injected_digest is None:
            return None
        return {
            "digest_sha256": _sha_payload(injected_digest),
            "consumption_receipt_sha256": str(
                (consumption_receipt or {}).get("sha256") or ""
            ),
            "direct_injection_count": 1,
        }

    def propose(
        self,
        observation: Mapping[str, Any],
        *,
        object_catalog: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Emit a blind proposal without executing or consuming recall."""

        if self.active_sleep_digest is not None:
            raise RuntimeError(
                "blind proposal cannot be generated with pending recall"
            )
        catalog_block = ""
        output_schema = _PROPOSAL_SCHEMA
        binding_instruction = ""
        if object_catalog is not None:
            catalog_schema = str(object_catalog.get("schema") or "")
            if catalog_schema not in {
                "ztare-grid-object-catalog-v1",
                "ztare-grid-object-catalog-presentation-v1",
            }:
                raise RuntimeError("unknown object catalog schema")
            if str(object_catalog.get("observation_sha256") or "") != (
                str(observation.get("sha256") or "")
            ):
                raise RuntimeError(
                    "proposal object catalog observation drifted"
                )
            objects = object_catalog.get("objects")
            if not isinstance(objects, list) or not objects:
                raise RuntimeError("proposal object catalog is empty")
            if catalog_schema == (
                "ztare-grid-object-catalog-presentation-v1"
            ):
                catalog_block = (
                    "\n\nCATALOG-SCOPED OBJECT PRESENTATION:\n"
                    f"{json.dumps(dict(object_catalog), separators=(',', ':'))}"
                    "\nBind the object you expect the action to control using "
                    "its short handle. List other objects your current plan "
                    "must visit or change, in order, as "
                    "ordered_waypoint_handles. Handles are local pointers, "
                    "not semantic role names."
                )
                output_schema = _CATALOG_SCOPED_PROPOSAL_SCHEMA
                binding_instruction = (
                    " Also return the controlled object handle and ordered "
                    "waypoint handles from that presentation."
                )
            else:
                catalog_block = (
                    "\n\nCONTENT-ADDRESSED OBJECT CATALOG:\n"
                    f"{json.dumps(dict(object_catalog), separators=(',', ':'))}"
                    "\nBind the object you expect the action to control using "
                    "its exact object_ref. List other objects your current "
                    "plan must visit or change, in order, as "
                    "ordered_waypoint_refs. Do not infer object identity from "
                    "a nickname when a catalog ref is available."
                )
                output_schema = _OBJECT_LINKED_PROPOSAL_SCHEMA
                binding_instruction = (
                    " Also return the exact controlled object ref and ordered "
                    "waypoint refs from that catalog."
                )
        prompt = (
            f"{self.instructions}\n\n"
            f"TURN {self._turn_index}: BLIND PROPOSAL PHASE\n"
            "SETTLED OBSERVATION (lossless row runs):\n"
            f"{json.dumps(dict(observation), separators=(',', ':'))}"
            f"{catalog_block}\n\n"
            "Do not execute an action. Return your current proposed next "
            "action, a falsifiable visible prediction, a short ordered plan "
            f"summary, and the main uncertainty.{binding_instruction} "
            "No recalled memory or external decision "
            "intervention is available in this phase."
        )
        row, session_state = self._run_json(
            prompt=prompt,
            output_schema=output_schema,
        )
        self.session_state = dict(session_state)
        receipt = {
            "schema": "ztare-codex-subscription-proposal-v1",
            "phase": "blind_pre_proposal",
            "turn_index": self._turn_index,
            "session_id": str(session_state["session_id"]),
            "session_tick_count": int(
                session_state.get("tick_count") or 0
            ),
            "action": row.get("action"),
            "prediction": str(row.get("prediction") or ""),
            "plan_summary": str(row.get("plan_summary") or ""),
            "uncertainty": str(row.get("uncertainty") or ""),
            "model": self.model_id,
            "reasoning_effort": self.reasoning_effort,
            "continuation": (
                "codex_exec_resume"
                if self.resume_session
                else "fresh_codex_session"
            ),
            "observation_sha256": str(
                observation.get("sha256") or ""
            ),
            "recall_injection": None,
        }
        if object_catalog is not None:
            receipt["catalog_sha256"] = str(
                object_catalog.get("catalog_sha256") or ""
            )
            if object_catalog.get("schema") == (
                "ztare-grid-object-catalog-presentation-v1"
            ):
                receipt.update({
                    "presentation_sha256": str(
                        object_catalog.get(
                            "presentation_sha256"
                        ) or ""
                    ),
                    "controlled_object_handle": str(
                        row.get("controlled_object_handle") or ""
                    ),
                    "ordered_waypoint_handles": list(
                        row.get("ordered_waypoint_handles") or []
                    ),
                })
            else:
                receipt.update({
                    "controlled_object_ref": str(
                        row.get("controlled_object_ref") or ""
                    ),
                    "ordered_waypoint_refs": list(
                        row.get("ordered_waypoint_refs") or []
                    ),
                })
        return receipt

    def revise(
        self,
        observation: Mapping[str, Any],
        *,
        pre_proposal: Mapping[str, Any],
        object_catalog: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Commit a same-observation proposal after offer or withholding."""

        if (
            str(pre_proposal.get("observation_sha256") or "")
            != str(observation.get("sha256") or "")
        ):
            raise RuntimeError(
                "proposal revision observation identity drifted"
            )
        if self.session_state is None or (
            str(pre_proposal.get("session_id") or "")
            != str(self.session_state.get("session_id") or "")
        ):
            raise RuntimeError(
                "proposal revision controller session drifted"
            )
        catalog_block = ""
        output_schema = _PROPOSAL_SCHEMA
        binding_instruction = ""
        if object_catalog is not None:
            catalog_schema = str(object_catalog.get("schema") or "")
            catalog_sha = str(
                object_catalog.get("catalog_sha256") or ""
            )
            if (
                catalog_schema not in {
                    "ztare-grid-object-catalog-v1",
                    "ztare-grid-object-catalog-presentation-v1",
                }
                or str(
                    object_catalog.get("observation_sha256") or ""
                )
                != str(observation.get("sha256") or "")
            ):
                raise RuntimeError(
                    "revision object catalog authority drifted"
                )
            if str(pre_proposal.get("catalog_sha256") or "") != (
                catalog_sha
            ):
                raise RuntimeError(
                    "proposal revision changed object catalog"
                )
            if catalog_schema == (
                "ztare-grid-object-catalog-presentation-v1"
            ):
                if str(
                    pre_proposal.get("presentation_sha256") or ""
                ) != str(
                    object_catalog.get("presentation_sha256") or ""
                ):
                    raise RuntimeError(
                        "proposal revision changed catalog presentation"
                    )
                catalog_block = (
                    "\n\nCATALOG-SCOPED OBJECT PRESENTATION "
                    "(unchanged from the blind proposal):\n"
                    f"{json.dumps(dict(object_catalog), separators=(',', ':'))}"
                    "\nReturn exact local handle values. The environment has "
                    "not advanced, so cross-presentation handles are invalid."
                )
                output_schema = _CATALOG_SCOPED_PROPOSAL_SCHEMA
                binding_instruction = (
                    " Bind the controlled object handle and ordered waypoint "
                    "handles again."
                )
            else:
                catalog_block = (
                    "\n\nCONTENT-ADDRESSED OBJECT CATALOG "
                    "(unchanged from the blind proposal):\n"
                    f"{json.dumps(dict(object_catalog), separators=(',', ':'))}"
                    "\nReturn exact catalog object_ref values. The "
                    "environment has not advanced, so cross-catalog refs are "
                    "invalid."
                )
                output_schema = _OBJECT_LINKED_PROPOSAL_SCHEMA
                binding_instruction = (
                    " Bind the controlled object ref and ordered waypoint "
                    "refs again."
                )
        (
            injected_digest,
            consumption_receipt,
            recall_block,
        ) = self._burn_recall_for_observation(observation)
        assignment_block = (
            recall_block
            if recall_block
            else (
                "\n\nCONTROL ASSIGNMENT: no external decision "
                "intervention is offered. Reconsider once using only the "
                "settled observation and your blind proposal; do not invent "
                "recalled facts."
            )
        )
        prompt = (
            f"{self.instructions}\n\n"
            f"TURN {self._turn_index}: PROPOSAL REVISION PHASE\n"
            "The environment has not advanced. The settled observation is "
            "still:\n"
            f"{json.dumps(dict(observation), separators=(',', ':'))}\n\n"
            "BLIND PARENT PROPOSAL:\n"
            f"{json.dumps(dict(pre_proposal), separators=(',', ':'))}"
            f"{catalog_block}{assignment_block}\n\n"
            "Return the committed next action, falsifiable visible "
            "prediction, short ordered plan summary, and main uncertainty. "
            f"{binding_instruction} Change the proposal only when "
            "the available evidence warrants it. This returned action will "
            "be charged."
        )
        row, session_state = self._run_json(
            prompt=prompt,
            output_schema=output_schema,
        )
        self.session_state = dict(session_state)
        receipt = {
            "schema": "ztare-codex-subscription-action-decision-v1",
            "phase": "post_proposal_commitment",
            "turn_index": self._turn_index,
            "session_id": str(session_state["session_id"]),
            "session_tick_count": int(
                session_state.get("tick_count") or 0
            ),
            "action": row.get("action"),
            "prediction": str(row.get("prediction") or ""),
            "plan_summary": str(row.get("plan_summary") or ""),
            "uncertainty": str(row.get("uncertainty") or ""),
            "model": self.model_id,
            "reasoning_effort": self.reasoning_effort,
            "continuation": (
                "codex_exec_resume"
                if self.resume_session
                else "fresh_codex_session"
            ),
            "recall_injection": self._recall_receipt(
                injected_digest,
                consumption_receipt,
            ),
            "extra_inference_tick_count": 1,
        }
        if object_catalog is not None:
            receipt["catalog_sha256"] = str(
                object_catalog.get("catalog_sha256") or ""
            )
            if object_catalog.get("schema") == (
                "ztare-grid-object-catalog-presentation-v1"
            ):
                receipt.update({
                    "presentation_sha256": str(
                        object_catalog.get(
                            "presentation_sha256"
                        ) or ""
                    ),
                    "controlled_object_handle": str(
                        row.get("controlled_object_handle") or ""
                    ),
                    "ordered_waypoint_handles": list(
                        row.get("ordered_waypoint_handles") or []
                    ),
                })
            else:
                receipt.update({
                    "controlled_object_ref": str(
                        row.get("controlled_object_ref") or ""
                    ),
                    "ordered_waypoint_refs": list(
                        row.get("ordered_waypoint_refs") or []
                    ),
                })
        self._turn_index += 1
        return receipt

    def decide(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        (
            injected_digest,
            consumption_receipt,
            recall_block,
        ) = self._burn_recall_for_observation(observation)
        prompt = (
            f"{self.instructions}\n\n"
            f"TURN {self._turn_index}\n"
            "SETTLED OBSERVATION (lossless row runs):\n"
            f"{json.dumps(dict(observation), separators=(',', ':'))}"
            f"{recall_block}\n\n"
            "Return the next action in the required JSON schema. Preserve and "
            "update your hypotheses from earlier turns in this same session."
        )
        action_row, session_state = self._run_json(
            prompt=prompt,
            output_schema=_ACTION_SCHEMA,
        )
        receipt = {
            "schema": "ztare-codex-subscription-action-decision-v1",
            "turn_index": self._turn_index,
            "session_id": str(session_state["session_id"]),
            "session_tick_count": int(
                session_state.get("tick_count") or 0
            ),
            "action": action_row.get("action"),
            "prediction": str(action_row.get("prediction") or ""),
            "model": self.model_id,
            "reasoning_effort": self.reasoning_effort,
            "continuation": (
                "codex_exec_resume"
                if self.resume_session
                else "fresh_codex_session"
            ),
            "recall_injection": self._recall_receipt(
                injected_digest,
                consumption_receipt,
            ),
        }
        self._turn_index += 1
        return receipt

    def consolidate(
        self,
        *,
        episode_turns: Sequence[Mapping[str, Any]],
        boundary_observation: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Run one uncharged, same-session level-boundary consolidation tick."""

        if not self.resume_session or not self.session_state:
            raise RuntimeError(
                "level-boundary sleep requires an existing resumed session"
            )
        compact_turns = [
            {
                "action_count": int(row["action_count"]),
                "action": int(row["action"]),
                "prediction": str(row.get("prediction") or ""),
                "levels_completed": int(row["levels_completed"]),
                "source_observation_sha256": str(
                    row.get("source_observation_sha256") or ""
                ),
                "successor_observation_sha256": str(
                    row.get("successor_observation_sha256") or ""
                ),
                "transition_identity": row.get("transition_identity"),
            }
            for row in episode_turns
        ]
        prompt = (
            "LEVEL-BOUNDARY MICRO-SLEEP. Do not choose or execute an "
            "environment action. Compress the completed wake segment into "
            "guarded causal memories for the next level. Retain learned "
            "action semantics, externally observed mechanic effects, failed "
            "hypotheses, and unresolved discriminators. Do not emit an exact "
            "future action sequence. Every memory must cite supporting action "
            "counts from the supplied segment, predict its decision delta, "
            "and price its retrieval cost.\n\n"
            "WAKE SEGMENT:\n"
            f"{json.dumps(compact_turns, separators=(',', ':'))}\n\n"
            "NEXT SETTLED OBSERVATION IDENTITY:\n"
            f"{json.dumps(dict(boundary_observation), separators=(',', ':'))}"
        )
        digest, session_state = self._run_json(
            prompt=prompt,
            output_schema=_SLEEP_SCHEMA,
        )
        receipt = {
            "schema": "ztare-arc3-level-boundary-sleep-v1",
            "session_id": str(session_state["session_id"]),
            "session_tick_count": int(
                session_state.get("tick_count") or 0
            ),
            "after_action_count": int(
                boundary_observation["action_count"]
            ),
            "boundary_observation_sha256": str(
                boundary_observation["sha256"]
            ),
            "digest": digest,
        }
        return receipt


def observation_metadata(
    grid: Sequence[Sequence[int]],
    *,
    action_count: int,
    levels_completed: int,
    available_action_indices: Sequence[int],
) -> dict[str, Any]:
    return {
        "schema": "ztare-arc3-direct-observation-v1",
        "action_count": int(action_count),
        "levels_completed": int(levels_completed),
        "available_action_indices": list(available_action_indices),
        "grid_shape": [len(grid), len(grid[0]) if grid else 0],
        "grid_rle_rows": grid_rle(grid),
    }


def _sleep_memory_scope(
    *,
    game_id: str,
    model_id: str,
    reasoning_effort: str,
    boundary_observation: Mapping[str, Any],
    action_arity: int,
) -> MemoryScope:
    return MemoryScope(
        task_sha256=_sha_payload({
            "game_id": game_id,
            "objective": "maximize_levels_within_fixed_action_budget",
        }),
        controller_sha256=_sha_payload({
            "kind": "persistent_codex_subscription_reasoner",
            "model": model_id,
            "reasoning_effort": reasoning_effort,
        }),
        context_sha256=str(boundary_observation["sha256"]),
        choice_set_sha256=_sha_payload({
            "available_action_indices": list(range(action_arity)),
        }),
        action_vocabulary_sha256=_sha_payload({
            "reset": -1,
            "action_indices": list(range(action_arity)),
        }),
    )


def select_sleep_digest_memories(
    digest: Mapping[str, Any],
    *,
    scope: MemoryScope,
    top_k: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Lower a typed sleep digest through the sparse recall router."""

    raw_memories = digest.get("memories") or []
    if not isinstance(raw_memories, list):
        raise ValueError("sleep digest memories must be a list")
    candidates: list[MemoryCandidate] = []
    memory_by_revision: dict[str, dict[str, Any]] = {}
    for raw in raw_memories:
        if not isinstance(raw, dict):
            raise ValueError("sleep digest memory must be an object")
        support_counts = tuple(
            sorted({int(value) for value in raw.get("support_action_counts") or []})
        )
        contradiction_counts = tuple(
            sorted({
                int(value)
                for value in raw.get("contradiction_action_counts") or []
            })
        )
        if not support_counts:
            raise ValueError("sleep memory requires supporting action counts")
        memory_payload = {
            "memory_id": str(raw.get("memory_id") or ""),
            "claim": str(raw.get("claim") or ""),
            "guard_features": list(raw.get("guard_features") or []),
            "support_action_counts": list(support_counts),
            "contradiction_action_counts": list(contradiction_counts),
        }
        revision = _sha_payload(memory_payload)
        support_refs = tuple(
            f"arc_action:{count}" for count in support_counts
        )
        boundary_refs = tuple(
            f"arc_action:{count}" for count in contradiction_counts
            if count in support_counts
        )
        candidate = MemoryCandidate(
            provider_id="same-session-level-boundary-sleep",
            memory_revision_sha256=revision,
            scope=scope,
            predicted_decision_delta=float(
                raw.get("predicted_decision_delta")
            ),
            retrieval_cost=float(raw.get("retrieval_cost")),
            primitive_action_cost=1.0,
            authority_score=50.0,
            actionability_score=1.0,
            recency_score=1.0,
            guard_features=tuple(
                str(value)
                for value in raw.get("guard_features") or []
            ),
            semantic_features=tuple(
                str(raw.get("claim") or "").lower().split()
            ),
            support_refs=support_refs,
            boundary_support_refs=boundary_refs,
            content_ref=(
                "same_session_sleep:"
                f"{str(raw.get('memory_id') or revision[:12])}"
            ),
        )
        candidates.append(candidate)
        memory_by_revision[revision] = {
            **raw,
            "memory_revision_sha256": revision,
        }
    recall = select_sparse_memories(
        WakeSleepCreditState(),
        candidates,
        scope=scope,
        max_items=top_k,
        guard_overlap_weight=0.20,
    )
    selected = [
        memory_by_revision[row.memory_revision_sha256]
        for row in recall.selections
    ]
    selected_digest = {
        "schema": "ztare-arc3-selected-sleep-memory-v1",
        "source_digest_sha256": _sha_payload(dict(digest)),
        "scope": scope.to_receipt(),
        "scope_sha256": scope.sha256,
        "memories": selected,
        "active_uncertainties": list(
            digest.get("active_uncertainties") or []
        ),
        "next_decision_questions": list(
            digest.get("next_decision_questions") or []
        ),
    }
    return selected_digest, recall.to_receipt()


def _initial_input(
    grid: Sequence[Sequence[int]],
    *,
    levels_completed: int,
    action_arity: int,
) -> list[dict[str, Any]]:
    return [{
        "role": "user",
        "content": observation_content(
            grid,
            action_count=0,
            levels_completed=levels_completed,
            available_action_indices=tuple(range(action_arity)),
        ),
    }]


def _tool_output(
    call_id: str,
    grid: Sequence[Sequence[int]],
    *,
    action_count: int,
    levels_completed: int,
    action_arity: int,
) -> list[dict[str, Any]]:
    return [{
        "type": "function_call_output",
        "call_id": call_id,
        "output": observation_content(
            grid,
            action_count=action_count,
            levels_completed=levels_completed,
            available_action_indices=tuple(range(action_arity)),
        ),
    }]


def run_probe(
    *,
    client: Any,
    adapter: ArcAgi3Adapter,
    game_id: str,
    budget: int,
    model_id: str,
    reasoning_effort: str,
    reasoning_context: str,
    max_output_tokens: int,
    timeout_seconds: float,
    turn_observer: Callable[[Mapping[str, Any]], None] | None = None,
    exchange_observer: (
        Callable[[Mapping[str, Any]], None] | None
    ) = None,
) -> dict[str, Any]:
    start = adapter.reset()
    start_levels = int(adapter.levels_completed)
    arity = int(adapter.action_arity)
    instructions = (
        "You are controlling an unknown interactive 2D grid game. Infer its "
        "rules only from the observation/action chronology supplied here. "
        "Your objective is to complete as many levels as possible within the "
        f"fixed budget of {budget} charged actions. Preserve discoveries across "
        "turns, test uncertain hypotheses with discriminating actions, avoid "
        "repeating disproven actions in the same visible context, and call "
        "take_arc_action exactly once per turn. Action -1 resets. Other action "
        f"indices are stable integers 0 through {arity - 1}. Do not assume "
        "puzzle-specific prior knowledge."
    )
    thread = PersistentResponsesToolThread(
        client,
        model_id=model_id,
        instructions=instructions,
        tool=action_tool(arity),
        reasoning_effort=reasoning_effort,
        reasoning_context=reasoning_context,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        exchange_observer=exchange_observer,
    )
    input_items = _initial_input(
        start,
        levels_completed=start_levels,
        action_arity=arity,
    )
    turns: list[dict[str, Any]] = []
    observations = [settled_observation_receipt(
        start,
        observation_index=0,
        action_count=0,
        levels_completed=start_levels,
        adapter_epoch=int(adapter.current_epoch),
        available_action_indices=tuple(range(arity)),
    )]
    for action_count in range(1, int(budget) + 1):
        source_observation = observations[-1]
        decision = thread.decide(input_items)
        action = decision.arguments.get("action")
        if isinstance(action, bool) or not isinstance(action, int):
            raise ValueError("model action must be an integer")
        if action == -1:
            next_grid = adapter.reset()
        elif 0 <= action < arity:
            next_grid = adapter.step(action)
        else:
            raise ValueError(f"model action {action} outside [-1, {arity - 1}]")
        successor_observation = settled_observation_receipt(
            next_grid,
            observation_index=len(observations),
            action_count=action_count,
            levels_completed=int(adapter.levels_completed),
            adapter_epoch=int(adapter.current_epoch),
            available_action_indices=tuple(range(arity)),
        )
        observations.append(successor_observation)
        turn = {
            **decision.to_receipt(),
            "action_count": action_count,
            "action": action,
            "prediction": str(decision.arguments.get("prediction") or ""),
            "levels_completed": int(adapter.levels_completed),
            "adapter_epoch": int(adapter.current_epoch),
            "source_observation_sha256": source_observation["sha256"],
            "successor_observation_sha256": (
                successor_observation["sha256"]
            ),
            "transition_identity": _transition_identity_receipt(adapter),
        }
        turns.append(turn)
        if turn_observer is not None:
            turn_observer(turn)
        input_items = _tool_output(
            decision.call_id,
            next_grid,
            action_count=action_count,
            levels_completed=int(adapter.levels_completed),
            action_arity=arity,
        )
    level_boundary_actions = _level_boundary_actions(
        turns,
        start_levels=start_levels,
    )
    return {
        "schema": "ztare-arc3-responses-agent-probe-v1",
        "status": (
            "level_gained"
            if int(adapter.levels_completed) > start_levels
            else "budget_exhausted"
        ),
        "game": game_id,
        "actor": {
            "kind": "persistent_responses_reasoner",
            "model": model_id,
            "reasoning_effort": reasoning_effort,
            "reasoning_context": reasoning_context,
            "continuation": "previous_response_id",
            "store": True,
        },
        "budget": int(budget),
        "actions_executed": len(turns),
        "start_levels_completed": start_levels,
        "end_levels_completed": int(adapter.levels_completed),
        "levels_gained": int(adapter.levels_completed) - start_levels,
        "first_level_action": (
            level_boundary_actions[0]["action_count"]
            if level_boundary_actions
            else None
        ),
        "level_boundary_actions": level_boundary_actions,
        "input_tokens": sum(row["input_tokens"] for row in turns),
        "output_tokens": sum(row["output_tokens"] for row in turns),
        "cached_input_tokens": sum(
            row["cached_input_tokens"] for row in turns
        ),
        "observations": observations,
        "turns": turns,
    }


def run_subscription_probe(
    *,
    adapter: ArcAgi3Adapter,
    game_id: str,
    budget: int,
    model_id: str,
    reasoning_effort: str,
    timeout_seconds: float,
    resume_session: bool = True,
    thread: CodexSubscriptionArcThread | None = None,
    turn_observer: Callable[[Mapping[str, Any]], None] | None = None,
    exchange_observer: (
        Callable[[Mapping[str, Any]], None] | None
    ) = None,
    level_boundary_sleep_top_k: int = 0,
    initial_recall_digest: Mapping[str, Any] | None = None,
    initial_recall_consumption_receipt: (
        Mapping[str, Any] | None
    ) = None,
    decision_recall_provider: (
        Callable[
            [
                Mapping[str, Any],
                int,
                Sequence[Mapping[str, Any]],
                Sequence[Mapping[str, Any]],
            ],
            Mapping[str, Any] | None,
        ]
        | None
    ) = None,
    restored_prefix_actions: Sequence[int] = (),
) -> dict[str, Any]:
    start = adapter.reset()
    arity = int(adapter.action_arity)
    prefix_actions = tuple(int(action) for action in restored_prefix_actions)
    if any(action < 0 or action >= arity for action in prefix_actions):
        raise ValueError("restored prefix action is outside the action space")
    reset_levels = int(adapter.levels_completed)
    prefix_observations = [settled_observation_receipt(
        start,
        observation_index=0,
        action_count=0,
        levels_completed=reset_levels,
        adapter_epoch=int(adapter.current_epoch),
        available_action_indices=tuple(range(arity)),
    )]
    prefix_transitions = []
    grid = start
    for prefix_index, action in enumerate(prefix_actions, start=1):
        source_observation = prefix_observations[-1]
        levels_before = int(adapter.levels_completed)
        grid = adapter.step(action)
        successor = settled_observation_receipt(
            grid,
            observation_index=prefix_index,
            action_count=prefix_index,
            levels_completed=int(adapter.levels_completed),
            adapter_epoch=int(adapter.current_epoch),
            available_action_indices=tuple(range(arity)),
        )
        prefix_observations.append(successor)
        prefix_transitions.append({
            "prefix_action_count": prefix_index,
            "action": action,
            "levels_before": levels_before,
            "levels_after": int(adapter.levels_completed),
            "source_observation_sha256": source_observation["sha256"],
            "successor_observation_sha256": successor["sha256"],
            "transition_identity": _transition_identity_receipt(adapter),
        })
    if int(adapter.levels_completed) != reset_levels:
        raise RuntimeError(
            "restored nonterminal prefix crossed a level boundary"
        )
    start = grid
    start_levels = int(adapter.levels_completed)
    instructions = subscription_arc_instructions(
        budget=budget,
        action_arity=arity,
    )
    actor = thread or CodexSubscriptionArcThread(
        model_id=model_id,
        reasoning_effort=reasoning_effort,
        instructions=instructions,
        timeout_seconds=timeout_seconds,
        resume_session=resume_session,
        exchange_observer=exchange_observer,
    )
    turns: list[dict[str, Any]] = []
    observations = [prefix_observations[-1]]
    if initial_recall_digest is not None:
        if (
            initial_recall_consumption_receipt is not None
            and str(
                initial_recall_consumption_receipt.get(
                    "observation_sha256"
                )
                or ""
            )
            != observations[0]["sha256"]
        ):
            raise RuntimeError(
                "initial recall consumption does not match restored "
                "observation"
            )
        queue_recall = getattr(actor, "queue_recall_digest", None)
        if not callable(queue_recall):
            raise RuntimeError(
                "initial recall requested but actor cannot queue recall"
            )
        queue_recall(
            initial_recall_digest,
            consumption_receipt=(
                initial_recall_consumption_receipt
            ),
        )
    sleep_cycles: list[dict[str, Any]] = []
    decision_recall_count = 0
    segment_start = 0
    for action_count in range(1, int(budget) + 1):
        source_observation = observations[-1]
        observation = observation_metadata(
            grid,
            action_count=len(prefix_actions) + action_count - 1,
            levels_completed=int(adapter.levels_completed),
            available_action_indices=tuple(range(arity)),
        )
        observation.update({
            "observation_index": source_observation["observation_index"],
            "adapter_epoch": source_observation["adapter_epoch"],
            "sha256": source_observation["sha256"],
        })
        if decision_recall_provider is not None:
            provided = decision_recall_provider(
                source_observation,
                action_count - 1,
                tuple(observations),
                tuple(turns),
            )
            if provided is not None:
                if not isinstance(provided, Mapping):
                    raise TypeError(
                        "decision recall provider must return a mapping"
                    )
                digest = provided.get("digest")
                if not isinstance(digest, Mapping):
                    raise ValueError(
                        "decision recall provider omitted a digest mapping"
                    )
                consumption_receipt = provided.get("consumption_receipt")
                if (
                    consumption_receipt is not None
                    and not isinstance(consumption_receipt, Mapping)
                ):
                    raise ValueError(
                        "decision recall consumption receipt is not a mapping"
                    )
                queue_recall = getattr(actor, "queue_recall_digest", None)
                if not callable(queue_recall):
                    raise RuntimeError(
                        "decision recall requested but actor cannot queue recall"
                    )
                queue_recall(
                    digest,
                    consumption_receipt=consumption_receipt,
                )
                decision_recall_count += 1
        decision = actor.decide(observation)
        action = decision.get("action")
        if isinstance(action, bool) or not isinstance(action, int):
            raise ValueError("model action must be an integer")
        levels_before = int(adapter.levels_completed)
        if action == -1:
            grid = adapter.reset()
        elif 0 <= action < arity:
            grid = adapter.step(action)
        else:
            raise ValueError(f"model action {action} outside [-1, {arity - 1}]")
        successor_observation = settled_observation_receipt(
            grid,
            observation_index=(
                len(prefix_actions) + len(observations)
            ),
            action_count=len(prefix_actions) + action_count,
            levels_completed=int(adapter.levels_completed),
            adapter_epoch=int(adapter.current_epoch),
            available_action_indices=tuple(range(arity)),
        )
        observations.append(successor_observation)
        turn = {
            **decision,
            "action_count": action_count,
            "total_action_count": len(prefix_actions) + action_count,
            "levels_completed": int(adapter.levels_completed),
            "adapter_epoch": int(adapter.current_epoch),
            "source_observation_sha256": source_observation["sha256"],
            "successor_observation_sha256": (
                successor_observation["sha256"]
            ),
            "transition_identity": _transition_identity_receipt(adapter),
        }
        turns.append(turn)
        if turn_observer is not None:
            turn_observer(turn)
        if (
            level_boundary_sleep_top_k > 0
            and int(adapter.levels_completed) > levels_before
            and action_count < int(budget)
        ):
            consolidate = getattr(actor, "consolidate", None)
            if not callable(consolidate):
                raise RuntimeError(
                    "level-boundary sleep requested but actor has no "
                    "consolidation method"
                )
            sleep_receipt = consolidate(
                episode_turns=turns[segment_start:],
                boundary_observation=successor_observation,
            )
            digest = sleep_receipt.get("digest")
            if not isinstance(digest, dict):
                raise RuntimeError("sleep consolidation omitted typed digest")
            scope = _sleep_memory_scope(
                game_id=game_id,
                model_id=model_id,
                reasoning_effort=reasoning_effort,
                boundary_observation=successor_observation,
                action_arity=arity,
            )
            selected_digest, recall_receipt = select_sleep_digest_memories(
                digest,
                scope=scope,
                top_k=level_boundary_sleep_top_k,
            )
            queue_recall = getattr(actor, "queue_recall_digest", None)
            if callable(queue_recall):
                queue_recall(selected_digest)
            else:
                setattr(actor, "active_sleep_digest", selected_digest)
            sleep_cycles.append({
                **sleep_receipt,
                "selected_digest": selected_digest,
                "recall": recall_receipt,
            })
            segment_start = len(turns)
    level_boundary_actions = _level_boundary_actions(
        turns,
        start_levels=start_levels,
    )
    return {
        "schema": "ztare-arc3-subscription-agent-probe-v1",
        "status": (
            "level_gained"
            if int(adapter.levels_completed) > start_levels
            else "budget_exhausted"
        ),
        "game": game_id,
        "actor": {
            "kind": "persistent_codex_subscription_reasoner",
            "model": model_id,
            "reasoning_effort": reasoning_effort,
            "continuation": (
                "codex_exec_resume"
                if resume_session
                else "fresh_codex_session_each_turn"
            ),
            "reasoning_context_attested": False,
            "level_boundary_sleep_top_k": int(
                level_boundary_sleep_top_k
            ),
            "initial_recall_injected": (
                initial_recall_digest is not None
            ),
            "decision_recall_provider_enabled": (
                decision_recall_provider is not None
            ),
            "decision_recall_count": decision_recall_count,
        },
        "budget": int(budget),
        "restored_prefix": {
            "actions": list(prefix_actions),
            "primitive_action_cost": len(prefix_actions),
            "observations": prefix_observations,
            "transitions": prefix_transitions,
            "final_observation_sha256": observations[0]["sha256"],
        },
        "actions_executed": len(turns),
        "total_actions_executed": len(prefix_actions) + len(turns),
        "start_levels_completed": start_levels,
        "end_levels_completed": int(adapter.levels_completed),
        "levels_gained": int(adapter.levels_completed) - start_levels,
        "first_level_action": (
            level_boundary_actions[0]["action_count"]
            if level_boundary_actions
            else None
        ),
        "level_boundary_actions": level_boundary_actions,
        "inference_tick_count": (
            len(turns)
            + len(sleep_cycles)
            + sum(
                int(row.get("extra_inference_tick_count") or 0)
                for row in turns
            )
        ),
        "observations": observations,
        "sleep_cycles": sleep_cycles,
        "turns": turns,
    }


def _level_boundary_actions(
    turns: Sequence[Mapping[str, Any]],
    *,
    start_levels: int,
) -> list[dict[str, int]]:
    boundaries: list[dict[str, int]] = []
    previous = int(start_levels)
    for turn in turns:
        observed = int(turn["levels_completed"])
        if observed > previous:
            boundaries.append({
                "action_count": int(turn["action_count"]),
                "from_levels_completed": previous,
                "to_levels_completed": observed,
            })
        previous = observed
    return boundaries


def _emit_turn_progress(turn: Mapping[str, Any]) -> None:
    print(
        json.dumps({
            "event": "arc3_action_receipt",
            "action_count": int(turn["action_count"]),
            "action": int(turn["action"]),
            "levels_completed": int(turn["levels_completed"]),
            "adapter_epoch": int(turn["adapter_epoch"]),
            "session_id": turn.get("session_id"),
            "session_tick_count": turn.get("session_tick_count"),
        }, sort_keys=True),
        file=sys.stderr,
        flush=True,
    )


def _append_trace_event(
    path: Path,
    event: Mapping[str, Any],
) -> None:
    """Durably append one inference or environment event."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(event), sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="ls20")
    parser.add_argument("--budget", type=int, default=32)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument(
        "--transport",
        choices=("api", "subscription"),
        default="api",
    )
    parser.add_argument(
        "--subscription-session",
        choices=("resume", "fresh"),
        default="resume",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("high", "xhigh", "max"),
        default="xhigh",
    )
    parser.add_argument(
        "--reasoning-context",
        choices=("all_turns", "current_turn"),
        default="all_turns",
    )
    parser.add_argument("--max-output-tokens", type=int, default=4096)
    parser.add_argument("--timeout-seconds", type=float, default=300)
    parser.add_argument(
        "--trace-jsonl",
        default="",
        help=(
            "new append-only path for immediate prompt/raw-output/turn "
            "persistence; refuses an existing file"
        ),
    )
    parser.add_argument(
        "--output",
        default="",
        help="new report path; defaults to the project workspace report",
    )
    parser.add_argument(
        "--level-boundary-sleep-top-k",
        type=int,
        default=0,
        help=(
            "run one same-session uncharged consolidation tick after each "
            "level gain and recall at most K guarded memories"
        ),
    )
    args = parser.parse_args()
    if args.budget <= 0:
        raise SystemExit("--budget must be positive")
    if args.level_boundary_sleep_top_k < 0:
        raise SystemExit("--level-boundary-sleep-top-k must be nonnegative")
    if (
        args.transport != "subscription"
        and args.level_boundary_sleep_top_k
    ):
        raise SystemExit(
            "--level-boundary-sleep-top-k currently requires subscription "
            "transport"
        )

    trace_path = (
        Path(args.trace_jsonl).expanduser().resolve()
        if str(args.trace_jsonl).strip()
        else None
    )
    if trace_path is not None and trace_path.exists():
        raise SystemExit("--trace-jsonl must name a new file")
    requested_output = (
        Path(args.output).expanduser().resolve()
        if str(args.output).strip()
        else None
    )
    if requested_output is not None and requested_output.exists():
        raise SystemExit("--output must name a new file")

    def trace_event(event: Mapping[str, Any]) -> None:
        if trace_path is not None:
            _append_trace_event(trace_path, event)

    def observe_turn(turn: Mapping[str, Any]) -> None:
        _emit_turn_progress(turn)
        trace_event({
            "schema": "ztare-arc3-probe-turn-checkpoint-v1",
            "turn": dict(turn),
        })

    trace_event({
        "schema": "ztare-arc3-probe-run-manifest-v1",
        "game": str(args.game),
        "budget": int(args.budget),
        "model": str(args.model),
        "reasoning_effort": str(args.reasoning_effort),
        "reasoning_context": str(args.reasoning_context),
        "transport": str(args.transport),
        "subscription_session": str(args.subscription_session),
    })

    bootstrap_dotenv_from_repo_root()
    from openai import OpenAI

    game_id = _resolve_game_id(args.game)
    if args.transport == "subscription":
        payload = run_subscription_probe(
            adapter=ArcAgi3Adapter(game_id),
            game_id=game_id,
            budget=args.budget,
            model_id=args.model,
            reasoning_effort=args.reasoning_effort,
            timeout_seconds=args.timeout_seconds,
            resume_session=args.subscription_session == "resume",
            turn_observer=observe_turn,
            exchange_observer=trace_event,
            level_boundary_sleep_top_k=(
                args.level_boundary_sleep_top_k
            ),
        )
    else:
        payload = run_probe(
            client=OpenAI(),
            adapter=ArcAgi3Adapter(game_id),
            game_id=game_id,
            budget=args.budget,
            model_id=args.model,
            reasoning_effort=args.reasoning_effort,
            reasoning_context=args.reasoning_context,
            max_output_tokens=args.max_output_tokens,
            timeout_seconds=args.timeout_seconds,
            turn_observer=observe_turn,
            exchange_observer=trace_event,
        )
    project = REPO / "projects" / f"arc3_{args.game.split('-', 1)[0]}_gov"
    run_label = (
        (
            f"subscription_{args.subscription_session}"
            f"_sleep{args.level_boundary_sleep_top_k}"
            if args.level_boundary_sleep_top_k
            else f"subscription_{args.subscription_session}"
        )
        if args.transport == "subscription"
        else "api"
    )
    output = requested_output or (
        project
        / "workspace"
        / f"arc3_{run_label}_agent_probe_report.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    trace_event({
        "schema": "ztare-arc3-probe-final-result-v1",
        "result": payload,
        "report_path": str(output),
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "level_gained" else 1


if __name__ == "__main__":
    raise SystemExit(main())
