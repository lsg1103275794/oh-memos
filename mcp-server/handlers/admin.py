#!/usr/bin/env python3
"""
MemOS MCP Server Admin Handlers

Handles memos_list_cubes, memos_register_cube, memos_create_user,
memos_validate_cubes, memos_delete tools.
"""

import json
import os

from typing import Any

import httpx

from config import (
    MEMOS_CUBES_DIR,
    MEMOS_DEFAULT_CUBE,
    MEMOS_ENABLE_DELETE,
    MEMOS_TIMEOUT_TOOL,
    MEMOS_URL,
    MEMOS_USER,
    _registered_cubes,
)
from cube_manager import (
    ensure_cube_registered,
    get_cube_path,
    get_cubes_base_dir,
    list_available_cubes,
    validate_and_fix_cube_config,
    verify_cube_loaded,
)
from mcp.types import TextContent

from handlers.utils import error_response, get_cube_id_from_args


async def handle_memos_list_cubes(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_list_cubes tool call."""
    include_status = arguments.get("include_status", False)
    available = list_available_cubes()

    if not available:
        cubes_dir = MEMOS_CUBES_DIR
        if cubes_dir.endswith(MEMOS_DEFAULT_CUBE):
            cubes_dir = os.path.dirname(cubes_dir)
        return [TextContent(
            type="text",
            text=f"## No cubes found\n\n"
                 f"Cubes directory: `{cubes_dir}`\n\n"
                 f"To create a new cube, use the MemOS web interface at {MEMOS_URL}/docs "
                 f"or create a cube directory with a config.json file."
        )]

    result = ["## Available Memory Cubes\n"]
    result.append(f"Cubes directory: `{MEMOS_CUBES_DIR}`\n")

    for cube in available:
        cube_id = cube["id"]
        cube_path = cube["path"]

        if include_status:
            # Check if cube is loaded
            is_loaded = await verify_cube_loaded(client, cube_id)
            status = "loaded" if is_loaded else "not loaded"
            result.append(f"- **{cube_id}**: `{cube_path}` ({status})")
        else:
            result.append(f"- **{cube_id}**: `{cube_path}`")

    result.append(f"\n**Default cube**: `{MEMOS_DEFAULT_CUBE}`")
    result.append("\n*Use `memos_list_cubes(include_status=True)` to check registration status.*")
    return [TextContent(type="text", text="\n".join(result))]


async def handle_memos_register_cube(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_register_cube tool call."""
    cube_id = arguments.get("cube_id")
    cube_path = arguments.get("cube_path")

    if not cube_id:
        return error_response("❌ `cube_id` is required")

    # If path not provided, try to find it
    if not cube_path:
        cube_path = get_cube_path(cube_id)
        if not cube_path:
            # List available cubes as helpful hint
            available = list_available_cubes()
            hint = ""
            if available:
                hint = "\n\n**Available cubes:**\n" + "\n".join([f"- `{c['id']}`" for c in available])
            return [TextContent(
                type="text",
                text=f"❌ Cube `{cube_id}` not found in cubes directory.\n\n"
                     f"Cubes directory: `{get_cubes_base_dir()}`{hint}"
            )]

    try:
        response = await client.post(
            f"{MEMOS_URL}/mem_cubes",
            json={
                "user_id": MEMOS_USER,
                "mem_cube_name_or_path": cube_path,
                "mem_cube_id": cube_id
            },
            timeout=MEMOS_TIMEOUT_TOOL
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                _registered_cubes.add(cube_id)
                return [TextContent(
                    type="text",
                    text=f"✅ **Cube registered successfully!**\n\n"
                         f"- Cube ID: `{cube_id}`\n"
                         f"- Path: `{cube_path}`\n\n"
                         f"You can now use this cube with other memos_* tools."
                )]
            else:
                error_msg = data.get("message", "Unknown error")
                # Provide helpful hints based on error
                hint = ""
                if "reranker" in error_msg.lower():
                    hint = "\n\n**Hint**: Edit the cube's config.json and change `reranker.backend` to `http_bge` or `noop`."
                elif "user" in error_msg.lower():
                    hint = "\n\n**Hint**: Use `memos_create_user` tool to create the user first."
                return error_response(f"❌ Registration failed: {error_msg}{hint}")
        else:
            return error_response(f"❌ API error: HTTP {response.status_code}")

    except Exception as e:
        return error_response(f"❌ Registration error: {e!s}")


async def handle_memos_create_user(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_create_user tool call."""
    user_id = arguments.get("user_id", MEMOS_USER)
    user_name = arguments.get("user_name", user_id)

    try:
        response = await client.post(
            f"{MEMOS_URL}/users",
            json={
                "user_name": user_name,
                "user_id": user_id,
                "role": "USER"
            },
            timeout=MEMOS_TIMEOUT_TOOL
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                return [TextContent(
                    type="text",
                    text=f"✅ **User created successfully!**\n\n"
                         f"- User ID: `{user_id}`\n"
                         f"- User Name: `{user_name}`\n\n"
                         f"You can now register cubes and store memories."
                )]
            else:
                error_msg = data.get("message", "Unknown error")
                # Check if user already exists
                if "exist" in error_msg.lower():
                    return [TextContent(type="text", text=f"ℹ️ User `{user_id}` already exists. You can proceed with cube registration.")]
                return error_response(f"❌ User creation failed: {error_msg}")
        else:
            return error_response(f"❌ API error: HTTP {response.status_code}")

    except Exception as e:
        return error_response(f"❌ User creation error: {e!s}")


async def handle_memos_validate_cubes(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_validate_cubes tool call."""
    fix_issues = arguments.get("fix", True)
    cubes_dir = get_cubes_base_dir()

    if not cubes_dir or not os.path.isdir(cubes_dir):
        return error_response(f"❌ Cubes directory not found: {cubes_dir}")

    results = ["## 🔍 Cube Configuration Validation\n"]
    fixed_count = 0
    error_count = 0
    ok_count = 0

    try:
        for cube_name in os.listdir(cubes_dir):
            cube_path = os.path.join(cubes_dir, cube_name)
            config_path = os.path.join(cube_path, "config.json")

            if not os.path.isdir(cube_path) or not os.path.isfile(config_path):
                continue

            # Read and check config
            try:
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)

                issues = []

                # Check cube_id
                if config.get("cube_id") != cube_name:
                    issues.append(f"cube_id: `{config.get('cube_id')}` → `{cube_name}`")

                # Check graph_db user_name
                text_cfg = config.get("text_mem", {}).get("config", {})
                graph_cfg = text_cfg.get("graph_db", {}).get("config", {})
                current_user_name = graph_cfg.get("user_name")

                if current_user_name and current_user_name != cube_name:
                    issues.append(f"user_name: `{current_user_name}` → `{cube_name}`")

                if issues:
                    if fix_issues:
                        was_fixed, error = validate_and_fix_cube_config(cube_name, config_path)
                        if was_fixed:
                            results.append(f"- **{cube_name}**: ✅ Fixed - {', '.join(issues)}")
                            fixed_count += 1
                        elif error:
                            results.append(f"- **{cube_name}**: ❌ Error - {error}")
                            error_count += 1
                    else:
                        results.append(f"- **{cube_name}**: ⚠️ Issues - {', '.join(issues)}")
                        error_count += 1
                else:
                    results.append(f"- **{cube_name}**: ✅ OK")
                    ok_count += 1

            except Exception as e:
                results.append(f"- **{cube_name}**: ❌ Error reading config - {e}")
                error_count += 1

        # Summary
        results.append("\n### Summary")
        results.append(f"- ✅ OK: {ok_count}")
        if fixed_count > 0:
            results.append(f"- 🔧 Fixed: {fixed_count}")
        if error_count > 0:
            results.append(f"- ⚠️ Issues: {error_count}")

        if fixed_count > 0:
            results.append("\n**Note:** Fixed cubes need API restart to take effect for existing loaded cubes.")

        return [TextContent(type="text", text="\n".join(results))]

    except Exception as e:
        return error_response(f"❌ Validation error: {e!s}")


async def handle_memos_delete(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_delete tool call."""
    # Safety check - only allow if explicitly enabled
    if not MEMOS_ENABLE_DELETE:
        return error_response("❌ Delete functionality is DISABLED. Set MEMOS_ENABLE_DELETE=true in environment to enable.")

    cube_id = get_cube_id_from_args(arguments)
    memory_id = arguments.get("memory_id")
    memory_ids = arguments.get("memory_ids", [])
    delete_all = arguments.get("delete_all", False)

    # Collect all IDs to delete
    ids_to_delete = []
    if memory_id:
        ids_to_delete.append(memory_id)
    if memory_ids:
        ids_to_delete.extend(memory_ids)

    # Auto-register cube
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return error_response(f"## Cube Registration Failed\n\n{reg_error}")

    if delete_all:
        # Delete ALL memories - very dangerous!
        response = await client.delete(
            f"{MEMOS_URL}/memories/{cube_id}",
            params={"user_id": MEMOS_USER}
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                return [TextContent(type="text", text=f"⚠️ **ALL memories deleted** from cube: `{cube_id}`")]
            else:
                return error_response(f"❌ **Delete all failed**: {data.get('message', 'Unknown error')}")
        else:
            return error_response(f"❌ **API error** during delete all: {response.status_code}")

    elif ids_to_delete:
        # Delete single or multiple memories
        results = []
        for mid in ids_to_delete:
            # Optional: Try to fetch memory first to confirm it exists and show content
            try:
                get_resp = await client.get(
                    f"{MEMOS_URL}/memories/{cube_id}/{mid}",
                    params={"user_id": MEMOS_USER}
                )
                mem_content = "*(Unknown content)*"
                if get_resp.status_code == 200:
                    g_data = get_resp.json()
                    if g_data.get("code") == 200 and g_data.get("data"):
                        # Extract memory text from the node
                        mem_node = g_data.get("data")
                        if isinstance(mem_node, dict):
                            mem_content = mem_node.get("memory", mem_content)
            except Exception:
                mem_content = "*(Fetch failed)*"

            response = await client.delete(
                f"{MEMOS_URL}/memories/{cube_id}/{mid}",
                params={"user_id": MEMOS_USER}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    results.append(f"✅ Deleted: `{mid}`\n   > {mem_content[:150]}...")
                else:
                    results.append(f"❌ Failed: `{mid}` ({data.get('message', 'Unknown error')})")
            else:
                results.append(f"❌ API Error: `{mid}` (Status: {response.status_code})")

        return [TextContent(type="text", text="\n".join(results))]

    else:
        return error_response("❌ Must provide either `memory_id`, `memory_ids` or `delete_all=true`")
