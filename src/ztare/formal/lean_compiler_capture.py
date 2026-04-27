"""GP-144 G5 translation-pair capture helper.

Emits workspace/lean_translation_pair.json for a given project so G5
translation_diff_gate can audit semantic-identity between the apparatus's
pre-translation expression (from compression_results.json) and the Lean
file written by lean_compiler / prove_from_compression.

Separated from lean_repl.py so the capture is OPT-IN — not every project
needs the pair logged; only those that will pass through G5 audit.

Invocation:
  from src.ztare.formal.lean_compiler_capture import capture_translation_pair
  capture_translation_pair(project_dir)

Safe to call repeatedly. Last capture wins. Requires:
  project_dir/workspace/compression_results.json  (pre-translation side)
  project_dir/<project_name>.lean                 (post-translation side)

Output:
  project_dir/workspace/lean_translation_pair.json
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def capture_translation_pair(project_dir: Path | str) -> dict:
    project_dir = Path(project_dir)
    comp_path = project_dir / "workspace" / "compression_results.json"
    lean_path = project_dir / f"{project_dir.name}.lean"
    out_path = project_dir / "workspace" / "lean_translation_pair.json"

    if not comp_path.is_file():
        return {"captured": False, "reason": f"compression_results.json missing at {comp_path}"}
    if not lean_path.is_file():
        return {"captured": False, "reason": f"Lean source missing at {lean_path}"}

    results = json.loads(comp_path.read_text())
    passed = [r for r in results if r.get("gates_passed")]
    if not passed:
        return {"captured": False, "reason": "No gate-passing compression entries"}
    best = min(passed, key=lambda r: r.get("bic", float("inf")))
    pre_expression = best.get("expression", "")

    post_lean = lean_path.read_text(encoding="utf-8", errors="ignore")

    pair = {
        "pre_translation_expression": pre_expression,
        "post_translation_lean_statement": post_lean,
        "capture_timestamp": datetime.now().isoformat(),
        "source_compression_entry_name": best.get("name"),
        "source_compression_entry_bic": best.get("bic"),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pair, indent=2))
    return {"captured": True, "path": str(out_path)}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 -m src.ztare.formal.lean_compiler_capture <project_dir>")
        sys.exit(1)
    r = capture_translation_pair(sys.argv[1])
    print(json.dumps(r, indent=2))
