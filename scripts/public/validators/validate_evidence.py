#!/usr/bin/env python3
"""GP-162 + GP-157 Phase 7 — Evidence Pre-Flight Validator.

Checks evidence.txt for substrate construction discipline issues that
cause silent run failures. Run as part of `make seal` or standalone.

Usage:
    python scripts/public/validators/validate_evidence.py <project_slug>
    python scripts/public/validators/validate_evidence.py <project_slug> --rubric rubrics/<name>.json

Cross-substrate checks (always run):
    1. evidence.txt exists and is non-empty
    2. Data is inline (not "run this command" / "see test_model.py")
    3. At least one numeric table with ≥ 5 rows of data
    4. Contains a Python code example (```python block)
    5. Code example does NOT contain GT constants from gate_harness.py
    6. Required sections: visible data, constraints, submission contract
    7. No GT functional form leaked (cross-check with gate_harness.py if present)

Class-aware checks (Phase 7, when --rubric supplied AND cage_meta.class set):
    8.  nd_features: evidence must mention `I_model` and `features` (the contract).
    9.  audit: evidence should not include fitting tables (audit substrates score on critique).
    10. proof_target: evidence must reference Lean / formal-proof tooling.
    11. closed_form_constant: evidence must reference PSLQ or integer-relation discovery.
    12. Generic: detect TODO / FIXME / XXX markers (low confidence in shipped state).

Soft / strict mode (Phase 7):
    By default, class-aware lints emit as warnings (advisory). Set
    `evidence_strict_lint: true` in the rubric to promote them to errors.
    Cross-substrate checks above remain blocking regardless — those have
    been load-bearing since GP-162.

Exit 0 = PASSED, Exit 1 = FAILED (with diagnostics).
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Ensure repo root is on sys.path regardless of cwd / Python invocation style.
# Without this, `from src.ztare.*` silently fails when invoked from a non-repo
# cwd or under a Python that does not auto-insert cwd onto sys.path; and the
# four typed-contract checks below silently degrade to soft-warnings while
# seal still reports PASSED — a class of silent-regression we now refuse.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

PROJECTS_DIR = Path("projects")


class _ApparatusImportError(RuntimeError):
    """Raised when the validator cannot import its own typed-contract
    modules. Distinct from substrate-side soft-warnings: this is an
    APPARATUS install / path failure and must fail seal loudly."""


def _import_apparatus_module(module_path: str, attrs: tuple[str, ...] = ()) -> object:
    """Import a `src.ztare.*` module + optional attrs. Raise
    _ApparatusImportError on `ModuleNotFoundError` for `src` or `src.ztare`,
    so the four typed checks differentiate apparatus failure (hard) from
    substrate pre-mutator state (soft)."""
    try:
        module = __import__(module_path, fromlist=list(attrs) or ["__name__"])
    except ModuleNotFoundError as exc:
        if exc.name in {"src", "src.ztare"} or (exc.name or "").startswith("src.ztare"):
            raise _ApparatusImportError(
                f"validator cannot import {module_path!r}: {exc}. "
                "This is an apparatus path failure, not a substrate issue. "
                f"Ensure the validator runs with the repo root ({_REPO_ROOT}) "
                "on sys.path. Refusing to silently degrade typed-contract "
                "checks to no-ops."
            ) from exc
        raise
    return module


def _read_rubric(rubric_path: Path | None) -> dict:
    """Return {} if rubric_path is None or unreadable. Never raises."""
    if rubric_path is None or not rubric_path.exists():
        return {}
    try:
        return json.loads(rubric_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _class_aware_lints(text: str, cage_meta_class: str) -> list[str]:
    """Run lints specific to the substrate class.

    Returns a list of advisory diagnostic strings (each one a single
    warning message). Caller decides whether to treat them as warnings
    or errors based on the strict-mode flag.
    """
    cls = cage_meta_class.strip().lower()
    diags: list[str] = []

    if cls == "nd_features":
        if not re.search(r"\bI_model\b", text):
            diags.append(
                "nd_features substrate: evidence does not mention `I_model`. "
                "Mutator may not know the override contract — see "
                "src/ztare/orchestrator/prompt.py for canonical contract block."
            )
        if not re.search(r"features\s*\[|\bfeatures\b\s*=|`features`", text):
            diags.append(
                "nd_features substrate: evidence does not mention `features` dict. "
                "Mutator must know it is invoked as `I_model(features)`."
            )
    elif cls == "audit":
        # Audit substrates (gp156, gp158) do NOT fit numeric tables — the
        # mutator's job is to find defects in a research artifact. A big
        # numeric table is a misframed substrate.
        table_rows = re.findall(r"^\|.*\d+\.\d+.*\|.*\d+\.\d+.*\|", text, re.MULTILINE)
        if len(table_rows) > 8:
            diags.append(
                f"audit substrate: evidence contains {len(table_rows)} numeric table rows. "
                f"Audit substrates score on critique, not curve-fitting — verify the "
                f"substrate was scaffolded as audit, not as a fitting target."
            )
    elif cls == "proof_target":
        if not re.search(r"\b(Lean|REPL|theorem|tactic)\b", text):
            diags.append(
                "proof_target substrate: evidence does not reference Lean / theorem / "
                "tactic. The mutator's contract is to write Lean proof obligations."
            )
    elif cls == "closed_form_constant":
        if not re.search(r"\b(PSLQ|integer.relation|continued.fraction)\b", text, re.IGNORECASE):
            diags.append(
                "closed_form_constant substrate: evidence does not reference PSLQ or "
                "integer-relation discovery. Verify the contract is constant-discovery, "
                "not fitting."
            )

    # Generic: TODO / FIXME / XXX markers signal the substrate isn't shipped.
    todo_hits = re.findall(r"\b(TODO|FIXME|XXX)\b", text)
    if todo_hits:
        diags.append(
            f"evidence.txt contains {len(todo_hits)} TODO/FIXME/XXX marker(s). "
            f"Sealed substrates should not have draft markers."
        )

    return diags


def validate_evidence(slug: str, rubric_path: Path | None = None) -> tuple[bool, list[str]]:
    proj = PROJECTS_DIR / slug
    evidence_path = proj / "evidence.txt"
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Exists and non-empty
    if not evidence_path.exists():
        errors.append("evidence.txt does not exist")
        return False, errors
    text = evidence_path.read_text(encoding="utf-8")
    if len(text.strip()) < 50:
        errors.append(f"evidence.txt too short ({len(text)} chars)")

    # 2. No "run this command" without inline data
    run_patterns = [
        r"Run.*test_model\.py.*--show-data",
        r"python.*--show-data",
        r"see test_model\.py",
        r"The data is in test_model\.py",
    ]
    for pat in run_patterns:
        if re.search(pat, text, re.IGNORECASE):
            # Only flag if there's no inline data table
            has_inline_table = bool(re.search(r"\|\s*[\d.]+\s*\|\s*[\d.]+\s*\|", text))
            if not has_inline_table:
                errors.append(
                    f"evidence.txt tells mutator to 'run' a command but has no inline data table. "
                    f"The mutator cannot execute commands. Inline the data."
                )

    # 3. Numeric table with ≥ 5 rows
    table_rows = re.findall(r"^\|.*\d+\.\d+.*\|.*\d+\.\d+.*\|", text, re.MULTILINE)
    if len(table_rows) < 5:
        # Also check for non-table inline data (tuple format)
        tuple_rows = re.findall(r"\(\s*[\d.]+\s*,\s*[\d.]+\s*\)", text)
        if len(tuple_rows) < 5:
            errors.append(
                f"evidence.txt has only {len(table_rows)} table rows and {len(tuple_rows)} "
                f"inline tuples. Need ≥ 5 data points visible to the mutator."
            )

    # 4. Python code example
    python_blocks = re.findall(r"```python(.*?)```", text, re.DOTALL)
    if not python_blocks:
        warnings.append("evidence.txt has no ```python block. Mutator may not know how to write I_model.")

    # 5. Code example doesn't contain GT constants
    harness_path = proj / "gate_harness.py"
    if harness_path.exists() and python_blocks:
        harness_text = harness_path.read_text(encoding="utf-8")
        gt_constants = set()
        for match in re.findall(r"(?:C\d|_P\[|TRUE|_ground_truth).*?([\d]+\.[\d]{3,})", harness_text):
            gt_constants.add(match)
        for match in re.findall(r"(?:^|\s)([A-Z]\w*)\s*=\s*([\d]+\.[\d]{3,})", harness_text):
            gt_constants.add(match[1])

        for block in python_blocks:
            for const in gt_constants:
                if const in block:
                    errors.append(
                        f"Python code example contains GT constant {const} from gate_harness.py — "
                        f"this leaks the answer. Use a WRONG example form."
                    )

    # 6. Required sections
    required_sections = [
        ("visible data", r"(?i)visible\s+data|data\s+table|evidence\s+set\s+a"),
        ("constraints", r"(?i)constraint|bound|rule"),
        ("submission contract", r"(?i)how\s+to\s+submit|python\s+contract|I_model|mandatory.*python"),
    ]
    for section_name, pattern in required_sections:
        if not re.search(pattern, text):
            warnings.append(f"evidence.txt may be missing '{section_name}' section")

    # 7. Anti-contamination: GT form in evidence
    if harness_path.exists():
        harness_text = harness_path.read_text(encoding="utf-8")
        gt_match = re.search(r"def _ground_truth\(.*?\):\s*\n(.*?)(?=\ndef |\nclass |\n[A-Z])",
                            harness_text, re.DOTALL)
        if gt_match:
            gt_body = gt_match.group(1)
            if "sin(" in gt_body and "sin" in text.lower():
                warnings.append(
                    "evidence.txt mentions 'sin' and gate_harness GT uses sin() — "
                    "verify the evidence doesn't hint at the oscillatory structure"
                )

    # 8-12. Class-aware lints (Phase 7, GP-157 v5.0).
    # Soft by default; STRICT mode promotes class-aware warnings to errors.
    rubric_data = _read_rubric(rubric_path)
    cage_meta = rubric_data.get("cage_meta") or {}
    cage_meta_class = (cage_meta.get("class") or "").strip() if isinstance(cage_meta, dict) else ""
    strict_mode = bool(rubric_data.get("evidence_strict_lint", False))

    class_diags: list[str] = []
    if cage_meta_class:
        class_diags = _class_aware_lints(text, cage_meta_class)

    # 13. Substrate-rubric class-consistency check (GP-157 Phase 4d follow-up).
    # gp159/160/161 regression: substrate declared cage_meta.class="nd_features"
    # but had no features.py → wrong contract hint injected. ALWAYS blocking
    # (not subject to soft/strict toggle) because it indicates a misclassified
    # substrate that cannot honor the contract the apparatus will assume.
    # Epistemic Handshake: refuse to seal substrates whose probe was
    # ambiguous AND no operator declaration. Forces explicit class
    # declaration before any iter spend. Per panel: 'route the problem
    # back to the operator, do not silently guess.'
    if cage_meta_class == "_ambiguous_pending_review":
        errors.append(
            "cage_meta.class='_ambiguous_pending_review' — substrate probe "
            "could not classify. The operator MUST manually declare a "
            "physical class in rubric.cage_meta.class (one of: 1d, "
            "1d_discrete, nd_features, time_series, time_series_chaotic, "
            "audit, literature, proof_target, closed_form_constant) "
            "before sealing. See class_diagnostics for probe output."
        )

    if cage_meta_class and cage_meta_class != "_ambiguous_pending_review":
        try:
            mod = _import_apparatus_module(
                "src.ztare.orchestrator", ("verify_class_consistency_with_substrate",)
            )
            verify_class_consistency_with_substrate = mod.verify_class_consistency_with_substrate
            consistency_msg = verify_class_consistency_with_substrate(cage_meta_class, proj)
            if consistency_msg is not None:
                errors.append(f"cage_meta.class consistency: {consistency_msg}")
        except _ApparatusImportError as ae:
            errors.append(f"APPARATUS: class-consistency check unrunnable — {ae}")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"could not run class-consistency check: {exc}")

    # 16. L1 Protocol-based boundary check (closes the unenforced-L1 gap):
    # if the substrate's test_model.py exists, import it and run adapt()
    # against the ContractSpec for the declared cage_meta.class. This is
    # the typed-receiver check that prompt.py's hint section advertises
    # but the apparatus had never invoked at seal time. Catches signature
    # / required-globals / contract violations BEFORE any iter spend.
    try:
        orch_mod = _import_apparatus_module(
            "src.ztare.orchestrator", ("ContractError", "adapt", "get_spec_by_class")
        )
        ContractError = orch_mod.ContractError
        adapt = orch_mod.adapt
        get_spec_by_class = orch_mod.get_spec_by_class
        spec = get_spec_by_class(cage_meta_class) if cage_meta_class else None
        tm_path = proj / "test_model.py"
        if spec is not None and tm_path.exists() and "I_model" in spec.required_module_globals:
            import importlib.util as _ilu
            _spec = _ilu.spec_from_file_location(f"_{slug}_seal_probe", str(tm_path))
            if _spec is not None and _spec.loader is not None:
                _mod = _ilu.module_from_spec(_spec)
                try:
                    _spec.loader.exec_module(_mod)
                    try:
                        adapt(_mod, spec)
                        # success — Protocol boundary clean
                    except ContractError as ce:
                        # Substrate placeholder may legitimately have a NaN
                        # I_model; treat as warning at seal (operator may
                        # be sealing pre-run with a placeholder), not error.
                        warnings.append(
                            f"L1 Protocol check: {ce.code} (likely substrate "
                            f"placeholder; will fire as R1 strike on first "
                            f"mutator submission). {ce.remediation}"
                        )
                except Exception as ie:  # noqa: BLE001
                    warnings.append(f"L1 Protocol check: test_model.py import error ({ie})")
    except _ApparatusImportError as ae:
        errors.append(f"APPARATUS: L1 Protocol boundary check unrunnable — {ae}")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"could not run L1 Protocol boundary check: {exc}")

    # 15. L2 typed evidence contract (Task #71): when the rubric declares
    # an `evidence_contract` block, parse the evidence with the explicit
    # spec rather than auto-detecting. Raises EvidenceContractError on
    # shape violations — fail-loud at seal time, not silent drop at iter time.
    try:
        ev_orch = _import_apparatus_module(
            "src.ztare.orchestrator",
            ("EvidenceContractError", "EvidenceFormat", "get_evidence_spec"),
        )
        EvidenceContractError = ev_orch.EvidenceContractError
        EvidenceFormat = ev_orch.EvidenceFormat
        get_evidence_spec = ev_orch.get_evidence_spec
        ev_parsers = _import_apparatus_module("src.ztare.fit.parsers", ("parse_evidence_typed",))
        parse_evidence_typed = ev_parsers.parse_evidence_typed
        _ev_spec = get_evidence_spec(rubric_data)
        if _ev_spec is not None and _ev_spec.format is not EvidenceFormat.NONE:
            try:
                _xs, _ys = parse_evidence_typed(text, _ev_spec)
                # Success: spec-driven parser extracted N rows
            except EvidenceContractError as ec_err:
                errors.append(f"L2 evidence contract: {ec_err}")
    except _ApparatusImportError as ae:
        errors.append(f"APPARATUS: L2 evidence-contract check unrunnable — {ae}")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"could not run L2 evidence-contract check: {exc}")

    # 14. Gap #3c: data-shape verification (substrate_probe). Cross-check
    # rubric's declared cage_meta.class against the actual evidence-data
    # geometry. Closes the gp159 wrong-class chain at the LAST possible
    # boundary before iter spend: even if the rubric/filesystem look
    # consistent (#13), the data shape itself must agree.
    if cage_meta_class and cage_meta_class.lower() not in {"audit", "literature", "proof_target", "nd_features"}:
        # Skip classes whose targets don't live in evidence.txt's y-column
        # (audit/literature score on critique; nd_features data lives in
        # features.py). For 1d / time_series / closed_form_constant the
        # y-column is the source of truth.
        try:
            import re as _re
            probe_mod = _import_apparatus_module(
                "src.ztare.scaffold.substrate_probe", ("verify_class_against_data",)
            )
            verify_class_against_data = probe_mod.verify_class_against_data
            # Extract numeric y-column from evidence.txt. Accepts whitespace
            # OR markdown-table format (matches fit_primitive parser).
            ys: list[float] = []
            for raw in text.splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("==="):
                    continue
                if "|" in line:
                    inner = line.strip("|").strip()
                    if all(set(p.strip()) <= set("-:= \t") for p in inner.split("|")):
                        continue
                    parts = [p.strip() for p in inner.split("|") if p.strip()]
                else:
                    parts = line.split()
                if len(parts) < 2:
                    continue
                try:
                    ys.append(float(parts[-1]))
                except ValueError:
                    continue
            if len(ys) >= 5:
                ok, msg = verify_class_against_data(cage_meta_class, ys)
                if not ok:
                    errors.append(f"data-shape probe: {msg}")
        except _ApparatusImportError as ae:
            errors.append(f"APPARATUS: data-shape probe unrunnable — {ae}")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"could not run data-shape probe: {exc}")

    if strict_mode:
        errors.extend(class_diags)
    else:
        warnings.extend(class_diags)

    all_pass = len(errors) == 0
    diagnostics: list[str] = []
    if cage_meta_class:
        mode_label = "STRICT" if strict_mode else "soft"
        diagnostics.append(f"  ℹ️  class-aware lints active: cage_meta.class={cage_meta_class!r} (mode={mode_label})")
    for e in errors:
        diagnostics.append(f"  ❌ {e}")
    for w in warnings:
        diagnostics.append(f"  ⚠️  {w}")

    return all_pass, diagnostics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evidence pre-flight validator (GP-162 + GP-157 Phase 7).")
    parser.add_argument("project_slug", help="Project slug (e.g. gp159_retrieval_trap)")
    parser.add_argument(
        "--rubric",
        default=None,
        help="Optional path to rubric JSON. Enables class-aware lints + STRICT mode honor.",
    )
    args = parser.parse_args(argv)

    slug = args.project_slug.replace("projects/", "")
    rubric_path = Path(args.rubric) if args.rubric else None
    passed, diagnostics = validate_evidence(slug, rubric_path=rubric_path)

    print(f"validate_evidence: {slug}")
    if diagnostics:
        for d in diagnostics:
            print(d)
    if passed:
        print(f"\n  RESULT: PASSED")
        return 0
    else:
        print(f"\n  RESULT: FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
