import os
import sys


# Ensure the project root is on sys.path when running in CI.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Provide defaults so module-level clients can initialize in tests.
os.environ.setdefault("ALPHAVANTAGE_API_KEY", "test_api_key")
os.environ.setdefault("ALPHAVANTAGE_BASE_URL", "https://example.com")
