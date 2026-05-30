#!/usr/bin/env python3
"""Compile + L3 audit for a single Lean proof artifact (canonical proof-audit).

Generalised from the original PR_A1-specific receipt. The audit takes any
Lean target and emits a typed receipt covering kernel compile status,
``#print axioms`` output (with auto-probe for files that don't already
declare them), and the deterministic L3 anti-pattern stack. The receipt
records evidence only — no proof credit, no public correctness claim.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from leanmill_paths import DATA_DIR, FACTORY_POLICY
from src.ztare.leanmill.policy import read_policy

# Audit primitives consolidated under ztare.gates (canonical location since
# 2026-05-29 consolidation). The scripts/public/control/v33_*.py files are
# backward-compat shims; new code imports directly from ztare.gates.
from ztare.gates import v33_consequence_exposure_gate as consequence_gate
from ztare.gates import v33_currency_mismatch_gate as currency_gate
from ztare.gates import v33_indirect_leakage_gate as indirect_gate
from ztare.gates import v33_paraphrase_gate as paraphrase_gate
from ztare.gates import v33_preflight_risk_detector as preflight_gate
from ztare.gates import v33_single_lemma_exact_gate as exact_gate

# Canonical Lean compile + axiom-probe primitives (consolidated 2026-05-29
# under ztare.gates.lean_compile_primitives). Local thin wrappers below
# keep the original names so the rest of this module is untouched.
from ztare.gates.lean_compile_primitives import (  # noqa: E402
    AXIOM_OUTPUT_RE as _CANONICAL_AXIOM_OUTPUT_RE,
    LEAN_ERROR_RE as _CANONICAL_LEAN_ERROR_RE,
    DECL_START_RE as _CANONICAL_DECL_START_RE,
    parse_axiom_output as _canonical_parse_axiom_output,
    run_lake_compile as _canonical_run_lake_compile,
    run_lake_compile_source as _canonical_run_lake_compile_source,
    probe_axioms_via_augment as _canonical_probe_axioms_via_augment,
)


DEFAULT_LEAN_ROOT = "ztare_proofs"
DEFAULT_TARGET = "ztare_proofs/ZtareProofs/PR_A1_BohrCoeffExpNe_Discharge.lean"
DEFAULT_OUT = f"{DATA_DIR}/leanmill_proof_audit.json"
DEFAULT_MD = f"{DATA_DIR}/leanmill_proof_audit.md"
DEFAULT_ALLOWED_AXIOMS = ["propext", "Classical.choice", "Quot.sound"]

DECL_START_RE = re.compile(
    r"(?m)^\s*(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(?:theorem|lemma)\s+([^\s:]+)"
)
AXIOM_OUTPUT_RE = re.compile(
    r"'([^']+)'\s+depends on axioms:\s+\[([^\]]*)\]",
    re.MULTILINE | re.DOTALL,
)
LEAN_ERROR_RE = re.compile(r"^\S*\.lean:\d+:\d+: error:", re.MULTILINE)
PROOF_START_RE = re.compile(r":=\s*by\b")
ASSIGN_RE = re.compile(r":=")
LINE_COMMENT_RE = re.compile(r"--.*$")
BLOCK_COMMENT_RE = re.compile(r"/-[\s\S]*?-/")
SORRY_RE = re.compile(r"\bsorry\b")
ADMIT_RE = re.compile(r"\badmit\b")
AXIOM_DECL_RE = re.compile(r"^\s*axiom\s+", re.MULTILINE)


@dataclass(frozen=True)
class DeclBlock:
    name: str
    start: int
    end: int
    block: str
    clean_block: str
    statement: str


def _strip_lean_comments(text: str) -> str:
    without_blocks = BLOCK_COMMENT_RE.sub("", text)
    return "\n".join(LINE_COMMENT_RE.sub("", line) for line in without_blocks.splitlines())


def _policy_allowed_axioms(policy_path: str | Path) -> list[str]:
    policy = read_policy(policy_path)
    operations = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    audit = operations.get("lean_compile_audit") if isinstance(operations.get("lean_compile_audit"), dict) else {}
    raw = audit.get("allowed_kernel_axioms") if isinstance(audit.get("allowed_kernel_axioms"), list) else []
    allowed = [str(item) for item in raw if str(item)]
    return allowed or list(DEFAULT_ALLOWED_AXIOMS)


def _relative_to_or_self(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def parse_axiom_output(output: str) -> dict[str, list[str]]:
    """Thin wrapper around ztare.gates.lean_compile_primitives.parse_axiom_output."""
    return _canonical_parse_axiom_output(output)


def _static_counts(source: str) -> dict[str, int]:
    clean = _strip_lean_comments(source)
    return {
        "sorry_count": len(SORRY_RE.findall(clean)),
        "admit_count": len(ADMIT_RE.findall(clean)),
        "axiom_decl_count": len(AXIOM_DECL_RE.findall(clean)),
    }


def extract_declarations(source: str) -> list[DeclBlock]:
    matches = list(DECL_START_RE.finditer(source))
    decls: list[DeclBlock] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        block = source[start:end].strip()
        clean_block = _strip_lean_comments(block).strip()
        proof_match = PROOF_START_RE.search(clean_block) or ASSIGN_RE.search(clean_block)
        statement = clean_block[: proof_match.start()].strip() if proof_match else clean_block
        decls.append(
            DeclBlock(
                name=match.group(1).strip(),
                start=start,
                end=end,
                block=block,
                clean_block=clean_block,
                statement=statement,
            )
        )
    return decls


def run_compile(target: Path, lean_root: Path, *, timeout_s: int) -> dict[str, Any]:
    """Thin wrapper around ztare.gates.lean_compile_primitives.run_lake_compile."""
    return _canonical_run_lake_compile(target, lean_root, timeout_s=timeout_s)


def _namespace_closers(prefix: str) -> str:
    stack: list[str] = []
    for line in prefix.splitlines():
        open_match = re.match(r"\s*namespace\s+([A-Za-z0-9_.'`]+)\s*$", line)
        if open_match:
            stack.append(open_match.group(1))
            continue
        close_match = re.match(r"\s*end(?:\s+([A-Za-z0-9_.'`]+))?\s*$", line)
        if close_match and stack:
            name = close_match.group(1)
            if name and name in stack:
                stack = stack[: stack.index(name)]
            else:
                stack.pop()
    return "\n".join(f"end {name}" for name in reversed(stack))


def _probe_source(source: str, decl: DeclBlock, tactic_body: str) -> str | None:
    original = source[decl.start : decl.end]
    proof_match = PROOF_START_RE.search(original)
    if not proof_match:
        return None
    prefix = source[: decl.start]
    header = original[: proof_match.start()].rstrip()
    closers = _namespace_closers(prefix)
    return f"{prefix}{header} := by\n{tactic_body.rstrip()}\n\n{closers}\n"


def _run_temp_lean(source: str, lean_root: Path, *, timeout_s: int) -> tuple[bool | None, str]:
    """Thin wrapper around ztare.gates.lean_compile_primitives.run_lake_compile_source."""
    return _canonical_run_lake_compile_source(
        source, lean_root, timeout_s=timeout_s, prefix="leanmill_proof_audit_",
    )


def _deep_exact_verify(source: str, decl: DeclBlock, lean_root: Path, *, timeout_s: int) -> dict[str, Any]:
    probe = _probe_source(source, decl, "  intros\n  exact?")
    if probe is None:
        return {"single_lemma_exact_confirmed": None, "error": "no tactic proof"}
    ok, output = _run_temp_lean(probe, lean_root, timeout_s=timeout_s)
    suggested = exact_gate.EXACT_SUCCESS_RE.search(output)
    failed = exact_gate.EXACT_FAIL_RE.search(output)
    confirmed = (suggested is not None) and (failed is None)
    return {
        "single_lemma_exact_confirmed": confirmed,
        "probe_compile_ok": ok,
        "exact_hint": suggested.group(1).strip()[:180] if suggested else None,
        "tail": output[-300:] if not confirmed else "",
    }


def _deep_indirect_verify(
    source: str,
    decl: DeclBlock,
    lean_root: Path,
    *,
    closer: str,
    timeout_s: int,
) -> dict[str, Any]:
    floor_probe = _probe_source(
        source,
        decl,
        "  first\n  | rfl\n  | trivial\n  | simp only []\n  | norm_num\n  | decide",
    )
    closer_probe = _probe_source(source, decl, f"  {closer}")
    if floor_probe is None or closer_probe is None:
        return {"indirect_leakage_confirmed": None, "error": "no tactic proof"}
    floor_ok, floor_tail = _run_temp_lean(floor_probe, lean_root, timeout_s=timeout_s)
    closer_ok, closer_tail = _run_temp_lean(closer_probe, lean_root, timeout_s=timeout_s)
    confirmed = floor_ok is False and closer_ok is True
    return {
        "indirect_leakage_confirmed": confirmed,
        "trivial_floor_closes": floor_ok,
        "global_automation_closes": closer_ok,
        "floor_tail": "" if floor_ok else floor_tail[-220:],
        "closer_tail": "" if closer_ok else closer_tail[-220:],
    }


def audit_l3(
    source: str,
    lean_root: Path,
    *,
    deep_v33: bool,
    timeout_s: int,
) -> dict[str, Any]:
    declarations = extract_declarations(source)
    rows: list[dict[str, Any]] = []
    confirmed_blockers: list[dict[str, Any]] = []
    review_flags: list[dict[str, Any]] = []
    for decl in declarations:
        row: dict[str, Any] = {"name": decl.name}
        preflight = preflight_gate.detect_risks(decl.statement)
        paraphrase = paraphrase_gate.detect_gold_name_verbatim(decl.clean_block)
        corpus = paraphrase_gate.independent_corpus_confirm(paraphrase.get("primary_cited"))
        exact_shape = exact_gate.detect_shape(decl.statement)
        indirect = indirect_gate.detect_shape(decl.clean_block)
        currency = currency_gate.detect_shape(decl.statement)
        consequence = consequence_gate.detect_shape(decl.clean_block)
        row.update(
            {
                "preflight_risk": preflight,
                "paraphrase": {
                    "detect": paraphrase,
                    "corpus_confirm": corpus,
                    # BLOCKER only on a TRIVIAL restatement (bare exact/term-mode of a
                    # gold lemma). A single gold lemma that CLOSES a proof doing real work
                    # (funext/simp/rw/…) is legitimate library composition -> advisory, not
                    # a blocker (2026-05-30 fix; ATLAS/APN audits showed the suspect-only
                    # rule false-flagged real proofs).
                    "confirmed": bool(paraphrase.get("trivial_restatement") and corpus.get("in_mathlib")),
                    "advisory": bool(paraphrase.get("gold_name_verbatim_suspect")
                                     and not paraphrase.get("trivial_restatement")
                                     and corpus.get("in_mathlib")),
                },
                "single_lemma_exact": {"shape": exact_shape, "verify": None},
                "indirect_leakage": {"shape": indirect, "verify": None},
                "currency_mismatch": currency,
                "consequence_exposure": consequence,
            }
        )

        if row["paraphrase"]["confirmed"]:
            confirmed_blockers.append({"name": decl.name, "class": "gold_name_verbatim_confirmed"})
        elif row["paraphrase"]["advisory"]:
            review_flags.append({"name": decl.name, "class": "gold_name_verbatim_library_close_advisory"})
        if bool(preflight.get("vacuity_suspected")):
            review_flags.append({"name": decl.name, "class": "vacuity_shape_suspected"})
        if bool(currency.get("scalar_wrapper_suspect")):
            review_flags.append({"name": decl.name, "class": "currency_mismatch_shape_suspected"})
        # Consequence-exposure (the assumed-hard-target smuggle class). The
        # gate's `blocking` field is already gated on a non-empty
        # hard-target set inside detect_shape (`_blk = bool(targets)`), so
        # with the default empty heads it is advisory-only and can never add
        # a confirmed_blocker on a clean file.
        if bool(consequence.get("blocking")):
            confirmed_blockers.append({"name": decl.name, "class": "consequence_exposure_confirmed"})
        elif bool(consequence.get("consequence_exposure_suspect")):
            review_flags.append({"name": decl.name, "class": "consequence_exposure_shape_suspected"})

        if bool(exact_shape.get("single_lemma_exact_suspect")):
            if deep_v33:
                verify = _deep_exact_verify(source, decl, lean_root, timeout_s=timeout_s)
                row["single_lemma_exact"]["verify"] = verify
                if verify.get("single_lemma_exact_confirmed") is True:
                    confirmed_blockers.append({"name": decl.name, "class": "single_lemma_exact_confirmed"})
                elif verify.get("single_lemma_exact_confirmed") is None:
                    review_flags.append({"name": decl.name, "class": "single_lemma_exact_inconclusive"})
            else:
                review_flags.append({"name": decl.name, "class": "single_lemma_exact_shape_suspected"})

        if bool(indirect.get("indirect_leakage_suspect")):
            if deep_v33 and indirect.get("closer_tactic"):
                verify = _deep_indirect_verify(
                    source,
                    decl,
                    lean_root,
                    closer=str(indirect.get("closer_tactic")),
                    timeout_s=timeout_s,
                )
                row["indirect_leakage"]["verify"] = verify
                if verify.get("indirect_leakage_confirmed") is True:
                    confirmed_blockers.append({"name": decl.name, "class": "indirect_leakage_confirmed"})
                elif verify.get("indirect_leakage_confirmed") is None:
                    review_flags.append({"name": decl.name, "class": "indirect_leakage_inconclusive"})
            else:
                review_flags.append({"name": decl.name, "class": "indirect_leakage_shape_suspected"})
        rows.append(row)

    if confirmed_blockers:
        status = "confirmed_blocker"
    elif review_flags:
        status = "advisory_review"
    else:
        status = "pass"
    return {
        "schema": "leanmill-pr-a1-l3-audit-v1",
        "status": status,
        "declaration_count": len(declarations),
        "confirmed_blockers": confirmed_blockers,
        "review_flags": review_flags,
        "deep_v33": deep_v33,
        "rows": rows,
        "credit_boundary": "L3 audit evidence only; no proof credit or public correctness claim is granted here",
    }


def _probe_axioms(target: Path, source: str, lean_root: Path, *, timeout_s: int) -> tuple[dict[str, list[str]], str]:
    """Augment-and-compile axiom probe.

    `run_compile` only parses `'<name>' depends on axioms: [...]` lines from
    the target's own output. Files authored without explicit `#print axioms`
    directives (e.g. third-party proofs routed through Lane B) therefore
    leave `axiom_map` empty even when the proof compiled cleanly. Probe by
    writing a scratch copy = original source + `#print axioms <decl>` lines
    for every top-level theorem/lemma found by `extract_declarations`, then
    parsing axiom output from the probe compile.
    """
    decls = extract_declarations(source)
    if not decls:
        return {}, ""
    print_lines = "\n".join(f"#print axioms {d.name}" for d in decls)
    augmented = source.rstrip() + "\n\n-- pr_a1_audit axiom probe --\n" + print_lines + "\n"
    with tempfile.TemporaryDirectory(prefix="leanmill_axiom_probe_") as td:
        probe = Path(td) / target.name
        probe.write_text(augmented, encoding="utf-8")
        try:
            proc = subprocess.run(
                ["lake", "env", "lean", str(probe)],
                cwd=str(lean_root), text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=timeout_s, check=False,
            )
            output = (proc.stdout or "") + "\n" + (proc.stderr or "")
            return parse_axiom_output(output), output[-1500:]
        except subprocess.TimeoutExpired:
            return {}, "probe_timed_out"


def build(args: argparse.Namespace) -> dict[str, Any]:
    target = Path(args.target)
    lean_root = Path(args.lean_root)
    source = target.read_text(encoding="utf-8")
    allowed_axioms = _policy_allowed_axioms(args.factory_policy)
    compile_receipt = run_compile(target, lean_root, timeout_s=args.timeout_s)
    static = _static_counts(source)
    axiom_map = compile_receipt.get("axioms") if isinstance(compile_receipt.get("axioms"), dict) else {}
    axiom_probe_tail = ""
    if bool(compile_receipt.get("ok")) and not axiom_map:
        axiom_map, axiom_probe_tail = _probe_axioms(target, source, lean_root, timeout_s=args.timeout_s)
        compile_receipt = {**compile_receipt, "axioms": axiom_map, "axiom_probe_output_tail": axiom_probe_tail}
    disallowed_axioms = {
        name: [ax for ax in axioms if ax not in set(allowed_axioms)]
        for name, axioms in axiom_map.items()
        if isinstance(axioms, list) and any(ax not in set(allowed_axioms) for ax in axioms)
    }
    l3 = audit_l3(source, lean_root, deep_v33=not args.skip_deep_v33, timeout_s=args.timeout_s)
    static_clean = all(int(static.get(key) or 0) == 0 for key in ("sorry_count", "admit_count", "axiom_decl_count"))
    compile_ok = bool(compile_receipt.get("ok"))
    # A clean-compiling file with no theorem/lemma declarations has nothing to
    # `#print axioms` over; an empty axiom_map then means "nothing to verify",
    # NOT "disallowed". Treat an empty map as a problem only when declarations
    # we expected to probe exist (and then as inconclusive, never "disallowed").
    provable_decls = extract_declarations(source)
    axiom_probe_satisfied = bool(axiom_map) or not provable_decls
    axiom_allowlist_ok = (not disallowed_axioms) and axiom_probe_satisfied
    if not static_clean:
        status = "static_open_or_axiom"
    elif not compile_ok:
        status = "compile_failed"
    elif not axiom_allowlist_ok:
        status = (
            "disallowed_axiom_dependency" if disallowed_axioms
            else "axiom_probe_inconclusive"
        )
    else:
        # Status-rule fix (2026-05-29): distinguish top-level vs helper.
        # Original rule promoted ANY confirmed_blocker to file-level
        # `l3_confirmed_blocker`, including blockers on internal helper
        # lemmas. That conflates helper-shape flags (normal Lean
        # scaffolding) with top-level laundering. Helper-only blockers
        # downgrade to `compile_pass_l3_advisory_review` with a structured
        # `top_level_target_name` field naming the user-declared target.
        l3_blockers = l3.get("confirmed_blockers") or []
        top_level_target = getattr(args, "target_name", None) or ""
        if top_level_target:
            top_level_blockers = [
                b for b in l3_blockers if b.get("name") == top_level_target
            ]
            helper_blockers = [
                b for b in l3_blockers if b.get("name") != top_level_target
            ]
        else:
            # No declared target: do NOT guess "last decl = top-level" — that
            # mis-attributes a real top-level blocker to a helper (silent
            # downgrade) or a helper to top-level (false escalate). Fail closed:
            # treat every confirmed blocker as top-level so a laundering blocker
            # is never downgraded. Pass --target-name for the precise split.
            top_level_blockers = list(l3_blockers)
            helper_blockers = []
        if top_level_blockers:
            status = "l3_confirmed_blocker_top_level"
        elif helper_blockers and l3.get("status") == "confirmed_blocker":
            status = "compile_pass_l3_advisory_review_helper_blockers_only"
        elif l3.get("status") == "advisory_review":
            status = "compile_pass_l3_advisory_review"
        else:
            status = "compile_pass_l3_advisory_pass"
    return {
        "schema": "leanmill-pr-a1-compile-l3-audit-v1",
        "generated_at_epoch": int(time.time()),
        "target": str(target),
        "lean_root": str(lean_root),
        "status": status,
        "static_clean": static_clean,
        "static": static,
        "compile": compile_receipt,
        "kernel_axiom_policy": {
            "allowed_axioms": allowed_axioms,
            "allowlist_ok": axiom_allowlist_ok,
            "disallowed_axioms": disallowed_axioms,
            "source": str(args.factory_policy),
        },
        "l3_audit": l3,
        "top_level_target_resolved": top_level_target if 'top_level_target' in locals() else None,
        "top_level_l3_blockers": (
            top_level_blockers if 'top_level_blockers' in locals() else []
        ),
        "helper_l3_blockers": (
            helper_blockers if 'helper_blockers' in locals() else []
        ),
        "meta_reasoning_receipt": {
            "failure_mode": "candidate closure could be treated as value before compile, axiom, or L3 leakage checks are recorded",
            "mechanized_prevention": [
                "compile must pass through lake env lean",
                "printed kernel axioms must stay inside the policy allowlist",
                "confirmed v33 L3 anti-patterns block review-ready status",
                "advisory status never grants proof credit",
            ],
            "gaming_guard": "the receipt changes dashboard routing only; proof credit remains outside this script",
        },
        "credit_boundary": "compile plus L3 audit receipt only; proof credit/public correctness requires the governed proof-review path",
    }


def write_markdown(path: str | Path, payload: dict[str, Any]) -> None:
    compile_receipt = payload.get("compile") if isinstance(payload.get("compile"), dict) else {}
    l3 = payload.get("l3_audit") if isinstance(payload.get("l3_audit"), dict) else {}
    policy = payload.get("kernel_axiom_policy") if isinstance(payload.get("kernel_axiom_policy"), dict) else {}
    lines = [
        "# PR_A1 Compile and L3 Audit",
        "",
        f"- generated_at_epoch: `{payload.get('generated_at_epoch')}`",
        f"- target: `{payload.get('target')}`",
        f"- status: `{payload.get('status')}`",
        f"- static_clean: `{payload.get('static_clean')}`",
        f"- compile_ok: `{compile_receipt.get('ok')}`",
        f"- compile_elapsed_s: `{compile_receipt.get('elapsed_s')}`",
        f"- axiom_allowlist_ok: `{policy.get('allowlist_ok')}`",
        f"- l3_status: `{l3.get('status')}`",
        f"- confirmed_blocker_count: `{len(l3.get('confirmed_blockers') or [])}`",
        f"- review_flag_count: `{len(l3.get('review_flags') or [])}`",
        f"- credit_boundary: {payload.get('credit_boundary')}",
        "",
        "## Axioms",
        "",
    ]
    axioms = compile_receipt.get("axioms") if isinstance(compile_receipt.get("axioms"), dict) else {}
    for theorem, names in sorted(axioms.items()):
        rendered = ", ".join(str(name) for name in names)
        lines.append(f"- `{theorem}`: `{rendered}`")
    lines.extend(["", "## L3 Summary", ""])
    for blocker in l3.get("confirmed_blockers") or []:
        lines.append(f"- blocker `{blocker.get('class')}` in `{blocker.get('name')}`")
    for flag in l3.get("review_flags") or []:
        lines.append(f"- review `{flag.get('class')}` in `{flag.get('name')}`")
    if not (l3.get("confirmed_blockers") or l3.get("review_flags")):
        lines.append("- no confirmed blocker or advisory review flag recorded")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _self_test() -> int:
    sample_output = (
        "'Foo.a' depends on axioms: [propext,\n Classical.choice,\n Quot.sound]\n"
        "'Foo.b' depends on axioms: [propext, Classical.choice, Quot.sound]\n"
    )
    parsed = parse_axiom_output(sample_output)
    assert parsed["Foo.a"] == ["propext", "Classical.choice", "Quot.sound"], parsed
    source = """import Mathlib
namespace Demo
lemma first : True := by
  trivial
lemma second (a b : Nat) : a = a := by
  rfl
end Demo
"""
    decls = extract_declarations(source)
    assert [d.name for d in decls] == ["first", "second"], decls
    assert _static_counts("lemma x : True := by\n  sorry\n")["sorry_count"] == 1
    assert _static_counts("/- sorry -/\nlemma x : True := by\n  trivial\n")["sorry_count"] == 0
    l3 = audit_l3(source, Path("."), deep_v33=False, timeout_s=5)
    assert l3["declaration_count"] == 2, l3
    print("leanmill_pr_a1_audit self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=DEFAULT_TARGET)
    ap.add_argument("--target-name", default=None,
                    help="Top-level theorem name to audit. If set, the file-level "
                         "L3 status only escalates on blockers attached to this "
                         "decl; helper-lemma blockers degrade to advisory_review.")
    ap.add_argument("--lean-root", default=DEFAULT_LEAN_ROOT)
    ap.add_argument("--factory-policy", default=str(FACTORY_POLICY))
    ap.add_argument("--timeout-s", type=int, default=120)
    ap.add_argument("--skip-deep-v33", action="store_true")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(args.md, payload)
    print(
        json.dumps(
            {
                "out": args.out,
                "md": args.md,
                "status": payload.get("status"),
                "compile_ok": (payload.get("compile") or {}).get("ok"),
                "l3_status": (payload.get("l3_audit") or {}).get("status"),
                "axiom_allowlist_ok": (payload.get("kernel_axiom_policy") or {}).get("allowlist_ok"),
            },
            sort_keys=True,
        )
    )
    return 0 if payload.get("status") in {"compile_pass_l3_advisory_pass", "compile_pass_l3_advisory_review"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
