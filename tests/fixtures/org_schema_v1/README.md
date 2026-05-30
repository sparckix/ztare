# org_schema_v1, frozen snapshot

This fixture captures the v1 org/ schema as it existed on 2026-04-23.
It is NOT the live org, do not edit these files to reflect operational
changes. It is the load-test for schema evolution: when the loader
gains a v2 feature, this fixture must still parse without error (or
the loader is a breaking change and must be flagged as such).

If a field is added in v2:
- keep this fixture as v1 baseline (do not update it)
- add a separate `org_schema_v2/` fixture alongside
- extend `tests/test_org_schema_compat.py` with a v2 case

If a field is renamed or removed in v2:
- the loader must accept both old and new names for at least one
  release cycle, or this fixture fails (which is the intended alarm)
