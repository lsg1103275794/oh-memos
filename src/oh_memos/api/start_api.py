import asyncio
import logging
import os
import threading
import time
import warnings

from typing import Any, Generic, TypeVar

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from oh_memos.api.config import APIConfig
from oh_memos.api.handlers.graph_handler import GraphHandler, HandlerDependencies
from oh_memos.api.middleware.request_context import RequestContextMiddleware
from oh_memos.api.product_models import (
    APIGraphRequest,
    APISchemaRequest,
    APITracePathRequest,
    ComponentHealth,
    GraphData,
    GraphResponse,
    HealthDetailData,
    HealthDetailResponse,
    HealthResponse,
    HealthStatus,
    PathEdge,
    PathNode,
    SchemaData,
    SchemaResponse,
    TracePath,
    TracePathData,
    TracePathResponse,
)
from oh_memos.configs.mem_os import MOSConfig
from oh_memos.mem_os.main import MOS
from oh_memos.mem_user.user_manager import UserManager, UserRole


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
_mos_init_lock = threading.Lock()


def get_mos_instance():
    """Get or create MOS instance with default user creation."""
    global MOS_INSTANCE
    if MOS_INSTANCE is None:
        with _mos_init_lock:
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


# Initialize graph handler
GRAPH_HANDLER = None
_graph_handler_init_lock = threading.Lock()


def get_graph_handler():
    """Lazy initialize GraphHandler with the current MOS instance's graph DB."""
    global GRAPH_HANDLER
    if GRAPH_HANDLER is None:
        with _graph_handler_init_lock:
            if GRAPH_HANDLER is None:
                mos = get_mos_instance()
                # Find a cube that has a graph_store
                graph_db = None
                # Try to get from the default cube if specified
                default_cube_id = os.environ.get("MEMOS_DEFAULT_CUBE", "dev_cube")
                if default_cube_id in mos.mem_cubes:
                    cube = mos.mem_cubes[default_cube_id]
                    if hasattr(cube, "text_mem") and hasattr(cube.text_mem, "graph_store"):
                        graph_db = cube.text_mem.graph_store

                # If not found, take the first available
                if not graph_db:
                    for cube in mos.mem_cubes.values():
                        if hasattr(cube, "text_mem") and hasattr(cube.text_mem, "graph_store"):
                            graph_db = cube.text_mem.graph_store
                            break

                if not graph_db:
                    logger.warning("No graph database found in any memory cube")

                deps = HandlerDependencies(graph_db=graph_db)
                GRAPH_HANDLER = GraphHandler(deps)
    return GRAPH_HANDLER


app = FastAPI(
    title="MemOS REST APIs",
    description="A REST API for managing and searching memories using MemOS.",
    version="1.0.0",
)

app.add_middleware(RequestContextMiddleware)


# Server start time for uptime calculation
_server_start_time = time.time()


# =============================================================================
# Health Check Endpoints
# =============================================================================


@app.get("/health", summary="Health check", response_model=HealthResponse)
async def health_check():
    """
    Simple health check for load balancers and k8s probes.

    Returns overall system status:
    - ok: All components operational
    - degraded: Non-critical components unavailable
    - down: Critical components unavailable
    """
    from datetime import datetime, timezone

    components = await asyncio.to_thread(_check_all_components)
    overall = _compute_overall_status(components)

    return HealthResponse(
        code=200,
        message=overall,
        data=HealthStatus(
            status=overall,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )


@app.get("/health/detail", summary="Detailed health check", response_model=HealthDetailResponse)
async def health_check_detail():
    """
    Detailed health check showing all component statuses.

    Returns status, latency, and error information for each component:
    - neo4j: Graph database
    - qdrant: Vector database
    """
    from datetime import datetime, timezone

    components = await asyncio.to_thread(_check_all_components)
    overall = _compute_overall_status(components)

    messages = {
        "ok": "All systems operational",
        "degraded": "Some non-critical components unavailable",
        "down": "Critical components unavailable",
    }

    return HealthDetailResponse(
        code=200,
        message=messages.get(overall, "Unknown status"),
        data=HealthDetailData(
            overall_status=overall,
            timestamp=datetime.now(timezone.utc).isoformat(),
            uptime_seconds=round(time.time() - _server_start_time, 2),
            components=components,
        ),
    )


def _check_all_components() -> dict[str, ComponentHealth]:
    """Check health of all components."""
    components = {}
    components["neo4j"] = _check_neo4j()
    components["qdrant"] = _check_qdrant()
    return components


def _compute_overall_status(components: dict[str, ComponentHealth]) -> str:
    """Compute overall system status."""
    critical = {"neo4j", "qdrant"}

    for comp_name in critical:
        comp = components.get(comp_name)
        if comp is None or comp.status != "ok":
            return "down"

    all_ok = all(c.status == "ok" for c in components.values())
    return "ok" if all_ok else "degraded"


def _check_neo4j() -> ComponentHealth:
    """Check Neo4j connection."""
    import time as _time

    try:
        mos = get_mos_instance()
        graph_db = None

        # Find graph_db from any cube
        for cube in mos.mem_cubes.values():
            if hasattr(cube, "text_mem") and hasattr(cube.text_mem, "graph_store"):
                graph_db = cube.text_mem.graph_store
                break

        if graph_db is None:
            return ComponentHealth(status="unavailable", error="No graph database configured")

        driver = getattr(graph_db, "driver", None)
        if driver is None:
            return ComponentHealth(status="unavailable", error="No driver available")

        start = _time.perf_counter()
        with driver.session() as session:
            result = session.run("RETURN 1 AS health_check")
            result.single()
        latency = (_time.perf_counter() - start) * 1000

        return ComponentHealth(status="ok", latency_ms=round(latency, 2))

    except Exception as e:
        logger.warning(f"Neo4j health check failed: {e}")
        return ComponentHealth(status="error", error=str(e)[:200])


def _check_qdrant() -> ComponentHealth:
    """Check Qdrant connection."""
    import time as _time

    try:
        mos = get_mos_instance()
        vector_db = None

        # Find vector_db from any cube
        for cube in mos.mem_cubes.values():
            if hasattr(cube, "text_mem"):
                # Try to find vec_db in graph_store (for Neo4jCommunity)
                graph_store = getattr(cube.text_mem, "graph_store", None)
                if graph_store and hasattr(graph_store, "vec_db"):
                    vector_db = graph_store.vec_db
                    break

        if vector_db is None:
            return ComponentHealth(status="unavailable", error="No vector database configured")

        client = getattr(vector_db, "client", None)
        if client is None:
            return ComponentHealth(status="unavailable", error="No client available")

        start = _time.perf_counter()
        client.get_collections()
        latency = (_time.perf_counter() - start) * 1000

        return ComponentHealth(status="ok", latency_ms=round(latency, 2))

    except Exception as e:
        logger.warning(f"Qdrant health check failed: {e}")
        return ComponentHealth(status="error", error=str(e)[:200])


# =============================================================================
# Auto-Archive Background Task
# =============================================================================

_archive_task = None


def _get_neo4j_driver():
    """Get Neo4j driver from MOS instance for archiver."""
    try:
        mos = get_mos_instance()
        for cube in mos.mem_cubes.values():
            if hasattr(cube, "text_mem"):
                graph_store = getattr(cube.text_mem, "graph_store", None)
                if graph_store and hasattr(graph_store, "driver"):
                    return graph_store.driver
    except Exception as e:
        logger.warning(f"Could not get Neo4j driver for archiver: {e}")
    return None


@app.on_event("startup")
async def startup_archiver():
    """Start background archive task if enabled."""
    global _archive_task

    auto_archive = os.environ.get("MEMOS_AUTO_ARCHIVE", "true").lower() == "true"
    if not auto_archive:
        logger.info("Startup: Auto-archive is disabled")
        return

    try:
        from oh_memos.mem_scheduler.archiver import periodic_archive_task

        _archive_task = asyncio.create_task(
            periodic_archive_task(_get_neo4j_driver)
        )
        logger.info("Startup: Archive background task started")
    except Exception as e:
        logger.warning(f"Startup: Failed to start archive task: {e}")


@app.on_event("shutdown")
async def shutdown_archiver():
    """Cancel archive task on shutdown."""
    global _archive_task
    if _archive_task:
        _archive_task.cancel()
        try:
            await _archive_task
        except asyncio.CancelledError:
            pass
        logger.info("Shutdown: Archive task cancelled")


# =============================================================================
# Archive API Endpoints
# =============================================================================


@app.post("/archive/run", summary="Run archive manually")
async def run_archive():
    """
    Manually trigger the archive process.

    Archives expired memories based on configured TTL and types.
    """
    driver = _get_neo4j_driver()
    if not driver:
        return {"code": 500, "message": "Neo4j driver not available", "data": None}

    try:
        from oh_memos.mem_scheduler.archiver import archive_expired_memories_sync, get_archive_config

        config = get_archive_config()
        archived_count = archive_expired_memories_sync(
            driver,
            ttl_days=config["ttl_days"],
            archive_types=config["archive_types"],
        )

        return {
            "code": 200,
            "message": f"Archive completed: {archived_count} memories archived",
            "data": {
                "archived_count": archived_count,
                "ttl_days": config["ttl_days"],
                "archive_types": config["archive_types"],
            }
        }
    except Exception as e:
        logger.error(f"Manual archive failed: {e}")
        return {"code": 500, "message": str(e), "data": None}


@app.get("/archive/stats", summary="Get archive statistics")
async def get_archive_stats():
    """
    Get statistics about archived vs active memories.
    """
    driver = _get_neo4j_driver()
    if not driver:
        return {"code": 500, "message": "Neo4j driver not available", "data": None}

    try:
        from oh_memos.mem_scheduler.archiver import get_archive_stats_sync, get_archive_config

        stats = get_archive_stats_sync(driver)
        config = get_archive_config()

        return {
            "code": 200,
            "message": "Stats retrieved",
            "data": {
                "status_counts": stats,
                "config": {
                    "enabled": config["enabled"],
                    "ttl_days": config["ttl_days"],
                    "archive_types": config["archive_types"],
                    "interval_seconds": config["interval_seconds"],
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to get archive stats: {e}")
        return {"code": 500, "message": str(e), "data": None}


@app.post("/archive/restore/{memory_id}", summary="Restore archived memory")
async def restore_archived_memory(memory_id: str):
    """
    Restore an archived memory back to active status.
    """
    driver = _get_neo4j_driver()
    if not driver:
        return {"code": 500, "message": "Neo4j driver not available", "data": None}

    try:
        from oh_memos.mem_scheduler.archiver import restore_archived_memory_sync

        restored = restore_archived_memory_sync(driver, memory_id)

        if restored:
            return {
                "code": 200,
                "message": f"Memory {memory_id} restored",
                "data": {"memory_id": memory_id, "restored": True}
            }
        else:
            return {
                "code": 404,
                "message": f"Memory {memory_id} not found or not archived",
                "data": {"memory_id": memory_id, "restored": False}
            }
    except Exception as e:
        logger.error(f"Failed to restore memory {memory_id}: {e}")
        return {"code": 500, "message": str(e), "data": None}


# Auto-register default cube on startup
@app.on_event("startup")
async def startup_auto_register():
    """Auto-register the default memory cube on API startup."""
    default_cube_id = os.environ.get("MEMOS_DEFAULT_CUBE", "dev_cube")
    cubes_dir = os.environ.get(
        "MEMOS_CUBES_DIR",
        os.environ.get("MOS_CUBES_DIR", os.environ.get("MOS_CUBE_PATH", ""))
    )

    if not cubes_dir:
        logger.info("Startup: No cubes directory set, skipping auto-registration")
        return

    # Convert relative path to absolute if needed
    if not os.path.isabs(cubes_dir):
        # Assume relative to project root or current work dir
        # start.bat runs from src/, so ./data/memos_cubes is ../data/memos_cubes
        cubes_dir = os.path.abspath(os.path.join(os.getcwd(), "..", cubes_dir))
        logger.info(f"Startup: Converted relative cubes_dir to absolute: {cubes_dir}")

    if not os.path.isdir(cubes_dir):
        logger.warning(f"Startup: Cubes directory not found at {cubes_dir}")
        return

    # Wait for Qdrant to be ready before registering cubes
    qdrant_host = os.environ.get("QDRANT_HOST", "localhost")
    qdrant_port = os.environ.get("QDRANT_PORT", "6333")
    qdrant_health_url = f"http://{qdrant_host}:{qdrant_port}/"
    qdrant_ready = False
    import httpx as _httpx
    for attempt in range(20):  # up to 20s
        try:
            async with _httpx.AsyncClient(timeout=2.0) as hc:
                resp = await hc.get(qdrant_health_url)
                if resp.status_code == 200:
                    qdrant_ready = True
                    logger.info(f"Startup: Qdrant ready after {attempt + 1}s")
                    break
                # 502 = starting up, keep waiting
        except _httpx.ConnectError:
            # Connection refused = Qdrant not running at all, no point waiting
            logger.warning(
                f"Startup: Qdrant not running at {qdrant_host}:{qdrant_port}. "
                "Start Qdrant first (run scripts/local/start.bat) for cube auto-registration."
            )
            break
        except Exception:
            pass
        await asyncio.sleep(1)

    if not qdrant_ready:
        logger.warning("Startup: Qdrant not ready, skipping cube auto-registration")
        return

    mos_instance = get_mos_instance()
    default_user = mos_instance.user_id  # Use the same user as MOS instance

    # Register all cubes found in the directory
    registered_count = 0
    for item in os.listdir(cubes_dir):
        cube_path = os.path.join(cubes_dir, item)
        if os.path.isdir(cube_path):
            config_path = os.path.join(cube_path, "config.json")
            if os.path.isfile(config_path):
                # Retry up to 3 times for transient Qdrant errors
                for retry in range(3):
                    try:
                        mos_instance.register_mem_cube(
                            mem_cube_name_or_path=cube_path,
                            mem_cube_id=item,
                            user_id=default_user,
                        )
                        logger.info(f"Startup: Auto-registered cube '{item}' from {cube_path}")
                        registered_count += 1
                        break
                    except Exception as e:
                        err_str = str(e)
                        if "502" in err_str and retry < 2:
                            logger.debug(f"Startup: Cube '{item}' retry {retry + 1}/3: {e}")
                            await asyncio.sleep(3)
                        else:
                            logger.warning(f"Startup: Failed to auto-register cube '{item}': {e}")
                            break

    if registered_count == 0:
        logger.warning(f"Startup: No valid cubes found in {cubes_dir}")



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
    install_cube_ids: list[str] | None = Field(
        None,
        description="List of cube IDs to search in",
        json_schema_extra={"example": ["cube123", "cube456"]},
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


# Graph endpoints
@app.post(
    "/product/graph/data", summary="Get graph data for visualization", response_model=GraphResponse
)
async def get_graph_data(graph_req: APIGraphRequest):
    """Fetch graph nodes and edges for visualization."""
    handler = get_graph_handler()
    return handler.handle_get_graph_data(graph_req)


@app.post(
    "/product/graph/trace_path", summary="Trace path between nodes", response_model=TracePathResponse
)
async def trace_path(req: APITracePathRequest):
    """Trace paths between two memory nodes."""
    handler = get_graph_handler()
    return handler.handle_trace_path(req)


@app.post(
    "/product/graph/schema", summary="Get graph schema", response_model=SchemaResponse
)
async def get_graph_schema(req: APISchemaRequest):
    """Get graph schema and statistics."""
    handler = get_graph_handler()
    return handler.handle_get_graph_schema(req)


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
    # Convert Pydantic model to dict for JSON serialization
    if result is not None and hasattr(result, "model_dump"):
        result = result.model_dump()
    return MemoryResponse(message="Memory retrieved successfully", data=result)


@app.post("/search", summary="Search memories", response_model=SearchResponse)
async def search_memories(search_req: SearchRequest):
    """Search for memories across MemCubes."""
    mos_instance = get_mos_instance()
    result = mos_instance.search(
        query=search_req.query,
        user_id=search_req.user_id,
        install_cube_ids=search_req.install_cube_ids,
    )
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
        return GraphResponse(code=500, message=f"Internal server error: {e!s}", data=None)


def _get_graph_db(mos_instance, user_id: str | None = None, mem_cube_id: str | None = None):
    """Helper to get graph database from MOS instance."""
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
async def trace_path(req: APITracePathRequest):
    """Trace reasoning paths between two memory nodes."""
    mos_instance = get_mos_instance()
    graph_db = _get_graph_db(mos_instance, req.user_id, req.mem_cube_id)

    if not graph_db:
        return TracePathResponse(code=404, message="No graph database found", data=None)

    try:
        # Use graph_db to find paths
        if hasattr(graph_db, 'find_path'):
            path_result = graph_db.find_path(
                source_id=req.source_id,
                target_id=req.target_id,
                max_depth=req.max_depth
            )
        else:
            # Fallback: direct Neo4j query (run in thread to avoid blocking event loop)
            path_result = await asyncio.to_thread(_neo4j_find_path, req.source_id, req.target_id, req.max_depth)

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
        logger.error(f"Error tracing path: {e}", exc_info=True)
        return TracePathResponse(code=500, message=f"Internal server error: {e!s}", data=None)


@app.post("/graph/schema", summary="Export graph schema", response_model=SchemaResponse)
async def export_schema(req: APISchemaRequest):
    """Export knowledge graph schema and statistics."""
    mos_instance = get_mos_instance()
    graph_db = _get_graph_db(mos_instance, req.user_id, req.mem_cube_id)

    if not graph_db:
        return SchemaResponse(code=404, message="No graph database found", data=None)

    try:
        # Use graph_db to get schema stats
        if hasattr(graph_db, 'get_schema_stats'):
            stats = graph_db.get_schema_stats(sample_size=req.sample_size)
        else:
            # Fallback: direct Neo4j query (run in thread to avoid blocking event loop)
            stats = await asyncio.to_thread(_neo4j_get_schema_stats, req.sample_size)

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
        logger.error(f"Error exporting schema: {e}", exc_info=True)
        return SchemaResponse(code=500, message=f"Internal server error: {e!s}", data=None)


def _neo4j_find_path(source_id: str, target_id: str, max_depth: int) -> dict:
    """Fallback: Direct Neo4j query for path finding."""
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
                return {"path_found": True, "paths": [{"nodes": [], "edges": []}]}
            return {"path_found": False, "paths": []}
    except Exception as e:
        logger.error(f"Neo4j path query error: {e}")

    return {"path_found": False, "paths": []}


def _neo4j_get_schema_stats(sample_size: int) -> dict:
    """Fallback: Direct Neo4j query for schema stats."""
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
        logger.error(f"Neo4j schema query error: {e}")

    return stats


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
