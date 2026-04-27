#!/usr/bin/env python3
"""Export a sanitized MLH prediction packet for the cold-agent step.

The packet contains only F1..F5 artifacts needed to author a family-level
prediction. It intentionally excludes:
  - all F6 files
  - all GT modules
  - all locked holdout artifacts

The script writes:
  1. a packet directory outside the repo (default: /tmp)
  2. a packet manifest registry entry inside the repo, so seal-time can
     verify the prediction cites a real packet via `source_packet_hash`
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKET_REGISTRY = REPO / "research_areas" / "private" / "mlh_prediction_packets"
OPEN_SLUGS = ("mlh_f1", "mlh_f2", "mlh_f3", "mlh_f4", "mlh_f5")

PROJECT_FILES = (
    "evidence.txt",
    "project_charter.md",
    "thesis.md",
    "latest_eval_results.json",
    "champion_eval_results.json",
    "latest_probability_dag.json",
)
WORKSPACE_FILES = (
    "latest_information_yield.json",
    "latest_loop_event.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_if_exists(src: Path, dst: Path, root: Path, copied: list[dict]) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.append(
        {
            "relative_path": str(dst.relative_to(root)),
            "sha256": _sha256(dst),
            "bytes": dst.stat().st_size,
        }
    )


def _packet_hash(files: list[dict]) -> str:
    canonical = json.dumps(
        sorted(files, key=lambda x: x["relative_path"]),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _readme_text() -> str:
    return (
        "# GP-135 MLH Prediction Packet\n\n"
        "Author the prediction JSON using only the artifacts in this packet.\n"
        "Do not consult the main repo, F6 project files, GT modules, or any\n"
        "prior sealed prediction. The resulting JSON must include:\n\n"
        '- `"source_packet_hash"` from `packet_manifest.json`\n'
        '- `training_substrates`\n'
        '- `holdout_substrate`\n'
        '- `invariant_statement`\n'
        '- `composition_class_prediction`\n'
        '- `composition_rule`\n'
        '- `prime_power_rule`\n'
        '- `predicted_holdout_values`\n'
        '- `predicted_at_n1`\n'
        '- `confidence`\n'
        '- `derivation_source`\n'
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Output directory for the sanitized packet. Defaults to /tmp/<timestamp>_mlh_prediction_packet",
    )
    args = ap.parse_args()

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    packet_id = now.replace(":", "-")
    out_dir = Path(args.out_dir) if args.out_dir else Path("/tmp") / f"{packet_id}_mlh_prediction_packet"
    out_dir.mkdir(parents=True, exist_ok=True)

    copied: list[dict] = []

    protocol_src = REPO / "docs" / "concepts" / "mlh_family_protocol.md"
    protocol_dst = out_dir / "docs" / "mlh_family_protocol.md"
    _copy_if_exists(protocol_src, protocol_dst, out_dir, copied)

    for slug in OPEN_SLUGS:
        project_dir = REPO / "projects" / slug
        packet_project_dir = out_dir / "projects" / slug
        for name in PROJECT_FILES:
            src = project_dir / name
            dst = packet_project_dir / name
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied.append(
                    {
                        "relative_path": str(dst.relative_to(out_dir)),
                        "sha256": _sha256(dst),
                        "bytes": dst.stat().st_size,
                    }
                )
        for name in WORKSPACE_FILES:
            src = project_dir / "workspace" / name
            dst = packet_project_dir / "workspace" / name
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied.append(
                    {
                        "relative_path": str(dst.relative_to(out_dir)),
                        "sha256": _sha256(dst),
                        "bytes": dst.stat().st_size,
                    }
                )

        rubric_src = REPO / "rubrics" / f"{slug}.json"
        rubric_dst = out_dir / "rubrics" / f"{slug}.json"
        if rubric_src.exists():
            rubric_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rubric_src, rubric_dst)
            copied.append(
                {
                    "relative_path": str(rubric_dst.relative_to(out_dir)),
                    "sha256": _sha256(rubric_dst),
                    "bytes": rubric_dst.stat().st_size,
                }
            )

    readme_path = out_dir / "README.md"
    readme_path.write_text(_readme_text(), encoding="utf-8")
    copied.append(
        {
            "relative_path": str(readme_path.relative_to(out_dir)),
            "sha256": _sha256(readme_path),
            "bytes": readme_path.stat().st_size,
        }
    )
    packet_hash = _packet_hash(copied)

    manifest = {
        "generated_at": now,
        "packet_id": packet_id,
        "packet_hash": packet_hash,
        "packet_dir": str(out_dir),
        "open_substrates": list(OPEN_SLUGS),
        "files": sorted(copied, key=lambda x: x["relative_path"]),
    }

    packet_manifest_path = out_dir / "packet_manifest.json"
    packet_manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    PACKET_REGISTRY.mkdir(parents=True, exist_ok=True)
    registry_path = PACKET_REGISTRY / f"{packet_id}_packet_manifest.json"
    registry_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"✅ exported sanitized MLH prediction packet → {out_dir}")
    print(f"   packet hash: {packet_hash}")
    print(f"   registry:    {registry_path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
