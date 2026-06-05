#!/usr/bin/env python3
"""Compat module-alias: ``leanmill_operator_contracts`` -> sibling ``operator_contracts``.
The cleanup branch renamed leanmill_*.py siblings to *.py but importers still use
the leanmill_ prefix; this aliases the module so ``from leanmill_operator_contracts import X`` works.
New code should import ``operator_contracts`` (or ``ztare.leanmill.*``) directly."""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules[__name__] = importlib.import_module("operator_contracts")
