# `tenants/` — instantiation slot

This directory is the **policy-adapter slot** for tenant-specific instantiations of the `org/` kernel primitives. It corresponds to GP-191 Stage 2 (the org-kernel/policy-boundary seam).

## What goes here

Each tenant is one subdirectory with this shape:

```
tenants/
  <tenant-id>/
    roles/                    ← tenant-specific role yamls (replace public org/roles/* of same name)
    preferences/              ← tenant-specific principal preferences (the values, not the schema)
    mandates/                 ← tenant-specific mandate bodies
    org_overlay/              ← optional: snapshots of objectives/, key_results/, sessions/ for backup
    ztare_workspace_snapshot/ ← optional: runtime state snapshots
```

The contents of any `tenants/<tenant-id>/` subdir are **gitignored from this repo** (per the public `.gitignore`). The tenant content lives in a sibling private repo and is symlinked in via the tenant's `setup_tenant.sh` script.

## Standing tenants

| Tenant id | Private repo | Description |
|---|---|---|
| `ztare` | `github.com/sparckix/ztare-research-co` | ZTARE Research Co — the principal's research org (the original instantiation that birthed this kernel) |

## How to add a new tenant

1. Create a new private repo, e.g. `<your-org>-tenant-overlay`
2. Mirror the `tenants/<tenant-id>/{roles,preferences,mandates}/` shape inside it
3. Write a `scripts/setup_tenant.sh` (use the ZTARE one as template) with relative symlinks pointing back at your private overlay
4. Add a row to the table above (PR welcome)

Forks of this kernel run in **kernel-only mode** by default — no tenant overlay required for the kernel to boot. See `docs/guides/forking_the_kernel.md` §1 for the kernel/instantiation split contract.

## Architectural references

- `seams/protocol/GP-191_org_kernel_policy_boundary_seam.md` — the seam this directory implements
- `seams/protocol/GP-192_enterprise_grade_org_runtime_seam.md` §Axis 7 — the daily-snapshot pattern this directory enables
- `docs/guides/forking_the_kernel.md` — operator-facing kernel/instantiation contract
- `docs/concepts/ztare_research_company_architecture.md` §Multi-Server Shape — the multi-tenant target architecture
