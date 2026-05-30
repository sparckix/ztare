---
id: ANTI-PATTERN-008
name: deployment_time_pre_spec_laundering
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: ["the pre-registration captures what we intended", "pre-spec written in parallel", "pre-reg finalized while agents were warming up", "we pre-registered the criteria during the deployment"]
  structural:
    - pre_spec_commit_timestamp_after_first_dispatch_log
    - pre_spec_sha_missing_or_empty_at_round_1_write_time
    - pre_spec_authored_with_visibility_into_partial_agent_outputs
    - retroactive_pre_spec_added_after_deployment_close
  problem_classes: [apparatus_self_audit]
detection_protocol:
  primary: PATTERN-001  # friction_debate (rule_6_pre_spec_locked_before_deployment)
  secondary: PATTERN-005  # falsifiable_asymmetry, does the pre-spec predict ANY agent attack vector it didn't already see?
  rule:
    - "For every Pattern-001 deployment, locate `orchestration_state/{task_id}/pre_spec_sha.txt`. If absent or empty, fire."
    - "Read the commit at pre_spec_sha. If its committer-timestamp is later than the earliest dispatch log entry for the deployment, fire."
    - "Check git log for amendments to the pre_spec file between dispatch and joint-verdict write time. Any post-dispatch amendment that touches the criteria list, verdict alphabet, or scoring rule fires."
    - "If pre_spec_sha was added retroactively (committed AFTER the deployment's joint verdict was written), fire, even if the file content claims earlier authorship."
mitigation:
  - "The deployment is automatic INSUFFICIENT_EVIDENCE on all criteria (per PATTERN-001 rule 6). Verdict cannot be repaired in place."
  - "The orchestration runner must REFUSE to write `round_1.json` when `pre_spec_sha.txt` is absent or empty. This is the central enforcement point."
  - "If a partial deployment was already run without a locked pre-spec, close it as INSUFFICIENT_EVIDENCE and re-deploy with a fresh task_id and a freshly-committed pre-spec."
  - "Do NOT 'recover' the deployment by writing the pre-spec from memory of what was 'intended'. The commit timestamp is the only honest signal."
examples:
  - id: catch_30
    summary: "Pincer META-DARWIN deployment, pre-registration was authored ~30 minutes INTO the 5-agent dispatch, with operator visibility into early agent outputs. The 'pre-spec' was task-conditional, not pre-registration."
    file: projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_audit_2026_05_08.md
  - id: catch_31
    summary: "Re-audit confirmed the fix-dispatch did not address this failure mode (no Lean code can fix a missing commit-before-dispatch). Promotion to ANTI-PATTERN-008 + PATTERN-001 rule_6 is the enforcement-level fix."
    file: projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_re_audit_2026_05_08.md
falsifiable_test:
  description: "For every Pattern-001 deployment, the file `orchestration_state/{task_id}/pre_spec_sha.txt` must exist, be non-empty, and reference a git commit whose committer-timestamp is strictly earlier than the earliest dispatch log entry for the deployment. The anti-pattern fires iff any of these conditions fails."
  binary_check: "exists(pre_spec_sha_path) AND non_empty(pre_spec_sha) AND git_commit_time(pre_spec_sha) < min(dispatch_log_times) AND no_post_dispatch_amendments(pre_spec_file), firing iff False."
  not_trivial: "Returns 'not firing' for any deployment whose pre-spec file was committed before the first agent prompt and never amended afterward. Catch #30's pincer deployment returns firing (pre-spec written ~30min into dispatch). A future deployment with a properly-locked pre-spec returns not-firing. The test discriminates on a numeric timestamp comparison; it is enforced by the orchestration runner refusing to write round_1.json without pre_spec_sha. NOT True := by trivial."
chain_position: pre  # runs BEFORE any agent dispatch; gates Pattern-001 entry
references:
  - "PATTERN-001 friction_debate (rule_6_pre_spec_locked_before_deployment)"
  - "PATTERN-005 falsifiable_asymmetry"
  - "projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_audit_2026_05_08.md"
  - "projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_re_audit_2026_05_08.md"
---

# ANTI-PATTERN-008, Deployment-Time Pre-Spec Laundering

## What it is

The pre-registration file (criteria, verdict alphabet, scoring
rule) for a Pattern-001 deployment is authored, finalized, or
amended AFTER the first agent dispatch, typically with operator
visibility into early agent outputs or attack vectors. The pre-
spec is therefore not pre- to anything; it is task-conditional
documentation dressed as pre-registration.

## Why it appears

Pre-registration is procedurally inconvenient. The natural workflow
is to dispatch agents first, see what they produce, then write
the criteria/scoring rule that best frames the outputs. This
inverts the epistemic role of pre-registration (constraint on the
operator) into post-registration (presentation aid for the
operator).

## Why it matters

A pre-spec written with visibility into agent outputs cannot
constrain operator behavior, it can only ratify it. Every
laundering catch this catalog defends against (charity grades,
criterion drift, vocabulary smuggling) becomes easier when the
pre-spec is movable.

## Detection protocol

1. Locate `orchestration_state/{task_id}/pre_spec_sha.txt`. If
   absent or empty, fire.
2. Read the git commit at pre_spec_sha. Compare its committer-
   timestamp to the earliest dispatch log entry. If pre-spec is
   later, fire.
3. Check `git log -- {pre_spec_path}` for amendments between
   dispatch and joint-verdict write. Any amendment touching the
   criteria list, verdict alphabet, or scoring rule fires.
4. If pre_spec_sha was added retroactively (committed AFTER
   joint-verdict write), fire.

## Mitigation when detected

- Deployment is automatic INSUFFICIENT_EVIDENCE on all criteria.
- Orchestration runner refuses to write `round_1.json` without
  a non-empty `pre_spec_sha.txt`. This refusal is the load-
  bearing enforcement.
- Re-deploy with a fresh task_id and a properly-committed pre-
  spec. Do not reconstruct the pre-spec from memory.

## Falsifiable test (catalog-level)

`pre_spec_sha exists AND committed_before_first_dispatch AND not_amended_post_dispatch`.
Firing iff False.

NOT trivially True: catch #30 fires (pre-spec ~30min into
dispatch); a properly-locked future deployment returns not-firing.
The test reduces to a numeric timestamp comparison and a git log
check, both binary and machine-checkable. NOT `True := by trivial`.

## Enforcement asymmetry vs aspiration

The enforceable part: the orchestration runner refuses to start
a Pattern-001 deployment without `pre_spec_sha.txt`. That refusal
is mechanical.

The aspirational part: a sufficiently determined operator can
always backfill the pre-spec into a prior commit by amending
history. This catalog cannot prevent that. The enforcement is
"honest operator + git log audit", not "cryptographic proof of
prior knowledge". This is the limit of the discipline; it is
documented honestly here rather than papered over.

## Cross-references

- PATTERN-001 (`org/patterns/pattern_1_friction_debate.md`,
  rule_6_pre_spec_locked_before_deployment)
- ANTI-PATTERN-005 (`org/anti-patterns/narrative_inflation.md`)
- `projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_audit_2026_05_08.md`
- `projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_re_audit_2026_05_08.md`
