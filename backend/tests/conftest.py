"""Test-suite guard, imported before any app module. Environment variables take
priority over the .env file in pydantic-settings, so these keep the suite
deterministic, offline and free regardless of local configuration:

- no real LLM calls; mock retrieval (no model files needed — the real hybrid
  stack has its own tests that skip when models aren't cached);
- a throwaway SQLite database per test session;
- auth disabled for the general API tests (test_auth.py re-enables it).
"""

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="advisory-tests-")
os.environ["USE_REAL_LLM"] = "false"
os.environ["RETRIEVAL_BACKEND"] = "mock"
os.environ["AUTH_ENABLED"] = "false"
os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp, "test.db").replace("\\", "/")
os.environ["QDRANT_URL"] = ""
os.environ["NEO4J_URI"] = ""
