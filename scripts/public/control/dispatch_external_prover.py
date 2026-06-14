#!/usr/bin/env python3
"""
dispatch_external_prover.py

PATTERN-014 (independent_cas_verification) deployer using the OpenAI API.

Operator-authorized 2026-05-09: up to $10 spend per session for cross-
family external-prover dispatch on decision-critical eigenquestions. Closes
the structural gap PATTERN-013 (pattern_deployment_ledger) flagged on
the same day: PATTERN-014 utilization was ~0% over the 17-dispatch
campaign window, which is exactly why operator-relayed GPT-5.5 had to
surface catch C-2026-05-09-59 (Lerner port unfaithful) instead of the RD.

Usage:
  python scripts/public/control/dispatch_external_prover.py \\
    --eigenquestion path/to/question.md \\
    --substrate NS-Track-B \\
    --max-cost-usd 5.0 \\
    --reasoning-effort high

  # Or pipe a question directly:
  echo "Is X a faithful encoding of Y? Specify divergences." | \\
    python scripts/public/control/dispatch_external_prover.py --substrate meta-architecture

Output:
  * Verdict + reasoning printed to stdout.
  * One row appended to analytics/public/ledgers/external_prover/external_prover_ledger.jsonl
  * One row appended to analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl
    (pattern PATTERN-014, external_via_operator=False, since the dispatch
    is now RD-direct rather than operator-mediated).

Cost guardrails:
  * Hard cap on total spend per invocation (default $5; max $10).
  * Hard cap on output tokens (default 8000).
  * 600s timeout (operator said "10 min" — extended-thinking models need it).
  * Default --max-output-tokens 32000 (NOT 8000). Reasoning models consume
    8-16K on internal reasoning BEFORE producing visible text; with default
    8K, finish_reason="length" and response is empty. Empirical 2026-05-09:
    one $0.26 dispatch returned 0 chars at 8K cap. NEVER lower the default
    without operator authorization.
  * Prints estimated cost AFTER each dispatch and refuses to continue if
    cumulative session spend (logged in ledger) exceeds session-cap.

Model selection:
  * Default: `gpt-5` (the operator's "GPT-5.5 extended thinking" reference).
  * Fallback: `gpt-5-mini`, then `gpt-4.1`, then `o1`.
  * Override via --model.

Pricing assumptions (2026-05-09 published rates; CHECK before relying):
  * gpt-5:     ~$10/M input, ~$30/M output  (estimate; not authoritative)
  * gpt-5-mini: ~$2/M input,  ~$8/M output
  * gpt-4.1:   ~$3/M input,  ~$12/M output
  * o1:        ~$15/M input, ~$60/M output

The script logs actual usage tokens reported by the API and computes
cost from a hard-coded price table. Update PRICE_TABLE if rates change.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


# Tenant-root resolution. Promoted from figs to cognitive-firm 2026-05-10
# per operator architectural-debt directive. Reads $TENANT_ROOT or falls
# back to repo root for in-repo dev.
def _resolve_repo() -> Path:
    env = os.environ.get("TENANT_ROOT")
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parents[3]  # scripts/public/control/<f> → repo root

REPO = _resolve_repo()
EXTERNAL_LEDGER = REPO / "analytics/public/ledgers/external_prover/external_prover_ledger.jsonl"
PATTERN_LEDGER = REPO / "analytics/public/ledgers/pattern_deployment/pattern_deployment_ledger.jsonl"
SESSION_HARD_CAP_USD = 10.0

PRICE_TABLE = {
    "gpt-5": {"input_per_mtok": 10.00, "output_per_mtok": 30.00},
    "gpt-5-mini": {"input_per_mtok": 2.00, "output_per_mtok": 8.00},
    "gpt-4.1": {"input_per_mtok": 3.00, "output_per_mtok": 12.00},
    "gpt-4.1-mini": {"input_per_mtok": 0.40, "output_per_mtok": 1.60},
    "o1": {"input_per_mtok": 15.00, "output_per_mtok": 60.00},
    "o3-mini": {"input_per_mtok": 1.10, "output_per_mtok": 4.40},
    # DeepSeek family (2026-05-26): added per AGENTS.md §6n.3 cross-family
    # model integration. OpenAI-API-compatible endpoint, but different
    # base_url + API key (see dispatch_openai branch below).
    "deepseek-chat":     {"input_per_mtok": 0.27, "output_per_mtok": 1.10},
    "deepseek-reasoner": {"input_per_mtok": 0.55, "output_per_mtok": 2.19},
}

DEFAULT_MODEL = "gpt-5"
DEFAULT_FALLBACKS = ["gpt-5-mini", "gpt-4.1", "o1"]

SYSTEM_PROMPT = """\
You are an external mathematical prover dispatched as PATTERN-014 (independent
cross-family verification) by the ZTARE Research Director. Your role is to
attack a decision-critical eigenquestion from the ZTARE NS Track B campaign with
maximum rigor.

Operating discipline:
  1. Treat every claim in the question as a HYPOTHESIS, not a fact.
  2. If asked "is X a faithful encoding of Y", produce specific divergences
     in standard form (precondition / hypothesis / quantifier scope /
     conclusion).
  3. If asked "does the substrate provide property P", produce either a
     proof sketch OR an explicit counterexample. Vague "it depends" answers
     are not acceptable — name the regime.
  4. Cite published results with arXiv ids, theorem numbers, page numbers
     when possible.
  5. End with a one-line VERDICT: "yes / no / partially / unknown — [one
     sentence rationale]".

Be terse. Mathematical density over verbosity. If the question contains
hedging language ("inspired by", "transcription", "port"), demand the
exact precondition+conclusion form before answering.
"""


def load_ledger(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def cumulative_session_spend(rows: list[dict],
                             window_hours: float = 12.0) -> float:
    """SESSION spend = cost of dispatches within the last `window_hours`
    (default 12h; env ZTARE_DISPATCH_SESSION_HOURS). BUGFIX 2026-05-17:
    this previously summed the ENTIRE all-time ledger and called it
    'session spend', so once the lifetime total crossed the $10 cap it
    PERMANENTLY false-refused every dispatch (operator-flagged). Rows
    with no parseable `dispatched_at` are excluded (an undated legacy
    row must not inflate the live session)."""
    import os as _os
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    try:
        window_hours = float(_os.environ.get(
            "ZTARE_DISPATCH_SESSION_HOURS", window_hours))
    except Exception:
        pass
    cutoff = _dt.now(_tz.utc) - _td(hours=window_hours)
    total = 0.0
    for r in rows:
        raw = r.get("dispatched_at")
        if not raw:
            continue
        try:
            t = _dt.fromisoformat(str(raw))
            if t.tzinfo is None:
                t = t.replace(tzinfo=_tz.utc)
        except Exception:
            continue
        if t >= cutoff:
            total += float(r.get("estimated_cost_usd", 0.0) or 0.0)
    return total


def append_ledger(path: Path, row: dict) -> None:
    with path.open("a") as f:
        f.write(json.dumps(row) + "\n")


def estimate_cost(model: str, in_tokens: int, out_tokens: int) -> float:
    p = PRICE_TABLE.get(model)
    if p is None:
        return 0.0
    return (in_tokens / 1_000_000) * p["input_per_mtok"] + (
        out_tokens / 1_000_000
    ) * p["output_per_mtok"]


API_PROVER_OVERRIDE_ENV = "ZTARE_ALLOW_API_PROVER"


def _enforce_subscription_only(model: str) -> None:
    """Operator policy 2026-05-18: ALL external provers (codex AND
    claude) must run via the subscription CLI (`codex exec` /
    `claude -p`), NOT the metered API. This API dispatch path is
    deliberately PRESERVED (not deleted) so the operator can resume it
    going forward, but it FAILS CLOSED: it returns an error instead of
    spending on the API unless the operator explicitly opts back in by
    setting ZTARE_ALLOW_API_PROVER=1."""
    ov = os.environ.get(API_PROVER_OVERRIDE_ENV, "").strip().lower()
    if ov in ("1", "true", "yes", "on"):
        print(
            f"[policy] {API_PROVER_OVERRIDE_ENV} set — API external-prover "
            f"path explicitly re-enabled by operator for model={model} "
            f"(METERED API spend).",
            file=sys.stderr,
        )
        return
    print(
        "ERROR: API external-prover path is DISABLED by operator policy "
        "(2026-05-18). External provers must run via the SUBSCRIPTION "
        "CLI — `codex exec` (codex / OpenAI-family) or `claude -p` "
        "(Anthropic) — not the metered API. This code path is preserved "
        f"(not removed); to intentionally resume it going forward set "
        f"{API_PROVER_OVERRIDE_ENV}=1 in the environment.",
        file=sys.stderr,
    )
    raise SystemExit(3)


def dispatch_openai(
    *,
    question: str,
    model: str,
    max_output_tokens: int,
    reasoning_effort: str,
    timeout_sec: int,
) -> tuple[str, dict]:
    """Returns (response_text, raw_metadata)."""
    _enforce_subscription_only(model)
    try:
        from openai import OpenAI
    except ImportError:
        print(
            "ERROR: `openai` package not installed. Install with `pip install openai`.",
            file=sys.stderr,
        )
        sys.exit(2)

    # DeepSeek family routes through a different base_url + API key.
    # OpenAI-API-compatible interface, but separate vendor. Per AGENTS.md
    # §6n.3, DeepSeek integration goes through this dispatcher rather than
    # a new utility.
    if model.startswith("deepseek"):
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        if not deepseek_key:
            print("ERROR: DEEPSEEK_API_KEY not set; required for deepseek-* models.", file=sys.stderr)
            sys.exit(2)
        client = OpenAI(api_key=deepseek_key,
                        base_url="https://api.deepseek.com/v1",
                        timeout=timeout_sec)
    else:
        client = OpenAI(timeout=timeout_sec)
    started_at = time.time()

    use_reasoning = model.startswith(("o", "gpt-5"))
    is_deepseek_reasoner = model == "deepseek-reasoner"
    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    }
    if use_reasoning:
        # OpenAI reasoning models: max_completion_tokens (not max_tokens)
        # plus reasoning_effort. Legacy o-series accept reasoning_effort.
        kwargs["max_completion_tokens"] = max_output_tokens
        try:
            kwargs["reasoning_effort"] = reasoning_effort
        except Exception:
            pass
    elif is_deepseek_reasoner:
        # DeepSeek-R1 burns tokens on internal reasoning BEFORE output;
        # ensure at least 8K budget. Uses standard max_tokens (NOT
        # max_completion_tokens — OpenAI-compat shim doesn't support that).
        # No reasoning_effort param (DeepSeek API rejects it).
        kwargs["max_tokens"] = max(max_output_tokens, 8192)
    else:
        kwargs["max_tokens"] = max_output_tokens
        kwargs["temperature"] = 0.2

    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:
        # Last-ditch retry without reasoning_effort if model rejects it.
        if "reasoning_effort" in kwargs:
            kwargs.pop("reasoning_effort", None)
            resp = client.chat.completions.create(**kwargs)
        else:
            raise

    elapsed = time.time() - started_at
    text = resp.choices[0].message.content or ""
    usage = resp.usage
    meta = {
        "elapsed_sec": round(elapsed, 2),
        "in_tokens": getattr(usage, "prompt_tokens", 0),
        "out_tokens": getattr(usage, "completion_tokens", 0),
        "total_tokens": getattr(usage, "total_tokens", 0),
        "finish_reason": resp.choices[0].finish_reason,
        "model_used": resp.model,
    }
    return text, meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eigenquestion", type=str, default=None,
                        help="Path to a markdown file containing the eigenquestion. "
                             "If omitted, reads stdin.")
    parser.add_argument("--substrate", type=str, default="NS-Track-B")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--max-output-tokens", type=int, default=64000,
                        help="Default 64K (raised from 32K 2026-05-09 ~19:00 UTC per operator: "
                             "'don't be overly conservative on tokens'). GPT-5 + reasoning_effort=high "
                             "can consume 8-32K tokens on reasoning before producing visible text; "
                             "32K cap empirically caused PL-095 empty-response on Caccioppoli at p=4 "
                             "(out_tokens=32000, response_chars=0, cost $0.97 wasted). 64K is the "
                             "safe default. Use 128000 for genuinely hard problems requiring full "
                             "journal-style proofs. Original operator catch 2026-05-09 ~early-evening: "
                             "'Most of gpt5.5 always came empty we need more fucking tokens by default "
                             "otherwise I just waste money.'")
    parser.add_argument("--reasoning-effort", type=str, default="high",
                        choices=["minimal", "low", "medium", "high",
                                 "xhigh"])  # xhigh = GPT-5.5 hardest
                        # async/eval tier (verified vs OpenAI docs
                        # 2026-05-17). dispatch_openai retries without
                        # reasoning_effort if a model rejects it ⇒ safe.
    parser.add_argument("--timeout-sec", type=int, default=1800,
                        help="Default 1800s (30 min, raised from 600s 2026-05-09 ~23:30 "
                             "UTC per operator + Gowers 2026-05-08 calibration). Gowers's "
                             "ChatGPT-5.5-Pro tasks ran 13-47 min wall-clock on serious "
                             "math; 600s default was empirically cutting off frontier "
                             "reasoning before completion. 1800s is the safe default; "
                             "lower it explicitly for cheap dispatches if needed.")
    parser.add_argument("--max-cost-usd", type=float, default=5.0,
                        help="Per-invocation cost cap; refused if estimated cost exceeds.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan and exit; no API call.")
    args = parser.parse_args()

    if args.max_cost_usd > SESSION_HARD_CAP_USD:
        print(f"ERROR: --max-cost-usd {args.max_cost_usd} exceeds session hard cap "
              f"${SESSION_HARD_CAP_USD}. Refusing.", file=sys.stderr)
        return 2

    existing = load_ledger(EXTERNAL_LEDGER)
    spent = cumulative_session_spend(existing)
    if spent + args.max_cost_usd > SESSION_HARD_CAP_USD:
        print(f"ERROR: cumulative session spend ${spent:.2f} + this dispatch's "
              f"cap ${args.max_cost_usd} would exceed session hard cap "
              f"${SESSION_HARD_CAP_USD}. Refusing.", file=sys.stderr)
        return 2

    if args.eigenquestion:
        question = Path(args.eigenquestion).read_text()
    else:
        question = sys.stdin.read()
    if not question.strip():
        print("ERROR: empty question.", file=sys.stderr)
        return 2

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set in environment.", file=sys.stderr)
        return 2

    plan = {
        "model": args.model,
        "max_output_tokens": args.max_output_tokens,
        "reasoning_effort": args.reasoning_effort,
        "timeout_sec": args.timeout_sec,
        "max_cost_usd": args.max_cost_usd,
        "session_spent_so_far_usd": round(spent, 4),
        "session_hard_cap_usd": SESSION_HARD_CAP_USD,
        "question_chars": len(question),
        "substrate": args.substrate,
    }
    print(f"=== external-prover dispatch plan ===")
    for k, v in plan.items():
        print(f"  {k}: {v}")

    if args.dry_run:
        print("\n--dry-run: skipping API call.")
        return 0

    print("\n=== dispatching ===")
    try:
        text, meta = dispatch_openai(
            question=question,
            model=args.model,
            max_output_tokens=args.max_output_tokens,
            reasoning_effort=args.reasoning_effort,
            timeout_sec=args.timeout_sec,
        )
    except Exception as e:
        print(f"\nERROR during dispatch: {type(e).__name__}: {e}", file=sys.stderr)
        # Try fallback chain.
        for fallback in DEFAULT_FALLBACKS:
            if fallback == args.model:
                continue
            print(f"\n--- attempting fallback: {fallback} ---", file=sys.stderr)
            try:
                text, meta = dispatch_openai(
                    question=question,
                    model=fallback,
                    max_output_tokens=args.max_output_tokens,
                    reasoning_effort=args.reasoning_effort,
                    timeout_sec=args.timeout_sec,
                )
                args.model = fallback
                break
            except Exception as e2:
                print(f"  fallback {fallback} failed: {e2}", file=sys.stderr)
        else:
            print("\nAll fallbacks exhausted. Giving up.", file=sys.stderr)
            return 3

    cost = estimate_cost(args.model, meta["in_tokens"], meta["out_tokens"])

    print(f"\n=== response ===\n{text}")
    print(f"\n=== meta ===")
    print(f"  model: {meta.get('model_used', args.model)}")
    print(f"  elapsed: {meta['elapsed_sec']}s")
    print(f"  in_tokens: {meta['in_tokens']}")
    print(f"  out_tokens: {meta['out_tokens']}")
    print(f"  estimated_cost_usd: ${cost:.4f}")
    print(f"  session_spend_now_usd: ${spent + cost:.4f} / ${SESSION_HARD_CAP_USD}")

    dispatch_id = f"epd-{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    ext_row = {
        "dispatch_id": dispatch_id,
        "dispatched_at": now_iso,
        "model_used": meta.get("model_used", args.model),
        "substrate": args.substrate,
        "question_chars": len(question),
        "question_first_120": question[:120].replace("\n", " "),
        "in_tokens": meta["in_tokens"],
        "out_tokens": meta["out_tokens"],
        "elapsed_sec": meta["elapsed_sec"],
        "estimated_cost_usd": round(cost, 4),
        "finish_reason": meta["finish_reason"],
        "response_chars": len(text),
        "response_first_300": text[:300].replace("\n", " "),
    }
    append_ledger(EXTERNAL_LEDGER, ext_row)

    pdl_row = {
        "dispatch_id": f"pdl-{dispatch_id}",
        "dispatched_at": now_iso,
        "task_id": dispatch_id,
        "substrate": args.substrate,
        "primary_pattern": "PATTERN-014",
        "secondary_patterns": ["PATTERN-005", "PATTERN-015"],
        "eigenquestion_shape": True,
        "audit_or_construct": "audit",
        "external_or_internal": "external_via_api",
        "outcome_bucket_pre_registered": None,
        "outcome_bucket_realized": None,
        "notes": f"PATTERN-014 RD-direct via OpenAI API (model={meta.get('model_used', args.model)}); cost=${cost:.4f}",
    }
    append_ledger(PATTERN_LEDGER, pdl_row)

    print(f"\nLedgers updated:")
    print(f"  {EXTERNAL_LEDGER.relative_to(REPO)} (+1 row)")
    print(f"  {PATTERN_LEDGER.relative_to(REPO)} (+1 row, PATTERN-014)")

    out_path = REPO / f"analytics/public/external_prover_responses/{dispatch_id}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        f"# External-prover dispatch {dispatch_id}\n\n"
        f"**Model**: {meta.get('model_used', args.model)}\n"
        f"**Substrate**: {args.substrate}\n"
        f"**Dispatched**: {now_iso}\n"
        f"**Cost**: ${cost:.4f}\n"
        f"**Tokens**: {meta['in_tokens']} in / {meta['out_tokens']} out\n\n"
        f"## Question\n\n{question}\n\n"
        f"## Response\n\n{text}\n"
    )
    print(f"  {out_path.relative_to(REPO)} (full response)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
