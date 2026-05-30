# Security

ZTARE is a single-operator research apparatus that runs on the operator's
own machine. It has no public network service, no user accounts, no
multi-tenant surface, and no remote control plane. Most of the
conventional web-application threat model does not apply. The threats
that *do* apply are the ones that follow from the apparatus's actual
shape: it executes agentic code, ingests untrusted text into agent
context, and asserts correctness through ledgers and pre-registered
contracts that depend on integrity rather than confidentiality.

This document states the threats taken seriously, the assumptions the
system already makes about its own integrity, and how to report
something that breaks those assumptions.

## Threat model

### 1. Agentic execution is arbitrary code execution under the operator's UID

The apparatus invokes LLM tool-use agents (Codex, Claude Code,
role-bound daemons) that can read the filesystem, write files, run
subprocesses, and call out to model APIs. There is no sandbox between
agent-emitted instructions and the operator's environment. Running this
repo is functionally equivalent to giving a junior contractor shell
access to your machine, with the additional property that the
contractor's behavior is sensitive to the contents of files the agent
reads.

**Assumption:** the operator runs the apparatus in an environment whose
blast radius they accept (a dedicated user, a VM, a workspace machine).
Running it on a host that holds production credentials, signing keys,
or write access to shared infrastructure is out of scope and not
supported.

### 2. Prompt injection through ingested artifacts

The apparatus ingests Lean sources, mathlib snapshots, mined corpora,
research papers, sampled web pages, and operator notes into agent
context. Any of those paths is a vector for instructions that target
the agent rather than the human reader. Inputs that look like data to a
human read as instructions to a model.

**Defenses already in the apparatus.** Source-readiness labels mark
which inputs are membrane-clean; observer/membrane boundaries restrict
what an agent at a given role may act on; the operator console is the
adjudication rail when a substrate is ambiguous; the Governance Gate
(`scripts/public/control/leanmill/governance_worker.py`) is the only
ratifier of proof-value credit and refuses unsourced promotion. These
are correctness controls, not security controls, but they constrain how
far an injected instruction can move before it hits a deterministic
gate.

**What breaks them:** ingesting an unlabeled source as if it were
membrane-clean, or letting an agent role write outside its declared
scope. Report either as a defect.

### 3. Audit-trail integrity is the central correctness property

The validator loop, the closure-claim governance discipline, the
forecast pool, and the reflexive mining layer all assume their ledgers
record what actually happened. Silent rewriting of
`analytics/public/ledgers/`, the catch ledger, the prediction ledger,
the trajectory archive, or rewriting git history on any branch the
operator treats as canonical, defeats the central correctness
guarantee. From the outside this looks like normal file editing; from
the apparatus's perspective it is forgery.

The mitigations are structural rather than cryptographic: append-only
ledger conventions, the pre-registered evaluation-harness contract with
its `contract_sha256` pin, separate publication-surface and
working-surface trees, and an explicit non-destructive operator
discipline (no force-push to operator-canonical branches, no
`--no-verify`, no destructive git without explicit authorization).

**Treat as a vulnerability:** any path through the apparatus that
silently mutates a ledger without leaving a corresponding event, any
gate that promotes a claim whose evidence packet is not source-labeled,
and any divergence between a pre-registered contract SHA and the file
the runner actually executes.

### 4. Sealed-result discipline

The forecast pool's calibration value depends on forecasts being sealed
before resolution: an observer who can read a resolved-but-not-revealed
forecast file before the resolution window leaks the apparatus's own
self-evaluation. The protection is filesystem layout and ledger
hygiene, not access control. Anyone with read access to the host has
access to these files; the discipline assumes the operator is also the
forecast author.

A pull request, fork, or shared CI runner that surfaces sealed
forecasts before resolution is a leak even if no key material moves.

### 5. Pre-registration drift

The evaluation-harness contract at
`analytics/public/leanmill/dashboard_data/evaluation_harness_contract.json`
pins a `contract_sha256` value that must match the file's actual
content hash at run time. The eval-harness runner enforces this check
and aborts on mismatch. A live mismatch currently exists (pinned
`6fbdce…6e71a90`, actual `ed46ada5…`); this is the system detecting
post-registration edits, exactly the behavior the pin was added for.
Operator reconciliation is pending; do not bypass the check with
`--skip-contract-sha-check` for credited runs.

### 6. LLM output treated as evidence

The deepest misuse is not a CVE. It is treating model-emitted prose as
evidence of capability without deterministic-gate corroboration. The
apparatus is structured to make this hard (rubrics, gates, ledgers,
falsifiers, demotions), but the discipline is operator-enforced. A
fork that publishes a model's narrative as a validated result while
stripping the gate/demotion machinery has not been hacked; it has
broken the contract this repo describes. If you find a path that lets
the apparatus publish such a claim without a demotion-on-failure
recorded, report it as a defect.

## Out of scope

- Conventional web-application vulnerabilities — there is no HTTP
  service, no auth surface, no session handling.
- Denial of service against a public endpoint — there is no public
  endpoint.
- Anything under `_archive/`, `workingpapers/`, `research_areas/private/`,
  `.ip_protected/`, `docs/internal/`, or paths matched by `.gitignore`.
  These are working state, not the publication surface.
- Dependency CVEs in `requirements.txt` — track separately with
  `pip-audit` or equivalent; an alert there is upstream maintenance,
  not a ZTARE-specific vulnerability.
- The HTML demo under `docs/landings/` — static, no scripts that touch
  apparatus state.
- Cosmetic, broken-link, or doc-staleness issues — open a normal issue.

## Reporting

Use the private channel; do not open a public issue.

- **Private GitHub Security Advisory:**
  <https://github.com/sparckix/ztare/security/advisories/new>
- **Email:** `sparckix@gmail.com`

Useful in the report: the path through the apparatus you took, the
file(s) or ledger(s) involved, whether you reproduced it, and whether
it surfaced through normal operator use or required a crafted input. A
working proof-of-concept is welcome but not required.

## What to expect

This is a single-operator research repository. There is no SLA, no
bounty program, no triage team. The realistic commitment is: an
acknowledgement within seven days, a written assessment (fix, document
as known, or rule as out of scope) within thirty, and a reporter
credit in the resulting commit and `DECISION_LOG.md` entry unless the
reporter prefers anonymity. Coordinated disclosure for issues that
might affect downstream forks is preferred over silent patching.
