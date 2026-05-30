#!/usr/bin/env python3
"""Build a dry-run auto-prover obligation packet from ZtareProofs sorries."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
CONTROL_DIR = REPO / "scripts" / "public" / "control"
if str(CONTROL_DIR) not in sys.path:
    sys.path.insert(0, str(CONTROL_DIR))

from src.ztare.leanmill.common import write_json_atomic, write_text_atomic  # noqa: E402

try:  # noqa: E402
    import v33_preflight_risk_detector
except Exception:  # noqa: BLE001
    v33_preflight_risk_detector = None
try:  # noqa: E402
    import v33_paraphrase_gate
except Exception:  # noqa: BLE001
    v33_paraphrase_gate = None
try:  # noqa: E402
    import v33_indirect_leakage_gate
except Exception:  # noqa: BLE001
    v33_indirect_leakage_gate = None
try:  # noqa: E402
    import v33_currency_mismatch_gate
except Exception:  # noqa: BLE001
    v33_currency_mismatch_gate = None

DEFAULT_ROOT = REPO / "ztare_proofs" / "ZtareProofs"
DEFAULT_OUT = REPO / "analytics" / "public" / "queries" / "ztareproofs_auto_prover_packet.json"
DEFAULT_MD = DEFAULT_OUT.with_suffix(".md")
DEFAULT_AUDIT_FILE = DEFAULT_ROOT / "PR_A1_BohrCoeffExpNe_Discharge.lean"

DECL_RE = re.compile(
    r"^\s*(?:@[^\n]*\n\s*)?"
    r"(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(?P<kind>theorem|lemma)\s+(?P<name>[^\s:{(]+)"
)
ANY_DECL_RE = re.compile(
    r"^\s*(?:@[^\n]*\n\s*)?"
    r"(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(?:theorem|lemma|def|class|structure|inductive)\s+"
)
SORRY_RE = re.compile(r"\bsorry\b")
AXIOM_RE = re.compile(r"^\s*axiom\s+([A-Za-z_][\w']*)", re.MULTILINE)
UNSAFE_TOKEN_RE = re.compile(r"\b(admit|native_decide|unsafe)\b")

FAMILY_RULES: list[tuple[str, str]] = [
    ("PR_A1", "pr_a1_almost_periodic_bohr"),
    ("PR_A2", "pr_a2_almost_periodic"),
    ("PR_B", "pr_b_finite_spec"),
    ("ns_", "ns_trackb"),
    ("batched_", "ns_trackb_generated_batch"),
    ("typed_patch", "ns_trackb_generated_patch"),
    ("apn", "apn"),
    ("oeis", "oeis"),
]


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def _imports(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        if line.startswith("import "):
            out.append(line)
        elif line.strip() and not line.startswith("--"):
            if out:
                break
    return out


def _code_lines(text: str) -> list[str]:
    """Return Lean-ish source lines with comments removed, preserving line count."""
    out: list[str] = []
    block_depth = 0
    for line in text.splitlines():
        i = 0
        buf: list[str] = []
        while i < len(line):
            if block_depth:
                next_start = line.find("/-", i)
                next_end = line.find("-/", i)
                if next_end < 0:
                    i = len(line)
                    continue
                if next_start >= 0 and next_start < next_end:
                    block_depth += 1
                    i = next_start + 2
                    continue
                block_depth -= 1
                i = next_end + 2
                continue
            line_comment = line.find("--", i)
            block_comment = line.find("/-", i)
            if line_comment < 0 and block_comment < 0:
                buf.append(line[i:])
                break
            if line_comment >= 0 and (block_comment < 0 or line_comment < block_comment):
                buf.append(line[i:line_comment])
                break
            buf.append(line[i:block_comment])
            block_depth = 1
            i = block_comment + 2
        out.append("".join(buf))
    return out


def _code_text(text: str) -> str:
    return "\n".join(_code_lines(text))


def _raw_sorry_count(text: str) -> int:
    return len(SORRY_RE.findall(_code_text(text)))


def _structural_family(path: Path, block_text: str = "") -> str:
    probe = f"{path.name}\n{block_text}".lower()
    for token, family in FAMILY_RULES:
        if token.lower() in probe:
            return family
    if "measuretheory" in probe or "intervalintegral" in probe or "bohr" in probe:
        return "analysis_measure_or_almost_periodic"
    if "complex" in probe or "fourier" in probe or "integral" in probe:
        return "analysis_complex_or_fourier"
    if "linearalgebra" in probe or "matrix" in probe or "spectrum" in probe:
        return "linear_algebra_or_spectral"
    return "uncategorized_formal"


def _difficulty_class(block_text: str, imports: list[str], file_text: str) -> str:
    hay = "\n".join(imports + [block_text]).lower()
    file_low = file_text.lower()
    if "axiom " in file_low or "navier" in hay or "leray" in hay or "pde" in hay:
        return "hard_open_math_or_axiom_surface"
    if "measuretheory" in hay or "intervalintegral" in hay or "bochner" in hay or "∫" in block_text:
        return "analysis_premise_bound"
    if "filter" in hay or "tendsto" in hay or "summable" in hay or "at_top" in hay:
        return "limit_or_series_bridge"
    if "complex" in hay or "fourier" in hay or "exp" in hay:
        return "complex_harmonic_bridge"
    if len(block_text.splitlines()) <= 4 and len(block_text) <= 360:
        return "small_tactic_or_statement_gap"
    return "medium_formalization_gap"


def _rank_score(row: dict[str, Any]) -> int:
    score = 0
    difficulty = str(row.get("difficulty_class") or "")
    score += {
        "small_tactic_or_statement_gap": 10,
        "complex_harmonic_bridge": 30,
        "limit_or_series_bridge": 35,
        "analysis_premise_bound": 45,
        "medium_formalization_gap": 50,
        "hard_open_math_or_axiom_surface": 90,
    }.get(difficulty, 60)
    score += 4 * int(row.get("sorry_count_in_decl") or 0)
    score += min(30, int(row.get("decl_line_count") or 0) // 4)
    return score


def _file_summary(path: Path) -> dict[str, Any]:
    text = path.read_text(errors="ignore")
    lines = text.splitlines()
    code = _code_text(text)
    imports = _imports(_code_lines(text))
    family = _structural_family(path, code[:1200])
    return {
        "path": _rel(path),
        "structural_family": family,
        "line_count": len(lines),
        "raw_sorry_count": _raw_sorry_count(code),
        "axiom_count": len(AXIOM_RE.findall(code)),
        "unsafe_token_count": len(UNSAFE_TOKEN_RE.findall(code)),
        "import_count": len(imports),
    }


def _signature(block: list[str]) -> str:
    text = "\n".join(block)
    idx = text.find(":= ")
    if idx >= 0:
        return text[:idx].rstrip() + " := by\n  sorry"
    idx = text.find(" by")
    if idx >= 0:
        return text[:idx].rstrip() + " := by\n  sorry"
    return text.strip() + " := by\n  sorry"


def _decl_blocks(path: Path) -> list[dict[str, Any]]:
    file_text = path.read_text(errors="ignore")
    file_code = _code_text(file_text)
    lines = _code_lines(file_text)
    imports = _imports(lines)
    starts: list[tuple[int, re.Match[str]]] = []
    for idx, line in enumerate(lines):
        match = DECL_RE.match(line)
        if match:
            starts.append((idx, match))
    rows: list[dict[str, Any]] = []
    for pos, (start, match) in enumerate(starts):
        next_decl = len(lines)
        for probe in range(start + 1, len(lines)):
            if ANY_DECL_RE.match(lines[probe]):
                next_decl = probe
                break
        block = lines[start:next_decl]
        block_text = "\n".join(block)
        if "sorry" not in block_text:
            continue
        row = {
            "name": match.group("name"),
            "kind": match.group("kind"),
            "path": _rel(path),
            "line": start + 1,
            "imports": imports,
            "doc_excerpt": _signature(block),
            "status": "open_obligation",
            "source": "ztareproofs_sorry_inventory",
            "ordinal_in_file": pos,
            "structural_family": _structural_family(path, block_text),
            "difficulty_class": _difficulty_class(block_text, imports, file_code),
            "sorry_count_in_decl": _raw_sorry_count(block_text),
            "decl_line_count": len(block),
            "file_raw_sorry_count": _raw_sorry_count(file_code),
            "file_axiom_count": len(AXIOM_RE.findall(file_code)),
        }
        row["rank_score"] = _rank_score(row)
        rows.append(row)
    return rows


def _all_decl_blocks(path: Path) -> list[dict[str, Any]]:
    file_text = path.read_text(errors="ignore")
    lines = _code_lines(file_text)
    starts: list[tuple[int, re.Match[str]]] = []
    for idx, line in enumerate(lines):
        match = DECL_RE.match(line)
        if match:
            starts.append((idx, match))
    rows: list[dict[str, Any]] = []
    for pos, (start, match) in enumerate(starts):
        next_decl = len(lines)
        for probe in range(start + 1, len(lines)):
            if ANY_DECL_RE.match(lines[probe]):
                next_decl = probe
                break
        block = "\n".join(lines[start:next_decl])
        rows.append({
            "name": match.group("name"),
            "kind": match.group("kind"),
            "line": start + 1,
            "ordinal_in_file": pos,
            "block_text": block,
            "sorry_count": _raw_sorry_count(block),
        })
    return rows


def _static_l3_decl_audit(block_text: str) -> dict[str, Any]:
    flags: list[str] = []
    details: dict[str, Any] = {}
    if v33_preflight_risk_detector is not None:
        try:
            risk = v33_preflight_risk_detector.detect_risks(block_text)
            details["vacuity_preflight"] = risk
            flags.extend(str(x) for x in risk.get("risk_flags", []) if str(x))
            if risk.get("vacuity_suspected"):
                flags.append("vacuity_suspected")
        except Exception as exc:  # noqa: BLE001
            details["vacuity_preflight"] = {"error": f"{type(exc).__name__}: {exc}"}
    if v33_paraphrase_gate is not None:
        try:
            detect = v33_paraphrase_gate.detect_gold_name_verbatim(block_text)
            corpus = (
                v33_paraphrase_gate.independent_corpus_confirm(detect.get("primary_cited"))
                if detect.get("gold_name_verbatim_suspect") else {"in_mathlib": False}
            )
            confirmed = bool(detect.get("gold_name_verbatim_suspect") and corpus.get("in_mathlib"))
            details["gold_name_verbatim"] = {"detect": detect, "corpus": corpus, "confirmed": confirmed}
            if confirmed:
                flags.append("gold_name_verbatim_confirmed")
        except Exception as exc:  # noqa: BLE001
            details["gold_name_verbatim"] = {"error": f"{type(exc).__name__}: {exc}"}
    if v33_indirect_leakage_gate is not None:
        try:
            shape = v33_indirect_leakage_gate.detect_shape(block_text)
            details["indirect_leakage_shape"] = shape
            if shape.get("indirect_leakage_suspect"):
                flags.append("indirect_leakage_shape_suspect_advisory")
        except Exception as exc:  # noqa: BLE001
            details["indirect_leakage_shape"] = {"error": f"{type(exc).__name__}: {exc}"}
    if v33_currency_mismatch_gate is not None:
        try:
            shape = v33_currency_mismatch_gate.detect_shape(block_text)
            details["currency_mismatch_shape"] = shape
            if shape.get("currency_mismatch_suspect"):
                flags.append("currency_mismatch_shape_suspect_advisory")
        except Exception as exc:  # noqa: BLE001
            details["currency_mismatch_shape"] = {"error": f"{type(exc).__name__}: {exc}"}
    confirmed = [flag for flag in flags if flag.endswith("_confirmed") or flag == "vacuity_suspected"]
    return {
        "status": "static_l3_clean_no_confirmed_laundering" if not confirmed else "static_l3_confirmed_laundering_risk",
        "flags": sorted(set(flags)),
        "confirmed_flags": sorted(set(confirmed)),
        "details": details,
    }


def _closed_file_audit(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": _rel(path), "exists": False, "audit_status": "missing"}
    text = path.read_text(errors="ignore")
    code = _code_text(text)
    decls = []
    confirmed_flags: list[str] = []
    for decl in _all_decl_blocks(path):
        audit = _static_l3_decl_audit(str(decl.pop("block_text") or ""))
        confirmed_flags.extend(audit.get("confirmed_flags") or [])
        decls.append({**decl, "static_l3_audit": audit})
    return {
        "path": _rel(path),
        "exists": True,
        "audit_schema": "leanmill-ztareproofs-closed-file-static-l3-audit-v1",
        "audit_status": (
            "static_l3_clean_pending_kernel_receipts"
            if not confirmed_flags and _raw_sorry_count(text) == 0
            else "static_l3_risk_or_open_obligation"
        ),
        "boundary": (
            "Static L3 scan only. Moat-grade PR status still requires lake build, "
            "axiom receipt, usedConstants review, and matched-negative-control governance."
        ),
        "line_count": len(text.splitlines()),
        "raw_sorry_count": _raw_sorry_count(code),
        "axiom_count": len(AXIOM_RE.findall(code)),
        "print_axioms_targets": re.findall(r"#print\s+axioms\s+([A-Za-z0-9_.]+)", code),
        "decl_count": len(decls),
        "confirmed_flags": sorted(set(confirmed_flags)),
        "decl_audits": decls,
    }


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        k = str(row.get(key) or "unknown")
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    files = sorted(root.rglob("*.lean"))
    file_summaries = [_file_summary(path) for path in files]
    obligations: list[dict[str, Any]] = []
    for path in files:
        if args.include and not re.search(args.include, str(path)):
            continue
        if args.exclude and re.search(args.exclude, str(path)):
            continue
        obligations.extend(_decl_blocks(path))
        if args.limit and len(obligations) >= args.limit:
            obligations = obligations[:args.limit]
            break
    payload = {
        "schema": "leanmill-ztareproofs-auto-prover-packet-v1",
        "root": _rel(root),
        "root_ref": {"path": _rel(root), "exists": root.exists(), "is_dir": root.is_dir()},
        "file_count": len(files),
        "raw_sorry_count": sum(int(row.get("raw_sorry_count") or 0) for row in file_summaries),
        "obligation_count": len(obligations),
        "open_obligation_boundary": (
            "declaration-level obligations only; raw sorry count may be higher when "
            "multiple sorries sit inside one declaration or outside theorem/lemma blocks"
        ),
        "family_counts": _counts(obligations, "structural_family"),
        "difficulty_counts": _counts(obligations, "difficulty_class"),
        "file_family_counts": _counts(file_summaries, "structural_family"),
        "top_files_by_sorry_count": sorted(
            [row for row in file_summaries if int(row.get("raw_sorry_count") or 0) > 0],
            key=lambda row: (-int(row.get("raw_sorry_count") or 0), str(row.get("path") or "")),
        )[:40],
        "closed_file_audits": [_closed_file_audit(Path(p)) for p in args.audit_file],
        "adapter": "scripts/public/lean/ztareproofs_auto_prover_packet.py",
        "auto_prover_command": (
            "scripts/public/lean/auto_prover_harness.py "
            f"--obligations-json {args.out} --dry-run"
        ),
        "proof_credit": "none_packet_only_no_prover_invoked",
        "artifact_boundary": {
            "write_mode": "atomic_replace",
            "canonical_truth": "ZtareProofs filesystem scan; not a Lean compile or governance receipt",
        },
        "obligations": obligations,
    }
    if args.out:
        write_json_atomic(args.out, payload)
    if args.md:
        _write_md(args.md, payload)
    return payload


def _write_md(path: str | Path, payload: dict[str, Any]) -> None:
    lines = [
        "# ZtareProofs Auto-Prover Packet",
        "",
        f"- root: `{payload.get('root')}`",
        f"- files scanned: `{payload.get('file_count')}`",
        f"- raw sorry count: `{payload.get('raw_sorry_count')}`",
        f"- open obligations: `{payload.get('obligation_count')}`",
        f"- proof_credit: `{payload.get('proof_credit')}`",
        "",
        "## Family Counts",
        "",
    ]
    for family, count in (payload.get("family_counts") or {}).items():
        lines.append(f"- `{family}`: `{count}`")
    lines.extend([
        "",
        "## Difficulty Counts",
        "",
    ])
    for difficulty, count in (payload.get("difficulty_counts") or {}).items():
        lines.append(f"- `{difficulty}`: `{count}`")
    lines.extend([
        "",
        "## Top Files By Raw Sorry Count",
        "",
        "| file | family | raw sorries | axioms |",
        "|---|---|---|---|",
    ])
    for row in payload.get("top_files_by_sorry_count", [])[:30]:
        lines.append(
            "| "
            + " | ".join([
                str(row.get("path") or ""),
                str(row.get("structural_family") or ""),
                str(row.get("raw_sorry_count") or 0),
                str(row.get("axiom_count") or 0),
            ])
            + " |"
        )
    lines.extend([
        "",
        "## Closed File Audits",
        "",
        "| file | audit status | sorries | axioms | print-axioms targets | confirmed flags |",
        "|---|---|---|---|---|---|",
    ])
    for row in payload.get("closed_file_audits", []):
        lines.append(
            "| "
            + " | ".join([
                str(row.get("path") or ""),
                str(row.get("audit_status") or ""),
                str(row.get("raw_sorry_count")),
                str(row.get("axiom_count")),
                str(len(row.get("print_axioms_targets") or [])),
                ", ".join(str(x) for x in row.get("confirmed_flags") or []),
            ])
            + " |"
        )
    lines.extend([
        "",
        "## First Obligations",
        "",
        "| name | kind | family | difficulty | score | file | line |",
        "|---|---|---|---|---|---|---|",
    ])
    for row in payload.get("obligations", [])[:80]:
        lines.append(
            "| "
            + " | ".join([
                str(row.get("name") or ""),
                str(row.get("kind") or ""),
                str(row.get("structural_family") or ""),
                str(row.get("difficulty_class") or ""),
                str(row.get("rank_score") or ""),
                str(row.get("path") or ""),
                str(row.get("line") or ""),
            ])
            + " |"
        )
    write_text_atomic(path, "\n".join(lines) + "\n")


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="ztareproofs_packet_") as td:
        root = Path(td)
        f = root / "Demo.lean"
        f.write_text(
            """import Mathlib

/- comment with fake declaration:
theorem fake_comment_decl : True := by
  sorry
  /- nested fake:
  lemma fake_nested_decl : True := by
    sorry
  -/
-/
-- another comment sorry
lemma demo : True := by
  sorry
"""
        )
        out = root / "packet.json"
        payload = build(argparse.Namespace(
            root=str(root),
            include="",
            exclude="",
            limit=0,
            out=str(out),
            md=str(root / "packet.md"),
            audit_file=[str(f)],
        ))
        assert payload["obligation_count"] == 1, payload
        assert payload["obligations"][0]["name"] == "demo", payload
        names = [str(row.get("name") or "") for row in payload["obligations"]]
        assert "fake_comment_decl" not in names, payload
        assert "fake_nested_decl" not in names, payload
        assert payload["raw_sorry_count"] == 1, payload
        assert payload["difficulty_counts"], payload
        assert payload["closed_file_audits"][0]["raw_sorry_count"] == 1, payload
    print("ztareproofs_auto_prover_packet self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--include", default="")
    ap.add_argument("--exclude", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--audit-file", action="append", default=[str(DEFAULT_AUDIT_FILE)])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--md", default=str(DEFAULT_MD))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "file_count": payload["file_count"],
        "obligation_count": payload["obligation_count"],
        "auto_prover_command": payload["auto_prover_command"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
