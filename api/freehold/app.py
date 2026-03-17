"""FastAPI application factory."""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .dependencies import verify_api_key
from .routers import collections, pages, pages_global, spaces, workspaces

# Allow the origin list to be overridden via env var for non-local deployments.
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app = FastAPI(title="Freehold API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Apply API key auth to every route via include_router's dependencies parameter.
_auth = [Depends(verify_api_key)]

app.include_router(workspaces.router, dependencies=_auth)
app.include_router(spaces.router, dependencies=_auth)
app.include_router(collections.router, dependencies=_auth)
app.include_router(pages.router, dependencies=_auth)
app.include_router(pages_global.router, dependencies=_auth)


@app.get("/health")
def health():
    return {"status": "ok"}
