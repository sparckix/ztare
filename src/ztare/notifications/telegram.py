"""Optional Telegram tenant transport.

Public ZTARE does not require Telegram. Live tenant overlays may provide the
canonical implementation through the sibling ``cognitive-firm`` package. This
module keeps the old import path stable while failing closed when that optional
transport is absent.
"""
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[3]
for _candidate in (
    _REPO_ROOT / "cognitive-firm" / "src",
    _REPO_ROOT.parent / "cognitive-firm" / "src",
):
    if _candidate.exists():
        sys.path.insert(0, str(_candidate))
        break

try:
    from cognitive_firm.notifications.telegram import *  # type: ignore # noqa: F401,F403,E402
    from cognitive_firm.notifications.telegram import (  # type: ignore # noqa: F401,E402
        Creds,
        InboundMessage,
        _api_call,
        _authorize,
        _classify,
        _load_creds,
        _load_offset,
        _save_offset,
        poll_inbound,
        push_notification,
        reply,
    )
except ModuleNotFoundError:

    @dataclass(frozen=True)
    class Creds:
        token: str
        chat_id: str
        authorized_user_ids: tuple[str, ...] = ()

    @dataclass(frozen=True)
    class InboundMessage:
        update_id: int
        chat_id: str
        text: str
        authorized: bool = False
        command: str | None = None
        payload: str | None = None

    def _transport_unavailable() -> RuntimeError:
        return RuntimeError(
            "Telegram transport is not installed in this public checkout; "
            "use filesystem/Orbit gates or install the tenant notification overlay."
        )

    def _load_creds() -> Creds:
        raise _transport_unavailable()

    def _api_call(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise _transport_unavailable()

    def _authorize(*_args: Any, **_kwargs: Any) -> bool:
        return False

    def _classify(*_args: Any, **_kwargs: Any) -> str:
        return "UNKNOWN"

    def _load_offset() -> int:
        return 0

    def _save_offset(_offset: int) -> None:
        return None

    def poll_inbound(*_args: Any, **_kwargs: Any) -> list[InboundMessage]:
        return []

    def push_notification(*_args: Any, **_kwargs: Any) -> bool:
        return False

    def reply(*_args: Any, **_kwargs: Any) -> bool:
        return False

    def _cli() -> int:
        print(
            "Telegram transport is not installed in this public checkout. "
            "Use filesystem/Orbit gates or install the tenant notification overlay."
        )
        return 0


if "_cli" not in globals():
    def _cli() -> int:
        rows = poll_inbound()
        for row in rows:
            print(row)
        return 0
