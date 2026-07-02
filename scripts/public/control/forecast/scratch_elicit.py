#!/usr/bin/env python3
"""On-demand forecast: elicit a probability for ANY question, then price it via the sealed pool.

The forecast pool (`pool.py scratch-forecast`) PRICES a supplied probability with tail-risk +
calibration — it does not invent the number. This thin layer closes that gap so the workbench can get
a forecast at a click: it elicits `p_success` (+ tail terms + rationale) via the ONE transport door
(`dispatch_call_text` — API or subscription, same as synthesis/autoresearch), then shells out to the
sealed pool to produce the priced scratch contract. The pool stays isolated (subprocess); only the
elicitation is agentic.

    ztare forecast scratch-elicit --question "Will X hold?" --domain ops [--model gemini] [--json]
    ztare forecast scratch-elicit --question "..." --stub-p 0.72   # deterministic, no model call

Output (--json): { question, domain, elicited{...}, scratch_id, contract_path, contract{...} }.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
POOL = REPO_ROOT / "scripts" / "public" / "control" / "forecast" / "pool.py"

ELICIT_SCHEMA = (
    "Return ONLY a JSON object with these fields (no prose):\n"
    '{"p_success": <0..1 probability the answer to the question is YES/the claim holds>,\n'
    ' "tail_insurance_premium": <0..1 how much you would pay to insure the bad tail>,\n'
    ' "tail_loss_magnitude": <0..1 how bad the downside is if wrong>,\n'
    ' "tail_downside_worry": <0..1 optional>, "tail_upside_surprise": <0..1 optional>,\n'
    ' "verbalized_confidence": <0..1 optional>,\n'
    ' "rationale_short": "<one sentence>",\n'
    ' "failure_modes": {"<mode label>": <0..1 weight>, ...}}\n'
)


def build_prompt(question: str, agent_id: str, context: str = "") -> str:
    """Compose the elicitation prompt: the pool's recommended fragments + the question + the schema."""
    block = ""
    try:
        out = subprocess.run(
            [sys.executable, str(POOL), "prompt-template", "--agent-id", agent_id, "--format", "json"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
        )
        if out.returncode == 0:
            block = str(json.loads(out.stdout).get("prompt_block") or "")
    except Exception:
        block = ""
    parts = [block.strip()] if block.strip() else []
    if context.strip():
        parts.append(f"Context:\n{context.strip()}")
    parts.append(f"Question: {question.strip()}")
    parts.append(ELICIT_SCHEMA)
    return "\n\n".join(parts)


def _coerce_unit(value, default=None):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, f))


def parse_elicitation(text: str) -> dict:
    """Extract the JSON object from the agent's reply and validate the required forecast fields."""
    m = re.search(r"\{.*\}", str(text or ""), re.S)
    if not m:
        raise ValueError("elicitation returned no JSON object")
    raw = json.loads(m.group(0))
    p = _coerce_unit(raw.get("p_success"))
    if p is None:
        raise ValueError("elicitation missing a valid p_success in [0,1]")
    fm = raw.get("failure_modes")
    if not isinstance(fm, dict) or not fm:
        fm = {"unspecified_failure": 1.0}
    return {
        "p_success": p,
        "tail_insurance_premium": _coerce_unit(raw.get("tail_insurance_premium"), 0.1),
        "tail_loss_magnitude": _coerce_unit(raw.get("tail_loss_magnitude"), 0.3),
        "tail_downside_worry": _coerce_unit(raw.get("tail_downside_worry"), 0.0),
        "tail_upside_surprise": _coerce_unit(raw.get("tail_upside_surprise"), 0.0),
        "verbalized_confidence": _coerce_unit(raw.get("verbalized_confidence")),
        "rationale_short": str(raw.get("rationale_short") or "Elicited on demand.").strip()[:280],
        "failure_modes": {str(k): _coerce_unit(v, 0.0) for k, v in fm.items()},
    }


def elicit_via_agent(question: str, domain: str, model: str, agent_id: str, context: str) -> dict:
    """Elicit through the ONE transport door (API or subscription per ZTARE_AGENT_DISPATCH[_FORECAST])."""
    from ztare.common.dispatch_model import dispatch_call_text
    from ztare.common.llm_runtime import LLMRuntime, MODEL_MAP

    runtime = LLMRuntime()
    model_id = MODEL_MAP.get(model, MODEL_MAP.get("gemini"))
    prompt = build_prompt(question, agent_id, context)
    response = dispatch_call_text(
        "forecast_elicit",
        prompt,
        llm_response_call=lambda p: runtime.call_text(
            p, model_id=model_id, retries=3, timeout_seconds=180, request_label="forecast elicitation"
        ),
        repo=REPO_ROOT,
        agent_id=agent_id,
    )
    return parse_elicitation(response.text)


def price_via_pool(question: str, domain: str, owner: str, elicited: dict, context_json: str) -> dict:
    """Shell out to the SEALED pool to price the elicited probability into a scratch contract."""
    cmd = [
        sys.executable, str(POOL), "scratch-forecast",
        "--question", question, "--domain", domain, "--owner", owner,
        "--p-success", str(elicited["p_success"]),
        "--tail-insurance-premium", str(elicited["tail_insurance_premium"]),
        "--tail-loss-magnitude", str(elicited["tail_loss_magnitude"]),
        "--tail-downside-worry", str(elicited["tail_downside_worry"]),
        "--tail-upside-surprise", str(elicited["tail_upside_surprise"]),
        "--rationale-short", elicited["rationale_short"],
        "--failure-modes-json", json.dumps(elicited["failure_modes"]),
        "--context-json", context_json or "{}",
        "--ack-uncertified",
    ]
    if elicited.get("verbalized_confidence") is not None:
        cmd += ["--verbalized-confidence", str(elicited["verbalized_confidence"])]
    out = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"pool scratch-forecast failed: {out.stderr.strip()[:300]}")
    receipt = json.loads(re.search(r"\{.*\}", out.stdout, re.S).group(0))
    contract = {}
    cpath = receipt.get("path")
    if cpath and (REPO_ROOT / cpath).exists():
        contract = json.loads((REPO_ROOT / cpath).read_text())
    return {"scratch_id": receipt.get("scratch_id"), "contract_path": cpath, "contract": contract}


def run(args: argparse.Namespace) -> dict:
    if args.stub_p is not None:  # deterministic path — no model call (used by the self-check + tests)
        elicited = parse_elicitation(json.dumps({
            "p_success": args.stub_p, "tail_insurance_premium": 0.1, "tail_loss_magnitude": 0.3,
            "rationale_short": "Stubbed elicitation.", "failure_modes": {"stub": 1.0},
        }))
    else:
        elicited = elicit_via_agent(args.question, args.domain, args.model, args.agent_id, args.context)
    priced = price_via_pool(args.question, args.domain, args.owner, elicited, args.context_json)
    return {"question": args.question, "domain": args.domain, "elicited": elicited, **priced}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="On-demand forecast: elicit a probability, then price it via the sealed pool.")
    ap.add_argument("--question", required=True)
    ap.add_argument("--domain", default="workbench")
    ap.add_argument("--owner", default="workbench:scratch")
    ap.add_argument("--model", default="gemini")
    ap.add_argument("--agent-id", default="claude")
    ap.add_argument("--context", default="")
    ap.add_argument("--context-json", default="{}")
    ap.add_argument("--stub-p", type=float, default=None, help="deterministic p_success (skips the model call)")
    ap.add_argument("--json", action="store_true", help="emit the full contract JSON")
    args = ap.parse_args(argv)
    result = run(args)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        e = result["elicited"]
        print(f"{round(e['p_success'] * 100)}% — {e['rationale_short']}")
        print(f"scratch_id: {result.get('scratch_id')}  contract: {result.get('contract_path')}")
    return 0


def _selfcheck() -> None:
    # parse_elicitation: clamps, fills defaults, requires p_success.
    e = parse_elicitation('{"p_success": 1.4, "rationale_short": "x", "failure_modes": {"m": 2}}')
    assert e["p_success"] == 1.0 and e["failure_modes"]["m"] == 1.0, e
    try:
        parse_elicitation('{"rationale_short": "no p"}'); assert False, "should require p_success"
    except ValueError:
        pass
    # build_prompt embeds the question + schema.
    pr = build_prompt("Will X hold?", "claude")
    assert "Will X hold?" in pr and "p_success" in pr
    print("scratch_elicit selfcheck: OK")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        _selfcheck()
    else:
        raise SystemExit(main())
