"""Uvicorn entry point.

Run from the api/ directory:
    uvicorn main:app --reload
"""

from marrow.app import app  # noqa: F401  re-exported for uvicorn
