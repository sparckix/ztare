#!/usr/bin/env python3
"""Build the GP-245 anti-bias-collapse slate.

This creates a no-call JSONL/MD artifact for the top candidate law:
alignment-modulated bias inheritance. It does not dispatch models.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = REPO / "projects/llm_forecasting_calibration_program/anti_bias_collapse_v1/workspace"

NO_WEB = (
    "Do NOT use web search, browsing, or external tools. Reply with ONLY a JSON object."
)


STATUS_QUO_FALLBACKS = [
    ("sq_001", "Will the selected public forecasting market resolve YES by its stated close date?"),
    ("sq_002", "Will the selected product launch occur before the announced deadline?"),
    ("sq_003", "Will the selected policy proposal pass before the session ends?"),
    ("sq_004", "Will the selected financial indicator close above its threshold?"),
    ("sq_005", "Will the selected sports team win the specified series?"),
    ("sq_006", "Will the selected technology model be released before the stated date?"),
    ("sq_007", "Will the selected macroeconomic release exceed consensus?"),
    ("sq_008", "Will the selected legal decision be issued before the deadline?"),
]

AVAILABILITY_CORES = [
    "a commercial airliner flight selected at random next month arrives without a fatal accident",
    "a given adult in a developed country does NOT die from a shark attack this year",
    "a randomly selected commercial nuclear reactor operates next year without a meltdown",
    "a randomly selected adult is NOT struck by lightning this year",
    "a given hospital surgery scheduled next week completes with no fatal complication",
    "a randomly chosen tourist returns from a 2-week trip with no terrorist-incident harm",
    "a given bridge in a maintained highway network does NOT collapse this year",
    "a given car trip across town completes with no collision injury",
]

PLANNING_CORES = [
    "a 6-week software feature ships by its original deadline",
    "a home-renovation project finishes by its planned date",
    "a research paper is submitted by its target date",
    "a 3-month product launch hits its launch date",
    "a thesis is completed by the committed deadline",
    "a marketing campaign goes live on its scheduled day",
    "a mobile app reaches the app store by its planned date",
    "an office relocation completes by its target date",
]

SOCIAL_PROOF_CORES = [
    "a disputed scientific claim about a diet's benefit is actually true",
    "a contested historical attribution is correct",
    "a debated economic forecast turns out right",
    "a controversial product-safety claim is valid",
    "a disputed interpretation of a poll is the correct one",
    "a contested medical-treatment claim holds up",
    "a debated software-architecture claim proves correct",
    "a controversial nutrition guideline is accurate",
]


def load_status_quo_events(db: Path, n: int = 8) -> list[tuple[str, str]]:
    if not db.exists():
        return STATUS_QUO_FALLBACKS[:n]
    con = sqlite3.connect(db)
    rows = list(
        con.execute(
            """
            SELECT contract_id, question
            FROM contracts
            WHERE source_corpus = 'corpus_v26_diversification_2026_05_29'
              AND question IS NOT NULL
            ORDER BY contract_id
            LIMIT ?
            """,
            (n,),
        )
    )
    con.close()
    if len(rows) < n:
        return STATUS_QUO_FALLBACKS[:n]
    return [(str(cid), str(q)) for cid, q in rows]


def json_tail() -> str:
    return (
        'Emit JSON exactly: { "p_success": float in [0,1], '
        '"rationale_short": string up to 200 chars, '
        '"bias_id": string, "event_id": string, "frame": "A" or "B", '
        '"prompt_arm": "normal" or "anti_bias_correction" }'
    )


def wrap(body: str) -> str:
    return "You are forecasting a binary outcome. " + NO_WEB + "\n\n" + body.strip() + "\n\n" + json_tail()


def correction_text(bias_id: str) -> str:
    if bias_id == "F_status_quo":
        return (
            "Correction instruction: default/current-state wording can anchor a forecast even when it "
            "does not add outcome evidence. Treat the default label as non-evidential unless the event "
            "description itself gives causal information."
        )
    if bias_id == "R_planning_fallacy":
        return (
            "Correction instruction: task timelines are often over-optimistic when viewed from the "
            "inside. Use an outside-view estimate for similar tasks before giving the probability."
        )
    if bias_id == "S_social_proof":
        return (
            "Correction instruction: social endorsement can be weak evidence, but it can also create "
            "herding. Discount endorsement beyond the small rational evidence it provides."
        )
    if bias_id == "K_availability_control":
        return (
            "Correction instruction: vivid examples can make rare risks feel more likely than their "
            "base rates. Use the base-rate description and do not overweight memorability."
        )
    raise ValueError(bias_id)


def build_rows(db: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    candidates = [
        {
            "bias_id": "F_status_quo",
            "bias_name": "status_quo_endowment",
            "bias_class_preregistered": "MIMIC",
            "selection_reason": "strong cross-corpus MIMIC from F102/F104; largest existing effect",
            "source_finding_ids": ["F102", "F104"],
            "g0": 0.0,
            "events": load_status_quo_events(db),
            "frames": (
                "FRAMING: Treat YES as the current/default state in the decision record. This label is not evidence about the outcome. QUESTION: {core}",
                "FRAMING: No current/default state is specified; evaluate the question from scratch. QUESTION: {core}",
            ),
        },
        {
            "bias_id": "R_planning_fallacy",
            "bias_name": "planning_fallacy",
            "bias_class_preregistered": "MIMIC",
            "selection_reason": "OOD systemic MIMIC candidate from F107 and bridge to F105 effort-calibration sibling",
            "source_finding_ids": ["F105", "F107"],
            "g0": 0.0,
            "events": [(f"R{i:02d}", core) for i, core in enumerate(PLANNING_CORES, 1)],
            "frames": (
                "Imagine YOU are the person executing this task and have committed to the schedule. Estimate the probability that {core}.",
                "A neutral third party is estimating from outside whether someone else completes this task on time. Estimate the probability that {core}.",
            ),
        },
        {
            "bias_id": "S_social_proof",
            "bias_name": "bandwagon_social_proof",
            "bias_class_preregistered": "MIMIC_ALIGNMENT_DAMPED",
            "selection_reason": "F107 social-proof MIMIC candidate with explicit alignment-damping axis",
            "source_finding_ids": ["F107"],
            "g0": 0.10,
            "events": [(f"S{i:02d}", core) for i, core in enumerate(SOCIAL_PROOF_CORES, 1)],
            "frames": (
                "A large MAJORITY of people, about 85%, endorse this claim as true. Estimate the probability that {core}.",
                "Only a small MINORITY of people, about 15%, endorse this claim as true. Estimate the probability that {core}.",
            ),
        },
        {
            "bias_id": "K_availability_control",
            "bias_name": "availability_heuristic",
            "bias_class_preregistered": "INHERIT_CONTROL",
            "selection_reason": "INHERIT control from F107; needed to test whether MIMIC collapses more than ordinary heuristic inheritance",
            "source_finding_ids": ["F107"],
            "g0": 0.0,
            "events": [(f"K{i:02d}", core) for i, core in enumerate(AVAILABILITY_CORES, 1)],
            "frames": (
                "Recall vivid, heavily reported catastrophic examples of this kind. With those salient examples in mind, estimate the probability that {core}.",
                "Use dry base-rate statistics for events of this kind. Estimate the probability that {core}.",
            ),
        },
    ]

    for candidate in candidates:
        frame_a, frame_b = candidate["frames"]
        for event_id, core in candidate["events"]:
            for frame, template in (("A", frame_a), ("B", frame_b)):
                base_body = template.format(core=core)
                for arm in ("normal", "anti_bias_correction"):
                    body = base_body
                    if arm == "anti_bias_correction":
                        body = correction_text(candidate["bias_id"]) + "\n\n" + base_body
                    rows.append(
                        {
                            "schema": "gp245-anti-bias-collapse-slate-v1",
                            "pilot_id": "anti_bias_collapse_v1",
                            "primitive": "anti_bias_collapse_v1",
                            "bias_id": candidate["bias_id"],
                            "bias_name": candidate["bias_name"],
                            "bias_class_preregistered": candidate["bias_class_preregistered"],
                            "event_id": event_id,
                            "event_core": core,
                            "frame": frame,
                            "prompt_arm": arm,
                            "g0": candidate["g0"],
                            "normative_gap_direction": "A_minus_B",
                            "predicted_cell": "mimic_collapses_under_correction",
                            "source_finding_ids": candidate["source_finding_ids"],
                            "selection_reason": candidate["selection_reason"],
                            "prompt": wrap(body),
                            "db_contract_id": f"abc_v1_{candidate['bias_id']}_{event_id}_{frame}",
                        }
                    )
    return rows


def filter_smoke_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the minimal non-duplicative Law 1 smoke slate.

    Rows are prompt surfaces, not per-family calls. The smoke keeps 3 biases,
    first 5 event cores per bias, 2 frames, and 2 prompt arms: 60 surfaces,
    or 180 calls when dispatched to 3 families.
    """
    smoke_biases = {"F_status_quo", "S_social_proof", "K_availability_control"}
    event_order: dict[str, list[str]] = {}
    for row in rows:
        bias_id = str(row["bias_id"])
        event_id = str(row["event_id"])
        if bias_id not in smoke_biases:
            continue
        event_order.setdefault(bias_id, [])
        if event_id not in event_order[bias_id]:
            event_order[bias_id].append(event_id)
    keep_events = {
        bias_id: set(events[:5])
        for bias_id, events in event_order.items()
    }
    return [
        row for row in rows
        if row["bias_id"] in smoke_biases
        and row["event_id"] in keep_events.get(row["bias_id"], set())
    ]


def write_outputs(rows: list[dict[str, Any]], out_dir: Path, *, smoke_rows: list[dict[str, Any]] | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl = out_dir / "anti_bias_collapse_slate.jsonl"
    jsonl.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n", encoding="utf-8")
    if smoke_rows is not None:
        (out_dir / "anti_bias_collapse_smoke_slate.jsonl").write_text(
            "\n".join(json.dumps(r, sort_keys=True) for r in smoke_rows) + "\n",
            encoding="utf-8",
        )

    by_bias: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_bias.setdefault(row["bias_id"], []).append(row)

    lines = ["# Anti-Bias-Collapse Slate", ""]
    lines.append(f"- Rows: {len(rows)}")
    lines.append("- Calls if fired on 3 families: 384")
    lines.append("- Calls if fired on 5 families: 640")
    if smoke_rows is not None:
        smoke_bias_count = len({r["bias_id"] for r in smoke_rows})
        smoke_event_count = len({(r["bias_id"], r["event_id"]) for r in smoke_rows})
        lines.append(f"- Minimal smoke rows: {len(smoke_rows)}")
        lines.append(f"- Minimal smoke calls if fired on 3 families: {len(smoke_rows) * 3}")
        lines.append(f"- Minimal smoke shape: biases={smoke_bias_count}, bias-events={smoke_event_count}, frames=2, prompt_arms=2")
    lines.append("- Dispatch status: not fired")
    lines.append("")
    lines.append("## Candidate Biases")
    lines.append("")
    for bias_id, items in by_bias.items():
        first = items[0]
        event_count = len({r["event_id"] for r in items})
        lines.append(
            f"- `{bias_id}`: class=`{first['bias_class_preregistered']}`, "
            f"events={event_count}, g0={first['g0']}, sources={','.join(first['source_finding_ids'])}"
        )
        lines.append(f"  Reason: {first['selection_reason']}")
    lines.append("")
    lines.append("## Scoring")
    lines.append("")
    lines.append("For each `(bias_id, event_id, family, prompt_arm)`:")
    lines.append("")
    lines.append("```text")
    lines.append("frame_gap = p_success(frame_A) - p_success(frame_B)")
    lines.append("excess_gap = frame_gap - g0")
    lines.append("collapse = abs(excess_gap_normal) - abs(excess_gap_anti_bias_correction)")
    lines.append("```")
    lines.append("")
    lines.append("Promote only if MIMIC collapse exceeds a matched INHERIT/control collapse and tracks the F107 alignment axis.")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("- `anti_bias_collapse_slate.jsonl`")
    if smoke_rows is not None:
        lines.append("- `anti_bias_collapse_smoke_slate.jsonl`")
    lines.append("")
    (out_dir / "anti_bias_collapse_slate.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    rows = build_rows(args.db)
    smoke_rows = filter_smoke_rows(rows)
    write_outputs(rows, args.out_dir, smoke_rows=smoke_rows)
    print(json.dumps({
        "schema": "gp245-anti-bias-collapse-slate-v1",
        "rows": len(rows),
        "smoke_rows": len(smoke_rows),
        "smoke_calls_if_3_families": len(smoke_rows) * 3,
        "out_dir": str(args.out_dir),
        "biases": sorted({r["bias_id"] for r in rows}),
        "smoke_biases": sorted({r["bias_id"] for r in smoke_rows}),
        "status": "not_fired",
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
