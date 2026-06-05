#!/usr/bin/env python3
"""Compat module-alias: ``leanmill_family_specs`` -> sibling ``family_specs``.
The cleanup branch renamed leanmill_*.py siblings to *.py but importers still use
the leanmill_ prefix; this aliases the module so ``from leanmill_family_specs import X`` works.
New code should import ``family_specs`` (or ``ztare.leanmill.*``) directly."""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules[__name__] = importlib.import_module("family_specs")
