"""Shared test fixtures – disable Gemini scheduling to keep tests fast and deterministic."""
from __future__ import annotations

import os

# Disable live Gemini calls during tests so the deterministic planner is always used.
os.environ["GEMINI_ENABLE_SCHEDULING"] = "false"
