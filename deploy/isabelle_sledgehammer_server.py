#!/usr/bin/env python3
"""Reference Isabelle `sledgehammer` HTTP server for MOVE_SLEDGEHAMMER (leanmill premise-mining).

Implements the EXACT contract `ztare.leanmill.solver.sledgehammer.run_sledgehammer` expects:
  • GET  /health        -> 200 "ok"
  • POST /sledgehammer   {"theory": <isabelle .thy source>, "timeout": <int s>}
                         -> 200 {"proof": "<by (metis …) one-liner>", "used_facts": ["add.commute", …]}
  • POST /verify         {"theory": <complete isabelle .thy source>, "timeout": <int s>}   (leanmill #73)
                         -> 200 {"ok": <bool>, "output": <captured isabelle build text>}
    Isabelle as an INDEPENDENT verification SUBSTRATE — run a complete theory (lemma + proof) through
    `isabelle build` and report whether Isabelle ACCEPTS it (the analog of the Lean proof-compile checker).
    Consumed by `ztare.leanmill.solver.sledgehammer.verify_isabelle`.

Point leanmill at it with `export ZTARE_ISABELLE_SERVER=http://127.0.0.1:8080`. The move is FAIL-CLOSED:
if this server is down/absent the move is a silent no-op (never a false closure), so running it is OPT-IN.

DEPENDENCY: a working Isabelle/HOL with at least one ATP backend (E / Vampire / Z3 / cvc5) configured for
sledgehammer. Install via `deploy/prepare_isabelle_server.sh` (heavyweight, ~1GB). The fact-name PARSING
reuses the UNIT-TESTED `extract_dependency_trace`; the ONLY part not exercisable without Isabelle is the
`_run_isabelle` subprocess invocation + stdout capture — VALIDATE IT ON FIRST LIVE RUN (the `--selftest`
flag exercises everything EXCEPT that subprocess against a fixture transcript).

Run:
  python deploy/isabelle_sledgehammer_server.py --port 8080
  python deploy/isabelle_sledgehammer_server.py --selftest      # no Isabelle needed (parse + HTTP shape)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Reuse the repo's UNIT-TESTED dependency-trace parser (single source of truth — no parallel parser).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
try:
    from ztare.leanmill.solver.sledgehammer import extract_dependency_trace
except Exception:  # noqa: BLE001 — allow standalone run; fall back to a local copy of the regex
    _FACT_RE = re.compile(r"[A-Za-z][\w']*(?:\.[A-Za-z][\w']*)*")
    _NONFACT = {"by", "metis", "smt", "z3", "cvc4", "cvc5", "verit", "simp", "auto", "using",
                "Try", "this", "ms", "add", "del", "no_types", "lifting"}

    def extract_dependency_trace(proof_line: str, max_facts: int = 6):
        out = []
        for tok in _FACT_RE.findall(re.sub(r"\((?:z3|cvc4|cvc5|verit|smt)\)", " ", proof_line or "")):
            if tok.lower() in _NONFACT or tok in _NONFACT or tok in out:
                continue
            out.append(tok)
            if len(out) >= max_facts:
                break
        return out


from pydantic import BaseModel, Field  # repo dep (requirements.txt) — typed/validated config + contract


# ── Typed, externalized CONFIG (pydantic + YAML — the repo convention, vs scattered hardcoded constants) ─
# Precedence: explicit path arg > $ZTARE_ISABELLE_CONFIG > deploy/isabelle_server.yaml > legacy ISABELLE_*
# env vars > field defaults. The YAML is the single source of truth for the operator; env stays for ad-hoc
# overrides + back-compat. Validated on load (a typo'd key / wrong type FAILS LOUD here, not at request time).
class IsabelleServerConfig(BaseModel):
    isabelle_bin: str = Field("isabelle", description="path to the `isabelle` launcher")
    parent_session: str = Field("HOL-Computational_Algebra",
                                description="pre-built heap whose image provides the goal's imports")
    provers: str = Field("e", description="ATP backend(s) sledgehammer drives, e.g. 'e' or 'e vampire z3'")
    prover_timeout_s: int = Field(30, ge=1, description="per-prover wallclock inside sledgehammer")
    build_threads: int = Field(1, ge=1, description="`isabelle build -o threads=` for the per-request session")
    default_imports: str = Field('Main "HOL-Library.Multiset" "HOL-Computational_Algebra.Computational_Algebra"',
                                 description="imports clause when a request omits one")

    @classmethod
    def load(cls, path: "str | None" = None) -> "IsabelleServerConfig":
        src = path or os.environ.get("ZTARE_ISABELLE_CONFIG") or str(Path(__file__).with_name("isabelle_server.yaml"))
        data: dict = {}
        try:
            if Path(src).exists():
                import yaml  # repo dep
                data = yaml.safe_load(Path(src).read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001 — a malformed YAML must not brick the server; fall back to defaults
            data = {}
        env = {"isabelle_bin": os.environ.get("ISABELLE_BIN"),
               "parent_session": os.environ.get("ISABELLE_PARENT_SESSION"),
               "provers": os.environ.get("ISABELLE_PROVERS")}
        data.update({k: v for k, v in env.items() if v})
        return cls(**data)


class SledgehammerRequest(BaseModel):
    """The /sledgehammer request CONTRACT (validated, vs hand-parsing a JSON dict). Preferred form sends the
    structured `goal` (+ optional `imports`); `theory` is the LEGACY form (a pre-baked .thy the server
    reverse-extracts the goal from — kept for back-compat, but the round-trip is the brittle path we moved off)."""
    goal: str = ""
    imports: str = ""
    theory: str = ""
    timeout: int = Field(120, ge=1)


class VerifyRequest(BaseModel):
    """The /verify request CONTRACT (#73): a COMPLETE Isabelle theory (lemma + proof) to run through
    `isabelle build` and accept/reject — Isabelle as an independent verification substrate, not the
    premise-search move."""
    theory: str = ""
    timeout: int = Field(120, ge=1)


CONFIG = IsabelleServerConfig.load()

# Isabelle renders the sledgehammer one-liner with jEdit ACTIVE-AREA markup (`sendbackpadding=commandid=NN`)
# that leaks into the captured plain-text string — strip it before parsing (a belt-and-suspenders backstop;
# `YXML.content_of` already decodes the markup in ML, so this only catches any residue).
_MARKUP_RE = re.compile(r"sendbackpadding=|commandid=\d+|\bxml_id=\w+")
# LEGACY-fallback only: `lemma <name>: "<statement>"` from a pre-baked theory (the preferred contract sends
# `goal` structured). Tolerant of trailing ws.
_LEMMA_RE = re.compile(r"\blemma\s+[A-Za-z_][\w']*\s*:\s*\"((?:[^\"\\]|\\.)*)\"", re.S)


def parse_try_this(stdout: str) -> str:
    """Pull the sledgehammer one-liner out of `Try this: <proof> (NN ms)` / `Found proof: <proof>` lines,
    stripping Isabelle's active-area markup. Returns the first proof one-liner, or '' if none."""
    clean = _MARKUP_RE.sub("", stdout or "")
    for pat in (r"Try this:\s*(.+?)\s*\(\d+(?:\.\d+)?\s*m?s\)", r"Try this:\s*(.+)", r"Found proof:\s*(.+)"):
        m = re.search(pat, clean)
        if m:
            return m.group(1).strip().rstrip(".")
    return ""


def _ml_lit(s: str) -> str:
    """Render a SAFE ASCII value (a filesystem path / prover name / integer) as an ML string literal. The
    GOAL no longer flows through here — it is read from a file as DATA (see `_build_runner_theory`), so this
    only handles values without Isabelle symbols. Escapes `"` and newlines."""
    return '"' + s.replace('"', '\\"').replace("\n", " ") + '"'


def _extract_lemma_statement(theory_source: str) -> str:
    """LEGACY-fallback only: the `"<statement>"` of the first `lemma` in a pre-baked theory."""
    m = _LEMMA_RE.search(theory_source or "")
    return m.group(1).strip() if m else ""


def _build_runner_theory(goal_path: str, imports_clause: str, out_path: str, timeout_s: int) -> str:
    """A self-contained runner theory that READS the goal from `goal_path` (DATA, not interpolated into the
    ML source) and drives the Sledgehammer ML API DIRECTLY — the Isar `sledgehammer` command's output is
    swallowed by `isabelle build`, but the API's returned proof string is not. Reading the goal as a file
    means a symbol-laden statement (`\\<forall>`, `\\<le>`) needs NO ML-string escaping (the brittle seam
    that produced the `\\<forall>` double-escape bug); only safe filesystem paths + the integer timeout are
    interpolated. Validated live 2026-06-09 (prover `e`)."""
    body = (
        "theory ZtareRun\n"
        f"  imports {imports_clause}\n"
        "begin\n\n"
        "ML \\<open>\n"
        "  val thy = @{theory}\n"
        "  val ctxt = @{context}\n"
        f"  val goal = Syntax.read_prop ctxt (File.read (Path.explode {_ml_lit(goal_path)}))\n"
        "  val state = Proof.theorem NONE (K I) [[(goal, [])]] ctxt\n"
        "  val params = Sledgehammer_Commands.default_params thy\n"
        f"                 [(\"provers\", {_ml_lit(CONFIG.provers)}), (\"timeout\", {_ml_lit(str(int(timeout_s)))})]\n"
        f"  val outpath = Path.explode {_ml_lit(out_path)}\n"
        "  val _ = File.write outpath \"\"\n"
        "  val (_, (_, msg)) =\n"
        "    Sledgehammer.run_sledgehammer params Sledgehammer_Prover.Normal NONE 1\n"
        "      Sledgehammer_Fact.no_fact_override state\n"
        # `msg` is YXML-encoded (active-area markup with \\x05/\\x06 element delimiters); `YXML.content_of`
        # decodes it to PLAIN text content (`Try this: by (metis …) (NN ms)`), dropping element names/attrs.
        "  val _ = File.append outpath (YXML.content_of msg)\n"
        "\\<close>\n\n"
        "end\n"
    )
    return body


def _imports_clause(theory_source: str) -> str:
    """LEGACY-fallback only: the `imports …` clause of a pre-baked theory (the preferred contract sends
    `imports` as a structured field). Verbatim, or `Main` if not found."""
    m = re.search(r"\bimports\b(.+?)\bbegin\b", theory_source or "", re.S)
    return " ".join(m.group(1).split()) if m else "Main"


def _run_isabelle(statement: str, imports_clause: str, timeout_s: int) -> str:
    """Run sledgehammer on `statement` (an Isabelle proposition) under `imports_clause` and return the
    captured proof text (fed to `parse_try_this`). Uses `isabelle build` SESSION mode — NOT `isabelle
    process` — because only the session/Scala launcher starts the `bash_process` server the ATPs fork
    through (`isabelle process` dies with 'Bad bash_process server address'). Returns '' on any failure
    (⇒ no premises, fail-closed)."""
    if not (statement or "").strip():
        return ""
    with tempfile.TemporaryDirectory(prefix="ztare_sh_") as td:
        out_path = str(Path(td) / "sh_out.txt")
        goal_path = str(Path(td) / "goal.txt")
        Path(goal_path).write_text(statement, encoding="utf-8")          # GOAL AS DATA — no ML escaping
        (Path(td) / "ZtareRun.thy").write_text(
            _build_runner_theory(goal_path, imports_clause or CONFIG.default_imports, out_path, timeout_s),
            encoding="utf-8")
        (Path(td) / "ROOT").write_text(
            f'session "ZtareRun" = "{CONFIG.parent_session}" +\n  theories\n    ZtareRun\n', encoding="utf-8")
        cmd = [CONFIG.isabelle_bin, "build", "-d", ".", "-o", f"threads={CONFIG.build_threads}", "ZtareRun"]
        try:
            subprocess.run(cmd, cwd=td, capture_output=True, text=True,
                           timeout=max(60, int(timeout_s) + 120), check=False)
        except subprocess.TimeoutExpired:
            return ""
        try:
            return Path(out_path).read_text(encoding="utf-8")
        except OSError:
            return ""


def sledgehammer_response(statement: str, imports_clause: str, timeout_s: int) -> dict:
    stdout = _run_isabelle(statement, imports_clause, timeout_s)
    proof = parse_try_this(stdout)
    return {"proof": proof, "used_facts": extract_dependency_trace(proof)}


# ── /verify — Isabelle as an INDEPENDENT VERIFICATION SUBSTRATE (leanmill #73) ───────────────────────
# The sledgehammer route FINDS premises; THIS route ANSWERS "does Isabelle accept this complete theory
# (lemma + proof)?" — the analog of the Lean `lake env lean` proof-compile checker. Reuses the SAME
# `isabelle build` SESSION mode + the same theory-as-data-on-disk pattern as `_run_isabelle`; the verdict
# is `isabelle build` exiting 0 with no `*** ` error markers in its captured output. The leanmill-side
# `sledgehammer.verify_isabelle` re-checks this output (error markers + the sorry/oops lexical ban), so a
# buggy build report can NOT mint a false accept — the same defense-in-depth as the Lean side's re-parse.
_BUILD_ERROR_MARKERS = ("*** ", "Failed to finish proof", "Outer syntax error", "Inner syntax error",
                        "Type unification failed", "Bad ", "Malformed", "Undefined")
_VERIFY_THEORY_RE = re.compile(r"\btheory\s+([A-Za-z_][\w']*)")


def _theory_name(theory_source: str) -> str:
    """The `theory <Name>` of a submitted .thy (the session theory we must list in ROOT). 'ZtareVerify'
    if absent (the caller usually names it; we don't rewrite their source)."""
    m = _VERIFY_THEORY_RE.search(theory_source or "")
    return m.group(1) if m else "ZtareVerify"


def verify_theory_response(theory_source: str, timeout_s: int) -> dict:
    """Run a COMPLETE Isabelle theory through `isabelle build` (session mode — the same launcher the
    sledgehammer path uses) and report whether Isabelle ACCEPTS it. Returns
    `{"ok": bool, "output": <captured session text>}`. `ok` iff the build exits 0 with no error marker;
    the FULL captured stdout/stderr is returned (truncated) so the leanmill checker can re-inspect it and
    surface a diagnostic. Fail-closed: any subprocess failure / timeout ⇒ `ok=False` with the reason in
    `output` (never a silent accept)."""
    src = (theory_source or "").strip()
    if not src:
        return {"ok": False, "output": "empty theory"}
    thy_name = _theory_name(src)
    with tempfile.TemporaryDirectory(prefix="ztare_verify_") as td:
        (Path(td) / f"{thy_name}.thy").write_text(src, encoding="utf-8")
        # Build the submitted theory as a child of the pre-built parent heap (same image as sledgehammer,
        # so its imports resolve without re-paying the parent build).
        (Path(td) / "ROOT").write_text(
            f'session "ZtareVerify" = "{CONFIG.parent_session}" +\n  theories\n    {thy_name}\n',
            encoding="utf-8")
        cmd = [CONFIG.isabelle_bin, "build", "-d", ".", "-o", f"threads={CONFIG.build_threads}", "ZtareVerify"]
        try:
            proc = subprocess.run(cmd, cwd=td, capture_output=True, text=True,
                                  timeout=max(60, int(timeout_s) + 120), check=False)
        except subprocess.TimeoutExpired:
            return {"ok": False, "output": "isabelle build timeout"}
        except Exception as e:  # noqa: BLE001 — never crash the request; report fail-closed
            return {"ok": False, "output": f"isabelle build exception: {e!r}"}
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    has_error = any(mk in output for mk in _BUILD_ERROR_MARKERS)
    ok = (proc.returncode == 0) and not has_error
    return {"ok": ok, "output": output[-4000:]}


def resolve_goal(req: "SledgehammerRequest") -> "tuple[str, str]":
    """(statement, imports) for a request. PREFERRED: the structured `goal` (+ optional `imports`). LEGACY:
    reverse-extract them from a pre-baked `theory` (the brittle round-trip we moved off, kept for back-compat).
    `imports` defaults to the configured `default_imports`."""
    statement = (req.goal or "").strip()
    imports = (req.imports or "").strip()
    if not statement and req.theory.strip():
        statement = _extract_lemma_statement(req.theory)
        imports = imports or _imports_clause(req.theory)
    return statement, (imports or CONFIG.default_imports)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str = "application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path.rstrip("/") == "/health":
            self._send(200, b"ok", "text/plain")
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self):  # noqa: N802
        route = self.path.rstrip("/")
        if route not in ("/sledgehammer", "/verify"):
            self._send(404, b'{"error":"not found"}')
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n) or b"{}")
            if route == "/verify":   # #73: full-theory verification (independent substrate)
                vreq = VerifyRequest(**payload)
                if not vreq.theory.strip():
                    self._send(400, b'{"error":"no theory (send {theory, timeout})"}')
                    return
                self._send(200, json.dumps(verify_theory_response(vreq.theory, vreq.timeout)).encode())
                return
            req = SledgehammerRequest(**payload)
            statement, imports = resolve_goal(req)   # structured `goal` preferred; legacy `theory` fallback
            if not statement:
                self._send(400, b'{"error":"no goal (send {goal, imports} or a legacy {theory})"}')
                return
            resp = sledgehammer_response(statement, imports, req.timeout)
            self._send(200, json.dumps(resp).encode())
        except subprocess.TimeoutExpired:
            self._send(200, json.dumps({"proof": "", "used_facts": []}).encode())
        except Exception as e:  # noqa: BLE001
            self._send(500, json.dumps({"error": repr(e)[:200]}).encode())

    def log_message(self, *_a):  # quiet
        pass


def _selftest() -> int:
    """Exercise everything EXCEPT the Isabelle subprocess: the `Try this:` parser + the fact-trace reuse +
    the response shape, against a fixture sledgehammer transcript."""
    fails = []
    fixture = ("Sledgehammering...\n"
               "e found a proof...\n"
               "Try this: by (metis add.commute mult.assoc Nat.add_0_right) (123 ms)\n")
    proof = parse_try_this(fixture)
    if proof != "by (metis add.commute mult.assoc Nat.add_0_right)":
        fails.append(f"parse_try_this wrong: {proof!r}")
    facts = extract_dependency_trace(proof)
    if facts != ["add.commute", "mult.assoc", "Nat.add_0_right"]:
        fails.append(f"trace wrong: {facts}")
    if parse_try_this("Sledgehammering...\nNo proof found.\n") != "":
        fails.append("no-proof transcript should yield ''")
    # REAL captured shape: the ML-API `msg` carries jEdit active-area markup that must be stripped (the
    # exact string observed live 2026-06-09 from prover `e`).
    markup = "Try this: sendbackpadding=commandid=236by auto (0.5 ms)"
    if parse_try_this(markup) != "by auto":
        fails.append(f"markup not stripped: {parse_try_this(markup)!r}")
    metis_markup = "Try this: sendbackpadding=commandid=7by (metis add.commute) (310 ms)"
    if parse_try_this(metis_markup) != "by (metis add.commute)":
        fails.append(f"markup+metis wrong: {parse_try_this(metis_markup)!r}")
    # lemma-statement + imports extraction (drives the session-build runner theory)
    thy = ('theory ZtareGoal\nimports Main "HOL-Library.Multiset"\nbegin\n'
           'lemma ztare_goal: "\\<forall>a b. a + b = b + (a::nat)"\n  sledgehammer\noops\nend\n')
    if _extract_lemma_statement(thy) != "\\<forall>a b. a + b = b + (a::nat)":
        fails.append(f"lemma extract wrong: {_extract_lemma_statement(thy)!r}")
    if _imports_clause(thy) != 'Main "HOL-Library.Multiset"':
        fails.append(f"imports extract wrong: {_imports_clause(thy)!r}")
    runner = _build_runner_theory("/tmp/goal.txt", "Main", "/tmp/o", 30)
    if 'Sledgehammer.run_sledgehammer' not in runner or "File.read" not in runner:
        fails.append("runner theory missing the ML API call / goal-as-file read")
    # CONTRACT (typed): structured `goal` preferred, legacy `theory` reverse-extracted, imports default
    s1, i1 = resolve_goal(SledgehammerRequest(goal="\\<forall>x. x = x", imports="Main"))
    if (s1, i1) != ("\\<forall>x. x = x", "Main"):
        fails.append(f"resolve_goal structured wrong: {(s1, i1)}")
    s2, i2 = resolve_goal(SledgehammerRequest(theory=thy))
    if s2 != "\\<forall>a b. a + b = b + (a::nat)" or i2 != 'Main "HOL-Library.Multiset"':
        fails.append(f"resolve_goal legacy-theory wrong: {(s2, i2)}")
    if resolve_goal(SledgehammerRequest(goal="True"))[1] != CONFIG.default_imports:
        fails.append("resolve_goal should default imports to CONFIG.default_imports")
    # CONFIG (typed): loads + a bad type fails loud
    try:
        IsabelleServerConfig(prover_timeout_s=-1); fails.append("config should reject prover_timeout_s<1")
    except Exception:  # noqa: BLE001
        pass
    # response shape (mock the subprocess)
    global _run_isabelle
    _orig = _run_isabelle
    _run_isabelle = lambda *_a, **_k: fixture  # noqa: E731
    try:
        r = sledgehammer_response("True", "Main", 60)
        if r["proof"] != proof or r["used_facts"] != facts:
            fails.append(f"response shape wrong: {r}")
    finally:
        _run_isabelle = _orig

    # /verify (#73): theory-name extraction + the accept/reject DECODE of `isabelle build` output (mock the
    # subprocess; the build itself is the only un-exercisable-without-Isabelle part — validate on live run).
    if _theory_name('theory MyThy imports Main begin\nlemma x: "True" by simp\nend') != "MyThy":
        fails.append("verify: theory-name extraction wrong")
    import subprocess as _sp
    _orig_run = _sp.run
    class _P:  # a stand-in CompletedProcess
        def __init__(self, rc, out):
            self.returncode, self.stdout, self.stderr = rc, out, ""
    try:
        _sp.run = lambda *a, **k: _P(0, "Finished ZtareVerify (0:00:03 elapsed time)")  # noqa: E731
        rv_ok = verify_theory_response('theory T imports Main begin\nlemma t: "True" by simp\nend', 30)
        if rv_ok.get("ok") is not True:
            fails.append(f"verify ACCEPT: clean build should be ok=True, got {rv_ok}")
        _sp.run = lambda *a, **k: _P(1, "*** Failed to finish proof:\n*** 1. n + 0 = n + 1")  # noqa: E731
        rv_no = verify_theory_response('theory T imports Main begin\nlemma t: "n + 0 = n + 1" by simp\nend', 30)
        if rv_no.get("ok") is not False or "Failed to finish proof" not in rv_no.get("output", ""):
            fails.append(f"verify REJECT: build error should be ok=False+surfaced, got {rv_no}")
        # rc==0 but an error marker leaked into output ⇒ still reject (defense-in-depth)
        _sp.run = lambda *a, **k: _P(0, "*** Type unification failed")  # noqa: E731
        if verify_theory_response('theory T imports Main begin\nlemma t: "True" oops\nend', 30).get("ok") is not False:
            fails.append("verify REJECT: rc==0 with an error marker must still be ok=False")
    finally:
        _sp.run = _orig_run
    if verify_theory_response("", 30).get("ok") is not False:
        fails.append("verify REJECT: empty theory must be ok=False")

    print("  [PASS] parse + trace + response shape + /verify decode" if not fails else f"  [FAIL] {fails}")
    print("ISABELLE SERVER SELFTEST", "PASSED (subprocess NOT exercised — validate on first live run)"
          if not fails else "FAILED")
    return 0 if not fails else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Isabelle sledgehammer server on http://{args.host}:{args.port} "
          f"(isabelle_bin={CONFIG.isabelle_bin}, parent_session={CONFIG.parent_session}, "
          f"provers={CONFIG.provers})", flush=True)
    print("  point leanmill at it: export ZTARE_ISABELLE_SERVER="
          f"http://{args.host}:{args.port}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
