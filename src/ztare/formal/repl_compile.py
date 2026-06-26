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
    code = _strip_prelude_for_repl(src)
    if not code.strip():
        return None
    try:
        r = pl.check(code, timeout=timeout, env=None)
    except Exception:  # noqa: BLE001 — a wedged elaboration: drop + respawn next call, fall back this one
        _drop_repl(project)
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
        _errs = r.get("errors") if isinstance(r, dict) else None
        if _errs:
            print(f"⚠️  CAMPAIGN SUBSTRATE DOES NOT COMPILE: {key} — {len(_errs)} hard error(s). The "
                  f"campaign-aware verify env is DEAD ⇒ citing / warm-verify / the faithfulness oracle all "
                  f"degrade (faithful proofs may FALSE-REJECT as `target_signature_altered`). FIX THE SUBSTRATE. "
                  f"First errors:", flush=True)
            for _e in _errs[:5]:
                print(f"      {str(_e)[:200]}", flush=True)
        return None
    env = int(r["env"])
    _FILE_ENV_CACHE[key] = (mtime, env)
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
    return (True, "axiom_clean")


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


_CAMPAIGN_NS_CACHE: "dict" = {}   # substrate path -> (mtime, [unique top-level namespaces])


def campaign_namespaces() -> "list[str]":
    """Unique top-level `namespace X` names declared in the ACTIVE campaign substrate theory. A campaign theory
    typically wraps ALL its decls in one namespace (`namespace P1N1RungA … end P1N1RungA`, repeated); the
    pre-elaborated env from `campaign_file_env` has that namespace CLOSED (each `end`), so a verify probe that
    references namespaced sibling defs UNQUALIFIED is `unknown identifier` ⇒ the rung can never close (the
    2026-06-20 'no closures' RCA). The verify seam re-enters this namespace so names resolve as in-file.
    Returns [] when no substrate / unreadable. Cached by (path, mtime)."""
    cs = _CAMPAIGN_SUBSTRATE
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
    code = _strip_prelude_for_repl(probe_code)
    # NAMESPACE-CONTEXT (2026-06-20 'no closures' RCA): a campaign theory wraps its decls in `namespace X`,
    # closed in the env, so a bare probe can't resolve namespaced sibling defs (unknown identifier ⇒ unclosable).
    # Re-enter the namespace so names resolve as in-file, AND qualify decl_name (X.decl) so the axiom audit below
    # targets the ACTUAL decl — a mis-targeted audit would print nothing and (pre-2026-06-20) silently PASS.
    # Only the single-namespace case (the campaign shape) is auto-wrapped; multi-namespace ⇒ no wrap (a miss,
    # never a false pass), and an already-wrapped probe is left alone.
    _ns = campaign_namespaces()
    if len(_ns) == 1 and not code.lstrip().startswith("namespace "):
        code = f"namespace {_ns[0]}\n{code}\nend {_ns[0]}\n"
        decl_name = f"{_ns[0]}.{decl_name}"
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
    # FAIL-CLOSED: the audit MUST produce a recognizable `#print axioms` verdict ("… depends on axioms …" or
    # "… does not depend on any axioms"). An empty/unknown output (e.g. a mis-qualified decl_name, dead REPL)
    # must NOT read as clean — that would be a silent false-pass (the no-false-closure invariant). [2026-06-20]
    if "axioms" not in raw:
        return (False, f"repl(campaign): AXIOM AUDIT INCONCLUSIVE for {decl_name} (no verdict) — fail-closed")
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
    "  match (← getEnv).find? `{target} with\n"
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
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
