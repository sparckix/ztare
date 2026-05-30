from pathlib import Path

from src.ztare.research_director.scientific_amnesia import run_scientific_amnesia_check


def test_scientific_amnesia_accepts_repo_relative_output_path():
    output = Path("tmp/test_scientific_amnesia_relative_output.json")
    if output.exists():
        output.unlink()
    try:
        report = run_scientific_amnesia_check(
            query="owner root no overlap channel prefix",
            substrate="ns_millennium_hunt",
            code_globs=[],
            max_hits=1,
            output_path=output,
            semantic_enabled=False,
        )
        assert output.exists()
        assert report.output_path == str(output)
    finally:
        if output.exists():
            output.unlink()
