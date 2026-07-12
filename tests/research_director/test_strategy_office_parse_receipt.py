from __future__ import annotations

from pathlib import Path

from ztare.research_director import strategy_office as so


class _Battery:
    def run_audits(self, project):
        return {"firing_signal": 0.5}

    def query_menu(self):
        return {}

    def experiment_kinds(self):
        return ["probe"]


def test_parse_reply_returns_receipt_not_silent_empty() -> None:
    reply = so._parse_reply("definitely not json {{{")
    assert reply["_parse_error"]
    assert reply["_raw_prefix"].startswith("definitely not json")

    reply = so._parse_reply("[1, 2, 3]")
    assert "expected a JSON object" in reply["_parse_error"]

    # well-formed replies are untouched
    assert so._parse_reply('{"experiments": []}') == {"experiments": []}


def test_convene_parse_failure_surfaces_in_next_round_prompt(tmp_path: Path) -> None:
    prompts: list[str] = []

    def leaf(prompt: str) -> str:
        prompts.append(prompt)
        return "definitely not json {{{"

    so.convene(tmp_path, _Battery(), leaf_fn=leaf, max_query_rounds=2)

    assert len(prompts) == 2
    # the retry round must see the named parse failure, not fall through silently
    assert "UNPARSEABLE" in prompts[1]
    assert "definitely not json" in prompts[1]
