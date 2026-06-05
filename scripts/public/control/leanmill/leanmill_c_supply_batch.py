#!/usr/bin/env python3
"""Compat module-alias: ``leanmill_c_supply_batch`` -> sibling ``c_supply_batch``.
The cleanup branch renamed leanmill_*.py siblings to *.py but importers still use
the leanmill_ prefix; this aliases the module so ``from leanmill_c_supply_batch import X`` works.
New code should import ``c_supply_batch`` (or ``ztare.leanmill.*``) directly."""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules[__name__] = importlib.import_module("c_supply_batch")
