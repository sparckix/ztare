"""Agentic LLM-leaf solver — the validated multi-step proof-search lever, productionized.

Empirically established 2026-06-02 (GP-246 seam): an agentic LLM leaf (codex/claude on the
operator's SUBSCRIPTION, iterating against `lake`) closes leaves that one-shot deterministic
search cannot — by INVENTING helper lemmas and decomposing — and reduces hard theorems to
proven scaffolding + a localized mathematical core. The deterministic vocabulary/router added
zero lift in one-shot mode; the lever is the agentic iterate-against-the-kernel loop.

This module codifies that loop as a reusable, SUBSTRATE-NEUTRAL primitive (works for any Lean
goal in any lake project — no APN/NS specifics). Three non-negotiable invariants, each a hard
lesson from this thread:

  1. CALIBRATION FIRST (fail-closed). Before any "could not prove" is admissible, BOTH
     instruments pass a positive control run through the SAME path the real work uses:
     the LLM provider must return a live trivial answer, AND the Lean substrate must pass
     substrate_liveness. A null from an un-calibrated instrument is INADMISSIBLE — that is
     how the dead REPL / dead-key / prompt-not-delivered episodes masqueraded as real
     negatives. (see substrate_liveness; feedback_negative_inadmissible_without_calibration)
  2. AGENT COMPOSES, KERNEL ARBITRATES. The agent's self-report ("it compiles") is never
     trusted. THIS module independently re-verifies: the proof compiles, no `sorry`, and
     `#print axioms ⊆ {propext, Classical.choice, Quot.sound}` (no sorryAx, no smuggled axiom).
  3. SUBSCRIPTION ONLY for OpenAI(codex)/Anthropic(claude). Never the metered API.

Dispatch + verify are injected callables (defaults provided) so the loop is unit-testable
offline and the substrate specifics live in the caller, not here.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from ztare.gates.lean_compile_primitives import AXIOM_ALLOWLIST  # F3: single source of truth (was a local literal)
_AXIOM_LINE = re.compile(r"depends on axioms:\s*\[([^\]]*)\]")


# ── independent kernel gate (agent self-report is never trusted) ─────────────
def verify_lean_proof(probe_path: str | Path, target: str, *, lake_bin: str,
                      project_dir: str | Path, timeout: int = 250,
                      retries: int = 1) -> tuple[bool, str]:
    """Compile the probe via `lake env lean` and gate on #print axioms. Returns
    (closed, reason). closed iff: compiles, no `sorry`, axioms ⊆ allowlist.

    Hardened against TRANSIENTS (the verify itself must not produce a false negative): the
    agent runs its OWN concurrent `lake` builds during the agentic dispatch, which can race
    a verify and surface a spurious error/timeout. So a non-clean first result is RE-RUN on a
    fresh read before being trusted — a real error reproduces; a transient/race does not."""
    import os
    p = Path(probe_path)
    txt = p.read_text(encoding="utf-8", errors="replace")
    txt2 = ensure_import_header(txt)   # warm/verify PARITY (RCA 2026-06-12) — see helper
    if txt2 != txt:
        print(f"[verify] prepended `import Mathlib` to import-less probe {p.name} "
              f"(warm-checker had Mathlib pre-loaded; standalone verify needs the header)", flush=True)
        txt = txt2
    if f"#print axioms {target}" not in txt:
        txt = txt + f"\n#print axioms {target}\n"
    p.write_text(txt, encoding="utf-8")
    # ABSOLUTE lean arg: cwd=project_dir, so a repo-relative probe path would DOUBLE
    # (project_dir/project_dir/probe → file-not-found → spurious 'error'). abspath fixes it.
    lean_arg = os.path.abspath(str(p))
    last = (False, "not_run")
    for attempt in range(retries + 1):
        try:
            r = subprocess.run([str(lake_bin), "env", "lean", lean_arg], cwd=str(project_dir),
                               text=True, capture_output=True, timeout=timeout)
            last = parse_verify_output((r.stdout or "") + (r.stderr or ""), target=target)
        except subprocess.TimeoutExpired:
            last = (False, "verify_timeout(transient?)")
        if last[0]:           # clean → trust immediately
            return last
        # not clean: if more attempts remain, re-run (defeats a build-race false negative)
    return last


def parse_verify_output(out: str, target: "str | None" = None) -> tuple[bool, str]:
    """Pure parser (unit-testable): classify a `lake env lean` + #print-axioms transcript.

    AXIOM CHECK — HARDENED (bug-hunt 2026-06-10, HIGH). A probe can carry MULTIPLE `#print axioms` directives
    (the agent has workspace-write and may add a clean helper's directive), so the TARGET's axiom verdict must
    be inspected SPECIFICALLY. The prior global `"does not depend on any axioms" in out` short-circuit + the
    first-`_AXIOM_LINE` scan let a CLEAN HELPER line MASK the target's real axioms — laundering e.g.
    `native_decide`'s `Lean.ofReduceBool` (a trust-the-compiler axiom) as axiom-clean. With `target` known we
    key on the `'target' …` line; without it we scan EVERY axiom line and reject if ANY carries a
    non-allowlisted axiom (no clean-line short-circuit). Fail-CLOSED: a target whose axiom line is absent is
    rejected."""
    low = out.lower()
    if "error" in low:
        return False, "compile_error"
    if "sorry" in low:  # 'declaration uses sorry' / sorryAx
        return False, "uses_sorry"
    if target:
        # Lean keys #print axioms by name: `'target' does not depend...` | `'target' depends on axioms: [...]`
        # (allow an optional `Namespace.` prefix on the echoed name).
        _t = r"'(?:[\w.']*\.)?" + re.escape(target) + r"'\s+"
        if re.search(_t + r"does not depend on any axioms", out):
            return True, "clean(no axioms)"
        mt = re.search(_t + r"depends on axioms:\s*\[([^\]]*)\]", out)
        if not mt:
            return False, "no_axiom_line_for_target"
        ax = {a.strip() for a in mt.group(1).split(",") if a.strip()}
        return (ax.issubset(AXIOM_ALLOWLIST),
                "clean " + str(sorted(ax)) if ax.issubset(AXIOM_ALLOWLIST)
                else "BAD_AXIOMS " + str(sorted(ax - AXIOM_ALLOWLIST)))
    # target unknown (legacy / pure-parser callers): scan EVERY axiom line; ANY non-allowlisted axiom REJECTS.
    bad: "set[str]" = set()
    saw_line = False
    for m in _AXIOM_LINE.finditer(out):
        saw_line = True
        bad |= ({a.strip() for a in m.group(1).split(",") if a.strip()} - AXIOM_ALLOWLIST)
    if bad:
        return False, "BAD_AXIOMS " + str(sorted(bad))
    if saw_line or "does not depend on any axioms" in out:
        return True, "clean(no axioms)"
    return False, "no_axiom_line"


# ── dispatch (subscription CLI only) ─────────────────────────────────────────
def leaf_runtime() -> str:
    """The agentic-leaf provider runtime (a SUBSCRIPTION agent — codex/claude CLI — NOT the metered API).
    DELEGATES to the canonical `common.subscription_agent_runtime.default_subscription_runtime` (which owns
    the supported-set + validation) scoped to the leaf's env var `ZTARE_LEANMILL_LEAF_RUNTIME` — does NOT
    re-implement runtime selection (operator request 2026-06-09). The single switch for the solver leaf."""
    from ztare.common.subscription_agent_runtime import default_subscription_runtime
    return default_subscription_runtime("ZTARE_LEANMILL_LEAF_RUNTIME")


def leaf_provider_order() -> "tuple[str, str]":
    """The solver leaf's provider TRY-ORDER: the configured leaf runtime first, the other second (a diversity
    shot + failover headroom). One env switch (ZTARE_LEANMILL_LEAF_RUNTIME / the global
    ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME) thus puts the LIVE provider first and the dead one second, instead of
    wasting the first attempt on an exhausted provider. Default-codex (parity) until a switch is set."""
    primary = leaf_runtime()
    return (primary, _alternate_runtime(primary))


# A provider-dead signature (quota/auth) is a DEAD CARRIER — its output is INADMISSIBLE (the operator's
# dead-instrument rule), NOT a real "the agent couldn't do it". Diagnosed 2026-06-10: codex returned
# `ERROR: You've hit your usage limit` in 2s/exit-1 for every formalize, turning a RUNG-A run into a 0/5
# dead-instrument artifact. codex and claude have SEPARATE subscription quotas, so failover keeps the run alive.
# A sentinel returned when EVERY subscription is dead — the dispatch is INADMISSIBLE (a dead instrument), so the
# caller must deposit/learn NOTHING and must NOT read it as a real negative (faithful=False / open). Distinct
# from "" (a real empty answer). The formalizer + firewall detect this and mark the outcome inadmissible (#89).
INADMISSIBLE_DISPATCH = "__LEANMILL_INADMISSIBLE_PROVIDER_DEAD__"

_PROVIDER_DEAD_MARKERS = (
    "hit your usage limit", "usage limit", "rate limit", "rate_limit", "quota exceeded", "quota",
    "upgrade to plus", "too many requests", "not authenticated", "authentication failed",
    "please log in", "login required", "session expired",
)


def _provider_dead(out: str, returncode: int) -> bool:
    """A quota/auth failure (non-zero exit AND a dead-carrier marker in the output). NOT triggered on a clean
    run (rc==0) so a healthy provider never fails over — parity when both subscriptions are live."""
    if returncode == 0:
        return False
    low = (out or "").lower()
    return any(m in low for m in _PROVIDER_DEAD_MARKERS)


def _alternate_runtime(rt: str) -> str:
    return "claude" if rt == "codex" else "codex"


# ── WARM AGENTS — via the SHARED durable session manager (the residual-family factory's proven pattern) ──────
# Hold a subscription session per (runtime, lake-repo) and RESUME it so the fungible leaf keeps the lemma-family
# context across the formalize→plan→solve dispatches (faster; a timed-out dispatch resumes instead of cold-
# restarting), and so planning + solving share ONE warm agent. This was a NON-DURABLE in-memory hand-rolled copy
# (#96, lost on process exit) sitting next to the SAME logic the factory worker (agent_repair_worker) already ran
# in production (warm default-ON) — that duplication was the Frankenstein. Now both go through
# `common.subscription_agent_runtime`'s durable manager: sessions persist to DISK (survive process / queue-item
# boundaries), rotate when stale (warm_max_tasks / warm_max_age_s), and the claude session-not-found recovery
# self-heals. A warm session is a PERFORMANCE CACHE of the fungible leaf, NOT a persistent identity (fungibility
# preserved). Default-ON to match the worker; ZTARE_LEANMILL_WARM_AGENTS=0 reverts to cold (the known-good path),
# ZTARE_LEANMILL_SESSION_DIR overrides the store. NOTE: warm RESUME is not yet live-validated for the leaf path —
# the self-heal (a failed resume → rotate + retry COLD once) guarantees correctness regardless of resume support.
def _warm_agents_on() -> bool:
    return os.environ.get("ZTARE_LEANMILL_WARM_AGENTS", "1") != "0"   # default-ON (matches the production worker)


def _warm_session_dir() -> "Path":
    # ABSOLUTE: the dispatch cwd is the lake project, NOT the ztare repo — anchor to the repo root so every leaf
    # dispatch (any lake project) shares the canonical session store with the factory worker.
    root = Path(__file__).resolve().parents[4]   # …/src/ztare/leanmill/solver/agentic_leaf.py → repo root
    return Path(os.environ.get("ZTARE_LEANMILL_SESSION_DIR")
                or str(root / "analytics/public/leanmill/dashboard_data/subscription_agent_sessions"))


def _leaf_agent_id(repo: "str | Path") -> str:
    # per lake-repo (a warm conversation never bleeds across substrates); shared across the leaf's
    # formalize/plan/solve dispatches IN that repo ⇒ one agent for planning+solving.
    return f"agentic_leaf_{Path(str(repo)).name}"


def _dispatch_once(prompt: str, runtime: str, repo: "str | Path", timeout: int,
                   agent_tag: str = "") -> "tuple[str, int]":
    from ztare.common.subscription_agent_runtime import (
        run_subscription_agent_with_recovery,
        get_or_create_warm_session,
        persist_warm_session,
        warm_session_recovery_callbacks,
    )
    import time as _t
    _t0 = _t.time()
    if timeout is None:   # defense-in-depth (2026-06-13): a None timeout from any caller must NOT crash the
        from ztare.common.timeouts import timeout_s as _ts_d   # run on int(None); default to the dispatch budget
        timeout = _ts_d("agent_dispatch")
    enabled = _warm_agents_on()
    sess_dir = _warm_session_dir()
    # `agent_tag` (#117 parallel sampling): a non-empty tag keys its OWN durable session BESIDE the
    # repo-scoped one, so CONCURRENT dispatches never collide on a single session resume (and tagged
    # slots stay warm across rounds — same economics, no shared-context correlation). A PARAMETER, not
    # an env var, by design: env is process-global and therefore not thread-safe under concurrency.
    agent_id = _leaf_agent_id(repo) + (f"__{agent_tag}" if agent_tag else "")
    sess = get_or_create_warm_session(sess_dir, runtime=runtime, agent_id=agent_id, enabled=enabled)
    inval, repl = warm_session_recovery_callbacks(sess_dir, runtime=runtime, agent_id=agent_id)
    resumed = bool(sess and not sess.get("is_new"))
    _mode = (", warm-resume" if resumed else ", warm-new" if sess else ", cold")
    print(f"[dispatch] {runtime} start (budget {int(timeout)}s{_mode})", flush=True)

    def _run(state):
        return run_subscription_agent_with_recovery(
            runtime=runtime, prompt=prompt, agent_id=agent_id,
            repo=repo, session_state=state, timeout_seconds=timeout,
            codex_sandbox="workspace-write", default_codex_model="account-default",
            invalidate_session=inval, create_replacement_session=repl)

    run = _run(sess)
    rc = run.result.returncode
    if resumed and rc != 0 and rc != 124:
        # a RESUME genuinely FAILED (NOT a timeout) — almost always a stale/unsupported session, NOT a provider
        # death. Durably ROTATE (next dispatch mints a fresh session, not a broken resume) and retry COLD once so
        # the dispatch still lands. Only a COLD failure is a real provider issue → reaches _provider_dead.
        # rc=124 is a TIMEOUT (the agent needed > budget), NOT a session break ⇒ EXCLUDED: rotating a GOOD warm
        # session + a second cold retry (which would also time out on the same hard goal) just burns 2× the
        # budget — observed live on a hard P1 sub-lemma (2026-06-11). On a timeout we KEEP the warm session
        # (resume worked) and return, letting the cascade move on within budget.
        inval(f"warm_resume_failed_rc_{rc}")
        print(f"[dispatch] {runtime} warm-resume failed (rc={rc}) → cold-fallback + session rotated", flush=True)
        run = _run(None)
        rc = run.result.returncode
    elif sess is not None and rc == 0:
        persist_warm_session(sess_dir, runtime=runtime, agent_id=agent_id, session_state=run.final_session_state)
    out = (run.result.stdout or "") + "\n" + (run.result.stderr or "")
    print(f"[dispatch] {runtime} done in {int(_t.time() - _t0)}s (exit {rc})", flush=True)
    return out, rc


def default_dispatch(prompt: str, *, runtime: str = "", repo: str | Path, timeout: int,
                     agent_tag: str = "") -> str:
    """Agentic dispatch on the operator's SUBSCRIPTION (codex/claude) via the shared
    `common/subscription_agent_runtime` wrapper — NOT a bespoke subprocess, and never the metered API.
    workspace-write so the agent can edit the probe + run lake; `repo` is the cwd (the lake project).
    `runtime=""` ⇒ `leaf_runtime()`. PROVIDER FAILOVER: if the chosen subscription is quota/auth-dead, retry
    once on the ALTERNATE subscription (separate quota) so one exhausted provider doesn't silently zero a run.
    A flushed HEARTBEAT brackets every dispatch (the 'too nested to troubleshoot' fix). `agent_tag` keys a
    per-tag durable session (concurrency-safe parallel sampling, #117); "" = the shared repo session."""
    runtime = runtime or leaf_runtime()
    out, rc = _dispatch_once(prompt, runtime, repo, timeout, agent_tag)
    if _provider_dead(out, rc):
        alt = _alternate_runtime(runtime)
        print(f"[dispatch] {runtime} PROVIDER-DEAD (quota/auth) → failover to {alt}", flush=True)
        out2, rc2 = _dispatch_once(prompt, alt, repo, timeout, agent_tag)
        if not _provider_dead(out2, rc2):
            return out2
        print("[dispatch] BOTH subscriptions dead (quota/auth) — INADMISSIBLE, not a real negative", flush=True)
        return INADMISSIBLE_DISPATCH
    return out


def provider_live(runtime: str, repo: str | Path, dispatch: Callable, timeout: int = 90) -> tuple[bool, str]:
    """Positive control: does the provider return a live trivial answer? (never read a
    'could not prove' off a dead/hung provider — the dead-codex lesson)."""
    try:
        out = dispatch("Reply with exactly the word: ALIVE", runtime=runtime, repo=repo, timeout=timeout)
        return ("ALIVE" in (out or "").upper()), (out or "")[:80]
    except Exception as e:
        return False, f"dispatch error: {str(e)[:80]}"


# ── the loop ─────────────────────────────────────────────────────────────────
@dataclass
class LeafResult:
    closed: bool
    target: str
    goal: str
    reason: str
    rounds: int = 0
    decomposed: bool = False
    calibration: dict = field(default_factory=dict)
    inadmissible: bool = False   # True ⇒ a negative here is NOT real (instrument not calibrated)
    timeout_retried: bool = False  # True ⇒ an attempt ran out of time and was retried with more budget
    gap: str = ""                # the leaf's own honest-gap diagnosis (`-- GAP: …`) — the exact missing
    #                              lemma(s) it could not prove; the most useful signal a non-closure gives
    statement_false: str = ""    # the leaf's REFUTATION (`-- STATEMENT-FALSE: …`) — the TARGET is mis-formalized
    #                              (counterexample + the corrected hypothesis); the SOFT reformulation trigger


# Timeout-aware retry (adaptive budget, 2026-06-03): when an agent dispatch RUNS OUT OF TIME
# (under-budget, not a genuine "cannot prove"), retry ONCE with this budget multiplier. This is
# the non-naive form of adaptive budget — give an out-of-time attempt MORE time rather than read
# it as a real negative. Non-iatrogenic: only fires on a DETECTED timeout; the kernel verify
# still gates (no false closure); a genuine failure (no timeout marker) is NOT retried.
import os as _os_arf  # noqa: E402
# Tunable so a research campaign can grant the agent MORE adaptive headroom when it signals (by timing out)
# that it was making progress and needed more — agency upstream of the soundness boundary (a budget can only
# let it SEARCH more; the kernel re-verifies every closure, so a larger retry can never launder one). Bounded:
# the whole-move deadline still caps the total, so this is bounded free-will, not unbounded burn. Default 1.6
# = byte-parity. The campaign knob: `ZTARE_LEANMILL_TIMEOUT_RETRY_FACTOR` (e.g. 2.5 to fund the crux leaf).
def _timeout_retry_factor() -> float:
    try:
        return max(1.0, float(_os_arf.environ.get("ZTARE_LEANMILL_TIMEOUT_RETRY_FACTOR", "1.6")))
    except (TypeError, ValueError):
        return 1.6
TIMEOUT_RETRY_FACTOR = 1.6   # module-level default retained for back-compat / direct readers
_MIN_DISPATCH_S = 30   # don't start a leaf dispatch with less than this budget left (a too-short call
#                        can't do anything useful) — the floor for the whole-move deadline below
_TIMEOUT_MARKERS = ("timed out after", "timeoutexpired")


def _dispatch_timed_out(out: str) -> bool:
    low = (out or "").lower()
    return any(m in low for m in _TIMEOUT_MARKERS)


def _extract_gap(probe: "str | Path") -> str:
    """Pull the leaf's honest-gap diagnosis (`-- GAP: …`) out of the probe — the leaf telling us the
    EXACT lemma(s) it needs but could not prove. Discarding this wastes the most useful signal an honest
    non-closure produces; the caller surfaces it (→ residual_to_lever / a targeted conjecture / the
    decompose retry below)."""
    try:
        txt = Path(probe).read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""
    gaps = re.findall(r"--\s*GAP:\s*(.+)", txt)
    return " | ".join(g.strip() for g in gaps if g.strip())[:600]


def _extract_statement_false(probe: "str | Path") -> str:
    """Pull the leaf's REFUTATION (`-- STATEMENT-FALSE: …`) out of the probe — the leaf saying the TARGET as
    stated is FALSE (mis-formalized), with the counterexample + the corrected hypothesis. Distinct from a GAP
    (a missing lemma of a TRUE statement): this is the SOFT trigger for the governed reformulation re-entry —
    the apparatus re-formalizes the intended statement, firewall-gated, and re-attempts (it can never launder)."""
    try:
        txt = Path(probe).read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""
    hits = re.findall(r"--\s*STATEMENT-FALSE:\s*(.+)", txt)
    return " | ".join(h.strip() for h in hits if h.strip())[:600]


def scan_probes_for_statement_false(scratch_dir: "str | Path", *, limit: int = 16) -> str:
    """Scan a scratch dir's probes (FRESHEST first) for the leaf's `-- STATEMENT-FALSE:` refutation — the SOFT
    reformulation trigger. This is solve_adhoc's SINGLE capture point (vs threading the signal through every
    `results.append` branch). Returns the freshest marker text, or "". Sound-neutral: a stale hit only triggers
    a BOUNDED, firewall-gated reformulation (it re-checks faithfulness vs the original NL — it can never
    launder), so robustness-of-which-probe is an efficiency concern, not a soundness one."""
    try:
        cands = sorted(Path(scratch_dir).rglob("*.lean"), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:  # noqa: BLE001
        return ""
    for pf in cands[:limit]:
        sf = _extract_statement_false(pf)
        if sf:
            return sf
    return ""


def _leaf_prompt(target: str, goal: str, probe_name: str, *, mode: str = "direct",
                 prior_gap: str = "") -> str:
    """The leaf is a FRONTIER research mathematician (codex-5.5-xhigh / opus-4.8 class) — prompt it like
    one, not like a compile-bot. The legacy prompt was iatrogenic three ways, and it is what INDUCED the
    instance-shadowing gaming on P1: (1) it optimized for COMPILATION, not truth — a stuck leaf then games
    to make it compile; (2) it asserted 'the needed definitions are already in the file', FALSE on an open
    target, pushing 'force a way'; (3) it forbade only sorry/axioms — NOT the laundering vectors — so the
    cheat was implicitly allowed under compile-pressure. It also must NOT blindfold the leaf from real
    mathematics. This prompt: give it room, the real objective (a GENUINE proof; the compile only CHECKS),
    an HONEST-GAP exit, and a precise prohibition on LAUNDERING (not on mathematics).
    `ZTARE_LEANMILL_LEGACY_PROMPT=1` reverts to the old narrow prompt (for the A/B). PROMPT TEXT lives in the
    canonical `leanmill/solver/prompts.py` (#49) — this only assembles the pieces + appends the runtime-specific
    affordances (the agent-callable tool block + the warm-REPL socket hint)."""
    from ztare.leanmill.solver import prompts as _p
    if os.environ.get("ZTARE_LEANMILL_LEGACY_PROMPT") == "1":
        tmpl = _p.LEAF_LEGACY_DECOMPOSE_PROMPT if mode == "decompose" else _p.LEAF_LEGACY_DIRECT_PROMPT
        return tmpl.format(target=target, goal=goal, probe=probe_name)
    common = _p.LEAF_SOLVE_COMMON
    # AGENT-ORCHESTRATED TOOL-USE: advertise the exogenous-compute helpers (SymPy / z3 / Isabelle) as tools the
    # agent CALLS itself (autonomy), NOT a hand-wired router; the kernel still re-verifies. Appended at RUNTIME
    # (live-gated), so it stays in render_tool_block, not the static template.
    try:
        from ztare.leanmill.solver.move_cards import render_tool_block
        common += render_tool_block()
    except Exception:  # noqa: BLE001 — tool advertising is additive; never break the prompt
        pass
    # WARM COMPILE: if the harness started the warm REPL (ZTARE_LEANMILL_LEAN_SOCKET — a non-discoverable
    # affordance, so it IS told), point the agent at it (~0.1s) instead of cold `lake env lean` (~30-90s/iter).
    _lean_sock = os.environ.get("ZTARE_LEANMILL_LEAN_SOCKET")
    if _lean_sock:
        common += _p.LEAF_WARMCHECK_HINT.format(socket=_lean_sock, probe=probe_name)
    if mode == "decompose":
        # RETRY FEEDBACK: hand back the direct attempt's honest-gap diagnosis so the decomposition targets
        # exactly what the leaf already identified as missing (not a blind retry).
        gap_fb = _p.LEAF_DECOMPOSE_GAP_FB.format(gap=prior_gap) if prior_gap else ""
        return _p.LEAF_DECOMPOSE_PREFIX.format(target=target, goal=goal, probe=probe_name, gap_fb=gap_fb) + common
    return _p.LEAF_DIRECT_PREFIX.format(target=target, goal=goal, probe=probe_name) + common


def ensure_import_header(text: str, *, header: str = "import Mathlib") -> str:
    """Guarantee a Lean file is SELF-CONTAINED for a STANDALONE compile — the permanent fix for the
    warm-vs-verify import asymmetry (RCA 2026-06-12). The agent iterates against the WARM checker
    (`lean_check_server` / `PersistentLean` run in a REPL session with Mathlib PRE-LOADED), so its final probe
    frequently OMITS `import Mathlib` — harmless in the warm session, but a STANDALONE `lake env lean` +
    `#print axioms` verify then fails to PARSE and FALSE-`compile_error`s a kernel-valid proof. (Observed: a
    complete 466-line RatFunc-antiderivative proof — sorry-free, axioms ⊆ allowlist once the header is present —
    was recorded `compile_error` and the closure was discarded.) Prepend the substrate header iff NO `import`
    line is present. Idempotent (any existing `import` ⇒ untouched). SOUND: the header is a pure SUPERSET — it
    can never make an unsound proof pass (the kernel + `#print axioms` audit still gate); it only stops a VALID
    proof from being thrown away. Use at EVERY standalone-compile choke point so the bug cannot recur."""
    if re.search(r"(?m)^\s*import\s+\w", text or ""):
        return text
    return f"{header}\n\n{text}"


def _probe_text(defs: str, goal: str, target: str) -> str:
    # Self-contained from creation (warm/verify parity) — `ensure_import_header` is idempotent if `defs` already imports.
    return ensure_import_header(f"{defs.rstrip()}\n\ntheorem {target} : {goal} := by\n  sorry\n")


def _dump_transcript(target: str, tag: str, out: str) -> None:
    """Persist the agent's RAW dispatch transcript (its CoT + every shell command it ran) so we can SEE what
    it actually did. DEFAULT-ON 2026-06-12 (=0 reverts; a path value redirects the dir): v3/v4 launched
    without it, so the iatrogenic-loop audit (was the agent failing, or the harness mis-using its output?)
    was only possible because an EARLIER run had it on by luck. Observability is a sound knob — a few KB-MB
    in /tmp per dispatch buys the ability to audit every burn; never run a long campaign blind again."""
    d = os.environ.get("ZTARE_LEANMILL_DEBUG_TRANSCRIPT", "1")
    if not d or d == "0":
        return
    try:
        base = Path("/tmp/leanmill_transcripts") if d == "1" else Path(d)
        _rt = re.sub(r"[^A-Za-z0-9_.-]+", "_", os.environ.get("ZTARE_SOLVER_RUN_TAG", "") or "untagged")
        base = base / _rt   # per-run subdir — same-named targets across runs no longer overwrite the evidence
        base.mkdir(parents=True, exist_ok=True)
        (base / f"{target}_{tag}.txt").write_text(out or "", encoding="utf-8")
    except Exception:  # noqa: BLE001 — debug capture must never break the solve
        pass


PROBE_SUBDIR = ".solver_scratch"   # generated probes live HERE, not the lake project ROOT — keeps the working
                                   # dir clean (the operator: probes "shouldnt be generated there"). Still INSIDE
                                   # the project so `lake env lean` resolves the env (mirrors the warm-leaf path,
                                   # which already writes .solver_scratch/<row_id>/target.lean). Gitignored.


def probe_dir(project_dir: "str | Path") -> Path:
    """The scratch dir generated probes are written to (created on demand). Shared by the writer (solve_leaf)
    and every readback site (solver_core RobustProbe/AdHoc readback + the governance-organ glob) so the write
    path and the read path can never drift — a drift would silently skip governance (the 2026-06-04 cold-route
    gap). Returns `<project_dir>/.solver_scratch`."""
    d = Path(project_dir) / PROBE_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def solve_leaf(
    goal: str,
    *,
    defs: str,
    project_dir: str | Path,
    repo: str | Path,
    lake_bin: str,
    probe_name: str = "AgenticLeafProbe.lean",
    target: str = "leaf",
    runtime: str = "codex",
    timeout: int = 600,
    decompose: bool = True,
    dispatch: Callable = default_dispatch,
    verify: Optional[Callable] = None,
    substrate_calibrate: Optional[Callable] = None,
) -> LeafResult:
    """Solve one Lean leaf with the agentic loop. SUBSTRATE-NEUTRAL: pass the project's `defs`
    (in-scope declarations, no imports — base env carries Mathlib), `project_dir`, `lake_bin`.

    Calibration-first & fail-closed: if the provider or substrate is not live, returns
    inadmissible=True (NOT closed=False-as-signal). Agent composes; this fn verifies."""
    project_dir, repo = Path(project_dir), Path(repo)
    res = LeafResult(closed=False, target=target, goal=goal, reason="")

    # 1) CALIBRATION FIRST — both instruments, fail-closed.
    live, sample = provider_live(runtime, repo, dispatch)
    res.calibration["provider"] = {"runtime": runtime, "live": live, "sample": sample}
    if not live:
        res.reason = f"provider {runtime} not live ({sample}) — INADMISSIBLE"
        res.inadmissible = True
        return res
    if substrate_calibrate is not None:
        try:
            res.calibration["substrate"] = substrate_calibrate()
        except Exception as e:
            res.reason = f"substrate calibration failed: {str(e)[:120]} — INADMISSIBLE"
            res.inadmissible = True
            return res

    # WARM LEAN for the AGENT (2026-06-10): start/reuse a warm REPL server + advertise its socket (read by
    # `_leaf_prompt`) so the agent's iterate-loop compiles ~0.1s (warm) instead of ~30-90s (cold `lake env lean`)
    # — the interactive-starvation foot-gun. Default-on; ZTARE_LEANMILL_LEAN_WARM=0 reverts to cold lake (the A/B
    # baseline). Graceful: a None socket ⇒ nothing advertised ⇒ the prompt keeps cold lake. Set BEFORE the
    # dispatch so the CLI-agent subprocess inherits ZTARE_LEANMILL_LEAN_SOCKET.
    if os.environ.get("ZTARE_LEANMILL_LEAN_WARM", "1") != "0":
        try:
            from ztare.formal.lean_check_server import ensure_server as _ensure_lean
            _sock = _ensure_lean(str(project_dir))
            if _sock:
                os.environ["ZTARE_LEANMILL_LEAN_SOCKET"] = _sock
        except Exception:  # noqa: BLE001 — warm-Lean is an optimization; never block the solve
            pass

    probe = probe_dir(project_dir) / probe_name
    # The agent's cwd is `project_dir` (the lake root), so it must reference the probe by its path RELATIVE to
    # that root — `.solver_scratch/<probe_name>` — not the bare basename (which would make it edit/compile a
    # NEW file at the root, re-cluttering). Mirrors the warm-leaf prompt, which hands the agent the explicit path.
    probe_ref = f"{PROBE_SUBDIR}/{probe_name}"
    if verify is None:
        from ztare.common.timeouts import timeout_s   # central budget factory (byte-parity: leaf_verify defaults to the prior 250)
        verify = lambda: verify_lean_proof(probe, target, lake_bin=lake_bin,
                                           project_dir=project_dir, timeout=timeout_s("leaf_verify"))

    # WHOLE-attempt deadline (2026-06-07 — the warm-domination fix). `timeout` is the TOTAL budget for
    # this solve_leaf; the direct + timeout-retry + decompose + decompose-retry SHARE it. Before this, each
    # phase got the FULL `timeout`, so one solve_leaf could run direct[t] + decompose[t] + retries ≈ 4·t —
    # and `solve_robust` then multiplied that by N providers (warm ran 1250s under a 150s cap, starving the
    # whole move space). Each dispatch now gets the REMAINING budget; a phase is skipped once it's spent.
    _dl = time.time() + max(_MIN_DISPATCH_S, timeout)

    def _budget() -> int:
        return max(0, int(_dl - time.time()))

    # 2) direct agentic attempt
    probe.write_text(_probe_text(defs, goal, target), encoding="utf-8")
    direct = _leaf_prompt(target, goal, probe_ref, mode="direct")
    out = dispatch(direct, runtime=runtime, repo=repo, timeout=max(_MIN_DISPATCH_S, _budget()))
    _dump_transcript(target, "direct", out)
    res.rounds = 1
    ok, why = verify()
    # Timeout-aware retry: an OPEN result whose dispatch RAN OUT OF TIME is under-budget, not a real
    # negative — retry with the budget that REMAINS (capped at the retry factor), only if any is left.
    if not ok and _dispatch_timed_out(out) and _budget() >= _MIN_DISPATCH_S:
        dispatch(direct, runtime=runtime, repo=repo,
                 timeout=min(int(timeout * _timeout_retry_factor()), _budget()))
        res.rounds += 1
        res.timeout_retried = True
        ok, why = verify()
    res.reason = why
    if ok:
        res.closed = True
        return res
    res.gap = _extract_gap(probe)   # capture the leaf's own diagnosis from the direct attempt
    res.statement_false = _extract_statement_false(probe)   # SOFT reformulation trigger (target mis-formalized)

    # 3) decomposition fallback (the conjecture-DAG move): ask for helper lemmas, reassemble — only if
    #    budget remains (else the direct attempt already consumed this move's time). RETRY FEEDBACK: hand
    #    the direct attempt's honest-gap diagnosis to the decomposition so it targets what the leaf found
    #    missing (not a blind retry).
    if decompose and _budget() >= _MIN_DISPATCH_S:
        decomp = _leaf_prompt(target, goal, probe_ref, mode="decompose", prior_gap=res.gap)
        out = dispatch(decomp, runtime=runtime, repo=repo, timeout=_budget())
        _dump_transcript(target, "decompose", out)
        res.rounds += 1
        res.decomposed = True
        ok, why = verify()
        if not ok and _dispatch_timed_out(out) and _budget() >= _MIN_DISPATCH_S:
            dispatch(decomp, runtime=runtime, repo=repo,
                     timeout=min(int(timeout * TIMEOUT_RETRY_FACTOR), _budget()))
            res.rounds += 1
            res.timeout_retried = True
            ok, why = verify()
        res.reason = why
        res.closed = ok
        if not ok:
            res.gap = _extract_gap(probe) or res.gap   # refresh with the decomposition's diagnosis
            res.statement_false = _extract_statement_false(probe) or res.statement_false
    return res


def solve_robust(
    goal: str,
    *,
    defs: str,
    project_dir: str | Path,
    repo: str | Path,
    lake_bin: str,
    providers: tuple[str, ...] = ("codex",),
    attempts_per_provider: int = 1,
    target: str = "leaf",
    timeout: int = 600,
    decompose: bool = True,
    dispatch: Callable = default_dispatch,
    verify: Optional[Callable] = None,
    substrate_calibrate: Optional[Callable] = None,
) -> LeafResult:
    """Best-of-N agentic solve across providers × attempts. The agentic leaf is STOCHASTIC
    (codex closed P1 d0 in ~1 of 3 runs); retrying and crossing providers (codex/claude/
    deepseek — different reasoning) raises the closure RATE and adds cross-family coverage,
    which is the cheapest scientific-progress lever on the tractable bucket. Returns the FIRST
    kernel-clean closure; if none closes, the most-informative admissible attempt (so the
    residual is still localized). Each attempt is independently calibrated + kernel-arbitrated;
    a closure from ANY attempt is a real closure (the kernel does not care which model found it)."""
    # WHOLE-MOVE deadline (2026-06-07 — the warm-domination fix). `timeout` is the TOTAL budget for the
    # ENTIRE best-of-N, not per-attempt: previously each of the N providers × attempts got the full
    # `timeout`, so the warm move ran N × (direct+decompose+retries) ≈ the whole wallclock under a tight
    # per-move cap, starving every other move. Each attempt now gets the budget that REMAINS; once it's
    # spent we stop starting new attempts and keep the best of what we have.
    deadline = time.time() + max(_MIN_DISPATCH_S, timeout)
    attempts: list[LeafResult] = []
    stop = False
    for provider in providers:
        if stop:
            break
        for i in range(attempts_per_provider):
            remaining = int(deadline - time.time())
            if attempts and remaining < _MIN_DISPATCH_S:   # budget spent → keep best-of-what-we-have
                stop = True
                break
            r = solve_leaf(goal, defs=defs, project_dir=project_dir, repo=repo, lake_bin=lake_bin,
                           probe_name=f"RobustProbe_{provider}_{i}.lean", target=target,
                           runtime=provider, timeout=max(_MIN_DISPATCH_S, remaining), decompose=decompose,
                           dispatch=dispatch, verify=verify, substrate_calibrate=substrate_calibrate)
            attempts.append(r)
            if r.closed:
                # carry the EXACT winning probe filename (2026-06-13 audit A1): the reader must not
                # reconstruct it from a `_0` guess + lexical glob (wrong when the win is on attempt i>0,
                # and `sorted()[-1]` mis-orders `_10`<`_9`). We know `i` here — record it.
                r.calibration["best_of"] = {"attempts_tried": len(attempts), "winner": provider,
                                            "winner_probe": f"RobustProbe_{provider}_{i}.lean"}
                return r
    # none closed: prefer an admissible attempt (real negative) over an inadmissible one
    admissible = [a for a in attempts if not a.inadmissible]
    best = (admissible[-1] if admissible else (attempts[-1] if attempts else
            LeafResult(closed=False, target=target, goal=goal, reason="no_attempts")))
    best.calibration["best_of"] = {"attempts_tried": len(attempts),
                                   "all_inadmissible": not admissible}
    return best


# ── offline self-test (the loop's logic, no live provider/lake) ──────────────
def _self_test() -> int:
    # The selftest MOCKS dispatch+verify, so the real warm-Lean server (solve_leaf:436 ensure_server) is pure
    # overhead here — and on a cold box it does a ~90s Mathlib load that makes the selftest *hang*. Force it off
    # so the test exercises only the logic it actually asserts (admissibility / axiom-audit / timeout-retry).
    os.environ["ZTARE_LEANMILL_LEAN_WARM"] = "0"
    fails = []
    # parse_verify_output: kernel-clean
    ok, _ = parse_verify_output("'leaf' depends on axioms: [propext, Classical.choice, Quot.sound]")
    if not ok: fails.append("clean-allowlist should pass")
    # sorryAx must fail
    ok, _ = parse_verify_output("'leaf' depends on axioms: [propext, sorryAx, Classical.choice]")
    if ok: fails.append("sorryAx must fail")
    # bad axiom must fail
    ok, why = parse_verify_output("'leaf' depends on axioms: [propext, myCustomAxiom]")
    if ok or "BAD_AXIOMS" not in why: fails.append("smuggled axiom must fail")
    # no-axiom proof passes
    ok, _ = parse_verify_output("'leaf' does not depend on any axioms")
    if not ok: fails.append("no-axiom proof should pass")
    # compile error fails
    ok, _ = parse_verify_output("Probe.lean:5:2: error: unknown identifier")
    if ok: fails.append("compile error must fail")
    # AXIOM-LAUNDERING regression (bug-hunt 2026-06-10, HIGH): a clean HELPER's #print-axioms line must NOT
    # mask the TARGET's real axioms (e.g. native_decide's Lean.ofReduceBool). With `target` known, key on it.
    _L = "'helper' does not depend on any axioms\n'tgt' depends on axioms: [propext, Lean.ofReduceBool]\n"
    ok, why = parse_verify_output(_L, target="tgt")
    if ok or "Lean.ofReduceBool" not in why:
        fails.append("axiom-launder: clean helper must NOT mask the target's bad axioms (target-keyed)")
    ok, _ = parse_verify_output(_L)   # no target ⇒ fallback scans EVERY line; any bad axiom rejects
    if ok: fails.append("axiom-launder: fallback must scan all axiom lines (no clean-line short-circuit)")
    ok, _ = parse_verify_output("'helper' does not depend on any axioms\n'tgt' does not depend on any axioms\n", target="tgt")
    if not ok: fails.append("axiom-launder: a genuinely-clean target with a clean helper must still pass")
    ok, why = parse_verify_output("'helper' does not depend on any axioms\n", target="tgt")
    if ok or "no_axiom_line_for_target" not in why:
        fails.append("axiom-launder: missing target axiom line must FAIL-CLOSED")
    # STATEMENT-FALSE parse (the SOFT reformulation trigger) — distinct from a GAP, fail-safe on a missing file
    import tempfile as _tf
    _f = _tf.NamedTemporaryFile("w", suffix=".lean", delete=False)
    _f.write("theorem t : P := by\n  -- STATEMENT-FALSE: counterexample x=0; needs hypothesis q ≠ 0\n  sorry\n")
    _f.close()
    if "counterexample x=0" not in _extract_statement_false(_f.name):
        fails.append("STATEMENT-FALSE must be parsed from the probe")
    if _extract_statement_false(_f.name + ".nope") != "":
        fails.append("missing probe must yield empty statement_false (fail-safe)")
    os.remove(_f.name)
    # scan_probes_for_statement_false (solve_adhoc's single capture point): finds the marker across a scratch dir
    _d = _tf.mkdtemp()
    Path(_d, "clean.lean").write_text("theorem a : T := by\n  sorry\n", encoding="utf-8")
    Path(_d, "refuted.lean").write_text("theorem b : F := by\n  -- STATEMENT-FALSE: CE num=X^2 den=X\n  sorry\n", encoding="utf-8")
    if "CE num=X^2" not in scan_probes_for_statement_false(_d):
        fails.append("scan_probes_for_statement_false must find the marker across a scratch dir")
    if scan_probes_for_statement_false(_d + "_missing") != "":
        fails.append("scan_probes_for_statement_false must be fail-safe on a missing dir")
    import shutil as _sh
    _sh.rmtree(_d, ignore_errors=True)
    # dead provider ⇒ inadmissible, not closed=False
    r = solve_leaf("True", defs="", project_dir=".", repo=".", lake_bin="lake",
                   dispatch=lambda *a, **k: "", verify=lambda: (True, "x"))
    if not r.inadmissible or r.closed:
        fails.append("dead provider must be INADMISSIBLE, not a real negative")
    # live provider + verify True ⇒ closed
    r = solve_leaf("True", defs="", project_dir=".", repo=".", lake_bin="lake",
                   dispatch=lambda p, **k: "ALIVE", verify=lambda: (True, "clean"))
    if not r.closed:
        fails.append("live provider + passing verify must close")
    # solve_robust: first live+passing attempt closes
    r = solve_robust("True", defs="", project_dir=".", repo=".", lake_bin="lake",
                     providers=("codex", "claude"), dispatch=lambda p, **k: "ALIVE",
                     verify=lambda: (True, "clean"))
    if not r.closed or r.calibration.get("best_of", {}).get("attempts_tried") != 1:
        fails.append("solve_robust must return first closing attempt")
    # solve_robust: all providers dead ⇒ inadmissible best (never a fake negative)
    r = solve_robust("True", defs="", project_dir=".", repo=".", lake_bin="lake",
                     providers=("codex", "claude"), dispatch=lambda *a, **k: "",
                     verify=lambda: (True, "x"))
    if r.closed or not r.calibration.get("best_of", {}).get("all_inadmissible"):
        fails.append("solve_robust all-dead must be inadmissible, not a fake negative")
    # _dispatch_timed_out detection
    if not _dispatch_timed_out("subscription agent command timed out after 600s"):
        fails.append("timeout marker must be detected")
    if _dispatch_timed_out("could not prove the goal"):
        fails.append("a genuine failure must NOT look like a timeout")
    # TIMEOUT-AWARE RETRY: an under-budget timeout (open, then closes with more budget) is
    # recovered; a GENUINE failure (no timeout marker) is NOT retried.
    st = {"d": 0, "v": 0}
    def _disp_timeout(prompt, **k):
        if "ALIVE" in prompt:
            return "ALIVE"
        st["d"] += 1
        return "...subscription agent command timed out after 600s" if st["d"] == 1 else "done"
    def _verify_then_close():
        st["v"] += 1
        return (st["v"] >= 2, "clean" if st["v"] >= 2 else "uses_sorry")
    r = solve_leaf("True", defs="", project_dir=".", repo=".", lake_bin="lake",
                   dispatch=_disp_timeout, verify=_verify_then_close, decompose=False)
    if not (r.closed and r.timeout_retried and r.rounds == 2):
        fails.append("timeout-retry must recover an under-budget timeout (closed+retried)")
    r = solve_leaf("True", defs="", project_dir=".", repo=".", lake_bin="lake",
                   dispatch=lambda p, **k: "ALIVE" if "ALIVE" in p else "could not prove",
                   verify=lambda: (False, "uses_sorry"), decompose=False)
    if r.closed or r.timeout_retried or r.rounds != 1:
        fails.append("a genuine failure must NOT trigger the timeout-retry")
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
