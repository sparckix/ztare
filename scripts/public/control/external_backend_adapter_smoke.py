#!/usr/bin/env python3
"""One-row external-backend adapter smoke for real Mathlib module rows.

This tests whether Hammer/Duper/Auto-style tactics are runnable against
the target sorry proofState extracted from the real source file. It is
not a benchmark and not a solver loop. It records a result row suitable
for lean_action_routing_dataset.py --external-results.

Important: prior deterministic routing showed that naively importing
Hammer/Duper/Auto into module source rows can break row context. This
smoke does not pretend otherwise; it records "adapter_unavailable" or
"open_failed" explicitly if the backend cannot be applied cleanly.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

FROZEN = "/tmp/rung1/four_arm_frozen_corpus.json"
DEFAULT_OUT = "/tmp/rung1/external_backend_adapter_smoke.jsonl"
DEFAULT_TOOLS = ["hammer", "duper", "aesop", "exact?", "simp_all"]
TOOL_PRELUDE = ("import Mathlib\nimport Hammer\nimport Duper\n"
                "import Auto\nopen scoped ENNReal NNReal BigOperators")
SYNTHETIC_BODY = """module

public import Mathlib
{tool_imports}

theorem ext_backend_synth : (1 : Nat) + 1 = 2 := by
  sorry
"""
MODULE_UNSAFE_TOKENS = ("hammer", "duper", "auto", "sorry")
SUGGESTION_PROPOSERS = [
    "hammer",
    "hammer {disableAesop := true, preprocessing := no_preprocessing, solverTimeout := 30}",
    "hammer {disableAesop := true, preprocessing := simp_all, solverTimeout := 30}",
    "hammer {solverTimeout := 30, autoPremises := 64, aesopPremises := 64}",
    "duper?",
]


def die(msg: str) -> None:
    print(f"FAIL-LOUD: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _load_row(corpus: Path, row_id: str) -> dict[str, Any]:
    data = json.loads(corpus.read_text())
    rows = data["rows"] if isinstance(data, dict) else data
    for row in rows:
        if row.get("id") == row_id:
            return row
    die(f"row not found in {corpus}: {row_id}")


def _target_state(L: Any, row: dict[str, Any], open_timeout: int) -> dict[str, Any]:
    of = L.open_file(row["sorried_file"], timeout=open_timeout)
    if not of.get("ok"):
        return {"ok": False, "reason": "open_failed",
                "errors": of.get("errors") or of.get("err") or ""}
    tl = row["target_line"]
    tgt = next((s for s in of.get("sorries", [])
                if s.get("line") and abs(s["line"] - tl) <= 3), None)
    if not tgt or tgt.get("proofState") is None:
        return {"ok": False, "reason": "target_sorry_not_found",
                "errors": of.get("errors") or []}
    return {"ok": True, "ps": tgt["proofState"], "goal": tgt.get("goal", "")}


def _replace_target_sorry(src: str, target_line: int, path: list[str]) -> str:
    # Reuse the proven replay helper from the deterministic ablation.
    import deterministic_tool_router_ablation as dtr
    return dtr._replace_target_sorry(src, target_line, path)


def _externalized_source(src: str, target_line: int, path: list[str]) -> str:
    """Make a non-module proving copy for external proposers.

    The authoritative replay still happens in the original module file.
    This copy exists only so non-module tactics can emit "Try this"
    suggestions over approximately the same local context.
    """
    replaced = _replace_target_sorry(src, target_line, path)
    lines = []
    inserted = False
    for line in replaced.splitlines():
        stripped = line.strip()
        if stripped == "module":
            continue
        if stripped.startswith("public import "):
            line = line.replace("public import ", "import ", 1)
            lines.append(line)
            if not inserted:
                lines.extend(["import Hammer", "import Duper", "import Auto"])
                inserted = True
            continue
        line = line.replace("@[expose] public section", "@[expose] section")
        lines.append(line)
    if not inserted:
        lines = ["import Mathlib", "import Hammer", "import Duper",
                 "import Auto"] + lines
    return "\n".join(lines) + "\n"


def _govern_candidate(L: Any, row: dict[str, Any], path: list[str],
                      timeout: int) -> dict[str, Any]:
    import authoritative_axioms as _AX
    src = Path(row["sorried_file"]).read_text(errors="ignore")
    candidate = _replace_target_sorry(src, row["target_line"], path)
    return _AX.govern(L, candidate, row["target_line"], row["target_name"],
                      timeout, persist=True)


def _extract_try_this(output: str) -> list[str]:
    suggestions: list[str] = []
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("try this"):
            buf: list[str] = []
            for nxt in lines[i + 1:]:
                s = nxt.strip()
                if re.search(r"\.lean:\d+:\d+:", s) or s.startswith("error:"):
                    break
                if not s:
                    if buf:
                        break
                    continue
                s = re.sub(r"^\[[^\]]+\]\s*", "", s).strip()
                if s:
                    buf.append(s)
            if buf:
                suggestions.append("\n".join(buf))
    # Stable de-duplication.
    out: list[str] = []
    seen: set[str] = set()
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _module_safe_suggestion(suggestion: str) -> bool:
    low = suggestion.lower()
    return not any(tok in low for tok in MODULE_UNSAFE_TOKENS)


def _direct_external_proposer(path: Path, timeout: int) -> dict[str, Any]:
    import coherent_rung1 as cr

    try:
        p = subprocess.run(
            ["lake", "env", "lean", str(path)],
            cwd=str(cr.SB),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        output = (p.stdout or "") + ("\n" if p.stdout and p.stderr else "") + (p.stderr or "")
        return {
            "phase": "external_proposer",
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "output": output.strip()[:4000],
            "suggestions": _extract_try_this(output),
        }
    except Exception as e:
        return {"phase": "external_proposer", "ok": False, "err": repr(e),
                "suggestions": []}


def run_suggestion_adapter(row: dict[str, Any], out_path: Path,
                           proposer_timeout: int,
                           govern_timeout: int) -> dict[str, Any]:
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    os.environ["ZTARE_GATE_RUN_ID"] = "external_backend_suggestion_smoke"
    os.environ["ZTARE_GATE_SOURCE"] = "external_backend_adapter_smoke"
    src = Path(row["sorried_file"]).read_text(errors="ignore")
    td = Path(tempfile.mkdtemp(prefix="ext_backend_suggest_"))
    events: list[dict[str, Any]] = []
    gate: dict[str, Any] | None = None
    winning: str | None = None
    status = "open"
    for i, proposer in enumerate(SUGGESTION_PROPOSERS):
        p = td / f"{row['id']}_p{i}.lean"
        p.write_text(_externalized_source(src, row["target_line"], [proposer]))
        ev = _direct_external_proposer(p, proposer_timeout)
        ev["proposer"] = proposer
        ev["source"] = str(p)
        events.append(ev)
        for sug in ev.get("suggestions") or []:
            safe = _module_safe_suggestion(sug)
            events.append({"phase": "suggestion_filter", "proposer": proposer,
                           "suggestion": sug, "module_safe": safe})
            if not safe:
                continue
            L = PersistentLean(cr.SB, prelude="import Mathlib", import_timeout=600)
            L.start_tactic_proof("theorem _w : True := by sorry", 180)
            try:
                gate = _govern_candidate(L, row, [sug], govern_timeout)
            finally:
                L.close()
            events.append({"phase": "authoritative_replay",
                           "suggestion": sug,
                           "verdict": gate.get("verdict"),
                           "reason": gate.get("reason")})
            if gate.get("verdict") == "closure":
                status = "closure"
                winning = sug
                break
        if status == "closure":
            break
    if status != "closure" and any((ev.get("suggestions") for ev in events
                                    if ev.get("phase") == "external_proposer")):
        status = "suggestions_not_ratified"
    rec = {
        "row_id": row["id"],
        "action": "use_external_backend_suggestion_adapter",
        "status": status,
        "ratified": 1 if status == "closure" else 0,
        "winning_suggestion": winning,
        "events": events,
        "gate": gate,
        "target_name": row.get("target_name"),
        "source": str(row.get("sorried_file")),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    print(json.dumps(rec, indent=1, sort_keys=True))
    return rec


def synthetic_suggestion_control(out_path: Path, proposer_timeout: int,
                                 govern_timeout: int) -> dict[str, Any]:
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    os.environ["ZTARE_GATE_RUN_ID"] = "external_backend_suggestion_synth"
    os.environ["ZTARE_GATE_SOURCE"] = "external_backend_adapter_smoke"
    td = Path(tempfile.mkdtemp(prefix="ext_backend_suggest_synth_"))
    module_src = """module

public import Mathlib

theorem ext_backend_suggestion_synth : (1 : Nat) + 1 = 2 := by
  sorry
"""
    module_file = td / "module_target.lean"
    module_file.write_text(module_src)
    row = {
        "id": "synthetic_suggestion_module",
        "sorried_file": str(module_file),
        "target_line": 6,
        "target_name": "ext_backend_suggestion_synth",
    }
    external_file = td / "external_hammer.lean"
    external_file.write_text(_externalized_source(module_src, 6, ["hammer"]))
    ev = _direct_external_proposer(external_file, proposer_timeout)
    ev["proposer"] = "hammer"
    ev["source"] = str(external_file)
    events: list[dict[str, Any]] = [ev]
    gate: dict[str, Any] | None = None
    winning: str | None = None
    status = "suggestions_not_ratified"
    for sug in ev.get("suggestions") or []:
        safe = _module_safe_suggestion(sug)
        events.append({"phase": "suggestion_filter", "proposer": "hammer",
                       "suggestion": sug, "module_safe": safe})
        if not safe:
            continue
        L = PersistentLean(cr.SB, prelude="import Mathlib", import_timeout=600)
        L.start_tactic_proof("theorem _w : True := by sorry", 180)
        try:
            gate = _govern_candidate(L, row, [sug], govern_timeout)
        finally:
            L.close()
        events.append({"phase": "authoritative_replay",
                       "suggestion": sug,
                       "verdict": gate.get("verdict"),
                       "reason": gate.get("reason")})
        if gate.get("verdict") == "closure":
            status = "mechanism_confirmed"
            winning = sug
            break
    rec = {
        "row_id": "synthetic_suggestion_module",
        "action": "use_external_backend_suggestion_adapter",
        "status": status,
        "ratified": 1 if status == "mechanism_confirmed" else 0,
        "winning_suggestion": winning,
        "events": events,
        "gate": gate,
        "source": str(module_file),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    print(json.dumps(rec, indent=1, sort_keys=True))
    return rec


def _direct_lean_check(path: Path, timeout: int) -> dict[str, Any]:
    import coherent_rung1 as cr

    try:
        p = subprocess.run(
            ["lake", "env", "lean", str(path)],
            cwd=str(cr.SB),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "phase": "direct_lean",
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout.strip()[:1000],
            "stderr": p.stderr.strip()[:1000],
        }
    except Exception as e:
        return {"phase": "direct_lean", "ok": False, "err": repr(e)}


def run(row: dict[str, Any], tools: list[str], out_path: Path,
        open_timeout: int, step_timeout: int, govern_timeout: int) -> dict[str, Any]:
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    os.environ["ZTARE_GATE_RUN_ID"] = "external_backend_adapter_smoke"
    os.environ["ZTARE_GATE_SOURCE"] = "external_backend_adapter_smoke"
    L = PersistentLean(cr.SB, prelude=TOOL_PRELUDE, import_timeout=600)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    try:
        st = _target_state(L, row, open_timeout)
        events: list[dict[str, Any]] = []
        gate: dict[str, Any] | None = None
        status = "open"
        path: list[str] = []
        if not st.get("ok"):
            status = st.get("reason", "open_failed")
            events.append({
                "phase": "open_file",
                "ok": False,
                "err": str(st.get("errors") or "")[:1000],
            })
        else:
            ps = st["ps"]
            for tool in tools:
                r = L.step(ps, tool, timeout=step_timeout)
                ev = {"tool": tool, "ok": bool(r.get("ok")),
                      "closed": bool(r.get("closed")),
                      "err": (r.get("err") or "")[:240],
                      "n_goals": len(r.get("goals") or [])}
                events.append(ev)
                if not r.get("ok"):
                    if "unknown tactic" in ev["err"].lower() or "unknown identifier" in ev["err"].lower():
                        status = "adapter_unavailable"
                    continue
                if r.get("closed"):
                    path = [tool]
                    gate = _govern_candidate(L, row, path, govern_timeout)
                    status = gate.get("verdict") or "candidate_closed"
                    break
            if status == "open" and events and all(not e["ok"] for e in events):
                status = "adapter_unavailable"
        rec = {
            "row_id": row["id"],
            "action": "use_external_backend_adapter",
            "status": status,
            "ratified": 1 if status == "closure" else 0,
            "path": path,
            "tools": tools,
            "events": events,
            "gate": gate,
            "target_name": row.get("target_name"),
            "source": str(row.get("sorried_file")),
        }
    finally:
        L.close()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    print(json.dumps(rec, indent=1, sort_keys=True))
    return rec


def synthetic_positive_control(out_path: Path, open_timeout: int,
                               step_timeout: int, govern_timeout: int) -> dict[str, Any]:
    """Synthetic module-row control. It checks the suspected mechanism:
    proof states from open_file see the FILE imports, not the REPL
    prelude. The no-tool-import file should make hammer unavailable;
    the tool-import file should at least recognize/invoke hammer."""
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    os.environ["ZTARE_GATE_RUN_ID"] = "external_backend_adapter_synth"
    os.environ["ZTARE_GATE_SOURCE"] = "external_backend_adapter_smoke"
    td = Path(tempfile.mkdtemp(prefix="ext_backend_synth_"))
    variants = {
        "mathlib_only": "",
        "with_tool_imports": "public import Hammer\npublic import Duper\npublic import Auto",
    }
    files: dict[str, Path] = {}
    for name, imports in variants.items():
        p = td / f"{name}.lean"
        p.write_text(SYNTHETIC_BODY.format(tool_imports=imports))
        files[name] = p
    L = PersistentLean(cr.SB, prelude=TOOL_PRELUDE, import_timeout=600)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    results: dict[str, Any] = {}
    try:
        for name, p in files.items():
            row = {"id": f"synthetic_{name}", "sorried_file": str(p),
                   "target_line": 6 if name == "mathlib_only" else 9,
                   "target_name": "ext_backend_synth"}
            st = _target_state(L, row, open_timeout)
            events: list[dict[str, Any]] = []
            gate: dict[str, Any] | None = None
            status = st.get("reason", "open") if not st.get("ok") else "open"
            if not st.get("ok"):
                events.append({
                    "phase": "open_file",
                    "ok": False,
                    "err": str(st.get("errors") or "")[:1000],
                })
                events.append(_direct_lean_check(p, min(open_timeout, 240)))
            else:
                for tool in ("hammer", "duper", "aesop", "exact?", "simp_all"):
                    r = L.step(st["ps"], tool, timeout=step_timeout)
                    ev = {"tool": tool, "ok": bool(r.get("ok")),
                          "closed": bool(r.get("closed")),
                          "err": (r.get("err") or "")[:240],
                          "n_goals": len(r.get("goals") or [])}
                    events.append(ev)
                    if r.get("closed"):
                        gate = _govern_candidate(L, row, [tool], govern_timeout)
                        status = gate.get("verdict") or "candidate_closed"
                        break
                if status == "open" and events and all(not e["ok"] for e in events):
                    status = "adapter_unavailable"
            results[name] = {"status": status, "events": events, "gate": gate,
                             "source": str(p)}
    finally:
        L.close()
    no_import_hammer_unknown = any(
        e.get("tool") == "hammer" and "unknown tactic" in e.get("err", "").lower()
        for e in results.get("mathlib_only", {}).get("events", []))
    with_import_hammer_invoked = any(
        e.get("tool") == "hammer" and "unknown tactic" not in e.get("err", "").lower()
        for e in results.get("with_tool_imports", {}).get("events", []))
    rec = {
        "row_id": "synthetic_module_positive_control",
        "action": "use_external_backend_adapter",
        "status": ("mechanism_confirmed" if no_import_hammer_unknown and with_import_hammer_invoked
                   else "mechanism_not_confirmed"),
        "ratified": 0,
        "no_import_hammer_unknown": no_import_hammer_unknown,
        "with_import_hammer_invoked": with_import_hammer_invoked,
        "variants": results,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    print(json.dumps(rec, indent=1, sort_keys=True))
    return rec


def self_test() -> int:
    class MockL:
        def open_file(self, path, timeout=60):
            return {"ok": True, "errors": [], "sorries": [{
                "line": 3, "proofState": 1, "goal": "⊢ True"}]}

        def step(self, ps, tool, timeout=60):
            return {"ok": tool == "hammer", "closed": tool == "hammer",
                    "goals": [], "err": "" if tool == "hammer" else "unknown tactic"}

    row = {"id": "r", "sorried_file": "x.lean", "target_line": 3,
           "target_name": "t"}
    st = _target_state(MockL(), row, 1)
    assert st["ok"] and st["ps"] == 1
    assert re.match(r"^[A-Za-z0-9_]+$", "external_backend_adapter_smoke")
    txt = "Try this:\n\n  [apply]   simp_all only [Nat.reduceAdd]\n"
    assert _extract_try_this(txt) == ["simp_all only [Nat.reduceAdd]"]
    assert _module_safe_suggestion("simp_all only [Nat.reduceAdd]")
    assert not _module_safe_suggestion("duper [] {portfolioInstance := 1}")
    print("external_backend_adapter_smoke self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=FROZEN)
    ap.add_argument("--row-id", default="MCB_001_convolution_integrand_bound_righ")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--tools", default=",".join(DEFAULT_TOOLS))
    ap.add_argument("--open-timeout", type=int, default=600)
    ap.add_argument("--step-timeout", type=int, default=30)
    ap.add_argument("--govern-timeout", type=int, default=220)
    ap.add_argument("--synthetic-positive-control", action="store_true")
    ap.add_argument("--synthetic-suggestion-control", action="store_true")
    ap.add_argument("--suggestion-adapter", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.synthetic_positive_control:
        synthetic_positive_control(Path(args.out), args.open_timeout,
                                   args.step_timeout, args.govern_timeout)
        return 0
    if args.synthetic_suggestion_control:
        synthetic_suggestion_control(Path(args.out), args.open_timeout,
                                     args.govern_timeout)
        return 0
    tools = [t.strip() for t in args.tools.split(",") if t.strip()]
    row = _load_row(Path(args.corpus), args.row_id)
    if args.suggestion_adapter:
        run_suggestion_adapter(row, Path(args.out), args.open_timeout,
                               args.govern_timeout)
        return 0
    run(row, tools, Path(args.out), args.open_timeout,
        args.step_timeout, args.govern_timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
