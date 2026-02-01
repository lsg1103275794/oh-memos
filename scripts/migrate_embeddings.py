"""
Embedding Migration Script for MemOS
=====================================
When switching embedding models (e.g., nomic-embed-text -> BGE-M3),
this script re-embeds all existing memories and updates both Qdrant and Neo4j.

Usage:
    python scripts/migrate_embeddings.py

    # Dry run (preview without writing):
    python scripts/migrate_embeddings.py --dry-run

    # Custom batch size:
    python scripts/migrate_embeddings.py --batch-size 50
"""

import argparse
import os
import sys
import time

from pathlib import Path

import httpx


# ============================================================
# Configuration - reads from .env or uses defaults
# ============================================================

# Neo4j
NEO4J_HTTP_URL = os.environ.get("NEO4J_HTTP_URL", "http://localhost:7474/db/neo4j/tx/commit")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "12345678")

# Qdrant
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

# Embedding API
EMBED_API_BASE = os.environ.get("MOS_EMBEDDER_API_BASE", "https://api.siliconflow.cn/v1")
EMBED_API_KEY = os.environ.get("MOS_EMBEDDER_API_KEY", "")
EMBED_MODEL = os.environ.get("MOS_EMBEDDER_MODEL", "BAAI/bge-m3")
EMBED_DIM = int(os.environ.get("EMBEDDING_DIMENSION", "1024"))

# Qdrant collections to migrate
COLLECTIONS = ["dev_cube", "dev_cube_graph"]


def neo4j_query(statement: str, parameters: dict = None) -> list:
    """Execute a Neo4j query via HTTP API."""
    body = {"statements": [{"statement": statement}]}
    if parameters:
        body["statements"][0]["parameters"] = parameters

    resp = httpx.post(
        NEO4J_HTTP_URL,
        json=body,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    errors = data.get("errors", [])
    if errors:
        raise RuntimeError(f"Neo4j error: {errors}")

    results = data.get("results", [{}])[0]
    columns = results.get("columns", [])
    rows = []
    for row_data in results.get("data", []):
        row = dict(zip(columns, row_data.get("row", [])))
        rows.append(row)
    return rows


def get_all_memories() -> list[dict]:
    """Fetch all Memory nodes from Neo4j."""
    rows = neo4j_query("""
        MATCH (n:Memory)
        WHERE n.memory IS NOT NULL AND n.memory <> ''
        RETURN n.id AS id, n.memory AS memory,
               n.memory_type AS memory_type, n.status AS status,
               n.user_name AS user_name, n.key AS key,
               n.confidence AS confidence, n.tags AS tags,
               n.background AS background,
               n.created_at AS created_at, n.updated_at AS updated_at
        ORDER BY n.created_at
    """)
    return rows


def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Call embedding API to get vectors. Handles batching."""
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = httpx.post(
            f"{EMBED_API_BASE}/embeddings",
            headers={
                "Authorization": f"Bearer {EMBED_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": EMBED_MODEL, "input": batch},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        batch_embeddings = [item["embedding"] for item in data["data"]]
        all_embeddings.extend(batch_embeddings)

        if i + batch_size < len(texts):
            time.sleep(0.5)  # Rate limiting

    return all_embeddings


def recreate_qdrant_collection(collection_name: str):
    """Delete and recreate a Qdrant collection with new dimension."""
    # Delete if exists
    resp = httpx.delete(f"{QDRANT_URL}/collections/{collection_name}", timeout=30)
    if resp.status_code == 200:
        print(f"  Deleted old collection: {collection_name}")
    else:
        print(f"  Collection {collection_name} not found, creating fresh")

    # Create with new dimension
    resp = httpx.put(
        f"{QDRANT_URL}/collections/{collection_name}",
        json={
            "vectors": {
                "size": EMBED_DIM,
                "distance": "Cosine",
            },
        },
        timeout=30,
    )
    resp.raise_for_status()
    print(f"  Created collection: {collection_name} (dim={EMBED_DIM})")

    # Create payload indexes
    for field in ["memory_type", "status", "user_name", "vector_sync"]:
        httpx.put(
            f"{QDRANT_URL}/collections/{collection_name}/index",
            json={"field_name": field, "field_schema": "keyword"},
            timeout=30,
        )


def upsert_qdrant_batch(collection_name: str, points: list[dict]):
    """Upsert points to Qdrant collection."""
    resp = httpx.put(
        f"{QDRANT_URL}/collections/{collection_name}/points",
        json={"points": points},
        timeout=120,
    )
    resp.raise_for_status()


def update_neo4j_embeddings(nodes: list[dict]):
    """Update embedding field on Neo4j Memory nodes (batch)."""
    neo4j_query(
        """
        UNWIND $nodes AS node
        MATCH (n:Memory {id: node.id})
        SET n.vector_sync = 'success'
        """,
        parameters={"nodes": [{"id": n["id"]} for n in nodes]},
    )


def main():
    parser = argparse.ArgumentParser(description="Migrate MemOS embeddings to new model")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size")
    parser.add_argument("--collection", type=str, default=None, help="Migrate specific collection only")
    args = parser.parse_args()

    collections = [args.collection] if args.collection else COLLECTIONS

    print("=" * 60)
    print("MemOS Embedding Migration")
    print("=" * 60)
    print(f"  Embedding model:  {EMBED_MODEL}")
    print(f"  Vector dimension: {EMBED_DIM}")
    print(f"  API base:         {EMBED_API_BASE}")
    print(f"  Collections:      {collections}")
    print(f"  Dry run:          {args.dry_run}")
    print()

    # Step 1: Fetch all memories from Neo4j
    print("[1/5] Fetching memories from Neo4j...")
    memories = get_all_memories()
    print(f"  Found {len(memories)} memory nodes")

    if not memories:
        print("  No memories to migrate. Done!")
        return

    # Step 2: Test embedding API
    print("\n[2/5] Testing embedding API...")
    try:
        test_result = embed_texts(["test"], batch_size=1)
        actual_dim = len(test_result[0])
        print(f"  API OK, actual dimension: {actual_dim}")
        if actual_dim != EMBED_DIM:
            print(f"  WARNING: Expected dim={EMBED_DIM}, got dim={actual_dim}")
            print(f"  Updating to actual dimension: {actual_dim}")
            global EMBED_DIM
            EMBED_DIM = actual_dim
    except Exception as e:
        print(f"  ERROR: Embedding API failed: {e}")
        sys.exit(1)

    if args.dry_run:
        print(f"\n[DRY RUN] Would re-embed {len(memories)} memories")
        print(f"[DRY RUN] Would recreate collections: {collections}")
        print("[DRY RUN] No changes made.")
        return

    # Step 3: Recreate Qdrant collections
    print("\n[3/5] Recreating Qdrant collections...")
    for col in collections:
        recreate_qdrant_collection(col)

    # Step 4: Re-embed all memories
    print(f"\n[4/5] Re-embedding {len(memories)} memories...")
    texts = [m["memory"] for m in memories]
    embeddings = embed_texts(texts, batch_size=args.batch_size)
    print(f"  Generated {len(embeddings)} embeddings")

    # Step 5: Upsert to Qdrant + update Neo4j
    print("\n[5/5] Writing to Qdrant and Neo4j...")
    for col in collections:
        points = []
        for mem, emb in zip(memories, embeddings):
            payload = {
                "memory": mem["memory"],
                "vector_sync": "success",
                "memory_type": mem.get("memory_type", ""),
                "status": mem.get("status", "activated"),
                "user_name": mem.get("user_name", "dev_user"),
                "key": mem.get("key", ""),
                "confidence": mem.get("confidence"),
                "tags": mem.get("tags", []),
                "background": mem.get("background", ""),
                "created_at": str(mem.get("created_at", "")),
                "updated_at": str(mem.get("updated_at", "")),
            }
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            points.append({
                "id": mem["id"],
                "vector": emb,
                "payload": payload,
            })

        # Batch upsert (100 per batch)
        for i in range(0, len(points), 100):
            batch = points[i:i + 100]
            upsert_qdrant_batch(col, batch)
            print(f"  [{col}] Upserted {min(i + 100, len(points))}/{len(points)} points")

    # Update Neo4j sync status
    update_neo4j_embeddings(memories)
    print("  Updated Neo4j vector_sync status")

    print("\n" + "=" * 60)
    print("Migration complete!")
    print(f"  Memories migrated: {len(memories)}")
    print(f"  Collections updated: {collections}")
    print(f"  New embedding model: {EMBED_MODEL}")
    print(f"  New dimension: {EMBED_DIM}")
    print("=" * 60)


if __name__ == "__main__":
    # Try to load .env
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key and value and key not in os.environ:
                    os.environ[key] = value

        # Re-read config after loading .env
        EMBED_API_BASE = os.environ.get("MOS_EMBEDDER_API_BASE", EMBED_API_BASE)
        EMBED_API_KEY = os.environ.get("MOS_EMBEDDER_API_KEY", EMBED_API_KEY)
        EMBED_MODEL = os.environ.get("MOS_EMBEDDER_MODEL", EMBED_MODEL)
        EMBED_DIM = int(os.environ.get("EMBEDDING_DIMENSION", str(EMBED_DIM)))

    main()
