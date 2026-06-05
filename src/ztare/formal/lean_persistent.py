"""Persistent-process Lean REPL (import-amortized) — in-loop primitive.

Why this exists: `lean_repl.check_lean` (and every prior probe substrate)
pays `import Mathlib` (~40s) ON EVERY CALL. Empirically that repeated
import was ~the entire cost of governed proof search (a ~3h run was
almost all re-imports). This wraps the canonical
`leanprover-community/repl` binary (vendored, built at the SAME pinned
toolchain as the project's Mathlib oleans — ABI requirement) as a
long-lived process: `import Mathlib` is paid ONCE, then each probe
elaborates against the live environment in ~0.01–0.2s.

Reuse, not fork: this is a thin process manager around the upstream
REPL, not a reimplemented Lean checker. Governance signals are
preserved — `#print axioms` works in-REPL, so the kernel axiom audit
the closure gate depends on is unchanged.

Isolation: every `check()` branches from the FROZEN prelude env, so
probes never contaminate each other (no shared mutable env, no batched
span-parsing / sentinel-desync — the artifact class that caused prior
misclassification simply does not exist here).

Robustness: a hung tactic can wedge the REPL (upstream has no
per-command timeout). We enforce one at the process level — on timeout
or crash the process is killed and lazily respawned (re-paying the
one-time import on the NEXT call only). A wedged/crashed command never
returns "closed": it returns a structured failure. Fail-closed by
construction (same invariant as the batched-screener fix).

Return contract mirrors `lean_repl.check_lean` so callers can swap:
    {"success", "output", "errors", "raw", "returncode", "sorries"}
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
DEFAULT_REPL_BIN = REPO / "vendor" / "lean_repl" / ".lake" / "build" / "bin" / "repl"
DEFAULT_PRELUDE = "import Mathlib\nopen scoped ENNReal NNReal BigOperators"


class PersistentLean:
    """One long-lived `lake env repl` process pinned to `project_dir`'s
    Mathlib. Not thread-safe per instance; use one instance per worker
    (the process itself is the unit of parallelism)."""

    def __init__(
        self,
        project_dir: Path | str,
        repl_bin: Path | str | None = None,
        prelude: str = DEFAULT_PRELUDE,
        import_timeout: int = 180,
        lake_bin: Path | str | None = None,
    ) -> None:
        self.project_dir = str(Path(project_dir).expanduser().resolve())
        self.repl_bin = str(Path(repl_bin).expanduser().resolve()
                            if repl_bin else DEFAULT_REPL_BIN)
        if not Path(self.repl_bin).exists():
            raise FileNotFoundError(
                f"repl binary missing: {self.repl_bin} — build it: "
                f"(cd vendor/lean_repl && lake build)")
        self.prelude = prelude
        self.import_timeout = import_timeout
        self.lake_bin = self._resolve_lake_bin(lake_bin)
        self._p: subprocess.Popen | None = None
        self._base_env: int | None = None

    @staticmethod
    def _resolve_lake_bin(lake_bin: Path | str | None = None) -> str:
        candidates: list[str] = []
        if lake_bin:
            candidates.append(str(Path(lake_bin).expanduser()))
        if os.environ.get("ZTARE_LAKE_BIN"):
            candidates.append(os.environ["ZTARE_LAKE_BIN"])
        found = shutil.which("lake")
        if found:
            candidates.append(found)
        home = Path.home()
        candidates.extend([
            str(home / ".elan" / "bin" / "lake"),
            "/usr/local/bin/lake",
            "/opt/homebrew/bin/lake",
        ])
        for candidate in candidates:
            path = Path(candidate).expanduser()
            if path.exists() and os.access(path, os.X_OK):
                return str(path.resolve())
        return "lake"

    # -- process lifecycle -------------------------------------------------
    def _check_toolchain(self) -> tuple[str, str, bool | None]:
        """Layer-1 deterministic guard (no process): compare the repl binary's
        lean-toolchain to the project's. Returns (repl_tc, proj_tc, match) where match is
        None if either is unknown. RAISES early on a DEFINITE mismatch — far cheaper and
        clearer than discovering it via the post-import positive control."""
        try:
            from ztare.formal.substrate_liveness import toolchain_match
            ok, rtc, ptc = toolchain_match(self.repl_bin, self.project_dir)
        except Exception:
            return "", "", None
        if rtc and ptc and not ok:
            raise RuntimeError(
                f"TOOLCHAIN MISMATCH — refusing to spawn: repl binary built at {rtc!r} "
                f"but project Mathlib oleans at {ptc!r}. `import Mathlib` would silently "
                f"return an empty env (the 2026-06-01 'going blind' RCA). Rebuild the repl "
                f"at {ptc!r} or point project_dir at a {rtc!r} Mathlib build.")
        return rtc, ptc, (ok if (rtc and ptc) else None)

    def _spawn(self) -> None:
        rtc, ptc, _ = self._check_toolchain()
        t0 = time.time()
        self._p = subprocess.Popen(
            [self.lake_bin, "env", self.repl_bin],
            cwd=self.project_dir,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
            start_new_session=True,
        )
        r = self._raw_cmd({"cmd": self.prelude}, self.import_timeout)
        if r is None or "env" not in r:
            self._kill()
            raise RuntimeError(f"prelude load failed (timeout/crash): {r}")
        self._base_env = r["env"]
        self._assert_prelude_live(r)
        # observability: one liveness line per spawn — the signal that was MISSING when we
        # went blind (a 0.8s import with Mathlib prelude is the dead-env signature).
        if os.environ.get("ZTARE_LEAN_QUIET") != "1":
            import sys as _sys
            print(f"[lean-substrate] LIVE | toolchain {rtc or '?'}=={ptc or '?'} | "
                  f"import {time.time()-t0:.1f}s | prelude positive control ok",
                  file=_sys.stderr, flush=True)

    def _assert_prelude_live(self, prelude_resp: dict) -> None:
        """FAIL-LOUD positive control: a toolchain/ABI mismatch (repl binary built at
        a DIFFERENT Lean than the project's oleans) makes `import Mathlib` SILENTLY
        return an empty env (env 0 in ~0.8s, no error) instead of loading Mathlib (~40s).
        Every probe against that dead env then errors, so a broken substrate masquerades
        as a real '0 closures / talent-bound' result — a non-probative confound. We refuse
        to hand back a base_env that cannot actually use its own prelude: probe a symbol
        the prelude is supposed to provide and raise with an actionable message if absent.
        """
        if "import mathlib" not in self.prelude.lower():
            return
        probe = self._raw_cmd(
            {"cmd": "example : Finset ℕ := ∅", "env": self._base_env}, 60)
        ok = bool(probe) and not any(
            str(m.get("severity", "")).lower() == "error"
            for m in (probe.get("messages") or []))
        if not ok:
            self._kill()
            raise RuntimeError(
                "PersistentLean prelude loaded an env but Mathlib is NOT usable "
                "(positive control `example : Finset ℕ := ∅` failed). Almost always a "
                "TOOLCHAIN/ABI MISMATCH: the repl binary and the project's Mathlib oleans "
                "were built at different Lean versions. Check that\n  "
                f"{self.repl_bin}\nand\n  {self.project_dir}\nshare the same lean-toolchain. "
                "Refusing to return a dead env (it would silently fail every probe).")

    def _ensure(self) -> None:
        if self._p is None or self._p.poll() is not None:
            self._spawn()

    def _kill(self) -> None:
        if self._p is not None:
            try:
                os.killpg(os.getpgid(self._p.pid), signal.SIGKILL)
            except Exception:
                try:
                    self._p.kill()
                except Exception:
                    pass
        self._p, self._base_env = None, None

    def close(self) -> None:
        self._kill()

    def __enter__(self) -> "PersistentLean":
        self._ensure()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- raw protocol (one JSON request -> one JSON response) --------------
    def _raw_cmd(self, obj: dict, timeout: int) -> dict | None:
        """Returns the parsed JSON response, or None on timeout/crash
        (caller treats None as fail-closed)."""
        p = self._p
        assert p is not None and p.stdin is not None and p.stdout is not None
        q: queue.Queue = queue.Queue(maxsize=1)

        def _reader() -> None:
            buf = ""
            try:
                while True:
                    line = p.stdout.readline()
                    if not line:
                        q.put(("eof", None)); return
                    if line.strip() == "" and buf.strip():
                        break
                    buf += line
                    try:
                        q.put(("ok", json.loads(buf))); return
                    except Exception:
                        continue
                q.put(("ok", json.loads(buf)) if buf.strip()
                      else ("eof", None))
            except Exception as e:  # pragma: no cover - defensive
                q.put(("err", str(e)))

        try:
            p.stdin.write(json.dumps(obj) + "\n\n")
            p.stdin.flush()
        except (BrokenPipeError, ValueError):
            return None
        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        try:
            kind, val = q.get(timeout=timeout)
        except queue.Empty:
            self._kill()          # wedged tactic -> kill; lazy respawn next
            return None
        if kind != "ok":
            self._kill()
            return None
        return val

    # -- public API (return contract == lean_repl.check_lean) -------------
    def check(self, code: str, timeout: int = 120,
              env: int | None = None) -> dict[str, Any]:
        """Elaborate `code` against an env. `env=None` ⇒ the frozen
        prelude base env (default, unchanged: independent, no
        cross-probe contamination). `env=<id>` ⇒ run against an
        ALREADY-OPEN env (e.g. the id `open_file()` returned) — the
        REPL's native env-reuse, so a proof can be governed in a
        module's elaborated context WITHOUT re-elaborating that module
        (the file-amortization the persistent REPL was built for but
        check() did not previously expose). NOTE: a respawn invalidates
        non-base env ids ⇒ on respawn an explicit env falls back to
        _fail (caller re-opens) rather than silently using base_env
        (which would be a DIFFERENT, wrong context — fail-loud)."""
        use_env = self._base_env if env is None else env
        try:
            self._ensure()
        except Exception as e:
            return self._fail(f"spawn_failed: {e}")
        r = self._raw_cmd({"cmd": code, "env": use_env}, timeout)
        if r is None:
            if env is not None:
                # explicit non-base env cannot survive a respawn —
                # do NOT silently rerun in base_env (wrong context).
                return self._fail("env_invalidated_respawn_reopen")
            try:
                self._ensure()
                r = self._raw_cmd({"cmd": code, "env": self._base_env},
                                   timeout)
            except Exception as e:
                return self._fail(f"respawn_failed: {e}")
        if r is None:
            return self._fail("timeout_or_crash")

        msgs = r.get("messages") or []
        sorries = r.get("sorries") or []
        err_lines, all_lines = [], []
        for m in msgs:
            sev = str(m.get("severity", "")).lower()
            data = str(m.get("data", ""))
            pos = m.get("pos") or {}
            tag = (f"L{pos.get('line','?')}:{pos.get('column','?')} "
                   f"{sev}: {data}")
            all_lines.append(tag)
            if sev == "error":
                err_lines.append(tag)
        raw = "\n".join(all_lines)
        success = (not err_lines) and (not sorries)
        return {
            "success": success,
            "output": raw,
            "errors": err_lines,
            "raw": raw,
            "returncode": 0 if success else 1,
            "sorries": sorries,
            "env": r.get("env"),
        }

    # -- proof-STATE stepping (LeanDojo-Gym; the real primitive) ----------
    def start_tactic_proof(
        self, decl_with_sorry: str, timeout: int = 120
    ) -> dict[str, Any]:
        """Open a tactic proof. `decl_with_sorry` must be a complete
        `theorem <name> <sig> := by sorry`. Returns
        {ok, ps, goal} — `ps` is the proofState id to step from,
        `goal` the pretty-printed goal+context. ok=False on
        elaboration error / no open goal."""
        try:
            self._ensure()
        except Exception as e:
            return {"ok": False, "ps": None, "goal": "", "err": str(e)}
        r = self._raw_cmd(
            {"cmd": decl_with_sorry, "env": self._base_env}, timeout)
        if r is None:
            return {"ok": False, "ps": None, "goal": "",
                    "err": "timeout_or_crash"}
        # upstream repl returns a SINGULAR top-level `message`
        # ("Lean error:\n...") on a hard failure, and a `messages`
        # LIST for elaboration diagnostics — both must fail-close.
        if r.get("message"):
            return {"ok": False, "ps": None, "goal": "",
                    "err": str(r["message"])[:200]}
        if any(str(m.get("severity", "")).lower() == "error"
               for m in (r.get("messages") or [])):
            return {"ok": False, "ps": None, "goal": "",
                    "err": "elaboration_error"}
        sorries = r.get("sorries") or []
        if not sorries:
            return {"ok": False, "ps": None, "goal": "",
                    "err": "no_open_goal"}
        s0 = sorries[0]
        return {"ok": True, "ps": s0.get("proofState"),
                "goal": s0.get("goal", ""), "err": ""}

    def step(
        self, ps: int, tactic: str, timeout: int = 60
    ) -> dict[str, Any]:
        """Apply ONE tactic to proof state `ps`. Returns
        {ok, closed, ps, goals, err}. ok=False (and the caller PRUNES
        this action, keeping `ps`) on any error message. closed=True
        iff the tactic left zero goals (branch complete — still must be
        kernel + #print axioms gated by replaying the sequence)."""
        if self._p is None or self._p.poll() is not None:
            return {"ok": False, "closed": False, "ps": ps,
                    "goals": [], "err": "repl_dead"}
        r = self._raw_cmd({"tactic": tactic, "proofState": ps}, timeout)
        if r is None:
            return {"ok": False, "closed": False, "ps": ps,
                    "goals": [], "err": "timeout_or_crash"}
        # FAIL-CLOSE on a hard failure: upstream returns a SINGULAR
        # top-level `message` ("Lean error:\n...") when the tactic
        # fails (NO goals/proofState) — distinct from a `messages`
        # LIST of elaboration diagnostics. The earlier bug: only the
        # plural list was checked, so a failed `rfl` (empty goals, no
        # messages-list) was misread as closed. Both paths fail-close;
        # a closed branch must additionally have proofStatus complete.
        if r.get("message"):
            return {"ok": False, "closed": False, "ps": ps,
                    "goals": [], "err": str(r["message"])[:200]}
        errs = [str(m.get("data", ""))
                for m in (r.get("messages") or [])
                if str(m.get("severity", "")).lower() == "error"]
        if errs:
            return {"ok": False, "closed": False, "ps": ps,
                    "goals": [], "err": errs[0][:200]}
        goals = r.get("goals") or []
        pstat = str(r.get("proofStatus", "")).lower()
        closed = (len(goals) == 0) and ("incomplete" not in pstat) \
            and ("error" not in pstat)
        return {"ok": True, "closed": closed,
                "ps": r.get("proofState"), "goals": goals, "err": ""}

    def open_file(self, path: str, timeout: int = 600) -> dict[str, Any]:
        """Elaborate a REAL Lean file through Lean's actual frontend
        (`{"path":…, "allTactics":true}`) — command-by-command, real
        parser/elaborator, true module context (opens / notation /
        section variables / prior lemmas all live). Returns
        {ok, sorries:[{pos,proofState,goal}], messages, err}.

        This is the cold-validated leak-tight primitive: replace one
        target's proof body with `sorry` in its own source file, open
        it here, and the returned proofState for that `sorry` is the
        genuine pre-command proof state with `T` NOT yet registered
        (variant-b, in-construction — self-reference structurally
        impossible). No regex context scrape, no LeanDojo trace."""
        try:
            self._ensure()
        except Exception as e:
            return {"ok": False, "sorries": [], "messages": [],
                    "err": str(e)}
        r = self._raw_cmd(
            {"path": path, "allTactics": True}, timeout)
        if r is None:
            return {"ok": False, "sorries": [], "messages": [],
                    "err": "timeout_or_crash"}
        if r.get("message"):
            return {"ok": False, "sorries": [], "messages": [],
                    "err": str(r["message"])[:200]}
        sorries = []
        for s in (r.get("sorries") or []):
            pos = s.get("pos") or {}
            sorries.append({
                "proofState": s.get("proofState"),
                "line": pos.get("line"), "column": pos.get("column"),
                "goal": s.get("goal", "")})
        msgs = r.get("messages") or []
        hard = [m for m in msgs
                if str(m.get("severity", "")).lower() == "error"]
        return {"ok": True, "sorries": sorries, "messages": msgs,
                "errors": hard, "env": r.get("env"), "err": ""}

    def print_axioms(self, name: str, timeout: int = 60) -> str:
        """`#print axioms <name>` in-REPL — the governance kernel audit.
        Returns the raw info string (caller parses 'depends on axioms')."""
        r = self.check(f"#print axioms {name}", timeout)
        return r["raw"]

    @staticmethod
    def _fail(reason: str) -> dict[str, Any]:
        return {
            "success": False, "output": reason, "errors": [reason],
            "raw": reason, "returncode": -1, "sorries": [],
            "env": None,
        }
