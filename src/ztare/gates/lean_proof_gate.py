"""GP-211 — Lean proof substrate gate.

Closes the gap surfaced by GP-211 iter-1/iter-2 (score 93/95 against a thesis
citing two hallucinated Mathlib lemmas — `Mathlib.CategoryTheory.Sites.Pushforward`
and `Sites.Equivalence.transport_isSheaf`). The judge couldn't run Lean, so it
scored Lean-shaped prose plus the existing tautological `test_model.py` (which
returns True regardless of the proof) as "validated."

Contract
--------
For any rubric whose `cage_meta.substrate_class == "lean_proof"`, this gate is
the authoritative falsifier. It:

  1. Extracts the largest ```lean fenced block from `thesis.md`.
  2. Writes it verbatim to `ztare_proofs/ZtareProofs/<project_slug>_iter.lean`.
  3. Runs `lake build ZtareProofs.<file_stem>` from the ztare_proofs root.
  4. Wraps `scripts/public/lean/verify_lean_stub.py` for axiom-allowlist + forbidden-token audit.
  5. Computes secondary observables (line count, Mathlib lemma count, applied
     lemmas) for the Generative Yield rubric dimension.

The orchestrator returns a single dict with `gate_passed: bool` (true iff
compiled AND axiom_audit_passed AND no forbidden tokens). This dict is then
formatted by `lean_substrate_runner.py` into the structured "LEAN UNIT TEST
RESULT" string the judge sees in place of the tautological PASS string.

Anti-gaming
-----------
- Hallucinated lemma names (`Sites.Equivalence.transport_isSheaf` is not in
  Mathlib v4.30) cause `lake build` to fail with "unknown constant" — no
  manual review needed.
- Smuggled axioms via `axiom foo : P` are caught by both the lexical scan
  and the post-compile `#print axioms` audit.
- `sorry`, `admit`, `native_decide` are caught by the lexical scan.
- A thesis with NO ```lean block fails immediately at extraction.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# scripts/public/ is not on sys.path by default; we depend on verify_lean_stub for
# axiom parsing so we don't reimplement the `#print axioms` driver.
_REPO_ROOT = Path(__file__).resolve().parents[3]
# verify_lean_stub moved under scripts/public/lean/ in the scripts reorg; keep the
# legacy scripts/ entry too so either layout resolves.
for _cand in (_REPO_ROOT / "scripts" / "public" / "lean", _REPO_ROOT / "scripts"):
    if _cand.is_dir() and str(_cand) not in sys.path:
        sys.path.insert(0, str(_cand))

import verify_lean_stub  # noqa: E402  (sys.path manipulation above)


GATE_ID = "G-LEAN-PROOF"
GATE_NAME = "lean_proof_gate"

# Match ```lean ... ``` fenced blocks (the language tag is required so we don't
# accidentally pick up a bare ``` block that contains ASCII-art or Python).
_LEAN_BLOCK_RE = re.compile(
    r"```lean\s*\n(.*?)\n```",
    flags=re.DOTALL | re.IGNORECASE,
)

# Mathlib identifier shape: Mathlib.X.Y(.Z...) where each segment starts uppercase.
_MATHLIB_IDENT_RE = re.compile(r"\bMathlib(?:\.[A-Z][A-Za-z0-9_]*)+\b")

# `apply NAME`, `exact NAME`, `refine NAME` where NAME contains a dot and starts
# with a capital letter — captures the use of named Mathlib lemmas inside tactics.
_TACTIC_LEMMA_RE = re.compile(
    r"\b(?:apply|exact|refine|rw|simp(?:\s+only)?\s*\[)\s+([A-Z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)"
)


@dataclass
class LeanProofGateResult:
    """Structured result of a single gate invocation.

    `gate_passed` is the conjunction the runner consumes; the sub-fields are
    surfaced to the judge so the rubric's Generative Yield dimension can score
    against actual compile output.
    """

    gate_id: str = GATE_ID
    gate_passed: bool = False
    extracted: bool = False
    lean_path: str | None = None
    compiled: bool = False
    lake_exit_code: int = -1
    compile_duration_s: float = 0.0
    compile_stdout: str = ""
    compile_stderr: str = ""
    axiom_audit_passed: bool = False
    extra_axioms: list[str] = field(default_factory=list)
    forbidden_tokens: list[str] = field(default_factory=list)
    line_count: int = 0
    mathlib_lemma_count: int = 0
    applied_lemmas: list[str] = field(default_factory=list)
    # v33 anti-laundering organs (2026-05-15): catches the false-closure
    # classes GP-211's compile+axiom audit does NOT (vacuous-but-axiom-free
    # Props, gold-name-verbatim of REAL Mathlib lemmas, single-lemma-exact,
    # simp/fun_prop indirect leakage). Surfaced additively; folded into
    # gate_passed iff enforce_anti_laundering=True.
    anti_laundering_passed: bool = True
    v33_organ_flags: list[str] = field(default_factory=list)
    v33_organ_detail: dict = field(default_factory=dict)
    # SM3 / ProofFlow-Aristotle move (2026-05-18): canonical statement
    # hash per proved theorem so a close can bind the PROOF to an
    # operator-registered target — not merely cite a hash in prose.
    # [{name, statement_sha256}]. Syntactic half only; semantic
    # equivalence to the informal problem stays human (epistemic
    # P16).
    theorem_statement_hashes: list[dict] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_claim_audit(self, *, claim_nl: str = "", claim_formal: str = "", mnc_passed: bool | None = None):
        """Distill the legible CLAIM AUDIT from this gate result — the math-side consumer of the
        substrate-neutral `common.claim_audit`. PURE distillation of the organ verdicts already on this
        dataclass (compiled / gate_passed / axiom_audit_passed / anti_laundering_passed / v33_organ_flags /
        extra_axioms / theorem_statement_hashes); it re-runs NOTHING. `mnc_passed` is the matched-negative-
        control verdict the solver gate runs alongside (not carried here) — pass it when known. Returns a
        `ClaimAudit` (render with `claim_audit.render_markdown`)."""
        from ztare.common.claim_audit import from_lean_gate_result
        return from_lean_gate_result(self.to_dict(), claim_nl=claim_nl,
                                     claim_formal=claim_formal, mnc_passed=mnc_passed)


# ---------------------------------------------------------------------------
# Step 1: extract
# ---------------------------------------------------------------------------


def extract_lean_from_thesis(thesis_path: Path) -> str | None:
    """Return the largest ```lean fenced block in `thesis_path`, or None.

    "Largest" means longest by character count — handles the common case
    where the mutator includes both a small statement-only block and a
    larger statement+proof block; we want the proof.
    """
    if not thesis_path.is_file():
        return None
    text = thesis_path.read_text(encoding="utf-8")
    blocks = _LEAN_BLOCK_RE.findall(text)
    if not blocks:
        return None
    return max(blocks, key=len).strip()


# ---------------------------------------------------------------------------
# Step 2: write
# ---------------------------------------------------------------------------


def _slug_to_module(project_slug: str) -> str:
    """Lean module names cannot contain `-` or start with a digit. Lowercase
    everything and replace non-[a-z0-9_] with `_`.
    """
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", project_slug).lower()
    if cleaned and cleaned[0].isdigit():
        cleaned = f"m_{cleaned}"
    return cleaned or "iter_proof"


def write_lean_target(
    lean_source: str, project_slug: str, ztare_proofs_root: Path
) -> Path:
    """Write `lean_source` verbatim to
    `ztare_proofs_root/ZtareProofs/<slug>_iter.lean` and return the path.

    Imports and namespace declarations are preserved as-is — we do not
    inject a preamble. If the mutator's source is missing imports, the
    compile will fail with a clear "unknown identifier" error and the
    gate will reject it; that is the desired behavior.
    """
    target_dir = ztare_proofs_root / "ZtareProofs"
    target_dir.mkdir(parents=True, exist_ok=True)
    file_stem = f"{_slug_to_module(project_slug)}_iter"
    target = target_dir / f"{file_stem}.lean"
    target.write_text(lean_source.rstrip() + "\n", encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Step 3: compile
# ---------------------------------------------------------------------------


def compile_lean(
    lean_path: Path, ztare_proofs_root: Path, timeout_seconds: int = 300
) -> dict[str, Any]:
    """Run `lake build ZtareProofs.<file_stem>` from `ztare_proofs_root`.

    Returns dict with: compiled, stdout, stderr, duration_s, exit_code.
    On FileNotFoundError (no lake in PATH) or TimeoutExpired the result has
    compiled=False and a populated stderr explaining why.
    """
    file_stem = lean_path.stem
    target = f"ZtareProofs.{file_stem}"
    cmd = ["lake", "build", target]
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(ztare_proofs_root),
        )
        duration = time.monotonic() - started
        return {
            "compiled": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_s": round(duration, 3),
            "exit_code": proc.returncode,
        }
    except FileNotFoundError:
        duration = time.monotonic() - started
        return {
            "compiled": False,
            "stdout": "",
            "stderr": "lake toolchain not installed (PATH lookup failed)",
            "duration_s": round(duration, 3),
            "exit_code": -1,
        }
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        return {
            "compiled": False,
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + f"\n[timeout after {timeout_seconds}s]",
            "duration_s": round(duration, 3),
            "exit_code": -2,
        }


# ---------------------------------------------------------------------------
# Step 4: axiom audit (delegates to verify_lean_stub)
# ---------------------------------------------------------------------------


def audit_axioms(lean_path: Path, ztare_proofs_root: Path) -> dict[str, Any]:
    """Return axiom-audit result for `lean_path`.

    Returns: {axiom_audit_passed, extra_axioms, forbidden_tokens}.

    Uses `verify_lean_stub.lexical_scan` for the forbidden-token sweep
    (sorry/admit/native_decide/standalone-axiom) and a lake-based driver
    for the post-compile `#print axioms` audit.

    Why we don't use `verify_lean_stub.print_axioms`: it shells out to bare
    `lean`, which can't resolve Mathlib imports outside lake's environment.
    Our targets always live inside the ztare_proofs lake project, so we
    append a transient driver module that imports the stub and runs
    `#print axioms`, then build that driver via lake and parse the output.
    """
    if not lean_path.is_file():
        return {
            "axiom_audit_passed": False,
            "extra_axioms": [],
            "forbidden_tokens": ["<lean source missing>"],
        }
    source = lean_path.read_text(encoding="utf-8")

    # Lexical pass first (no compile required).
    forbidden = verify_lean_stub.lexical_scan(source)

    # Axiom pass per theorem via a lake-built driver module.
    # Use namespace-qualified names so `#print axioms` resolves from the
    # driver, which is OUTSIDE any namespace declared in the stub.
    theorems = _qualify_theorem_names(source)
    extras: list[str] = []
    if not theorems:
        extras.append("<no-theorem-or-lemma-declarations>")
    if theorems:
        driver_extras = _audit_axioms_via_lake_driver(
            lean_path, ztare_proofs_root, theorems
        )
        extras.extend(driver_extras)

    return {
        "axiom_audit_passed": (not forbidden) and (not extras),
        "extra_axioms": extras,
        "forbidden_tokens": forbidden,
    }


def _audit_axioms_via_lake_driver(
    lean_path: Path,
    ztare_proofs_root: Path,
    theorems: list[str],
    timeout_seconds: int = 180,
) -> list[str]:
    """Write `<stem>_axioms.lean` next to the stub with `#print axioms`
    statements, run `lake build` on it, parse the output for unauthorized
    axioms. Returns a list of "thm:axiom" strings (empty = clean).
    """
    target_dir = lean_path.parent  # ztare_proofs/ZtareProofs/
    stub_module = lean_path.stem
    driver_stem = f"{stub_module}_axioms"
    driver_path = target_dir / f"{driver_stem}.lean"
    driver_module = f"ZtareProofs.{driver_stem}"

    body_lines = [f"import ZtareProofs.{stub_module}", ""]
    body_lines.extend(f"#print axioms {thm}" for thm in theorems)
    driver_path.write_text("\n".join(body_lines) + "\n", encoding="utf-8")

    extras: list[str] = []
    try:
        proc = subprocess.run(
            ["lake", "build", driver_module],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(ztare_proofs_root),
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        # `#print axioms` emits one of:
        #   'thm' depends on axioms: [a1, a2, ...]
        #   'thm' does not depend on any axioms
        # `lake` surfaces these as info diagnostics, prefixed with the file
        # path. Parse line-by-line to associate each axiom set with its theorem.
        per_thm = re.findall(
            r"'([A-Za-z0-9_.]+)'\s+depends on axioms:\s*\[([^\]]*)\]",
            output,
            flags=re.DOTALL,
        )
        seen: set[str] = set()
        for thm, axiom_list in per_thm:
            seen.add(thm)
            axioms = {a.strip() for a in axiom_list.split(",") if a.strip()}
            unauthorized = axioms - verify_lean_stub.ALLOWED_AXIOMS
            for ax in sorted(unauthorized):
                extras.append(f"{thm}:{ax}")
        # `does not depend on any axioms` lines also count as "seen".
        for thm in re.findall(
            r"'([A-Za-z0-9_.]+)'\s+does not depend on any axioms",
            output,
        ):
            seen.add(thm)
        # Any theorem the driver was supposed to inspect but that didn't
        # appear in the output is an audit failure (couldn't verify).
        for thm in theorems:
            if thm not in seen:
                extras.append(f"{thm}:<print-axioms-no-output>")
    except FileNotFoundError:
        extras.append("<lake-not-installed>")
    except subprocess.TimeoutExpired:
        extras.append(f"<axiom-audit-timeout-{timeout_seconds}s>")
    finally:
        # Clean up the driver so it doesn't pollute future builds. We keep
        # the stub itself for operator inspection.
        driver_path.unlink(missing_ok=True)
    return extras


# Strip Lean line/block comments before namespace tracking — comments
# may contain `namespace`/`end`/`theorem` tokens that would otherwise
# corrupt the stack.
_LEAN_LINE_COMMENT_RE = re.compile(r"--[^\n]*")
_LEAN_BLOCK_COMMENT_RE = re.compile(r"/-.*?-/", re.DOTALL)


def _strip_lean_comments(source: str) -> str:
    """Remove `-- ...` line comments and `/- ... -/` block comments."""
    no_block = _LEAN_BLOCK_COMMENT_RE.sub("", source)
    return _LEAN_LINE_COMMENT_RE.sub("", no_block)


_NAMESPACE_OPEN_RE = re.compile(r"^\s*namespace\s+([A-Za-z_][\w.]*)\s*$", re.MULTILINE)
_NAMESPACE_END_RE = re.compile(r"^\s*end\s+([A-Za-z_][\w.]*)\s*$", re.MULTILINE)
_THEOREM_RE = re.compile(r"^\s*(?:theorem|lemma)\s+([A-Za-z_][\w']*)", re.MULTILINE)


def _qualify_theorem_names(source: str) -> list[str]:
    """Return fully-namespace-qualified theorem/lemma names.

    Walks the Lean source line by line maintaining a namespace stack:
    `namespace X.Y` pushes (the dot-separated segments handled together);
    `end X.Y` pops the matching frame. Each `theorem foo` / `lemma foo`
    is qualified by the current stack joined with dots.

    Necessary because `_audit_axioms_via_lake_driver` emits a driver
    module that lives outside any namespace; short names like `foo`
    won't resolve unless qualified to `X.Y.foo`.
    """
    cleaned = _strip_lean_comments(source)
    stack: list[str] = []
    qualified: list[str] = []
    # Tokenize per line so we can process namespace/end/theorem in order.
    for raw_line in cleaned.splitlines():
        ns_open = _NAMESPACE_OPEN_RE.match(raw_line)
        if ns_open:
            stack.append(ns_open.group(1))
            continue
        ns_end = _NAMESPACE_END_RE.match(raw_line)
        if ns_end and stack:
            # Lean allows `end X.Y` to close a single matching frame; we
            # tolerate mismatch by popping the top regardless (the source
            # already type-checked, so the structure is well-formed).
            stack.pop()
            continue
        thm = _THEOREM_RE.match(raw_line)
        if thm:
            short = thm.group(1)
            qualified.append(".".join(stack + [short]) if stack else short)
    return qualified


# Capture the WHOLE signature (binders + `:` type) from after the
# theorem name up to `:=` or ` by ` — do NOT split on the first `:`
# (real binders like `(x : T)` contain colons; splitting there
# mis-parses and mis-hashes). Self-MD round-3 fix.
_THM_SIG_RE = re.compile(
    r"\b(?:theorem|lemma)\s+([A-Za-z_][\w']*)(.*?)(?:\:\=|\bby\b)",
    re.DOTALL)


def canonical_statement(stmt: str) -> str:
    """Normalize a Lean statement for hashing: strip comments, collapse
    all whitespace runs to single spaces, trim. Deterministic syntactic
    canonical form (NOT kernel-canonical — alpha/defeq differences are
    NOT collapsed; that is the acknowledged syntactic-only bound, P16).
    The operator registers sha256 of canonical_statement(<stmt text>);
    the same function is applied here so the two are comparable."""
    s = _strip_lean_comments(stmt)
    return " ".join(s.split()).strip()


def theorem_statement_hashes(source: str) -> list[dict]:
    """[{name, statement_sha256}] for every theorem/lemma — the
    namespace-qualified name plus sha256 of the canonical statement
    text (binders + `:` type, up to `:=`/`by`). Lets a close bind the
    PROOF's actual statement to an operator-registered target hash
    (SM3 / ProofFlow-Aristotle), closing the cite-a-hash-while-
    proving-something-weaker bypass."""
    cleaned = _strip_lean_comments(source)
    names = _qualify_theorem_names(source)
    out: list[dict] = []
    for i, m in enumerate(_THM_SIG_RE.finditer(cleaned)):
        short = m.group(1)
        # group(2) = the full signature text (binders + `:` type),
        # everything between the name and `:=`/`by`. Hash it whole.
        canon = canonical_statement(m.group(2) or "")
        qname = names[i] if i < len(names) else short
        out.append({
            "name": qname,
            "statement_sha256": hashlib.sha256(
                canon.encode("utf-8")).hexdigest(),
            # C3: the canonical statement TEXT, so a close can run a
            # Lean-kernel defeq probe against the registered target
            # text (not just compare hashes). Syntactic-only bound
            # still applies to the HASH; the TEXT enables the kernel
            # check that supersedes it.
            "statement_text": canon,
        })
    return out


# ---------------------------------------------------------------------------
# Step 5: secondary observables
# ---------------------------------------------------------------------------


def compute_secondary_observables(lean_path: Path) -> dict[str, Any]:
    """Compute the rubric's Generative Yield secondary observables.

    Returns: {line_count, mathlib_lemma_count, applied_lemmas}.

    `mathlib_lemma_count` = #(distinct fully-qualified Mathlib.X.Y identifiers)
    + #(distinct dotted identifiers used as args to apply/exact/refine/rw/simp).
    Permissive but deterministic — counts surface usage, not semantic depth.
    """
    if not lean_path.is_file():
        return {"line_count": 0, "mathlib_lemma_count": 0, "applied_lemmas": []}
    source = lean_path.read_text(encoding="utf-8")
    line_count = sum(1 for _ in source.splitlines())

    mathlib_idents = set(_MATHLIB_IDENT_RE.findall(source))
    tactic_lemmas = set(_TACTIC_LEMMA_RE.findall(source))
    applied = sorted(mathlib_idents | tactic_lemmas)
    return {
        "line_count": line_count,
        "mathlib_lemma_count": len(applied),
        "applied_lemmas": applied,
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


# NOTE (2026-06-21): the KERNEL type-equality oracle that USED to live here as `_kernel_type_equiv_fn` was a
# byte-identical copy of `solver_core._target_type_equiv_fn` — the recurring "missed sibling" bug class. It is
# now the ONE canonical `statement_integrity.kernel_type_equiv_fn`, built DEFAULT-ON inside
# `statement_integrity.check` (we just pass `lean_root`). No copy to hand-sync, no sibling to forget.


def run_anti_laundering_kernel(lean_source: str, lean_path: Path,
                               ztare_proofs_root: Path,
                               deep_verify: bool = False,
                               original_source: str | None = None,
                               target_name: str | None = None,
                               target_type_equiv_fn=None) -> dict[str, Any]:
    """THE ONE governance anti-laundering kernel (renamed 2026-06-06 from the cryptic
    `_run_v33_anti_laundering`; a back-compat alias is kept at module end). This is the single canonical
    organ stack EVERY solving mode routes through — never re-implement a reduced per-mode gate battery
    beside it (the `proof_cage` experiment showed that parallel gate stacks
    drift and disagree). Organs: vacuity / gold-name-verbatim / single-lemma-exact /
    indirect-leakage / consequence-exposure / statement-integrity.

    Run the anti-laundering organs on the (already-compiled) Lean
    source. Component-1 shape detectors + gold-name corpus confirm are
    CHEAP (no extra Lean). Component-2 Lean re-probes are gated behind
    deep_verify (the loop already paid one compile; don't 5x it).

    `original_source` + `target_name` (optional): when the caller knows the POSED statement (e.g. the
    sorried candidate / row source), the statement-integrity organ runs — it diffs the probe's
    pre-existing decls against the original and flags `statement_altered_confirmed` if the agent edited
    a depended-on definition (the def-alteration channel v33's single-file organs structurally cannot
    see). This is a GENERAL-PURPOSE organ of the ONE kernel: every solving mode that passes the
    original (factory C-rows, ad-hoc, validator) gets it — not an ad-hoc special case.

    Returns {passed, flags, detail}. passed=False iff any organ confirms a false-closure class.
    """
    import importlib.util as _ilu
    ctl = ztare_proofs_root.parent.parent / "scripts/public/control"
    if not ctl.exists():
        ctl = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve() / "scripts/public/control"

    # DUAL-PATH (2026-05-16): loop-executed v33 organs belong in src/
    # (scripts/ = one-shot operator tools per convention). Resolve
    # src/ztare/gates/ (this dir) FIRST, then the legacy
    # scripts/public/control/ fallback — so the family can migrate to
    # src/ one organ at a time with zero breakage (no big-bang refactor
    # of cross-agent infra). v33_consequence_exposure_gate migrated
    # 2026-05-16; siblings still load from the scripts/ fallback.
    _src_gates = Path(__file__).resolve().parent

    def _load(modname: str):
        for base in (_src_gates, ctl):
            p = base / f"{modname}.py"
            if p.exists():
                spec = _ilu.spec_from_file_location(modname, p)
                m = _ilu.module_from_spec(spec)
                try:
                    spec.loader.exec_module(m)  # type: ignore[attr-defined]
                    return m
                except Exception:
                    return None
        return None

    flags: list[str] = []
    detail: dict[str, Any] = {}

    vac = _load("v33_preflight_risk_detector")
    if vac is not None:
        try:
            r = vac.detect_risks(lean_source)
            detail["vacuity"] = r
            if r.get("vacuity_suspected"):
                flags.append("vacuity_suspect")
        except Exception as e:
            detail["vacuity"] = {"error": str(e)}

    para = _load("v33_paraphrase_gate")
    if para is not None:
        try:
            d = para.detect_gold_name_verbatim(lean_source)
            prim = d.get("primary_cited")
            corp = para.independent_corpus_confirm(prim) if (d.get("gold_name_verbatim_suspect") and prim) else {"in_mathlib": False}
            detail["gold_name_verbatim"] = {"detect": d, "corpus": corp}
            # Blocker only on a TRIVIAL restatement; a gold lemma closing real proof
            # work is legitimate library composition -> advisory (2026-05-30 fix).
            if d.get("trivial_restatement") and corp.get("in_mathlib"):
                flags.append("gold_name_verbatim_confirmed")
            elif d.get("gold_name_verbatim_suspect") and corp.get("in_mathlib"):
                flags.append("gold_name_verbatim_library_close_advisory")
        except Exception as e:
            detail["gold_name_verbatim"] = {"error": str(e)}

    sle = _load("v33_single_lemma_exact_gate")
    if sle is not None:
        try:
            s = sle.detect_shape(lean_source)
            detail["single_lemma_exact"] = {"shape": s}
            if s.get("single_lemma_exact_suspect"):
                if deep_verify:
                    from ztare.common.timeouts import timeout_s   # central budget factory (byte-parity: independent_verify defaults to the prior 70)
                    v = sle.independent_exact_verify_rowfile(lean_source, ztare_proofs_root, timeout=timeout_s("independent_verify"))
                    detail["single_lemma_exact"]["verify"] = v
                    if v.get("single_lemma_exact_confirmed"):
                        flags.append("single_lemma_exact_confirmed")
                else:
                    flags.append("single_lemma_exact_shape_suspect_advisory")
        except Exception as e:
            detail["single_lemma_exact"] = {"error": str(e)}

    ind = _load("v33_indirect_leakage_gate")
    if ind is not None:
        try:
            s = ind.detect_shape(lean_source)
            detail["indirect_leakage"] = {"shape": s}
            if s.get("indirect_leakage_suspect"):
                if deep_verify:
                    from ztare.common.timeouts import timeout_s   # central budget factory (byte-parity: independent_verify defaults to the prior 70)
                    v = ind.independent_verify(lean_source, s.get("closer_tactic"), ztare_proofs_root, timeout=timeout_s("independent_verify"))
                    detail["indirect_leakage"]["verify"] = v
                    if v.get("indirect_leakage_confirmed"):
                        flags.append("indirect_leakage_confirmed")
                else:
                    flags.append("indirect_leakage_shape_suspect_advisory")
        except Exception as e:
            detail["indirect_leakage"] = {"error": str(e)}

    # GP-188 Q3 v3.1: consequence-exposure organ. Parses the claimed-
    # closure SIGNATURE binders (object distinct from every other v33
    # organ) for a hard target smuggled in as an assumed hypothesis,
    # after file-local delta/structure closure + transparent-wrapper
    # descent. `hard_target_heads` is substrate-supplied & narrow via a
    # sidecar; ABSENT ⇒ the blocking rule is inert (advisory-only) — the
    # correct staged-blocking default, never false-FAIL on the live loop.
    cex = _load("v33_consequence_exposure_gate")
    if cex is not None:
        try:
            s = cex.detect_shape(lean_source)
            detail["consequence_exposure"] = {"shape": s}
            if s.get("blocking"):
                flags.append("consequence_exposure_confirmed")
            elif s.get("consequence_exposure_suspect"):
                flags.append("consequence_exposure_shape_suspect_advisory")
        except Exception as e:
            detail["consequence_exposure"] = {"error": str(e)}

    # currency-mismatch organ (scalar-wrapper smuggle). ADVISORY — added 2026-06-06 to make THIS kernel
    # the canonical SUPERSET so `proof_audit` (which ran currency but not statement_integrity) can reuse
    # the kernel without losing an organ. Advisory flag ⇒ does NOT change any existing caller's pass/fail
    # (only `_confirmed` flags + `vacuity_suspect` block), so this addition is byte-parity for `passed`.
    cur = _load("v33_currency_mismatch_gate")
    if cur is not None:
        try:
            s = cur.detect_shape(lean_source)
            detail["currency_mismatch"] = {"shape": s}
            if s.get("scalar_wrapper_suspect"):
                flags.append("currency_mismatch_shape_suspect_advisory")
        except Exception as e:
            detail["currency_mismatch"] = {"error": str(e)}

    # statement-integrity organ (two-input: original vs probe) — the def-alteration channel the
    # single-file organs above cannot see. Runs whenever the caller supplies the posed statement.
    if original_source and target_name:
        try:
            from ztare.leanmill.solver.statement_integrity import check as _si_check
            # KERNEL TYPE-EQUALITY oracle — now built DEFAULT-ON inside `check` itself (2026-06-21): we pass
            # `lean_root` and the ONE canonical `statement_integrity.kernel_type_equiv_fn` is constructed at the
            # DEEPEST chokepoint (the consumer), so EVERY governance path gets reformulation-tolerance with no
            # sibling call site to forget. This WAS the missed sibling of the solve-time statement_integrity fix
            # — two hand-synced oracle copies rejected the consciousness factorization iffs the solve check
            # accepted; the structural cure is one oracle, default-on at the consumer (not copied per caller).
            # A faithful ∀-fronted / `↑(Set.range E)` reformulation ACCEPTS; a real weakening is a different Prop
            # ⇒ `rfl` fails ⇒ still rejected. A caller may still inject `target_type_equiv_fn` to override.
            iv = _si_check(original_source, lean_source, target_name,
                           target_type_equiv_fn=target_type_equiv_fn, lean_root=ztare_proofs_root)
            detail["statement_integrity"] = iv.to_dict()
            if not iv.ok:
                flags.append("statement_altered_confirmed")
        except Exception as e:
            # FAIL-CLOSED (soundness #84/F5, 2026-06-12; ZTARE_STATEMENT_INTEGRITY_FAILOPEN=1 reverts):
            # statement_integrity is PURE-PYTHON (a decl-block parse, no Lean tooling), so a crash is a parser
            # bug or ADVERSARIAL input crafted to crash the parser — NOT a tooling flake. Failing OPEN here would
            # let such a probe BYPASS the def-alteration check, so treat an organ crash as a CONFIRMED suspect.
            # (canonical_reelaboration still independently backstops the hijack class; this closes the one
            # remaining pure-python fail-open. The Lean-recompile organs below stay fail-open — a compile-infra
            # flake there is NOT adversarial.)
            detail["statement_integrity"] = {"error": str(e)}
            import os as _os_si
            if _os_si.environ.get("ZTARE_STATEMENT_INTEGRITY_FAILOPEN") != "1":
                flags.append("statement_integrity_error_confirmed")

    # canonical re-elaboration organ (2026-06-06): the airtight backstop for the WHOLE context-semantic-
    # hijack class (added instance / notation / macro / set_option that hijacks a verbatim statement — the
    # FALSIFY false-statement control's instance-shadowing was the seed). Strips the ADDED elaboration-
    # context from the probe (KEEPS opens / lemmas) and RE-COMPILES; if the target no longer closes
    # sorry-free, the proof DEPENDED on the manipulation. Recompiles ONLY when there is hijack-context to
    # strip (else a fast pass) ⇒ cost paid only on suspect probes. Default-ON; ZTARE_CANONICAL_REELAB=0 off.
    import os as _os_reelab
    if (original_source and target_name and ztare_proofs_root is not None
            and _os_reelab.environ.get("ZTARE_CANONICAL_REELAB", "1") != "0"):
        try:
            from ztare.leanmill.solver.canonical_reelaboration import check as _reelab
            # SINGLE-DOOR SUBSTRATE BASELINE (2026-07-05, THE recurring cited-rung `context_hijack` — operator "for
            # once truly fixed / why re-elaborate a solved theorem"). canonical_reelaboration STRIPS from the probe
            # every decl not in `original_source` and re-compiles; a CITED-RUNG / composite governance path passes
            # only the POSED statement as `original_source` (a partial slice), so the substrate's OWN inlined defs
            # get stripped → the proof breaks → FALSE `context_hijack` (statement_integrity only flags ALTERED
            # shared defs, so it PASSES → the `si_ok=True si_viol=[]` signature). Its internal `get_campaign_
            # substrate()` union returned None at this seam (cross-process global). Cure at the ONE kernel door
            # every governance path routes through (solve-time 1445 AND cited-rung 4571): read the registered
            # substrate HERE (main process, env-var mirror live) and hand the FULL baseline to _reelab EXPLICITLY —
            # so its decls count as PRE-EXISTING and it no longer depends on the blind global. SOUND: a genuinely-
            # injected hijack decl is NOT in the substrate ⇒ still stripped + caught. Additive; a read failure
            # keeps the passed baseline (byte-parity for a flat/non-campaign gate call).
            _reelab_orig = original_source
            try:
                from ztare.formal.repl_compile import get_campaign_substrate as _gcs_re
                _subp = _gcs_re()
                if _subp and Path(_subp).exists():
                    _reelab_orig = original_source + "\n\n" + Path(_subp).read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001 — union is additive; a failure keeps the caller's baseline
                pass
            _ok_re, _d_re = _reelab(_reelab_orig, lean_source, target_name, ztare_proofs_root)
            detail["canonical_reelaboration"] = {"ok": _ok_re, "detail": _d_re}
            if not _ok_re:
                flags.append("context_hijack_confirmed")
        except Exception as e:  # noqa: BLE001 — fail-OPEN on a compile-infra error (never block on tooling)
            detail["canonical_reelaboration"] = {"error": str(e)}

    # A CONFIRMED organ (not merely advisory shape-suspect) fails the layer.
    confirmed = [f for f in flags if f.endswith("_confirmed") or f == "vacuity_suspect"]
    return {"passed": len(confirmed) == 0, "flags": flags,
            "detail": detail, "confirmed": confirmed}


# Back-compat alias: the kernel was `_run_v33_anti_laundering` before the 2026-06-06 rename. External
# callers (ns_governance_gate, closure_claim_discipline_linter, older solver code) import the old name;
# this keeps them working with ZERO behavior change while the canonical name is `run_anti_laundering_kernel`.
_run_v33_anti_laundering = run_anti_laundering_kernel


def run_lean_proof_gate(
    thesis_path: Path,
    project_slug: str,
    ztare_proofs_root: Path,
    timeout_seconds: int = 300,
    enforce_anti_laundering: bool = True,
    deep_verify: bool = False,
) -> dict[str, Any]:
    """Single-call orchestrator: extract → write → compile → audit →
    observables → v33 anti-laundering organs.

    `enforce_anti_laundering` (default True, per 2026-05-15 directive to
    make the in-loop gate stronger): a CONFIRMED false-closure organ
    flips gate_passed to False. `deep_verify` (default False): also run
    the Component-2 Lean re-probes for single-lemma-exact / indirect-
    leakage (extra ~30-70s compiles; the loop already paid one).

    Returns the LeanProofGateResult as a dict (with `gate_passed` set).
    """
    result = LeanProofGateResult()

    lean_source = extract_lean_from_thesis(thesis_path)
    if lean_source is None:
        result.rationale = (
            "No ```lean fenced block found in thesis.md. The mutator must "
            "submit a Lean theorem statement + proof inside a ```lean ... ``` "
            "block (cage_meta.substrate_class=lean_proof requires verifiable "
            "Lean code, not Lean-shaped prose)."
        )
        return result.to_dict()
    result.extracted = True

    lean_path = write_lean_target(lean_source, project_slug, ztare_proofs_root)
    result.lean_path = str(lean_path)

    compile_result = compile_lean(lean_path, ztare_proofs_root, timeout_seconds)
    result.compiled = bool(compile_result["compiled"])
    result.lake_exit_code = int(compile_result["exit_code"])
    result.compile_duration_s = float(compile_result["duration_s"])
    # Truncate logs so a multi-megabyte stderr doesn't blow up the prompt
    # context; full logs remain on disk via lake's own caching.
    result.compile_stdout = compile_result["stdout"][-2000:]
    result.compile_stderr = compile_result["stderr"][-4000:]

    audit = audit_axioms(lean_path, ztare_proofs_root)
    result.axiom_audit_passed = bool(audit["axiom_audit_passed"])
    result.extra_axioms = list(audit["extra_axioms"])
    result.forbidden_tokens = list(audit["forbidden_tokens"])

    obs = compute_secondary_observables(lean_path)
    result.line_count = int(obs["line_count"])
    result.mathlib_lemma_count = int(obs["mathlib_lemma_count"])
    result.applied_lemmas = list(obs["applied_lemmas"])
    try:
        result.theorem_statement_hashes = theorem_statement_hashes(
            lean_source)
    except Exception:
        result.theorem_statement_hashes = []

    # v33 anti-laundering organ layer (additive; only meaningful once the
    # proof compiled — a non-compiling proof is already a fail).
    if result.compiled:
        try:
            v33 = run_anti_laundering_kernel(lean_source, lean_path,
                                           ztare_proofs_root, deep_verify=deep_verify)
            result.anti_laundering_passed = bool(v33["passed"])
            result.v33_organ_flags = list(v33["flags"])
            result.v33_organ_detail = v33["detail"]
        except Exception as e:
            result.anti_laundering_passed = True  # fail-open: never block on organ-layer crash
            result.v33_organ_flags = [f"organ_layer_error:{e}"]

    base_pass = bool(
        result.compiled
        and result.axiom_audit_passed
        and not result.forbidden_tokens
    )
    result.gate_passed = base_pass and (
        result.anti_laundering_passed if enforce_anti_laundering else True
    )

    if result.gate_passed:
        adv = [f for f in result.v33_organ_flags if f.endswith("_advisory")]
        result.rationale = (
            f"Lean proof compiled (exit 0 in {result.compile_duration_s}s); "
            f"axiom audit passed; {result.mathlib_lemma_count} Mathlib refs; "
            f"anti-laundering organs passed"
            + (f" (advisory flags: {adv})" if adv else "")
            + "."
        )
    else:
        reasons: list[str] = []
        if not result.compiled:
            reasons.append(f"compile failed (exit {result.lake_exit_code})")
        if result.forbidden_tokens:
            reasons.append(
                f"forbidden tokens: {len(result.forbidden_tokens)} (sorry/admit/native_decide/axiom)"
            )
        if not result.axiom_audit_passed and not result.forbidden_tokens:
            reasons.append("axiom audit failed (no theorem/lemma, extra axioms, or print-axioms parse failure)")
        if enforce_anti_laundering and not result.anti_laundering_passed:
            confirmed = [f for f in result.v33_organ_flags if f.endswith("_confirmed") or f == "vacuity_suspect"]
            reasons.append(f"anti-laundering FAILED: {confirmed} "
                           f"(false-closure class compile+axiom-audit cannot catch)")
        result.rationale = "; ".join(reasons)
    return result.to_dict()


# ---------------------------------------------------------------------------
# Smoke test (callable by hand or by the runner's __main__)
# ---------------------------------------------------------------------------


def _smoke_test() -> int:
    """Smoke-test the gate against:
       (a) the GP-211 iter-2 hallucinated thesis (should FAIL — no ```lean
           block at all, so gate returns extracted=False).
       (b) a minimal known-good thesis with `theorem one_eq_one : 1 = 1 := rfl`
           (should PASS).
    """
    repo = Path(__file__).resolve().parents[3]
    ztare_proofs = repo / "ztare_proofs"

    # --- Case (a): existing GP-211 thesis ---
    print("=" * 70)
    print("SMOKE A: GP-211 iter-2 hallucinated thesis")
    print("=" * 70)
    gp211_thesis = repo / "projects" / "gp211_paper8_lean_proofs" / "thesis.md"
    if gp211_thesis.exists():
        a = run_lean_proof_gate(gp211_thesis, "gp211_smoke", ztare_proofs, timeout_seconds=120)
        print(f"gate_passed: {a['gate_passed']} (expect False)")
        print(f"extracted:   {a['extracted']}")
        print(f"compiled:    {a['compiled']}")
        print(f"rationale:   {a['rationale']}")
    else:
        print(f"(thesis not found: {gp211_thesis})")
        a = {"gate_passed": True}  # so we report mismatch loudly below

    # --- Case (b): synthetic known-good thesis ---
    print()
    print("=" * 70)
    print("SMOKE B: minimal known-good Lean theorem")
    print("=" * 70)
    import tempfile
    good_thesis_text = (
        "# Smoke thesis\n\n"
        "Trivial reflexivity.\n\n"
        "```lean\n"
        "theorem one_eq_one : 1 = 1 := rfl\n"
        "```\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(good_thesis_text)
        good_path = Path(fh.name)
    try:
        b = run_lean_proof_gate(good_path, "lean_proof_gate_smoke", ztare_proofs, timeout_seconds=300)
        print(f"gate_passed: {b['gate_passed']} (expect True)")
        print(f"compiled:    {b['compiled']}")
        print(f"line_count:  {b['line_count']}")
        print(f"applied_lemmas: {b['applied_lemmas']}")
        print(f"rationale:   {b['rationale']}")
    finally:
        good_path.unlink(missing_ok=True)

    a_ok = (a["gate_passed"] is False)
    b_ok = (b["gate_passed"] is True)
    print()
    print("=" * 70)
    print(f"SMOKE A (hallucinated FAIL): {'PASS' if a_ok else 'FAIL'}")
    print(f"SMOKE B (known-good PASS):   {'PASS' if b_ok else 'FAIL'}")
    print("=" * 70)
    return 0 if (a_ok and b_ok) else 1


if __name__ == "__main__":
    raise SystemExit(_smoke_test())
