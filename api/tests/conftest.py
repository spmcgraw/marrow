"""Pytest config — runs before any test module imports."""

import os

# Tests exercise unauthenticated paths and toggle OIDC/API_KEY per-test.
# The app's startup guard would otherwise refuse to import when both are unset.
os.environ.setdefault("MARROW_ALLOW_ANONYMOUS", "true")
