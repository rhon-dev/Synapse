"""MongoDB connection layer using Motor (async driver).

Lazy connection model — the client is created the first time `get_db()`
runs inside a request handler, not at app startup. Suits serverless
(Vercel/Lambda) where lifespan startup hooks are unreliable and a
failing ping at boot would kill every endpoint, including ones that
never touch the DB (e.g. /healthz).
"""
import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def _build_client() -> tuple[AsyncIOMotorClient, AsyncIOMotorDatabase]:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "synapse")
    is_srv = mongo_uri.startswith("mongodb+srv://")
    timeout_ms = 15000 if is_srv else 5000
    client: AsyncIOMotorClient = AsyncIOMotorClient(
        mongo_uri,
        serverSelectionTimeoutMS=timeout_ms,
        appname="synapse",
    )
    db: AsyncIOMotorDatabase = client[db_name]
    return client, db


async def connect_to_mongo() -> None:
    """No-op shim retained for backwards compatibility. Connection is lazy."""
    return None


async def close_mongo_connection() -> None:
    """Close client. Best-effort — may be skipped under serverless."""
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


def get_db() -> AsyncIOMotorDatabase:
    """Return active DB handle, lazily creating it on first call.

    Connection ping is NOT performed here — failures surface on the
    first real query with proper Motor exceptions. Prevents lifespan
    startup from killing the whole app under serverless.
    """
    global _client, _db
    if _db is None:
        _client, _db = _build_client()
    return _db


def get_events_collection():
    return get_db().events
