"""FastAPI application factory."""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .dependencies import verify_auth
from .routers import auth, collections, organizations, pages, pages_global, spaces, workspaces

# Allow the origin list to be overridden via env var for non-local deployments.
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

_secret_key = os.getenv("SECRET_KEY", "changeme")

app = FastAPI(title="Marrow API", version="0.1.0")

# SessionMiddleware is required by authlib for OAuth state management.
app.add_middleware(SessionMiddleware, secret_key=_secret_key)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth router is registered WITHOUT the global auth dependency so that
# unauthenticated users can initiate the login flow.
app.include_router(auth.router)

# All other routers require authentication.
_auth = [Depends(verify_auth)]

app.include_router(organizations.router, dependencies=_auth)
app.include_router(workspaces.router, dependencies=_auth)
app.include_router(spaces.router, dependencies=_auth)
app.include_router(collections.router, dependencies=_auth)
app.include_router(pages.router, dependencies=_auth)
app.include_router(pages_global.router, dependencies=_auth)


@app.get("/health")
def health():
    return {"status": "ok"}
