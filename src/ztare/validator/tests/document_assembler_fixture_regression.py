from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from ztare.validator.utilities.document_assembler import (
    assemble_document_from_manifest,
    load_document_manifest,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def run_document_assembler_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="document_assembler_fixture_") as tmp:
        tmp_path = Path(tmp)
        frag1 = tmp_path / "01_intro.md"
        frag2 = tmp_path / "02_body.md"
        output = tmp_path / "full.md"
        manifest_path = tmp_path / "document_manifest.json"

        frag1.write_text("## Intro  \r\nLine one.\r\n")
        frag2.write_text("## Body\nLine two.\n")
        _write_json(
            manifest_path,
            {
                "document_id": "demo_document",
                "output_path": str(output),
                "fragments": [str(frag1), str(frag2)],
            },
        )

        manifest = load_document_manifest(manifest_path)
        summary = assemble_document_from_manifest(manifest)
        assembled = output.read_text()
        results.append(
            {
                "case_id": "ordered_fragments_are_concatenated_with_normalized_newlines",
                "passed": assembled == "## Intro\nLine one.\n\n## Body\nLine two.\n",
            }
        )
        results.append(
            {
                "case_id": "summary_reports_output_and_fragment_count",
                "passed": summary["output_path"] == str(output)
                and summary["fragments_included"] == [str(frag1), str(frag2)],
            }
        )

        optional_manifest_path = tmp_path / "optional_manifest.json"
        optional_output = tmp_path / "optional_full.md"
        _write_json(
            optional_manifest_path,
            {
                "document_id": "demo_optional",
                "output_path": str(optional_output),
                "fragments": [
                    str(frag1),
                    {"path": str(tmp_path / "03_missing.md"), "required": False},
                    str(frag2),
                ],
            },
        )
        optional_manifest = load_document_manifest(optional_manifest_path)
        optional_summary = assemble_document_from_manifest(optional_manifest)
        results.append(
            {
                "case_id": "optional_missing_fragments_are_skipped",
                "passed": optional_summary["missing_optional_fragments"]
                == [str(tmp_path / "03_missing.md")]
                and optional_output.read_text() == "## Intro\nLine one.\n\n## Body\nLine two.\n",
            }
        )

    all_passed = all(result["passed"] for result in results)
    return {
        "suite": "document_assembler_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run generic document assembler fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_document_assembler_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Document assembler fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
