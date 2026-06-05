#!/usr/bin/env python3
"""Compat module-alias: ``leanmill_evaluation_harness_runner`` -> sibling ``evaluation_harness_runner``.
The cleanup branch renamed leanmill_*.py siblings to *.py but importers still use
the leanmill_ prefix; this aliases the module so ``from leanmill_evaluation_harness_runner import X`` works.
New code should import ``evaluation_harness_runner`` (or ``ztare.leanmill.*``) directly."""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules[__name__] = importlib.import_module("evaluation_harness_runner")
