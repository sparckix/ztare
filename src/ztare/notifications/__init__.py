"""Notification primitives for the org runtime.

The filesystem gate/channel tree is authoritative. Notification transports are
optional projections supplied by a deployment or tenant overlay.
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
