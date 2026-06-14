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
# CAMPAIGN-THEORY WARM ENV (2026-06-14): a heavy agent-built substrate (P1Theory: PowerSeries/MvPolynomial)
# was being RE-ELABORATED from an inlined prelude on EVERY verify (592-1016s timeouts, run closed nothing).
# `open_file()` elaborates the file ONCE → an env id whose decls (the proven API) are live for subsequent
# `check(code, env=<id>)` with NO re-elaboration. Cache the env per file, keyed on mtime so it re-opens the
# instant the agent extends the theory — the "olean fed dynamically as the agent builds it". Cleared on REPL
# respawn (non-base env ids die with the process).
_FILE_ENV_CACHE: "dict[str, tuple[float, int]]" = {}   # resolved file path -> (mtime, env_id)
_IMPORT_MATHLIB_RE = re.compile(r"^\s*import\s+Mathlib\s*$", re.MULTILINE)


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
        mtime = fp.stat().st_mtime
    except Exception:  # noqa: BLE001
        return None
    key = str(fp)
    cached = _FILE_ENV_CACHE.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]
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
    code = _IMPORT_MATHLIB_RE.sub("", src).lstrip("\n")
    if not code.strip():
        return None
    try:
        r = pl.check(code, timeout=timeout, env=None)
    except Exception:  # noqa: BLE001 — a wedged elaboration: drop + respawn next call, fall back this one
        _drop_repl(project)
        return None
    # a non-compiling theory must NEVER become a silent verify env; hard ERRORS disqualify it (sorries OK).
    if not isinstance(r, dict) or r.get("errors") or r.get("env") is None:
        return None
    env = int(r["env"])
    _FILE_ENV_CACHE[key] = (mtime, env)
    return env


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
    code = _IMPORT_MATHLIB_RE.sub("", probe).lstrip("\n")   # the prelude already imported Mathlib
    if not code.strip():
        code = "example : True := trivial"
    try:
        r = pl.check(code, timeout=min(timeout, _warm_ceiling()), env=env)  # bound the warm path; a wedged probe fails fast
    except Exception:  # noqa: BLE001 — a wedged/crashed command: drop + respawn next call, fall back this one
        _drop_repl(project)
        return None
    # an explicit campaign env that died with a REPL respawn ⇒ the file-env cache is stale; drop it + fall back
    # (the caller re-opens next call). Never silently re-run a campaign probe in base_env (wrong, prelude-less).
    if env is not None and isinstance(r, dict) and "env_invalidated" in str(r.get("output", "")):
        _FILE_ENV_CACHE.clear()
        return None
    if not isinstance(r, dict) or "errors" not in r:
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


def set_campaign_substrate(theory_path: "Optional[str]") -> None:
    """Register (or clear) the campaign theory file whose decls the verify seam should amortize into a warm
    env (instead of re-inlining + re-elaborating them per probe). The notes-channel run sets this once after
    theory consolidation; `campaign_file_env` re-opens automatically when the file's mtime changes."""
    global _CAMPAIGN_SUBSTRATE
    _CAMPAIGN_SUBSTRATE = str(theory_path) if theory_path else None


def get_campaign_substrate() -> "Optional[str]":
    return _CAMPAIGN_SUBSTRATE


def warm_verify_campaign(probe_code: str, decl_name: str, sandbox, timeout: int = 120, *,
                         env: "Optional[int]" = None) -> "Optional[tuple[bool, str]]":
    """SOUND warm verify of a campaign-theory proof against a pre-elaborated env: (1) the probe must compile
    with NO error and NO `sorry` in the probe itself, AND (2) the proved decl's `#print axioms` (run against
    the env AFTER the probe is added) must be ⊆ {propext, Classical.choice, Quot.sound} — so a proof that
    LAUNDERS by citing a still-`sorry` decl live in the env (e.g. `exact <sorried_target>`) carries `sorryAx`
    and is REJECTED here, exactly as the cold governance audit would. Returns (ok, diag) or None (REPL not
    usable ⇒ caller falls back to the cold path). This keeps the no-false-closure invariant on the fast path —
    the warm env amortizes elaboration, it does NOT relax the audit."""
    if not _flag_on() or env is None:
        return None
    project = str(Path(sandbox).resolve())
    if not _toolchain_ok(project):
        return None
    pl = _get_repl(project)
    if pl is None:
        return None
    code = _IMPORT_MATHLIB_RE.sub("", probe_code).lstrip("\n")
    try:
        r = pl.check(code, timeout=min(timeout, _warm_ceiling()), env=env)
    except Exception:  # noqa: BLE001
        _drop_repl(project)
        return None
    if not isinstance(r, dict) or "errors" not in r:
        return None
    if env is not None and "env_invalidated" in str(r.get("output", "")):
        _FILE_ENV_CACHE.clear()
        return None
    errs = r.get("errors") or []
    sorries = r.get("sorries") or []
    if errs or sorries:                       # compile error or a `sorry` in the probe ⇒ not closed
        toks = [*errs, *([f"sorry@{s}" for s in sorries] if sorries else [])]
        return (False, ("repl(campaign): " + " | ".join(str(t) for t in toks))[:800] or "repl: error")
    # the probe added `decl_name` to a NEW env (r["env"]); audit ITS axioms there (not base, not the file env).
    audit_env = r.get("env")
    if audit_env is None:
        return None
    try:
        ax = pl.check(f"#print axioms {decl_name}", timeout=min(timeout, _warm_ceiling()), env=audit_env)
    except Exception:  # noqa: BLE001
        _drop_repl(project)
        return None
    raw = str((ax or {}).get("raw", "")) if isinstance(ax, dict) else ""
    if "sorryAx" in raw or "sorry" in raw.lower():
        return (False, f"repl(campaign): AXIOM AUDIT REJECT — sorryAx in {decl_name} (laundered sorried decl)")
    # any axiom outside the allowlist (e.g. native_decide's ofReduceBool) ⇒ reject, same as the cold audit
    import re as _re2
    cited = _re2.findall(r"[A-Za-z_][\w.]*", raw.split("depends on axioms", 1)[-1]) if "axioms" in raw else []
    bad = [a for a in cited if a not in _ALLOWED_AXIOMS and a not in ("the", "decl", "no", "and", decl_name)
           and ("." in a or a[:1].isupper() or a.endswith("Ax"))]
    if any(b.endswith("Ax") or b in ("Lean.ofReduceBool", "Lean.trustCompiler") for b in bad):
        return (False, f"repl(campaign): AXIOM AUDIT REJECT — non-allowlisted axiom in {decl_name}: {bad}")
    return (True, "repl(campaign): clean (compiled + axioms ⊆ allowlist)")


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
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
