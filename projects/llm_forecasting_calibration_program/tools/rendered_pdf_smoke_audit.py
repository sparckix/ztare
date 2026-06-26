#!/usr/bin/env python3
"""Smoke-test the rendered GP-245 PDF.

The TeX source audits catch most regressions, but they do not prove that the
compiled PDF is fresh, readable, and still contains the paper's main boundaries.
This check extracts text from the PDF and verifies a small set of rendered
sentences, captions, sections, and prose hygiene constraints.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
PAPER = REPO / "papers/llm-forecast-calibration-cross-corpus"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/rendered_pdf_smoke_2026_06_17"

MAIN_TEX = PAPER / "main.tex"
MAIN_PDF = PAPER / "main.pdf"

REQUIRED_RENDERED_TEXT = {
    "title": "When Does an LLM Forecasting Benchmark Measure Forecasting?",
    "introduction": "Introduction",
    "core_results": "Core empirical results",
    "controlled_use": "Controlled use under source and market constraints",
    "limits": "What this paper does not establish",
    "conclusion": "Conclusion",
    "reproducibility": "Reproducibility",
    "evidence_ledger": "Evidence ledger for compressed diagnostics",
    "coverage_appendix": "Coverage audit for omitted or deferred work",
    "companion_benchmark_caption": "Companion benchmark tracks",
    "field_wide_protocol_caption": "Broader validity audit protocol",
    "row_schema_fields": "equal-information comparator timing, effective sample size",
    "market_control_caption": "Equal-information market controls",
    "low_probability_caption": "Per-family correction for very small probabilities",
    "market_boundary": "These controls do not establish a general result about markets and models",
    "field_prevalence_boundary": "It does not report a failure rate across the field",
    "human_market_limit": "It does not show that LLMs beat humans, human crowds, or prediction markets",
    "generality_limit": "replication on open models and public questions is required",
    "prospective_design": "what would make a positive result uninformative",
}

INTERNAL_LANGUAGE_PATTERNS = [
    r"\bF47\b",
    r"\bF100\b",
    r"\bharnessing thesis\b",
    r"\blandmark\b",
    r"\bAccepted claim spin\b",
    r"\bshould not be sold\b",
    r"\bsold as\b",
    r"\bclaim spine\b",
    r"\bpaper spine\b",
    r"\bload-bearing\b",
    r"\bload bearing\b",
    r"\blands hard\b",
    r"\breal work\b",
    r"\bsystem recipe\b",
    r"\brepair loops\b",
    r"\bmethodological backbone\b",
    r"\baxis-1/2/3\b",
    r"\bright unit is closer\b",
    r"\bnot an established mechanism\b",
    r"\bmechanism established\b",
    r"\bartifact\b",
    r"\bartifacts\b",
    r"\breceipt\b",
    r"\breceipts\b",
    r"\bcarrier\b",
    r"\bcarriers\b",
    r"\bshould\b",
]


@dataclass
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def check(name: str, condition: bool, detail: str) -> Check:
    return Check(name=name, status="pass" if condition else "fail", detail=detail)


def compact_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def rendered_search_texts(text: str) -> tuple[str, str]:
    normalized = compact_ws(text)
    return normalized, normalized.replace("- ", "-")


def run_command(args: list[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(args, check=False, capture_output=True, text=True)
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def parse_pdfinfo(output: str) -> dict[str, Any]:
    info: dict[str, Any] = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        info[key.strip()] = value.strip()
    pages_raw = info.get("Pages")
    try:
        info["Pages"] = int(str(pages_raw))
    except (TypeError, ValueError):
        info["Pages"] = None
    return info


def build_report(generated_at: str) -> dict[str, Any]:
    checks: list[Check] = []
    pdf_exists = MAIN_PDF.exists() and MAIN_PDF.stat().st_size > 0
    tex_exists = MAIN_TEX.exists() and MAIN_TEX.stat().st_size > 0
    checks.append(
        check(
            "pdf_file_present",
            pdf_exists,
            f"{rel(MAIN_PDF)} exists and is nonempty" if pdf_exists else f"{rel(MAIN_PDF)} missing or empty",
        )
    )
    checks.append(
        check(
            "tex_source_present",
            tex_exists,
            f"{rel(MAIN_TEX)} exists and is nonempty" if tex_exists else f"{rel(MAIN_TEX)} missing or empty",
        )
    )

    pdf_current = pdf_exists and tex_exists and MAIN_PDF.stat().st_mtime >= MAIN_TEX.stat().st_mtime
    checks.append(
        check(
            "pdf_current_with_tex",
            pdf_current,
            "PDF timestamp is current with TeX source" if pdf_current else "PDF is older than TeX source",
        )
    )

    pdfinfo_code, pdfinfo_out, pdfinfo_err = run_command(["pdfinfo", str(MAIN_PDF)]) if pdf_exists else (1, "", "")
    pdfinfo = parse_pdfinfo(pdfinfo_out)
    pages = pdfinfo.get("Pages")
    checks.append(
        check(
            "pdfinfo_available",
            pdfinfo_code == 0 and isinstance(pages, int),
            f"pdfinfo pages={pages}" if pdfinfo_code == 0 else f"pdfinfo failed: {pdfinfo_err.strip()}",
        )
    )
    checks.append(
        check(
            "page_count_plausible",
            isinstance(pages, int) and pages >= 30,
            f"{pages} pages" if isinstance(pages, int) else "page count unavailable",
        )
    )

    text_code, rendered_text, text_err = (
        run_command(["pdftotext", "-layout", str(MAIN_PDF), "-"]) if pdf_exists else (1, "", "")
    )
    normalized, hyphen_normalized = rendered_search_texts(rendered_text)
    checks.append(
        check(
            "pdftotext_available",
            text_code == 0 and len(normalized) > 1000,
            f"{len(normalized)} extracted characters"
            if text_code == 0
            else f"pdftotext failed: {text_err.strip()}",
        )
    )

    missing_text = [
        name
        for name, phrase in REQUIRED_RENDERED_TEXT.items()
        if phrase not in normalized and phrase not in hyphen_normalized
    ]
    checks.append(
        check(
            "required_rendered_text_present",
            not missing_text,
            f"{len(REQUIRED_RENDERED_TEXT)} rendered text checks pass"
            if not missing_text
            else "missing: " + ", ".join(missing_text),
        )
    )

    internal_hits: list[dict[str, str]] = []
    for pattern in INTERNAL_LANGUAGE_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            start = max(0, match.start() - 80)
            end = min(len(normalized), match.end() + 80)
            internal_hits.append(
                {
                    "pattern": pattern,
                    "match": match.group(0),
                    "context": normalized[start:end],
                }
            )
    checks.append(
        check(
            "rendered_internal_language_absent",
            not internal_hits,
            "no internal wording found" if not internal_hits else f"{len(internal_hits)} internal wording hits",
        )
    )

    failed = [item for item in checks if item.status != "pass"]
    return {
        "schema": "gp245-rendered-pdf-smoke-audit-v1",
        "generated_at": generated_at,
        "status": "pass" if not failed else "fail",
        "pdf": {
            "path": rel(MAIN_PDF),
            "size_bytes": MAIN_PDF.stat().st_size if pdf_exists else 0,
            "pages": pages,
            "pdf_current_with_tex": pdf_current,
        },
        "summary": {
            "checks": len(checks),
            "failed_checks": len(failed),
            "required_text_checks": len(REQUIRED_RENDERED_TEXT),
            "internal_language_hits": len(internal_hits),
            "extracted_characters": len(normalized),
        },
        "checks": [item.__dict__ for item in checks],
        "internal_language_hits": internal_hits,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Rendered PDF Smoke Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        f"Pages: `{(report.get('pdf') or {}).get('pages')}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for item in report["checks"]:
        lines.append(f"| {item['name']} | {item['status']} | {str(item['detail']).replace('|', '/')} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report = build_report(generated_at)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.out_dir / "rendered_pdf_smoke_audit.json"
    md_path = args.out_dir / "rendered_pdf_smoke_audit.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "out_dir": str(args.out_dir),
                "outputs": [str(json_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
