"""Checklist verifier for applying external theorems to a route leaf.

This is not literature retrieval.  A substrate profile supplies theorem
templates with required hypothesis fields.  The verifier compares route text
against those fields and returns APPLIES / PARTIAL / DOES_NOT_APPLY plus the
missing fields.  Outputs are stable JSON for downstream agents.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[a-z0-9]+")


def _norm(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower().replace("_", " ")))


def _has_phrase(text_norm: str, phrase: str) -> bool:
    phrase_norm = _norm(phrase)
    if not phrase_norm:
        return False
    return phrase_norm in text_norm


def verify_applicability(text: str, profile: dict[str, Any]) -> dict[str, Any]:
    text_norm = _norm(text)
    rows: list[dict[str, Any]] = []
    for template in profile.get("templates", []):
        required = template.get("requires", {})
        matched_fields: dict[str, list[str]] = {}
        missing_fields: list[str] = []
        for field, phrases in required.items():
            hits = [phrase for phrase in phrases if _has_phrase(text_norm, phrase)]
            if hits:
                matched_fields[field] = hits
            else:
                missing_fields.append(field)
        not_enough_hits = [
            phrase
            for phrase in template.get("not_enough", [])
            if _has_phrase(text_norm, phrase)
        ]
        if not missing_fields and not not_enough_hits:
            verdict = "APPLIES"
        elif matched_fields:
            verdict = "PARTIAL"
        else:
            verdict = "DOES_NOT_APPLY"
        rows.append({
            "template_id": template.get("id"),
            "theorem": template.get("theorem"),
            "verdict": verdict,
            "matched_fields": matched_fields,
            "missing_fields": missing_fields,
            "not_enough_hits": not_enough_hits,
            "concludes": template.get("concludes", []),
        })
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    return {
        "schema_version": profile.get("schema_version", "unknown"),
        "profile_name": profile.get("name", "unnamed_profile"),
        "verdict_counts": counts,
        "rows": rows,
    }


def load_profile(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify theorem applicability against checklist templates."
    )
    ap.add_argument("--profile", required=True)
    ap.add_argument("--text")
    ap.add_argument("--text-file", action="append")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    chunks: list[str] = []
    if args.text:
        chunks.append(args.text)
    for path in args.text_file or []:
        chunks.append(Path(path).read_text(encoding="utf-8"))
    text = "\n".join(chunks)
    if not text.strip():
        raise SystemExit("provide --text or --text-file")

    result = verify_applicability(text, load_profile(args.profile))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"profile: {result['profile_name']}")
    print(f"verdict_counts: {result['verdict_counts']}")
    for row in result["rows"]:
        if row["verdict"] == "DOES_NOT_APPLY":
            continue
        print(
            f"- {row['template_id']}: {row['verdict']} "
            f"missing={row['missing_fields']} not_enough={row['not_enough_hits']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
