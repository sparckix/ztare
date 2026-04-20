"""write_seal.py — write sandbox_seal.json attestation artifact.

Called by `make seal` after sentinel + integration tests pass.
Kept as a module to avoid shell quoting issues with inline -c Python.

Usage:
    python -m src.ztare.scaffold.write_seal PROJECT_BARE PROJ_DIR RUBRIC_PATH SEAL_PATH
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path


def sha(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except FileNotFoundError:
        return None


def main():
    if len(sys.argv) != 5:
        print("Usage: write_seal PROJECT_BARE PROJ_DIR RUBRIC_PATH SEAL_PATH", file=sys.stderr)
        sys.exit(1)

    project_bare, proj_dir_str, rubric_path_str, seal_path_str = sys.argv[1:]
    proj = Path(proj_dir_str)
    rubric = Path(rubric_path_str)
    seal_path = Path(seal_path_str)

    seal = {
        "project": project_bare,
        "rubric": str(rubric),
        "sealed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sentinel": "passed",
        "integration": "passed",
        "artifact_hashes": {
            f: sha(proj / f)
            for f in ["evidence.txt", "evidence_holdout.txt", "gate_harness.py",
                      "project_charter.md", "thesis.md"]
            if (proj / f).exists()
        },
        "rubric_hash": sha(rubric),
        "attestation": (
            "All Division B artifacts scanned by sentinel. "
            "Integration tests pass. Sandbox is sealed."
        ),
    }

    seal_path.write_text(json.dumps(seal, indent=2), encoding="utf-8")
    print(f"  ✅ Seal written to {seal_path}")


if __name__ == "__main__":
    main()
