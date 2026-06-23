from __future__ import annotations

import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def _load_module():
    path = REPO / "scripts" / "public" / "control" / "evidence_packet_check.py"
    spec = importlib.util.spec_from_file_location("evidence_packet_check", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_claim_card_checker_accepts_required_public_fields(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    linked = tmp_path / "source.md"
    linked.write_text("# Source\n", encoding="utf-8")
    cards = tmp_path / "claim_cards.md"
    cards.write_text(
        """# Claim Cards

## Card 1: Demo

**Claim.** A scoped claim.

**Evidence level.** L3 as claim-governance evidence.

**Primary sources.**

- [Source](source.md)

**Runnable anchor.**

```bash
echo ok
```

**Non-claims.** Not externally replicated.

**Next falsifier.** Add a controlled comparison.
""",
        encoding="utf-8",
    )

    report = module._check_claim_cards(cards)

    assert report["ok"] is True
    assert report["card_count"] == 1
    assert report["results"][0]["local_links"] == 1


def test_claim_card_checker_rejects_missing_fields_and_bad_evidence_level(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    cards = tmp_path / "claim_cards.md"
    cards.write_text(
        """# Claim Cards

## Card 1: Demo

**Claim.** A scoped claim.

**Evidence level.** strong but untyped.

**Primary sources.**

- no linked source

**Non-claims.** Not externally replicated.
""",
        encoding="utf-8",
    )

    report = module._check_claim_cards(cards)
    row = report["results"][0]

    assert report["ok"] is False
    assert row["ok"] is False
    assert "Runnable anchor" in row["missing_fields"]
    assert "Next falsifier" in row["missing_fields"]
    assert "Evidence level value" in row["missing_fields"]


def test_claim_card_checker_rejects_numbering_gaps(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    linked = tmp_path / "source.md"
    linked.write_text("# Source\n", encoding="utf-8")
    cards = tmp_path / "claim_cards.md"
    cards.write_text(
        """# Claim Cards

## Card 2: Demo

**Claim.** A scoped claim.

**Evidence level.** L3 as claim-governance evidence.

**Primary sources.**

- [Source](source.md)

**Runnable anchor.**

```bash
echo ok
```

**Non-claims.** Not externally replicated.

**Next falsifier.** Add a controlled comparison.
""",
        encoding="utf-8",
    )

    report = module._check_claim_cards(cards)

    assert report["ok"] is False
    assert report["sequence_ok"] is False
    assert report["actual_sequence"] == [2]
    assert report["expected_sequence"] == [1]


def test_packet_readme_checker_rejects_stale_packet_list(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    packet_dir = tmp_path / "docs" / "evidence_atlas" / "packets"
    packet_dir.mkdir(parents=True)
    packet_a = packet_dir / "a.md"
    packet_b = packet_dir / "b.md"
    packet_a.write_text("# A\n", encoding="utf-8")
    packet_b.write_text("# B\n", encoding="utf-8")
    readme = packet_dir / "README.md"
    readme.write_text(
        """# Evidence Packets

## Packets

- [A](a.md)
""",
        encoding="utf-8",
    )

    report = module._check_packet_readme([packet_a, packet_b], readme)

    assert report["ok"] is False
    assert report["missing_packets"] == ["b.md"]
    assert report["extra_packets"] == []
    assert report["duplicate_packets"] == []


def test_packet_checker_rejects_missing_evidence_level_value(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "REPO", tmp_path)
    packet = tmp_path / "packet.md"
    packet.write_text(
        """# Packet

## Scoped Claim

Claim.

## Evidence Level

High confidence.

## Primary Sources

- source

## Runnable Anchor

```bash
echo ok
```

## Evidence Summary

Summary.

## Non-Claims

None.

## Missing Upgrade

Upgrade.
""",
        encoding="utf-8",
    )

    report = module._check_packet(packet)

    assert report["ok"] is False
    assert "Evidence Level value" in report["missing_sections"]
