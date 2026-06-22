"""API-backed agentic leaf: kimi / deepseek as a TOOL-USING prover via OpenAI-compatible function-calling.

WHY (operator 2026-06-21): the CLI leaves (codex/claude) iterate mid-proof with tools (warm `lean_check`,
Loogle `mathlib_search`) through the *vendor's* agent harness — which is why the leaf was subscription-only.
This runs that same tool loop OURSELVES around a METERED API model, so kimi/deepseek can be a real agentic
leaf. PURPOSE: spread leaf load off the rate-limited SUBSCRIPTION quota (the recurring "usage-limit
dead-instrument" that has zeroed runs) onto cheap pay-as-you-go API, and run more proofs in parallel.

SOUND BY CONSTRUCTION (Goldilocks): the leaf is a proof PRODUCER, not a judge — the kernel re-verifies every
closure (statement_integrity + #print-axioms + MNC) regardless of which model produced it. So a weaker/cheaper
leaf can only lower the CLOSURE RATE, never launder a false closure. Zero new soundness surface.

DEFAULT-OFF: the leaf stays codex/claude. Set `ZTARE_LEANMILL_LEAF_RUNTIME=kimi` (or `deepseek`) to route the
leaf here; `agentic_leaf.default_dispatch` branches on `is_api_runtime`. Same TEXT contract as the CLI leaf
(a fenced ```lean proof, with `-- GAP:` / `-- STATEMENT-FALSE:` markers preserved), so every downstream
verify/govern/extract path is unchanged. A/B vs codex/claude is the open lift measurement.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

# The API runtimes this leaf serves (OpenAI-compatible chat+tools). codex/claude are the CLI agents and are
# NOT here — they go through subscription_agent_runtime. Model ids resolve via llm_runtime's alias table.
_API_RUNTIMES = {"kimi", "deepseek"}
_MODEL_ID = {"kimi": "kimi-k2.6", "deepseek": "deepseek-chat"}
_MAX_ROUNDS = 24          # tool-call turns before we force a final answer (bounded free-will; budget also caps)
_LEAN_CHECK_TIMEOUT = 60  # per lean_check tool call (warm REPL is ~ms-s; this is the safety ceiling)


def is_api_runtime(runtime: str) -> bool:
    """True iff `runtime` names an API-backed agentic leaf (kimi/deepseek), so `default_dispatch` routes here
    instead of the CLI subscription path. Reads the raw value — subscription_agent_runtime's supported-set
    (codex/claude) deliberately does NOT include these, so the CLI selector still degrades unknowns to codex."""
    return (runtime or "").strip().lower() in _API_RUNTIMES


def _client_and_model(runtime: str):
    """The configured OpenAI-SDK client (base_url + key) + resolved model id for an API runtime — REUSES
    `llm_runtime.LLMRuntime`'s kimi/deepseek clients (no re-rolled base_urls/keys). Returns (client, model_id)
    or (None, "") when the SDK/key is absent (⇒ caller treats as inadmissible, never a real negative)."""
    rt = (runtime or "").strip().lower()
    try:
        from ztare.common.llm_runtime import LLMRuntime
        rtme = LLMRuntime()
        client = rtme.kimi_client() if rt == "kimi" else rtme.deepseek_client() if rt == "deepseek" else None
    except Exception:  # noqa: BLE001 — missing key/SDK ⇒ no client
        client = None
    return client, _MODEL_ID.get(rt, rt)


# ── tools (REUSE the canonical primitives — warm REPL compile + Loogle) ────────────────────────────────
_TOOL_SCHEMA = [
    {"type": "function", "function": {
        "name": "lean_check",
        "description": "Compile a complete Lean 4 snippet (with `import Mathlib`) against the warm Mathlib "
                       "environment and return the compiler diagnostics. Use it to VERIFY a proof or probe a "
                       "tactic before finalizing. `sorry` is allowed (reported, not an error).",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "The full Lean source to compile."}}, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "mathlib_search",
        "description": "Search Mathlib for declarations matching a Loogle query (by name substring, or by type "
                       "pattern like `(?a -> ?b) -> List ?a -> List ?b`). Returns matching declaration names+types.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "A Loogle query string."}}, "required": ["query"]}}},
]


def _lean_check(code: str, repo: str | Path) -> str:
    """Compile `code` against the warm REPL (the canonical `repl_compile.compile_probe_via_repl`, sorry-OK)
    and return a short diagnostics string. Falls back to the cold `_compile_probe` bool when the REPL is off."""
    code = (code or "").strip()
    if not code:
        return "lean_check: empty code."
    try:
        from ztare.formal.repl_compile import compile_probe_via_repl
        res = compile_probe_via_repl(code, repo, _LEAN_CHECK_TIMEOUT)
        if res is not None:
            ok, diag = res
            return ("OK — compiles clean." if ok else f"ERRORS:\n{(diag or '').strip()[:1500]}")
    except Exception as e:  # noqa: BLE001 — fall through to cold probe
        _ = e
    try:
        from ztare.gates.v33_preflight_risk_detector import _compile_probe
        ok = _compile_probe(code, Path(repo), "ApiLeafCheck", _LEAN_CHECK_TIMEOUT)
        return "OK — compiles clean." if ok is True else "ERRORS: did not compile (no diagnostics available)."
    except Exception as e:  # noqa: BLE001
        return f"lean_check unavailable: {str(e)[:160]}"


def _mathlib_search(query: str) -> str:
    """Loogle search — delegates to the canonical `agent_tools.loogle_search_text` (the ONE Loogle endpoint+format,
    shared with the CLI `_tool_search`). No re-rolled HTTP here."""
    query = (query or "").strip()
    if not query:
        return "mathlib_search: empty query."
    from ztare.leanmill.agent_tools import loogle_search_text
    return loogle_search_text(query, max_hits=12)


def _exec_tool(name: str, args: dict, repo: str | Path) -> str:
    if name == "lean_check":
        return _lean_check((args or {}).get("code", ""), repo)
    if name == "mathlib_search":
        return _mathlib_search((args or {}).get("query", ""))
    return f"unknown tool `{name}`."


# TASK-NEUTRAL system prompt — lives in the CANONICAL prompts registry (#49; never inline a prompt in a move
# module). NEUTRAL by design: `default_dispatch` serves proving AND formalizing AND planning, so it must NOT
# hardcode "you are a prover" (that forced kimi to try to PROVE a formalize request → tool-loop stall, fixed
# 2026-06-21). See `prompts.API_LEAF_SYSTEM`.
from ztare.leanmill.solver.prompts import API_LEAF_SYSTEM as _SYSTEM


def api_agentic_dispatch(prompt: str, *, runtime: str, repo: str | Path, timeout: int) -> str:
    """Run the function-calling tool loop for an API model (kimi/deepseek) and return its final TEXT answer
    (the fenced proof / GAP / STATEMENT-FALSE marker) — the SAME contract as the CLI leaf, so downstream
    extract+verify+govern is unchanged. Returns `INADMISSIBLE_DISPATCH` if the client/key is absent or the
    provider is dead (a dead instrument is NOT a real 'cannot prove')."""
    from ztare.leanmill.solver.agentic_leaf import INADMISSIBLE_DISPATCH
    client, model_id = _client_and_model(runtime)
    if client is None:
        print(f"[api-leaf] {runtime}: no client (missing key/SDK) → INADMISSIBLE", flush=True)
        return INADMISSIBLE_DISPATCH
    deadline = time.time() + max(30, int(timeout))
    messages = [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}]
    last_text = ""
    print(f"[api-leaf] {runtime}({model_id}) start (budget {int(timeout)}s)", flush=True)
    for rnd in range(_MAX_ROUNDS):
        if time.time() > deadline:
            print(f"[api-leaf] {runtime}: budget exhausted at round {rnd}", flush=True)
            break
        try:
            # NO temperature override — kimi-k2.6 rejects anything but 1 ("only 1 is allowed for this model",
            # caught in live validation 2026-06-21); each provider's default is fine for a tool-driven prover.
            resp = client.chat.completions.create(
                model=model_id, messages=messages, tools=_TOOL_SCHEMA, tool_choice="auto",
                timeout=min(180, max(30, int(deadline - time.time()))))
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            from ztare.leanmill.solver.agentic_leaf import _provider_dead  # quota/auth markers
            if _provider_dead(msg, 1):
                print(f"[api-leaf] {runtime}: PROVIDER-DEAD ({msg[:80]}) → INADMISSIBLE", flush=True)
                return INADMISSIBLE_DISPATCH
            print(f"[api-leaf] {runtime}: api error ({msg[:120]}) → stop", flush=True)
            break
        choice = resp.choices[0].message
        last_text = choice.content or last_text
        tool_calls = getattr(choice, "tool_calls", None) or []
        # Append the assistant turn (with any tool_calls) verbatim so the tool replies thread correctly.
        messages.append({"role": "assistant", "content": choice.content or "",
                         **({"tool_calls": [tc.model_dump() for tc in tool_calls]} if tool_calls else {})})
        if not tool_calls:
            print(f"[api-leaf] {runtime}: final answer at round {rnd} ({len(last_text)} chars)", flush=True)
            return last_text
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:  # noqa: BLE001
                args = {}
            result = _exec_tool(tc.function.name, args, repo)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result[:4000]})
    return last_text


def _selftest() -> None:
    """Hermetic loop-logic test (NO live API): a fake client returns one tool_call then a final answer; assert
    the loop EXECUTES the tool and returns the final text. Tool execution is stubbed (no live Lean/Loogle)."""
    class _FakeFn:
        def __init__(self, name, arguments):
            self.name, self.arguments = name, arguments

    class _FakeTC:
        def __init__(self, name, arguments):
            self.id, self.function = "tc1", _FakeFn(name, arguments)

        def model_dump(self):
            return {"id": self.id, "type": "function",
                    "function": {"name": self.function.name, "arguments": self.function.arguments}}

    class _FakeMsg:
        def __init__(self, content, tool_calls):
            self.content, self.tool_calls = content, tool_calls

    class _FakeResp:
        def __init__(self, msg):
            self.choices = [type("C", (), {"message": msg})()]

    seq = [_FakeResp(_FakeMsg("", [_FakeTC("mathlib_search", '{"query": "List.map"}')])),
           _FakeResp(_FakeMsg("```lean\ntheorem t : 1 + 1 = 2 := by norm_num\n```", None))]
    calls = {"n": 0}

    class _FakeClient:
        class chat:  # noqa: N801
            class completions:  # noqa: N801
                @staticmethod
                def create(**_kw):
                    r = seq[calls["n"]]
                    calls["n"] += 1
                    return r

    # PATCH globals() — NOT a re-import. Under `python -m`, this module is `__main__`, so
    # `import ztare...api_agentic_leaf as _self` would patch a SEPARATE module object while the
    # function under test reads `__main__`'s globals → the mock silently misses (the -m double-module
    # trap, memory 2026-06-14). globals() is the SAME namespace the function resolves names from.
    _g = globals()
    _orig_cam, _orig_exec = _g["_client_and_model"], _g["_exec_tool"]
    _g["_client_and_model"] = lambda rt: (_FakeClient(), "kimi-k2.6")
    _g["_exec_tool"] = lambda name, args, repo: f"TOOL[{name}]={args}"
    try:
        out = api_agentic_dispatch("prove 1+1=2", runtime="kimi", repo=".", timeout=60)
        assert "norm_num" in out and "theorem t" in out, out
        assert calls["n"] == 2, f"expected 2 rounds (tool then final), got {calls['n']}"
        assert is_api_runtime("kimi") and is_api_runtime("deepseek") and not is_api_runtime("codex")
        print("[api_agentic_leaf] SELFTEST PASS (loop executes tool then returns final proof)")
    finally:
        _g["_client_and_model"], _g["_exec_tool"] = _orig_cam, _orig_exec


if __name__ == "__main__":
    _selftest()
