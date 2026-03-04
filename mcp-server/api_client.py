#!/usr/bin/env python3
"""
MemOS MCP Server API Client Module

Contains HTTP client management and API communication utilities.
"""

import asyncio

import httpx

from config import (
    MEMOS_API_WAIT_MAX,
    MEMOS_TIMEOUT_HEALTH,
    MEMOS_TIMEOUT_TOOL,
    MEMOS_URL,
    logger,
)


# ============================================================================
# HTTP Client Management (Connection Reuse)
# ============================================================================

_http_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create a shared HTTP client for connection reuse."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=MEMOS_TIMEOUT_TOOL,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
    return _http_client


async def close_http_client():
    """Close the shared HTTP client."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


# ============================================================================
# API Readiness Check
# ============================================================================

async def wait_for_api_ready(max_wait: float | None = None, interval: float = 2.0) -> bool:
    """Wait for MemOS API to be ready. Returns True if ready."""
    import time
    if max_wait is None:
        max_wait = MEMOS_API_WAIT_MAX
    start = time.time()

    async with httpx.AsyncClient(timeout=MEMOS_TIMEOUT_HEALTH) as client:
        while time.time() - start < max_wait:
            try:
                response = await client.get(f"{MEMOS_URL}/users")
                if response.status_code == 200:
                    logger.debug("MemOS API is ready")
                    return True
            except httpx.ConnectError:
                pass
            except Exception as e:
                logger.debug(f"API check failed: {e}")

            await asyncio.sleep(interval)

    logger.warning(f"MemOS API not ready after {max_wait}s")
    return False


# ============================================================================
# API Call with Retry Helper
# ============================================================================

async def api_call_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    cube_id: str,
    **kwargs
) -> tuple[bool, dict | None, int]:
    """
    Make API call with automatic cube re-registration on failure.

    Args:
        client: HTTP client
        method: HTTP method (GET, POST, DELETE)
        url: API endpoint URL
        cube_id: Cube ID for re-registration if needed
        **kwargs: Additional arguments for the request

    Returns:
        tuple: (success: bool, data: dict | None, status_code: int)
    """
    # Import here to avoid circular imports
    from config import _registered_cubes
    from cube_manager import ensure_cube_registered

    # First attempt
    if method.upper() == "GET":
        response = await client.get(url, **kwargs)
    elif method.upper() == "POST":
        response = await client.post(url, **kwargs)
    elif method.upper() == "DELETE":
        response = await client.delete(url, **kwargs)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

    if response.status_code == 200:
        data = response.json()
        if data.get("code") == 200:
            return True, data, 200

        # API returned error code - try re-registration
        _registered_cubes.discard(cube_id)
        reg_success, _ = await ensure_cube_registered(client, cube_id, force=True)
        if reg_success:
            # Retry
            if method.upper() == "GET":
                retry_response = await client.get(url, **kwargs)
            elif method.upper() == "POST":
                retry_response = await client.post(url, **kwargs)
            else:
                retry_response = await client.delete(url, **kwargs)

            if retry_response.status_code == 200:
                retry_data = retry_response.json()
                if retry_data.get("code") == 200:
                    return True, retry_data, 200
                return False, retry_data, 200

        return False, data, 200

    elif response.status_code == 400:
        # 400 often means cube not loaded - force re-register and retry
        _registered_cubes.discard(cube_id)
        reg_success, _ = await ensure_cube_registered(client, cube_id, force=True)
        if reg_success:
            if method.upper() == "GET":
                retry_response = await client.get(url, **kwargs)
            elif method.upper() == "POST":
                retry_response = await client.post(url, **kwargs)
            else:
                retry_response = await client.delete(url, **kwargs)

            if retry_response.status_code == 200:
                retry_data = retry_response.json()
                if retry_data.get("code") == 200:
                    return True, retry_data, 200
        return False, None, 400

    return False, None, response.status_code
