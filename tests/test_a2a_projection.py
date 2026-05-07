from __future__ import annotations

from pathlib import Path

from src.ztare.orchestration import a2a_projection as a2a


def test_a2a_agent_card_projection_from_role_yaml(tmp_path: Path, monkeypatch):
    roles = tmp_path / "roles"
    channels = tmp_path / "channels"
    cards = tmp_path / "cards"
    roles.mkdir()
    (roles / "research_director.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "role_id: research_director",
                "description: Test director",
                "authorized_paths:",
                "  - research_areas/",
                "forbidden_paths:",
                "  - src/",
                "delegates_to:",
                "  - worker.explore_agent",
                "escalates_to:",
                "  - role.principal",
                "mandate_path: org/mandates/research_director_mandate.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(a2a, "ROLES_DIR", roles)
    monkeypatch.setattr(a2a, "CHANNELS_DIR", channels)
    monkeypatch.setattr(a2a, "CARD_DIR", cards)

    card = a2a.build_agent_card("research_director")
    assert card.role_id == "research_director"
    assert card.inbox_path.endswith("org/channels/research_director/inbox")
    assert "research_areas/" in card.authorized_paths
    assert "src/" in card.forbidden_paths
    assert "inform" in card.message_kinds
    assert "not execution authority" in card.authority_note

    paths = a2a.write_agent_cards()
    assert len(paths) == 1
    assert paths[0].exists()
