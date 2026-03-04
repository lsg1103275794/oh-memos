
import asyncio
import os
import sys


# Add src to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from oh_memos.api.config import APIConfig
from oh_memos.api.start_api import UserRole
from oh_memos.mem_os.core import MOSConfig
from oh_memos.mem_os.main import MOS


async def fix_user():
    config = APIConfig.get_product_default_config()
    mos_config = MOSConfig(**config)
    mos = MOS(mos_config)
    # await mos.initialize()  # No initialize method in MOSCore
    
    user_manager = mos.user_manager
    user_id = "dev_user"
    
    # Check if user exists
    users = user_manager.list_users()
    user_ids = [u.user_id for u in users]
    print(f"Current user IDs: {user_ids}")
    
    if user_id not in user_ids:
        print(f"Creating user {user_id}...")
        user_manager.create_user(user_name=user_id, role=UserRole.ADMIN, user_id=user_id)
        print(f"User {user_id} created.")
    else:
        print(f"User {user_id} already exists.")
    
    # Ensure user is active (if there's such a concept, usually just existence is enough)
    # Some systems might need a specific "activation" or "login" to init the user's home cube
    
    # Let's try to get or create the dev_cube for this user
    cube_id = "dev_cube"
    cubes = mos.list_mem_cubes(user_id=user_id)
    print(f"User {user_id} cubes: {cubes}")
    
    if cube_id not in cubes:
        print(f"Registering cube {cube_id} for user {user_id}...")
        # Path should be absolute
        cube_path = os.path.join(os.getcwd(), "..", "data", "memos_cubes", "dev_cube")
        await mos.register_mem_cube(user_id, cube_id, cube_path)
        print(f"Cube {cube_id} registered.")
    
    print("Done.")

if __name__ == "__main__":
    asyncio.run(fix_user())
