from __future__ import annotations

import json

from ztare.common.equivariance import stable_sha256
from ztare.investment.closed_book import CLOSED_BOOK_RUN_SCHEMA, CLOSED_BOOK_SETTLEMENT_SCHEMA
from ztare.investment.workspace import _closed_book_research_scorecards


def test_sealed_paper_watch_settlement_becomes_research_outcome(tmp_path) -> None:
    leaf = "a" * 64
    for horizon, active_return in ((21, -0.30), (90, 0.12)):
        run_body = {
            "schema": CLOSED_BOOK_RUN_SCHEMA,
            "run_id": f"run-{horizon}",
            "opened_at": "2026-01-01T00:00:00Z",
            "horizon_days": horizon,
            "evidence_packet": {
                "subject": {
                    "kind": "paper_watch_decision", "candidate_leaf": leaf,
                    "subject_id": "watch:ABC",
                },
                "research_snapshot": {"evidence": {"dossier_sha256": "d" * 64}},
            },
        }
        run = {**run_body, "run_sha256": stable_sha256(run_body)}
        settlement_body = {
            "schema": CLOSED_BOOK_SETTLEMENT_SCHEMA,
            "settlement_id": f"run-{horizon}::settlement",
            "run_id": run["run_id"], "run_sha256": run["run_sha256"],
            "evaluated_at": "2026-04-01T00:00:00Z",
            "actual_values": {"active_return": active_return},
        }
        settlement = {
            **settlement_body, "settlement_sha256": stable_sha256(settlement_body),
        }
        for directory, payload in (("runs", run), ("settlements", settlement)):
            path = tmp_path / "closed_book" / directory / f"run-{horizon}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload), encoding="utf-8")

    assert _closed_book_research_scorecards(tmp_path)[(leaf, "d" * 64)][
        "net_excess_return"
    ] == 0.12
