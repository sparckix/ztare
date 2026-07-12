"""REPL-backed whole-file compile — route a Lean probe through a WARM PersistentLean instead of a cold
`lake env lean`. The `import Mathlib` reload (~40-90s on a no-persistent-REPL box) is paid ONCE per
(repl, project); every subsequent probe elaborates in ~0.1s. Same verdict contract as a fresh compile
(success ⇔ no error ∧ no sorry), so it's a drop-in for `_compile_probe` / native_hammer's per-tactic compile.

DROP-IN + FAIL-SAFE: returns `True`/`False` only when a LIVE MATCHED REPL exists for the sandbox and the
check ran; returns `None` (→ the caller falls back to the canonical `lake env lean` path) when the flag is off,
the repl toolchain does NOT match the substrate (the drift guard — never trust a mismatched REPL), or the REPL
died. Gated by `ZTARE_LEANMILL_REPL_COMPILE` (default-OFF = byte-parity with the current cold path) until the
REPL-vs-lake parity is validated, then flip on. The whole point: kill the cold-reload-per-probe cost that the
hand-guessed timeouts kept false-failing on — at the source, not by budgeting around it.
"""
from __future__ import annotations

import atexit
import os
import re
from pathlib import Path
from typing import Optional

_REPL_CACHE: "dict[str, object]" = {}     # resolved project_dir -> live PersistentLean (import paid once)
_TC_CACHE: "dict[str, bool]" = {}         # resolved project_dir -> toolchain_match(repl, project)

import threading as _threading
_REPL_LOCKS: "dict[str, object]" = {}     # per-project mutex — serialize pl.check on the SHARED warm REPL
_REPL_LOCK_GUARD = _threading.Lock()


def _repl_lock(project: str):
    with _REPL_LOCK_GUARD:
        lk = _REPL_LOCKS.get(project)
        if lk is None:
            lk = _REPL_LOCKS[project] = _threading.Lock()
        return lk


def _emit_verify_trace(project: str, row: dict) -> None:
    """Best-effort JSONL trace for warm/campaign verifier routing. Never participates in proof decisions."""
    try:
        import json as _json
        import time as _time
        p = Path(os.environ.get(
            "ZTARE_LEANMILL_VERIFY_TRACE",
            str(Path(project) / "analytics" / "public" / "queries" / "leanmill_verify_trace.jsonl"),
        ))
        p.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": _time.time(), **row}
        with p.open("a", encoding="utf-8") as fh:
            fh.write(_json.dumps(rec, sort_keys=True) + "\n")
    except Exception:  # noqa: BLE001
        return


def _emit_substrate_verdict(file_path: "str | Path", project: str, kind: str, detail: str,
                            source_text: str = "") -> None:
    """Best-effort typed verdict for substrate liveness RCA. Never participates in compile decisions."""
    try:
        from ztare.leanmill.control_plane import StatementId, Verdict, VerdictKind
        from ztare.leanmill.verdict_store import emit_verdict
        fp = Path(file_path)
        vk = (VerdictKind.SUBSTRATE_BROKEN if kind == "broken"
              else VerdictKind.SUBSTRATE_UNAVAILABLE)
        emit_verdict(Verdict(
            kind=vk,
            statement_id=StatementId.from_parts(
                target_name=fp.name,
                source_text=source_text or "",
                closed_prop=f"substrate:{fp.resolve()}",
                substrate_path=fp,
            ),
            provenance="campaign_file_env.cold_substrate_check",
            detail=(detail or "")[:1000],
            artifacts={"substrate_path": str(fp), "project": str(project or "")},
        ), extra={"substrate_verdict": kind})
    except Exception:  # noqa: BLE001
        return


def _robust_repl_check(pl, project: str, code: str, timeout: int, env, *, retries: int = 2,
                       acquire_timeout: float = 30.0, cap_warm: bool = True):
    """WORLD-CLASS access to the SHARED warm REPL (2026-07-05, operator: "brittle error handling without retries
    on a contested warm compile — must be distributed-systems grade"). The warm REPL is ONE resource; the solver
    holds it while proving, and un-serialized concurrent `pl.check` calls corrupt its socket → a transient dead
    reply that callers then mis-read as a NEGATIVE verdict (the dead-instrument fallacy — a false reject). This:
      (1) SERIALIZES via a per-project mutex, but with a BOUNDED acquire timeout ⇒ a long-busy REPL degrades to
          `None` (⇒ the caller does its INDEPENDENT cold compile) instead of DEADLOCKING;
      (2) RETRIES the TRANSIENT failures — a wedged command (drop+respawn), a malformed/partial reply — with
          exponential backoff, because a transient infra failure is 'instrument unavailable', never a verdict;
      (3) returns the result dict on a real RUN (has `errors`), or `None` = 'unavailable ⇒ fall back'. The
          None/ran distinction is the whole point: only a RUN yields a verdict. THE single door every warm-REPL
          consumer (probe compile, campaign env) routes through, so the resilience is inherited, not per-caller."""
    import time as _time
    lk = _repl_lock(project)
    if not lk.acquire(timeout=acquire_timeout):
        return None                                       # contended past the bound ⇒ fall back, never block forever
    try:
        _delay = 0.25
        for _attempt in range(retries + 1):
            _p = pl if _attempt == 0 else _get_repl(project)
            if _p is None:
                _time.sleep(_delay); _delay *= 2; continue
            try:
                _to = min(timeout, _warm_ceiling()) if cap_warm else timeout   # heavy env-builds opt out of the probe cap
                r = _p.check(code, timeout=_to, env=env)
            except Exception:  # noqa: BLE001 — wedged/crashed command: drop + respawn + retry (transient)
                _drop_repl(project)
                _time.sleep(_delay); _delay *= 2; continue
            if isinstance(r, dict) and "errors" in r:
                return r                                  # the instrument RAN ⇒ a real verdict (may be errors)
            _time.sleep(_delay); _delay *= 2              # malformed/partial ⇒ transient ⇒ retry
        return None                                       # retries exhausted ⇒ unavailable ⇒ caller falls back
    finally:
        lk.release()
# CAMPAIGN-THEORY WARM ENV (2026-06-14): a heavy agent-built substrate (P1Theory: PowerSeries/MvPolynomial)
# was being RE-ELABORATED from an inlined prelude on EVERY verify (592-1016s timeouts, run closed nothing).
# `open_file()` elaborates the file ONCE → an env id whose decls (the proven API) are live for subsequent
# `check(code, env=<id>)` with NO re-elaboration. Cache the env per file, keyed on mtime so it re-opens the
# instant the agent extends the theory — the "olean fed dynamically as the agent builds it". Cleared on REPL
# respawn (non-base env ids die with the process).
_FILE_ENV_CACHE: "dict[str, tuple[float, int, str, int]]" = {}   # resolved file path -> (mtime, size, sha16, env_id)


def drop_campaign_file_env_cache(file_path: "str | Path | None" = None) -> None:
    """Invalidate cached campaign-file env ids.

    Bank writes can replace a file multiple times inside one filesystem timestamp tick. A cache keyed only by mtime can
    then hand back an env for previous bytes. Size+sha guards reads; explicit invalidation keeps mutation sites simple."""
    if file_path is None:
        _FILE_ENV_CACHE.clear()
        return
    try:
        _FILE_ENV_CACHE.pop(str(Path(file_path).resolve()), None)
    except Exception:  # noqa: BLE001
        _FILE_ENV_CACHE.clear()
_IMPORT_MATHLIB_RE = re.compile(r"^\s*import\s+Mathlib\s*$", re.MULTILINE)
# Strip ALL imports before a warm-REPL probe: the persistent REPL's base env IS the full Mathlib prelude
# (which re-exports Aesop / Batteries / Std), and the REPL rejects ANY `import` mid-session with
# "invalid 'import' command, it must be used in the beginning of the file". Stripping only `import Mathlib`
# left e.g. miniF2F's `import Aesop` in place → every probe failed_compile regardless of proof correctness
# (a dead instrument). SOUND: an import whose decls are NOT already in the base env ⇒ the probe fails with
# "unknown identifier" (a real failure), never a false PASS — so stripping can only fix, never launder.
_ALL_IMPORTS_RE = re.compile(r"^\s*import\s+\S+.*$", re.MULTILINE)
# Explicit `universe …` COMMAND lines (not the `Type u` USES). They COLLIDE with the PERSISTENT warm-REPL
# environment: a `universe u` re-declared across probes in ONE warm session errors `universe 'u' already
# declared`, so any probe the formalizer renders with `universe u v w` + `Type u/v/w` FALSE-FAILS on the 2nd+
# attempt in the session (RCA 2026-06-22: the stochastic-factorization rung — a CORRECT 6-line proof rejected
# as `did not typecheck :: universe … already declared`, 14/23 attempts poisoned, never the math; the leaf got
# exactly ONE real shot per warm session). Stripping the COMMAND is SOUND: Lean 4 AUTO-BINDS the now-unbound
# `Type u/v/w` (each declaration gets fresh LOCAL universes — verified byte-equivalent closure), and a
# genuinely-missing universe fails `unknown universe`, never a false PASS. Mirrors the import-strip rationale.
_UNIVERSE_CMD_RE = re.compile(r"^\s*universe\s+\S.*$", re.MULTILINE)


def _strip_prelude_for_repl(src: str) -> str:
    """Strip the file-scope prelude that collides with the persistent warm-REPL env: `import` lines (Mathlib is
    already in the base env) AND `universe …` command lines (see `_UNIVERSE_CMD_RE`). ONE canonical accessor so
    the two strips can never drift apart across the four warm-check sites (anti-sibling)."""
    return _UNIVERSE_CMD_RE.sub("", _ALL_IMPORTS_RE.sub("", src)).lstrip("\n")


def _flag_on() -> bool:
    # DEFAULT-ON 2026-06-09 (broad REPL-vs-lake parity validated across probe classes + both sorry policies;
    # #print axioms audit is a separate untouched path). `=0` reverts to the cold `lake env lean` path. The
    # fast path still only ACTIVATES when a live toolchain-matched repl exists for the sandbox (else None →
    # fallback), so default-on is safe on a box without a matching REPL.
    return os.environ.get("ZTARE_LEANMILL_REPL_COMPILE", "1") != "0"


def _warm_ceiling() -> int:
    """Bound the per-probe WARM-REPL compile timeout. The persistent REPL elaborates in ~0.1s; a probe that
    blocks the warm REPL for >ceiling is pathological (expensive / non-terminating elaboration — exact?/apply?
    library search on a hard goal, or a wedged tactic) and must FAIL-CLOSED fast rather than consume the whole
    solve wallclock. ROOT CAUSE of the recurring P1-RUNG-A 'silent death' (diagnosed 2026-06-10 via faulthandler):
    native_hammer passed its ≥60s..remaining-budget timeout straight through, so ONE wedged `exact?` probe blocked
    ~200s+ on the warm REPL and the detached run appeared hung. The cold `lake env lean` fallback keeps the
    caller's FULL timeout for legitimately-slow COLD compiles — this caps ONLY the warm path (which should never
    legitimately need >ceiling). Tunable via ZTARE_LEANMILL_REPL_WARM_CEILING_S (default 90), resolved through
    the central time-budget factory `ztare.common.timeouts` so every blocking timeout lives in one place."""
    from ztare.common.timeouts import timeout_s
    return timeout_s("warm_repl_ceiling")


def _toolchain_ok(project: str) -> bool:
    if project in _TC_CACHE:
        return _TC_CACHE[project]
    try:
        from ztare.formal.lean_persistent import DEFAULT_REPL_BIN
        from ztare.formal.substrate_liveness import toolchain_match
        ok = bool(toolchain_match(DEFAULT_REPL_BIN, project)[0])
    except Exception:  # noqa: BLE001 — any error ⇒ don't use the REPL (fall back to lake env lean)
        ok = False
    _TC_CACHE[project] = ok
    return ok


def _get_repl(project: str):
    """Lazily start (and cache) a live PersistentLean over `project`; respawn on death. None on failure."""
    pl = _REPL_CACHE.get(project)
    if pl is not None:
        return pl
    try:
        from ztare.formal.lean_persistent import PersistentLean
        pl = PersistentLean(project_dir=project)
        pl.__enter__()                       # starts the process + pays the one-time Mathlib import
        _REPL_CACHE[project] = pl
        return pl
    except Exception:  # noqa: BLE001 — repl missing / import failed ⇒ no REPL path
        return None


def _drop_repl(project: str) -> None:
    pl = _REPL_CACHE.pop(project, None)
    _FILE_ENV_CACHE.clear()   # non-base env ids die with the REPL process — never hand back a stale file env
    if pl is not None:
        try:
            pl.close()
        except Exception:  # noqa: BLE001
            pass


def _substrate_cold_compiles(fp: "Path", project: str, timeout: int) -> "Optional[bool]":
    """GROUND TRUTH for "is this substrate actually broken?" — a cold `lake env lean` compile (the same kernel
    path a real closure uses), used to CONFIRM a warm-REPL "substrate broken" verdict before it is trusted (the
    2026-07-05 CLOB false-DEAD RCA: the stateful warm REPL lost a section-scoped `[LT T]` and reported a HEALTHY
    substrate DEAD; cold compiles it CLEAN). True = compiles (warnings OK), False = real hard errors, None =
    cannot run (no lake/toolchain) ⇒ caller must not treat 'None' as broken. Best-effort + bounded; never raises."""
    import subprocess as _sp, shutil as _sh, os as _os
    lake = _sh.which("lake") or _os.path.expanduser("~/.elan/bin/lake")
    if not _os.path.exists(lake):
        return None
    try:
        r = _sp.run([lake, "env", "lean", str(fp)], cwd=project, capture_output=True, text=True,
                    timeout=timeout)
    except Exception:  # noqa: BLE001 — cannot run cold ⇒ inconclusive (None), never a false 'broken'
        return None
    if r.returncode == 0:
        return True                                  # rc 0 = clean (warnings-only still exits 0)
    out = (r.stdout or "") + (r.stderr or "")
    # UNAVAILABLE ≠ VERDICT (2026-07-06, gale false-DEAD recurrence): a cold `lake env lean` that cannot RESOLVE
    # its dependencies — `unknown module prefix 'Mathlib'`, an empty/olean-less search path, a missing package —
    # is a BROKEN INSTRUMENT, not a broken substrate. Bucketing that `error:` as False (the old line below) made
    # the cold check "confirm" a transient warm-REPL contamination as a dead substrate → the recurring false
    # "SUBSTRATE DOES NOT COMPILE" + guard-revert risk. This is the SAME dead-instrument discipline already applied
    # to the warm path (principle 10) — it was just never applied to the cold ground-truth check (anti-sibling).
    # These env/dep-resolution failures are inconclusive (None) ⇒ caller falls back to warm/inline, no revert.
    _low = out.lower()
    if any(s in _low for s in ("unknown module prefix", "in the search path", "unknown package",
                               "no such file or directory")):
        return None
    return False if ": error:" in out or "error:" in out else None


def campaign_file_env(file_path, sandbox, timeout: int = 600) -> "Optional[int]":
    """Elaborate a campaign theory file ONCE via `open_file` and cache its env id (re-open on mtime change), so
    verify probes can `check(code, env=<id>)` against it — the heavy substrate's decls already elaborated —
    instead of re-inlining + recompiling them on every probe. Returns the env id, or None (flag off / toolchain
    mismatch / dead REPL / open failed / open produced a hard error) ⇒ caller falls back to the inline path.

    SOUNDNESS: this only AMORTIZES the substrate's elaboration; it changes WHERE deps are elaborated, never the
    verdict. A probe checked against this env that cites a still-`sorry` decl carries `sorryAx` → the `#print
    axioms` allowlist audit (unchanged, separate path) rejects it exactly as before. The probe must use a FRESH
    decl name (the caller's job) since the target's own sorried decl is live in this env (re-declaring clashes)."""
    if not _flag_on():
        return None
    try:
        fp = Path(file_path).resolve()
        if not fp.exists():
            return None
        st = fp.stat()
        mtime = st.st_mtime
        size = st.st_size
        import hashlib as _hashlib
        sha16 = _hashlib.sha256(fp.read_bytes()).hexdigest()[:16]
    except Exception:  # noqa: BLE001
        return None
    key = str(fp)
    cached = _FILE_ENV_CACHE.get(key)
    if cached is not None and cached[0] == mtime and cached[1] == size and cached[2] == sha16:
        return cached[3]
    project = str(Path(sandbox).resolve())
    if not _toolchain_ok(project):           # the drift guard — never trust a mismatched REPL
        return None
    pl = _get_repl(project)
    if pl is None:
        return None
    # Elaborate the theory's DECLS onto the warm base (Mathlib) env via `check(env=None)` — NOT `open_file`,
    # which re-runs the file's own `import Mathlib` from scratch (re-importing Mathlib ⇒ >700s / timeout on a
    # heavy file). Stripping the redundant `import Mathlib` and branching from base_env pays only the decls'
    # elaboration ONCE; `check` returns the new env id (valid even with `sorry` targets — those are the holes,
    # not errors). Other imports (non-Mathlib) would error here ⇒ None ⇒ caller falls back (campaign theory is
    # Mathlib + inline decls by construction).
    try:
        src = fp.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return None
    code = _strip_prelude_for_repl(src)
    if not code.strip():
        return None
    # SERIALIZED + RETRIED (the single door): a busy/wedged REPL degrades to None (⇒ caller falls back), never a
    # false 'substrate DEAD'. cap_warm=False: the full-substrate elaboration legitimately needs the 600s budget.
    r = _robust_repl_check(pl, project, code, timeout, None, cap_warm=False)
    if r is None:
        return None
    # a non-compiling theory must NEVER become a silent verify env; hard ERRORS disqualify it (sorries OK).
    # LOUD-ON-FAILURE (2026-06-25 RCA — the AMM `not_riskFreeProfit_zero` `<;>` bug): a single broken decl
    # ANYWHERE in the registered substrate makes this return None, which SILENTLY kills the WHOLE campaign-aware
    # layer — citing, warm-verify, AND the kernel faithfulness oracle (which then falls back to a Mathlib-only
    # probe that can't resolve campaign vocab → FALSE-REJECTS every faithful ∀-fronted proof as
    # `target_signature_altered`). The silence is what let a non-compiling substrate masquerade as "hard math"
    # for a whole campaign. Surface the compile errors LOUDLY so a dead substrate env is a VISIBLE dead
    # instrument (the same discipline as the embedder-liveness banner), never a silent degrade. (Still returns
    # None — the soundness policy is unchanged; only the observability is fixed.)
    if not isinstance(r, dict) or r.get("errors") or r.get("env") is None:
        # WARM-REPL "substrate broken" is NOT ground truth (2026-07-05 CLOB false-DEAD RCA): the persistent REPL is
        # STATEFUL — a prior probe's leaked `variable`/`section`/`open` state can make a HEALTHY multi-section
        # substrate spuriously fail (`failed to synthesize [LT T]` on a lemma whose section-scoped instance the
        # contaminated env lost), which cold `lake env lean` compiles CLEAN. Collapsing that into "substrate DEAD"
        # is the dead-instrument fallacy (principle 10: UNAVAILABLE ≠ VERDICT) — it triggered a false guard-revert +
        # rung retraction + the whole-campaign spin. CONFIRM before condemning: (1) respawn a FRESH REPL and
        # re-elaborate once — a clean process has no leaked state; (2) if it STILL errors, cold-compile as ground
        # truth. Only a COLD break is a real dead substrate. A transient/contaminated warm failure over a
        # cold-CLEAN file returns None WITHOUT the DEAD signal (caller falls back to the inline/cold path; the
        # substrate stays HEALTHY ⇒ no revert/retract cascade).
        _drop_repl(project)                                       # clear any leaked session state
        pl2 = _get_repl(project)
        if pl2 is not None:
            r2 = _robust_repl_check(pl2, project, code, timeout, None, cap_warm=False)
            if isinstance(r2, dict) and not r2.get("errors") and r2.get("env") is not None:
                env = int(r2["env"]); _FILE_ENV_CACHE[key] = (mtime, size, sha16, env)
                return env                                        # fresh REPL: the warm failure was contamination
            r = r2 if isinstance(r2, dict) else r                 # report the fresh REPL's errors if it has them
        _cold = _substrate_cold_compiles(fp, project, timeout)
        if _cold is True:                                         # substrate is HEALTHY; warm/cold parity glitch
            print(f"⚠️  [substrate-env] warm REPL reported {key} broken but a COLD `lake env lean` compile is CLEAN "
                  f"— transient warm-parity glitch, NOT a dead substrate. Falling back to the cold path; no revert/"
                  f"retract.", flush=True)
            return None
        if _cold is None:                                         # cold check COULD NOT RUN (no lake / can't resolve
            # Mathlib / empty search path) — INCONCLUSIVE, not a verdict. Do NOT claim "confirmed by cold compile"
            # (the recurring false DEAD): the warm error was most likely leaked-session contamination over a HEALTHY
            # substrate. Fall back to the inline/cold path with NO revert, NO alarm. (principle 10: UNAVAILABLE ≠ dead.)
            _emit_substrate_verdict(fp, project, "unavailable",
                                    "warm REPL reported substrate errors, but cold substrate check could not run",
                                    src)
            print(f"ℹ️  [substrate-env] warm REPL reported {key} broken but the COLD `lake env lean` ground-truth check "
                  f"COULD NOT RUN (toolchain/Mathlib not resolvable) — INCONCLUSIVE, not a dead substrate. Falling "
                  f"back; no revert/retract.", flush=True)
            return None
        _errs = r.get("errors") if isinstance(r, dict) else None
        _emit_substrate_verdict(fp, project, "broken",
                                "cold substrate compile failed: " + "; ".join(str(e)[:200] for e in (_errs or [])[:5]),
                                src)
        if _errs:
            print(f"⚠️  CAMPAIGN SUBSTRATE DOES NOT COMPILE: {key} — {len(_errs)} hard error(s), confirmed by cold "
                  f"compile. The campaign-aware verify env is DEAD ⇒ citing / warm-verify / the faithfulness oracle "
                  f"all degrade (faithful proofs may FALSE-REJECT as `target_signature_altered`). FIX THE "
                  f"SUBSTRATE. First errors:", flush=True)
            for _e in _errs[:5]:
                print(f"      {str(_e)[:200]}", flush=True)
        return None
    env = int(r["env"])
    _FILE_ENV_CACHE[key] = (mtime, size, sha16, env)
    return env


def campaign_file_decl_axiom_clean(file_path, sandbox, decl_name: str, timeout: int = 120) -> "Optional[tuple[bool, str]]":
    """`#print axioms <decl_name>` against the CACHED campaign-file env (the decl is already live there), so the
    bank chokepoint can audit a just-banked decl IN ITS PERSISTED ENV without a second full re-elaboration —
    the reverify call just built/cached this env for the current mtime, so this is a single cheap REPL query.

    Returns `(clean, diag)` — `clean=False` ONLY on a DETECTED `sorryAx` / non-allowlisted axiom (fail-CLOSED:
    the caller reverts) — or `None` when the audit cannot run / is inconclusive (flag off / toolchain / dead
    REPL / unknown decl / no verdict) so the caller fails OPEN (a flaky audit never blocks compounding; the
    cold governance audit remains the backstop). This is the persistence-world half of the two-verify-worlds
    fix (RCA 2026-06-25): banking re-verified COMPILE here but never AXIOMS, so a rung citing a still-`sorry`
    canonical sibling compiled and banked, surfacing `sorryAx` only when the target was re-elaborated."""
    env = campaign_file_env(file_path, sandbox, timeout=timeout)
    if env is None:
        return None
    project = str(Path(sandbox).resolve())
    pl = _get_repl(project)
    if pl is None:
        return None
    try:
        ax = pl.check(f"#print axioms {decl_name}", timeout=min(timeout, _warm_ceiling()), env=env)
    except Exception:  # noqa: BLE001
        _drop_repl(project)
        return None
    raw = str((ax or {}).get("raw", "")) if isinstance(ax, dict) else ""
    if "axioms" not in raw:
        return None                                       # unknown decl / no verdict ⇒ inconclusive (fail-open)
    low = raw.lower()
    if "sorryax" in low:
        return (False, f"sorryAx in {decl_name} (persisted env — laundered sorried sibling)")
    import re as _re_ax
    cited = _re_ax.findall(r"[A-Za-z_][\w.]*", raw.split("depends on axioms", 1)[-1]) if "depends on axioms" in raw else []
    bad = [a for a in cited if a not in _ALLOWED_AXIOMS and (a.endswith("Ax") or a in ("Lean.ofReduceBool", "Lean.trustCompiler"))]
    if bad:
        return (False, f"non-allowlisted axiom in {decl_name}: {bad}")
    # CLEAN: return the actual allowlisted axiom LIST (not the "axiom_clean" sentinel) so the caller can STAMP
    # the honest persisted-world axioms for P0 provenance — no consumer branches on the clean-diag string
    # (def_denotation reads res[0] only; the bank guard only logs it). "(no axioms)" when the decl is axiom-free.
    return (True, ", ".join(cited) if cited else "(no axioms)")


def compile_probe_via_repl(probe: str, sandbox, timeout: int = 120, *,
                           reject_sorry: bool = False, env: "Optional[int]" = None) -> "Optional[tuple[bool, str]]":
    """Compile a whole-file Lean `probe` against a warm REPL over `sandbox`. Returns `(ok, diagnostics)` or
    `None` when the REPL is not usable here (flag off / toolchain mismatch / dead) ⇒ the caller MUST fall back
    to `lake env lean`. `reject_sorry` MUST match the CALLER's policy: `_compile_probe` treats `sorry` as a
    WARNING and returns clean (it audits sorried decompositions) ⇒ `reject_sorry=False`; the no-false-closure
    checker (`_is_compile_ok` / `LeanLakeChecker.verify`) rejects sorry ⇒ `reject_sorry=True`. Getting this
    wrong manufactures a parity break (the REPL rejecting an intentional sorry breaks the decomposition audit —
    caught by the broad parity gate). Strips the leading `import Mathlib` (the prelude already has it).

    `env` (2026-06-14): an already-open env id (from `campaign_file_env`) to check AGAINST — the campaign
    theory's decls are live there, so the probe needs no inlined prelude and pays no re-elaboration. The probe
    must use a FRESH decl name (the target's sorried decl is live in this env). `env=None` ⇒ the frozen base
    (Mathlib) env, unchanged."""
    if not _flag_on():
        return None
    project = str(Path(sandbox).resolve())
    if not _toolchain_ok(project):           # the drift guard: a mismatched REPL is silently-empty → never use it
        return None
    pl = _get_repl(project)
    if pl is None:
        return None
    code = _strip_prelude_for_repl(probe)   # the prelude already has Mathlib (+Aesop/Batteries)
    if not code.strip():
        code = "example : True := trivial"
    # SERIALIZED + RETRIED shared-REPL access (the single door): returns the result dict on a real RUN, or None =
    # 'instrument unavailable ⇒ fall back to `lake env lean`' — NEVER a transient contention failure mis-read as a
    # verdict. A wedged command respawns + retries inside; a long-busy REPL degrades to None (cold fallback).
    r = _robust_repl_check(pl, project, code, timeout, env)
    if r is None:
        return None
    # an explicit campaign env that died with a REPL respawn ⇒ the file-env cache is stale; drop it + fall back
    # (the caller re-opens next call). Never silently re-run a campaign probe in base_env (wrong, prelude-less).
    if env is not None and "env_invalidated" in str(r.get("output", "")):
        _FILE_ENV_CACHE.clear()
        return None
    errs = r.get("errors") or []
    sorries = r.get("sorries") or []
    # match the CALLER's sorry policy (the parity fix): always reject on a real error; reject a sorry ONLY when
    # the caller does (`_is_compile_ok`/verify), NOT for `_compile_probe` which audits intentionally-sorried probes.
    ok = (not errs) and not (sorries and reject_sorry)
    if ok:
        diag = "repl: clean" + (f" (sorry present, allowed)" if sorries else "")
    else:
        toks = [*errs, *([f"sorry@{s}" for s in sorries] if (sorries and reject_sorry) else [])]
        diag = ("repl: " + " | ".join(toks))[:800] or "repl: error"
    return (ok, diag)


_ALLOWED_AXIOMS = ("propext", "Classical.choice", "Quot.sound")   # the kernel-sound allowlist (F1/F2)
_CAMPAIGN_SUBSTRATE: "Optional[str]" = None   # the active campaign theory file (set by the notes-channel run)
_CAMPAIGN_SUBSTRATE_ENV = "ZTARE_LEANMILL_CAMPAIGN_SUBSTRATE"   # cross-process mirror (subprocess/worker visibility)


def set_campaign_substrate(theory_path: "Optional[str]") -> None:
    """Register (or clear) the campaign theory file whose decls the verify seam should amortize into a warm
    env (instead of re-inlining + re-elaborating them per probe). The notes-channel run sets this once after
    theory consolidation; `campaign_file_env` re-opens automatically when the file's mtime changes."""
    global _CAMPAIGN_SUBSTRATE
    _CAMPAIGN_SUBSTRATE = str(theory_path) if theory_path else None
    # ALSO publish to the environment so the substrate crosses process boundaries. The in-memory global is
    # invisible to a spawned subprocess (`lean_check_server`, a re-imported module in a worker) — the RCA 2026-07-05
    # of CLOB "0 closures": native_hammer / proposer_pool built probe envs WITHOUT the theory (`Book`/`Order`
    # `unknown identifier` / metavariable) because `get_campaign_substrate()` returned None off the main thread,
    # so the whole close path was context-blind while decompose (which self-includes the preamble) worked → the
    # engine decomposed forever, never closing. os.environ is inherited by every child + visible to every import.
    if theory_path:
        os.environ[_CAMPAIGN_SUBSTRATE_ENV] = str(theory_path)
    else:
        os.environ.pop(_CAMPAIGN_SUBSTRATE_ENV, None)


_SUBSTRATE_LAST_GOOD: "dict[str, str]" = {}   # resolved path → last content that COMPILED (auto-revert snapshot)


def _last_good_snapshot_path(key: str) -> "Path":
    """Sidecar file holding the last-GOOD substrate content next to it (`.last_good`, not a `.lean` so lake ignores
    it). DISK persistence is the fix (2026-07-06) for the gale substrate-death that spun 30min: `_SUBSTRATE_LAST_GOOD`
    is an in-memory module dict, so a spawned worker / a fresh process (or the banking path that corrupted the file)
    has an EMPTY dict → `guard_substrate_compiles` finds "no snapshot to revert" and can't recover. Same class as the
    `_CAMPAIGN_SUBSTRATE` cross-process bug; same cure — persist it so EVERY process can revert."""
    return Path(key + ".last_good")


def _persist_last_good(key: str, content: str) -> None:
    _SUBSTRATE_LAST_GOOD[key] = content
    try:
        _last_good_snapshot_path(key).write_text(content, encoding="utf-8")
    except Exception:  # noqa: BLE001 — the in-memory copy still works within the process
        pass


def _load_last_good(key: str) -> "Optional[str]":
    snap = _SUBSTRATE_LAST_GOOD.get(key)
    if snap is not None:
        return snap
    try:
        p = _last_good_snapshot_path(key)
        return p.read_text(encoding="utf-8") if p.exists() else None
    except Exception:  # noqa: BLE001
        return None


def guard_substrate_compiles(path, lean_root, *, log=print) -> bool:
    """FIX-FOREVER for the silent SUBSTRATE-DEATH class (RCA 2026-07-03 — the EF1 capstone was stubbed `:= by
    aesop`; aesop is CONTEXT-dependent, so when a mid-run bank changed the surrounding lemmas it stopped compiling
    → `campaign_file_env` returned None → the whole campaign-aware verify env went DEAD → every subsequent proof,
    including CORRECT ones, false-rejected as `target_signature_altered` → the run SPUN degraded. The LOUD warning
    fired but nothing ACTED). This makes a broken substrate impossible to ignore: verify it COMPILES; snapshot it
    when good; on a break, REVERT to the last-good snapshot (keeping every compile-gated bank up to it) + LOUD.
    Call before each lemma attack AND after any theory write. Returns True iff LIVE after any revert.
    ZTARE_LEANMILL_SUBSTRATE_GUARD=0 reverts to the prior degrade-silently behaviour (A/B)."""
    import os as _os
    if _os.environ.get("ZTARE_LEANMILL_SUBSTRATE_GUARD", "1") == "0":
        return True
    p = Path(path)
    if not p.exists():
        return False
    key = str(p.resolve())
    if campaign_file_env(key, str(lean_root)) is not None:
        try:
            _persist_last_good(key, p.read_text(encoding="utf-8"))   # snapshot the KNOWN-GOOD state (in-mem + disk)
        except Exception:  # noqa: BLE001
            pass
        return True
    # `campaign_file_env` is None — but that can mean the warm REPL is momentarily UNAVAILABLE, NOT that the
    # substrate is broken (2026-07-05 CLOB false-DEAD RCA). Cold `lake env lean` is the ground truth: if the file
    # cold-compiles CLEAN, the substrate is HEALTHY and the warm miss is transient — NEVER revert a healthy
    # substrate to an older snapshot (that would DESTROY every compile-gated bank since it, over a warm glitch).
    # Only a COLD-confirmed break may revert (principle 10: UNAVAILABLE ≠ VERDICT).
    try:
        from ztare.common.timeouts import timeout_s as _timeout_s
        _cold_timeout = int(_timeout_s("cold_compile"))
    except Exception:  # noqa: BLE001
        _cold_timeout = 0
    if _cold_timeout > 0 and _substrate_cold_compiles(p.resolve(), str(Path(lean_root).resolve()), _cold_timeout) is True:
        try:
            _persist_last_good(key, p.read_text(encoding="utf-8"))   # cold-healthy ⇒ refresh the good snapshot (in-mem + disk)
        except Exception:  # noqa: BLE001
            pass
        return True
    snap = _load_last_good(key)   # in-memory OR the cross-process DISK snapshot (the gale substrate-death fix)
    if snap is not None:
        try:
            p.write_text(snap, encoding="utf-8")
            _FILE_ENV_CACHE.clear()
            log(f"⚠️  [substrate-guard] the campaign substrate STOPPED COMPILING mid-run — auto-REVERTED to the "
                f"last-good snapshot ({len(snap.splitlines())} lines). A broken substrate silently kills the verify "
                f"env (correct proofs false-reject); reverted so the run stays HEALTHY.", flush=True)
        except Exception:  # noqa: BLE001
            pass
        return campaign_file_env(key, str(lean_root)) is not None
    log("⚠️  [substrate-guard] substrate broke with NO last-good snapshot — the verify env is DEAD. FIX THE "
        "SUBSTRATE (a target stub must be `sorry`, never a fragile `by aesop`).", flush=True)
    return False


def get_campaign_substrate() -> "Optional[str]":
    """THE one reader: the in-memory global when set (main thread/process), else the env-var mirror (a spawned
    subprocess / re-imported module in a worker, where the global is None). Every campaign-context consumer —
    the native_hammer prepend, the fingerprint, namespaces/variables, campaign_file_env — routes through here,
    so the theory context reaches EVERY prover env, not just the ones sharing the main process's memory."""
    return _CAMPAIGN_SUBSTRATE or os.environ.get(_CAMPAIGN_SUBSTRATE_ENV) or None


_SUBSTRATE_FP_CACHE: "dict" = {}   # substrate path -> (mtime, def-vocabulary fingerprint)


def current_substrate_fingerprint() -> str:
    """The def-vocabulary fingerprint of the REGISTERED campaign substrate (2026-07-05, the reuse-invalidation
    single door). Every reuse cache prepends this to its key so a rendering/proof confirmed against one theory
    vocabulary is transparently NOT served against a different one — the general-purpose cure for substrate-BLIND
    reuse (v2's existential `Marketable` reused over v3's decidable one). '' when no substrate is registered (non-
    campaign use keeps its flat namespace). Memoized by (path, mtime): a file read + hash only when the substrate
    changes on disk; stable across a run (the vocabulary is fixed; banked lemmas don't affect `def_fingerprint`)."""
    sub = get_campaign_substrate()
    if not sub:
        return ""
    try:
        p = Path(sub)
        mt = p.stat().st_mtime
        cached = _SUBSTRATE_FP_CACHE.get(sub)
        if cached and cached[0] == mt:
            return cached[1]
        from ztare.leanmill.lean_source import def_fingerprint as _dfp
        fp = _dfp(p.read_text(encoding="utf-8", errors="replace"))
        _SUBSTRATE_FP_CACHE[sub] = (mt, fp)
        return fp
    except Exception:  # noqa: BLE001 — fingerprint is best-effort; '' ⇒ flat namespace (never breaks reuse)
        return ""


_CAMPAIGN_NS_CACHE: "dict" = {}   # substrate path -> (mtime, [unique top-level namespaces])


def campaign_namespaces() -> "list[str]":
    """Unique top-level `namespace X` names declared in the ACTIVE campaign substrate theory. A campaign theory
    typically wraps ALL its decls in one namespace (`namespace P1N1RungA … end P1N1RungA`, repeated); the
    pre-elaborated env from `campaign_file_env` has that namespace CLOSED (each `end`), so a verify probe that
    references namespaced sibling defs UNQUALIFIED is `unknown identifier` ⇒ the rung can never close (the
    2026-06-20 'no closures' RCA). The verify seam re-enters this namespace so names resolve as in-file.
    Returns [] when no substrate / unreadable. Cached by (path, mtime)."""
    cs = get_campaign_substrate()
    if not cs:
        return []
    try:
        p = Path(cs)
        mt = p.stat().st_mtime
    except Exception:  # noqa: BLE001
        return []
    hit = _CAMPAIGN_NS_CACHE.get(cs)
    if hit and hit[0] == mt:
        return hit[1]
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return []
    import re as _re_ns
    ns: "list[str]" = []
    for m in _re_ns.finditer(r"(?m)^\s*namespace\s+([A-Za-z_][\w.]*)", src):
        if m.group(1) not in ns:
            ns.append(m.group(1))
    _CAMPAIGN_NS_CACHE[cs] = (mt, ns)
    return ns


_CAMPAIGN_VAR_CACHE: "dict" = {}   # substrate path -> (mtime, [section `variable` lines])


def campaign_variables() -> "list[str]":
    """The `variable …` context the ACTIVE campaign substrate declares (see lean_source.section_variable_lines):
    the type/instance binders that section-scoping drops on `end`, so a warm-verify probe that only re-enters the
    namespace still can't synthesize them (`synthInstanceFailed`) unless they are re-declared — the 2026-07-02
    median-voter 'can't ratify a section-style target' RCA. Cached by (path, mtime), mirroring campaign_namespaces.
    `[]` when no substrate / unreadable / flat theory (⇒ no re-declaration ⇒ byte-parity for prior campaigns)."""
    cs = get_campaign_substrate()
    if not cs:
        return []
    try:
        p = Path(cs)
        mt = p.stat().st_mtime
    except Exception:  # noqa: BLE001
        return []
    hit = _CAMPAIGN_VAR_CACHE.get(cs)
    if hit and hit[0] == mt:
        return hit[1]
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return []
    from ztare.leanmill.lean_source import section_variable_lines
    vs = section_variable_lines(src)
    _CAMPAIGN_VAR_CACHE[cs] = (mt, vs)
    return vs


_CAMPAIGN_OPEN_CACHE: "dict" = {}   # substrate path -> (mtime, [distinct top-level `open …` lines])


def campaign_open_lines() -> "list[str]":
    """The distinct top-level `open …` statements the ACTIVE campaign substrate uses to bring its
    (possibly NESTED-namespace) defs into UNQUALIFIED scope for its own work-item theorems. RCA 2026-07-05
    (CLOB native_hammer 0/69): the substrate's types live in `namespace LimitOrderBookV3` (+ nested `Side`),
    reachable only via `open LimitOrderBookV3`; but every such `open` sits INSIDE a `section … end` (the
    family-lemma-library banked rungs each wrap their own section), and the file's LAST line is `end`, so a
    COLD probe appended after the substrate lands OUTSIDE every open → `Book`/`Order` read as unknown →
    `autoImplicit` mangles them to `?m.2` → the whole native-hammer/conjecture cold cascade is dead on any
    nested-namespace theory (the `len(ns)==1` single-namespace fixes never covered this shape). Re-emitting
    these exact lines before the probe body restores EXACTLY the scope the substrate's own theorems compile
    under. Cached by (path, mtime). `[]` when no substrate / a flat theory that uses no `open` (⇒ the caller
    keeps its single-namespace re-entry path ⇒ byte-parity for every prior campaign)."""
    cs = get_campaign_substrate()
    if not cs:
        return []
    try:
        p = Path(cs)
        mt = p.stat().st_mtime
    except Exception:  # noqa: BLE001
        return []
    hit = _CAMPAIGN_OPEN_CACHE.get(cs)
    if hit and hit[0] == mt:
        return hit[1]
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return []
    import re as _re_op
    opens: "list[str]" = []
    # per-line ([ \t], not \s) so `open A` / `open B` on separate lines are DISTINCT matches and the capture
    # can never cross a newline into an unrelated statement (a plain `open Foo` or `open Foo Bar` line only).
    for m in _re_op.finditer(r"(?m)^[ \t]*(open[ \t]+[A-Za-z_][\w.]*(?:[ \t]+[A-Za-z_][\w.]*)*)[ \t]*$", src):
        ln = m.group(1).strip()
        if ln not in opens:
            opens.append(ln)
    _CAMPAIGN_OPEN_CACHE[cs] = (mt, opens)
    return opens


def campaign_scope_prefix(body: str = "") -> "Optional[str]":
    """THE single door BOTH cold-compile probe assemblers (native_hammer `_native_campaign_context`,
    conjecture `_campaign_probe`) share to re-establish the campaign substrate's name-resolution scope for a
    `body` appended after the substrate SOURCE — so neither can silently drift blind on a nested-namespace /
    `open`-style theory again (CLOB, 2026-07-05). Returns the `open …` + section-`variable …` prefix to emit
    directly before the body, or None when the substrate uses NO top-level `open` (⇒ a flat single-namespace
    theory ⇒ the caller keeps its existing `namespace ns … end ns` re-entry, byte-parity for prior campaigns).
    Section `variable` lines are injected ONLY when the body declares none of its own (a self-contained probe
    already has one consistent set; a second `{…}` at a fresh universe → `sort Type (max …)`, the EF1 v5
    regression — the SAME rule as assemble_campaign_probe, the warm-env twin of this cold door)."""
    if not get_campaign_substrate():
        return None
    opens = campaign_open_lines()
    if not opens:
        # NAMESPACE-style substrate (gale-Shapley, 2026-07-06): the theory lives inside `namespace X` and the file
        # NEVER emits a top-level `open X` (its own theorems sit inside X), so a body appended after the substrate's
        # `end X` — or a self-contained probe's defs hoisted to top level — reads X's members as `unknown
        # identifier`. Synthesize `open X` for each campaign namespace so this ONE door covers BOTH the open-style
        # (CLOB, nested `open`s) and the namespace-style shapes. A truly flat theory declares no namespace ⇒
        # `campaign_namespaces()` is [] ⇒ opens stays [] ⇒ None below ⇒ byte-parity for every prior flat campaign.
        opens = [f"open {ns}" for ns in campaign_namespaces()]
    if not opens:
        return None
    try:
        from ztare.leanmill.lean_source import section_variable_lines
        has_own = bool(section_variable_lines(body))
    except Exception:  # noqa: BLE001
        has_own = False
    vlines = [] if has_own else campaign_variables()
    parts = opens + vlines
    return ("\n".join(parts) + "\n") if parts else None


def assemble_cold_probe(warm_source: str, body: str = "", *, keep: str = "") -> "Optional[str]":
    """THE single door BOTH cold-probe assemblers use — native_hammer (`solver_core._native_campaign_context`)
    and conjecture-advance (`conjecture._campaign_probe`) — to build a cold compile probe that carries the
    campaign substrate PLUS any WARM-ONLY defs `warm_source` declares that the substrate never banked (an inline
    `inductive ProposalRun`, whose home is the warm/self-contained world — the source of truth for it). Returns
    `substrate + open/namespace scope + warm-only-defs + body`, or None off-campaign (no substrate ⇒ the caller
    keeps its flat fallback). CONSOLIDATION (2026-07-06 gale): this was TWO sibling copies, and the drift left the
    conjecture-advance path blind on `ProposalRun` (a FALSE `no_advance` thrash) after native_hammer was fixed —
    exactly the forgotten-sibling class this file keeps hitting, so now there is ONE door. `keep` = a decl name to
    retain even when the substrate also declares it (native_hammer keeps its target). Empty/off-campaign ⇒ byte-parity."""
    sub = get_campaign_substrate()
    if not sub or not Path(sub).exists():
        return None
    from ztare.leanmill.lean_source import strip_scope_commands, strip_env_declared_decls
    import re as _re
    subtext = Path(sub).read_text(encoding="utf-8", errors="replace").rstrip()
    body = strip_scope_commands(body or "")
    extra = ""
    if (warm_source or "").strip():
        _e = strip_scope_commands(strip_env_declared_decls(warm_source, subtext, keep=keep))
        _e = _re.sub(r"\A\s*import\s+Mathlib\s*\n+", "", _e).strip()
        extra = (_e + "\n\n") if _e else ""
    _scope = campaign_scope_prefix(body or extra)
    if _scope is not None:
        return (f"{subtext}\n\n{_scope.rstrip()}\n{extra}{body}").rstrip() + "\n"
    ns = campaign_namespaces()
    if len(ns) == 1:
        vb = "".join(v + "\n" for v in campaign_variables())
        return f"{subtext}\n\nnamespace {ns[0]}\n{vb}{extra}{body}\nend {ns[0]}\n"
    return None


def assemble_campaign_probe(code: str, ns: str, campaign_vars: "list[str]") -> str:
    """Wrap a probe body in the campaign's ONE namespace + variable context, normalizing scoping so a probe's OWN
    (possibly mis-nested) scope markers can't reject it and its OWN binders aren't duplicated. THE assembly for
    warm-verify — pure + REPL-free so its invariants are metamorphically testable (`_selftest_assemble`). Three
    RCA-hardened, general rules:
      • strip the probe's top-level namespace/section/end — a probe shown a `namespace X` + named `section Y`
        theory copies+mis-nests them (`end X` while `section Y` open) → an `end`-mismatch that rejects a VALID
        proof (EF1 round-robin, 2026-07-03);
      • inject the substrate's `variable` lines ONLY if the probe declares NONE of its own — a self-contained probe
        already has ONE consistent set; re-prepending them adds a SECOND `{Agent Item K}` at a fresh universe →
        `Application type mismatch … sort Type (max …)` (the v5 regression). A bare probe still inherits them
        (the 2026-07-02 synthInstance case);
      • re-enter exactly one `namespace ns … end ns` so namespaced siblings resolve (the 2026-06-20 'no closures')."""
    from ztare.leanmill.lean_source import strip_scope_commands, section_variable_lines
    code = strip_scope_commands(code)
    has_vars = bool(section_variable_lines(code))   # comment-safe (a `-- variable …` line is NOT a binder command)
    vblock = "" if has_vars else "".join(v + "\n" for v in campaign_vars)
    return f"namespace {ns}\n{vblock}{code}\nend {ns}\n"


def _selftest_assemble() -> None:
    """METAMORPHIC guard for assemble_campaign_probe — asserts the invariants each EF1 scope/universe bug violated
    (2026-07-03), so the class cannot recur. Pure (no REPL)."""
    from ztare.leanmill.lean_source import strip_scope_commands as _ssc
    _VARS = ["variable {Agent Item K : Type*}", "variable [Field K] [LinearOrder K]"]
    # a self-contained probe that ALSO mis-nests its scopes (the RoundRobin shape) + declares its own binders
    _selfc = ("namespace EF1Allocation\nvariable {Agent Item K : Type*}\nvariable [Field K] [LinearOrder K]\n"
              "section OrderedField\ntheorem EnvyFree.T (profile : Agent -> K) : True := trivial\nend EF1Allocation")
    _bare = "theorem T : True := trivial"
    _a = assemble_campaign_probe(_selfc, "EF1Allocation", _VARS)
    _b = assemble_campaign_probe(_bare, "EF1Allocation", _VARS)
    for _out in (_a, _b):   # (1) balanced single namespace; the probe's own scope markers (incl mis-nested section) gone
        assert _out.count("namespace EF1Allocation") == 1 and _out.count("\nend EF1Allocation\n") == 1, _out
        assert "section" not in _out and "end OrderedField" not in _out, "probe's mis-nested scope survived → end-mismatch"
    assert _a.count("variable {Agent Item K") == 1, "duplicate base binder → universe mismatch"   # (2)
    assert "variable {Agent Item K" in _b and "variable [Field K]" in _b, "bare probe lost the section context"  # (3)
    assert _ssc(_ssc(_selfc)) == _ssc(_selfc)                                                       # (4) idempotent
    assert "-- namespace Foo" in _ssc("-- namespace Foo\ntheorem T : True := trivial")             #     comment-safe
    _cmt = assemble_campaign_probe("-- variable {Bogus}\ntheorem T : True := trivial", "EF1Allocation", _VARS)
    assert "variable {Agent Item K" in _cmt, "a commented `variable` must NOT suppress substrate binders"  # (5)
    print("assemble_campaign_probe metamorphic selftest ok")


def _warm_check_audit(pl, project: str, code: str, decl_name: str, verify_env, timeout: int
                      ) -> "Optional[tuple[bool, str]]":
    """Compile `code` in the REPL against `verify_env` (None = frozen base Mathlib; an int = a pre-elaborated
    campaign env), then `#print axioms` the proved decl in the RESULTING env and enforce the allowlist. The SOUND
    core shared by BOTH warm-verify routes — a `sorry` or a non-allowlisted axiom is REJECTED exactly as the cold
    governance audit would; a mis-qualified/empty verdict FAILS CLOSED. Returns (ok, diag), or None when the REPL
    is unusable / the env was invalidated (⇒ caller falls back). The warm env amortizes elaboration; it never
    relaxes the audit (the no-false-closure invariant holds on the fast path)."""
    try:
        r = pl.check(code, timeout=min(timeout, _warm_ceiling()), env=verify_env)
    except Exception:  # noqa: BLE001
        _drop_repl(project)
        return None
    if not isinstance(r, dict) or "errors" not in r:
        return None
    if verify_env is not None and "env_invalidated" in str(r.get("output", "")):
        _FILE_ENV_CACHE.clear()
        return None
    errs = r.get("errors") or []
    sorries = r.get("sorries") or []
    if errs or sorries:                       # compile error or a `sorry` in the probe ⇒ not closed
        toks = [*errs, *([f"sorry@{s}" for s in sorries] if sorries else [])]
        return (False, ("repl(campaign): " + " | ".join(str(t) for t in toks))[:800] or "repl: error")
    audit_env = r.get("env")                  # the probe added `decl_name` to a NEW env; audit ITS axioms there
    if audit_env is None:
        return None
    try:
        ax = pl.check(f"#print axioms {decl_name}", timeout=min(timeout, _warm_ceiling()), env=audit_env)
    except Exception:  # noqa: BLE001
        _drop_repl(project)
        return None
    raw = str((ax or {}).get("raw", "")) if isinstance(ax, dict) else ""
    # FAIL-CLOSED: the audit MUST produce a recognizable `#print axioms` verdict; empty/unknown ⇒ NOT clean.
    if "axioms" not in raw:
        return (False, f"repl(campaign): AXIOM AUDIT INCONCLUSIVE for {decl_name} (no verdict) — fail-closed")
    if "sorryAx" in raw or "sorry" in raw.lower():
        return (False, f"repl(campaign): AXIOM AUDIT REJECT — sorryAx in {decl_name} (laundered sorried decl)")
    import re as _re2
    cited = _re2.findall(r"[A-Za-z_][\w.]*", raw.split("depends on axioms", 1)[-1]) if "axioms" in raw else []
    bad = [a for a in cited if a not in _ALLOWED_AXIOMS and a not in ("the", "decl", "no", "and", decl_name)
           and ("." in a or a[:1].isupper() or a.endswith("Ax"))]
    if any(b.endswith("Ax") or b in ("Lean.ofReduceBool", "Lean.trustCompiler") for b in bad):
        return (False, f"repl(campaign): AXIOM AUDIT REJECT — non-allowlisted axiom in {decl_name}: {bad}")
    return (True, "repl(campaign): clean (compiled + axioms ⊆ allowlist)")


def warm_verify_campaign(probe_code: str, decl_name: str, sandbox, timeout: int = 120, *,
                         env: "Optional[int]" = None) -> "Optional[tuple[bool, str]]":
    """SOUND warm verify of a campaign-theory proof against a pre-elaborated env: (1) the probe must compile
    with NO error and NO `sorry` in the probe itself, AND (2) the proved decl's `#print axioms` (run against
    the env AFTER the probe is added) must be ⊆ {propext, Classical.choice, Quot.sound} — so a proof that
    LAUNDERS by citing a still-`sorry` decl live in the env (e.g. `exact <sorried_target>`) carries `sorryAx`
    and is REJECTED here, exactly as the cold governance audit would. Returns (ok, diag) or None (REPL not
    usable ⇒ caller falls back to the cold path). This keeps the no-false-closure invariant on the fast path —
    the warm env amortizes elaboration, it does NOT relax the audit."""
    if not _flag_on():
        return None
    # NOTE: `env is None` is NOT an early-out anymore (2026-07-06, the gale substrate-death → lost-proof RCA). A
    # SELF-CONTAINED probe verifies against BASE Mathlib (Path A, env=None internally) and needs NOTHING from the
    # campaign env — so when the substrate is momentarily dead (`campaign_file_env` → None → env None) a valid
    # self-contained proof MUST still be confirmable, not silently dropped to the cold path (which then also fails
    # on the dead substrate) and recorded as a decompose-gap. Only the CITING path (Path B) needs the env; the
    # `env is None` guard moved down to just before it.
    project = str(Path(sandbox).resolve())
    if not _toolchain_ok(project):
        return None
    pl = _get_repl(project)
    if pl is None:
        return None
    code = _strip_prelude_for_repl(probe_code)
    # ROUTE BY PROBE TYPE (RCA 2026-07-03 — EF1 v4→v7 universe FALSE-REJECT). A probe is one of two shapes:
    #   • SELF-CONTAINED — re-declares the campaign defs/structures + the target itself (the formalizer's usual
    #     output). It needs NOTHING from the substrate env. Verifying it AGAINST that env forces its re-stated,
    #     universe-POLYMORPHIC signature (`variable {Agent Item K : Type*}` → `profile : Agent → Valuation Item K`)
    #     to unify with the env's ALREADY-elaborated defs, manufacturing a spurious
    #     `Application type mismatch … sort Type (max …)` that rejects a proof which compiles PERFECTLY standalone
    #     (verified: EXIT 0 under `lake env lean`). Cure: verify it against the FROZEN BASE Mathlib env (env=None) —
    #     the SAME base the cold path uses, so byte-identical soundness, but warm (no ~100s Mathlib re-import) and
    #     free of the substrate-env interaction. No strip / no rename / no rewrap — the probe is already well-formed.
    #   • CITING — references env decls without re-declaring them. It NEEDS the substrate env + the dedup/rename/
    #     namespace re-entry (the chronic 'already been declared' 2026-07-01 + 'no closures' 2026-06-20 fixes — the
    #     good reason the strip exists). Detected precisely: does stripping env-held decls CHANGE the probe?
    _envtext = ""
    try:
        _subp = get_campaign_substrate()
        _envtext = Path(_subp).read_text(encoding="utf-8", errors="replace") if _subp else ""
    except Exception:  # noqa: BLE001
        _envtext = ""
    _self_contained = False
    _strip_changed = False
    if _envtext:
        try:
            from ztare.leanmill.lean_source import strip_env_declared_decls
            _strip_changed = (strip_env_declared_decls(code, _envtext, keep=decl_name) != code)
            _self_contained = _strip_changed
        except Exception:  # noqa: BLE001
            _self_contained = False
    _ns = campaign_namespaces()
    _qual = (lambda dn: f"{_ns[0]}.{dn}" if (len(_ns) == 1 and not dn.startswith(f"{_ns[0]}.")) else dn)

    def _probe_decl_name(code_text: str, dn: str) -> str:
        """Name of `dn` as declared in this probe. Self-contained probes can use their own namespace; do not
        audit them under the campaign namespace."""
        try:
            from ztare.leanmill.solver.statement_integrity import decl_blocks as _db
            names = [n for n, _b in _db(code_text or "")]
            for n in names:
                if n == dn:
                    return n
            for n in names:
                if str(n).endswith("." + dn):
                    return n
        except Exception:  # noqa: BLE001
            pass
        return dn

    _probe_dn = _probe_decl_name(code, decl_name)
    _trace_base = {
        "kind": "warm_verify_campaign",
        "target": decl_name,
        "project": project,
        "env_available": env is not None,
        "substrate_available": bool(_envtext),
        "envtext_len": len(_envtext),
        "self_contained": _self_contained,
        "strip_changed": _strip_changed,
        "probe_decl": _probe_dn,
    }

    # PATH A — self-contained ⇒ base Mathlib env, probe VERBATIM (audit the decl name as it appears in the
    # probe, since self-contained probes may live in a probe namespace). A CLEAN close here is authoritative (== the cold standalone that
    # passes). Anything else (real error / laundering / a rare probe that ALSO cites a substrate-only rung) falls
    # through to the substrate path, which re-audits and is the sound backstop for sorry/axiom laundering.
    if _self_contained:
        _v = _warm_check_audit(pl, project, code, _probe_dn, None, timeout)
        _emit_verify_trace(project, {
            **_trace_base,
            "path": "self_contained_base",
            "result": None if _v is None else bool(_v[0]),
            "diag": None if _v is None else str(_v[1])[:500],
        })
        if _v is not None and _v[0]:
            return _v

    # PATH B needs the campaign env; when it is unavailable (substrate dead / not yet elaborated) a CITING probe
    # cannot be warm-verified here — fall back to the cold path. (A self-contained probe already had its
    # authoritative Path A shot above, so a dead substrate never discards it — the gale lost-proof fix.)
    if env is None:
        _emit_verify_trace(project, {**_trace_base, "path": "campaign_env", "result": None,
                                    "diag": "skipped: env unavailable"})
        return None
    # PATH B — citing (or a self-contained probe that did not cleanly verify on base): substrate env + dedup +
    # fresh-name + namespace re-entry, exactly as before. THIS is the one door every warm-verify caller inherits.
    if _envtext:
        try:
            from ztare.leanmill.lean_source import strip_env_declared_decls, rename_decl
            code = strip_env_declared_decls(code, _envtext, keep=decl_name)
            if decl_name and (f" {decl_name}" in code):   # fresh-name the target (env holds it SORRIED; mirrors _zwv)
                _fresh = f"{decl_name}_wv"
                _renamed = rename_decl(code, decl_name, _fresh)
                if _renamed != code:
                    code = _renamed
                    decl_name = _fresh
        except Exception:  # noqa: BLE001 — dedup/rename is best-effort; the cold path is the sound fallback
            pass
    if len(_ns) == 1:                                  # re-enter the campaign namespace so sibling names resolve
        code = assemble_campaign_probe(code, _ns[0], campaign_variables())
    decl_name = _qual(decl_name)
    _v = _warm_check_audit(pl, project, code, decl_name, env, timeout)
    _emit_verify_trace(project, {
        **_trace_base,
        "path": "campaign_env",
        "campaign_decl": decl_name,
        "result": None if _v is None else bool(_v[0]),
        "diag": None if _v is None else str(_v[1])[:500],
    })
    return _v


def axioms_raw_via_repl(lean_source: str, target_name: str, sandbox, timeout: int = 180) -> "Optional[str]":
    """Warm fast path for the GOVERNANCE #print-axioms audit (`gates.lean_compile_primitives.audit_axioms_subset`).
    Elaborate `lean_source` (the closure source carrying the target decl + a `#print axioms <target_name>`
    directive) against the warm FROZEN base-Mathlib env and return the RAW REPL output — the
    `'<name>' depends on axioms: [...]` lines — for the CALLER to parse with the SAME `parse_axiom_output` it
    uses for the cold path. So the soundness gate is byte-IDENTICAL; the warm env only amortizes the ~100s+
    Mathlib re-import that the cold `lake env lean` pays on EVERY closure audit (the recurring verify-starvation
    bug — #66 warm-routed `_compile_probe` but this audit leg was missed).

    Returns None ⇒ caller MUST fall back to `lake env lean`: when the REPL is off / toolchain-mismatched / dead,
    or the probe does not compile cleanly (a real `error:` — let the authoritative cold path decide; fail-open).
    A `sorry` in the probe is NOT an error here — that is exactly the laundering `#print axioms` must expose as
    `sorryAx`, which the caller's allowlist check then REJECTS. Base env (env=None) so a self-contained source
    that inlines the campaign theory still pays only the theory elaboration, never the Mathlib import."""
    if not _flag_on():
        return None
    project = str(Path(sandbox).resolve())
    if not _toolchain_ok(project):           # drift guard: a mismatched REPL is silently-empty → never trust it
        return None
    pl = _get_repl(project)
    if pl is None:
        return None
    src = lean_source if f"#print axioms {target_name}" in (lean_source or "") else (
        (lean_source or "").rstrip() + f"\n#print axioms {target_name}\n")
    code = _strip_prelude_for_repl(src)   # the base env already has Mathlib (+Aesop/Batteries)
    if not code.strip():
        return None
    try:
        r = pl.check(code, timeout=min(timeout, _warm_ceiling()), env=None)   # frozen base Mathlib env
    except Exception:  # noqa: BLE001 — wedged/crashed command: drop + respawn next call, fall back this one
        _drop_repl(project)
        return None
    if not isinstance(r, dict) or "errors" not in r:
        return None
    if r.get("errors"):                      # a real compile error ⇒ inconclusive; cold path is authoritative
        return None
    raw = str(r.get("raw", "") or r.get("output", ""))
    # only hand back output that actually carries the #print-axioms verdict (else the caller sees "no line for
    # target" ⇒ inconclusive ⇒ cold fallback — same fail-open as the cold path when the directive produced nothing).
    return raw if ("depends on axioms" in raw or "does not depend on any axioms" in raw) else None


_TYPE_HASH_RE = re.compile(r"ZTARE_TYPE_HASH:(\d+)")

# Erase binder NAMES (so `∀ x` ≡ `∀ y`) + strip mdata, then take Lean's structural `Expr.hash` of the target's
# TYPE. The kernel stores bound-variable OCCURRENCES as de Bruijn indices, so this single hash is invariant under
# α-renaming AND ∀-fronting (`(h : H) : Q` and `: ∀ h : H, Q` have the SAME forall-type) — the equivalences NO text
# regex can collapse (the 2026-06-24 cache-never-hits RCA). `Expr.hash`/`==` are binder-NAME-sensitive by default
# (that is `Expr.equal`; `Expr.eqv` is the α one), so we normalise the names first. The marker is our OWN line, not
# Lean source, so parsing it with a tiny regex is fine. Verified: ∀-fronting + α variants → identical hash.
_TYPE_HASH_SNIPPET = (
    "\nopen Lean in\n"
    "partial def ztareErase : Expr → Expr\n"
    "  | .forallE _ d b bi => .forallE `x (ztareErase d) (ztareErase b) bi\n"
    "  | .lam _ d b bi => .lam `x (ztareErase d) (ztareErase b) bi\n"
    "  | .letE _ t v b nd => .letE `x (ztareErase t) (ztareErase v) (ztareErase b) nd\n"
    "  | .app f a => .app (ztareErase f) (ztareErase a)\n"
    "  | .mdata _ e => ztareErase e\n"
    "  | .proj n i e => .proj n i (ztareErase e)\n"
    "  | e => e\n"
    "open Lean Elab Command in\n"
    "#eval liftTermElabM do\n"
    # NAMESPACE-ROBUST resolution (RCA 2026-07-04): the bare `find? `{target}` MISSED a namespaced decl — the
    # EF1 stub wraps the theorem in `namespace FormalizeProbe`, so the real name is `FormalizeProbe.iso_lemma2`
    # and `find? `iso_lemma2` returned NONE ⇒ the α/∀-invariant KEY silently degraded to a brittle text key ⇒
    # the checkpoint NEVER resumed ⇒ codex re-derived a 400-line proof from scratch every attempt, starving 2
    # errors from done, for 9h. Fix: exact name first, else the FILE-LOCAL decl (`constants.map₂` — the stub's
    # OWN decls, a handful, NOT the imported Mathlib) whose short name matches. Cheap + correct (the target's
    # short name is unique among the stub's decls; a fresh base env holds no rival banked `X.iso_lemma2`).
    "  let env ← getEnv\n"
    "  let tgt := `{target}\n"
    "  let want := \".\" ++ tgt.toString\n"
    "  let ci? : Option ConstantInfo := match env.find? tgt with\n"
    "    | some ci => some ci\n"
    "    | none =>\n"
    "        let hits := env.constants.map₂.toList.filter (fun p =>\n"
    "          (p.1 == tgt || p.1.toString.endsWith want) && !p.1.isInternal)\n"
    "        hits.reverse.head?.map (·.2)\n"
    "  match ci? with\n"
    "  | some ci => IO.println s!\"ZTARE_TYPE_HASH:{{(ztareErase ci.type).hash}}\"\n"
    "  | none => IO.println \"ZTARE_TYPE_HASH:NONE\"\n"
)


def canonical_type_hash_via_repl(lean_source: str, target_name: str, sandbox, timeout: int = 120,
                                 *, env: "Optional[int]" = None) -> "Optional[str]":
    """Canonical, α-/∀-fronting-invariant KEY for a theorem statement: the kernel `Expr.hash` of the target decl's
    binder-name-erased TYPE, computed by elaborating `lean_source` against the warm REPL (a byproduct of the verify
    the caller already runs — the economics-safe source, never a dedicated equivalence call). This is the principled
    replacement for text-regex statement normalisation in the proof cache (which mis-keyed multi-decl probes on
    their leading `def`'s `:=` and could not collapse ∀-fronting). Returns the hash as a decimal string, or None ⇒
    caller falls back to the text key (`proof_cache.normalize_statement`): when the REPL is off / toolchain-
    mismatched / dead, the probe does not elaborate, or the target decl is absent. SOUND regardless of key quality —
    a proof-cache hit is ALWAYS re-verified in-context before it can close anything, so the key only needs RECALL."""
    if not _flag_on() or not (target_name or "").strip():
        return None
    project = str(Path(sandbox).resolve())
    if not _toolchain_ok(project):
        return None
    pl = _get_repl(project)
    if pl is None:
        return None
    code = _strip_prelude_for_repl((lean_source or "")) + _TYPE_HASH_SNIPPET.format(target=target_name)
    if not code.strip():
        return None
    try:
        r = pl.check(code, timeout=min(timeout, _warm_ceiling()), env=env)
    except Exception:  # noqa: BLE001 — wedged/crashed command: drop + respawn next call, fall back this one
        _drop_repl(project)
        return None
    if not isinstance(r, dict) or r.get("errors"):   # a real elaboration error ⇒ inconclusive; text-key fallback
        return None
    m = _TYPE_HASH_RE.search(str(r.get("raw", "") or r.get("output", "")))
    return m.group(1) if m else None


@atexit.register
def _cleanup() -> None:
    for project in list(_REPL_CACHE):
        _drop_repl(project)


def _selftest() -> int:
    fails = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    # explicit OFF (=0) ⇒ always None (caller uses lake env lean) — the revert path. (Default is now ON, so we
    # set =0 here rather than unset, and avoid starting a real REPL in the unit test.)
    os.environ["ZTARE_LEANMILL_REPL_COMPILE"] = "0"
    ok("flag=0 ⇒ None (explicit revert to the cold lake path)",
       compile_probe_via_repl("import Mathlib\n\ntheorem t : True := trivial", "ztare_proofs") is None)
    # the import-strip (the prelude already has Mathlib)
    stripped = _IMPORT_MATHLIB_RE.sub("", "import Mathlib\n\ntheorem t : True := trivial").lstrip("\n")
    ok("strips the leading import Mathlib", "import Mathlib" not in stripped and "theorem t" in stripped)
    # flag-on but a non-existent / non-matching sandbox ⇒ None (fall back), never crashes
    os.environ["ZTARE_LEANMILL_REPL_COMPILE"] = "1"
    ok("flag-on + bogus sandbox ⇒ None (toolchain gate, no crash)",
       compile_probe_via_repl("theorem t : True := trivial", "/nonexistent/_bogus_root") is None)
    os.environ.pop("ZTARE_LEANMILL_REPL_COMPILE", None)
    # METAMORPHIC: the campaign-probe assembly invariants (scope-balanced, single binder set, bare-gets-vars) — the
    # class the EF1 scope-mismatch + universe-mismatch bugs violated (2026-07-03). Pure, no REPL.
    try:
        _selftest_assemble()
        ok("assemble_campaign_probe metamorphic invariants hold", True)
    except AssertionError as _e:  # noqa: BLE001
        ok(f"assemble_campaign_probe metamorphic FAILED: {_e}", False)
    # ROUTING GATE (RCA 2026-07-03): warm_verify_campaign routes SELF-CONTAINED probes to the base env and CITING
    # probes to the substrate env; the decision variable is "does stripping env-held decls CHANGE the probe?".
    # Guard that classifier so the universe-false-reject class cannot silently return (a self-contained probe
    # mis-classed as citing → substrate env → the EF1 v4→v7 `sort Type (max …)` false-reject).
    try:
        from ztare.leanmill.lean_source import strip_env_declared_decls as _seld
        _env = ("namespace X\nstructure Valuation (Item K : Type*) where value : Item -> K\n"
                "theorem lem : True := trivial\nend X")
        _selfc = "structure Valuation (Item K : Type*) where value : Item -> K\ntheorem T : True := trivial"
        _cit = "theorem T : True := by have := lem; trivial"
        ok("self-contained probe (re-declares env def) ⇒ routes to BASE env", _seld(_selfc, _env, keep="T") != _selfc)
        ok("citing probe (no env-held decls) ⇒ routes to SUBSTRATE env", _seld(_cit, _env, keep="T") == _cit)
    except Exception as _e:  # noqa: BLE001
        ok(f"warm-verify routing classifier FAILED: {_e}", False)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
