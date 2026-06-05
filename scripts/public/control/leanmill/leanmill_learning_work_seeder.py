#!/usr/bin/env python3
"""Compat module-alias: ``leanmill_learning_work_seeder`` -> sibling ``learning_work_seeder``.
The cleanup branch renamed leanmill_*.py siblings to *.py but importers still use
the leanmill_ prefix; this aliases the module so ``from leanmill_learning_work_seeder import X`` works.
New code should import ``learning_work_seeder`` (or ``ztare.leanmill.*``) directly."""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules[__name__] = importlib.import_module("learning_work_seeder")
