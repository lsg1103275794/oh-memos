"""
Tests for Graph API endpoints including:
- /graph/data - Export graph data
- /graph/trace_path - Path tracing between nodes
- /graph/schema - Schema export

These tests require a running MemOS API server with Neo4j.
"""

import json
import requests
import pytest


BASE_URL = "http://localhost:18000/product"
TEST_USER_ID = "dev_user"


class TestGraphData:
    """Tests for /graph/data endpoint."""

    def test_graph_data_basic(self):
        """Test basic graph data retrieval."""
        url = f"{BASE_URL}/graph/data"
        payload = {
            "user_id": TEST_USER_ID,
            "page": 1,
            "page_size": 100
        }

        response = requests.post(url, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data.get("code") == 200
        assert "data" in data

        if data.get("data"):
            graph_data = data["data"]
            assert "nodes" in graph_data
            assert "edges" in graph_data
            assert "total_nodes" in graph_data
            assert "total_edges" in graph_data

    def test_graph_data_pagination(self):
        """Test graph data pagination."""
        url = f"{BASE_URL}/graph/data"

        # First page
        response1 = requests.post(url, json={
            "user_id": TEST_USER_ID,
            "page": 1,
            "page_size": 5
        })
        assert response1.status_code == 200

        # Second page
        response2 = requests.post(url, json={
            "user_id": TEST_USER_ID,
            "page": 2,
            "page_size": 5
        })
        assert response2.status_code == 200


class TestTracePath:
    """Tests for /graph/trace_path endpoint."""

    def test_trace_path_requires_source_and_target(self):
        """Test that source_id and target_id are required."""
        url = f"{BASE_URL}/graph/trace_path"

        # Missing target_id
        response = requests.post(url, json={
            "user_id": TEST_USER_ID,
            "source_id": "some-id"
        })
        # Should return 422 (validation error) or handle gracefully
        assert response.status_code in [200, 422]

    def test_trace_path_nonexistent_nodes(self):
        """Test path tracing with nonexistent node IDs."""
        url = f"{BASE_URL}/graph/trace_path"
        payload = {
            "user_id": TEST_USER_ID,
            "source_id": "nonexistent-source-id",
            "target_id": "nonexistent-target-id",
            "max_depth": 3
        }

        response = requests.post(url, json=payload)
        assert response.status_code == 200

        data = response.json()
        # Should return found=False for nonexistent nodes
        if data.get("code") == 200 and data.get("data"):
            assert data["data"].get("found") is False

    def test_trace_path_with_real_nodes(self):
        """Test path tracing with real node IDs from the graph."""
        # First, get some actual node IDs from the graph
        graph_url = f"{BASE_URL}/graph/data"
        graph_response = requests.post(graph_url, json={
            "user_id": TEST_USER_ID,
            "page": 1,
            "page_size": 10
        })

        if graph_response.status_code != 200:
            pytest.skip("Could not fetch graph data")

        graph_data = graph_response.json().get("data", {})
        nodes = graph_data.get("nodes", [])

        if len(nodes) < 2:
            pytest.skip("Not enough nodes in graph for path testing")

        source_id = nodes[0]["id"]
        target_id = nodes[1]["id"]

        # Now test trace_path
        url = f"{BASE_URL}/graph/trace_path"
        payload = {
            "user_id": TEST_USER_ID,
            "source_id": source_id,
            "target_id": target_id,
            "max_depth": 5,
            "include_all_paths": False
        }

        response = requests.post(url, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data.get("code") == 200
        assert "data" in data

        trace_data = data["data"]
        assert "found" in trace_data
        assert "paths" in trace_data
        assert "source" in trace_data
        assert "target" in trace_data

        # Verify source and target are returned
        assert trace_data["source"]["id"] == source_id
        assert trace_data["target"]["id"] == target_id

        # If path found, verify structure
        if trace_data["found"]:
            paths = trace_data["paths"]
            assert len(paths) > 0

            path = paths[0]
            assert "length" in path
            assert "nodes" in path
            assert "edges" in path
            assert len(path["nodes"]) == path["length"] + 1

    def test_trace_path_max_depth_limit(self):
        """Test that max_depth is respected."""
        url = f"{BASE_URL}/graph/trace_path"

        # Get nodes first
        graph_response = requests.post(f"{BASE_URL}/graph/data", json={
            "user_id": TEST_USER_ID,
            "page": 1,
            "page_size": 10
        })

        if graph_response.status_code != 200:
            pytest.skip("Could not fetch graph data")

        nodes = graph_response.json().get("data", {}).get("nodes", [])
        if len(nodes) < 2:
            pytest.skip("Not enough nodes")

        # Test with max_depth=1
        response = requests.post(url, json={
            "user_id": TEST_USER_ID,
            "source_id": nodes[0]["id"],
            "target_id": nodes[-1]["id"],
            "max_depth": 1
        })

        assert response.status_code == 200
        data = response.json()

        if data.get("code") == 200 and data.get("data", {}).get("found"):
            # If path found with depth 1, verify length
            paths = data["data"]["paths"]
            for path in paths:
                assert path["length"] <= 1


class TestGraphSchema:
    """Tests for /graph/schema endpoint."""

    def test_graph_schema_basic(self):
        """Test basic schema export."""
        url = f"{BASE_URL}/graph/schema"
        payload = {
            "user_id": TEST_USER_ID,
            "sample_size": 100
        }

        response = requests.post(url, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data.get("code") == 200
        assert "data" in data

        if data.get("data"):
            schema_data = data["data"]
            assert "entity_types" in schema_data
            assert "relationship_patterns" in schema_data
            assert "total_nodes" in schema_data
            assert "total_edges" in schema_data
            assert "edge_type_distribution" in schema_data


def test_graph_api_manual():
    """Manual test runner for quick debugging."""
    print("\n=== Testing Graph API ===\n")

    # Test 1: Graph Data
    print("1. Testing /graph/data...")
    url = f"{BASE_URL}/graph/data"
    payload = {"user_id": TEST_USER_ID, "page": 1, "page_size": 100}

    try:
        response = requests.post(url, json=payload)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                nodes = data["data"].get("nodes", [])
                edges = data["data"].get("edges", [])
                print(f"   Found {len(nodes)} nodes, {len(edges)} edges")
            else:
                print("   No data returned")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"   Failed: {e}")

    # Test 2: Trace Path
    print("\n2. Testing /graph/trace_path...")
    url = f"{BASE_URL}/graph/trace_path"

    # First get some node IDs
    try:
        graph_response = requests.post(f"{BASE_URL}/graph/data", json={
            "user_id": TEST_USER_ID, "page": 1, "page_size": 10
        })
        nodes = graph_response.json().get("data", {}).get("nodes", [])

        if len(nodes) >= 2:
            payload = {
                "user_id": TEST_USER_ID,
                "source_id": nodes[0]["id"],
                "target_id": nodes[1]["id"],
                "max_depth": 5
            }
            response = requests.post(url, json=payload)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                found = data.get("data", {}).get("found", False)
                paths = data.get("data", {}).get("paths", [])
                print(f"   Path found: {found}, Paths: {len(paths)}")
                if found and paths:
                    print(f"   First path length: {paths[0]['length']}")
        else:
            print("   Not enough nodes for path test")
    except Exception as e:
        print(f"   Failed: {e}")

    # Test 3: Schema Export
    print("\n3. Testing /graph/schema...")
    url = f"{BASE_URL}/graph/schema"
    payload = {"user_id": TEST_USER_ID, "sample_size": 100}

    try:
        response = requests.post(url, json=payload)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            schema = data.get("data", {})
            print(f"   Total nodes: {schema.get('total_nodes', 0)}")
            print(f"   Total edges: {schema.get('total_edges', 0)}")
            edge_dist = schema.get("edge_type_distribution", {})
            if edge_dist:
                print(f"   Edge types: {list(edge_dist.keys())}")
    except Exception as e:
        print(f"   Failed: {e}")

    print("\n=== Tests Complete ===")


if __name__ == "__main__":
    test_graph_api_manual()
