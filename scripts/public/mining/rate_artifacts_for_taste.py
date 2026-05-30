#!/usr/bin/env python3
"""LLM taste rater for sampled apparatus artifacts.

Reads ``analytics/public/queries/taste/_taste_sample.md`` (produced by
``sample_artifacts_for_taste.py``), sends each sample through an
LLM with a 0-5 insight-density rubric, parses ratings, writes
``analytics/public/queries/taste/_taste_ratings.json``.

Three operating modes:

  --mode llm        (default) — call LLMRuntime with the configured
                                 model_id. Used when re-running
                                 without a human rater.

  --mode stub       Stub mode — writes the rating prompts to
                    ``analytics/public/queries/taste/_taste_prompts.md`` for
                    paste-into-Claude or paste-into-cold-agent rating.
                    Caller hand-edits the resulting ratings into a
                    table at ``analytics/public/queries/taste/_taste_ratings.md``
                    in the format the aggregator expects.

  --mode cold-agent Spawn a cold Claude sub-agent (via the Task tool
                    in the parent context) to rate. This script does
                    NOT spawn the agent itself; it just prepares the
                    instructions file. Caller invokes the agent
                    separately with the prepared instruction.

The rating format the aggregator expects:
```
SAMPLE_001 | 3 | non-obvious framing of charter contamination as feature
SAMPLE_002 | 1 | restates substrate-meta schema; no new insight
...
```

Usage (LLM mode):
    python scripts/public/mining/sample_artifacts_for_taste.py
    python scripts/public/mining/rate_artifacts_for_taste.py --mode llm

Usage (stub mode for paste-into-Claude):
    python scripts/public/mining/sample_artifacts_for_taste.py
    python scripts/public/mining/rate_artifacts_for_taste.py --mode stub
    # paste the prompt(s), receive ratings, save to _taste_ratings.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[3]
SAMPLE_MD = REPO / "analytics" / "public" / "queries" / "taste" / "_taste_sample.md"
PROMPTS_MD = REPO / "analytics" / "public" / "queries" / "_taste_prompts.md"
RATINGS_JSON = REPO / "analytics" / "public" / "queries" / "taste" / "_taste_ratings.json"
RATINGS_MD = REPO / "analytics" / "public" / "queries" / "taste" / "_taste_ratings.md"

RUBRIC = """\
Rate each sample 0-5 on insight density:
  0 = boilerplate, scaffolding, or restated apparatus state
  1 = trivially observable; doesn't change downstream reasoning
  2 = useful but expected; consolidates known
  3 = non-obvious finding or sharp framing; would help a future reader
  4 = surprising / load-bearing / mechanism-revealing
  5 = paradigm-shifting; reframes the problem or apparatus

For each sample, output exactly one line in this format:
  SAMPLE_NNN | <integer score 0-5> | <one-line rationale, ≤120 chars>

Output ONLY the rating lines. No preamble, no summary, no commentary.
"""


def _split_samples(md_text: str) -> list[tuple[str, str]]:
    """Return list of (sample_id, content_block) from the rater-visible md."""
    out = []
    chunks = re.split(r"^## (SAMPLE_\d+) \(([^)]+)\)$", md_text, flags=re.MULTILINE)
    # chunks[0] is the preamble; then alternating (id, kind, content)
    i = 1
    while i + 2 < len(chunks):
        sid = chunks[i]
        kind = chunks[i + 1]
        content = chunks[i + 2].strip()
        out.append((sid, kind, content))
        i += 3
    return out


def _llm_call(prompt: str, model: Optional[str] = None) -> str:
    sys.path.insert(0, str(REPO))
    from src.ztare.common.llm_runtime import (  # noqa: E402
        LLMRuntime,
        pick_default_model_id_for_scripts,
    )
    runtime = LLMRuntime()
    model_id = model or pick_default_model_id_for_scripts()
    if model_id is None:
        raise RuntimeError(
            "No LLM provider available — set ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY"
        )
    resp = runtime.call_text(
        prompt, model_id=model_id, max_tokens=2000,
        request_label="taste_rater",
    )
    return resp.text or ""


_RATING_RE = re.compile(r"^(SAMPLE_\d+)\s*\|\s*(\d)\s*\|\s*(.+)$", re.MULTILINE)


def _parse_ratings(text: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for m in _RATING_RE.finditer(text or ""):
        sid = m.group(1)
        try:
            score = int(m.group(2))
        except Exception:  # noqa: BLE001
            continue
        if not (0 <= score <= 5):
            continue
        rationale = m.group(3).strip()[:200]
        out[sid] = {"score": score, "rationale": rationale}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--mode",
        choices=["llm", "stub", "cold-agent", "parse-existing"],
        default="stub",
        help="llm = call LLM. stub = write prompt for paste-in. "
             "cold-agent = prepare instructions for parent to invoke a sub-agent. "
             "parse-existing = convert an existing rater .md (--out-md) to .json "
             "(G5 fix 2026-05-16: branch existed but was unreachable via CLI).",
    )
    ap.add_argument("--model", default=None,
                    help="Model id for --mode llm (defaults to env-picked)")
    ap.add_argument("--batch-size", type=int, default=20,
                    help="Samples per LLM call (only --mode llm)")
    ap.add_argument("--sample-md", type=Path, default=SAMPLE_MD)
    ap.add_argument("--out-json", type=Path, default=RATINGS_JSON)
    ap.add_argument("--out-md", type=Path, default=RATINGS_MD)
    args = ap.parse_args()

    if not args.sample_md.exists():
        print(f"ERROR: missing {args.sample_md}; run sample_artifacts_for_taste.py first")
        return 2
    md_text = args.sample_md.read_text(encoding="utf-8")
    samples = _split_samples(md_text)
    print(f"=== taste rater [{args.mode}] ===")
    print(f"  samples to rate: {len(samples)}")

    if args.mode == "stub":
        # Write a single paste-ready prompt
        lines = [RUBRIC, "\n---\n", "Samples:\n"]
        for sid, kind, content in samples:
            lines.append(f"\n### {sid} ({kind})\n```\n{content}\n```\n")
        prompt = "\n".join(lines)
        PROMPTS_MD.parent.mkdir(parents=True, exist_ok=True)
        PROMPTS_MD.write_text(prompt)
        print(f"  wrote stub prompt → {PROMPTS_MD}")
        print(f"  next step: paste {PROMPTS_MD} content into rater (Claude / cold agent)")
        print(f"  rater output should be saved to {args.out_md}")
        print(f"  then run with --mode parse-existing to convert .md → .json")
        return 0

    if args.mode == "cold-agent":
        # Prepare an instruction file for the parent context to spawn
        # a sub-agent. The sub-agent will get fresh context + the
        # sample.md as input.
        instruction = f"""\
Read the apparatus-artifact taste sample at:
    {args.sample_md.relative_to(REPO)}

Apply the following rubric and produce ratings:

{RUBRIC}

Each sample is delimited by `## SAMPLE_NNN (kind)` followed by a code
block with the artifact content (truncated to 1.2KB).

Output your ratings to:
    {args.out_md.relative_to(REPO)}

In the exact format specified by the rubric — one line per sample,
no preamble, no commentary, no summary. Output exactly one line for
every SAMPLE_NNN present in the sample file (do not assume a fixed
count).

You are deliberately a COLD agent here — you have no context from
this codebase's recent work. Score on the artifact text alone.

NOTE: cold rating is a CONTROL baseline only — it structurally floors
low (no codebase context to recognise domain-significant work). The
CANONICAL primary rater is the CONTEXTUALIZED (warm) rater. Do not
aggregate cold ratings into the primary series. See
docs/concepts/reflexive_mining_methodology.md §2.1.
"""
        instruction_path = REPO / "analytics" / "public" / "queries" / "_taste_cold_agent_instruction.md"
        instruction_path.write_text(instruction)
        print(f"  wrote cold-agent instruction → {instruction_path}")
        print(f"  next step: parent context invokes sub-agent with this instruction")
        return 0

    if args.mode == "parse-existing":
        if not args.out_md.exists():
            print(f"ERROR: --mode parse-existing needs {args.out_md} to exist (rater output)")
            return 2
        ratings = _parse_ratings(args.out_md.read_text(encoding="utf-8"))
        payload = {
            "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "n_rated": len(ratings),
            "ratings": ratings,
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, indent=2))
        print(f"  parsed {len(ratings)} ratings → {args.out_json}")
        return 0

    # mode == "llm"
    print(f"  model: {args.model or '(env default)'}")
    all_ratings: dict[str, dict] = {}
    for i in range(0, len(samples), args.batch_size):
        batch = samples[i : i + args.batch_size]
        bid = i // args.batch_size + 1
        prompt_lines = [RUBRIC, "\n---\nSamples:\n"]
        for sid, kind, content in batch:
            prompt_lines.append(f"\n### {sid} ({kind})\n```\n{content}\n```\n")
        prompt = "\n".join(prompt_lines)
        try:
            resp_text = _llm_call(prompt, model=args.model)
        except Exception as exc:  # noqa: BLE001
            print(f"  batch {bid} failed: {type(exc).__name__}: {exc}")
            continue
        parsed = _parse_ratings(resp_text)
        all_ratings.update(parsed)
        print(f"  batch {bid}: parsed {len(parsed)} of {len(batch)}")
        time.sleep(0.5)

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(samples),
        "n_rated": len(all_ratings),
        "ratings": all_ratings,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
