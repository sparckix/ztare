"""Out-of-loop JUDGE producer (GP-241 mutator→JUDGE→monitor; cold
review bbx3cuw8s PROCEED-WITH-CHANGES).

DIFF PATH ONLY — does NOT import test_thesis / autoresearch (cold (c):
that has import-time CLI/global coupling). Reuses the *proven*
cross-provider mechanism (codex gpt-5.5 xhigh — separate family from a
claude mutator) as the judge engine, plus an INDEPENDENT critique
pass (cold (a): a single judge rubber-stamps polished prose; the
critique catches an inflated PASS). Rubric is OBLIGATION-DERIVED (cold
(b): the obligation's own text + witness_schema.required + why_not_enum
recomputed un-forgeably — NOT autoresearch project rubrics).

Emits `propose --type judge_verdict` binding
{tick_id,contract_id,item_id,witness_sha,artifact_sha,verdict,
judge_identity}. The mutator then discharges its substantive
obligation with provenance `judge:<this verdict's proposal_id>`;
_resolve_provenance verifies PASS + exact binding.

Usage:
  python -m src.ztare.validator.judge_out_of_loop \
    --tick-id T --contract-id C --item-id darwin_idea_killer \
    --goal "<the tick goal>" --transition-type result \
    --witness-json '<the discharge dict MINUS provenance>' \
    [--artifact-file path]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request

# Judge = a DIRECT OpenAI API call (NOT the codex agent CLI). The
# obligation-grading task is bounded + near-deterministic (fixed
# rubric + fixed witness → JSON verdict): it needs a competent grader,
# NOT an agent with tools/sandbox/repo access. A plain chat-completion
# at temperature 0 is faster (seconds, not codex-harness minutes),
# cheaper, MORE reproducible (a deterministic judge is better for
# audit), and removes the entire codex subscription/CODEX_HOME/
# sandbox surface. gpt-4.1 is fully available via the API key (the
# ChatGPT-subscription "gpt-4.1 unsupported" limit was a codex-CLI
# auth-mode artefact, irrelevant here). The anti-gaming guarantee is
# STRUCTURAL (OS-separated judge key + cross-FAMILY + monitor
# binding), NOT judge-model IQ and NOT the transport. gpt-4.1 is
# openai-family ≠ the claude/anthropic mutator. All env-overridable.
JUDGE_MODEL = os.environ.get("ZTARE_JUDGE_MODEL", "gpt-4.1")
JUDGE_IDENTITY = f"openai:{JUDGE_MODEL}"  # openai family ≠ claude
_OPENAI_URL = os.environ.get(
    "ZTARE_JUDGE_API_URL", "https://api.openai.com/v1/chat/completions")

# GP-241 #2: the producer's ONLY output is the verdicts queue (owned
# by ztare_judge, read by the daemon). It NEVER writes the inbox /
# runs propose (the old cwd='/usr/local/ztare_gate' path is removed —
# it was a non-existent dir and an agent-relay surface). Store path is
# resolved EXACTLY as the daemon resolves it (same env var).
import pathlib as _pl
_STORE = _pl.Path(os.environ.get(
    "ZTARE_OFFICIAL_STORE",
    str(_pl.Path.home() / "ztare_official_store")))
_JVERD = _STORE / "judge_queue" / "verdicts"


def _llm(prompt: str, timeout: int = 90) -> str:
    """One deterministic OpenAI chat-completion. temperature=0 so the
    verdict is reproducible/auditable. The API key is read from the
    env (the worker unit supplies it from an agent-UNREADABLE
    EnvironmentFile; the producing mutator cannot read it and, even
    if it could, still lacks the ed25519 judge key to sign a verdict).
    Any non-200 / missing key / empty content RAISES ⇒ run_request
    returns 3 (terminal, NO verdict) ⇒ the substantive tick stays
    fail-closed (cold review bxu2w8voa R3 semantics preserved)."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY unset for the judge identity — "
            "fail-closed, no verdict")
    body = json.dumps({
        "model": JUDGE_MODEL,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        _OPENAI_URL, data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"judge API HTTP {e.code} — fail-closed, no verdict")
    except Exception as e:
        raise RuntimeError(
            f"judge API error {type(e).__name__} — fail-closed")
    try:
        content = payload["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError("judge API: no message content — "
                           "fail-closed, no verdict")
    if not str(content).strip():
        raise RuntimeError("judge API: empty content — fail-closed")
    return str(content)


def _extract_json(text: str) -> dict:
    # last {...} block the judge emitted
    depth = 0
    start = -1
    best = None
    for i, c in enumerate(text):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                best = text[start:i + 1]
    try:
        return json.loads(best) if best else {}
    except Exception:
        return {}


def _judge_core(*, tick_id: str, contract_id: str, item_id: str,
                goal: str, transition_type: str, declared: dict,
                witness: dict, artifact_sha: str = "") -> dict:
    """Run the out-of-loop judge (codex, cross-family) + the
    independent critique pass, judge-key-sign the execution proof, and
    return the `close` dict. Raises RuntimeError if the obligation is
    not a real fired one, or if the judge key is unreadable (=> this
    process is NOT the provisioned judge identity; a mutator cannot
    sign — fail-closed)."""
    witness = {k: v for k, v in (witness or {}).items()
               if k != "provenance"}
    witness_sha = hashlib.sha256(json.dumps(
        witness, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    # SINGLE-SOURCE prompt: the daemon recomputes this EXACT prompt
    # from the FROZEN start_tick and binds sha256(it) as prompt_hash
    # — a weakened rubric cannot be fed. Empty => not a real fired
    # obligation.
    from src.ztare.surfacing.pre_tick_obligation_compiler import (
        judge_prompt_for)
    judge_prompt = judge_prompt_for(
        goal, transition_type, declared or {}, item_id, witness)
    if not judge_prompt:
        raise RuntimeError(
            f"obligation {item_id!r} not a real fired obligation")
    prompt_hash = hashlib.sha256(
        judge_prompt.encode("utf-8")).hexdigest()
    raw1 = _llm(judge_prompt)
    v1 = _extract_json(raw1)
    raw_all = raw1
    verdict = str(v1.get("verdict", "fail")).strip().lower()
    # INDEPENDENT critique pass: a single judge rubber-stamps polished
    # prose; the critique downgrades an inflated/ungrounded PASS.
    if verdict == "pass":
        raw2 = _llm(
            "You are a SECOND independent reviewer. A first judge "
            "PASSED this discharge. Detect rubber-stamping / inflated "
            "pass / ungrounded acceptance.\nJUDGE PROMPT+WITNESS:\n"
            + judge_prompt + "\nFIRST VERDICT:\n"
            + json.dumps(v1, indent=2)
            + "\nOutput ONLY JSON: {\"first_pass_sound\": true|false,"
            " \"reason\": \"..\"}. false if the witness does not "
            "actually evidence the required work.")
        raw_all = raw_all + "\n---CRITIQUE---\n" + raw2
        crit = _extract_json(raw2)
        if not bool(crit.get("first_pass_sound", False)):
            verdict = "fail"
            v1["critique_override"] = crit.get("reason", "inflated")
    raw_output_hash = hashlib.sha256(
        raw_all.encode("utf-8")).hexdigest()
    proof = {
        "tick_id": tick_id, "contract_id": contract_id,
        "item_id": item_id, "prompt_hash": prompt_hash,
        "witness_sha": witness_sha, "artifact_sha": artifact_sha,
        "model_identity": JUDGE_IDENTITY,
        "raw_output_hash": raw_output_hash, "verdict": verdict,
    }
    proof_msg = json.dumps(proof, sort_keys=True, ensure_ascii=False)
    from src.ztare.gates._daemon_sig import judge_sign
    try:
        judge_sig = judge_sign(hashlib.sha256(
            proof_msg.encode("utf-8")).hexdigest())
    except Exception as e:
        raise RuntimeError(
            f"judge key unreadable ({e}) — not the provisioned judge "
            f"identity; a mutator cannot sign a verdict (fail-closed)")
    close = dict(proof)
    close["judge_identity"] = JUDGE_IDENTITY
    close["judge_sig"] = judge_sig
    close["proof_msg"] = proof_msg
    close["judged_witness"] = witness
    close["_v1"] = v1
    return close


def _emit_to_jverd(req_id: str, close: dict) -> None:
    """The producer's ONLY output: an atomic write into the
    ztare_judge-owned verdicts queue. The daemon relays it into the
    inbox. No inbox write, no propose, no agent-relay surface."""
    _JVERD.mkdir(parents=True, exist_ok=True)
    tmp = _JVERD / f".{req_id}.tmp"
    tmp.write_text(json.dumps({"close": close}), encoding="utf-8")
    tmp.replace(_JVERD / f"{req_id}.json")


def run_request(req_path: str) -> int:
    """Worker mode: service ONE daemon-signed judge_request. The
    daemon is the sole writer of requests; this verifies the daemon
    signature so a forged request (agent-steered witness/rubric)
    cannot drive the judge."""
    rec = json.loads(open(req_path, encoding="utf-8").read())
    payload = rec.get("payload") or {}
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    from src.ztare.gates._daemon_sig import verify as daemon_verify
    if not daemon_verify(hashlib.sha256(
            canonical.encode("utf-8")).hexdigest(),
            str(rec.get("daemon_sig", ""))):
        print(json.dumps({"error": "judge_request not daemon-signed "
                          "(forged/agent-steered request rejected)"}))
        return 4
    if payload.get("kind") != "judge_request":
        print(json.dumps({"error": "not a judge_request"}))
        return 4
    rid = str(payload["req_id"])
    try:
        close = _judge_core(
            tick_id=str(payload["tick_id"]),
            contract_id=str(payload["contract_id"]),
            item_id=str(payload["item_id"]),
            goal=str(payload["goal"]),
            transition_type=str(payload["start_transition_type"]),
            declared=payload.get("start_declared_signals") or {},
            witness=payload.get("witness") or {})
    except RuntimeError as e:
        print(json.dumps({"error": str(e), "req_id": rid}))
        return 3
    v1 = close.pop("_v1", {})
    # GP-241 #60: carry the judge's WHY in-band. Previously _v1 (the
    # model's verdict json incl. its `reason` / `critique_override`)
    # was popped and only printed to the worker journal — so a FAIL
    # reason never reached the agent-readable ledger and the closing
    # agent had to ssh+cat the ztare_judge-owned verdicts queue to
    # learn why (the exact information asymmetry the autoresearch
    # loop does NOT have: there the verifier feedback is in-band).
    # `judge_reason` is ADVISORY feedback only — it is NOT part of the
    # signed `proof` (verdict + raw_output_hash already cryptographically
    # bind the full model output for trust); adding an unsigned
    # feedback string cannot weaken the verdict. Bounded length.
    close["judge_reason"] = str(
        v1.get("reason")
        or v1.get("critique_override")
        or v1.get("rationale")
        or "")[:800]
    _emit_to_jverd(rid, close)
    print(json.dumps({"req_id": rid, "judge_verdict": close["verdict"],
                      "v1": v1}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", help="path to a daemon-signed "
                    "judge_request (worker mode — the ONLY supported "
                    "mode; the producer never writes the inbox)")
    a = ap.parse_args()
    if not a.request:
        print(json.dumps({"error": "judge_out_of_loop is request-"
              "driven only: pass --request <daemon-signed file>. The "
              "daemon emits requests; the ztare_judge worker services "
              "them. There is no agent-invoked path (by design)."}))
        return 2
    return run_request(a.request)


if __name__ == "__main__":
    raise SystemExit(main())
