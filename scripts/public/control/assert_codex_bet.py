#!/usr/bin/env python3
"""assert_codex_bet.py <contract_id> — forcing guard for the kernel
ORDERING rule "never resolve a micro contract before an independent
forecaster wake is consumed". Exits 0 iff an accepted independent-agent
forecast exists. The legacy filename is kept for back-compat.
Born from a RECURRENCE (catches C-2026-05-16-136 and -137): the prose
rule was non-forcing → resolved-before-forecaster twice. Call this
immediately before every `forecast_pool.py resolve`.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
F = REPO / "analytics/public/forecast_pool/forecasts"
ALIASES = {
    "codex": "codex",
    "codex_forecaster": "codex",
    "codexforecaster": "codex",
    "claude": "claude",
    "claude_forecaster": "claude",
    "claudeforecaster": "claude",
}


def norm(value: object) -> str:
    return "".join(ch for ch in str(value or "").strip().lower()
                   if ch.isalnum() or ch in "_:-")


def recognized_forecasts(cid: str) -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    root = F / cid
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except Exception:
            payload = {}
        agent_id = payload.get("agent_id") if isinstance(payload, dict) else None
        if ALIASES.get(norm(agent_id or path.stem)) in {"claude", "codex"}:
            out.append(path)
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: assert_codex_bet.py <contract_id>")
        return 2
    cid = sys.argv[1]
    rows = recognized_forecasts(cid)
    if rows:
        print("OK recognized forecaster bet present:")
        for path in rows:
            print(f"  {path}")
        return 0
    print(f"BLOCK: no recognized independent-agent forecast for '{cid}' "
          f"— ORDERING: do NOT resolve before a forecaster warm-wake is "
          f"consumed. Run warm-daemon-once and wait.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
