"""Notification primitives for GP-128 / GP-128b manager-agent seam.

Bidirectional Telegram channel as of 2026-04-25 (ntfy.sh retired).
``push_notification`` is the legacy outbound API (now Telegram-backed);
``poll_inbound`` and ``reply`` are the bidirectional Telegram primitives.
"""

from .push import push_notification, push_gate_escalation, NTFY_TOPIC
from .telegram import poll_inbound, reply, InboundMessage

__all__ = [
    "push_notification",
    "push_gate_escalation",
    "poll_inbound",
    "reply",
    "InboundMessage",
    "NTFY_TOPIC",  # legacy; always None after GP-128b
]
