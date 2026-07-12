from __future__ import annotations

import json
from pathlib import Path

from ztare.common.turn_profile_adapter import build_turn_profiles, format_profile_table


def test_build_turn_profiles_writes_jsonl_and_table(tmp_path: Path) -> None:
    prompt_root = tmp_path / "workspace" / "agent_prompt_debug"
    rollout_root = tmp_path / "sessions"
    prompt_root.mkdir(parents=True)
    rollout_dir = rollout_root / "2026" / "07" / "09"
    rollout_dir.mkdir(parents=True)

    prompt_meta = {
        "schema": "ztare-agent-prompt-debug-v1",
        "created_at_utc": "2026-07-09T19:31:26.000000+00:00",
        "agent_id": "autoresearch_mutator",
        "runtime": "codex",
        "prompt_sha256": "abc",
        "prompt_path": str(prompt_root / "x.txt"),
    }
    (prompt_root / "20260709T193126.000000Z_autoresearch_mutator_codex_abc.request.meta.json").write_text(
        json.dumps(prompt_meta) + "\n",
        encoding="utf-8",
    )
    rollout_path = rollout_dir / "rollout-2026-07-09T19-31-27-abc.jsonl"
    rollout_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-07-09T19:31:27.000Z",
                        "type": "session_meta",
                        "payload": {
                            "session_id": "abc",
                            "cwd": "/tmp/repo",
                            "thread_source": "user",
                        },
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-07-09T19:31:28.000Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "token_count",
                            "info": {
                                "last_token_usage": {
                                    "input_tokens": 100,
                                    "output_tokens": 7,
                                }
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-07-09T19:31:30.000Z",
                        "type": "response_item",
                        "payload": {"type": "function_call"},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    out = build_turn_profiles(
        prompt_debug_root=prompt_root,
        rollout_root=rollout_root,
        output_path=tmp_path / "workspace" / "turn_profiles.jsonl",
        limit=1,
    )

    assert out["count"] == 1
    assert (tmp_path / "workspace" / "turn_profiles.jsonl").exists()
    table = format_profile_table(out["rows"])
    assert "cli_startup" in table
    assert "100/7" in table
