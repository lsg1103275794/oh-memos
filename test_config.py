import os
import sys


sys.path.insert(0, 'src')

from dotenv import load_dotenv


load_dotenv(dotenv_path='src/.env', override=True)

print("=== Environment Variables ===")
print(f"MEM_READER_BACKEND: {os.getenv('MEM_READER_BACKEND')}")
print(f"MOS_CHAT_MODEL: {os.getenv('MOS_CHAT_MODEL')}")
print(f"MOS_EMBEDDER_BACKEND: {os.getenv('MOS_EMBEDDER_BACKEND')}")
print(f"OPENAI_API_BASE: {os.getenv('OPENAI_API_BASE')}")

print("\n=== Testing Config ===")
from memos.api.config import APIConfig


print("\nget_reader_config():")
print(APIConfig.get_reader_config())

print("\nget_product_default_config()['mem_reader']:")
config = APIConfig.get_product_default_config()
print(config.get('mem_reader', 'NOT FOUND'))
