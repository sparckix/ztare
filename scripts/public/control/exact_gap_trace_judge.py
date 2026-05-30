#!/usr/bin/env python3
"""Strict exact-gap / falsifier judge for four-arm decider traces.

This is Meta-Darwin Test 2: on rows jointly left non-ratified by A and
B1_governed_static, did either arm produce value as a formalizable gap
or falsifier rather than a closure?

The judge is deliberately conservative. Credited outputs must contain a
Lean-looking missing lemma/theorem statement or a concrete
counterexample/falsifier shape. Timeout-only traces, generic prose, and
gate-rejected proof claims are not exact gaps.
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_CKPT = "/tmp/rung1/four_arm_decider_ckpt.jsonl"
DEFAULT_OUT = "/tmp/rung1/exact_gap_trace_judge_decider.json"
DEFAULT_ARMS = ("B1gs", "A")

GAP_WORDS = re.compile(
    r"\b(gap|missing|need(?:ed|s)?|blocked|cannot|stuck|lemma|"
    r"theorem|obstruction)\b",
    re.I,
)
SUCCESS_CLAIMS = re.compile(
    r"\b(compiles?\s+(?:successfully|cleanly)|complete proof|"
    r"verification passed|no remaining `?sorry|replaced the `?sorry)\b",
    re.I,
)
FORMAL_STMT = re.compile(
    r"(?ms)\b(?:theorem|lemma|example)\s+"
    r"[A-Za-z_][A-Za-z0-9_'.]*[^:\n]*(?:\([^)]*\)|\[[^]]*\]|\{[^}]*\}"
    r"|\s)*\s*:\s*.+?(?=(?:\n\s*(?:theorem|lemma|example)\b)|\Z)"
)
ANON_EXAMPLE = re.compile(
    r"(?ms)\bexample\s*(?:\([^)]*\)|\[[^]]*\]|\{[^}]*\}|\s)*"
    r":\s*.+?(?=(?:\n\s*(?:theorem|lemma|example)\b)|\Z)"
)
MISSING_STMT = re.compile(
    r"(?ms)\b(?:missing|needed|need|gap)\s+(?:lemma|theorem)\b"
    r"[^:\n]*:\s*.+?(?=\n\S|\Z)",
    re.I,
)
FALSIFIER_WORDS = re.compile(
    r"\b(counterexample|falsifier|contradiction|refutable|false)\b",
    re.I,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _raw_files(trace_dir: Path) -> list[Path]:
    return sorted(trace_dir.glob("round_*.raw_model_output.txt"))


def _govern_files(trace_dir: Path) -> list[Path]:
    return sorted(trace_dir.glob("round_*.govern.json"))


def _read_texts(paths: list[Path]) -> list[str]:
    out: list[str] = []
    for p in paths:
        try:
            out.append(p.read_text(errors="ignore"))
        except OSError:
            out.append("")
    return out


def _read_govern(paths: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in paths:
        try:
            out.append(json.loads(p.read_text()))
        except (OSError, json.JSONDecodeError):
            out.append({"verdict": "unreadable", "path": str(p)})
    return out


def _is_timeout_only(texts: list[str]) -> bool:
    if not texts:
        return True
    stripped = [t.strip().lower() for t in texts if t.strip()]
    return not stripped or all(t == "timeout" for t in stripped)


def _gate_rejected(governs: list[dict[str, Any]], arm_rec: dict[str, Any]) -> str | None:
    bad_verdicts = {"unverified", "axiom_smuggled", "single_lemma", "wrong_target"}
    for g in governs:
        verdict = str(g.get("verdict") or "")
        reason = str(g.get("reason") or "")
        if verdict in bad_verdicts:
            return f"governance_reject:{verdict}:{reason}".rstrip(":")
    verdict = str(arm_rec.get("verdict") or "")
    reason = str(arm_rec.get("reason") or "")
    if verdict in bad_verdicts or arm_rec.get("axiom_smuggled") or arm_rec.get("wrong_target_kind"):
        return f"arm_reject:{verdict}:{reason}".rstrip(":")
    return None


def _formal_statement(text: str) -> str | None:
    for pat in (FORMAL_STMT, MISSING_STMT):
        m = pat.search(text)
        if not m:
            continue
        stmt = " ".join(m.group(0).split())
        # A useful gap statement must have some proposition structure,
        # not merely "lemma foo:" followed by prose.
        if any(tok in stmt for tok in (":", "∀", "∃", "→", "↔", "=", "<", ">", "≤", "≥")):
            return stmt[:500]
    return None


def _falsifier_statement(text: str) -> str | None:
    if not FALSIFIER_WORDS.search(text):
        return None
    stmt = _formal_statement(text)
    if stmt:
        return stmt
    m = ANON_EXAMPLE.search(text)
    if m:
        return " ".join(m.group(0).split())[:500]
    if re.search(r"\b(?:let|take|choose|set)\b.+\b(?:contradiction|counterexample)\b",
                 text, re.I | re.S):
        return "concrete counterexample construction prose"
    return None


def classify_trace(trace_dir: Path, arm_rec: dict[str, Any]) -> dict[str, Any]:
    raws = _raw_files(trace_dir)
    governs_p = _govern_files(trace_dir)
    texts = _read_texts(raws)
    governs = _read_govern(governs_p)
    joined = "\n\n".join(texts)

    if _is_timeout_only(texts):
        cls = "no_gap"
        evidence = "timeout_only_or_no_output"
    else:
        reject = _gate_rejected(governs, arm_rec)
        formal = _formal_statement(joined)
        falsifier = _falsifier_statement(joined)
        if reject and SUCCESS_CLAIMS.search(joined):
            cls = "invalid_gap"
            evidence = reject
        elif falsifier:
            cls = "valid_falsifier"
            evidence = falsifier
        elif formal:
            cls = "exact_gap"
            evidence = formal
        elif reject:
            cls = "invalid_gap"
            evidence = reject
        elif GAP_WORDS.search(joined):
            cls = "vague_gap"
            evidence = "gap_language_without_formalizable_statement"
        else:
            cls = "no_gap"
            evidence = "non_gap_output"

    return {
        "class": cls,
        "credited": 1 if cls in {"exact_gap", "valid_falsifier"} else 0,
        "evidence": evidence,
        "trace_dir": str(trace_dir),
        "raw_files": [str(p) for p in raws],
        "govern_files": [str(p) for p in governs_p],
        "raw_count": len(raws),
        "govern_count": len(governs_p),
    }


def _joint_nonratified(row: dict[str, Any], arms: tuple[str, ...]) -> bool:
    for arm in arms:
        rec = row.get(arm) or {}
        if rec.get("ratified") or rec.get("verdict") == "closure":
            return False
    return True


def judge(ckpt: Path, arms: tuple[str, ...], only_joint_open: bool) -> dict[str, Any]:
    rows = _read_jsonl(ckpt)
    considered = [r for r in rows if (not only_joint_open or _joint_nonratified(r, arms))]
    summary = {
        arm: {
            "exact_gap": 0,
            "valid_falsifier": 0,
            "vague_gap": 0,
            "invalid_gap": 0,
            "no_gap": 0,
            "credited": 0,
        }
        for arm in arms
    }
    judged_rows: list[dict[str, Any]] = []
    for row in considered:
        arms_out: dict[str, Any] = {}
        for arm in arms:
            arm_rec = row.get(arm) or {}
            trace_dir = Path(str(arm_rec.get("trace_dir") or ""))
            c = classify_trace(trace_dir, arm_rec)
            summary[arm][c["class"]] += 1
            summary[arm]["credited"] += c["credited"]
            arms_out[arm] = c
        judged_rows.append({
            "id": row.get("id"),
            "gold": row.get("gold"),
            "arms": arms_out,
        })

    return {
        "ckpt": str(ckpt),
        "arms": list(arms),
        "only_joint_open": only_joint_open,
        "n_total_rows": len(rows),
        "n_considered_rows": len(considered),
        "credit_policy": "exact_gap or valid_falsifier only",
        "summary": summary,
        "pairwise": {
            f"{arms[-1]}_minus_{arms[0]}_credited":
                summary[arms[-1]]["credited"] - summary[arms[0]]["credited"]
        } if len(arms) >= 2 else {},
        "rows": judged_rows,
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rows = []
        for rid in ("R1", "R2", "R3"):
            rows.append({
                "id": rid,
                "gold": 1,
                "B1gs": {
                    "verdict": "open",
                    "ratified": 0,
                    "trace_dir": str(root / rid / "B1gs"),
                },
                "A": {
                    "verdict": "open",
                    "ratified": 0,
                    "trace_dir": str(root / rid / "A"),
                },
            })
        ckpt = root / "ckpt.jsonl"
        ckpt.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

        for rid in ("R1", "R2", "R3"):
            for arm in DEFAULT_ARMS:
                (root / rid / arm).mkdir(parents=True)

        (root / "R1" / "B1gs" / "round_01.raw_model_output.txt").write_text(
            "Missing lemma:\n```lean\n"
            "lemma foo_gap (n : Nat) : n = n := by\n  sorry\n```"
        )
        (root / "R1" / "A" / "round_01.raw_model_output.txt").write_text("timeout")

        (root / "R2" / "B1gs" / "round_01.raw_model_output.txt").write_text(
            "Need a lemma about continuity here."
        )
        (root / "R2" / "A" / "round_01.raw_model_output.txt").write_text(
            "Complete proof. Verification passed."
        )
        (root / "R2" / "A" / "round_01.govern.json").write_text(json.dumps({
            "verdict": "unverified",
            "reason": "injected_audit_errors",
        }))

        (root / "R3" / "B1gs" / "round_01.raw_model_output.txt").write_text(
            "Counterexample:\n```lean\n"
            "example : False := by\n  contradiction\n```"
        )
        (root / "R3" / "A" / "round_01.raw_model_output.txt").write_text(
            "No useful progress."
        )

        out = judge(ckpt, DEFAULT_ARMS, True)
        assert out["n_considered_rows"] == 3
        assert out["summary"]["B1gs"]["exact_gap"] == 1
        assert out["summary"]["B1gs"]["valid_falsifier"] == 1
        assert out["summary"]["B1gs"]["vague_gap"] == 1
        assert out["summary"]["A"]["invalid_gap"] == 1
        assert out["summary"]["A"]["no_gap"] == 2
        assert out["summary"]["B1gs"]["credited"] == 2
        assert out["summary"]["A"]["credited"] == 0
    print("exact_gap_trace_judge self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default=DEFAULT_CKPT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--arms", default=",".join(DEFAULT_ARMS))
    ap.add_argument("--all-rows", action="store_true",
                    help="judge every checkpoint row, not only jointly non-ratified rows")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    if not arms:
        ap.error("--arms must contain at least one arm")
    out = judge(Path(args.ckpt), arms, not args.all_rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "out": str(out_path),
        "n_considered_rows": out["n_considered_rows"],
        "summary": out["summary"],
        "pairwise": out["pairwise"],
    }, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
