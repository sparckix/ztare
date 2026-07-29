#!/usr/bin/env python3
"""v33_preflight_risk_detector.py — the governance harness's missing organ.

Closes the gap the operator flagged: tick541 / carleman vacuity was caught
OFFLINE by GPT-5.5, NOT by the harness. This builds the preflight,
statement-level, LEAKAGE-INDEPENDENT vacuity/risk detector + an independent
Lean verifier that confirms vacuity WITHOUT any audit verdict.

This is the leakage-independent failure-attestation mechanism the converged
terminal finding said was missing. It is primitive-first and immediately
validatable on documented ground truth.

Two components:
  1. detect_risks(statement)  — deterministic statement-shape flags, NO proof,
     NO audit verdict. Flags:
       - vacuous_True_hypothesis     : a hypothesis of type exactly `True`
       - vacuous_trivial_exists_hyp  : `∃ x : T, <trivially-satisfiable>`
       - vacuous_exists_prop_concl   : conclusion `∃ _ : Prop, _`  (⟨True,trivial⟩)
       - literal_True_conclusion     : conclusion is `True`
       - opaque_predicate_present    : statement uses `opaque` (REAL content — anti-flag)
  2. independent_verify(stmt, imports, sandbox) — synthesize a probe
     `example : <stmt> := by (first | trivial | exact ⟨trivial⟩ | tauto | simp)`
     and Lean-compile. If it closes by a trivial tactic → vacuity CONFIRMED,
     leakage-independent (no reference to any kill verdict).

Ground-truth validation built in (--validate): the pre-fix carleman
backward-uniqueness pattern (MUST flag) vs the opaque-fixed version
(MUST NOT flag).
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
DEFAULT_SANDBOX = ROOT / ("analytics/public/leanmill/external_benchmarks/"
                          "sandboxes/v28A_carleson_baseline/carleson")
LEAN_ERR_RE = re.compile(r"^\S*\.lean:\d+:\d+: error:", re.MULTILINE)


# ---------------------------------------------------------------------------
# Component 1 — deterministic statement-shape risk detector (NO proof, NO audit)
# ---------------------------------------------------------------------------

_REL_TOKENS = ["↔", "≤", "≥", "<", ">", "=", "∣"]


def _conclusion(s: str) -> str:
    """The conclusion = text after the THEOREM TYPE colon. The type colon is the first top-level `:`
    that is NOT inside a `∀`/`∃`/`λ`/`Σ`/`Π` binder (those carry their own `:` — e.g. `∃ δ : ℝ, …` — and
    splitting on the LAST top-level `:` garbled every ∃/∀-conclusion statement: 2026-06-04 overfit pass).
    A raw proposition that STARTS with a quantifier has no type colon ⇒ the whole string is the conclusion."""
    body = re.split(r":=", s, 1)[0]
    depth = 0
    in_binder = False  # between a top-level ∀/∃/λ/Σ/Π and its closing comma
    for i, ch in enumerate(body):
        if ch in "([{⦃":
            depth += 1
        elif ch in ")]}⦄":
            depth -= 1
        elif depth == 0:
            if ch in "∀∃λΣΠ":
                in_binder = True
            elif ch == "," and in_binder:
                in_binder = False
            elif ch == ":" and not in_binder:
                return body[i + 1:].strip()      # the theorem type colon
    return body.strip()


def _norm_term(t: str) -> str:
    """Whitespace/paren/`id`-insensitive normal form so `f x`, `(f x)`, `id (f x)` compare equal —
    defeats the trivial wrappers the red-team used to slip a reflexive/circular goal past byte-equality."""
    t = re.sub(r"\bid\b\s*", "", t or "")
    return re.sub(r"[()\s]", "", t)


def _top_split_rel(concl: str, rel: str) -> "tuple[str, str] | None":
    """Split the conclusion on `rel` at paren-depth 0 (so a buried rel inside a domain isn't matched)."""
    depth = 0
    for i, ch in enumerate(concl):
        if ch in "([{⦃":
            depth += 1
        elif ch in ")]}⦄":
            depth -= 1
        elif depth == 0 and concl[i:i + len(rel)] == rel:
            # avoid matching '=' inside ':=' / '≤' as '<' etc. (rel tokens are distinct chars; ':=' stripped)
            return concl[:i].strip(), concl[i + len(rel):].strip()
    return None


def _hyp_types(s: str) -> list:
    """Explicit binder TYPES `(name : type)` — for the circular (conclusion ≡ a hypothesis) check."""
    out = []
    for m in re.finditer(r"\(([^():]+):([^()]+)\)", s):
        out.append(m.group(2).strip())
    return out


def detect_risks(statement: str) -> dict:
    """statement = the Lean type (hypotheses + conclusion), no `:= proof`."""
    s = statement
    flags: list[str] = []

    # opaque present → real content, strong ANTI-vacuity signal
    has_opaque = bool(re.search(r"\bopaque\b", s))

    # Split hypotheses (paren / bracket binders) from conclusion (after last top-level `:`)
    # Hypotheses of literal type True:  `(name : True)` or `: True →` or `, True →`
    if re.search(r"\(\s*[\w']+\s*:\s*True\s*\)", s) or re.search(r":\s*True\s*(?:→|\bto\b)", s):
        flags.append("vacuous_True_hypothesis")

    # Trivially-satisfiable existential HYPOTHESIS (inside a binder, NOT the conclusion): ∃ x : ℝ, 0 < x …
    # Scoped to hypothesis binder types — scanning the whole statement hard-false-flagged genuine
    # CONCLUSION existentials (ε–δ: `… → ∃ δ : ℝ, 0 < δ`); the red-team corpus caught that FP (2026-06-04).
    for _ht in _hyp_types(s):           # PER hyp type — a joined blob only let the LAST ∃-hyp terminate
        matched = False                  # cleanly (`$`), so the leg was positionally dead (overfit pass 2026-06-04)
        for m in re.finditer(r"∃\s*[\w']+\s*:\s*(ℝ|ℕ|ℤ|Nat|Real|Int)\s*,\s*(.+?)(?:,|→|$)", _ht):
            body = m.group(2).strip()
            if re.match(r"0\s*<\s*[\w']+$", body) or re.match(r"[\w']+\s*>\s*0$", body) \
               or body in ("True",) or re.match(r"[\w']+\s*=\s*[\w']+$", body):
                flags.append("vacuous_trivial_exists_hyp")
                matched = True
                break
        if matched:
            break

    # ∃ _ : Prop, _   conclusion (the ⟨True, trivial⟩ shape)
    if re.search(r"∃\s*[\w']+\s*:\s*Prop\s*,\s*[\w']+\s*$", s) or \
       re.search(r"∃\s*[\w']+\s*:\s*Prop\s*,\s*[\w']+\s*\)?\s*$", s):
        flags.append("vacuous_exists_prop_concl")

    # conclusion literally True (last top-level token)
    if re.search(r"(?::|→|,)\s*True\s*$", s.strip()):
        flags.append("literal_True_conclusion")

    # single-lemma-exact candidate: very short statement, single relation, no binders chain
    if len(s) < 90 and s.count("→") == 0 and s.count("∀") <= 1 and ("=" in s or "≤" in s or "<" in s):
        flags.append("single_lemma_exact_candidate")

    # --- semantic-degeneracy classes the 2026-06-04 red-team showed escape every existing organ ---
    concl = _conclusion(s)
    nconcl = _norm_term(concl)
    # reflexive conclusion: `X <rel> X`, lhs≡rhs over ANY relation (=,≤,≥,<,>,↔) — paren/id/ws-normalized
    # so `u x = u x`, `(f a) ≤ f a`, `id P ↔ P` are caught (the trivial-wrapper evasions).
    for _rel in _REL_TOKENS:
        _sp = _top_split_rel(concl, _rel)
        if _sp and _norm_term(_sp[0]) and _norm_term(_sp[0]) == _norm_term(_sp[1]):
            flags.append("reflexive_conclusion")
            break
    # circular: the conclusion is (normalized) one of the hypothesis types (assume-conclusion)
    if len(concl.strip()) >= 3 and nconcl and any(_norm_term(h) == nconcl for h in _hyp_types(s)):
        flags.append("circular_conclusion")
    # empty-domain / vacuous quantification: `∈ ∅` / `Finset.range 0` / `Fin 0`, or a hyp `S = ∅` whose S
    # bounds the conclusion (quantifying over an empty domain is vacuously true).
    # empty OPEN interval with equal bounds: Ioo a a = Ico a a = Ioc a a = ∅ (Icc a a = {a} is NOT empty).
    _empty_interval = re.search(r"\bI(?:oo|co|oc)\s+([\w'.]+)\s+([\w'.]+)", concl)
    if re.search(r"∈\s*\(?\s*∅", concl) or re.search(r"\bFinset\.range\s+0\b", concl) \
       or re.search(r":\s*Fin\s+0\b", s) \
       or (_empty_interval and _norm_term(_empty_interval.group(1)) == _norm_term(_empty_interval.group(2))):
        flags.append("empty_domain_quantification")
    else:
        _me = re.search(r"\(\s*[\w']+\s*:\s*([\w']+)\s*=\s*∅\s*\)", s)
        if _me and re.search(r"(?<![\w'])" + re.escape(_me.group(1)) + r"(?![\w'])", concl):
            flags.append("empty_domain_quantification")
    # unanchored OPAQUE OBJECT (autoformalizer faithfulness — ADVISORY): a statement-local binder whose
    # type is or ends in Sort/Prop/Type is an INTRODUCED predicate / type / proposition — the agent
    # smuggling in the very object the claim is ABOUT (research-math formalizations forced by Mathlib's
    # gaps do exactly this: `(IsTaylorOfAlgebraic : PowerSeries ℚ → Prop)`, `(genus : Scheme → ℕ)`…).
    # The master-discriminator made structural: a faithful formalization names objects that EXIST; an
    # opaque shell introduces them as undefined binders. ADVISORY only (a genuine general lemma may
    # legitimately quantify over a predicate) — route to the cold judge / decline, never a lexical hard-block.
    _opaque = [t for t in _hyp_types(s)
               if re.search(r"(?:->|→)\s*(?:Prop|Sort\b|Type\b)", t) or re.match(r"\s*(?:Prop|Sort\b|Type\b)", t)]
    if _opaque:
        flags.append("unanchored_opaque_object")

    # degenerate-sign SUSPECT (ADVISORY — confirm via the exogenous probe, see independent_verify): a hyp
    # `v ≤ 0` / `v = 0` whose v also bounds the conclusion's domain (collapses e.g. `Icc 0 v` to a point).
    for _ms in re.finditer(r"\(\s*[\w']+\s*:\s*([\w']+)\s*(?:≤\s*0|=\s*0)\s*\)", s):
        if re.search(r"(?<![\w'])" + re.escape(_ms.group(1)) + r"(?![\w'])", concl):
            flags.append("degenerate_sign_suspect")
            break

    return {
        "statement_preview": s.strip()[:200],
        "risk_flags": sorted(set(flags)),
        "opaque_predicate_present": has_opaque,
        # HARD vacuity = the CONCLUSION is vacuously/trivially true by structure (empty domain, reflexive,
        # circular, literal True, ∃Prop ⟨True,_⟩). DECORATIVE-HYPOTHESIS smells are ADVISORY, not hard: a
        # trivial-∃ hyp (`degenerate_sign_suspect` likewise) on a GENUINE conclusion does NOT make the
        # theorem vacuous — flagging it hard is an FP (overfit pass 2026-06-04). `vacuous_True_hypothesis`
        # and `vacuous_exists_prop_concl` stay hard: a True-hyp formalization dropped a hypothesis, and an
        # ∃Prop conclusion IS the ⟨True,trivial⟩ vacuity. Contradictory-hyp vacuity is SEMANTIC → the probe.
        "vacuity_suspected": (not has_opaque) and any(
            (f.startswith("vacuous_") and f != "vacuous_trivial_exists_hyp")
            or f in ("literal_True_conclusion", "reflexive_conclusion",
                     "circular_conclusion", "empty_domain_quantification")
            for f in flags
        ),
    }


# ---------------------------------------------------------------------------
# Component 2 — independent Lean verifier (confirms vacuity, NO audit verdict)
# ---------------------------------------------------------------------------

def independent_verify(statement: str, imports: list[str], sandbox: Path,
                       timeout: int = 60) -> dict:
    """Synthesize `example : <statement> := by <trivial-cascade>` and compile.
    If it closes by a trivial tactic, vacuity is CONFIRMED leakage-independent.
    """
    if not sandbox.exists():
        return {"verified": None, "error": f"sandbox missing: {sandbox}"}
    imp = "\n".join(imports) if imports else "import Mathlib"
    probe = (
        f"{imp}\n\n"
        f"-- v33 independent vacuity probe (no audit verdict referenced)\n"
        f"example : {statement.strip()} := by\n"
        f"  first\n"
        f"  | trivial\n"
        f"  | exact ⟨trivial⟩\n"
        f"  | exact ⟨True, trivial⟩\n"
        f"  | exact ⟨1, by norm_num⟩\n"
        f"  | tauto\n"
        f"  | simp_all\n"
    )
    tmpdir = sandbox / "V33VacuityProbe"
    tmpdir.mkdir(exist_ok=True)
    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".lean", dir=str(tmpdir), delete=False)
    tf.write(probe)
    tf.close()
    rel = Path(tf.name).relative_to(sandbox)
    started = time.time()
    try:
        proc = subprocess.run(
            ["nice", "-n", "10", "lake", "env", "lean", str(rel)],
            cwd=str(sandbox), text=True, capture_output=True, timeout=timeout, check=False,
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        err = bool(LEAN_ERR_RE.search(out))
        closed_trivially = (proc.returncode == 0) and (not err)
        return {
            "verified": closed_trivially,         # True = vacuity CONFIRMED independently
            "elapsed_s": round(time.time() - started, 2),
            "probe_preview": probe[:400],
            "error_tail": out[-300:] if err else "",
        }
    except subprocess.TimeoutExpired:
        return {"verified": None, "timed_out": True, "elapsed_s": timeout}
    except Exception as e:
        return {"verified": None, "error": str(e)}


def _compile_probe_standalone(probe: str, sandbox: Path, tag: str, timeout: int) -> "bool | None":
    """Compile a Lean snippet in the sandbox; True=clean, False=error, None=infra failure."""
    sandbox = Path(sandbox).resolve()
    if not sandbox.exists():
        return None
    # WARM/VERIFY PARITY (RCA 2026-06-12): the warm REPL path (below) has Mathlib PRE-LOADED so an import-less
    # snippet passes, but the cold `lake env lean` path needs the header — without it a VALID proof false-errors.
    # Ensure the substrate header so BOTH paths see the same self-contained probe (canonical helper, idempotent).
    try:
        from ztare.leanmill.lean_source import ensure_import_header
        probe = ensure_import_header(probe)
    except Exception:  # noqa: BLE001 — never break the gate on the helper
        pass
    # REPL-backed fast path (ZTARE_LEANMILL_REPL_COMPILE=1 + a LIVE toolchain-matched repl over `sandbox`):
    # a warm PersistentLean elaborates in ~0.1s vs the ~60-90s cold `lake env lean` reload below — SAME verdict
    # contract as the cold path: clean ⇔ no `error:` line. SORRY IS ALLOWED ON BOTH PATHS BY DESIGN — this probe
    # AUDITS sorried decomposition DAGs (a sorried sub-lemma must still COMPILE as a placeholder), so it calls
    # `compile_probe_via_repl` with the default `reject_sorry=False` and the cold path below only screens
    # `LEAN_ERR_RE`. DO NOT add a sorry-reject here: a True from `_compile_probe` means "compiles", NOT
    # "sorry-free" — the no-false-closure checkers that need sorry-free are `LeanLakeChecker.verify` /
    # `_is_compile_ok` (reject_sorry=True), NOT this one. Returns None when unusable (flag off / toolchain
    # mismatch / dead) ⇒ fall through to the canonical compile (byte-parity when off). Never breaks the cold path.
    try:
        from ztare.formal.repl_compile import compile_probe_via_repl
        _r = compile_probe_via_repl(probe, sandbox, timeout)
        if _r is not None:
            # A warm success is sufficient.  A warm failure is not: imported project modules can be absent from
            # the base REPL environment even though the same complete file compiles under ``lake env lean``.
            # Treat the negative as an optimization miss and fall through to the canonical cold compiler.
            if _r[0] is True:
                return True
    except Exception:  # noqa: BLE001
        pass
    d = sandbox / tag
    d.mkdir(exist_ok=True)
    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".lean", dir=str(d), delete=False)
    tf.write(probe); tf.close()
    rel = Path(tf.name).relative_to(sandbox)
    try:
        proc = subprocess.run(["nice", "-n", "10", "lake", "env", "lean", str(rel)],
                              cwd=str(sandbox), text=True, capture_output=True, timeout=timeout, check=False)
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return (proc.returncode == 0) and (not LEAN_ERR_RE.search(out))
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def _compile_probe(probe: str, sandbox: Path, tag: str, timeout: int) -> "bool | None":
    """STRICT-SAFE CAMPAIGN-AWARE compile (2026-06-20). Standalone first (self-contained probes pass here ⇒
    zero regression, byte-parity when no campaign substrate is registered); ONLY on a standalone compile
    FAILURE, retry the probe against the registered campaign theory ENV (namespace-wrapped) so a probe that
    references campaign-theory defs resolves instead of `unknown identifier`. This is the campaign-blind
    `_compile_probe` bug class (it killed the proposer pool on every namespaced P1 rung). It can ONLY turn a
    false-FAIL into a pass — never breaks a passing probe — and the downstream sorry-free / anti-laundering /
    #print-axioms gates are UNCHANGED (this is compile reachability, not a closure gate; `sorry` stays allowed
    on both paths since this probe audits sorried decomposition DAGs).

    WARM-FIRST when a substrate is registered (2026-06-25, the single warm-compile door): a campaign probe
    references substrate defs absent from bare Mathlib, so standalone-first ALWAYS fails first → a doomed
    ~73-156s cold Mathlib re-import before the warm retry (the cold-Lake tax). Try the warm env FIRST (~0.1s)
    and SHORT-CIRCUIT only on warm-SUCCESS; a warm-fail/miss falls through to the authoritative standalone, so a
    self-contained probe the namespace-wrap might perturb is still judged cold (no regression — strictly ≥ the
    old path, which paid cold THEN warm on every campaign probe). ZTARE_LEANMILL_WARM_COMPILE=0 reverts."""
    if os.environ.get("ZTARE_LEANMILL_WARM_COMPILE", "1") != "0":
        try:
            from ztare.formal.repl_compile import (get_campaign_substrate, campaign_file_env,
                                                   campaign_namespaces, compile_probe_via_repl)
            _sub = get_campaign_substrate()
            if _sub:
                _sb = Path(sandbox).resolve()
                _env = campaign_file_env(_sub, _sb)
                if _env is not None:
                    _nss = campaign_namespaces()
                    _wp = (f"namespace {_nss[0]}\n{probe}\nend {_nss[0]}\n"
                           if (len(_nss) == 1 and "namespace " not in probe) else probe)
                    _rr = compile_probe_via_repl(_wp, _sb, timeout, env=_env)
                    if isinstance(_rr, tuple) and _rr[0] is True:
                        return True                # warm CONFIRMED — skip the doomed cold compile
        except Exception:  # noqa: BLE001 — warm is best-effort; the standalone path below is the fallback
            pass
    r = _compile_probe_standalone(probe, sandbox, tag, timeout)
    if r is not False:
        return r                                   # clean / infra-unavailable ⇒ standalone verdict stands
    try:
        from ztare.formal.repl_compile import (get_campaign_substrate, campaign_file_env,
                                               campaign_namespaces, compile_probe_via_repl)
        _sub = get_campaign_substrate()
        if _sub:
            _sb = Path(sandbox).resolve()
            _env = campaign_file_env(_sub, _sb)
            if _env is not None:
                _nss = campaign_namespaces()
                _wp = (f"namespace {_nss[0]}\n{probe}\nend {_nss[0]}\n"
                       if (len(_nss) == 1 and "namespace " not in probe) else probe)
                _rr = compile_probe_via_repl(_wp, _sb, timeout, env=_env)
                if isinstance(_rr, tuple):
                    return _rr[0]
    except Exception:  # noqa: BLE001 — env rescue is best-effort; the standalone False stands (fail-closed)
        pass
    return False


def nondegenerate_instance_probe(statement: str, sandbox: Path, imports: "list[str] | None" = None,
                                 timeout: int = 90) -> dict:
    """EXOGENOUS teeth for hidden vacuity — the master-discriminator as a Lean compile.

    A lexically-flagged vacuity suspect (reflexive / empty-domain / S=∅ / circular) is CONFIRMED only
    if the KERNEL can prove that no NON-DEGENERATE instance exists: concrete values satisfying the
    hypotheses for which the conclusion's quantified domain is inhabited. We build the refutation
    target  `¬ (∃ <explicit values>, <hyps> ∧ <conclusion-domain non-empty>)`  and compile it.
      • refutation COMPILES  → no non-degenerate instance → vacuity CONFIRMED (exogenous, sound).
      • refutation fails / indeterminate → stay ADVISORY (never false-confirm on prover weakness).
    This distinguishes *vacuously* true from *genuinely* trivially true, which `independent_verify`
    alone cannot. ADVISORY-first per §3b — promote to fail-closed only after adversarial survival."""
    imp = "\n".join(imports) if imports else "import Mathlib"
    concl = _conclusion(statement)
    head = statement[:statement.rfind(concl)] if (concl and concl in statement) else statement
    implicit = " ".join(re.findall(r"[\{\[][^\}\]]*[\}\]]", head))          # {..}/[..] kept verbatim
    explicit = re.findall(r"\(([^():]+):([^()]+)\)", head)                  # (name : type)
    REL = ("=", "<", "≤", "≥", "∈", "≠", "↔", "∧", "∨")
    values = [(n.strip(), t.strip()) for n, t in explicit if not any(r in t for r in REL)]
    hyps = [t.strip() for n, t in explicit if any(r in t for r in REL)]
    mdom = re.search(r"∀\s*[\w']+\s*∈\s*([^,]+?),", concl)
    if mdom:
        domain_nonempty = f"∃ _z ∈ ({mdom.group(1).strip()}), True"
    elif values:
        domain_nonempty = "True"                                            # conclusion ranges over the values
    else:
        return {"nondegenerate": None, "reason": "no parseable domain/values (advisory)"}
    ex_vars = " ".join(f"({n} : {t})" for n, t in values)
    parts = [h for h in hyps] + ([domain_nonempty] if domain_nonempty != "True" else [])
    conj = " ∧ ".join(parts) if parts else "True"
    target = f"∃ {ex_vars}, {conj}" if ex_vars else conj
    if target == "True":
        return {"nondegenerate": None, "reason": "trivial target (advisory)"}
    # EVERY branch must CLOSE-or-FAIL: a bare `simp_all`/`simp` SUCCEEDS without closing, so `first` would
    # commit to it and shadow the later linarith/omega (the real_disjoint miss, 2026-06-04). Each arity
    # therefore folds linarith|omega|(simp_all;done)|(norm_num;done) so a non-closer backtracks. linarith/
    # omega refute a genuinely-UNSATISFIABLE hyp set and CANNOT prove a false goal ⇒ sound (no false-confirm).
    _close = "first | linarith | omega | (simp_all; done) | (norm_num; done) | (decide)"
    refute = (
        f"{imp}\n\nexample {implicit} : ¬ ({target}) := by\n"
        f"  first\n"
        f"  | (rintro ⟨x, _⟩; exact isEmptyElim x)\n"
        f"  | (rintro ⟨_, _⟩; {_close})\n"
        f"  | (rintro ⟨_, _, _⟩; {_close})\n"
        f"  | (rintro ⟨_, _, _, _⟩; {_close})\n"
        f"  | (rintro ⟨_, _, _, _, _⟩; {_close})\n"
        f"  | (rintro ⟨_, _, _, _, _, _⟩; {_close})\n"
        f"  | (intro _; aesop)\n"
        f"  | (intro _; (simp_all; done))\n"
        f"  | decide\n"
    )
    exists_p = (
        f"{imp}\n\nexample {implicit} : ({target}) := by\n"
        f"  first | exact ⟨by infer_instance⟩ | (refine ⟨?_, ?_⟩ <;> simp_all) | aesop | simp | norm_num | decide\n"
    )
    refuted = _compile_probe(refute, sandbox, "V33NonDegRefute", timeout)
    if refuted is True:
        return {"nondegenerate": False, "vacuity_confirmed": True, "carrier": "lean_refutation",
                "target": target, "note": "kernel proved NO non-degenerate instance exists → vacuous"}
    exists = _compile_probe(exists_p, sandbox, "V33NonDegExists", timeout)
    if exists is True:
        return {"nondegenerate": True, "vacuity_confirmed": False, "carrier": "lean_witness",
                "target": target, "note": "kernel constructed a non-degenerate instance → has content"}
    return {"nondegenerate": None, "vacuity_confirmed": None, "target": target,
            "note": "neither refuted nor witnessed within budget → ADVISORY (prover-weakness-safe)"}


# ---------------------------------------------------------------------------
# Randomized multi-point falsifier (#38) — Schwartz-Zippel ext. of the above
# ---------------------------------------------------------------------------
def _parse_value_binders(statement: str) -> "tuple[list, str]":
    """Extract instantiable (name, type) VALUE binders — explicit `(n:T)` params in the head AND
    leading `∀ n : T,` binders in the conclusion — plus the conclusion body with those leading ∀s
    stripped (so concrete values can be substituted). Hypothesis binders (types containing a relation)
    are excluded; only nameable value variables are returned."""
    concl = _conclusion(statement)
    head = statement[:statement.rfind(concl)] if (concl and concl in statement) else statement
    REL = ("=", "<", "≤", "≥", "∈", "≠", "↔", "∧", "∨", "→")
    vars_ = []
    for names, t in re.findall(r"\(([^():]+):([^()]+)\)", head):
        if any(r in t for r in REL):
            continue
        for n in names.split():                 # split multi-name binders: (a b : ℝ) → a:ℝ, b:ℝ
            if n.strip():
                vars_.append((n.strip(), t.strip()))
    body = concl
    m = re.match(r"\s*∀\s+([\w'\s]+):\s*([^,]+?),\s*(.*)", body, re.DOTALL)
    while m:
        t = m.group(2).strip()
        vars_ += [(n.strip(), t) for n in m.group(1).split() if n.strip()]
        body = m.group(3)
        m = re.match(r"\s*∀\s+([\w'\s]+):\s*([^,]+?),\s*(.*)", body, re.DOTALL)
    return vars_, body.strip()


def randomized_falsification_probe(statement: str, sandbox: Path, k: int = 8, timeout: int = 90,
                                   seed: int = 1729, imports: "list[str] | None" = None) -> dict:
    """Schwartz-Zippel-style EXOGENOUS falsifier for the COMPUTABLE-ALGEBRAIC class (#38, generalizing
    `nondegenerate_instance_probe` from ONE instance to K RANDOM ones). Instantiate the statement's
    value-variables at K random concrete points and try to prove the conclusion FALSE there
    (`¬ concl[vars:=c]` via norm_num/decide). SOUND in the catch direction: a falsification that
    COMPILES ⇒ the conclusion is genuinely false at c (a wording-quirk / false conjectured lemma /
    laundered statement) — the fraud collapses under the random probe. NONE compiling ⇒
    consistent-with-true, ADVISORY (never a false-confirm on prover weakness, and never auto-reject:
    a parsing slip could mis-substitute, so this is advisory and MUST be calibrated on true+false
    controls before any gating). Cheap: concrete evaluation, NO proof search. Best uses: a PRE-PROOF
    filter for conjectured lemmas (#35 — kill a false L before spending a solve) and a multi-point
    strengthening of the #24 vacuity probe. Applies ONLY when every value var is a computable numeric
    type (ℕ/ℤ/ℚ/ℝ/Int/Nat/Rat/Real); otherwise returns an advisory skip."""
    import random as _r
    imp = "\n".join(imports) if imports else "import Mathlib"
    vars_, body = _parse_value_binders(statement)
    if not vars_:
        return {"applicable": False, "reason": "no instantiable value variables (advisory skip)"}
    # SOUNDNESS GUARD (red-team-driven, 2026-06-05): this conclusion-falsifier IGNORES hypotheses, so it
    # is only sound for UNCONDITIONAL statements. A hypothesis-guarded theorem (a binder whose type is a
    # relation/implication, or a top-level → / ↔ in the conclusion) would be FALSE-falsified by random
    # points that violate its hypotheses (e.g. real_ineq `(a b:ℝ)(h:a≤b): a-b≤0` at a=5,b=3). Skip those —
    # hypothesis-guarded vacuity is the randomized-NON-VACUITY probe's job (a separate tool), not this one.
    _HYPREL = ("=", "<", "≤", "≥", "∈", "≠", "↔", "→")
    _concl = _conclusion(statement)
    _head = statement[:statement.rfind(_concl)] if (_concl and _concl in statement) else statement
    # scan the WHOLE head (catches hyp binders the (n:T) regex misses on nested-paren types like
    # `(h : (0:ℝ)=1)`, and function-type binders); a relation in the head ⇒ a hypothesis ⇒ skip (sound).
    if any(s in _head for s in _HYPREL) or "→" in body or "↔" in body:
        return {"applicable": False, "reason": "hypothesis-guarded — conclusion-falsifier ignores hyps (would false-falsify); skip"}
    NUM = ("ℕ", "ℤ", "ℚ", "ℝ", "Nat", "Int", "Rat", "Real")
    if not all(any(c in t for c in NUM) for _, t in vars_):
        return {"applicable": False, "reason": f"non-computable var type(s): {[t for _, t in vars_]} (skip)"}
    rng = _r.Random(seed)

    def _val(t: str) -> str:
        lo = 0 if ("ℕ" in t or "Nat" in t) else -9
        return f"({rng.randint(lo, 17 if lo == 0 else 9)} : {t.strip()})"

    checked = 0
    for i in range(k):
        subs, vals = body, []
        for n, t in vars_:
            v = _val(t)
            subs = re.sub(rf"(?<![\w']){re.escape(n)}(?![\w'])", v, subs)
            vals.append(f"{n}:={v}")
        probe = (f"{imp}\n\nexample : ¬ ({subs}) := by\n"
                 f"  first | norm_num | decide | simp_arith | (norm_num [Finset.sum_range_succ]; done)\n")
        res = _compile_probe(probe, sandbox, f"V33RandFalsify{i}", timeout)
        checked += 1
        if res is True:
            return {"applicable": True, "falsified": True, "carrier": "lean_random_refutation",
                    "counterexample": vals, "k_checked": checked,
                    "note": "conclusion proven FALSE at a random instance → quirk / false lemma / laundered"}
    return {"applicable": True, "falsified": False, "k_checked": checked,
            "note": f"no random refutation across k={checked} — consistent-with-true (ADVISORY, not a proof)"}


# ---------------------------------------------------------------------------
# Ground-truth validation
# ---------------------------------------------------------------------------

GT_POSITIVE = {  # documented-vacuous (pre-fix carleman). detector MUST flag.
    "name": "carleman_prefix_vacuous",
    "statement": "(parabolic_equation : True) → (vanishing_at_tip : ∃ ρ : ℝ, 0 < ρ) → ∃ vanishing_certificate : Prop, vanishing_certificate",
}
GT_NEGATIVE = {  # opaque-fixed version. detector MUST NOT flag (real content).
    "name": "carleman_opaque_fixed",
    "statement": "(hcone : ParabolicEquationOnBackwardCone data v T x r) → (htip : VanishingOnSpatialNeighborhood v T x) → BackwardUniquenessConcluded v T x r",
}


def run_validation() -> dict:
    pos = detect_risks(GT_POSITIVE["statement"])
    neg = detect_risks(GT_NEGATIVE["statement"])
    pos_ok = pos["vacuity_suspected"] is True
    neg_ok = neg["vacuity_suspected"] is False
    verdict = "DETECTOR_VALIDATED" if (pos_ok and neg_ok) else "DETECTOR_FAILS_GROUND_TRUTH"
    return {
        "ground_truth_positive": {**GT_POSITIVE, "detected": pos, "expected_vacuous": True, "pass": pos_ok},
        "ground_truth_negative": {**GT_NEGATIVE, "detected": neg, "expected_vacuous": False, "pass": neg_ok},
        "verdict": verdict,
        "rationale": (
            "detector flags the documented pre-fix carleman vacuity (True-hyp + "
            "trivial-∃-hyp + ∃Prop-concl) AND does NOT flag the opaque-fixed "
            "version — leakage-independent, preflight, no audit verdict used."
            if verdict == "DETECTOR_VALIDATED" else
            f"pos_ok={pos_ok} neg_ok={neg_ok} — shape rules need refinement"
        ),
    }


# --- Red-team corpus (checked-in, runnable — replaces the self-reported "5/6 caught" numbers) -------
# Each laundered case is a degeneracy class; `hard` = the detector must mark it vacuity_suspected
# (fail-closed-eligible), `advisory` = it should FLAG but NOT mark vacuity_suspected (needs the
# exogenous probe / cold judge), `escape` = the LEXICAL detector is expected to MISS it (documents the
# residual the exogenous non-degenerate-instance probe exists to close). Genuine controls MUST never be
# vacuity_suspected; some legitimately trip an ADVISORY flag (the reason advisory legs can't be promoted).
RED_TEAM_LAUNDERED = [   # HARD = vacuous CONCLUSION / empty DOMAIN (structural). Lexical detector must catch.
    ("reflexive_concl",      "(x : ℝ) (f : ℝ → ℝ) : f x = f x", "hard"),
    ("circular_concl",       "(hyp : SomeProp) : SomeProp", "hard"),
    ("empty_domain_fin0",    "(x : Fin 0) : x = x", "hard"),
    ("empty_domain_emptyset","(f : ℕ → ℕ) : ∀ x ∈ (∅ : Finset ℕ), f x = 0", "hard"),
    ("empty_domain_S_eq",    "(S : Set ℝ) (hS : S = ∅) : ∀ x ∈ S, x = 7", "hard"),
    ("empty_interval_Ioo",   "(f : ℝ → ℝ) (a : ℝ) : ∀ x ∈ Set.Ioo a a, f x = 0", "hard"),
    ("vacuous_True_hyp",     "(h : True) (a : ℕ) : a + 0 = a", "hard"),
    ("literal_True_concl",   "(a b : ℕ) : True", "hard"),
    ("exists_prop_concl",    "(data : ℕ) : ∃ cert : Prop, cert", "hard"),
    # ADVISORY = a smell that needs the probe/judge to confirm (a decorative hyp on a genuine conclusion
    # is NOT vacuous — flagging it hard is an FP, so these stay advisory).
    ("sign_collapse",        "(v : ℝ) (hv : v ≤ 0) (f : ℝ → ℝ) : ∀ x ∈ Set.Icc 0 v, f x = 0", "advisory"),
    ("trivial_exists_hyp",   "(h : ∃ x : ℝ, 0 < x) (a b : ℕ) : a + b = b + a", "advisory"),
    ("opaque_object",        "(IsNice : ℕ → Prop) (n : ℕ) : IsNice n ∨ ¬ IsNice n", "advisory"),
    ("quantifier_reorder",   "(f : ℝ → ℝ) : ∃ δ : ℝ, ∀ ε : ℝ, 0 < ε → 0 < δ", "escape"),
]
RED_TEAM_GENUINE = [   # MUST NOT be vacuity_suspected. `adv_ok` = an advisory flag here is expected (not a fail).
    ("peano_induction", "(P : ℕ → Prop) (h0 : P 0) (hs : ∀ n, P n → P (n + 1)) (n : ℕ) : P n", True),
    ("real_ineq",       "(a b : ℝ) (h : a ≤ b) : a - b ≤ 0", False),
    ("am_gm",           "(a b : ℝ) (ha : 0 ≤ a) (hb : 0 ≤ b) : 2 * (a * b) ≤ a ^ 2 + b ^ 2", False),
    ("genuine_forall_exists", "(f : ℝ → ℝ) : ∀ ε : ℝ, 0 < ε → ∃ δ : ℝ, 0 < δ", False),
    ("decorative_exists_hyp", "(h : ∃ x : ℝ, 0 < x) (a b : ℕ) : a + b = b + a", True),  # genuine; ∃-hyp advisory only
    ("genuine_icc_point",     "(f : ℝ → ℝ) : ∀ x ∈ Set.Icc 0 0, f x = f x", False),    # Icc a a = {a} NON-empty
]
# SEMANTIC tier: degeneracy the LEXICAL detector CANNOT see (contradictory hyps / ex-falso / false-equality).
# Documented here so the corpus is NOT confirmatory — these are the exogenous-probe's job (linarith/omega in
# nondegenerate_instance_probe), validated separately under lake; lexically they are EXPECTED to escape.
RED_TEAM_SEMANTIC = [
    ("nat_lt_zero_contradiction", "(n : ℕ) (h : n < 0) : n = n + 1"),
    ("real_disjoint_contradiction", "(x : ℝ) (h1 : 0 < x) (h2 : x < 0) : x = 42"),
    ("ex_falso", "(p : Prop) (hp : p) (hnp : ¬ p) : ∃ q : Prop, q"),
    ("false_equality_hyp", "(h : (0:ℝ) = 1) (a b : ℝ) : a = b"),
]


def run_redteam() -> dict:
    rows, hard_caught, adv_flagged, escapes = [], 0, 0, []
    n_hard = sum(1 for _, _, k in RED_TEAM_LAUNDERED if k == "hard")
    n_adv = sum(1 for _, _, k in RED_TEAM_LAUNDERED if k == "advisory")
    for name, stmt, kind in RED_TEAM_LAUNDERED:
        r = detect_risks(stmt)
        susp, flags = r["vacuity_suspected"], r["risk_flags"]
        if kind == "hard":
            ok = susp is True
            hard_caught += int(ok)
            cls = "CAUGHT(hard)" if ok else "MISSED(hard!)"
        elif kind == "advisory":
            ok = (susp is False) and bool(flags)   # flagged but not fail-closed
            adv_flagged += int(ok)
            cls = "advisory" if ok else ("escaped(adv)" if not flags else "OVER-HARD(adv!)")
        else:  # escape — lexically expected to slip; record it
            escapes.append(name)
            cls = "escaped(known-gap)" if not susp else "caught(bonus)"
        rows.append({"name": name, "kind": kind, "class": cls, "vacuity_suspected": susp, "flags": flags})
    fp_hard, fp_adv = [], []
    for name, stmt, adv_ok in RED_TEAM_GENUINE:
        r = detect_risks(stmt)
        if r["vacuity_suspected"] is True:
            fp_hard.append({"name": name, "flags": r["risk_flags"]})
        elif r["risk_flags"]:
            fp_adv.append({"name": name, "flags": r["risk_flags"], "expected": adv_ok})
        rows.append({"name": "GENUINE:" + name, "vacuity_suspected": r["vacuity_suspected"], "flags": r["risk_flags"]})
    # SEMANTIC tier — lexical detector is EXPECTED to escape these (they need the exogenous probe).
    probe_territory = []
    for name, stmt in RED_TEAM_SEMANTIC:
        r = detect_risks(stmt)
        probe_territory.append({"name": name, "lexical_vacuity_suspected": r["vacuity_suspected"],
                                "flags": r["risk_flags"],
                                "handled_by": "exogenous nondegenerate_instance_probe (linarith/omega) under lake — NOT lexical"})
    verdict = "REDTEAM_PASS" if (hard_caught == n_hard and not fp_hard) else "REDTEAM_FAIL"
    return {
        "verdict": verdict,
        "hard_catch": f"{hard_caught}/{n_hard}",
        "advisory_flagged": f"{adv_flagged}/{n_adv}",
        "lexical_escapes": escapes,
        "semantic_probe_territory": probe_territory,            # lexical-blind classes → the probe's job
        "false_positives_hard": fp_hard,                       # MUST be empty
        "false_positives_advisory": fp_adv,                    # documents why advisory legs can't be promoted
        "note": ("HARD legs catch all hard-laundered with ZERO fail-closed FP. Advisory legs flag but "
                 "do NOT block (a genuine predicate like Peano induction trips unanchored_opaque_object — "
                 "so they CANNOT be promoted to fail-closed lexically). The lexical escapes "
                 f"({escapes}) are the residual the exogenous non-degenerate-instance probe must close."),
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="run ground-truth validation")
    ap.add_argument("--redteam", action="store_true", help="run the degeneracy red-team corpus (catch/escape/FP)")
    ap.add_argument("--statement", default=None, help="classify a single Lean statement")
    ap.add_argument("--verify", action="store_true", help="also run independent Lean verifier")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.validate:
        res = run_validation()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        if args.out:
            Path(args.out).write_text(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["verdict"] == "DETECTOR_VALIDATED" else 1

    if args.redteam:
        res = run_redteam()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        if args.out:
            Path(args.out).write_text(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["verdict"] == "REDTEAM_PASS" else 1

    if args.statement:
        r = detect_risks(args.statement)
        if args.verify:
            r["independent_verify"] = independent_verify(args.statement, ["import Mathlib"], DEFAULT_SANDBOX)
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
