"""LeanMill engine package.

Stable importable surface for the LeanMill subsystem (GP-225 station factory).
The operator scripts under ``scripts/public/control/leanmill_*`` and
``scripts/public/control/leansearch_*`` may import from here; this package
must NOT import from those scripts (per the boundary rules in
``scripts/README.md``).

Public submodules (the ones to import):

- ``ztare.leanmill.common`` — atomic JSON write, JSON read with safe fallback,
  subprocess wrapper, SQLite open with WAL + busy_timeout. The canonical
  helpers; new code should use these instead of re-inventing them.

Phase A (2026-05-23) — only the common helpers and an empty package shell
live here. The full migration of ``leanmill_work_queue``,
``leanmill_source_query_contract`` and ``leanmill_factory_config`` into this
package is staged below as shim re-exports, allowing scripts to switch
their imports incrementally without breaking the live mill.
"""

__all__ = ["common"]
