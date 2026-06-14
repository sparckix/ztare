"""Bridge from the leanmill forecast_router POLICY to the canonical forecast POOL (the diverse-EXTERNAL-
forecaster prediction market in ``scripts/public/control/forecast/pool.py``).

WHY a bridge, not an import: the pool lives under ``scripts/`` and leanmill under ``src/``; ``src/`` must NOT
import ``scripts/`` (the scripts/README boundary). So this calls the pool CLI via SUBPROCESS. leanmill only
EMITS a micro forecast contract per target, READS the aggregate (the diverse forecasters' consensus P(close)),
and RESOLVES it against the KERNEL outcome — the pool's warm DAEMON (its configured diverse forecasters) does
the actual forecasting. This is "route the policy to the actual code", NOT a one-off forecaster: the cross-agent
diversity is the point, and the own-agent leaf vote is at most ONE configured pool forecaster (necessary, not
sufficient).

Best-effort + boundary-safe: ANY failure (pool absent, CLI error, no forecasts yet) degrades to ``None``/``False``
so the forecast_router simply falls back to its cheap signals — the bridge NEVER breaks the solve batch.

  python -m ztare.leanmill.solver.forecast_pool_bridge --selftest
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
_POOL = _REPO / "scripts/public/control/forecast/pool.py"
_AGG_DIR = _REPO / "analytics/public/forecast_pool/aggregates"
_CONTRACT_DIR = _REPO / "analytics/public/forecast_pool/contracts"

# The CONFIGURED diverse forecasters (the cross-agent diversity that is the pool's whole point). codex+claude
# personas by default; override to add deepseek/gemini/etc. Format: "runtime:agent_id:role,...".
DEFAULT_FORECASTERS = os.environ.get(
    "ZTARE_LEANMILL_POOL_FORECASTERS",
    "claude:claude_forecaster:forecasting_agent,codex:codex_forecaster:forecasting_agent")


def pool_available() -> bool:
    return _POOL.exists()


def contract_id_for(target: str) -> str:
    """A bounded, slug-safe contract id for a leanmill target (theorem name / row_id)."""
    slug = re.sub(r"[^A-Za-z0-9_]+", "_", str(target)).strip("_").lower() or "anon"
    return f"leanmill_close_{slug}"[:120]


def _run(args: "list[str]", timeout: int = 120) -> "subprocess.CompletedProcess | None":
    try:
        return subprocess.run([sys.executable, str(_POOL), *args], cwd=str(_REPO),
                              capture_output=True, text=True, timeout=timeout, check=False)
    except Exception:  # noqa: BLE001 — boundary-safe: never raise into the solver
        return None


def emit_micro_contract(target: str, goal: str, *, success_threshold: str = "kernel_ratified_closure",
                        horizon: str = "bounded_attempt", resolver: str = "leanmill_kernel",
                        emit_warm_wake: bool = True, forecasters: "str | None" = None,
                        timeout: int = 120) -> "str | None":
    """Emit a MICRO forecast contract ("will this target close?") and (default) publish the warm wake so the
    pool's diverse forecasters pick it up. Returns the contract_id, or None on any failure."""
    if not pool_available():
        return None
    cid = contract_id_for(target)
    question = ("Will the leanmill solver CLOSE this target with a KERNEL-verified, governance-ratified proof "
                "in one bounded attempt (no sorry/axiom/statement-swap)? Target: " + (str(goal) or target)[:600])
    args = ["init-contract", "--contract-id", cid, "--layer", "micro", "--task-type", "leanmill_close",
            "--question", question, "--objective-resolver", resolver,
            "--success-threshold", str(success_threshold), "--horizon", str(horizon),
            "--created-by", "leanmill:forecast_router", "--allow-overwrite"]
    if emit_warm_wake:
        args += ["--emit-warm-wake", "--warm-forecasters", forecasters or DEFAULT_FORECASTERS]
    r = _run(args, timeout=timeout)
    return cid if (r is not None and r.returncode == 0) else None


def read_aggregate(contract_id: str, *, refresh: bool = True, timeout: int = 60) -> "float | None":
    """The diverse forecasters' CONSENSUS P(close) for a contract (aggregate.p_success), or None when there is
    no aggregate yet (no forecasts have landed — the daemon hasn't run / isn't configured)."""
    if refresh and pool_available():
        _run(["aggregate", "--contract-id", contract_id], timeout=timeout)
    p = _AGG_DIR / f"{contract_id}.json"
    if not p.exists():
        return None
    try:
        agg = (json.loads(p.read_text(encoding="utf-8")) or {}).get("aggregate") or {}
    except Exception:  # noqa: BLE001
        return None
    v = agg.get("p_success")
    if isinstance(v, (int, float)):
        return max(0.0, min(1.0, float(v)))
    return None


def resolve_contract(contract_id: str, *, success: bool, compile_status: "str | None" = None,
                     sorry_delta: "int | None" = None, goal_delta: "int | None" = None,
                     error_type: "str | None" = None, note: str = "", voided: bool = False,
                     timeout: int = 60) -> bool:
    """Resolve a contract against the KERNEL outcome → the pool scores the forecasters (calibration compounds).
    The kernel outcome is GROUND TRUTH, so if the ORDERING guard trips (no independent forecaster bet landed
    yet), retry with the documented override. Best-effort (False on failure)."""
    if not pool_available():
        return False
    args = ["resolve", "--contract-id", contract_id]
    if voided:
        args += ["--voided"]
    else:
        args += ["--success-bool" if success else "--no-success-bool"]
        if compile_status is not None:
            args += ["--compile-status", str(compile_status)]
        if sorry_delta is not None:
            args += ["--sorry-delta", str(int(sorry_delta))]
        if goal_delta is not None:
            args += ["--goal-delta", str(int(goal_delta))]
        if error_type is not None:
            args += ["--error-type", str(error_type)]
    if note:
        args += ["--resolution-note", note]
    r = _run(args, timeout=timeout)
    if r is not None and r.returncode == 0:
        return True
    # ORDERING guard (resolve before a recognized independent forecaster bet) — the kernel outcome is ground
    # truth regardless, so override with a logged reason.
    if r is not None and "independent" in ((r.stderr or "") + (r.stdout or "")).lower():
        r2 = _run(args + ["--allow-no-independent-forecaster",
                          "--no-independent-forecaster-reason",
                          "leanmill kernel outcome is objective ground truth"], timeout=timeout)
        return bool(r2 is not None and r2.returncode == 0)
    return False


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    ok("pool CLI present", pool_available())
    ok("contract_id slug is bounded + safe",
       contract_id_for("Foo.bar baz/qux") == "leanmill_close_foo_bar_baz_qux" and
       len(contract_id_for("x" * 500)) <= 120)
    if pool_available():
        cid = emit_micro_contract("leanmill_bridge_selftest_target",
                                  "theorem t : 1 + 1 = 2 := by rfl", emit_warm_wake=False)
        ok("emit micro contract returns an id", cid is not None)
        if cid:
            ok("contract artifact written", (_CONTRACT_DIR / f"{cid}.json").exists())
            ok("read_aggregate is graceful with no forecasts (None)", read_aggregate(cid) is None)
            ok("resolve (void cleanup) succeeds", resolve_contract(cid, success=False, voided=True,
                                                                   note="selftest cleanup"))
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
