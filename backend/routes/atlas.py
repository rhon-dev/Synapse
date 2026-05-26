"""Atlas Admin API v2 read-only endpoints.

These are thin pass-through wrappers around `backend.services.atlas`.
Returns the raw Atlas JSON payload — no transformation — so the
frontend (or any caller) gets the official Atlas schema unchanged.
"""
from fastapi import APIRouter, Path

from backend.services import atlas

router = APIRouter(prefix="/atlas", tags=["atlas"])


@router.get("/projects")
async def get_projects() -> dict:
    """List all projects accessible by the configured API key."""
    return await atlas.list_projects()


@router.get("/project")
async def get_current_project() -> dict:
    """Get the project identified by ATLAS_PROJECT_ID."""
    return await atlas.get_project()


@router.get("/clusters")
async def get_clusters() -> dict:
    """List clusters in the configured project."""
    return await atlas.list_clusters()


@router.get("/clusters/{cluster_name}")
async def get_cluster(
    cluster_name: str = Path(..., min_length=1, max_length=64),
) -> dict:
    return await atlas.get_cluster(cluster_name)


@router.get("/database-users")
async def get_database_users() -> dict:
    return await atlas.list_database_users()


@router.get("/network-access")
async def get_network_access() -> dict:
    return await atlas.list_network_access()


@router.get("/orgs/{org_id}")
async def get_organization(
    org_id: str = Path(..., min_length=24, max_length=24),
) -> dict:
    return await atlas.get_organization(org_id)
