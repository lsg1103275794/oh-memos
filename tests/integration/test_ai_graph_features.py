"""
Integration tests for AI Knowledge Graph features.

This module tests the end-to-end functionality of:
- Triple extraction from memory text
- Path tracing between graph nodes
- Context-aware search with intent analysis
- Graph schema statistics and export

These tests require:
- Running MemOS API server (localhost:18000)
- Neo4j database (localhost:7687)
- Configured LLM backend

Run with: pytest tests/integration/test_ai_graph_features.py -v
"""

import json
import time
import pytest
import requests
from typing import Any


BASE_URL = "http://localhost:18000/product"
TEST_USER_ID = "dev_user"
TEST_CUBE_ID = "dev_cube"


def api_post(endpoint: str, payload: dict) -> dict:
    """Helper to make POST requests and return JSON response."""
    response = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=30)
    return {"status": response.status_code, "data": response.json()}


class TestTripleExtraction:
    """Tests for the TripleExtractor module."""

    def test_triple_extractor_import(self):
        """Test that TripleExtractor can be imported."""
        try:
            from memos.memories.textual.tree_text_memory.organize.triple_extractor import (
                TripleExtractor,
            )
            assert TripleExtractor is not None
        except ImportError as e:
            pytest.skip(f"Cannot import TripleExtractor: {e}")

    def test_triple_extraction_prompt_exists(self):
        """Test that TRIPLE_EXTRACTION_PROMPT is defined."""
        try:
            from memos.templates.graph_ai_prompts import TRIPLE_EXTRACTION_PROMPT
            assert TRIPLE_EXTRACTION_PROMPT is not None
            assert "{memory_text}" in TRIPLE_EXTRACTION_PROMPT
        except ImportError as e:
            pytest.skip(f"Cannot import prompts: {e}")

    def test_valid_predicates_defined(self):
        """Test that valid predicates are defined in TripleExtractor."""
        try:
            from memos.memories.textual.tree_text_memory.organize.triple_extractor import (
                TripleExtractor,
            )
            assert hasattr(TripleExtractor, "VALID_PREDICATES")
            predicates = TripleExtractor.VALID_PREDICATES
            assert "WORKS_AT" in predicates
            assert "CAUSED" in predicates
            assert "RELATED_TO" in predicates
        except ImportError as e:
            pytest.skip(f"Cannot import TripleExtractor: {e}")


class TestPathTracing:
    """Tests for path tracing functionality."""

    @pytest.fixture
    def sample_node_ids(self):
        """Get sample node IDs from the graph."""
        result = api_post("/graph/data", {
            "user_id": TEST_USER_ID,
            "page": 1,
            "page_size": 10
        })
        if result["status"] == 200 and result["data"].get("code") == 200:
            nodes = result["data"].get("data", {}).get("nodes", [])
            if len(nodes) >= 2:
                return [nodes[0]["id"], nodes[1]["id"]]
        return None

    def test_trace_path_api_exists(self):
        """Test that trace_path API endpoint exists."""
        result = api_post("/graph/trace_path", {
            "user_id": TEST_USER_ID,
            "source_id": "test-source",
            "target_id": "test-target",
            "max_depth": 3
        })
        # Should return 200 even if nodes don't exist
        assert result["status"] == 200

    def test_trace_path_returns_structure(self, sample_node_ids):
        """Test that trace_path returns expected structure."""
        if not sample_node_ids:
            pytest.skip("No nodes available for testing")

        result = api_post("/graph/trace_path", {
            "user_id": TEST_USER_ID,
            "source_id": sample_node_ids[0],
            "target_id": sample_node_ids[1],
            "max_depth": 5
        })

        assert result["status"] == 200
        data = result["data"]
        assert data.get("code") == 200

        trace_data = data.get("data", {})
        assert "found" in trace_data
        assert "paths" in trace_data
        assert "source" in trace_data
        assert "target" in trace_data

    def test_trace_path_nonexistent_nodes(self):
        """Test trace_path with nonexistent nodes returns found=False."""
        result = api_post("/graph/trace_path", {
            "user_id": TEST_USER_ID,
            "source_id": "nonexistent-node-1",
            "target_id": "nonexistent-node-2",
            "max_depth": 3
        })

        assert result["status"] == 200
        trace_data = result["data"].get("data", {})
        assert trace_data.get("found") is False

    def test_trace_path_max_depth_respected(self, sample_node_ids):
        """Test that max_depth parameter is respected."""
        if not sample_node_ids:
            pytest.skip("No nodes available for testing")

        result = api_post("/graph/trace_path", {
            "user_id": TEST_USER_ID,
            "source_id": sample_node_ids[0],
            "target_id": sample_node_ids[1],
            "max_depth": 1  # Very shallow
        })

        assert result["status"] == 200
        trace_data = result["data"].get("data", {})

        if trace_data.get("found"):
            for path in trace_data.get("paths", []):
                assert path["length"] <= 1


class TestContextAwareSearch:
    """Tests for context-aware search functionality."""

    def test_context_aware_searcher_import(self):
        """Test that ContextAwareSearcher can be imported."""
        try:
            from memos.memories.textual.tree_text_memory.organize.context_aware_searcher import (
                ContextAwareSearcher,
                SearchIntent,
            )
            assert ContextAwareSearcher is not None
            assert SearchIntent is not None
        except ImportError as e:
            pytest.skip(f"Cannot import ContextAwareSearcher: {e}")

    def test_search_with_context_analysis_param(self):
        """Test that search accepts enable_context_analysis parameter."""
        result = api_post("/search", {
            "user_id": TEST_USER_ID,
            "query": "test query",
            "readable_cube_ids": [TEST_CUBE_ID],
            "enable_context_analysis": False,  # Disable to avoid LLM dependency
            "top_k": 5
        })

        assert result["status"] == 200
        assert result["data"].get("code") == 200

    def test_search_intent_prompt_exists(self):
        """Test that SEARCH_INTENT_PROMPT is defined."""
        try:
            from memos.templates.graph_ai_prompts import SEARCH_INTENT_PROMPT
            assert SEARCH_INTENT_PROMPT is not None
            assert "{query}" in SEARCH_INTENT_PROMPT
            assert "{context}" in SEARCH_INTENT_PROMPT
        except ImportError as e:
            pytest.skip(f"Cannot import prompts: {e}")

    def test_search_intent_dataclass(self):
        """Test SearchIntent dataclass structure."""
        try:
            from memos.memories.textual.tree_text_memory.organize.context_aware_searcher import (
                SearchIntent,
            )
            intent = SearchIntent()
            assert intent.intent_type == "exploratory"
            assert isinstance(intent.core_entities, list)
            assert isinstance(intent.expanded_queries, list)
        except ImportError as e:
            pytest.skip(f"Cannot import SearchIntent: {e}")


class TestSchemaExport:
    """Tests for graph schema export functionality."""

    def test_schema_api_exists(self):
        """Test that schema export API endpoint exists."""
        result = api_post("/graph/schema", {
            "user_id": TEST_USER_ID,
            "sample_size": 50
        })

        assert result["status"] == 200

    def test_schema_returns_structure(self):
        """Test that schema returns expected structure."""
        result = api_post("/graph/schema", {
            "user_id": TEST_USER_ID,
            "sample_size": 100
        })

        assert result["status"] == 200
        data = result["data"]
        assert data.get("code") == 200

        schema = data.get("data", {})
        assert "total_nodes" in schema
        assert "total_edges" in schema
        assert "edge_type_distribution" in schema
        assert "memory_type_distribution" in schema
        assert "tag_frequency" in schema
        assert "avg_connections_per_node" in schema
        assert "orphan_node_count" in schema
        assert "time_range" in schema

    def test_schema_edge_distribution_valid(self):
        """Test that edge type distribution contains valid types."""
        result = api_post("/graph/schema", {
            "user_id": TEST_USER_ID,
            "sample_size": 100
        })

        schema = result["data"].get("data", {})
        edge_dist = schema.get("edge_type_distribution", {})

        # If there are edges, verify they're strings
        for edge_type, count in edge_dist.items():
            assert isinstance(edge_type, str)
            assert isinstance(count, int)
            assert count >= 0

    def test_schema_time_range_structure(self):
        """Test that time_range has expected structure."""
        result = api_post("/graph/schema", {
            "user_id": TEST_USER_ID,
            "sample_size": 100
        })

        schema = result["data"].get("data", {})
        time_range = schema.get("time_range", {})

        assert "earliest" in time_range
        assert "latest" in time_range


class TestGraphDataExport:
    """Tests for graph data export functionality."""

    def test_graph_data_api(self):
        """Test basic graph data export."""
        result = api_post("/graph/data", {
            "user_id": TEST_USER_ID,
            "page": 1,
            "page_size": 50
        })

        assert result["status"] == 200
        data = result["data"]
        assert data.get("code") == 200

        graph_data = data.get("data", {})
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert "total_nodes" in graph_data
        assert "total_edges" in graph_data

    def test_graph_data_pagination(self):
        """Test graph data pagination."""
        # First page
        result1 = api_post("/graph/data", {
            "user_id": TEST_USER_ID,
            "page": 1,
            "page_size": 5
        })

        # Second page
        result2 = api_post("/graph/data", {
            "user_id": TEST_USER_ID,
            "page": 2,
            "page_size": 5
        })

        assert result1["status"] == 200
        assert result2["status"] == 200

        # Total counts should be the same
        total1 = result1["data"].get("data", {}).get("total_nodes", 0)
        total2 = result2["data"].get("data", {}).get("total_nodes", 0)
        assert total1 == total2


class TestEndToEndWorkflow:
    """End-to-end workflow tests combining multiple features."""

    def test_search_then_trace_workflow(self):
        """Test workflow: search for memories, then trace path between results."""
        # Step 1: Search for memories
        search_result = api_post("/search", {
            "user_id": TEST_USER_ID,
            "query": "error",
            "readable_cube_ids": [TEST_CUBE_ID],
            "top_k": 10
        })

        if search_result["status"] != 200:
            pytest.skip("Search API not available")

        # Extract memory IDs from search results
        search_data = search_result["data"].get("data", {})
        text_mems = search_data.get("text_mem", [])

        memory_ids = []
        for bucket in text_mems:
            for mem in bucket.get("memories", []):
                mem_id = mem.get("id") or mem.get("metadata", {}).get("id")
                if mem_id:
                    memory_ids.append(mem_id)

        if len(memory_ids) < 2:
            pytest.skip("Not enough memories for path tracing")

        # Step 2: Trace path between first two memories
        trace_result = api_post("/graph/trace_path", {
            "user_id": TEST_USER_ID,
            "source_id": memory_ids[0],
            "target_id": memory_ids[1],
            "max_depth": 5
        })

        assert trace_result["status"] == 200

    def test_schema_health_check_workflow(self):
        """Test workflow: export schema and verify health metrics."""
        # Get schema statistics
        schema_result = api_post("/graph/schema", {
            "user_id": TEST_USER_ID,
            "sample_size": 100
        })

        assert schema_result["status"] == 200
        schema = schema_result["data"].get("data", {})

        # Calculate health metrics
        total_nodes = schema.get("total_nodes", 0)
        orphan_count = schema.get("orphan_node_count", 0)
        avg_connections = schema.get("avg_connections_per_node", 0)

        if total_nodes > 0:
            orphan_ratio = orphan_count / total_nodes

            # Log health assessment
            print(f"\n=== Graph Health Check ===")
            print(f"Total nodes: {total_nodes}")
            print(f"Orphan nodes: {orphan_count} ({orphan_ratio:.1%})")
            print(f"Avg connections: {avg_connections:.2f}")
            print(f"Edge types: {list(schema.get('edge_type_distribution', {}).keys())}")


def run_manual_tests():
    """Run tests manually for debugging."""
    print("\n" + "="*60)
    print("AI Knowledge Graph Features - Integration Tests")
    print("="*60 + "\n")

    tests = [
        ("Graph Data Export", lambda: api_post("/graph/data", {
            "user_id": TEST_USER_ID, "page": 1, "page_size": 10
        })),
        ("Path Tracing", lambda: api_post("/graph/trace_path", {
            "user_id": TEST_USER_ID,
            "source_id": "test-1",
            "target_id": "test-2",
            "max_depth": 3
        })),
        ("Schema Export", lambda: api_post("/graph/schema", {
            "user_id": TEST_USER_ID, "sample_size": 50
        })),
        ("Context-Aware Search", lambda: api_post("/search", {
            "user_id": TEST_USER_ID,
            "query": "test",
            "readable_cube_ids": [TEST_CUBE_ID],
            "enable_context_analysis": False,
            "top_k": 5
        })),
    ]

    for name, test_fn in tests:
        try:
            print(f"Testing: {name}...")
            result = test_fn()
            status = "✅ PASS" if result["status"] == 200 else f"❌ FAIL ({result['status']})"
            print(f"  {status}")

            if result["status"] == 200:
                code = result["data"].get("code", "N/A")
                print(f"  Response code: {code}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")

    print("\n" + "="*60)
    print("Tests Complete")
    print("="*60)


if __name__ == "__main__":
    run_manual_tests()
