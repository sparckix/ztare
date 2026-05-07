#!/usr/bin/env python3
# Licensed under Business Source License 1.1 — see LICENSE-BSL
"""Small CLI for the local persistent-agent channel.

This is a devops/debug surface, not the intended product UI. Orbit/Telegram
should project the same underlying `org/channels/` records for human use.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.ztare.orchestration.agent_channels import (  # noqa: E402
    list_agent_messages,
    send_agent_message,
    update_agent_message_status,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="ZTARE persistent-agent channel")
    sub = parser.add_subparsers(dest="cmd", required=True)

    send = sub.add_parser("send", help="send a message between persistent role offices")
    send.add_argument("--from-role", required=True)
    send.add_argument("--to-role", required=True)
    send.add_argument("--kind", required=True,
                      choices=["inform", "request", "proposal", "handoff", "clarification", "refusal", "status"])
    send.add_argument("--subject", required=True)
    send.add_argument("--body", required=True)
    send.add_argument("--expects-response", action="store_true")
    send.add_argument("--reference", action="append", default=[])
    send.add_argument("--artifact", action="append", default=[])

    inbox = sub.add_parser("inbox", help="list messages for a role")
    inbox.add_argument("--role", required=True)
    inbox.add_argument("--all", action="store_true", help="include non-open messages")
    inbox.add_argument("--limit", type=int, default=20)

    close = sub.add_parser("status", help="set message status")
    close.add_argument("--role", required=True)
    close.add_argument("--message-id", required=True)
    close.add_argument("--status", required=True, choices=["open", "acknowledged", "closed"])
    close.add_argument("--actor", required=True)
    close.add_argument("--note", default="")

    args = parser.parse_args()
    if args.cmd == "send":
        msg = send_agent_message(
            from_role=args.from_role,
            to_role=args.to_role,
            kind=args.kind,
            subject=args.subject,
            body=args.body,
            expects_response=args.expects_response,
            references=args.reference,
            artifacts=args.artifact,
        )
        print(msg.message_id)
        return 0
    if args.cmd == "inbox":
        messages = list_agent_messages(
            role_id=args.role,
            status=None if args.all else "open",
            limit=args.limit,
        )
        for msg in messages:
            marker = "!" if msg.expects_response else "-"
            print(f"{marker} {msg.message_id} [{msg.kind}] {msg.from_role} -> {msg.to_role}: {msg.subject}")
        return 0
    if args.cmd == "status":
        msg = update_agent_message_status(
            role_id=args.role,
            message_id=args.message_id,
            status=args.status,
            actor=args.actor,
            note=args.note,
        )
        print(f"{msg.message_id} {msg.status}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
