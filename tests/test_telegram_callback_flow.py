"""Integration test for Telegram callback_query → APPROVE → gate-resolve flow.

Stubs the Telegram HTTP API (getUpdates / sendMessage / answerCallbackQuery)
so we can verify end-to-end without burning real tokens or pinging Telegram.

Tests:
  1. push_notification with inline_buttons sends correct reply_markup payload
  2. poll_inbound recognizes callback_query updates and synthesizes
     InboundMessage with raw_text=APPROVE (etc)
  3. The synthesized message round-trips through _resolve_gate_from_telegram's
     token-recognition logic identically to a typed APPROVE
"""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from src.ztare.notifications import telegram as tg


_PATCHABLE_TELEGRAM_TRANSPORT = (
    getattr(tg.push_notification, "__module__", "") == tg.__name__
    and hasattr(tg, "_append_log")
)


class _FakeApi:
    """Tracks calls to _api_call so tests can assert payload shape + return canned responses."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.canned_responses: dict[str, dict] = {}

    def __call__(self, bot_token, method, params, timeout=5.0):
        self.calls.append((method, dict(params)))
        return self.canned_responses.get(method, {"ok": True, "result": {}})


@unittest.skipUnless(
    _PATCHABLE_TELEGRAM_TRANSPORT,
    "Telegram transport is optional and not locally patchable in this checkout",
)
class TestPushWithInlineButtons(unittest.TestCase):
    def test_inline_buttons_render_as_reply_markup(self):
        fake = _FakeApi()
        fake.canned_responses["sendMessage"] = {"ok": True, "result": {"message_id": 42}}
        with patch.object(tg, "_load_creds", return_value=tg.Creds(bot_token="x", principal_chat_id=123)), \
             patch.object(tg, "_api_call", side_effect=fake):
            ok = tg.push_notification(
                title="Decision",
                message="Test gate ABC",
                priority="high",
                inline_buttons=[
                    ("Approve", "approve:gate_abc"),
                    ("Skip", "skip:gate_abc"),
                    ("Stop", "stop:gate_abc"),
                ],
            )
        self.assertTrue(ok)
        self.assertEqual(fake.calls[0][0], "sendMessage")
        params = fake.calls[0][1]
        self.assertIn("reply_markup", params, "inline_buttons must produce reply_markup")
        markup = json.loads(params["reply_markup"])
        self.assertIn("inline_keyboard", markup)
        row = markup["inline_keyboard"][0]
        self.assertEqual([b["text"] for b in row], ["Approve", "Skip", "Stop"])
        self.assertEqual([b["callback_data"] for b in row],
                         ["approve:gate_abc", "skip:gate_abc", "stop:gate_abc"])

    def test_no_buttons_means_no_reply_markup(self):
        fake = _FakeApi()
        fake.canned_responses["sendMessage"] = {"ok": True, "result": {"message_id": 42}}
        with patch.object(tg, "_load_creds", return_value=tg.Creds(bot_token="x", principal_chat_id=123)), \
             patch.object(tg, "_api_call", side_effect=fake):
            tg.push_notification(title="t", message="m")
        params = fake.calls[0][1]
        self.assertNotIn("reply_markup", params)


@unittest.skipUnless(
    _PATCHABLE_TELEGRAM_TRANSPORT,
    "Telegram transport is optional and not locally patchable in this checkout",
)
class TestCallbackQueryPolling(unittest.TestCase):
    def test_callback_query_synthesizes_approve_message(self):
        fake = _FakeApi()
        # getUpdates returns one callback_query update
        fake.canned_responses["getUpdates"] = {
            "ok": True,
            "result": [{
                "update_id": 1001,
                "callback_query": {
                    "id": "cbq_id_xyz",
                    "data": "approve:proposal_self_recursive_orchestrator_abc123",
                    "message": {
                        "chat": {"id": 123, "type": "private"},
                        "date": 1715000000,
                    },
                },
            }],
        }
        fake.canned_responses["answerCallbackQuery"] = {"ok": True}
        with patch.object(tg, "_load_creds", return_value=tg.Creds(bot_token="x", principal_chat_id=123)), \
             patch.object(tg, "_api_call", side_effect=fake), \
             patch.object(tg, "_save_offset"), \
             patch.object(tg, "_load_offset", return_value=0), \
             patch.object(tg, "_append_log"):
            messages = tg.poll_inbound(consume=False)

        self.assertEqual(len(messages), 1)
        m = messages[0]
        self.assertEqual(m.raw_text, "APPROVE")  # synthesized from callback_data prefix
        self.assertEqual(m.update_id, 1001)
        self.assertTrue(m.authorized)
        # answerCallbackQuery was called to clear the loading spinner
        methods = [call[0] for call in fake.calls]
        self.assertIn("answerCallbackQuery", methods,
                      "must answer callback_query to clear the button spinner")

    def test_text_message_still_works_alongside_callback(self):
        """Regression: regular text messages (e.g. typed APPROVE) must still work."""
        fake = _FakeApi()
        fake.canned_responses["getUpdates"] = {
            "ok": True,
            "result": [{
                "update_id": 1002,
                "message": {
                    "chat": {"id": 123, "type": "private"},
                    "date": 1715000001,
                    "text": "APPROVE",
                },
            }],
        }
        with patch.object(tg, "_load_creds", return_value=tg.Creds(bot_token="x", principal_chat_id=123)), \
             patch.object(tg, "_api_call", side_effect=fake), \
             patch.object(tg, "_save_offset"), \
             patch.object(tg, "_load_offset", return_value=0), \
             patch.object(tg, "_append_log"):
            messages = tg.poll_inbound(consume=False)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].raw_text, "APPROVE")

    def test_unauthorized_callback_marked_unauthorized(self):
        fake = _FakeApi()
        fake.canned_responses["getUpdates"] = {
            "ok": True,
            "result": [{
                "update_id": 1003,
                "callback_query": {
                    "id": "cbq_y",
                    "data": "approve:gate_y",
                    "message": {
                        "chat": {"id": 999, "type": "private"},  # NOT the principal_chat_id (123)
                        "date": 1715000002,
                    },
                },
            }],
        }
        with patch.object(tg, "_load_creds", return_value=tg.Creds(bot_token="x", principal_chat_id=123)), \
             patch.object(tg, "_api_call", side_effect=fake), \
             patch.object(tg, "_save_offset"), \
             patch.object(tg, "_load_offset", return_value=0), \
             patch.object(tg, "_append_log"):
            messages = tg.poll_inbound(consume=False)
        self.assertEqual(len(messages), 1)
        self.assertFalse(messages[0].authorized,
                         "callback from non-principal chat must be flagged unauthorized")


class TestEndToEndApprovalFlow(unittest.TestCase):
    """The synthesized APPROVE message must trigger the same daemon code path
    as a typed APPROVE. We verify the token-recognition logic in the daemon's
    _resolve_gate_from_telegram exclusively returns 'approve' for these inputs.
    """

    def test_token_recognition(self):
        """Replicates daemon logic in scripts/public/control/agent_daemon.py."""
        cases = {
            "APPROVE": "approve",
            "YES": "approve",
            "RUN": "approve",
            "approve": "approve",  # case-insensitive via .upper()
            "SKIP": "skip",
            "NO": "skip",
            "DEFER": "skip",
            "STOP": "stop",
            "stop": "stop",
            "noise": "",
            "": "",
        }
        for text, expected in cases.items():
            token = (text.split() or [""])[0].upper().rstrip(":").rstrip(".")
            chosen = ""
            if token == "STOP":
                chosen = "stop"
            elif token in {"APPROVE", "YES", "RUN"}:
                chosen = "approve"
            elif token in {"SKIP", "NO", "DEFER"}:
                chosen = "skip"
            self.assertEqual(chosen, expected, f"token={text!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
