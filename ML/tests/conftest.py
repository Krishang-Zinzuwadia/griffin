"""Shared pytest setup.

Force the mock provider and clear any real credentials before any ML module is
imported, so the whole suite runs offline, deterministically, with no network.
"""

import os

os.environ["LLM_PROVIDER"] = "mock"
os.environ["GRIFFIN_OFFLINE"] = "1"
for _var in ("GITHUB_TOKEN", "GITHUB_OWNER", "VERCEL_TOKEN"):
    os.environ.pop(_var, None)
