#!/usr/bin/env python3
"""tool_router.py — Layer-B kernel-grounded tool/action router.

GPT-5.5 verdict §3 Layer-B + §6: do NOT build a hammer; ROUTE to the
ones already in the pinned sandbox (Hammer/Duper/auto/aesop +
Mathlib's tactic zoo — all built into the sandbox oleans, zero new
deps). Given a live proof state, try tools in a band-graded order
(seed mined from the 110-trace governed ledger, NOT a trained policy),
cost-accounted (every probe counts), first governed-clean close wins.

Reuse, no fork: thin wrapper over PersistentLean.step(); the Lean
trust boundary and governance are unchanged. The router only chooses
ORDER; closure is still kernel-verified + governance-adjudicated by
the caller (two-scoreboard preserved — a close here is a CANDIDATE).

Machine-safety: this module is pure routing logic; the only heavy-Lean
part is PersistentLean.step(), which the caller gates (never run a
second heavy-Lean process concurrent with another — the crash rule).

HONEST: exact tactic syntax for `hammer`/`duper` is the standard
LeanHammer/Duper surface; if a name/arg differs at the pin it fails
cleanly (router just moves to the next tool — sound by construction,
never a false close). Confirmed at first live run (gated behind
hardened-30).
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    """Routable Lean tactic/tool metadata.

    This is intentionally declarative. Invocation, proof-state mutation,
    and governance remain owned by the existing REPL/gate callers.
    """

    tool_id: str
    tactic: str
    class_name: str
    prelude_imports: tuple[str, ...] = ()
    default_timeout_s: int = 30
    available_if_imported: bool = False


TOOL_CATALOG: dict[str, ToolSpec] = {
    "exact?": ToolSpec("exact?", "exact?", "suggestion", default_timeout_s=20),
    "apply?": ToolSpec("apply?", "apply?", "suggestion", default_timeout_s=20),
    "simp_all": ToolSpec("simp_all", "simp_all", "simplifier", default_timeout_s=20),
    "simp": ToolSpec("simp", "simp", "simplifier", default_timeout_s=20),
    "aesop": ToolSpec("aesop", "aesop", "automation", default_timeout_s=30),
    "duper": ToolSpec(
        "duper",
        "duper",
        "first_order_automation",
        prelude_imports=("import Duper",),
        default_timeout_s=45,
        available_if_imported=True,
    ),
    "hammer": ToolSpec(
        "hammer",
        "hammer",
        "hammer",
        prelude_imports=("import Hammer",),
        default_timeout_s=60,
        available_if_imported=True,
    ),
    "auto": ToolSpec(
        "auto",
        "auto",
        "automation",
        prelude_imports=("import Auto",),
        default_timeout_s=45,
        available_if_imported=True,
    ),
    "norm_num": ToolSpec("norm_num", "norm_num", "arithmetic", default_timeout_s=20),
    "omega": ToolSpec("omega", "omega", "arithmetic", default_timeout_s=20),
    "linarith": ToolSpec("linarith", "linarith", "arithmetic", default_timeout_s=20),
    "nlinarith": ToolSpec("nlinarith", "nlinarith", "arithmetic", default_timeout_s=25),
    "ring": ToolSpec("ring", "ring", "algebra", default_timeout_s=20),
    "ring_nf": ToolSpec("ring_nf", "ring_nf", "algebra", default_timeout_s=25),
    "field_simp": ToolSpec("field_simp", "field_simp", "algebra", default_timeout_s=30),
    "rfl": ToolSpec("rfl", "rfl", "cheap_closer", default_timeout_s=10),
    "assumption": ToolSpec("assumption", "assumption", "cheap_closer", default_timeout_s=10),
    "constructor": ToolSpec("constructor", "constructor", "decomposition", default_timeout_s=15),
    "intro": ToolSpec("intro", "intro _", "decomposition", default_timeout_s=15),
    "rcases_exists": ToolSpec(
        "rcases_exists",
        "rcases ‹_› with ⟨⟩",
        "decomposition",
        default_timeout_s=15,
    ),
}

# Band-graded seed (mined: april_trace_ledger — 2-4:93%, 5-15:~70%,
# 16+:33%). Cheap closers first on easy bands; strong automation early
# on mid/hard; decompose on hardest. Tools are tried in order until one
# closes (goals==[]) or the per-goal budget is spent.
ROUTING_SEED: dict[str, list[str]] = {
    "2-4": ["exact?", "apply?", "simp_all", "aesop", "omega", "norm_num",
            "hammer"],
    "5-8": ["hammer", "duper", "aesop", "exact?", "apply?", "simp_all",
            "nlinarith", "linarith", "norm_num"],
    "9-15": ["hammer", "duper", "aesop", "simp_all", "exact?", "apply?",
             "nlinarith", "field_simp"],
    "16+": ["aesop", "hammer", "duper", "intro", "constructor",
            "rcases_exists", "simp_all"],
}
DEFAULT_ORDER = ROUTING_SEED["5-8"]


def tool_spec(tool_id: str) -> ToolSpec:
    if tool_id not in TOOL_CATALOG:
        raise KeyError(f"unknown tool_id: {tool_id}")
    return TOOL_CATALOG[tool_id]


def prelude_imports(tool_ids: list[str]) -> list[str]:
    """Return deduped imports required by a tool route."""
    seen: set[str] = set()
    out: list[str] = []
    for tool_id in tool_ids:
        for imp in tool_spec(tool_id).prelude_imports:
            if imp not in seen:
                seen.add(imp)
                out.append(imp)
    return out


def route_plan(*, gold_n_steps: int | None = None) -> list[dict[str, Any]]:
    """Serializable route plan for orchestrator telemetry/contracts."""
    return [
        {
            "tool_id": spec.tool_id,
            "tactic": spec.tactic,
            "class_name": spec.class_name,
            "default_timeout_s": spec.default_timeout_s,
            "prelude_imports": list(spec.prelude_imports),
            "available_if_imported": spec.available_if_imported,
        }
        for spec in (tool_spec(t) for t in ROUTING_SEED.get(band_of(gold_n_steps), DEFAULT_ORDER))
    ]


def band_of(gold_n_steps: int | None) -> str:
    g = gold_n_steps or 0
    return ("2-4" if g <= 4 else "5-8" if g <= 8
            else "9-15" if g <= 15 else "16+")


def route(L: Any, ps: int, *, gold_n_steps: int | None = None,
          budget_s: float = 120.0, step_timeout: int = 30) -> dict:
    """Try seed-ordered tools on proof state `ps` via L.step(); first
    governed-clean close wins. Cost-accounted: returns probes spent.
    Returns {closed, tool, probes, secs, residual_tools_tried}.

    A close here is a CANDIDATE — caller must still kernel/governance
    adjudicate (two-scoreboard). Never fabricates a close: relies on
    L.step()'s fail-closed semantics (error/timeout ⇒ not closed)."""
    order = ROUTING_SEED.get(band_of(gold_n_steps), DEFAULT_ORDER)
    t0 = time.time()
    tried: list[str] = []
    for tool in order:
        if (time.time() - t0) >= budget_s:
            break
        spec = tool_spec(tool)
        r = L.step(ps, spec.tactic, timeout=min(step_timeout, spec.default_timeout_s))
        tried.append(tool)
        if not r.get("ok"):
            continue
        if r.get("closed"):
            return {"closed": True, "tool": tool,
                    "probes": len(tried), "tools_tried": tried,
                    "secs": round(time.time() - t0, 2),
                    "scoreboard": "CANDIDATE — caller must "
                    "governance-adjudicate (two-scoreboard)"}
        # tool made progress but did not close: record + keep going
        # (the residual feeds residual_to_lever via the caller).
    return {"closed": False, "tool": None, "probes": len(tried),
            "tools_tried": tried,
            "secs": round(time.time() - t0, 2),
            "residual": "no seed-ordered tool closed in budget — "
            "route to residual_to_lever (next_lever), do NOT mark "
            "impossible (non-treadmill)"}


if __name__ == "__main__":
    # Logic self-test with a mock REPL (machine-safe; NO Lean).
    class _Mock:
        def __init__(self, win_on):
            self.win_on, self.calls = win_on, []

        def step(self, ps, tac, timeout=30):
            self.calls.append(tac)
            ok = True
            return {"ok": ok, "closed": (tac == self.win_on)}

    for band, gs in (("2-4", 3), ("5-8", 6), ("9-15", 12), ("16+", 20)):
        m = _Mock(ROUTING_SEED[band][2])  # 3rd tool closes
        out = route(m, 0, gold_n_steps=gs, budget_s=999)
        assert out["closed"] and out["probes"] == 3, (band, out)
        plan = route_plan(gold_n_steps=gs)
        assert plan[0]["tool_id"] == ROUTING_SEED[band][0], (band, plan)
        print(f"[{band}] order={ROUTING_SEED[band][:4]}… "
              f"closed via '{out['tool']}' in {out['probes']} probes ✓")
    imports = prelude_imports(["exact?", "hammer", "duper", "aesop", "auto"])
    assert imports == ["import Hammer", "import Duper", "import Auto"], imports
    m = _Mock("NOTHING")
    out = route(m, 0, gold_n_steps=6, budget_s=999)
    assert not out["closed"] and "residual" in out
    print(f"[no-close] tried {len(out['tools_tried'])} tools → "
          f"residual (non-treadmill) ✓")
    print("tool_router logic self-test PASS (mock; live run gated "
          "behind hardened-30 / machine-safety)")
