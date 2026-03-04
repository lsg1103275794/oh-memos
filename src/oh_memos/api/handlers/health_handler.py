"""
Health check handler for MemOS API.

Provides endpoints for monitoring system component health including:
- Neo4j (graph database)
- Qdrant (vector database)
- Redis (cache/scheduler)
- Ollama (LLM, optional)
"""

import time
from datetime import datetime, timezone
from typing import Literal

from oh_memos.api.handlers.base_handler import BaseHandler, HandlerDependencies
from oh_memos.api.product_models import (
    ComponentHealth,
    HealthDetailData,
    HealthDetailResponse,
    HealthResponse,
    HealthStatus,
)
from oh_memos.log import get_logger


logger = get_logger(__name__)

# Server start time for uptime calculation
_start_time = time.time()


class HealthHandler(BaseHandler):
    """Handler for health check endpoints."""

    # Critical components - if any fails, status is "down"
    CRITICAL_COMPONENTS = {"neo4j", "qdrant"}

    # Timeout for each component check (seconds)
    CHECK_TIMEOUT = 5.0

    def __init__(
        self,
        dependencies: HandlerDependencies,
        redis_client=None,
        llm=None,
    ):
        """
        Initialize health handler.

        Args:
            dependencies: Handler dependencies containing graph_db and vector_db
            redis_client: Redis client instance (optional)
            llm: LLM instance for Ollama check (optional)
        """
        super().__init__(dependencies)
        self.redis_client = redis_client
        self._llm = llm

    def handle_health(self) -> HealthResponse:
        """
        Simple health check - returns overall status quickly.

        Used by load balancers and k8s probes.
        """
        components = self._check_all_components()
        overall = self._compute_overall_status(components)

        return HealthResponse(
            code=200,
            message=overall,
            data=HealthStatus(
                status=overall,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        )

    def handle_health_detail(self) -> HealthDetailResponse:
        """
        Detailed health check - returns status of all components.

        Used for monitoring dashboards and debugging.
        """
        components = self._check_all_components()
        overall = self._compute_overall_status(components)

        return HealthDetailResponse(
            code=200,
            message=self._get_status_message(overall),
            data=HealthDetailData(
                overall_status=overall,
                timestamp=datetime.now(timezone.utc).isoformat(),
                uptime_seconds=round(time.time() - _start_time, 2),
                components=components,
            ),
        )

    def _check_all_components(self) -> dict[str, ComponentHealth]:
        """Check health of all components."""
        components = {}

        # Always check critical components
        components["neo4j"] = self._check_neo4j()
        components["qdrant"] = self._check_qdrant()

        # Check Redis if available
        if self.redis_client is not None:
            components["redis"] = self._check_redis()

        # Check Ollama if configured
        if self._llm is not None:
            components["ollama"] = self._check_ollama()

        return components

    def _compute_overall_status(
        self, components: dict[str, ComponentHealth]
    ) -> Literal["ok", "degraded", "down"]:
        """
        Compute overall system status based on component health.

        Rules:
        - Any critical component (neo4j, qdrant) fails -> "down"
        - All components ok -> "ok"
        - Otherwise -> "degraded"
        """
        # Check critical components
        for comp_name in self.CRITICAL_COMPONENTS:
            comp = components.get(comp_name)
            if comp is None or comp.status != "ok":
                return "down"

        # Check if all components are ok
        all_ok = all(c.status == "ok" for c in components.values())
        if all_ok:
            return "ok"

        return "degraded"

    def _get_status_message(self, status: str) -> str:
        """Get human-readable message for status."""
        messages = {
            "ok": "All systems operational",
            "degraded": "Some non-critical components unavailable",
            "down": "Critical components unavailable",
        }
        return messages.get(status, "Unknown status")

    def _check_neo4j(self) -> ComponentHealth:
        """Check Neo4j connection by running a simple query."""
        if self.graph_db is None:
            return ComponentHealth(status="unavailable", error="Not configured")

        start = time.perf_counter()
        try:
            # Try to get the driver and run a simple query
            driver = getattr(self.graph_db, "driver", None)
            if driver is None:
                return ComponentHealth(status="unavailable", error="No driver available")

            with driver.session() as session:
                result = session.run("RETURN 1 AS health_check")
                result.single()

            latency = (time.perf_counter() - start) * 1000
            return ComponentHealth(status="ok", latency_ms=round(latency, 2))

        except Exception as e:
            logger.warning(f"Neo4j health check failed: {e}")
            return ComponentHealth(status="error", error=str(e)[:200])

    def _check_qdrant(self) -> ComponentHealth:
        """Check Qdrant connection by listing collections."""
        if self.vector_db is None:
            return ComponentHealth(status="unavailable", error="Not configured")

        start = time.perf_counter()
        try:
            # Try to get collections (lightweight operation)
            client = getattr(self.vector_db, "client", None)
            if client is None:
                return ComponentHealth(status="unavailable", error="No client available")

            client.get_collections()

            latency = (time.perf_counter() - start) * 1000
            return ComponentHealth(status="ok", latency_ms=round(latency, 2))

        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")
            return ComponentHealth(status="error", error=str(e)[:200])

    def _check_redis(self) -> ComponentHealth:
        """Check Redis connection using PING."""
        if self.redis_client is None:
            return ComponentHealth(status="unavailable", error="Not configured")

        start = time.perf_counter()
        try:
            self.redis_client.ping()

            latency = (time.perf_counter() - start) * 1000
            return ComponentHealth(status="ok", latency_ms=round(latency, 2))

        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return ComponentHealth(status="error", error=str(e)[:200])

    def _check_ollama(self) -> ComponentHealth:
        """Check Ollama connection by listing models."""
        if self._llm is None:
            return ComponentHealth(status="unavailable", error="Not configured")

        start = time.perf_counter()
        try:
            # Try to get the Ollama client
            client = getattr(self._llm, "client", None)
            if client is None:
                return ComponentHealth(status="unavailable", error="No client available")

            # List models is a lightweight operation
            client.list()

            latency = (time.perf_counter() - start) * 1000
            return ComponentHealth(status="ok", latency_ms=round(latency, 2))

        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return ComponentHealth(status="error", error=str(e)[:200])
