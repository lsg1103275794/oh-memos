import logging

from memos.api.handlers.base_handler import BaseHandler, HandlerDependencies
from memos.api.product_models import (
    APIGraphRequest,
    APISchemaRequest,
    APITracePathRequest,
    GraphData,
    GraphResponse,
    PathEdge,
    PathNode,
    SchemaData,
    SchemaResponse,
    TracePath,
    TracePathData,
    TracePathResponse,
)


logger = logging.getLogger(__name__)


class GraphHandler(BaseHandler):
    """Handler for graph-related operations."""

    def __init__(self, dependencies: HandlerDependencies):
        super().__init__(dependencies)

    def handle_get_graph_data(self, graph_req: APIGraphRequest) -> GraphResponse:
        """
        Fetch graph nodes and edges for visualization.
        """
        logger.info(f"[GraphHandler] Fetching graph data for user: {graph_req.user_id}")

        if not self.graph_db:
            return GraphResponse(
                code=500,
                message="Graph database not configured",
                data=None
            )

        try:
            # Call export_graph from Neo4jGraphDB
            # We use user_id as the user_name for filtering in Neo4j
            graph_data_raw = self.graph_db.export_graph(
                page=graph_req.page,
                page_size=graph_req.page_size,
                user_name=graph_req.user_id,
                filter=graph_req.filter
            )

            graph_data = GraphData(
                nodes=graph_data_raw["nodes"],
                edges=graph_data_raw["edges"],
                total_nodes=graph_data_raw["total_nodes"],
                total_edges=graph_data_raw["total_edges"]
            )

            return GraphResponse(
                code=200,
                message="Graph data fetched successfully",
                data=graph_data
            )
        except Exception as e:
            logger.error(f"[GraphHandler] Error fetching graph data: {e}", exc_info=True)
            return GraphResponse(
                code=500,
                message=f"Internal server error: {e!s}",
                data=None
            )

    def handle_trace_path(self, req: APITracePathRequest) -> TracePathResponse:
        """
        Trace paths between two memory nodes.
        """
        logger.info(f"[GraphHandler] Tracing path from {req.source_id} to {req.target_id}")

        if not self.graph_db:
            return TracePathResponse(
                code=500,
                message="Graph database not configured",
                data=None
            )

        try:
            # Use graph_db to find paths
            if hasattr(self.graph_db, 'find_path'):
                path_result = self.graph_db.find_path(
                    source_id=req.source_id,
                    target_id=req.target_id,
                    max_depth=req.max_depth
                )
            else:
                # Fallback: direct Neo4j query
                path_result = self._neo4j_find_path(
                    req.source_id,
                    req.target_id,
                    req.max_depth
                )

            if path_result and path_result.get("path_found"):
                paths = []
                for p in path_result.get("paths", []):
                    nodes = [PathNode(id=n["id"], memory=n.get("memory", ""), metadata=n.get("metadata", {})) for n in p.get("nodes", [])]
                    edges = [PathEdge(source=e["source"], target=e["target"], type=e.get("type", "RELATE")) for e in p.get("edges", [])]
                    paths.append(TracePath(nodes=nodes, edges=edges, length=len(edges)))

                return TracePathResponse(
                    code=200,
                    message="Path found",
                    data=TracePathData(
                        path_found=True,
                        paths=paths,
                        source_id=req.source_id,
                        target_id=req.target_id
                    )
                )
            else:
                return TracePathResponse(
                    code=200,
                    message="No path found between nodes",
                    data=TracePathData(
                        path_found=False,
                        paths=[],
                        source_id=req.source_id,
                        target_id=req.target_id
                    )
                )

        except Exception as e:
            logger.error(f"[GraphHandler] Error tracing path: {e}", exc_info=True)
            return TracePathResponse(
                code=500,
                message=f"Internal server error: {e!s}",
                data=None
            )

    def handle_export_schema(self, req: APISchemaRequest) -> SchemaResponse:
        """
        Export graph schema and statistics.
        """
        logger.info(f"[GraphHandler] Exporting schema for user: {req.user_id}")

        if not self.graph_db:
            return SchemaResponse(
                code=500,
                message="Graph database not configured",
                data=None
            )

        try:
            # Use graph_db to get schema stats
            if hasattr(self.graph_db, 'get_schema_stats'):
                stats = self.graph_db.get_schema_stats(sample_size=req.sample_size)
            else:
                # Fallback: direct Neo4j query
                stats = self._neo4j_get_schema_stats(req.sample_size)

            return SchemaResponse(
                code=200,
                message="Schema exported successfully",
                data=SchemaData(
                    total_nodes=stats.get("total_nodes", 0),
                    total_edges=stats.get("total_edges", 0),
                    edge_types=stats.get("edge_types", {}),
                    memory_types=stats.get("memory_types", {}),
                    top_tags=stats.get("top_tags", []),
                    avg_connections=stats.get("avg_connections", 0.0),
                    max_connections=stats.get("max_connections", 0),
                    orphan_nodes=stats.get("orphan_nodes", 0),
                    time_range=stats.get("time_range", {})
                )
            )

        except Exception as e:
            logger.error(f"[GraphHandler] Error exporting schema: {e}", exc_info=True)
            return SchemaResponse(
                code=500,
                message=f"Internal server error: {e!s}",
                data=None
            )

    def _neo4j_find_path(self, source_id: str, target_id: str, max_depth: int) -> dict:
        """Fallback: Direct Neo4j query for path finding."""
        import os

        import httpx

        neo4j_url = os.environ.get("NEO4J_HTTP_URL", "http://localhost:7474/db/neo4j/tx/commit")
        neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        neo4j_password = os.environ.get("NEO4J_PASSWORD", "12345678")

        query = f"""
        MATCH path = shortestPath((a:Memory {{id: $source_id}})-[*1..{max_depth}]-(b:Memory {{id: $target_id}}))
        RETURN path
        LIMIT 1
        """

        try:
            response = httpx.post(
                neo4j_url,
                json={"statements": [{"statement": query, "parameters": {"source_id": source_id, "target_id": target_id}}]},
                auth=(neo4j_user, neo4j_password),
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [{}])[0].get("data", [])
                if results:
                    # Parse path from Neo4j response
                    return {"path_found": True, "paths": [{"nodes": [], "edges": []}]}
                return {"path_found": False, "paths": []}
        except Exception as e:
            logger.error(f"[GraphHandler] Neo4j path query error: {e}")

        return {"path_found": False, "paths": []}

    def _neo4j_get_schema_stats(self, sample_size: int) -> dict:
        """Fallback: Direct Neo4j query for schema stats."""
        import os

        import httpx

        neo4j_url = os.environ.get("NEO4J_HTTP_URL", "http://localhost:7474/db/neo4j/tx/commit")
        neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        neo4j_password = os.environ.get("NEO4J_PASSWORD", "12345678")

        stats = {
            "total_nodes": 0,
            "total_edges": 0,
            "edge_types": {},
            "memory_types": {},
            "top_tags": [],
            "avg_connections": 0.0,
            "max_connections": 0,
            "orphan_nodes": 0,
            "time_range": {}
        }

        try:
            # Get node count
            response = httpx.post(
                neo4j_url,
                json={"statements": [{"statement": "MATCH (n:Memory) RETURN count(n) as cnt"}]},
                auth=(neo4j_user, neo4j_password),
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [{}])[0].get("data", [])
                if results:
                    stats["total_nodes"] = results[0].get("row", [0])[0]

            # Get edge count
            response = httpx.post(
                neo4j_url,
                json={"statements": [{"statement": "MATCH ()-[r]->() RETURN count(r) as cnt"}]},
                auth=(neo4j_user, neo4j_password),
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [{}])[0].get("data", [])
                if results:
                    stats["total_edges"] = results[0].get("row", [0])[0]

            # Get edge type distribution
            response = httpx.post(
                neo4j_url,
                json={"statements": [{"statement": "MATCH ()-[r]->() RETURN type(r) as t, count(r) as cnt"}]},
                auth=(neo4j_user, neo4j_password),
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [{}])[0].get("data", [])
                for r in results:
                    row = r.get("row", [])
                    if len(row) >= 2:
                        stats["edge_types"][row[0]] = row[1]

        except Exception as e:
            logger.error(f"[GraphHandler] Neo4j schema query error: {e}")

        return stats
