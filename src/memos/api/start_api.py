import logging
import os
import warnings

from typing import Any, Generic, TypeVar

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from memos.api.product_models import (
    APIGraphRequest,
    GraphData,
    GraphEdge,
    GraphNode,
    GraphResponse,
    TracePathRequest,
    TracePathResponse,
    TracePathData,
    PathNode,
    PathEdge,
    PathDetail,
    GraphSchemaRequest,
    GraphSchemaResponse,
    GraphSchemaData,
    SchemaRelationPattern,
)
from memos.api.handlers.graph_handler import GraphHandler, HandlerDependencies

from memos.api.config import APIConfig
from memos.api.middleware.request_context import RequestContextMiddleware
from memos.configs.mem_os import MOSConfig
from memos.mem_os.main import MOS
from memos.mem_user.user_manager import UserManager, UserRole

# Suppress harmless warnings
warnings.filterwarnings("ignore", message=".*PyTorch.*TensorFlow.*Flax.*")
warnings.filterwarnings("ignore", message=".*PydanticSerializationUnexpectedValue.*")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

T = TypeVar("T")

# Use product default config which includes mem_reader
DEFAULT_CONFIG = APIConfig.get_product_default_config()

# Initialize MOS instance with lazy initialization
MOS_INSTANCE = None


def get_mos_instance():
    """Get or create MOS instance with default user creation."""
    global MOS_INSTANCE
    if MOS_INSTANCE is None:
        # Create a temporary MOS instance to access user manager
        temp_config = MOSConfig(**DEFAULT_CONFIG)
        temp_mos = MOS.__new__(MOS)
        temp_mos.config = temp_config
        temp_mos.user_id = temp_config.user_id
        temp_mos.session_id = temp_config.session_id
        temp_mos.mem_cubes = {}
        temp_mos.chat_llm = None  # Will be initialized later
        temp_mos.user_manager = UserManager()

        # Create default user if it doesn't exist
        if not temp_mos.user_manager.validate_user(temp_config.user_id):
            temp_mos.user_manager.create_user(
                user_name=temp_config.user_id, role=UserRole.USER, user_id=temp_config.user_id
            )
            logger.info(f"Created default user: {temp_config.user_id}")

        # Now create the actual MOS instance
        MOS_INSTANCE = MOS(config=temp_config)

    return MOS_INSTANCE


app = FastAPI(
    title="MemOS REST APIs",
    description="A REST API for managing and searching memories using MemOS.",
    version="1.0.0",
)

app.add_middleware(RequestContextMiddleware)


class BaseRequest(BaseModel):
    """Base model for all requests."""

    user_id: str | None = Field(
        None, description="User ID for the request", json_schema_extra={"example": "user123"}
    )


class BaseResponse(BaseModel, Generic[T]):
    """Base model for all responses."""

    code: int = Field(200, description="Response status code", json_schema_extra={"example": 200})
    message: str = Field(
        ..., description="Response message", json_schema_extra={"example": "Operation successful"}
    )
    data: T | None = Field(None, description="Response data")


class Message(BaseModel):
    role: str = Field(
        ...,
        description="Role of the message (user or assistant).",
        json_schema_extra={"example": "user"},
    )
    content: str = Field(
        ...,
        description="Message content.",
        json_schema_extra={"example": "Hello, how can I help you?"},
    )


class MemoryCreate(BaseRequest):
    messages: list[Message] | None = Field(
        None,
        description="List of messages to store.",
        json_schema_extra={"example": [{"role": "user", "content": "Hello"}]},
    )
    mem_cube_id: str | None = Field(
        None, description="ID of the memory cube", json_schema_extra={"example": "cube123"}
    )
    memory_content: str | None = Field(
        None,
        description="Content to store as memory",
        json_schema_extra={"example": "This is a memory content"},
    )
    doc_path: str | None = Field(
        None,
        description="Path to document to store",
        json_schema_extra={"example": "/path/to/document.txt"},
    )


class SearchRequest(BaseRequest):
    query: str = Field(
        ...,
        description="Search query.",
        json_schema_extra={"example": "How to implement a feature?"},
    )
    user_id: str | None = Field(
        None,
        description="User ID for the search",
        json_schema_extra={"example": "user123"},
    )
    install_cube_ids: list[str] | None = Field(
        None,
        description="List of cube IDs to search in",
        json_schema_extra={"example": ["cube123", "cube456"]},
    )
    enable_context_analysis: bool = Field(
        False,
        description="Enable LLM-powered context analysis for smarter search",
    )
    chat_history: list[dict] | None = Field(
        None,
        description="Chat history for context-aware search",
        json_schema_extra={"example": [{"role": "user", "content": "debugging login"}]},
    )
    top_k: int = Field(
        10,
        description="Number of results to return",
    )


class MemCubeRegister(BaseRequest):
    mem_cube_name_or_path: str = Field(
        ...,
        description="Name or path of the MemCube to register.",
        json_schema_extra={"example": "/path/to/cube"},
    )
    mem_cube_id: str | None = Field(
        None, description="ID for the MemCube", json_schema_extra={"example": "cube123"}
    )


class ChatRequest(BaseRequest):
    query: str = Field(
        ...,
        description="Chat query message.",
        json_schema_extra={"example": "What is the latest update?"},
    )


class UserCreate(BaseRequest):
    user_name: str | None = Field(
        None, description="Name of the user", json_schema_extra={"example": "john_doe"}
    )
    role: str = Field("user", description="Role of the user", json_schema_extra={"example": "user"})
    user_id: str = Field(..., description="User ID", json_schema_extra={"example": "user123"})


class CubeShare(BaseRequest):
    target_user_id: str = Field(
        ..., description="Target user ID to share with", json_schema_extra={"example": "user456"}
    )


class SimpleResponse(BaseResponse[None]):
    """Simple response model for operations without data return."""


class ConfigResponse(BaseResponse[None]):
    """Response model for configuration endpoint."""


class MemoryResponse(BaseResponse[dict]):
    """Response model for memory operations."""


class SearchResponse(BaseResponse[dict]):
    """Response model for search operations."""


class ChatResponse(BaseResponse[str]):
    """Response model for chat operations."""


class UserResponse(BaseResponse[dict]):
    """Response model for user operations."""


class UserListResponse(BaseResponse[list]):
    """Response model for user list operations."""


@app.post("/configure", summary="Configure MemOS", response_model=ConfigResponse)
async def set_config(config: MOSConfig):
    """Set MemOS configuration."""
    global MOS_INSTANCE

    # Create a temporary user manager to check/create default user
    temp_user_manager = UserManager()

    # Create default user if it doesn't exist
    if not temp_user_manager.validate_user(config.user_id):
        temp_user_manager.create_user(
            user_name=config.user_id, role=UserRole.USER, user_id=config.user_id
        )
        logger.info(f"Created default user: {config.user_id}")

    # Now create the MOS instance
    MOS_INSTANCE = MOS(config=config)
    return ConfigResponse(message="Configuration set successfully")


@app.post("/users", summary="Create a new user", response_model=UserResponse)
async def create_user(user_create: UserCreate):
    """Create a new user."""
    mos_instance = get_mos_instance()
    role = UserRole(user_create.role)
    user_id = mos_instance.create_user(
        user_id=user_create.user_id, role=role, user_name=user_create.user_name
    )
    return UserResponse(message="User created successfully", data={"user_id": user_id})


@app.get("/users", summary="List all users", response_model=UserListResponse)
async def list_users():
    """List all active users."""
    mos_instance = get_mos_instance()
    users = mos_instance.list_users()
    return UserListResponse(message="Users retrieved successfully", data=users)


@app.get("/users/me", summary="Get current user info", response_model=UserResponse)
async def get_user_info():
    """Get current user information including accessible cubes."""
    mos_instance = get_mos_instance()
    user_info = mos_instance.get_user_info()
    return UserResponse(message="User info retrieved successfully", data=user_info)


@app.post("/mem_cubes", summary="Register a MemCube", response_model=SimpleResponse)
async def register_mem_cube(mem_cube: MemCubeRegister):
    """Register a new MemCube."""
    mos_instance = get_mos_instance()
    mos_instance.register_mem_cube(
        mem_cube_name_or_path=mem_cube.mem_cube_name_or_path,
        mem_cube_id=mem_cube.mem_cube_id,
        user_id=mem_cube.user_id,
    )
    return SimpleResponse(message="MemCube registered successfully")


@app.delete(
    "/mem_cubes/{mem_cube_id}", summary="Unregister a MemCube", response_model=SimpleResponse
)
async def unregister_mem_cube(mem_cube_id: str, user_id: str | None = None):
    """Unregister a MemCube."""
    mos_instance = get_mos_instance()
    mos_instance.unregister_mem_cube(mem_cube_id=mem_cube_id, user_id=user_id)
    return SimpleResponse(message="MemCube unregistered successfully")


@app.post(
    "/mem_cubes/{cube_id}/share",
    summary="Share a cube with another user",
    response_model=SimpleResponse,
)
async def share_cube(cube_id: str, share_request: CubeShare):
    """Share a cube with another user."""
    mos_instance = get_mos_instance()
    success = mos_instance.share_cube_with_user(cube_id, share_request.target_user_id)
    if success:
        return SimpleResponse(message="Cube shared successfully")
    else:
        raise ValueError("Failed to share cube")


@app.post("/memories", summary="Create memories", response_model=SimpleResponse)
async def add_memory(memory_create: MemoryCreate):
    """Store new memories in a MemCube."""
    if not any([memory_create.messages, memory_create.memory_content, memory_create.doc_path]):
        raise ValueError("Either messages, memory_content, or doc_path must be provided")
    mos_instance = get_mos_instance()
    if memory_create.messages:
        messages = [m.model_dump() for m in memory_create.messages]
        mos_instance.add(
            messages=messages,
            mem_cube_id=memory_create.mem_cube_id,
            user_id=memory_create.user_id,
        )
    elif memory_create.memory_content:
        mos_instance.add(
            memory_content=memory_create.memory_content,
            mem_cube_id=memory_create.mem_cube_id,
            user_id=memory_create.user_id,
        )
    elif memory_create.doc_path:
        mos_instance.add(
            doc_path=memory_create.doc_path,
            mem_cube_id=memory_create.mem_cube_id,
            user_id=memory_create.user_id,
        )
    return SimpleResponse(message="Memories added successfully")


@app.get("/memories", summary="Get all memories", response_model=MemoryResponse)
async def get_all_memories(
    mem_cube_id: str | None = None,
    user_id: str | None = None,
):
    """Retrieve all memories from a MemCube."""
    mos_instance = get_mos_instance()
    result = mos_instance.get_all(mem_cube_id=mem_cube_id, user_id=user_id)
    return MemoryResponse(message="Memories retrieved successfully", data=result)


@app.get(
    "/memories/{mem_cube_id}/{memory_id}", summary="Get a memory", response_model=MemoryResponse
)
async def get_memory(mem_cube_id: str, memory_id: str, user_id: str | None = None):
    """Retrieve a specific memory by ID from a MemCube."""
    mos_instance = get_mos_instance()
    result = mos_instance.get(mem_cube_id=mem_cube_id, memory_id=memory_id, user_id=user_id)
    return MemoryResponse(message="Memory retrieved successfully", data=result)


@app.post("/search", summary="Search memories", response_model=SearchResponse)
async def search_memories(search_req: SearchRequest):
    """Search for memories across MemCubes.

    When enable_context_analysis=True, uses LLM to analyze search intent
    from the query and chat_history for smarter results.
    """
    mos_instance = get_mos_instance()

    # Build search kwargs
    search_kwargs = {
        "query": search_req.query,
        "user_id": search_req.user_id,
        "install_cube_ids": search_req.install_cube_ids,
    }

    # Add context analysis parameters if enabled
    if search_req.enable_context_analysis and search_req.chat_history:
        search_kwargs["chat_history"] = search_req.chat_history
        search_kwargs["enable_context_analysis"] = True

    if search_req.top_k:
        search_kwargs["top_k"] = search_req.top_k

    result = mos_instance.search(**search_kwargs)
    return SearchResponse(message="Search completed successfully", data=result)


@app.put(
    "/memories/{mem_cube_id}/{memory_id}", summary="Update a memory", response_model=SimpleResponse
)
async def update_memory(
    mem_cube_id: str, memory_id: str, updated_memory: dict[str, Any], user_id: str | None = None
):
    """Update an existing memory in a MemCube."""
    mos_instance = get_mos_instance()
    mos_instance.update(
        mem_cube_id=mem_cube_id,
        memory_id=memory_id,
        text_memory_item=updated_memory,
        user_id=user_id,
    )
    return SimpleResponse(message="Memory updated successfully")


@app.delete(
    "/memories/{mem_cube_id}/{memory_id}", summary="Delete a memory", response_model=SimpleResponse
)
async def delete_memory(mem_cube_id: str, memory_id: str, user_id: str | None = None):
    """Delete a specific memory from a MemCube."""
    mos_instance = get_mos_instance()
    mos_instance.delete(mem_cube_id=mem_cube_id, memory_id=memory_id, user_id=user_id)
    return SimpleResponse(message="Memory deleted successfully")


@app.delete("/memories/{mem_cube_id}", summary="Delete all memories", response_model=SimpleResponse)
async def delete_all_memories(mem_cube_id: str, user_id: str | None = None):
    """Delete all memories from a MemCube."""
    mos_instance = get_mos_instance()
    mos_instance.delete_all(mem_cube_id=mem_cube_id, user_id=user_id)
    return SimpleResponse(message="All memories deleted successfully")


@app.post("/graph/data", summary="Get graph data", response_model=GraphResponse)
async def get_graph_data(graph_req: APIGraphRequest):
    """Fetch graph nodes and edges for visualization."""
    mos_instance = get_mos_instance()

    # Find the specified cube or search for one that has tree_text memory
    graph_db = None
    
    if graph_req.mem_cube_id:
        try:
            cube = mos_instance.get_mem_cube(graph_req.mem_cube_id, user_id=graph_req.user_id)
            if hasattr(cube, "text_mem") and hasattr(cube.text_mem, "graph_store"):
                graph_db = cube.text_mem.graph_store
        except Exception as e:
            logger.warning(f"Could not get specified cube {graph_req.mem_cube_id}: {e}")

    if not graph_db:
        # Fallback: search across all active cubes in the instance
        for cube in mos_instance.mem_cubes.values():
            if hasattr(cube, "text_mem") and hasattr(cube.text_mem, "graph_store"):
                graph_db = cube.text_mem.graph_store
                break

    if not graph_db:
        # Try to get from a registered cube if none found in iteration
        try:
            for cube_id in mos_instance.list_mem_cubes(user_id=graph_req.user_id):
                cube = mos_instance.get_mem_cube(cube_id, user_id=graph_req.user_id)
                if hasattr(cube, "text_mem") and hasattr(cube.text_mem, "graph_store"):
                    graph_db = cube.text_mem.graph_store
                    break
        except Exception:
            pass

    if not graph_db:
        return GraphResponse(code=404, message="No graph database found in any memory cube", data=None)

    try:
        # Use the export_graph method from neo4j.py
        graph_data_raw = graph_db.export_graph(
            page=graph_req.page,
            page_size=graph_req.page_size,
            user_name=graph_req.user_id,
            filter=graph_req.filter,
        )

        graph_data = GraphData(
            nodes=graph_data_raw["nodes"],
            edges=graph_data_raw["edges"],
            total_nodes=graph_data_raw["total_nodes"],
            total_edges=graph_data_raw["total_edges"],
        )
        return GraphResponse(code=200, message="Graph data fetched successfully", data=graph_data)
    except Exception as e:
        logger.error(f"Error fetching graph data: {e}", exc_info=True)
        return GraphResponse(code=500, message=f"Internal server error: {str(e)}", data=None)


def _get_graph_db_for_cube(mos_instance, mem_cube_id: str | None, user_id: str):
    """Helper to get graph_db from a cube."""
    graph_db = None

    if mem_cube_id:
        try:
            cube = mos_instance.get_mem_cube(mem_cube_id, user_id=user_id)
            if hasattr(cube, "text_mem") and hasattr(cube.text_mem, "graph_store"):
                graph_db = cube.text_mem.graph_store
        except Exception as e:
            logger.warning(f"Could not get specified cube {mem_cube_id}: {e}")

    if not graph_db:
        for cube in mos_instance.mem_cubes.values():
            if hasattr(cube, "text_mem") and hasattr(cube.text_mem, "graph_store"):
                graph_db = cube.text_mem.graph_store
                break

    if not graph_db:
        try:
            for cube_id in mos_instance.list_mem_cubes(user_id=user_id):
                cube = mos_instance.get_mem_cube(cube_id, user_id=user_id)
                if hasattr(cube, "text_mem") and hasattr(cube.text_mem, "graph_store"):
                    graph_db = cube.text_mem.graph_store
                    break
        except Exception:
            pass

    return graph_db


@app.post("/graph/trace_path", summary="Trace path between nodes", response_model=TracePathResponse)
async def trace_path(trace_req: TracePathRequest):
    """
    Trace paths between two memory nodes in the knowledge graph.

    This enables AI reasoning about how memories are connected:
    - Understanding causality chains (A caused B caused C)
    - Finding indirect relationships between concepts
    - Exploring memory dependencies and influences
    """
    mos_instance = get_mos_instance()
    graph_db = _get_graph_db_for_cube(mos_instance, trace_req.mem_cube_id, trace_req.user_id)

    if not graph_db:
        return TracePathResponse(code=404, message="No graph database found", data=None)

    if not hasattr(graph_db, "trace_path"):
        return TracePathResponse(code=501, message="trace_path not implemented", data=None)

    try:
        result = graph_db.trace_path(
            source_id=trace_req.source_id,
            target_id=trace_req.target_id,
            max_depth=trace_req.max_depth,
            user_name=trace_req.user_id,
            include_all_paths=trace_req.include_all_paths,
        )

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
            paths.append(PathDetail(length=path_data.get("length", 0), nodes=nodes, edges=edges))

        source_node = None
        if result.get("source"):
            source_node = PathNode(id=result["source"]["id"], memory=result["source"].get("memory", ""))

        target_node = None
        if result.get("target"):
            target_node = PathNode(id=result["target"]["id"], memory=result["target"].get("memory", ""))

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
        logger.error(f"Error tracing path: {e}", exc_info=True)
        return TracePathResponse(code=500, message=f"Internal server error: {str(e)}", data=None)


@app.post("/graph/schema", summary="Export graph schema", response_model=GraphSchemaResponse)
async def get_graph_schema(schema_req: GraphSchemaRequest):
    """
    Export graph schema information for understanding the knowledge structure.

    This provides:
    - Statistics on relationship types and counts
    - Common relationship patterns in the graph
    - Total node and edge counts
    """
    mos_instance = get_mos_instance()
    graph_db = _get_graph_db_for_cube(mos_instance, schema_req.mem_cube_id, schema_req.user_id)

    if not graph_db:
        return GraphSchemaResponse(code=404, message="No graph database found", data=None)

    try:
        if hasattr(graph_db, "get_schema_statistics"):
            stats = graph_db.get_schema_statistics(
                user_name=schema_req.user_id,
                sample_size=schema_req.sample_size,
            )
        else:
            # Fallback to basic export_graph
            graph_data = graph_db.export_graph(
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
            for edge in graph_data.get("edges", []):
                edge_type = edge.get("type", "UNKNOWN")
                stats["edge_type_distribution"][edge_type] = stats["edge_type_distribution"].get(edge_type, 0) + 1

        patterns = []
        for edge_type, count in sorted(stats.get("edge_type_distribution", {}).items(), key=lambda x: x[1], reverse=True):
            frequency = "high" if count > 10 else "medium" if count > 3 else "low"
            patterns.append(SchemaRelationPattern(pattern=f"Memory -[{edge_type}]-> Memory", frequency=frequency))

        schema_data = GraphSchemaData(
            entity_types=[],
            relationship_patterns=patterns,
            total_nodes=stats.get("total_nodes", 0),
            total_edges=stats.get("total_edges", 0),
            edge_type_distribution=stats.get("edge_type_distribution", {}),
            memory_type_distribution=stats.get("memory_type_distribution", {}),
            tag_frequency=stats.get("tag_frequency", {}),
            avg_connections_per_node=stats.get("avg_connections_per_node", 0.0),
            max_connections=stats.get("max_connections", 0),
            orphan_node_count=stats.get("orphan_node_count", 0),
            time_range={
                "earliest": str(stats.get("time_range", {}).get("earliest")) if stats.get("time_range", {}).get("earliest") else None,
                "latest": str(stats.get("time_range", {}).get("latest")) if stats.get("time_range", {}).get("latest") else None,
            },
        )

        return GraphSchemaResponse(code=200, message="Graph schema exported successfully", data=schema_data)
    except Exception as e:
        logger.error(f"Error exporting schema: {e}", exc_info=True)
        return GraphSchemaResponse(code=500, message=f"Internal server error: {str(e)}", data=None)


@app.post("/chat", summary="Chat with MemOS", response_model=ChatResponse)
async def chat(chat_req: ChatRequest):
    """Chat with the MemOS system."""
    mos_instance = get_mos_instance()
    response = mos_instance.chat(query=chat_req.query, user_id=chat_req.user_id)
    if response is None:
        raise ValueError("No response generated")
    return ChatResponse(message="Chat response generated", data=response)


@app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)
async def home():
    """Redirect to the OpenAPI documentation."""
    return RedirectResponse(url="/docs", status_code=307)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions globally."""
    return JSONResponse(
        status_code=400,
        content={"code": 400, "message": str(exc), "data": None},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions globally."""
    logger.exception("Unhandled error:")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": str(exc), "data": None},
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()
