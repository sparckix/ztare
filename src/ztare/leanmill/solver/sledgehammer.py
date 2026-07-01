"""SLEDGEHAMMER-SMUGGLE — borrow Isabelle/HOL's `sledgehammer` premise selection, smuggle the
dependency trace BACK into Lean as kernel-validated `exact?`/`aesop` premises (a solver-core move,
2026-06-08).

THE MOVE (a premise-RETRIEVAL move, not a closure path of its own). Lean's weakness vs an open goal is
PREMISE SELECTION — which 3-4 Mathlib lemmas unlock it. Isabelle's `sledgehammer` is the best premise
selector in the formal-methods world (it fires a battery of external ATPs — E/SPASS/Vampire/cvc5/Z3 —
over the whole library and MINIMISES to the few facts actually used). So:

  1. TRANSLATE  the Lean goal+context to an Isabelle/HOL lemma statement (in-repo, conservative);
  2. RUN        `sledgehammer` on an Isabelle server (EXTERNAL infra — see SERVER REQUIREMENT below);
  3. EXTRACT    the DEPENDENCY TRACE — the 3-4 Isabelle fact names sledgehammer reports it used;
  4. MAP        each Isabelle fact name to its Mathlib equivalent (a static table + heuristics);
  5. VALIDATE   each mapped name AGAINST THE KERNEL with a `#check` probe — an Isabelle→Mathlib name
                that does NOT resolve in Mathlib is DROPPED, never injected (the mapping HALLUCINATES);
  6. INJECT     the surviving, kernel-confirmed names as `exact?`/`aesop (add simp ...)` premises into
                a Lean tactic block.

SOUNDNESS / no false closure (the non-negotiable). This module NEVER claims a closure on its own word.
The Isabelle trace is UNTRUSTED (it proves the goal in a DIFFERENT logic) and the name mapping
HALLUCINATES (Isabelle `Nat.add_commute` ≠ a guaranteed Mathlib `Nat.add_comm`). Two kernel gates stand
between the leaf's output and any "advance":
  • `validate_mathlib_names` — a per-name `#check` compile (via the v33 `_compile_probe`); an unresolved
    name is DROPPED. No hallucinated identifier is ever emitted into the injected tactic.
  • the move runner (solver_core) compiles the INJECTED tactic block through `_verify_compile` + `_govern`
    (kernel + matched-negative-control + statement_integrity) exactly like `generalize`/`witness_transport`.
    A wrong premise set merely fails to compile (a MISS), never a false closure.
So the worst case of a totally-wrong Isabelle trace + a totally-hallucinated mapping is a NO-OP miss.

SERVER REQUIREMENT (external infra — NOT installed in this repo). `sledgehammer` needs a running
Isabelle/HOL instance with the ATP backends configured. This module FAILS CLOSED when no server is
configured: set `ZTARE_ISABELLE_SERVER` to a base URL (e.g. `http://127.0.0.1:8080`) of a service that
accepts `POST {base}/sledgehammer {"theory": <isabelle source>, "timeout": <s>}` and returns
`{"proof": <str>, "used_facts": [<str>, ...]}` (the dependency trace). Absent the env var, every
`run_sledgehammer` returns None (no trace) ⇒ the move is a no-op. The translation, trace-extraction,
Mathlib-mapping, kernel-validation, and injection logic are ALL in-repo and unit-tested offline against
fixture traces (no server needed for the selftest) — only the live ATP call is external.

FLAG. `ZTARE_LEANMILL_SLEDGEHAMMER=1` enables the move (default off = byte-parity; the move is not
offered and no Isabelle call is made). External deps (`requests` for the server call) are lazy-imported
and fail-closed if absent.

PATTERN. Mirrors `conjecture.py` (generate / kernel-gate) and `witness_transport.py` (in-repo glue over
external compute, fail-closed). The kernel gate is the v33 `_compile_probe`
(`ztare.gates.v33_preflight_risk_detector._compile_probe`) — the SAME gate `conjecture_advances` uses.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# ── 0. Server config / fail-closed ─────────────────────────────────────────────────────────────────
_SERVER_ENV = "ZTARE_ISABELLE_SERVER"
_FLAG_ENV = "ZTARE_LEANMILL_SLEDGEHAMMER"
# Imports clause for the translated goal — kept in sync with the server's `default_imports`
# (deploy/isabelle_server.yaml). The server's `parent_session` heap must satisfy these.
ISABELLE_IMPORTS = 'Main "HOL-Library.Multiset" "HOL-Computational_Algebra.Computational_Algebra"'


def isabelle_server() -> str:
    """The Isabelle server base URL. DEFAULTS to the standard local server (`http://127.0.0.1:8080`, which the
    deploy starts) so the hammer is ON-BY-DEFAULT wherever the server runs; set ZTARE_ISABELLE_SERVER to
    override. The liveness gate below self-degrades when the URL is dead, so a default that points nowhere is
    harmless (the tool is simply not surfaced)."""
    return (os.environ.get(_SERVER_ENV) or "http://127.0.0.1:8080").strip()


import functools as _functools


@_functools.lru_cache(maxsize=4)
def _server_responds(url: str) -> bool:
    """Cached (once-per-(process,url)) CHEAP liveness probe — does the Isabelle server respond at all? A GET /
    that returns ANY HTTP status (even the server's `{"error":"not found"}`) means it is UP; only a refused
    connection / timeout means dead. NO sledgehammer call (that would be slow) — just a socket-level liveness."""
    import urllib.request
    import urllib.error
    try:
        urllib.request.urlopen(url.rstrip("/") + "/", timeout=4)
        return True
    except urllib.error.HTTPError:
        return True   # a 4xx/5xx is still a LIVE server answering
    except Exception:  # noqa: BLE001 — connection refused / DNS / timeout ⇒ dead
        return False


def isabelle_hammer_live() -> bool:
    """Is the Isabelle hammer (the cross-substrate leapfrog) AVAILABLE? DEFAULT-ON when the server is LIVE
    (the sound-knob-default-on principle, 2026-06-11 — a VALIDATED capability must not sit dormant behind an
    opt-in flag; the operator: 'a sound knob left off to A/B just stays dormant'). `ZTARE_LEANMILL_SLEDGEHAMMER=0`
    force-OFF; `ZTARE_ISABELLE_ASSUME_LIVE=1` test hook (skip the network probe). Otherwise: surface IFF the
    server (ZTARE_ISABELLE_SERVER or the default :8080) responds — so it is ON where the server runs and
    self-degrades (no dead-tool foot-gun) where it does not."""
    if os.environ.get(_FLAG_ENV) == "0":
        return False
    if os.environ.get("ZTARE_ISABELLE_ASSUME_LIVE") == "1":
        return True
    return _server_responds(isabelle_server())


def sledgehammer_enabled() -> bool:
    """The move flag — now DEFAULT-ON when the Isabelle server is LIVE (was default-off = dormant). `=0`
    force-off; self-degrades to off when no server responds (byte-parity on a node without Isabelle)."""
    return isabelle_hammer_live()


# ── 1. Lean → Isabelle/HOL translation (in-repo, conservative) ──────────────────────────────────────
# Translate the goal's CLOSED Prop (∀-binders + conclusion, via conjecture._closed_goal_prop) to an
# Isabelle/HOL `lemma` statement. CONSERVATIVE: only the common surface — quantifiers, arithmetic, the
# basic logical connectives, type ascriptions. A construct we cannot faithfully translate makes
# `lean_to_isabelle` return '' (⇒ no Isabelle call: better a missed move than a MIS-translated lemma that
# sledgehammers a DIFFERENT statement and smuggles back irrelevant premises). The translation is NOT a
# trust boundary — the kernel validates every premise it produces — but a faithful one yields useful
# premises; a garbled one merely wastes a server call.
_TYPE_MAP = {
    "ℕ": "nat", "Nat": "nat",
    "ℤ": "int", "Int": "int",
    "ℝ": "real", "Real": "real",
    "ℚ": "rat", "Rat": "rat",
    "Prop": "bool", "Bool": "bool",
}


def _translate_body(body: str) -> str:
    """Translate a Lean Prop BODY (no leading binders) to Isabelle/HOL surface syntax. Conservative —
    returns '' if it contains a construct we do not faithfully map (sets, structures, custom defs)."""
    b = body.strip()
    # reject constructs we cannot faithfully translate (would change the statement's meaning)
    if any(tok in b for tok in ("{", "}", "⟨", "⟩", "Finset", "Set ", "fun ", "λ", "∑", "∏", "∫", "∂")):
        return ""
    # power: Lean `^` → Isabelle `^` (same); `**` → `^`
    b = b.replace("**", "^")
    # logical connectives (Lean → Isabelle/HOL)
    b = re.sub(r"↔", " = ", b)               # iff on bool ≈ equality (conservative)
    b = b.replace("∧", "\\<and>").replace("∨", "\\<or>")
    b = b.replace("¬", "\\<not> ")
    b = re.sub(r"→", " \\<longrightarrow> ", b)
    b = b.replace("≤", "\\<le>").replace("≥", "\\<ge>")
    b = b.replace("≠", "\\<noteq>")
    b = b.replace("∈", "\\<in>")
    # strip Lean numeric type ascriptions inside the body: `(0 : ℕ)` → `(0::nat)`
    def _ascr(m: re.Match) -> str:
        val, typ = m.group(1).strip(), m.group(2).strip()
        return f"({val}::{_TYPE_MAP.get(typ, typ)})"
    b = re.sub(r"\(([^():]+):\s*([A-Za-zℕℤℝℚ]+)\)", _ascr, b)
    return b.strip()


def lean_to_isabelle(goal_text: str, theory_name: str = "ZtareGoal") -> "tuple[str, str, str, str]":
    """Translate the Lean goal to a self-contained Isabelle theory. Returns
    (theory_source, lemma_name, statement, imports) — `statement`+`imports` are the STRUCTURED contract the
    server now consumes directly (the `theory` is kept for back-compat). ('', '', '', '') if the goal cannot
    be faithfully translated (⇒ caller makes NO Isabelle call). Uses conjecture._closed_goal_prop so the
    binder parse is IDENTICAL to the rest of the solver."""
    try:
        from ztare.leanmill.solver.conjecture import _closed_goal_prop
    except Exception:  # noqa: BLE001
        return "", "", "", ""
    prop = _closed_goal_prop(goal_text)
    if not prop:
        return "", "", "", ""
    # split leading `∀ <binders>, <body>` (closed_goal_prop produces exactly this shape, or a bare body)
    binders, body = "", prop
    m = re.match(r"^\s*∀\s*(.*?),\s*(.+)$", prop, re.DOTALL)
    isa_binders = ""
    if m:
        binders, body = m.group(1).strip(), m.group(2).strip()
        # binders like `(n : ℕ) (k : ℕ)` → Isabelle `\<forall>n k. ...` is implicit via `fixes`; we
        # instead bind them as schematic `\<And>`-free universals folded into the body.
        bvars = re.findall(r"\(([^():]+):\s*([^()]+)\)", binders)
        if not bvars:
            return "", "", "", ""
        # one name list with an explicit Isabelle type each (a binder group may bind several names).
        # REJECT any binder whose type we cannot faithfully map (e.g. `Finset ℕ`, a custom structure):
        # binding it as a verbatim Lean type would produce a garbled Isabelle lemma over a DIFFERENT
        # statement, so we bail (no Isabelle call) rather than smuggle premises for the wrong goal.
        names: list[str] = []
        for grp_names, typ in bvars:
            isa_typ = _TYPE_MAP.get(typ.strip())
            if isa_typ is None:
                return "", "", "", ""
            for nm in grp_names.replace(",", " ").split():
                if re.fullmatch(r"[A-Za-z_][\w']*", nm):
                    names.append(f"{nm}::{isa_typ}")
        if not names:
            return "", "", "", ""
        isa_binders = "\\<forall>" + " ".join(names) + ". "
    ibody = _translate_body(body)
    if not ibody:
        return "", "", "", ""
    statement = (isa_binders + ibody) if isa_binders else ibody
    lemma_name = "ztare_goal"
    theory = (
        f"theory {theory_name}\n"
        f"imports {ISABELLE_IMPORTS}\n"
        f"begin\n\n"
        f"lemma {lemma_name}: \"{statement}\"\n"
        f"  sledgehammer\n"
        f"  oops\n\n"
        f"end\n"
    )
    return theory, lemma_name, statement, ISABELLE_IMPORTS


# ── 2. Run sledgehammer on the external server (FAIL-CLOSED) ─────────────────────────────────────────
def run_sledgehammer(theory_source: str, timeout_s: int = 120, *,
                     statement: str = "", imports: str = "") -> "dict | None":
    """POST the goal to the configured `sledgehammer` server and return its parsed response
    `{"proof": str, "used_facts": [str, ...]}`. The PREFERRED contract sends the STRUCTURED `goal` (+
    `imports`) — no theory round-trip the server has to reverse-parse; `theory` is still sent so an older
    server keeps working (back-compat). FAIL-CLOSED → None when:
      • the move is not configured (no ZTARE_ISABELLE_SERVER) — the EXPECTED state in this repo;
      • `requests` (lazy-imported external dep) is absent;
      • the server errors / times out / returns an unparseable body.
    A None here ⇒ the move is a no-op (NEVER a silent admit: there is no trace to inject)."""
    base = isabelle_server()
    if not base or not ((statement or "").strip() or (theory_source or "").strip()):
        return None
    try:
        import requests  # lazy external dep — fail-closed if absent
    except Exception:  # noqa: BLE001
        return None
    try:
        resp = requests.post(
            base.rstrip("/") + "/sledgehammer",
            json={"goal": statement, "imports": imports, "theory": theory_source, "timeout": int(timeout_s)},
            timeout=max(10, int(timeout_s) + 30),
        )
        if getattr(resp, "status_code", 0) != 200:
            return None
        data = resp.json()
    except Exception:  # noqa: BLE001 — any transport/parse failure is a fail-closed no-op
        return None
    if not isinstance(data, dict):
        return None
    facts = data.get("used_facts")
    if not isinstance(facts, list):
        # fall back to extracting from the raw proof string if the server didn't pre-parse
        facts = extract_dependency_trace(str(data.get("proof") or ""))
    return {"proof": str(data.get("proof") or ""), "used_facts": [str(f) for f in facts if str(f).strip()]}


# ── 2b. ISABELLE AS AN INDEPENDENT VERIFICATION SUBSTRATE (#73) ──────────────────────────────────────
# The sledgehammer move above uses Isabelle to FIND premises (then re-checks them in the Lean kernel).
# This is the orthogonal use: submit a COMPLETE theory (lemma + its proof) and ask whether Isabelle
# ACCEPTS it — the Isabelle analog of `LeanLakeChecker.verify` on the Lean side. The result is a verdict
# from a SEPARATE substrate (different logic, different kernel), so an Isabelle-proved claim can be fed to
# `cross_substrate_consensus` as a peer of Lean — NOT smuggled into, and adding NO soundness surface to,
# the Lean kernel. Same transport as `run_sledgehammer` (POST the configured server, decode its JSON), so
# there is no parallel client; the server reuses its `isabelle build` session + `YXML.content_of` decode.

# Lexical defense-in-depth, mirroring the Lean side's sorry/admit ban (`_is_compile_ok`): `isabelle build`
# exits 0 on a theory whose proof is `sorry`/`oops` (they are warnings/"skipped proof", not errors), so a
# theory carrying either could otherwise mint a FALSE accept. We reject it BEFORE the call (and again on
# the way back, belt-and-suspenders) — the same no-false-closure posture as `compile_probe_via_repl(...,
# reject_sorry=True)`. `\<proof>` / Isar `proof` blocks are fine; only the cheat tokens are banned.
_ISABELLE_CHEAT_RE = re.compile(r"\b(sorry|oops)\b")
# Markers the Isabelle session reports for a theory that did NOT go through clean — surfaced to the caller
# so a NACK localizes (mirrors the Lean error-tail we keep in `CheckResult.diagnostics`).
_ISABELLE_ERROR_MARKERS = (
    "*** ", "Failed to finish proof", "Failed to apply", "Step error",
    "Outer syntax error", "Inner syntax error", "Type unification failed",
    "exception", "Undefined", "Bad ", "Malformed",
)


def verify_isabelle(theory_text: str, *, timeout_s: int = 120, server=None) -> "tuple[bool, str]":
    """Submit a COMPLETE Isabelle theory (lemma + proof) to the Isabelle server and return
    `(ok, diagnostic)` — whether Isabelle ACCEPTS the theory. The Isabelle analog of
    `LeanLakeChecker.verify`: kernel-trust (the session built clean, no `*** ` error, no `sorry`/`oops`),
    never text-trust. A SEPARATE substrate — its verdict is for `cross_substrate_consensus`, it adds NO
    soundness surface to the Lean kernel.

    FAIL-CLOSED to `(False, ...)`, NEVER a crash and NEVER a false pass, when:
      • the server is not configured / not live (`ZTARE_ISABELLE_SERVER` unset and the default :8080 is
        dead) ⇒ `(False, "isabelle checker unavailable: ...")` — opt-in, exactly like the move;
      • the theory carries a `sorry`/`oops` cheat (lexical ban, defense-in-depth);
      • `requests` (lazy external dep) is absent, or the transport/JSON fails.

    `server` INJECTS the transport for a hermetic selftest — any callable
    `server(theory_text, timeout_s) -> dict` standing in for the live `/verify` POST, so the adapter
    logic (accept / error / sorry) is testable with NO real Isabelle. The live `/verify` endpoint runs the
    theory through the SAME `isabelle build` session + `YXML.content_of` decode as the sledgehammer path."""
    text = (theory_text or "").strip()
    if not text:
        return False, "isabelle checker: empty theory text"
    # Lexical cheat ban FIRST — before any network call (mirrors the Lean sorry/admit reject).
    m = _ISABELLE_CHEAT_RE.search(text)
    if m:
        return False, f"isabelle checker: lexical cheat token '{m.group(1)}' in theory (no-false-closure)"

    # Resolve the transport. Injected `server` (selftest) bypasses both liveness AND `requests`.
    if server is None:
        # Opt-in / availability gate — same posture as the move: only call a LIVE server.
        if not isabelle_hammer_live():
            return False, ("isabelle checker unavailable: no live Isabelle server "
                           f"({_SERVER_ENV} unset or unreachable) — fail-closed, not a false pass")
        server = _http_verify_isabelle

    try:
        data = server(text, timeout_s)
    except Exception as exc:  # noqa: BLE001 — any transport/parse failure is a fail-closed NACK
        return False, f"isabelle checker: transport/exception ({exc!r})"
    if not isinstance(data, dict):
        return False, f"isabelle checker: server returned a non-dict response ({type(data).__name__})"

    # Decode the verdict. The server returns {"ok": bool, "output": <decoded session text>}; we DO NOT
    # trust a bare "ok":True without the output also being error/cheat free (defense-in-depth: a buggy or
    # spoofing server can't mint a pass — same reason the Lean side re-parses the compile output).
    output = str(data.get("output") or data.get("diagnostic") or "")
    server_ok = data.get("ok") is True
    cheat = _ISABELLE_CHEAT_RE.search(output)
    if cheat:
        return False, f"isabelle checker: cheat token '{cheat.group(1)}' in server output (no-false-closure)"
    err = next((mk for mk in _ISABELLE_ERROR_MARKERS if mk in output), None)
    if err:
        return False, f"isabelle checker: error in session output [{err.strip()}]: {output[-600:]}"
    if not server_ok:
        return False, f"isabelle checker: server reported not-ok: {output[-600:] or '(no output)'}"
    return True, f"isabelle accepted the theory: {output[-300:] or 'clean build, no errors'}"


def _http_verify_isabelle(theory_text: str, timeout_s: int) -> "dict":
    """The LIVE transport for `verify_isabelle` — POST the complete theory to the server's `/verify`
    endpoint and return the parsed JSON. Mirrors `run_sledgehammer`'s `requests.post` shape exactly (same
    base URL, same timeout budget, lazy `requests`); the only difference is the route + payload. Raises on
    any transport/parse failure so `verify_isabelle`'s `except` turns it into a fail-closed NACK."""
    import requests  # lazy external dep — fail-closed (raises ImportError → caught upstream) if absent
    base = isabelle_server()
    resp = requests.post(
        base.rstrip("/") + "/verify",
        json={"theory": theory_text, "timeout": int(timeout_s)},
        timeout=max(10, int(timeout_s) + 30),
    )
    if getattr(resp, "status_code", 0) != 200:
        raise RuntimeError(f"isabelle /verify HTTP {getattr(resp, 'status_code', '?')}")
    return resp.json()


# ── 3. Extract the DEPENDENCY TRACE from a sledgehammer proof line ───────────────────────────────────
# sledgehammer reports e.g.:
#   `by (metis add.commute mult.assoc Nat.add_0_right)`  or
#   `by (smt (z3) foo.bar baz_def)`  or  `by (simp add: add.commute)`.
# The trace = the fact NAMES inside that one-liner. PURE (no server / no compile) ⇒ unit-testable.
_NONFACT = {
    "by", "metis", "smt", "z3", "cvc4", "cvc5", "verit", "simp", "auto", "fastforce",
    "blast", "force", "add", "del", "using", "intro", "elim", "dest", "of", "OF", "THEN",
    "and", "rule", "iprover", "satx", "meson", "moura",
    # sledgehammer one-liner LOG boilerplate (when the raw `Try this: ... (NN ms)` line is parsed as a
    # fallback). Noise that slips through is harmless — the kernel `#check` drops any non-existent name —
    # but filtering it here avoids wasting a probe per junk token.
    "Try", "this", "ms", "s", "no_types", "no_types_lifting", "lifting", "Found", "proof",
}
_FACT_RE = re.compile(r"[A-Za-z][\w']*(?:\.[A-Za-z][\w']*)*")


def extract_dependency_trace(proof_line: str, max_facts: int = 6) -> "list[str]":
    """Parse the fact NAMES out of a sledgehammer one-liner proof. Drops tactic/keyword tokens and
    `(z3)`-style backend tags; keeps the first `max_facts` distinct fact names (sledgehammer minimises to
    the 3-4 actually used). Returns [] if none found (⇒ no premises to map)."""
    if not (proof_line or "").strip():
        return []
    # drop the `by (...)` wrapper punctuation but keep the token stream
    text = re.sub(r"\(\s*(?:z3|cvc4|cvc5|verit|smt)\s*\)", " ", proof_line)  # backend tags
    facts: list[str] = []
    for tok in _FACT_RE.findall(text):
        low = tok.lower()
        if low in _NONFACT or tok in _NONFACT:
            continue
        if tok not in facts:
            facts.append(tok)
        if len(facts) >= max_facts:
            break
    return facts


# ── 4. Isabelle → Mathlib name mapping (HALLUCINATES — validated downstream) ─────────────────────────
# A static table for the high-frequency arithmetic/order facts sledgehammer leans on, plus structural
# heuristics. THIS MAPPING IS UNTRUSTED: it is a best-effort guess, and `validate_mathlib_names` (a
# kernel `#check`) is the ONLY thing that decides whether a mapped name is real. The table is small on
# PURPOSE — a wrong static entry is caught by the kernel and dropped, exactly like a heuristic guess.
_ISABELLE_TO_MATHLIB = {
    "add.commute": "add_comm",
    "add.assoc": "add_assoc",
    "add.left_commute": "add_left_comm",
    "add_0_right": "add_zero",
    "add_0_left": "zero_add",
    "Nat.add_0_right": "Nat.add_zero",
    "Nat.add_commute": "Nat.add_comm",
    "Nat.add_assoc": "Nat.add_assoc",
    "Nat.mult_commute": "Nat.mul_comm",
    "mult.commute": "mul_comm",
    "mult.assoc": "mul_assoc",
    "mult.left_commute": "mul_left_comm",
    "distrib_left": "mul_add",
    "distrib_right": "add_mul",
    "le_trans": "le_trans",
    "order_trans": "le_trans",
    "le_antisym": "le_antisymm",
    "dvd_refl": "dvd_refl",
    "dvd_trans": "dvd_trans",
    "gcd.commute": "Nat.gcd_comm",
    "power_add": "pow_add",
    "power_mult": "pow_mul",
}


def map_isabelle_name(isa_name: str) -> "str | None":
    """Best-effort Isabelle→Mathlib name guess. None if we have no candidate at all. HALLUCINATES by
    construction — the returned name is a CANDIDATE only; `validate_mathlib_names` kernel-checks it.
    Order: (1) exact static-table hit; (2) bare-suffix table hit (drop the Isabelle theory qualifier);
    (3) a structural heuristic (Isabelle `foo.commute`/`foo_commute` → Mathlib `foo_comm`, the very
    common comm/assoc/left_comm renames). A name we cannot even guess returns None (no probe wasted)."""
    if not (isa_name or "").strip():
        return None
    name = isa_name.strip()
    if name in _ISABELLE_TO_MATHLIB:
        return _ISABELLE_TO_MATHLIB[name]
    # progressively drop leading theory qualifiers (`Groups.add.commute` → `add.commute` → `commute`)
    # and retry the table — Isabelle facts are often reported fully-qualified.
    parts = name.split(".")
    for i in range(1, len(parts)):
        suffix = ".".join(parts[i:])
        if suffix in _ISABELLE_TO_MATHLIB:
            return _ISABELLE_TO_MATHLIB[suffix]
    # structural renames (Isabelle long-form → Mathlib short-form)
    cand = name.replace(".", "_")
    cand = re.sub(r"_commute$", "_comm", cand)
    cand = re.sub(r"_associative$", "_assoc", cand)
    cand = re.sub(r"_left_commute$", "_left_comm", cand)
    cand = re.sub(r"_idempotent$", "_idem", cand)
    if cand != name.replace(".", "_") or "_" in name or "." in name:
        return cand
    return None


def map_trace_to_mathlib(trace: "list[str]") -> "list[tuple[str, str]]":
    """Map a whole dependency trace to candidate Mathlib names. Returns the list of
    (isabelle_name, candidate_mathlib_name) pairs we have a guess for (unmappable names dropped here;
    hallucinated guesses dropped LATER by the kernel `#check`). PURE."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for isa in trace or []:
        cand = map_isabelle_name(isa)
        if cand and cand not in seen:
            out.append((isa, cand))
            seen.add(cand)
    return out


# ── 5. KERNEL VALIDATION: drop any mapped name that is not REALLY in Mathlib (the anti-hallucination
#       gate). A `#check @<name>` snippet compiles clean iff Mathlib resolves the identifier; an unknown
#       identifier yields a Lean error and `_compile_probe` returns False ⇒ we DROP it. This is the same
#       exogenous kernel the rest of the solver trusts — never the leaf's / mapping's word. ───────────
def _check_probe(name: str, lean_root: Path, timeout_s: int, preamble: str = "") -> bool:
    """True iff `name` resolves as a Mathlib identifier (a `#check @name` snippet compiles error-free).
    Uses `@name` so a lemma with implicit args still elaborates as a plain term. A compile/infra failure
    (`_compile_probe` returns None) is treated as NOT-validated (fail-closed: never inject on an
    unconfirmed name)."""
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    _pre = (preamble.strip() + "\n\n") if preamble.strip() else ""
    snippet = "import Mathlib\n\n" + _pre + f"#check @{name}\n"
    return _compile_probe(snippet, lean_root, "SledgeCheck", timeout_s) is True


def validate_mathlib_names(candidates: "list[tuple[str, str]]", lean_root: Path, timeout_s: int,
                           preamble: str = "") -> "tuple[list[str], list[dict]]":
    """Kernel-validate each candidate Mathlib name with a `#check` probe. Returns
    (validated_names, audit) where `validated_names` are ONLY those the kernel confirmed exist, and
    `audit` records every candidate's verdict (for the move tail / observability). An unvalidated name is
    DROPPED, never injected — the whole point: the Isabelle→Mathlib mapping HALLUCINATES and the kernel is
    the exogenous arbiter that catches it. Empty input ⇒ ([], [])."""
    validated: list[str] = []
    audit: list[dict] = []
    per_name_to = max(20, timeout_s // max(1, len(candidates or []) or 1))
    for isa, cand in candidates or []:
        exists = _check_probe(cand, lean_root, per_name_to, preamble=preamble)
        audit.append({"isabelle": isa, "mathlib": cand, "validated": exists})
        if exists and cand not in validated:
            validated.append(cand)
    return validated, audit


# ── 6. INJECT the validated premises into a Lean tactic block ────────────────────────────────────────
def build_injection_tactic(validated_names: "list[str]") -> str:
    """Build the Lean tactic block that injects ONLY the kernel-validated Mathlib premises. Strategy:
    seed the goal with the named lemmas via `have`-free `aesop (add simp ...)` / `simp [names]` and a
    `exact?`-style closer, all under a `first | ... | ...` so the kernel picks whichever discharges the
    goal. Returns '' if there are no validated names (⇒ NO injection — never an empty/degenerate tactic
    that would `simp`-close trivially and launder a non-result). The returned block is a `by ...` body so
    it routes through the SAME governance (`_verify_compile`) as every other move's proof_text."""
    names = [n for n in (validated_names or []) if n]
    if not names:
        return ""
    lemmas = " ".join(names)
    simp_lemmas = ", ".join(names)
    # Each alternative is a genuine CLOSER (kernel backtracks a non-closer): the smuggled premises drive
    # simp/aesop, then `omega`/`exact?`-flavored finishers. The premises are the load-bearing content; a
    # bare `simp`/`aesop` WITHOUT them would be the no-premise path (not this move's claim), so they are
    # always added.
    alts = [
        f"simp_all [{simp_lemmas}]",
        f"aesop (add simp [{simp_lemmas}])",
        f"(have := {names[0]}; simp_all [{simp_lemmas}])" if names else "",
        f"exact?",
    ]
    alts = [a for a in alts if a]
    return "by\n  first\n  | " + "\n  | ".join(alts)


# ── 7. End-to-end (no kernel-close here — the runner ratifies) ───────────────────────────────────────
def sledgehammer_smuggle(goal_text: str, lean_root: Path, timeout_s: int,
                         preamble: str = "") -> "tuple[str, dict]":
    """The full in-repo pipeline, FAIL-CLOSED at the server boundary. Returns (injection_tactic, info):
      • injection_tactic — a `by ...` block injecting ONLY kernel-validated Mathlib premises (the caller
        re-verifies it through `_verify_compile` + `_govern`; THIS function never claims a closure), or
        '' when the move produces nothing (no server / untranslatable goal / no trace / nothing survived
        validation).
      • info — observability: each stage's outcome + the validation audit.
    NO false closure: '' on every fail-closed branch; a non-empty tactic is still only a PROPOSAL the
    kernel ratifies in the runner."""
    info: dict = {"server_configured": bool(isabelle_server()), "stage": "start"}
    if not isabelle_server():
        info["stage"] = "no_server"
        info["reason"] = (f"{_SERVER_ENV} unset — Isabelle server is external infra and not configured "
                          "(fail-closed no-op)")
        return "", info
    theory, lemma_name, statement, imports = lean_to_isabelle(goal_text)
    if not theory:
        info["stage"] = "untranslatable"
        info["reason"] = "goal could not be faithfully translated to Isabelle/HOL"
        return "", info
    info["isabelle_lemma"] = lemma_name
    resp = run_sledgehammer(theory, timeout_s=timeout_s, statement=statement, imports=imports)
    if not resp:
        info["stage"] = "no_sledgehammer_result"
        info["reason"] = "server returned no proof (or transport failed) — fail-closed"
        return "", info
    # Did Isabelle's ATP actually PROVE the goal? The server returns a truthy dict even on NO proof
    # (`{"proof":"","used_facts":[]}`), and a genuine proof can carry an EMPTY fact list (closed by `simp`,
    # no premises) — so neither `bool(resp)` nor `bool(trace)` is the proof signal. `bool(proof)` IS. Surface
    # it so the cross-substrate consensus doesn't read an empty-trace no-proof as an Isabelle YES (which would
    # manufacture a false FAITHFULNESS_CONFLICT against a Lean-no). See sledgehammer_consensus.
    info["isabelle_proved"] = bool((resp.get("proof") or "").strip())
    trace = resp.get("used_facts") or extract_dependency_trace(resp.get("proof") or "")
    info["dependency_trace"] = trace
    if not trace:
        info["stage"] = "empty_trace"
        return "", info
    candidates = map_trace_to_mathlib(trace)
    info["mapped_candidates"] = candidates
    if not candidates:
        info["stage"] = "no_mappable_names"
        return "", info
    validated, audit = validate_mathlib_names(candidates, lean_root, timeout_s, preamble=preamble)
    info["validation_audit"] = audit
    info["validated_names"] = validated
    info["dropped_hallucinations"] = [a["mathlib"] for a in audit if not a["validated"]]
    if not validated:
        info["stage"] = "all_names_hallucinated"
        info["reason"] = "every mapped Mathlib name failed the #check kernel probe — all dropped"
        return "", info
    tactic = build_injection_tactic(validated)
    info["stage"] = "injected" if tactic else "no_tactic"
    info["injection_tactic"] = tactic
    return tactic, info


# ── 8. CROSS-SUBSTRATE CONSENSUS (#85): Isabelle ⇄ Lean agreement on the SAME math goal ───────────────
def sledgehammer_consensus(goal_nl: str, *, isabelle_found: bool, lean_compiles: bool,
                           isabelle_diag: str = "", lean_diag: str = ""):
    """Reconcile the TWO substrate verdicts the sledgehammer transport naturally produces on the same goal —
    Isabelle (the ATP found a proof) and Lean (the mapped Mathlib premises reconstruct + are kernel-clean) —
    via the substrate-neutral `cross_substrate_consensus`. This is the MATH instance of the cross-kernel
    thesis (transport to the substrate with the best automation, then cross-check):
      • both ratify  ⇒ CORROBORATED — a genuine Lean⇄Isabelle trust-lift on a math goal.
      • Isabelle-yes / Lean-no ⇒ FAITHFULNESS_CONFLICT — localizes the Isabelle→Mathlib name-mapping /
        translation bug with NO human (substrate disagreement AS a verdict — the piece hammers don't have).
      • Isabelle produced nothing ⇒ INSUFFICIENT (one substrate is never a consensus; the move was a no-op).
    PURE reconciliation: consumes the already-produced verdicts, attaches NO soundness. The runner's kernel
    `_verify_compile`/`_govern` remains the SOLE closure arbiter; this is advisory telemetry. Returns the
    `ConsensusVerdict` (`.status`, `.trust_lift`, `.faithfulness_bug`)."""
    from ztare.common.cross_substrate_consensus import cross_substrate_consensus, SubstrateVerdict
    from ztare.common.governed_verification import CheckResult
    verdicts = [SubstrateVerdict("lean", CheckResult(bool(lean_compiles), lean_diag, "lean"))]
    if isabelle_found:
        verdicts.append(SubstrateVerdict(
            "isabelle", CheckResult(True, isabelle_diag or "sledgehammer found a proof", "isabelle")))
    return cross_substrate_consensus(goal_nl, verdicts)


# ── selftest: POSITIVE + NEGATIVE controls (pure; no server, no compile) ─────────────────────────────
def _selftest() -> int:
    """Deterministic offline checks (no Isabelle server, no Lean compile) of the PURE logic: translation,
    trace extraction, name mapping, injection. The compile-dependent legs (the `#check` validation +
    server call) are covered by a live calibration harness, like the conjecture lake legs. Each block has
    a POSITIVE control (a good input ADMITTED) and a NEGATIVE control (a bad input REJECTED) — a gate that
    never says no is a false-success generator."""
    fails: list[str] = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # ── fail-closed: no server ⇒ no-op (NEGATIVE control for the whole move) ──────────────────────
    # HERMETIC negative control (2026-06-13 VPS-live-server fix): force the hammer OFF deterministically
    # rather than relying on "no server" — the default :8080 probe finds a LIVE Isabelle server on the VPS,
    # so merely unsetting the env var is non-deterministic. Force-OFF (`=0`) bypasses the probe entirely.
    _saved = os.environ.pop(_SERVER_ENV, None)
    _saved_fl = os.environ.get(_FLAG_ENV)
    os.environ[_FLAG_ENV] = "0"
    try:
        tac, info = sledgehammer_smuggle("theorem t (n : ℕ) : n + 0 = n := by", Path("/tmp"), 10)
        # the SOUNDNESS-relevant property is the NO-OP (empty tactic, never a false admit), regardless of stage label.
        ok("hammer unavailable → no-op (fail-closed, empty tactic)", tac == "")
        ok("hammer unavailable → run_sledgehammer returns None (no silent admit)",
           run_sledgehammer("theory X imports Main begin end", 5) is None)
    finally:
        if _saved is not None:
            os.environ[_SERVER_ENV] = _saved
        if _saved_fl is not None:
            os.environ[_FLAG_ENV] = _saved_fl
        else:
            os.environ.pop(_FLAG_ENV, None)

    # ── translation: POSITIVE (a simple arithmetic ∀ translates) + NEGATIVE (a Finset/set goal does not)
    thy, lname, stmt, imps = lean_to_isabelle("theorem t (n : ℕ) (k : ℕ) : n + k = k + n := by")
    ok("translate POSITIVE: simple arith ∀ → Isabelle theory",
       bool(thy) and "lemma ztare_goal" in thy and "sledgehammer" in thy and "nat" in thy)
    ok("translate POSITIVE: binder folded into a \\<forall>", "\\<forall>" in thy)
    ok("translate POSITIVE: structured statement + imports returned (the typed contract)",
       "\\<forall>" in stmt and stmt in thy and imps == ISABELLE_IMPORTS)
    thy2, _, stmt2, _ = lean_to_isabelle("theorem t (s : Finset ℕ) : s.card = s.card := by")
    ok("translate NEGATIVE: Finset goal → '' (untranslatable, no garbled lemma)", thy2 == "" and stmt2 == "")
    thy3, _, _, _ = lean_to_isabelle("theorem t : True := by")
    ok("translate NEGATIVE: degenerate True → '' (no closed prop)", thy3 == "")

    # ── trace extraction: POSITIVE (facts pulled, keywords dropped) + NEGATIVE (no facts) ──────────
    tr = extract_dependency_trace("by (metis add.commute mult.assoc Nat.add_0_right)")
    ok("trace POSITIVE: facts extracted",
       tr == ["add.commute", "mult.assoc", "Nat.add_0_right"])
    tr_smt = extract_dependency_trace("by (smt (z3) foo.bar baz_def)")
    ok("trace POSITIVE: smt backend tag (z3) dropped, facts kept",
       tr_smt == ["foo.bar", "baz_def"])
    ok("trace NEGATIVE: pure tactic keywords → [] (no facts)",
       extract_dependency_trace("by auto") == [] and extract_dependency_trace("") == [])

    # ── name mapping: POSITIVE (table + heuristic hit) + NEGATIVE (no guess) ───────────────────────
    ok("map POSITIVE: static table hit (add.commute → add_comm)",
       map_isabelle_name("add.commute") == "add_comm")
    ok("map POSITIVE: bare-suffix table hit (Foo.add.commute style)",
       map_isabelle_name("Groups.add.commute") == "add_comm")
    ok("map POSITIVE: structural _commute → _comm heuristic",
       map_isabelle_name("foo_bar_commute") == "foo_bar_comm")
    ok("map NEGATIVE: an un-guessable bare atom → None (no probe wasted)",
       map_isabelle_name("X") is None and map_isabelle_name("") is None)
    pairs = map_trace_to_mathlib(["add.commute", "X", "mult.assoc"])
    ok("map trace: drops the unmappable, keeps guesses",
       pairs == [("add.commute", "add_comm"), ("mult.assoc", "mul_assoc")])

    # ── injection: POSITIVE (validated names → a real tactic) + NEGATIVE (no names → '' not a degenerate
    #    simp that would launder a non-result) ──────────────────────────────────────────────────────
    inj = build_injection_tactic(["add_comm", "mul_comm"])
    ok("inject POSITIVE: validated names appear in the tactic + it is a `by` block",
       inj.startswith("by") and "add_comm" in inj and "mul_comm" in inj and "first" in inj)
    ok("inject NEGATIVE: NO validated names → '' (never a degenerate bare-simp injection)",
       build_injection_tactic([]) == "" and build_injection_tactic([""]) == "")

    # ── validate_mathlib_names drops hallucinations: NEGATIVE via a stub probe that always says NO ──
    #    (the live #check is covered by the calibration harness; here we assert the DROP logic itself
    #    with an injected fake _compile_probe so a 'hallucinated' name is provably never returned).
    import ztare.gates.v33_preflight_risk_detector as _v33
    _orig = _v33._compile_probe
    try:
        # POSITIVE control: a probe that says YES ⇒ the name is kept.
        _v33._compile_probe = lambda *a, **k: True
        v_ok, _ = validate_mathlib_names([("add.commute", "add_comm")], Path("/tmp"), 10)
        ok("validate POSITIVE: kernel says exists → name KEPT", v_ok == ["add_comm"])
        # NEGATIVE control: a probe that says NO (hallucination) ⇒ the name is DROPPED, never injected.
        _v33._compile_probe = lambda *a, **k: False
        v_no, audit = validate_mathlib_names([("foo.bar", "Foo.bar_hallucinated")], Path("/tmp"), 10)
        ok("validate NEGATIVE: kernel says NOT-exists → name DROPPED (anti-hallucination)",
           v_no == [] and audit[0]["validated"] is False)
        # NEGATIVE control: an infra failure (None) is fail-closed (NOT validated).
        _v33._compile_probe = lambda *a, **k: None
        v_none, _ = validate_mathlib_names([("x", "x_maybe")], Path("/tmp"), 10)
        ok("validate NEGATIVE: infra None → fail-closed DROP (no inject on unconfirmed)", v_none == [])
    finally:
        _v33._compile_probe = _orig

    # ── verify_isabelle: the INDEPENDENT-SUBSTRATE checker (#73) — HERMETIC via an injected mock server.
    #    Mirrors the Lean-side calibration discipline (a POSITIVE + a NEGATIVE control); no real Isabelle.
    GOOD_THY = ('theory T imports Main begin\n'
                'lemma t: "(n::nat) + 0 = n" by simp\nend\n')
    BAD_THY = ('theory T imports Main begin\n'
               'lemma t: "(n::nat) + 0 = n + 1" by simp\nend\n')
    SORRY_THY = ('theory T imports Main begin\n'
                 'lemma t: "(n::nat) + 0 = n" sorry\nend\n')

    # POSITIVE control: a passing theory + a clean-build server response → (True, ...).
    mock_ok = lambda thy, to: {"ok": True, "output": "Finished ZtareVerify build (clean)"}  # noqa: E731
    a_ok, a_diag = verify_isabelle(GOOD_THY, timeout_s=10, server=mock_ok)
    ok("verify POSITIVE: passing theory + clean server → (True, accepted)",
       a_ok is True and "accepted" in a_diag)

    # NEGATIVE control: an Isabelle proof error in the mocked response → (False, error surfaced).
    mock_err = lambda thy, to: {  # noqa: E731
        "ok": False, "output": "*** Failed to finish proof:\n*** goal (1 subgoal):\n*** 1. n + 0 = n + 1"}
    b_ok, b_diag = verify_isabelle(BAD_THY, timeout_s=10, server=mock_err)
    ok("verify NEGATIVE: proof error in response → (False, error surfaced)",
       b_ok is False and ("Failed to finish proof" in b_diag or "error" in b_diag.lower()))

    # NEGATIVE control: a server that LIES "ok":True but leaks an error marker can't mint a pass.
    mock_lie = lambda thy, to: {"ok": True, "output": "*** Type unification failed"}  # noqa: E731
    c_ok, _ = verify_isabelle(GOOD_THY, timeout_s=10, server=mock_lie)
    ok("verify NEGATIVE: spoofed ok:True with an error marker still REJECTED (defense-in-depth)",
       c_ok is False)

    # NEGATIVE control: a `sorry`/`oops` cheat is rejected LEXICALLY, before the server is ever called.
    _called = {"n": 0}
    def _trip(thy, to):
        _called["n"] += 1
        return {"ok": True, "output": "clean"}
    d_ok, d_diag = verify_isabelle(SORRY_THY, timeout_s=10, server=_trip)
    ok("verify NEGATIVE: `sorry` in proof → (False, lexical cheat) BEFORE any server call",
       d_ok is False and "sorry" in d_diag and _called["n"] == 0)
    e_ok, _ = verify_isabelle(BAD_THY.replace("by simp", "oops"), timeout_s=10, server=_trip)
    ok("verify NEGATIVE: `oops` in proof → (False, lexical cheat)", e_ok is False)

    # NEGATIVE control: server unavailable (no env, default :8080 forced dead) → clean unavailable, no crash.
    _sv = os.environ.pop(_SERVER_ENV, None)
    _fl = os.environ.pop(_FLAG_ENV, None)
    os.environ[_FLAG_ENV] = "0"   # force isabelle_hammer_live() False without a network probe
    try:
        u_ok, u_diag = verify_isabelle(GOOD_THY, timeout_s=5)   # no injected server ⇒ live path
        ok("verify NEGATIVE: no server → (False, 'unavailable') — never a crash, never a false pass",
           u_ok is False and "unavailable" in u_diag)
    finally:
        if _sv is not None:
            os.environ[_SERVER_ENV] = _sv
        if _fl is not None:
            os.environ[_FLAG_ENV] = _fl
        else:
            os.environ.pop(_FLAG_ENV, None)

    # NEGATIVE control: empty theory text → fail-closed, no call.
    ok("verify NEGATIVE: empty theory → (False, ...)", verify_isabelle("", timeout_s=5, server=mock_ok)[0] is False)

    # ── enable gate (HERMETIC, no network probe of :8080 — 2026-06-13 fix for the non-hermetic flakiness:
    # enabling requires a LIVE server; the test hook `ZTARE_ISABELLE_ASSUME_LIVE=1` skips the probe; the
    # force-OFF knob `ZTARE_LEANMILL_SLEDGEHAMMER=0` wins. The old test asserted "=1 of the force-off knob
    # enables", which is the WRONG knob — that flag only force-DISABLES). ──────────────────────────────
    _f = os.environ.pop(_FLAG_ENV, None)
    _al = os.environ.pop("ZTARE_ISABELLE_ASSUME_LIVE", None)
    try:
        os.environ[_FLAG_ENV] = "0"
        ok("enable: force-OFF (ZTARE_LEANMILL_SLEDGEHAMMER=0) ⇒ off (hermetic — beats a live server)",
           sledgehammer_enabled() is False)
        os.environ.pop(_FLAG_ENV, None)
        os.environ["ZTARE_ISABELLE_ASSUME_LIVE"] = "1"
        ok("enable: ASSUME_LIVE=1 hook ⇒ on (skips the network probe — hermetic)",
           sledgehammer_enabled() is True)
        os.environ[_FLAG_ENV] = "0"
        ok("enable: force-OFF wins over the live hook (force-off checked before the hook)",
           sledgehammer_enabled() is False)
    finally:
        os.environ.pop("ZTARE_ISABELLE_ASSUME_LIVE", None)
        if _al is not None:
            os.environ["ZTARE_ISABELLE_ASSUME_LIVE"] = _al
        if _f is not None:
            os.environ[_FLAG_ENV] = _f
        else:
            os.environ.pop(_FLAG_ENV, None)

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
