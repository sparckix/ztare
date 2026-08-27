#!/usr/bin/env python3
"""Run the pre-registered H97 Codex app-server fork conformance test."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.common.codex_app_server_fork import (
    CodexAppServerClient,
    stable_sha256,
    text_sha256,
)


BASE = Path(__file__).resolve().parent
ATTEMPT = BASE / "h97_causal_response_derivative/app_server_transport/attempt_01"
TRACE = ATTEMPT / "protocol_trace.jsonl"
CHECKPOINT = ATTEMPT / "checkpoint.json"
WORK_CWD = Path("/private/tmp/ztare_h97_app_server_fork_cwd")
MODEL = "gpt-5.6-sol"
EFFORT = "xhigh"
ROOT_TOKEN = "ROOT-91C7-E5A2"
BRANCH_NONCES = {
    "a": "BRANCH-A-7F3C",
    "b": "BRANCH-B-2D8E",
}


BASE_INSTRUCTIONS = """You are a sealed JSON controller.
Never use tools, shell, files, web search, MCP, or external environments.
The caller supplies the complete state. Return only JSON satisfying the given
schema. Do not invent or mention sibling-branch data absent from inherited
history."""


PARENT_PROMPT = f"""Memorize the opaque root token `{ROOT_TOKEN}` as part of
this thread's controller state. Do not analyze the token. Return a JSON object
with `root_token` equal to that token and `parent_marker` equal to
`parent_complete`."""


PARENT_SCHEMA = {
    "type": "object",
    "required": ["root_token", "parent_marker"],
    "properties": {
        "root_token": {"type": "string"},
        "parent_marker": {
            "type": "string",
            "enum": ["parent_complete"],
        },
    },
    "additionalProperties": False,
}


def branch_prompt(nonce: str) -> str:
    return f"""This fork's opaque nonce is `{nonce}`. Without tools, return
the inherited root token, this current branch nonce, and any *different*
branch nonce already present in inherited history. If no different branch
nonce is present, `other_branch_nonce` must be the empty string."""


def branch_schema(nonce: str) -> dict:
    return {
        "type": "object",
        "required": [
            "inherited_root_token",
            "current_branch_nonce",
            "other_branch_nonce",
        ],
        "properties": {
            "inherited_root_token": {"type": "string"},
            "current_branch_nonce": {
                "type": "string",
                "enum": [nonce],
            },
            "other_branch_nonce": {"type": "string"},
        },
        "additionalProperties": False,
    }


def load_checkpoint() -> dict:
    if not CHECKPOINT.is_file():
        return {"schema": "ztare-h97-app-server-fork-checkpoint-v1"}
    return json.loads(CHECKPOINT.read_text(encoding="utf-8"))


def save_checkpoint(state: dict) -> None:
    ATTEMPT.mkdir(parents=True, exist_ok=True)
    temporary = CHECKPOINT.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(CHECKPOINT)


def parse_controller_json(receipt: dict) -> dict:
    payload = json.loads(receipt["assistant_text"])
    if not isinstance(payload, dict):
        raise ValueError("controller output is not a JSON object")
    return payload


def turn_ids(thread_result: dict) -> tuple[str, ...]:
    thread = thread_result.get("thread")
    if not isinstance(thread, dict):
        raise ValueError("thread/read omitted thread")
    turns = thread.get("turns")
    if not isinstance(turns, list):
        raise ValueError("thread/read omitted turns")
    return tuple(str(row["id"]) for row in turns)


def main() -> int:
    ATTEMPT.mkdir(parents=True, exist_ok=True)
    WORK_CWD.mkdir(parents=True, exist_ok=True)
    state = load_checkpoint()
    codex_version = subprocess.run(
        ("codex", "--version"),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    with CodexAppServerClient(
        trace_path=TRACE,
        cwd=WORK_CWD,
        timeout_seconds=900,
    ) as client:
        if "parent" not in state:
            started = client.start_thread(
                model=MODEL,
                cwd=WORK_CWD,
                base_instructions=BASE_INSTRUCTIONS,
            )
            parent_thread = started["thread"]
            parent_turn = client.run_turn(
                thread_id=str(parent_thread["id"]),
                prompt=PARENT_PROMPT,
                output_schema=PARENT_SCHEMA,
                model=MODEL,
                effort=EFFORT,
            )
            state["parent"] = {
                "thread": parent_thread,
                "turn": parent_turn.to_receipt(),
                "output": parse_controller_json(parent_turn.to_receipt()),
            }
            save_checkpoint(state)

        parent_thread_id = str(state["parent"]["thread"]["id"])
        parent_turn_id = str(state["parent"]["turn"]["turn_id"])
        if "forks" not in state:
            fork_a = client.fork_thread(
                source_thread_id=parent_thread_id,
                last_turn_id=parent_turn_id,
                model=MODEL,
                cwd=WORK_CWD,
            )
            fork_b = client.fork_thread(
                source_thread_id=parent_thread_id,
                last_turn_id=parent_turn_id,
                model=MODEL,
                cwd=WORK_CWD,
            )
            state["forks"] = {
                "a": fork_a.to_receipt(),
                "b": fork_b.to_receipt(),
            }
            save_checkpoint(state)

        for label in ("a", "b"):
            branch_key = f"branch_{label}"
            if branch_key in state:
                continue
            fork = state["forks"][label]
            branch_thread_id = str(fork["fork_thread_id"])
            client.resume_thread(
                branch_thread_id,
                model=MODEL,
                cwd=WORK_CWD,
            )
            prompt = branch_prompt(BRANCH_NONCES[label])
            turn = client.run_turn(
                thread_id=branch_thread_id,
                prompt=prompt,
                output_schema=branch_schema(BRANCH_NONCES[label]),
                model=MODEL,
                effort=EFFORT,
            )
            state[branch_key] = {
                "turn": turn.to_receipt(),
                "output": parse_controller_json(turn.to_receipt()),
            }
            save_checkpoint(state)

        reads = {
            label: client.read_thread(
                str(state["forks"][label]["fork_thread_id"]),
                include_turns=True,
            )
            for label in ("a", "b")
        }

    parent_output = state["parent"]["output"]
    output_a = state["branch_a"]["output"]
    output_b = state["branch_b"]["output"]
    fork_a = state["forks"]["a"]
    fork_b = state["forks"]["b"]
    turns_a = turn_ids(reads["a"])
    turns_b = turn_ids(reads["b"])
    branch_turn_a = str(state["branch_a"]["turn"]["turn_id"])
    branch_turn_b = str(state["branch_b"]["turn"]["turn_id"])
    trace_rows = [
        json.loads(line)
        for line in TRACE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    turn_start_requests = [
        row["payload"]
        for row in trace_rows
        if row.get("channel") == "client_request"
        and isinstance(row.get("payload"), dict)
        and row["payload"].get("method") == "turn/start"
    ]

    checks = {
        "parent_output_valid": parent_output == {
            "root_token": ROOT_TOKEN,
            "parent_marker": "parent_complete",
        },
        "fork_thread_ids_distinct": (
            fork_a["fork_thread_id"] != fork_b["fork_thread_id"]
            and fork_a["fork_thread_id"] != parent_thread_id
            and fork_b["fork_thread_id"] != parent_thread_id
        ),
        "forked_from_parent_exact": (
            fork_a["forked_from_id"] == parent_thread_id
            and fork_b["forked_from_id"] == parent_thread_id
        ),
        "fork_prefixes_identical": (
            fork_a["inherited_turn_ids"] == fork_b["inherited_turn_ids"]
            == [parent_turn_id]
        ),
        "branch_prompt_bytes_matched": (
            len(branch_prompt(BRANCH_NONCES["a"]).encode("utf-8"))
            == len(branch_prompt(BRANCH_NONCES["b"]).encode("utf-8"))
        ),
        "branch_a_inherited_root": (
            output_a.get("inherited_root_token") == ROOT_TOKEN
        ),
        "branch_b_inherited_root": (
            output_b.get("inherited_root_token") == ROOT_TOKEN
        ),
        "branch_current_nonces_exact": (
            output_a.get("current_branch_nonce") == BRANCH_NONCES["a"]
            and output_b.get("current_branch_nonce") == BRANCH_NONCES["b"]
        ),
        "no_reported_sibling_nonce": (
            output_a.get("other_branch_nonce") == ""
            and output_b.get("other_branch_nonce") == ""
        ),
        "no_sibling_nonce_in_raw_output": (
            BRANCH_NONCES["b"]
            not in state["branch_a"]["turn"]["assistant_text"]
            and BRANCH_NONCES["a"]
            not in state["branch_b"]["turn"]["assistant_text"]
        ),
        "branch_turn_ids_disjoint": (
            branch_turn_a in turns_a
            and branch_turn_a not in turns_b
            and branch_turn_b in turns_b
            and branch_turn_b not in turns_a
        ),
        "parent_turn_in_both_branches": (
            parent_turn_id in turns_a and parent_turn_id in turns_b
        ),
        "zero_tool_items": all(
            int(state[key]["turn"]["tool_item_count"]) == 0
            for key in ("parent", "branch_a", "branch_b")
        ),
        "all_turns_completed": all(
            state[key]["turn"]["status"] == "completed"
            for key in ("parent", "branch_a", "branch_b")
        ),
        "model_requested_on_all_turns": (
            len(turn_start_requests) >= 3
            and all(
                row.get("params", {}).get("model") == MODEL
                for row in turn_start_requests[-3:]
            )
        ),
        "xhigh_requested_on_all_turns": (
            len(turn_start_requests) >= 3
            and all(
                row.get("params", {}).get("effort") == EFFORT
                for row in turn_start_requests[-3:]
            )
        ),
        "per_message_trace_persisted": len(trace_rows) >= 12,
    }
    verdict = (
        "transport_conformant"
        if all(checks.values())
        else "transport_rejected"
    )
    result = {
        "schema": "ztare-h97-app-server-fork-conformance-v1",
        "status": "offline_runtime_complete",
        "verdict": verdict,
        "preregistration": (
            "h97_pre_live_subscription_fork_transport_amendment.md"
        ),
        "codex_version": codex_version,
        "model": MODEL,
        "reasoning_effort": EFFORT,
        "controller_contact": True,
        "arc_environment_contact": False,
        "arc_action_count": 0,
        "trace_path": str(TRACE.relative_to(REPO)),
        "trace_row_count": len(trace_rows),
        "checks": checks,
        "parent": state["parent"],
        "forks": state["forks"],
        "branch_a": state["branch_a"],
        "branch_b": state["branch_b"],
        "branch_turn_ids": {
            "a": list(turns_a),
            "b": list(turns_b),
        },
        "prompt_identities": {
            "parent_sha256": text_sha256(PARENT_PROMPT),
            "branch_a_sha256": text_sha256(
                branch_prompt(BRANCH_NONCES["a"])
            ),
            "branch_b_sha256": text_sha256(
                branch_prompt(BRANCH_NONCES["b"])
            ),
        },
        "claim_boundary": [
            "This run tests Codex subscription thread-fork transport only.",
            "No ARC environment state or action was exposed to the controller.",
            "A conformant fork permits but does not settle the H97 live causal experiment.",
            "No response child, compounding, ARC improvement, or capability takeoff follows from this result.",
        ],
    }
    result["result_sha256"] = stable_sha256(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if verdict == "transport_conformant" else 1


if __name__ == "__main__":
    raise SystemExit(main())
