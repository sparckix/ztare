from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def _python_files(root: Path) -> list[Path]:
    return [
        path for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def test_leanmill_does_not_import_pde_facade() -> None:
    offenders = []
    for path in _python_files(REPO / "src" / "ztare" / "leanmill"):
        text = path.read_text(encoding="utf-8")
        if "ztare.pde" in text:
            offenders.append(str(path.relative_to(REPO)))

    assert offenders == []


def test_pde_facade_does_not_import_ns_app_profiles() -> None:
    offenders = []
    for path in _python_files(REPO / "src" / "ztare" / "pde"):
        text = path.read_text(encoding="utf-8")
        if "ns_millennium_hunt" in text:
            offenders.append(str(path.relative_to(REPO)))

    assert offenders == []


def test_pde_applicability_cards_do_not_import_leanmill_lemma_bank() -> None:
    path = REPO / "src" / "ztare" / "pde" / "applicability_cards.py"
    text = path.read_text(encoding="utf-8")

    assert "ztare.leanmill" not in text
    assert "semantic_premise_shelf" not in text
    assert "family_lemma_library" not in text


def test_pde_formal_surface_status_does_not_import_leanmill() -> None:
    path = REPO / "src" / "ztare" / "pde" / "formal_surface_status.py"
    text = path.read_text(encoding="utf-8")

    assert "ztare.leanmill" not in text
    assert "semantic_premise_shelf" not in text
    assert "family_lemma_library" not in text
