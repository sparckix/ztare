from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DocumentAssemblyFragment:
    path: str
    required: bool = True


@dataclass(frozen=True)
class DocumentAssemblyManifest:
    document_id: str
    output_path: str
    fragments: tuple[DocumentAssemblyFragment, ...]


def manifest_from_dict(payload: dict[str, Any]) -> DocumentAssemblyManifest:
    fragments: list[DocumentAssemblyFragment] = []
    for item in payload.get("fragments", ()):
        if isinstance(item, str):
            fragments.append(DocumentAssemblyFragment(path=item, required=True))
        else:
            fragments.append(
                DocumentAssemblyFragment(
                    path=str(item["path"]),
                    required=bool(item.get("required", True)),
                )
            )
    return DocumentAssemblyManifest(
        document_id=str(payload["document_id"]),
        output_path=str(payload["output_path"]),
        fragments=tuple(fragments),
    )


def load_document_manifest(path: Path) -> DocumentAssemblyManifest:
    return manifest_from_dict(json.loads(path.read_text()))


def _normalize_fragment_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def assemble_document_from_manifest(manifest: DocumentAssemblyManifest) -> dict[str, object]:
    chunks: list[str] = []
    included_paths: list[str] = []
    missing_optional_paths: list[str] = []

    for fragment in manifest.fragments:
        path = Path(fragment.path)
        if not path.exists():
            if fragment.required:
                raise FileNotFoundError(f"Required fragment missing: {fragment.path}")
            missing_optional_paths.append(fragment.path)
            continue
        chunks.append(_normalize_fragment_text(path.read_text()))
        included_paths.append(fragment.path)

    output_path = Path(manifest.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    assembled = "\n\n".join(chunk for chunk in chunks if chunk).rstrip() + "\n"
    output_path.write_text(assembled)
    return {
        "document_id": manifest.document_id,
        "output_path": str(output_path),
        "fragments_included": included_paths,
        "missing_optional_fragments": missing_optional_paths,
        "output_chars": len(assembled),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble an ordered document from markdown fragments.")
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    manifest = load_document_manifest(args.manifest_path)
    summary = assemble_document_from_manifest(manifest)
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Document assembler: output=`{summary['output_path']}` "
        f"fragments={len(summary['fragments_included'])} "
        f"missing_optional={len(summary['missing_optional_fragments'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
