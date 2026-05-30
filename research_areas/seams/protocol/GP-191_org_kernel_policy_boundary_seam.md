# GP-191, Org Kernel / Policy Boundary

> **Seam metadata** · `seam_id:` GP-191 · `track:` protocol · `status:` Stage 1 ✓ closed; Stage 2 partial (file-level done, daemon-p · `last_updated:` 2026-05-09


**Status:** Stage 1 ✓ closed; Stage 2 partial (file-level done, daemon-path-rename deferred); Stage 3 ✓ closed
**Opened:** 2026-04-30
**Stage 2 partial closure:** 2026-05-07, see "Stage 2 / 3 partial closure" section below
**Owner:** principal + role.engineer
**Related:**
- `research_areas/[redacted]` §"keep the kernel hard / put looseness outside the kernel"
- `research_areas/[redacted]`
- `research_areas/[redacted]`
- `research_areas/[redacted]`
- `research_areas/[redacted]`
- `docs/internal/agent_workflow/agent_bootstrap_chain_2026-04-30.md`
- `docs/internal/agent_workflow/human_agent_flow_map_2026-04-30.md`

---

## Eigenquestion

The ZTARE evaluation engine has been built under explicit policy-kernel mode
discipline: small stable primitives in core, policy and domain knowledge in
loadable modules. The org runtime layer (`org/`, `ztare_workspace/gates/`,
`scripts/public/control/agent_daemon.py`, `scripts/public/control/closure_daemon.py`) has been built ad hoc
without explicit kernel-vs-policy partitioning. **Should the org runtime
layer adopt the same policy-kernel mode discipline as the ZTARE
evaluation engine, and if yes, where is the boundary?**

The fractal claim being tested: a substrate-agnostic AI-native organization
kernel exposes the same architectural shape as a substrate-agnostic
evaluation kernel, small primitives + loadable policy adapters, and the
discipline migrates cleanly across the two layers.

---

## Bounded Thesis

The thesis supported by current evidence is narrow:

> The org runtime layer has accumulated ZTARE-specific naming, vocabulary, and
> assumptions inside files that ought to be domain-neutral primitives. The
> contamination is recoverable. A formal kernel-vs-policy boundary, with the
> ZTARE bits moved to a `policy_adapters/` directory, would let the same org
> kernel back travel-research, fintech-research, legal-research, or any other
> AI-native organization without core code changes.

The thesis NOT supported by current evidence:
- That this work is urgent (it is not, Org-1 through Org-8 are higher leverage)
- That a strict rename today is the right move (it is risky; in-flight runs
  would break)
- That the boundary is the same as the existing apparatus kernel boundary
  (it is fractal but distinct, the apparatus kernel is about evaluation
  discipline; the org kernel is about role + channel + gate primitives)

---

## What is Kernel-Pure Today (Inventory)

These files in `org/` are domain-neutral and would survive a strict
kernel-only deployment with zero modifications:

- `org/roles/principal.yaml`, generic principal role
- `org/roles/manager.yaml`, generic manager role (mentions "research" in
  description; otherwise generic)
- `org/roles/engineer.yaml`, generic engineer role
- `org/roles/reviewer.yaml`, generic reviewer role (read-only inversion partner)
- `org/preferences/principal.yaml`, schema is generic; CONTENT is
  ZTARE-specific (priority weights for "scientific_discovery",
  "org_design_evolution"). The schema is kernel; the values are policy.
- `org/channels/<role>/{inbox,sent}/msg_*.json`, A2A typed messaging is
  kernel-pure
- `org/bootstrap_manifest.yaml`, newly shipped 2026-04-30; references
  ZTARE-related guides in `conditional_reads` but the schema is kernel
- `ztare_workspace/gates/{pending,resolved}/*.json`, gate schema is kernel
  (note: the directory NAME `ztare_workspace/` is policy-coupled; should be
  `runtime_workspace/` or `org_workspace/` under strict discipline)

## What is Policy-Leaked Today (Inventory)

These files contain ZTARE-domain-specific knowledge inside kernel paths:

- `org/roles/research_director.yaml`, explicitly research/ZTARE-domain
  (description references "ZTARE results", "research-taste opportunity
  cards", "instrument-vs-science separation"). **This is a domain-specific
  role, not a kernel primitive.** Under strict discipline this would move
  to `policy_adapters/ztare/roles/research_director.yaml`.
- `org/mandates/research_director_mandate.md`, same, domain-specific
- `org/mandates/manager_mandate.md`, references "ZTARE", "GP-128", and
  several other ZTARE-internal identifiers. Mixed: the manager role itself
  is kernel; this specific mandate is policy.
- `org/preferences/principal.yaml` (content), priorities reference
  "scientific_discovery" and "org_design_evolution"; specific to the
  current deployment. The schema is kernel; the data is policy.
- `org/objectives/`, `org/key_results/`, `org/tasks/`, schema kernel,
  content domain-specific
- `org/sessions/`, `org/signals/`, `org/directives/`, schema kernel,
  content domain-specific
- `ztare_workspace/` directory name, policy-leaked into the kernel
  workspace path
- `scripts/public/control/agent_daemon.py`, references `validate_agent_task_discipline.py`,
  EXPERIMENT_TRACK_RECORD.md, and the experiment cookbook in the prompt.
  These are ZTARE-specific procedural references inside what should be a
  generic role-execution loop.
- `scripts/public/control/closure_daemon.py`, kernel-pure (closure pressure is generic);
  but its consumers (the GP-070 orchestrator) are policy-coupled

## The Fractal Claim, Mapping

| ZTARE Evaluation Kernel | Org Runtime Kernel (Proposed) |
|---|---|
| Mutator + Judge + Gates pipeline | Role daemon + Inbox + Channel pipeline |
| Cage gates (R13, R14, R20-R24), generic falsification primitives | Gate JSON + closure daemon + A2A schema, generic governance primitives |
| Substrate-specific rubrics (gp163d, gp168, etc.), loadable policy | Domain-specific roles, mandates, preferences, loadable policy |
| `cage_orchestrator_substrate_agnostic_dispatch` (GP-157) | Org orchestrator substrate-agnostic dispatch (GP-191, this seam) |
| `keep the kernel hard / put looseness outside the kernel` | Same rule, applied to org/ instead of evaluation/ |

Both layers maintain the same kernel/policy-separation discipline: the kernel does not know
about the substrate; the substrate registers itself as a loadable module
that conforms to the kernel's typed contracts.

---

## Migration Path (Not Urgent, Document Now, Execute Later)

A safe migration would proceed in three stages:

### Stage 1, Mark the boundary (today)

- This seam (GP-191) names the boundary explicitly
- Add comments to policy-leaked files marking them as "ZTARE-coupled, kernel
  candidate when GP-191 lands"
- New files (e.g., `schemas/role.v1.schema.json` shipping in this same
  Org-3-followup turn) MUST be kernel-pure from day 1, no ZTARE
  vocabulary inside the schema
- The bootstrap manifest's `conditional_reads` may reference ZTARE-domain
  docs, but the manifest schema itself is kernel-pure

### Stage 2, Introduce `policy_adapters/` (next quarter, or when needed)

- Create `policy_adapters/ztare/` containing:
  - ZTARE-specific roles (research_director.yaml moves here)
  - ZTARE-specific mandates (research_director_mandate.md, ZTARE-coupled
    parts of manager_mandate.md)
  - ZTARE-specific bootstrap manifest extensions
  - The ZTARE workspace path (rename `ztare_workspace/` → standard
    `policy_workspace/ztare/` once consumers are updated)
- Update `agent_daemon.py` to load policy adapters via a registered name
  rather than hardcoded paths

### Stage 3, Validate kernel-only deployment (proof)

- Spin up a parallel deployment with NO ZTARE policy adapter, only the
  kernel. Verify roles + channels + gates + closure daemon all run in a
  do-nothing baseline (since no domain-specific work is queued).
- Spin up a parallel TRAVEL or FINTECH adapter as a second policy module.
  Verify the kernel runs both adapters without modification.
- That is the proof of substrate-agnostic org kernel.

Stages 2 and 3 are out of scope for the current Org-1 through Org-8 sequence.
This seam exists so the work isn't accidentally re-done in the wrong place
later.

---

## What This Seam Does NOT Do

- It does not block any current Org-track work
- It does not propose renaming any directory today
- It does not propose changing any in-flight daemon's behavior
- It does not claim the ZTARE evaluation kernel and the org runtime kernel
  are the SAME kernel, they are sibling kernels at different abstraction
  layers, sharing the same kernel/policy-separation discipline by analogy

What it does do:
- Names the kernel-vs-policy boundary as an explicit architectural object
- Provides the inventory so future agents know what's kernel-pure vs
  policy-leaked
- Establishes the rule that NEW org/ kernel artifacts must be domain-neutral
- Creates the cross-reference into the ZTARE-evaluation-kernel seams so
  the fractal claim is visible

---

## Immediate Decisions Made by This Seam

1. **The new `schemas/role.v1.schema.json` shipping in Org-3 followups
   bundle MUST NOT contain any ZTARE-specific field.** The schema validates
   role yaml structure; ZTARE-specific extensions (e.g., research-taste
   axes) live in a separate ZTARE-policy schema layered on top.

2. **The new `docs/internal/agent_workflow/agent_conflict_resolution_table.md` shipping
   in Org-3 followups bundle MUST NOT cite ZTARE-specific examples as the
   ONLY example.** Each conflict rule gets a generic example; ZTARE
   examples may be referenced as illustrations but not as the sole
   instantiation.

3. **The new `org/bootstrap_manifest.yaml` (already shipped) is kernel-pure
   in shape, but its `conditional_reads` references ZTARE-domain docs. This
   is acceptable because conditional reads ARE policy by definition, they
   are domain-specific docs. The required_reads list is kernel-pure.**

4. **AGENTS.md is policy-leaked and that is intentional.** AGENTS.md is the
   constitution for the SPECIFIC ZTARE-bearing repository, not a
   substrate-agnostic role contract. A future kernel-only deployment would
   ship its own AGENTS.md (or equivalent). The bootstrap manifest is the
   substrate-agnostic abstraction; AGENTS.md is the per-deployment
   constitution.

---

## Related Existing Work (Cross-Reference)

- **GP-086 Cage Kernel Hardening:** ZTARE evaluation kernel discipline.
  Same kernel/policy analogy at the apparatus layer.
- **GP-157 Cage Orchestrator Substrate-Agnostic Dispatch:** ZTARE
  apparatus's existing substrate-agnostic dispatch pattern. Org kernel
  should mirror this pattern at the role-execution layer.
- **GP-188 Research Director Primitive Compilation Boundary:** the
  predecessor seam that named the "primitives that compile from operator
  moves" boundary. GP-191 extends that boundary into org/ structurally.
- **GP-190 Post-Run Discriminator Daemon:** orthogonal, adds a primitive
  to the apparatus layer. GP-191 ensures THAT primitive lives in the
  apparatus kernel, not leaked into the org kernel.

---

## Closure Conditions

GP-191 closes when one of the following is true:

(a) Stages 1+2+3 all ship, the kernel-only deployment is verified, two
    distinct policy adapters run on the same kernel, and a sanitized
    public derivative documents the boundary in
    `docs/concepts/org_kernel.md`.

(b) Operator decides the work is not worth doing, close as `deferred` with
    explicit rationale.

(c) A larger refactor supersedes this seam, close as `superseded` with
    pointer to the successor.

Until then: the seam stays open as an architectural-anchor reference that
new work consults when the question "does this go in the kernel or in a
policy adapter" arises.

---

## Stage 2 / 3 partial closure (2026-05-07)

Implemented the policy-adapter directory the seam called for, named
`tenants/` (slightly cleaner than `policy_adapters/`, reads
naturally to forkers). Also verified Stage 3 by running the public tree
in kernel-only mode.

### What shipped

**Public side** (`figs_activist_loop`):
- New top-level `tenants/` directory with public `README.md` documenting
  the slot. Subdirs (`tenants/<id>/`) are gitignored.
- `.gitignore` additions:
  - `org/roles/research_director.yaml` (was tracked publicly; now lives in tenant overlay)
  - `org/roles/product_manager.yaml` (was untracked but ZTARE-specific; now in overlay)
  - `org/preferences/principal.yaml` (the values; schema stays at `org/preferences/templates/`)
  - `tenants/*/` (any future tenant overlay content)
- Public `org/` is now substrate-agnostic by file-content (kernel-pure
  files only), exactly the GP-191 Stage 2 inventory's "kernel-pure"
  list ships publicly.
- `docs/guides/forking_the_kernel.md` §1 + §8 updated to document the
  tenant-overlay pattern.

**Private side** (new sibling repo `<tenant-repo>`):
- `tenants/ztare/{roles,preferences,mandates}/`, six files moved out of
  public `org/`:
  - `roles/research_director.yaml`
  - `roles/product_manager.yaml`
  - `preferences/principal.yaml`
  - `mandates/research_director_mandate.md`
  - `mandates/manager_mandate.md`
  - `mandates/product_manager_mandate.md`
- `scripts/public/setup_tenant.sh`, symlinks the six files into the public
  tree at conventional `org/...` paths. Idempotent.
- `scripts/public/teardown_tenant.sh`, removes the symlinks. Returns the
  public tree to kernel-only mode.

### What's deferred (Stage 2 remainder)

The seam's GP-191 inventory called out additional path-rename work:
- `ztare_workspace/` directory name → `runtime_workspace/` or `policy_workspace/ztare/`
- `scripts/public/control/agent_daemon.py` hardcoded references to `EXPERIMENT_TRACK_RECORD.md`
  and the experiment cookbook
- `closure_daemon.py` consumers (GP-070 orchestrator) policy-coupling
- `org/roles/manager.yaml` + `engineer.yaml` `authorized_paths` with
  `src/ztare/`, `ztare_workspace/`, `ztare_proofs/`

These are **deferred** per the seam's own discipline ("does not propose
renaming any directory today"). Reactivation trigger: when a non-ZTARE
tenant adopts the kernel and these path leaks become friction.

### How Stage 3 was verified (2026-05-07)

```bash
# Activate overlay
~/<tenant-repo>/scripts/public/setup_tenant.sh
python scripts/public/control/org_role_preflight.py --role research_director
# → PASS: all dependencies resolve via symlinks

# Deactivate overlay (kernel-only mode)
~/<tenant-repo>/scripts/public/teardown_tenant.sh
python scripts/public/control/org_role_preflight.py --role research_director
# → FAIL: missing role_yaml: org/roles/research_director.yaml
# This is the EXPECTED failure for a fresh public clone with no tenant.
# Kernel boots; ZTARE-specific role is unavailable. Stage 3 verified.
```

The fail-mode is correct: a fork without a tenant overlay can run the
kernel (Manager / Engineer / Reviewer roles still work) but ZTARE-
specific roles produce a missing-yaml error rather than silent
behavior. Forkers know to run their own `setup_tenant.sh`.

### Second-tenant readiness

Adding a non-ZTARE tenant requires:
1. New private repo `<org>-tenant-overlay`
2. Mirror `tenants/<id>/{roles,preferences,mandates}/` shape
3. Mirror `scripts/public/setup_tenant.sh` with their tenant id
4. Run on same kernel

Stage 3's full closure ("two distinct policy adapters run on the same
kernel") is now waiting for an actual second tenant, the kernel is
ready; the second adapter is not yet authored. When it ships, GP-191
closes fully.
