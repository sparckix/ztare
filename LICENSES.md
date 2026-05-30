# Licensing Map

All published code in this repository is MIT-licensed. This file is a
repository map, not legal advice. If a file contains its own SPDX header
or license notice, that file-level notice controls.

## MIT-Licensed Materials

The MIT License in [LICENSE](LICENSE) covers everything published in this
repository, including:

- all source code under `src/ztare/` and `scripts/`;
- governance/orchestration code under `src/ztare/orchestration/`,
  `src/ztare/supervisor/`, `src/ztare/sessions/`, `src/ztare/signals/`,
  and `src/ztare/notifications/`, plus `org/`, `supervisor/`, `orbit/`,
  and `deploy/` (these are ZTARE's tenant-overlay integration of the
  upstream cognitive-firm kernel; the canonical kernel and its license
  live at https://github.com/sparckix/cognitive-firm);
- deterministic rubrics and public benchmark fixtures under `rubrics/`,
  `benchmarks/`, and `tests/`;
- public documentation under `docs/`;
- public papers and public research ledgers under `papers/` and
  `research_areas/`;
- Lean proof/checker modules under `ztare_proofs/`;
- public project examples that are not gitignored.

## Not Part Of The Public License Grant

Gitignored/private files are not shipped public artifacts and are not
part of the public license grant until deliberately promoted or rendered
into a public derivative. This includes:

- `research_areas/private/`;
- `.ip_protected/`;
- active strategy seams, sealed pre-registrations, GT derivations, and
  in-flight experiment tactics;
- principal preferences, mandates, channels, directives, sessions,
  runtime task state, local transition logs, and approval queues;
- credentials, contact channels, API keys, local logs, cloud/GPU
  telemetry, and machine-specific runtime state.

## Dependency Artifacts

Generated dependency folders such as `node_modules/`, `orbit/node_modules/`,
`venv/`, `.lake/`, and build outputs are not source artifacts. They should
be rebuilt from lockfiles or toolchain manifests rather than committed.
