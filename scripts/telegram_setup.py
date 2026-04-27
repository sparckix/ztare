#!/usr/bin/env python3
"""Interactive setup wizard for GP-128b Telegram channel.

Walks the principal through:
  1. Creating the bot via @BotFather (one-time, manual)
  2. Capturing the bot token
  3. Sending a hello message from the principal's account
  4. Auto-detecting the principal's chat_id via getUpdates
  5. Writing creds to org/mandates/.telegram_creds (gitignored, mode 0600)
  6. Sanity-checking by sending a confirmation reply

Stdlib-only.

Usage:
    python scripts/telegram_setup.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CREDS_PATH = REPO_ROOT / "org" / "mandates" / ".telegram_creds"
TELEGRAM_API_BASE = "https://api.telegram.org"


def _api(token: str, method: str, params: dict | None = None, timeout: float = 10.0):
    url = f"{TELEGRAM_API_BASE}/bot{token}/{method}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "description": f"HTTP {exc.code}: {exc.reason}"}
    except urllib.error.URLError as exc:
        return {"ok": False, "description": f"network error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "description": f"unexpected: {exc}"}


def _print(s: str = "") -> None:
    print(s, flush=True)


def main() -> int:
    _print("═" * 70)
    _print("  GP-128b — Telegram channel setup wizard")
    _print("═" * 70)
    _print()

    if CREDS_PATH.exists():
        existing = CREDS_PATH.read_text(encoding="utf-8")
        _print(f"Existing creds at {CREDS_PATH}:")
        for ln in existing.splitlines():
            if ln.startswith("bot_token="):
                tok = ln.split("=", 1)[1].strip()
                masked = tok[:8] + "…" + tok[-4:] if len(tok) > 16 else "(short)"
                _print(f"  bot_token={masked}")
            elif ln.strip() and not ln.startswith("#"):
                _print(f"  {ln}")
        _print()
        ans = input("Overwrite? (y/N) ").strip().lower()
        if ans not in ("y", "yes"):
            _print("Aborted.")
            return 0
        _print()

    _print("STEP 1 — Create the bot")
    _print("-" * 70)
    _print("Open Telegram, search for @BotFather, send /newbot.")
    _print("Pick a name (anything) and a username ending in 'bot' (e.g. ztare_manager_bot).")
    _print("@BotFather will reply with a token like '123456789:AABBCCDD...'")
    _print()
    token = input("Paste the bot token here: ").strip()
    if not token or ":" not in token:
        _print("That doesn't look like a valid bot token. Aborting.")
        return 1
    _print()

    _print("STEP 2 — Verify the token")
    _print("-" * 70)
    me = _api(token, "getMe")
    if not me.get("ok"):
        _print(f"  ❌ Token check failed: {me.get('description')}")
        return 1
    bot_info = me.get("result", {})
    _print(f"  ✅ Bot: @{bot_info.get('username')} ({bot_info.get('first_name')})")
    _print()

    _print("STEP 3 — Send a hello message from your account")
    _print("-" * 70)
    _print(f"Open the bot @{bot_info.get('username')} in Telegram and send any message.")
    _print("(e.g. 'hello'). The wizard will detect your chat_id from that message.")
    _print()
    input("Press Enter once you've sent the message... ")

    _print()
    _print("STEP 4 — Detect your chat_id")
    _print("-" * 70)
    chat_id = None
    for attempt in range(6):
        time.sleep(2.0)
        upds = _api(token, "getUpdates", {"timeout": 0})
        if not upds.get("ok"):
            _print(f"  ⚠️  getUpdates failed: {upds.get('description')}")
            continue
        updates = upds.get("result", [])
        if not updates:
            _print(f"  ({attempt+1}/6) no messages yet, waiting...")
            continue
        # Take the most recent message
        last = updates[-1]
        msg = last.get("message") or last.get("edited_message") or {}
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        username = chat.get("username", "<no username>")
        first_name = chat.get("first_name", "")
        text = msg.get("text", "")
        _print(f"  ✅ Detected chat_id={chat_id}  user=@{username} ({first_name})")
        _print(f"     latest message: {text!r}")
        break
    if chat_id is None:
        _print()
        _print("  ❌ No message received within ~12 seconds.")
        _print("     Make sure you sent a message to the bot, then re-run this script.")
        return 1
    _print()

    confirm = input(f"Use chat_id={chat_id} for the principal? (Y/n) ").strip().lower()
    if confirm in ("n", "no"):
        custom = input("Enter the chat_id manually: ").strip()
        try:
            chat_id = int(custom)
        except ValueError:
            _print("Not a valid integer. Aborting.")
            return 1
    _print()

    _print("STEP 5 — Write creds")
    _print("-" * 70)
    CREDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    contents = (
        "# GP-128b Telegram creds — gitignored, mode 0600.\n"
        "# Generated by scripts/telegram_setup.py.\n"
        "# Rotate the bot_token via @BotFather → /token if it leaks.\n"
        f"bot_token={token}\n"
        f"principal_chat_id={chat_id}\n"
    )
    CREDS_PATH.write_text(contents, encoding="utf-8")
    try:
        os.chmod(CREDS_PATH, 0o600)
    except OSError:
        pass
    _print(f"  ✅ Wrote {CREDS_PATH}")
    _print()

    _print("STEP 6 — Send confirmation")
    _print("-" * 70)
    sent = _api(
        token,
        "sendMessage",
        {
            "chat_id": str(chat_id),
            "text": "✅ GP-128b Telegram channel is live.\n\n"
                    "Send STOP / PAUSE / RESUME / STATUS / DIRECTIVE: <text>\n"
                    "or any free-form text (treated as DIRECTIVE).\n\n"
                    "ntfy.sh has been retired.",
        },
    )
    if sent.get("ok"):
        _print("  ✅ Confirmation message sent. Check your phone.")
    else:
        _print(f"  ⚠️  Confirmation send failed: {sent.get('description')}")
        _print(f"     But creds are written; check your phone or rerun.")
    _print()

    _print("═" * 70)
    _print("  Setup complete.")
    _print()
    _print("  Test inbound polling:  python scripts/poll_telegram.py")
    _print("  Send a manager push:")
    _print("      python -c \"from src.ztare.notifications import push_notification;"
           " push_notification(title='hi', message='from manager', priority='high')\"")
    _print("═" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
