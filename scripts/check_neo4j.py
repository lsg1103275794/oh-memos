
from neo4j import GraphDatabase


def check_neo4j_nodes():
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "12345678"
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        # Check total count
        result = session.run("MATCH (n:Memory) RETURN count(n) as count")
        print(f"Total Memory nodes: {result.single()['count']}")
        
        # Check a few nodes for properties
        result = session.run("MATCH (n:Memory) RETURN n LIMIT 5")
        for record in result:
            node = record["n"]
            print(f"\nNode ID: {node.get('id')}")
            print(f"Properties: {list(node.keys())}")
            print(f"project_name: {node.get('project_name')}")
            print(f"user_name: {node.get('user_name')}")
            
        # Check nodes with specific project_name
        result = session.run("MATCH (n:Memory) WHERE n.project_name = 'ddsp-svc-6.3' RETURN count(n) as count")
        print(f"\nNodes with project_name='ddsp-svc-6.3': {result.single()['count']}")
        
        # Check nodes with specific project_name AND user_name
        result = session.run("MATCH (n:Memory) WHERE n.project_name = 'ddsp-svc-6.3' AND n.user_name = 'dev_user' RETURN count(n) as count")
        print(f"Nodes with project_name='ddsp-svc-6.3' AND user_name='dev_user': {result.single()['count']}")

    driver.close()

if __name__ == "__main__":
    check_neo4j_nodes()
