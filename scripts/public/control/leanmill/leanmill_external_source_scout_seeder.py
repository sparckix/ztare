#!/usr/bin/env python3
"""Compat module-alias: ``leanmill_external_source_scout_seeder`` -> sibling ``external_source_scout_seeder``.
The cleanup branch renamed leanmill_*.py siblings to *.py but importers still use
the leanmill_ prefix; this aliases the module so ``from leanmill_external_source_scout_seeder import X`` works.
New code should import ``external_source_scout_seeder`` (or ``ztare.leanmill.*``) directly."""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules[__name__] = importlib.import_module("external_source_scout_seeder")
