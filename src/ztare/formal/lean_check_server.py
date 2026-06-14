"""Warm Lean REPL as a SOCKET SERVER — so the INTERACTIVE CLI AGENT reaches the warm REPL (~0.1s/check)
instead of shelling out to COLD `lake env lean` (~30-90s/check, a fresh Mathlib import every time).

WHY (the operator's foot-gun, 2026-06-10): the solver is agent-INTERACTIVE — the prompt tells the agent to
"Run `lake env lean <probe>` and iterate until it compiles". But the warm REPL (`lean_persistent.PersistentLean`)
is an IN-PROCESS python object the harness holds; the agent runs in a CLI SUBPROCESS and cannot reach it, so its
iterate-against-the-kernel loop got ~2-5 COLD compiles per budget instead of dozens WARM. We warmed the harness
compile path (#66/#69) but left the agent — which compiles MOST — on cold lake. This closes that gap: one warm
server (pays the Mathlib import ONCE, stays hot), a thin `--check` client the agent invokes per iteration.

  python -m ztare.formal.lean_check_server --serve <socket> <project>      # the HARNESS starts this once
  python -m ztare.formal.lean_check_server --check <socket> <file.lean>    # the AGENT runs this (warm, fast)

Soundness note: this is a SPEED path for the agent's OWN iteration only. The governance gate (the firewall /
kernel verify) recompiles INDEPENDENTLY — the agent's self-check is never trusted as the verdict — so a warm
self-check cannot launder. Unix socket (same box, same repo). Single-threaded: Lean elaboration isn't parallel,
and serializing one warm REPL is the whole point (no contention)."""
from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path


def _recv_all(conn: socket.socket) -> bytes:
    """Read until the peer half-closes (shutdown(SHUT_WR)) ⇒ clean request/response framing, no length prefix."""
    chunks = []
    while True:
        b = conn.recv(65536)
        if not b:
            break
        chunks.append(b)
    return b"".join(chunks)


def serve(socket_path: str, project: str) -> int:
    """Hold ONE warm `PersistentLean` over `project` and answer `{code, timeout, reject_sorry}` checks on a unix
    socket. Warms Mathlib once at startup so every subsequent check is ~0.1s."""
    from ztare.formal.repl_compile import _get_repl   # the PROVEN construction (+ toolchain guard) the harness uses
    from ztare.common.timeouts import timeout_s       # ONE home for blocking-op budgets (defaults-in-code + env)
    pl = _get_repl(project)
    if pl is None:
        print(f"[lean-check-server] FATAL: warm REPL unavailable for {project} "
              "(toolchain mismatch / repl not built / dead) — the agent must fall back to `lake env lean`", flush=True)
        return 4
    try:
        pl.check("example : True := trivial", timeout=timeout_s("lean_warmup"))     # pay the Mathlib import ONCE (warm)
    except Exception as e:  # noqa: BLE001
        print(f"[lean-check-server] WARN warmup failed: {e!r}", flush=True)
    if os.path.exists(socket_path):
        os.unlink(socket_path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(socket_path)
    srv.listen(8)
    print(f"[lean-check-server] WARM + listening on {socket_path} (project={project})", flush=True)
    while True:
        try:
            conn, _ = srv.accept()
        except KeyboardInterrupt:
            break
        try:
            req = json.loads(_recv_all(conn).decode("utf-8") or "{}")
            code = req.get("code", "") or ""
            reject_sorry = bool(req.get("reject_sorry", False))
            try:
                r = pl.check(code, timeout=int(req.get("timeout", 120)))
                errs = (r or {}).get("errors") or []
                sorries = (r or {}).get("sorries") or []
                ok = (not errs) and not (sorries and reject_sorry)
                toks = [*[str(e) for e in errs],
                        *([f"sorry@{s}" for s in sorries] if (sorries and reject_sorry) else [])]
                diag = "clean" + (" (sorry present)" if sorries and not reject_sorry else "") if ok \
                    else (" | ".join(toks))[:1800]
                resp = {"ok": ok, "diagnostics": diag, "n_errors": len(errs), "n_sorries": len(sorries)}
            except Exception as e:  # noqa: BLE001
                resp = {"ok": False, "diagnostics": f"repl-error: {e!r}", "n_errors": -1, "n_sorries": 0}
            conn.sendall(json.dumps(resp).encode("utf-8"))
            try:
                conn.shutdown(socket.SHUT_WR)
            except OSError:
                pass
        except Exception:  # noqa: BLE001 — never let one bad request kill the server
            pass
        finally:
            conn.close()
    return 0


def check_via_server(socket_path: str, code: str, *, timeout: int = 120, reject_sorry: bool = False) -> "dict | None":
    """Client: send `code` to the warm server, return its `{ok, diagnostics, ...}` (or None if unreachable ⇒
    the caller falls back to cold `lake env lean`)."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(socket_path)
    except OSError:
        return None
    try:
        s.sendall(json.dumps({"code": code, "timeout": timeout, "reject_sorry": reject_sorry}).encode("utf-8"))
        s.shutdown(socket.SHUT_WR)
        return json.loads(_recv_all(s).decode("utf-8") or "{}")
    except Exception:  # noqa: BLE001
        return None
    finally:
        s.close()


def default_socket_path(project: str) -> str:
    """Deterministic per-project socket path (stable across processes — NOT `hash()`, which is randomized)."""
    import hashlib
    h = hashlib.md5(str(Path(project).resolve()).encode("utf-8")).hexdigest()[:10]
    return f"/tmp/leanmill_lean_{h}.sock"


def ensure_server(project: str, *, socket_path: "str | None" = None, warm_wait_s: int = 180) -> "str | None":
    """Idempotently ensure a WARM lean-check server is up for `project`; return its socket path (or None if it
    could not be warmed ⇒ caller keeps cold `lake env lean`). Safe to call before every agentic solve: instant
    no-op if already warm, else starts a DETACHED server and blocks until warm (one-time Mathlib-import cost).
    This is what makes the interactive agent's compiles WARM (~0.1s) instead of cold (~30-90s)."""
    import subprocess
    import time
    sp = socket_path or default_socket_path(project)
    if check_via_server(sp, "example : True := trivial", timeout=20) is not None:
        return sp                                 # already warm
    repo = str(Path(__file__).resolve().parents[3])
    env = dict(os.environ)
    env["PYTHONPATH"] = env.get("PYTHONPATH") or "src"
    try:
        log = open("/tmp/lean_check_server.log", "a")  # noqa: SIM115
        subprocess.Popen([sys.executable, "-m", "ztare.formal.lean_check_server", "--serve", sp, str(project)],
                         cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    except Exception:  # noqa: BLE001
        return None
    left = warm_wait_s
    while left > 0:
        if check_via_server(sp, "example : True := trivial", timeout=10) is not None:
            return sp
        time.sleep(3)
        left -= 3
    return None                                   # warmup did not finish in time ⇒ fall back to cold lake


def _check_cli(socket_path: str, file_path: str, reject_sorry: bool) -> int:
    """The command the AGENT runs: `lean-check <socket> <file>`. Prints the warm diagnostics, exit 0 iff clean.
    Strips a leading `import Mathlib` (the warm prelude already has it). Exit 3 = server unreachable (fall back)."""
    code = Path(file_path).read_text(encoding="utf-8")
    import re
    code = re.sub(r"^\s*import\s+Mathlib\s*$", "", code, flags=re.MULTILINE).lstrip("\n") or "example : True := trivial"
    resp = check_via_server(socket_path, code, reject_sorry=reject_sorry)
    if resp is None:
        print("lean-check: server unreachable — run `lake env lean <file>` instead", file=sys.stderr)
        return 3
    if resp.get("ok"):
        print(f"lean-check: OK — zero errors ({resp.get('n_sorries', 0)} sorry).")
        return 0
    print("lean-check: ERRORS (fix EXACTLY these):\n" + (resp.get("diagnostics") or ""))
    return 1


def main(argv: "list[str] | None" = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) >= 3 and argv[0] == "--serve":
        return serve(argv[1], argv[2])
    if len(argv) >= 3 and argv[0] == "--check":
        return _check_cli(argv[1], argv[2], reject_sorry=("--reject-sorry" in argv))
    print("usage: python -m ztare.formal.lean_check_server (--serve <socket> <project> | --check <socket> <file> [--reject-sorry])",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
