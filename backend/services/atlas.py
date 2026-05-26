"""MongoDB Atlas Admin API v2 client.

Async wrapper around https://cloud.mongodb.com/api/atlas/v2.
Auth: HTTP Digest using a Programmatic API Key
      (Atlas → Access Manager → API Keys → Create).

Reads from env vars at first use (no client created until needed):
  ATLAS_API_BASE_URL     default https://cloud.mongodb.com/api/atlas/v2
  ATLAS_API_PUBLIC_KEY
  ATLAS_API_PRIVATE_KEY
  ATLAS_PROJECT_ID       24-char hex (the group ID)
  ATLAS_API_VERSION      default 2025-03-12 (sent in Accept header)
"""
from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from fastapi import HTTPException, status

_DEFAULT_BASE = "https://cloud.mongodb.com/api/atlas/v2"
_DEFAULT_API_VERSION = "2025-03-12"

_client: Optional[httpx.AsyncClient] = None


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val or val.startswith("your_") or val == "changeme":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Env var {name} not configured. See README → Atlas setup.",
        )
    return val


def get_project_id() -> str:
    return _require_env("ATLAS_PROJECT_ID")


def _get_client() -> httpx.AsyncClient:
    """Lazy singleton httpx client with Digest auth + Atlas Accept header."""
    global _client
    if _client is None:
        public = _require_env("ATLAS_API_PUBLIC_KEY")
        private = _require_env("ATLAS_API_PRIVATE_KEY")
        base = os.getenv("ATLAS_API_BASE_URL", _DEFAULT_BASE).rstrip("/")
        api_version = os.getenv("ATLAS_API_VERSION", _DEFAULT_API_VERSION)
        _client = httpx.AsyncClient(
            base_url=base,
            auth=httpx.DigestAuth(public, private),
            headers={
                "Accept": f"application/vnd.atlas.{api_version}+json",
                "Content-Type": f"application/vnd.atlas.{api_version}+json",
                "User-Agent": "Synapse/1.0 (+atlas-admin-api)",
            },
            timeout=20.0,
        )
    return _client


async def close_atlas_client() -> None:
    """Called on FastAPI shutdown to close the httpx pool."""
    global _client
    if _client is not None:
        await _client.aclose()
    _client = None


# ----------------------------------------------------------------------
# Generic request helper — maps httpx errors → HTTPException
# ----------------------------------------------------------------------

async def _request(method: str, path: str, **kwargs: Any) -> Any:
    client = _get_client()
    try:
        resp = await client.request(method, path, **kwargs)
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Atlas API timed out: {exc}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Atlas API connection error: {exc}",
        ) from exc

    if resp.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Atlas authentication failed. Check ATLAS_API_PUBLIC_KEY / PRIVATE_KEY.",
        )
    if resp.status_code == 403:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Atlas API key lacks permission for this operation.",
        )
    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Atlas resource not found: {path}",
        )
    if resp.status_code >= 400:
        # Surface Atlas's own error payload when present
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Atlas API error {resp.status_code}: {body}",
        )

    if resp.status_code == 204 or not resp.content:
        return None
    try:
        return resp.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Atlas returned non-JSON body: {exc}",
        ) from exc


# ----------------------------------------------------------------------
# Public API surface — narrow subset of Atlas Admin API v2.
# Extend as needed; the _request helper handles auth/headers/errors.
# ----------------------------------------------------------------------

async def list_projects() -> dict:
    """GET /groups — all projects the API key can see."""
    return await _request("GET", "/groups")


async def get_project(project_id: Optional[str] = None) -> dict:
    """GET /groups/{groupId}"""
    pid = project_id or get_project_id()
    return await _request("GET", f"/groups/{pid}")


async def list_clusters(project_id: Optional[str] = None) -> dict:
    """GET /groups/{groupId}/clusters — list cluster summaries."""
    pid = project_id or get_project_id()
    return await _request("GET", f"/groups/{pid}/clusters")


async def get_cluster(cluster_name: str, project_id: Optional[str] = None) -> dict:
    """GET /groups/{groupId}/clusters/{clusterName}"""
    pid = project_id or get_project_id()
    return await _request("GET", f"/groups/{pid}/clusters/{cluster_name}")


async def list_database_users(project_id: Optional[str] = None) -> dict:
    """GET /groups/{groupId}/databaseUsers"""
    pid = project_id or get_project_id()
    return await _request("GET", f"/groups/{pid}/databaseUsers")


async def list_network_access(project_id: Optional[str] = None) -> dict:
    """GET /groups/{groupId}/accessList — IP allowlist entries."""
    pid = project_id or get_project_id()
    return await _request("GET", f"/groups/{pid}/accessList")


async def get_organization(org_id: str) -> dict:
    """GET /orgs/{orgId}"""
    return await _request("GET", f"/orgs/{org_id}")
