#!/usr/bin/env python3
"""Shim — real implementation at ``ztare.leanmill.work_queue``.

Existing ``import leanmill_work_queue as work_queue`` patterns used by
~14 worker scripts continue to work without modification.

The boundary rule (kernel must not depend on scripts) is preserved:
this shim depends on the kernel via the standard package import; the
kernel does not depend on this shim.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[4] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Re-export the entire public surface so `import leanmill_work_queue as wq;
# wq.<name>` continues to work. Names enumerated explicitly (rather than via
# `from ... import *`) so static analysers and IDEs can see them.
from ztare.leanmill.work_queue import (  # noqa: E402, F401
    DEFAULT_DB,
    DEFAULT_EVENTS,
    FALLBACK_STALE_PROCESS_GRACE_S,
    FALLBACK_WORKER_HEARTBEAT_STALE_S,
    PROCESS_STARTED_AT,
    STATUSES,
    FACTORY_POLICY,
    append_event,
    artifact_ref,
    artifact_refs,
    artifact_refs_for_path,
    claim,
    claim_matching,
    connect,
    enqueue,
    heartbeat,
    list_items,
    main,
    open_stats,
    reclaim_all_open_claims,
    reclaim_expired,
    reclaim_worker_claims,
    reclaim_terminated_worker_claims,
    record_artifact_ref,
    terminalize_exhausted_queued,
    record_terminal_item,
    record_worker_heartbeat,
    requeue_with_payload_update,
    row_to_dict,
    runtime_version_receipt,
    runtime_version_settings,
    stats,
    update_status,
    worker_version_health,
)


if __name__ == "__main__":
    raise SystemExit(main())
