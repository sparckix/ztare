from __future__ import annotations

import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def test_makefile_python_script_paths_exist() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    refs = sorted(set(re.findall(r"(?<![A-Za-z0-9_./-])((?:scripts|projects)/[A-Za-z0-9_./-]+\.py)", makefile)))
    missing = [ref for ref in refs if not (REPO / ref).is_file()]
    assert missing == []
