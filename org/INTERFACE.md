# org/ — Public Interface for ZTARE Consumers

**Version**: see `org/VERSION` (semver, bumped on contract changes).

This document declares the contract between `org/` (governance + agentic
patterns + role definitions) and downstream consumers (currently ZTARE,
in the future: any substrate that wants Director-style orchestration).

## What lives in `org/`

| Path | Purpose | Stable? |
|---|---|---|
| `org/patterns/*.md` | Orchestration pattern catalog (SKILL.md format) | Stable contract |
| `org/anti-patterns/*.md` | Anti-pattern catalog — recurring failure modes paired with detection patterns (SKILL.md format) | Stable contract |
| `org/anti-patterns/INDEX.md` | Anti-pattern entries + cross-reference map (anti-pattern ↔ detection pattern) | Stable contract |
| `org/menu/orchestration_menu.yaml` | Problem-class → pattern-chain menu (hierarchical) | Stable contract |
| `org/runtime/pattern_catalog.yaml` | Generated index from frontmatter | Generated, do not hand-edit |
| `org/mandates/*.md` | Role mandates (Research Director, Manager, etc.) | Stable contract |
| `org/roles/*.yaml` | Role schemas | Stable contract |
| `org/runtime/process_catalog_seed.yaml` | Process registry | Stable contract |
| `org/runtime/substrate_portfolio.yaml` | Substrate registry | Stable contract |
| `org/directives/*.json` | Time-series directive log | Append-only |
| `org/key_results/*.yaml` | Key results with recurrence | Stable contract |
| `org/gates/`, `org/channels/`, etc. | Misc M-form runtime artifacts | Stable contract |

## What ZTARE reads from `org/`

ZTARE's `src/ztare/` modules read FROM `org/` but never write TO it
(except via specific CLI entry points that emit to `org/directives/`).

**Authorized read paths**:
- `org/bootstrap_manifest.yaml` — bootstrap chain
- `org/mandates/*.md` — mandate text loaded by Director agents at runtime
- `org/menu/orchestration_menu.yaml` — pattern-chain recommendations
- `org/patterns/*.md` — individual pattern files (SKILL.md format)
- `org/anti-patterns/*.md` — anti-pattern catalog (SKILL.md format); run BEFORE deployment as cheap precondition, parallel to pattern detection
- `org/runtime/pattern_catalog.yaml` — generated pattern index
- `org/roles/*.yaml` — role schemas
- `org/runtime/*.yaml` — process catalog + substrate portfolio
- `org/key_results/*.yaml` — duty register

**Authorized write paths** (ZTARE → org/, only via CLI):
- `org/directives/{ts}_*.json` — Director directives via CLI
- `org/sessions/*.json` — session telemetry
- `org/gates/*` — gate state via closure_daemon

## What `org/` MUST NOT depend on

The split-readiness guarantee (per Debate B verdict 2026-05-08):

* `org/` source files MUST NOT contain `from src.ztare` or `import ztare`
* `org/` markdown files MAY reference ZTARE files for documentation but
  MUST NOT prescribe ZTARE-specific function calls

CI lint enforces: `scripts/check_org_independence.py`.

When this constraint is violated and not patched in the same commit,
the split-ready property degrades and a future polyrepo extraction will
require re-engineering the offending references.

## Versioning policy

`org/VERSION` follows semver:
- **Major (1.0.0 → 2.0.0)**: breaking change to a stable contract path
- **Minor (0.1.0 → 0.2.0)**: new pattern, new menu class, new role
- **Patch (0.1.0 → 0.1.1)**: bug fix, prose-only update

Consumers (autoresearch_loop, ZTARE Director agents) SHOULD pin or warn
on major version mismatch.

## Migration path to standalone repo

When ≥2 non-ZTARE substrates require `org/` standalone (the falsifiable
trigger from Debate B), the migration is:

```bash
git subtree split --prefix=org/ -b org-runtime-extract
git push <remote-org-runtime-repo> org-runtime-extract:main
# In ZTARE: add as pip dependency
echo "org-runtime @ git+https://github.com/sparckix/org-runtime@v0.X" >> pyproject.toml
# Remove org/ subtree from ZTARE
git rm -rf org/
```

Until that trigger fires, `org/` stays as a subdirectory in ZTARE
monorepo, engineered to be split-ready.

## Consumers (current)

- ZTARE validator (`src/ztare/validator/autoresearch_loop.py`) — reads
  bootstrap, mandates, runtime
- Research Director agent (Claude/Codex/GPT invoked via Director CLI) —
  reads mandate + patterns + menu at runtime
- Manager agent — reads manager_mandate.md
- closure_daemon — reads key_results for duty enforcement

## Consumers (future, hypothetical)

- Lean dojo bridge orchestrator (proof-search-as-substrate)
- mini-ZTARE (smaller-scale validator with same governance)
- VPS SRO daemon (autonomous research-out-of-the-box)

When N(future_consumers) ≥ 2, the split trigger fires.
