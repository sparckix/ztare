#!/usr/bin/env python3
"""Static literature-positioning audit for the GP-245 manuscript.

This check keeps the related-work boundary explicit: each external system named
in the paper should have a bibliography key, a source URL, and a short statement
of how GP-245 differs from it. The script is intentionally offline; source URLs
are reviewed separately and recorded here so readiness checks can catch deleted
or stale positioning.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
PAPER_DIR = REPO / "papers/llm-forecast-calibration-cross-corpus"
MAIN_TEX = PAPER_DIR / "main.tex"
REFS_BIB = PAPER_DIR / "refs.bib"
DEFAULT_OUT_DIR = PROGRAM / "paper_alignment_v1/workspace/literature_positioning_2026_06_16"


ROWS = [
    {
        "category": "Future-question benchmarks",
        "examples": "ForecastBench; Prophet Arena",
        "bibkeys": ["karger2024forecastbench", "yang2025prophetarena"],
        "source_urls": [
            "https://arxiv.org/abs/2409.19839",
            "https://arxiv.org/abs/2510.17638",
        ],
        "source_titles": [
            "ForecastBench: A Dynamic Benchmark of AI Forecasting Capabilities",
            "LLM-as-a-Prophet: Understanding Predictive Intelligence with Prophet Arena",
        ],
        "boundary": "They evaluate forecast generation over live or future questions; GP-245 asks whether each scored row has source-currency, label-time, and equal-information documentation.",
    },
    {
        "category": "System forecasters",
        "examples": "AIA Forecaster",
        "bibkeys": ["alur2025aiaforecaster"],
        "source_urls": ["https://arxiv.org/abs/2511.07678"],
        "source_titles": ["AIA Forecaster: Technical Report"],
        "boundary": "They report an end-to-end forecasting system and additive market information; GP-245 isolates the evidence unit underneath system-level performance claims.",
    },
    {
        "category": "Belief updating",
        "examples": "EvolveCast",
        "bibkeys": ["yuan2025evolvecast"],
        "source_urls": ["https://arxiv.org/abs/2509.23936"],
        "source_titles": ["Assessing Large Language Models in Updating Their Forecasts with New Information"],
        "boundary": "They test updates after new information; GP-245 tests whether the row's original information state is documented before scoring.",
    },
    {
        "category": "Numerical forecast intervals",
        "examples": "QuantSightBench",
        "bibkeys": ["qin2026quantsightbench"],
        "source_urls": ["https://arxiv.org/abs/2604.15859"],
        "source_titles": ["QuantSightBench: Evaluating LLM Quantitative Forecasting with Prediction Intervals"],
        "boundary": "It evaluates continuous-quantity prediction intervals; GP-245 studies binary-event probability rows, same-information baselines, and controlled use after row validation.",
    },
    {
        "category": "Question generation and resolution",
        "examples": "Automated forecasting-question generation and resolution",
        "bibkeys": ["bosse2026automatingforecasting"],
        "source_urls": ["https://arxiv.org/abs/2601.22444"],
        "source_titles": ["Automating Forecasting Question Generation and Resolution for AI Evaluation"],
        "boundary": "It studies automated forecasting-question generation and resolution; GP-245 asks whether the resolved row has label-time, settlement-rule, and same-information-comparator metadata before score comparisons are interpreted.",
    },
    {
        "category": "Confidence elicitation and fictional markets",
        "examples": "Confidence elicitation; fictional prediction-market framing",
        "bibkeys": ["xiong2024confidence", "todasco2025fakepredictionmarkets"],
        "source_urls": [
            "https://arxiv.org/abs/2306.13063",
            "https://arxiv.org/abs/2512.05998",
        ],
        "source_titles": [
            "Can LLMs Express Their Uncertainty? An Empirical Evaluation of Confidence Elicitation in LLMs",
            "Going All-In on LLM Accuracy: Fake Prediction Markets, Real Confidence Signals",
        ],
        "boundary": "They study confidence or wager-like signals; GP-245 requires resolved forecast rows and same-information baselines before such signals are interpreted as forecasting evidence.",
    },
    {
        "category": "Trading and replay benchmarks",
        "examples": "Prediction Arena; PolyBench; PredictionMarketBench",
        "bibkeys": [
            "zhang2026predictionarena",
            "cheng2026polybench",
            "arora2026predictionmarketbench",
        ],
        "source_urls": [
            "https://arxiv.org/abs/2604.07355",
            "https://arxiv.org/abs/2604.14199",
            "https://arxiv.org/abs/2602.00133",
        ],
        "source_titles": [
            "Prediction Arena: Benchmarking AI Models on Real-World Prediction Markets",
            "PolyBench: Benchmarking LLM Forecasting and Trading Capabilities on Live Prediction Market Data",
            "PredictionMarketBench: A SWE-bench-Style Framework for Backtesting Trading Agents on Prediction Markets",
        ],
        "boundary": "They include execution, fees, liquidity, timing, and position sizing; GP-245 separates same-contract probability accuracy from trading profit.",
    },
    {
        "category": "Market-style evaluation and coordination",
        "examples": "Foresight Arena; MarketBench; Reppo",
        "bibkeys": ["nechepurenko2026foresight", "fradkin2026marketbench", "reppo2026"],
        "source_urls": [
            "https://arxiv.org/abs/2605.00420",
            "https://arxiv.org/abs/2604.23897",
            "https://reppo.xyz/",
        ],
        "source_titles": [
            "Foresight Arena: An On-Chain Benchmark for Evaluating AI Forecasting Agents",
            "MarketBench: Evaluating AI Agents as Market Participants",
            "Training AI using prediction markets",
        ],
        "boundary": "They use market-style designs or infrastructure for forecasting or AI-training data; GP-245 asks what row-level documentation is needed before model, human, and market evidence can be compared.",
    },
    {
        "category": "Relative-judgment forecasting",
        "examples": "Semantic Trading; Strategic Foresight venture tournament",
        "bibkeys": ["capponi2025semantictrading", "csaszar2026strategicforesight"],
        "source_urls": ["https://arxiv.org/abs/2512.02436", "https://arxiv.org/abs/2602.01684"],
        "source_titles": [
            "Semantic Trading: Agentic AI for Discovering Relationships Between Prediction Markets",
            "The Strategic Foresight of LLMs: Evidence from a Fully Prospective Venture Tournament",
        ],
        "boundary": "They support market-relationship discovery and pairwise ranking as credible interfaces; GP-245 treats pairwise evidence as scoped ranking support rather than standalone probability translation.",
    },
    {
        "category": "Evaluation-warning work",
        "examples": "Pitfalls; consistency checks",
        "bibkeys": ["paleka2025pitfalls", "paleka2024consistency"],
        "source_urls": [
            "https://arxiv.org/abs/2506.00723",
            "https://arxiv.org/abs/2412.18544",
        ],
        "source_titles": [
            "Pitfalls in Evaluating Language Model Forecasters",
            "Consistency Checks for Language Model Forecasters",
        ],
        "boundary": "They identify temporal leakage, extrapolation risk, and consistency tests; GP-245 adds scored database audits and same-information market controls.",
    },
    {
        "category": "2024 baseline claims",
        "examples": "Halawi et al.; Schoenegger et al.",
        "bibkeys": ["halawi2024approaching", "schoenegger2024ensemble"],
        "source_urls": [
            "https://arxiv.org/abs/2402.18563",
            "https://arxiv.org/abs/2402.19379",
        ],
        "source_titles": [
            "Approaching Human-Level Forecasting with Language Models",
            "Wisdom of the Silicon Crowd: LLM Ensemble Prediction Capabilities Rival Human Crowd Accuracy",
        ],
        "boundary": "They motivate the comparison target; GP-245 rechecks what can be concluded under source-currency, power, and same-information constraints.",
    },
]

ADDITIONAL_CHECKS = [
    {
        "category": "Market-resolution systems",
        "source_url": "https://arxiv.org/abs/2605.30802",
        "decision": (
            "Reviewed as adjacent infrastructure. Not cited in the manuscript because "
            "settlement-method design is outside the present scored forecast-row claim."
        ),
    },
    {
        "category": "Fictional-market confidence elicitation",
        "source_url": "https://arxiv.org/abs/2512.05998",
        "decision": (
            "Promoted into the related-work table as adjacent confidence-framing work. "
            "The manuscript distinguishes confidence or stake signals from resolved forecast-row scoring."
        ),
    },
]


CSV_FIELDS = [
    "category",
    "examples",
    "bibkeys",
    "source_urls",
    "source_titles",
    "boundary",
    "main_mentions",
    "bib_mentions",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def build_report(main_tex: Path, refs_bib: Path) -> dict[str, object]:
    main_text = read_text(main_tex)
    refs_text = read_text(refs_bib)
    rows = []
    missing: list[str] = []
    for item in ROWS:
        main_mentions = {}
        bib_mentions = {}
        for key in item["bibkeys"]:
            in_main = bool(re.search(rf"\\cite\{{[^}}]*\b{re.escape(key)}\b[^}}]*\}}", main_text))
            in_bib = f"{{{key}," in refs_text
            main_mentions[key] = in_main
            bib_mentions[key] = in_bib
            if not in_main:
                missing.append(f"{key}: not cited in main.tex")
            if not in_bib:
                missing.append(f"{key}: missing from refs.bib")
        rows.append(
            {
                **item,
                "bibkeys": ", ".join(item["bibkeys"]),
                "source_urls": ", ".join(item["source_urls"]),
                "source_titles": "; ".join(item["source_titles"]),
                "main_mentions": json.dumps(main_mentions, sort_keys=True),
                "bib_mentions": json.dumps(bib_mentions, sort_keys=True),
            }
        )
    return {
        "schema": "gp245-literature-positioning-audit-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "pass" if not missing else "fail",
        "rows": rows,
        "additional_checks": ADDITIONAL_CHECKS,
        "missing": missing,
        "interpretation": (
            "The manuscript positions GP-245 as a row-level validity and controlled-use paper, "
            "not as a replacement for live forecasting, trading, belief-updating, or market-coordination benchmarks."
        ),
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report: dict[str, object]) -> str:
    lines = [
        "# GP-245 Literature Positioning Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
        str(report["interpretation"]),
        "",
        "| Category | Examples | Checked titles | Keys | Boundary |",
        "|---|---|---|---|---|",
    ]
    for item in report["rows"]:
        lines.append(
            "| "
            + " | ".join(
                str(item[field]).replace("|", "/")
                for field in ("category", "examples", "source_titles", "bibkeys", "boundary")
            )
            + " |"
        )
    lines.append("")
    missing = report.get("missing") or []
    if missing:
        lines.extend(["## Missing", ""])
        for item in missing:
            lines.append(f"- {item}")
        lines.append("")
    additional_checks = report.get("additional_checks") or []
    if additional_checks:
        lines.extend(["## Additional Sources Checked", ""])
        lines.append("| Category | Source | Decision |")
        lines.append("|---|---|---|")
        for item in additional_checks:
            lines.append(
                "| "
                + " | ".join(
                    str(item[field]).replace("|", "/")
                    for field in ("category", "source_url", "decision")
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-tex", type=Path, default=MAIN_TEX)
    parser.add_argument("--refs-bib", type=Path, default=REFS_BIB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    report = build_report(args.main_tex, args.refs_bib)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "literature_positioning_audit.json"
    csv_path = args.out_dir / "literature_positioning_audit.csv"
    md_path = args.out_dir / "literature_positioning_audit.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["rows"])
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "rows": len(report["rows"]),
                "missing": report["missing"],
                "out_dir": str(args.out_dir),
                "outputs": [str(json_path), str(csv_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
