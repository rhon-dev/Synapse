"""MongoDB connection layer using Motor (async driver)."""
import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> None:
    """Open client connection. Called on FastAPI startup."""
    global _client, _db
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "synapse")

    client: AsyncIOMotorClient = AsyncIOMotorClient(
        mongo_uri, serverSelectionTimeoutMS=5000
    )
    db: AsyncIOMotorDatabase = client[db_name]

    # Force handshake so failures surface at startup not first request
    await client.admin.command("ping")
    # Index for fast per-session lookups
    await db.events.create_index([("session_id", 1), ("timestamp", 1)])

    _client = client
    _db = db


async def close_mongo_connection() -> None:
    """Close client. Called on FastAPI shutdown."""
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


def get_db() -> AsyncIOMotorDatabase:
    """Return active DB handle. Raise if not connected."""
    if _db is None:
        raise RuntimeError("MongoDB not connected. Call connect_to_mongo() first.")
    return _db


def get_events_collection():
    return get_db().events
