#!/usr/bin/env python3
"""Compat module-alias: ``leanmill_source_search_integrator`` -> sibling ``source_search_integrator``.
The cleanup branch renamed leanmill_*.py siblings to *.py but importers still use
the leanmill_ prefix; this aliases the module so ``from leanmill_source_search_integrator import X`` works.
New code should import ``source_search_integrator`` (or ``ztare.leanmill.*``) directly."""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules[__name__] = importlib.import_module("source_search_integrator")
