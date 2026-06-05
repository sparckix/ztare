#!/usr/bin/env python3
"""Compat module-alias: ``leanmill_learning_feedback_contract`` -> sibling ``learning_feedback_contract``.
The cleanup branch renamed leanmill_*.py siblings to *.py but importers still use
the leanmill_ prefix; this aliases the module so ``from leanmill_learning_feedback_contract import X`` works.
New code should import ``learning_feedback_contract`` (or ``ztare.leanmill.*``) directly."""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules[__name__] = importlib.import_module("learning_feedback_contract")
