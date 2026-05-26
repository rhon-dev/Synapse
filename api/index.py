"""Vercel serverless entrypoint.

Vercel's @vercel/python builder looks for files under /api and exposes them
as serverless functions. For ASGI apps (FastAPI), the builder detects the
`app` callable and runs it through an ASGI shim.

We re-export the FastAPI app defined in backend/main.py so Vercel can find
it without restructuring the project. All routes, lifespan hooks, and
static mounts defined on the original app continue to work — except the
StaticFiles mount, which is shadowed on Vercel by static routes defined
in vercel.json (frontend files are served by Vercel's CDN, not by the
Python function).
"""
from backend.main import app  # noqa: F401  (re-exported for Vercel)
