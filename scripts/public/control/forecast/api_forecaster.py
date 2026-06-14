#!/usr/bin/env python3
"""Cheap one-off API forecasters for the forecast pool.

The pool's `warm-consumer` only dispatches PERSISTENT WARM SUBSCRIPTION agents (claude/codex CLI). But the
pool's `add-forecast` CLI is GENERIC — any agent_id may submit a `p_success`. So this feeds the pool with
EPHEMERAL one-off API calls to CHEAP models (deepseek-chat ~1-2s, gemini-3.1-flash-lite) via the existing
`llm_runtime`, instead of burning the claude/codex subscription on forecasting (which should be saved for
SOLVING). Cheap models are perfectly good at "estimate P(close)". No edit to pool.py — it just calls
`pool.py add-forecast`.

  one-off:  python -m scripts...api_forecaster --contract-id <id>
  daemon :  python -m scripts...api_forecaster --loop --interval 20
  (default forecasters: deepseek + gemini-lite — diverse + cheap)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
POOL = REPO / "scripts/public/control/forecast/pool.py"
CONTRACTS = REPO / "analytics/public/forecast_pool/contracts"

DEFAULT_MODELS = [m.strip() for m in
                  os.environ.get("ZTARE_POOL_API_FORECASTERS", "deepseek,gemini-lite").split(",") if m.strip()]
_PJSON = re.compile(r'"p_success"\s*:\s*([01](?:\.\d+)?|0?\.\d+)')
_RJSON = re.compile(r'"rationale"\s*:\s*"([^"]{0,200})"')


def _read_contract(cid: str) -> "dict | None":
    p = CONTRACTS / f"{cid}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _forecast(question: str, model_name: str, *, timeout: int = 60) -> "tuple[float | None, str]":
    """One EPHEMERAL API completion → (p_success, rationale). None on any failure (the model abstains)."""
    try:
        from src.ztare.common.llm_runtime import LLMRuntime, MODEL_MAP  # type: ignore
    except Exception as e:  # noqa: BLE001
        return None, f"llm_runtime import failed: {e}"[:120]
    model_id = MODEL_MAP.get(model_name, model_name)
    prompt = (
        "You are a calibrated forecaster pricing a YES/NO question for a prediction market. Estimate the "
        "PROBABILITY (a number strictly between 0 and 1) that it resolves YES. Weigh difficulty and base "
        "rates; avoid 0 and 1. Reply with ONLY a one-line JSON object: "
        '{"p_success": <0..1>, "rationale": "<=12 words"}.\n\nQUESTION: ' + (question or "")[:1500]
    )
    try:
        resp = LLMRuntime().call_text(prompt, model_id=model_id, timeout_seconds=timeout,
                                      max_tokens=400, request_label="pool_api_forecast")
        text = getattr(resp, "text", "") or (resp if isinstance(resp, str) else "")
    except Exception as e:  # noqa: BLE001
        return None, f"call failed: {e}"[:120]
    m = _PJSON.search(text or "")
    if m:
        try:
            p = float(m.group(1))
        except ValueError:
            return None, "p parse error"
    else:
        nums = re.findall(r"(?<![\w.])(?:0?\.\d+|1\.0+|[01])(?![\w.])", text or "")
        if not nums:
            return None, "no number parsed"
        try:
            p = float(nums[-1])
        except ValueError:
            return None, "p parse error"
    p = max(0.001, min(0.999, p))  # keep strictly interior (the pool prefers non-degenerate prices)
    rm = _RJSON.search(text or "")
    return p, (rm.group(1) if rm else f"{model_name} api forecast")


def forecast_contract(cid: str, models: "list[str]") -> int:
    c = _read_contract(cid)
    if not c:
        print(f"[api_forecaster] no contract {cid}", flush=True)
        return 0
    q = c.get("question", "")
    submitted = 0
    for model_name in models:
        p, rat = _forecast(q, model_name)
        if p is None:
            print(f"[api_forecaster] {model_name} on {cid}: SKIP ({rat})", flush=True)
            continue
        r = subprocess.run(
            [sys.executable, str(POOL), "add-forecast", "--contract-id", cid,
             "--agent-id", f"{model_name}:api_forecaster", "--p-success", f"{p:.4f}",
             "--rationale-short", rat[:200], "--read-only-attestation", "--allow-missing-best-practice"],
            cwd=str(REPO), capture_output=True, text=True)
        ok = r.returncode == 0
        print(f"[api_forecaster] {model_name} on {cid}: p={p:.3f} add-forecast="
              f"{'OK' if ok else ((r.stderr or r.stdout) or '')[-120:]}", flush=True)
        submitted += int(ok)
    return submitted


def _pending(min_forecasts: int) -> "list[str]":
    r = subprocess.run([sys.executable, str(POOL), "status"], cwd=str(REPO), capture_output=True, text=True)
    if r.returncode != 0:
        return []
    try:
        rows = json.loads(r.stdout).get("contracts", [])
    except Exception:  # noqa: BLE001
        return []
    return [str(row["contract_id"]) for row in rows
            if not row.get("resolved") and int(row.get("forecast_count", 0)) < min_forecasts]


def main() -> int:
    ap = argparse.ArgumentParser(description="Cheap API forecasters feeding the forecast pool.")
    ap.add_argument("--contract-id", default=None, help="forecast one contract; omit to sweep pending")
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    ap.add_argument("--min-forecasts", type=int, default=2)
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=float, default=20.0)
    ap.add_argument("--max-iterations", type=int, default=None)
    args = ap.parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    it = 0
    while True:
        cids = [args.contract_id] if args.contract_id else _pending(args.min_forecasts)
        total = sum(forecast_contract(cid, models) for cid in cids)
        if cids:
            print(f"[api_forecaster] tick {it}: {len(cids)} contract(s), {total} forecast(s) submitted", flush=True)
        it += 1
        if not args.loop or (args.max_iterations is not None and it >= args.max_iterations):
            break
        time.sleep(max(1.0, args.interval))
    return 0


if __name__ == "__main__":
    sys.exit(main())
