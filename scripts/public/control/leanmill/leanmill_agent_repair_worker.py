#!/usr/bin/env python3
"""Compat module-alias: ``leanmill_agent_repair_worker`` -> sibling ``agent_repair_worker``.
The cleanup branch renamed leanmill_*.py siblings to *.py but importers still use
the leanmill_ prefix; this aliases the module so ``from leanmill_agent_repair_worker import X`` works.
New code should import ``agent_repair_worker`` (or ``ztare.leanmill.*``) directly."""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules[__name__] = importlib.import_module("agent_repair_worker")
