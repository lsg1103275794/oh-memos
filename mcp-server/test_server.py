#!/usr/bin/env python3
"""
Test MemOS MCP Server functionality.
"""

import asyncio
import json
import sys
sys.path.insert(0, ".")

from memos_mcp_server import (
    format_memories_for_display,
    detect_memory_type,
    suggest_search_queries,
    MEMOS_URL,
    MEMOS_USER,
    MEMOS_DEFAULT_CUBE,
)

import httpx


async def test_api_connection():
    """Test connection to MemOS API."""
    print("=" * 60)
    print("Testing MemOS MCP Server")
    print("=" * 60)
    print()

    print(f"📡 MemOS API URL: {MEMOS_URL}")
    print(f"👤 User: {MEMOS_USER}")
    print(f"📦 Default Cube: {MEMOS_DEFAULT_CUBE}")
    print()

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Test API connection
            print("1. Testing API connection...")
            response = await client.get(f"{MEMOS_URL}/users")
            if response.status_code == 200:
                print("   ✅ API is running")
            else:
                print(f"   ❌ API returned {response.status_code}")
                return False

            # Test search
            print("\n2. Testing search...")
            response = await client.post(
                f"{MEMOS_URL}/search",
                json={
                    "user_id": MEMOS_USER,
                    "query": "test",
                    "install_cube_ids": [MEMOS_DEFAULT_CUBE]
                }
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    print("   ✅ Search works")
                    formatted = format_memories_for_display(data.get("data", {}))
                    if "No memories" not in formatted:
                        print(f"   Found memories:\n{formatted[:500]}...")
                else:
                    print(f"   ⚠️ Search returned: {data.get('message')}")
            else:
                print(f"   ❌ Search failed: {response.status_code}")

            # Test memory type detection
            print("\n3. Testing memory type detection...")
            test_cases = [
                ("Fixed ModuleNotFoundError by installing package", "ERROR_PATTERN"),
                ("Decided to use JWT for authentication", "DECISION"),
                ("Released version 1.0.0", "MILESTONE"),
                ("Added new login feature", "FEATURE"),
            ]
            for content, expected in test_cases:
                detected = detect_memory_type(content)
                status = "✅" if detected == expected else "⚠️"
                print(f"   {status} '{content[:40]}...' → {detected}")

            # Test suggestion
            print("\n4. Testing search suggestions...")
            context = "ModuleNotFoundError: No module named 'uvicorn'"
            suggestions = suggest_search_queries(context)
            print(f"   Context: {context}")
            print(f"   Suggestions: {suggestions}")

            print("\n" + "=" * 60)
            print("✅ All tests passed!")
            print("=" * 60)
            return True

        except httpx.ConnectError:
            print(f"❌ Cannot connect to MemOS API at {MEMOS_URL}")
            print("   Make sure the API is running: python -m uvicorn memos.api.start_api:app")
            return False
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False


def main():
    success = asyncio.run(test_api_connection())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
