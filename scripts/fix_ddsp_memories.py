import logging
import os
import sys

from dotenv import load_dotenv


# Set project root and python path
PROJECT_ROOT = "G:/test/MemOS"
sys.path.append(os.path.join(PROJECT_ROOT, "src"))

# Import MemOS components
try:
    from memos.api.config import APIConfig
    from memos.configs.mem_os import MOSConfig
    from memos.mem_os.main import MOS
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def fix_ddsp_memories():
    load_dotenv(override=True)
    
    # Initialize MOS
    print("Initializing MemOS...")
    default_cfg = APIConfig.get_product_default_config()
    config = MOSConfig(**default_cfg)
    mos = MOS(config=config)
    
    cube_id = "ddsp_svc_6_3_cube"
    user_id = "dev_user"
    
    # Find cube path
    cubes_dir = os.environ.get("MEMOS_CUBES_DIR", "data/memos_cubes")
    if not os.path.isabs(cubes_dir):
        cubes_dir = os.path.abspath(os.path.join(PROJECT_ROOT, cubes_dir))
        
    cube_path = os.path.join(cubes_dir, cube_id)
    if not os.path.exists(cube_path):
        logger.error(f"Cube path not found: {cube_path}")
        return

    print(f"Registering cube: {cube_id} at {cube_path}")
    try:
        mos.register_mem_cube(
            mem_cube_name_or_path=cube_path,
            mem_cube_id=cube_id,
            user_id=user_id
        )
    except Exception as e:
        logger.info(f"Note: {e}")

    # Get the cube
    cube = mos.mem_cubes.get(cube_id)
    if not cube:
        logger.error(f"Cube {cube_id} not found after registration")
        return
        
    if not cube.text_mem:
        logger.error(f"Cube {cube_id} has no textual memory")
        return
    
    # Get the graph store
    graph_store = cube.text_mem.graph_store
    
    # Get all memory nodes from Neo4j
    # We query all nodes with label Memory
    print("Fetching all memory nodes from Neo4j...")
    query = "MATCH (n:Memory) RETURN n"
    
    with graph_store.driver.session(database=graph_store.db_name) as session:
        result = session.run(query)
        records = list(result)
        
    print(f"Found {len(records)} nodes in Neo4j")
    
    if not records:
        print("No nodes found to update.")
        return

    # Update nodes with project_name using Cypher
    print("Updating nodes with project_name using Cypher...")
    update_query = """
    MATCH (n:Memory)
    SET n.project_name = 'ddsp-svc-6.3'
    RETURN count(n) as updated_count
    """
    
    with graph_store.driver.session(database=graph_store.db_name) as session:
        result = session.run(update_query)
        updated_count = result.single()["updated_count"]
        
    print(f"Successfully updated {updated_count} nodes with project_name='ddsp-svc-6.3'")

if __name__ == "__main__":
    fix_ddsp_memories()
