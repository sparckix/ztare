# SPDX-License-Identifier: MIT
"""Engine logic for the ``ztare autoresearch`` CLI surface.

The ``ztare autoresearch`` dispatcher in :mod:`ztare.cli` is a thin wrapper:
it parses arguments, routes to a verb, and formats output. The actual
computation — project-intake defaults, run-readiness blocker checks — lives
here so the dispatcher stays a dispatcher. Stdlib-only, no model calls.
"""
