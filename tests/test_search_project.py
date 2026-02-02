
import requests


print("Script started...")

def test_search():
    url = "http://localhost:18000/search"
    payload = {
        "query": "ddsp",
        "user_id": "dev_user",
        "install_cube_ids": ["ddsp_svc_6_3_cube"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Search Results:")
            # Extract textual memories
            text_mems = data.get("data", {}).get("text_mem", [])
            for cube_res in text_mems:
                cube_id = cube_res.get("cube_id")
                memories = cube_res.get("memories", [])
                print(f"\nCube: {cube_id} ({len(memories)} memories)")
                for mem in memories:
                    # Check if project_name exists
                    project_name = mem.get("project_name")
                    content = mem.get("memory", "")[:100] + "..."
                    print(f"  - Project: {project_name}")
                    print(f"    Content: {content}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_search()
