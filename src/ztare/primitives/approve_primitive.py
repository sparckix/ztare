import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ztare.common.paths import GLOBAL_PRIMITIVES_DIR, REPO_ROOT
from ztare.workspace.compile_evidence import write_json
from ztare.primitives.draft_primitives import render_candidate_markdown


ROOT_DIR = REPO_ROOT
GLOBAL_DIR = GLOBAL_PRIMITIVES_DIR
REVIEW_DIR = GLOBAL_DIR / "review"
APPROVED_DIR = GLOBAL_DIR / "approved"
REJECTED_DIR = GLOBAL_DIR / "rejected"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote or reject a primitive candidate from the review queue.")
    parser.add_argument("--primitive-key", required=True, help="Primitive key, e.g. cooked_books.")
    parser.add_argument("--decision", required=True, choices=["approved", "rejected"])
    parser.add_argument("--note", help="Optional review note to store on the primitive card.")
    return parser.parse_args()


def load_candidate(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_items(directory: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not directory.exists():
        return items
    for path in sorted(directory.glob("*.json")):
        if path.name == "index.json":
            continue
        data = load_candidate(path)
        items.append(
            {
                "primitive_key": data.get("primitive_key", path.stem),
                "title": data.get("title", ""),
                "status": data.get("status", ""),
                "confidence": data.get("confidence", ""),
                "path": str(path.relative_to(ROOT_DIR)),
            }
        )
    return items


def rebuild_indexes() -> None:
    write_json(REVIEW_DIR / "index.json", {"items": list_items(REVIEW_DIR)})
    write_json(APPROVED_DIR / "index.json", {"items": list_items(APPROVED_DIR)})
    write_json(REJECTED_DIR / "index.json", {"items": list_items(REJECTED_DIR)})


def main() -> int:
    args = parse_args()

    json_src = REVIEW_DIR / f"{args.primitive_key}.json"
    md_src = REVIEW_DIR / f"{args.primitive_key}.md"
    if not json_src.exists():
        raise SystemExit(f"Candidate not found in review/: {json_src}")

    candidate = load_candidate(json_src)
    candidate["status"] = args.decision
    candidate["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    if args.note:
        candidate["review_note"] = args.note

    if args.decision == "approved":
        target_dir = APPROVED_DIR
    else:
        target_dir = REJECTED_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    json_dst = target_dir / json_src.name
    md_dst = target_dir / md_src.name
    write_json(json_dst, candidate)
    md_dst.write_text(render_candidate_markdown(candidate), encoding="utf-8")

    json_src.unlink()
    if md_src.exists():
        md_src.unlink()

    rebuild_indexes()

    print(f"{args.decision.title()}: {json_dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
