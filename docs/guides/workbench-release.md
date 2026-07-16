---
description: "Supported install, project-visibility, remote-access, and release-verification procedure for Project Workbench."
---

# Project Workbench Release Guide

> Up: [Documentation map](../README.md) · Product details: [Workbench README](../../forensic-workbench/README.md)

This guide answers four operational questions: how to start the Workbench, which projects it may reveal,
how to reach it on another machine, and how to prove the artifact is ready to share.

## Supported operating model

Project Workbench is a local-first, trusted-user application. Its Python server serves the compiled React
app, reads project files, writes bounded project history, and relays actions through the ZTARE CLI. Access to
the server is therefore equivalent to access to those project files under the server process's user.

Supported:

- one trusted operator on loopback;
- one-port container deployment on `127.0.0.1:8765`;
- remote use through an SSH tunnel to a loopback-bound server;
- fail-closed `public` or explicit `allowlist` project visibility for demos.

Not supported:

- an internet-facing port;
- multiple untrusted users;
- authentication, authorization, tenant isolation, or rate limiting;
- treating CORS or a project allowlist as an authentication layer.

## Install and start

### One-container path

Requirements: Docker Engine or Docker Desktop, Docker Compose, and Docker Buildx.

```bash
git clone https://github.com/sparckix/ztare && cd ztare
make forensic-workbench-docker
```

Open `http://127.0.0.1:8765`. The image contains the compiled frontend and Python runtime. `projects/` and
`rubrics/` are bind-mounted from the checkout so the container works on the operator's files without baking
them into the image.

### Source path

Requirements: Python 3.11+, Node 20+, npm, and the repository Python environment.

```bash
git clone https://github.com/sparckix/ztare && cd ztare
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-public-smoke.txt
pip install -e .
make forensic-workbench-live
```

Open `http://127.0.0.1:5174`. The launcher starts the API on port 8765, starts Vite on port 5174, and installs
the locked frontend dependencies with `npm ci` on first use.

That installation is sufficient for the Workbench and subscription-CLI paths. API-backed model actions load
their provider only when selected; add `ztare[google]`, `ztare[anthropic]`, `ztare[openai]`, or
`ztare[providers]` as needed. Use the full `requirements.txt` only for research and solver development.

## Choose the project boundary

### Local scope

`local` is the default for a trusted operator. It can inventory project folders in the mounted checkout.

```bash
make forensic-workbench-docker
```

Do not use local scope for a shared demo if the checkout contains private projects.

### Public scope

`public` exposes exactly the slugs in `forensic-workbench/public-projects.json`. An unlisted project is
removed from inventory and rejected by project snapshots, file previews, and write routes even when it is
present on disk.

```bash
ZTARE_WORKBENCH_PROJECT_SCOPE=public make forensic-workbench-docker
```

Review and commit the manifest as release material. Never add a project merely to make a smoke test pass.

### One-off allowlist

Use an explicit list when the boundary should not be committed:

```bash
python scripts/public/control/forensic_workbench_live.py \
  --project-scope allowlist \
  --projects demo_claims,ops_root_cause_diagnosis_demo
```

The allowlist is a disclosure boundary, not an identity boundary. Anyone who can reach the server can use
the allowed read and write actions.

## Remote access

Start the server on the remote host in `public` or explicit `allowlist` scope. Keep the published port bound
to `127.0.0.1`.

```bash
# remote host
ZTARE_WORKBENCH_PROJECT_SCOPE=public make forensic-workbench-docker

# operator laptop
ssh -N -L 8765:127.0.0.1:8765 user@remote-host
```

Open `http://127.0.0.1:8765` on the laptop. Do not change the Compose binding to `0.0.0.0`; the SSH tunnel is
the supported network boundary.

## Release gate

From a checkout containing only intended release changes:

```bash
make forensic-workbench-release-check
make forensic-workbench-docker-build
```

The first command must report zero failures after checking:

- the production frontend exists and is served by the API origin;
- the public manifest is valid and exactly matches the visible inventory;
- an unlisted project snapshot, file preview, and write are refused before action dispatch;
- an untrusted browser origin is not admitted by CORS.

The second command proves the same source builds the one-port image. Buildx is required because the
Workbench-specific Docker ignore file keeps private projects, research trees, solver corpora, caches, and
local artifacts out of the build context.

With a local server running, also verify the real UI/API interaction contract:

```bash
make workbench-interaction-smoke
```

That smoke exercises existing-project reads, generated-document preview, LeanMill reads, new-project create
and cleanup, run preview, and LeanMill target preview without launching a model-backed run.

Before tagging or sharing, complete the [repository release checklist](../../RELEASE_CHECKLIST.md), including
the canonical route render checks and CI job `workbench-release-boundary`.

## Expected healthy state

`GET /api/status` should report:

- `ok: true`;
- `app_built: true` for the one-port image;
- `project_visibility.scope` equal to the selected mode;
- `project_visibility.visible_project_count` equal to the intended public/allowlist count.

In public scope, `/api/projects` must contain no slug outside the manifest. A rejected project request should
return `project is not available in this Workbench` without revealing whether the folder exists.

## Troubleshooting

**`docker buildx` is missing.** Install the Buildx plugin supplied by Docker Desktop or your package manager,
then rerun `docker buildx version`. Do not fall back to a legacy builder for a release artifact; it does not
honor the Workbench-specific context filter consistently.

**Port 8765 or 5174 is occupied.** Stop the earlier Workbench process. The launcher refuses to silently move
ports because bookmarks and API-origin assumptions should stay deterministic.

**A private project appears in a demo.** Stop the server, switch from `local` to `public` or `allowlist`, review
the manifest/list, and rerun `make forensic-workbench-release-check` before reopening it.

**A model-backed action cannot run in the container.** The release image supports the Workbench, its read
models, and light CLI actions. Full autoresearch campaigns require the repository's heavier research runtime
and model credentials; run those on the trusted host and inspect their durable project outputs in Workbench.
