"""General contract-governed hardening meta-runner entry point.

This module is the stable, non-V4-specific name for the deterministic
promotion-contract runner described in the contract-governed hardening paper.

The historical implementation lives in ``v4_meta_runner.py`` because the first
governed queue was the ``epistemic_engine_v4`` six-stage hardening board. Keep
that file for reproducibility and old shell shortcuts; import this module when
the concept is general contract-governed hardening rather than the historical V4
queue.
"""
from __future__ import annotations

from ztare.validator.v4_meta_runner import (  # noqa: F401
    CONTRACT_REGISTRY,
    DEFAULT_QUEUE,
    ContractResult,
    ContractVerdict,
    MetaRunner,
    MetaRunnerState,
    Priority,
    StageSpec,
    build_parser,
    ensure_plan_exists,
    ensure_state_exists,
    load_runner,
    main,
    plan_path,
    print_status,
    project_dir,
    state_path,
)


if __name__ == "__main__":
    raise SystemExit(main())
