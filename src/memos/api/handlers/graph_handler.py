import logging
from typing import Any

from memos.api.handlers.base_handler import BaseHandler, HandlerDependencies
from memos.api.product_models import (
    APIGraphRequest,
    GraphData,
    GraphResponse,
    GraphSchemaData,
    GraphSchemaRequest,
    GraphSchemaResponse,
    PathDetail,
    PathEdge,
    PathNode,
    SchemaRelationPattern,
    TracePathData,
    TracePathRequest,
    TracePathResponse,
)


logger = logging.getLogger(__name__)


class GraphHandler(BaseHandler):
    """Handler for graph-related operations."""

    def __init__(self, dependencies: HandlerDependencies):
        super().__init__(dependencies)
        self.graph_db = dependencies.graph_db

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
                message=f"Internal server error: {str(e)}",
                data=None
            )

    def handle_trace_path(self, trace_req: TracePathRequest) -> TracePathResponse:
        """
        Trace paths between two memory nodes in the knowledge graph.

        This enables reasoning about how memories are connected, useful for:
        - Understanding causality chains
        - Finding indirect relationships
        - Exploring memory dependencies
        """
        logger.info(
            f"[GraphHandler] Tracing path from {trace_req.source_id[:8]}... "
            f"to {trace_req.target_id[:8]}... for user: {trace_req.user_id}"
        )

        if not self.graph_db:
            return TracePathResponse(
                code=500,
                message="Graph database not configured",
                data=None
            )

        try:
            # Check if graph_db has trace_path method
            if not hasattr(self.graph_db, "trace_path"):
                return TracePathResponse(
                    code=501,
                    message="trace_path not implemented for this graph database",
                    data=None
                )

            # Call trace_path from Neo4jGraphDB
            result = self.graph_db.trace_path(
                source_id=trace_req.source_id,
                target_id=trace_req.target_id,
                max_depth=trace_req.max_depth,
                user_name=trace_req.user_id,
                include_all_paths=trace_req.include_all_paths,
            )

            # Convert to response models
            paths = []
            for path_data in result.get("paths", []):
                nodes = [
                    PathNode(
                        id=n["id"],
                        memory=n.get("memory", ""),
                        metadata=n.get("metadata", {}),
                    )
                    for n in path_data.get("nodes", [])
                ]
                edges = [
                    PathEdge(
                        source=e["source"],
                        target=e["target"],
                        type=e["type"],
                    )
                    for e in path_data.get("edges", [])
                ]
                paths.append(PathDetail(
                    length=path_data.get("length", 0),
                    nodes=nodes,
                    edges=edges,
                ))

            source_node = None
            if result.get("source"):
                source_node = PathNode(
                    id=result["source"]["id"],
                    memory=result["source"].get("memory", ""),
                )

            target_node = None
            if result.get("target"):
                target_node = PathNode(
                    id=result["target"]["id"],
                    memory=result["target"].get("memory", ""),
                )

            trace_data = TracePathData(
                found=result.get("found", False),
                paths=paths,
                source=source_node,
                target=target_node,
            )

            return TracePathResponse(
                code=200,
                message="Path traced successfully" if trace_data.found else "No path found",
                data=trace_data,
            )

        except Exception as e:
            logger.error(f"[GraphHandler] Error tracing path: {e}", exc_info=True)
            return TracePathResponse(
                code=500,
                message=f"Internal server error: {str(e)}",
                data=None,
            )

    def handle_get_schema(self, schema_req: GraphSchemaRequest) -> GraphSchemaResponse:
        """
        Export graph schema information for understanding the knowledge structure.

        This provides:
        - Statistics on node types and counts
        - Relationship type distribution
        - Tag frequency
        - Connectivity statistics
        - Time range of data
        """
        logger.info(f"[GraphHandler] Exporting graph schema for user: {schema_req.user_id}")

        if not self.graph_db:
            return GraphSchemaResponse(
                code=500,
                message="Graph database not configured",
                data=None
            )

        try:
            # Check if graph_db has get_schema_statistics method
            if hasattr(self.graph_db, "get_schema_statistics"):
                stats = self.graph_db.get_schema_statistics(
                    user_name=schema_req.user_id,
                    sample_size=schema_req.sample_size,
                )
            else:
                # Fallback to basic export_graph
                graph_data = self.graph_db.export_graph(
                    page=1,
                    page_size=schema_req.sample_size,
                    user_name=schema_req.user_id,
                )
                stats = {
                    "total_nodes": graph_data.get("total_nodes", 0),
                    "total_edges": graph_data.get("total_edges", 0),
                    "edge_type_distribution": {},
                    "memory_type_distribution": {},
                    "tag_frequency": {},
                    "avg_connections_per_node": 0.0,
                    "max_connections": 0,
                    "orphan_node_count": 0,
                    "time_range": {"earliest": None, "latest": None},
                }
                # Compute edge type distribution from edges
                for edge in graph_data.get("edges", []):
                    edge_type = edge.get("type", "UNKNOWN")
                    stats["edge_type_distribution"][edge_type] = (
                        stats["edge_type_distribution"].get(edge_type, 0) + 1
                    )

            # Generate relationship patterns from edge distribution
            patterns = []
            for edge_type, count in sorted(
                stats.get("edge_type_distribution", {}).items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                frequency = "high" if count > 10 else "medium" if count > 3 else "low"
                patterns.append(SchemaRelationPattern(
                    pattern=f"Memory -[{edge_type}]-> Memory",
                    frequency=frequency,
                ))

            schema_data = GraphSchemaData(
                entity_types=[],  # Would need LLM analysis for meaningful types
                relationship_patterns=patterns,
                total_nodes=stats.get("total_nodes", 0),
                total_edges=stats.get("total_edges", 0),
                edge_type_distribution=stats.get("edge_type_distribution", {}),
                memory_type_distribution=stats.get("memory_type_distribution", {}),
                tag_frequency=stats.get("tag_frequency", {}),
                avg_connections_per_node=stats.get("avg_connections_per_node", 0.0),
                max_connections=stats.get("max_connections", 0),
                orphan_node_count=stats.get("orphan_node_count", 0),
                time_range=stats.get("time_range", {"earliest": None, "latest": None}),
            )

            return GraphSchemaResponse(
                code=200,
                message="Graph schema exported successfully",
                data=schema_data,
            )

        except Exception as e:
            logger.error(f"[GraphHandler] Error exporting schema: {e}", exc_info=True)
            return GraphSchemaResponse(
                code=500,
                message=f"Internal server error: {str(e)}",
                data=None,
            )
