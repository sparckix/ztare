#!/usr/bin/env python3
"""Compat module-alias: ``leanmill_heldout_receipt_gate`` -> sibling ``heldout_receipt_gate``.
The cleanup branch renamed leanmill_*.py siblings to *.py but importers still use
the leanmill_ prefix; this aliases the module so ``from leanmill_heldout_receipt_gate import X`` works.
New code should import ``heldout_receipt_gate`` (or ``ztare.leanmill.*``) directly."""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules[__name__] = importlib.import_module("heldout_receipt_gate")
