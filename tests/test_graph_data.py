
import requests


def test_get_graph_data():
    url = "http://localhost:18000/product/graph/data"
    
    # We want to see nodes from ddsp-svc-6.3
    # The filter field expects a dictionary according to APIGraphRequest schema
    payload = {
        "user_id": "dev_user",
        "page": 1,
        "page_size": 100,
        "filter": {"project_name": "ddsp-svc-6.3"}
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            data = result.get("data", {})
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])
            
            print("\nGraph Results:")
            print(f"Total Nodes in result: {len(nodes)}")
            print(f"Total Edges in result: {len(edges)}")
            
            if nodes:
                print("\nSample Nodes (first 5):")
                for i, node in enumerate(nodes[:5]):
                    # Neo4j nodes in our API return properties inside 'metadata'
                    metadata = node.get("metadata", {})
                    project = metadata.get("project_name", "N/A")
                    memory = node.get("memory", "")[:50] + "..."
                    print(f"  {i+1}. [Project: {project}] {memory}")
            
            if edges:
                print("\nSample Edges (first 5):")
                for i, edge in enumerate(edges[:5]):
                    source = edge.get("source", "N/A")
                    target = edge.get("target", "N/A")
                    rel_type = edge.get("type", "N/A")
                    print(f"  {i+1}. {source} --[{rel_type}]--> {target}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    # Ensure the server is running or wait for it
    test_get_graph_data()
