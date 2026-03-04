"""
Memory Archiver Module

Automatically archives expired memories (e.g., PROGRESS type after TTL).
Prevents storage bloat while preserving data for potential recovery.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from oh_memos.log import get_logger

if TYPE_CHECKING:
    from neo4j import Driver

logger = get_logger(__name__)


# ─── Configuration ──────────────────────────────────────────────────────────────

def get_archive_config() -> dict:
    """Get archiver configuration from environment."""
    return {
        "enabled": os.getenv("MEMOS_AUTO_ARCHIVE", "true").lower() == "true",
        "ttl_days": int(os.getenv("MEMOS_ARCHIVE_TTL_DAYS", "7")),
        "interval_seconds": int(os.getenv("MEMOS_ARCHIVE_INTERVAL", "3600")),
        "archive_types": [
            t.strip().upper()
            for t in os.getenv("MEMOS_ARCHIVE_TYPES", "PROGRESS").split(",")
            if t.strip()
        ],
    }


# ─── Core Archive Logic ─────────────────────────────────────────────────────────

def archive_expired_memories_sync(
    driver: "Driver",
    ttl_days: int = 7,
    archive_types: list[str] | None = None,
    user_name: str | None = None,
) -> int:
    """
    Archive expired memories by setting status to 'archived'.

    This is a soft delete - memories can be restored later.

    Args:
        driver: Neo4j driver instance
        ttl_days: Days after which memories are archived
        archive_types: Memory types to archive (default: ["PROGRESS"])
        user_name: Optional user filter

    Returns:
        Number of archived memories
    """
    if archive_types is None:
        archive_types = ["PROGRESS"]

    cutoff_date = datetime.now() - timedelta(days=ttl_days)
    cutoff_iso = cutoff_date.isoformat()

    # Build user filter clause
    user_clause = ""
    params = {
        "cutoff": cutoff_iso,
        "archive_types": archive_types,
    }
    if user_name:
        user_clause = "AND n.user_name = $user_name"
        params["user_name"] = user_name

    # Cypher query to archive expired memories
    # We check for memory type in tags (format: [TYPE] content)
    cypher = f"""
    MATCH (n:Memory)
    WHERE n.status = 'activated'
      AND n.created_at < datetime($cutoff)
      AND (
        any(tag IN n.tags WHERE tag IN $archive_types)
        OR any(t IN $archive_types WHERE n.memory STARTS WITH '[' + t + ']')
      )
      {user_clause}
    SET n.status = 'archived',
        n.archived_at = datetime(),
        n.archived_reason = 'TTL_EXPIRED'
    RETURN count(n) as archived_count
    """

    try:
        with driver.session() as session:
            result = session.run(cypher, params)
            record = result.single()
            archived_count = record["archived_count"] if record else 0

            if archived_count > 0:
                logger.info(
                    f"Archived {archived_count} memories "
                    f"(types={archive_types}, ttl={ttl_days}d, user={user_name or 'all'})"
                )

            return archived_count

    except Exception as e:
        logger.error(f"Archive operation failed: {e}")
        return 0


def get_archive_stats_sync(
    driver: "Driver",
    user_name: str | None = None,
) -> dict:
    """
    Get archive statistics.

    Returns:
        Dict with counts by status
    """
    user_clause = ""
    params = {}
    if user_name:
        user_clause = "WHERE n.user_name = $user_name"
        params["user_name"] = user_name

    cypher = f"""
    MATCH (n:Memory)
    {user_clause}
    RETURN n.status as status, count(n) as count
    """

    try:
        with driver.session() as session:
            result = session.run(cypher, params)
            stats = {record["status"]: record["count"] for record in result}
            return stats
    except Exception as e:
        logger.error(f"Failed to get archive stats: {e}")
        return {}


def restore_archived_memory_sync(
    driver: "Driver",
    memory_id: str,
    user_name: str | None = None,
) -> bool:
    """
    Restore an archived memory back to activated status.

    Args:
        driver: Neo4j driver instance
        memory_id: ID of the memory to restore
        user_name: Optional user filter for safety

    Returns:
        True if restored, False otherwise
    """
    user_clause = ""
    params = {"memory_id": memory_id}
    if user_name:
        user_clause = "AND n.user_name = $user_name"
        params["user_name"] = user_name

    cypher = f"""
    MATCH (n:Memory {{id: $memory_id}})
    WHERE n.status = 'archived'
      {user_clause}
    SET n.status = 'activated',
        n.restored_at = datetime()
    RETURN n.id as restored_id
    """

    try:
        with driver.session() as session:
            result = session.run(cypher, params)
            record = result.single()
            if record:
                logger.info(f"Restored memory {memory_id}")
                return True
            return False
    except Exception as e:
        logger.error(f"Failed to restore memory {memory_id}: {e}")
        return False


# ─── Background Task ────────────────────────────────────────────────────────────

async def periodic_archive_task(
    get_driver_func,
    interval_seconds: int | None = None,
    ttl_days: int | None = None,
    archive_types: list[str] | None = None,
):
    """
    Background task that periodically archives expired memories.

    Args:
        get_driver_func: Callable that returns a Neo4j driver
        interval_seconds: Override interval from config
        ttl_days: Override TTL from config
        archive_types: Override types from config
    """
    config = get_archive_config()

    if not config["enabled"]:
        logger.info("Auto-archive is disabled")
        return

    interval = interval_seconds or config["interval_seconds"]
    ttl = ttl_days or config["ttl_days"]
    types = archive_types or config["archive_types"]

    logger.info(
        f"Starting periodic archive task "
        f"(interval={interval}s, ttl={ttl}d, types={types})"
    )

    while True:
        try:
            # Wait for interval first (let system stabilize on startup)
            await asyncio.sleep(interval)

            # Get driver and run archive
            driver = get_driver_func()
            if driver:
                archived = archive_expired_memories_sync(
                    driver,
                    ttl_days=ttl,
                    archive_types=types,
                )
                if archived > 0:
                    logger.info(f"Periodic archive completed: {archived} memories archived")
            else:
                logger.warning("Archive skipped: no driver available")

        except asyncio.CancelledError:
            logger.info("Archive task cancelled")
            break
        except Exception as e:
            logger.error(f"Archive task error: {e}")
            # Continue running despite errors
            await asyncio.sleep(60)  # Short delay before retry
