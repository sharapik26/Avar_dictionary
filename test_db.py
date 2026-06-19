import asyncio
import logging
import sys
import os

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set env var
os.environ["DATABASE_URL"] = "postgresql://postgres:Sharapudin1.@db.wzvwsfrqhgishbwoxcfn.supabase.co:5432/postgres"

# Import from bot
sys.path.insert(0, os.path.abspath("bot"))
from db import init_db, add_subscriber, get_all_subscribers

async def main():
    print("Testing init_db...")
    await init_db()
    print("Testing add_subscriber...")
    res = await add_subscriber(12345)
    print("add_subscriber result:", res)
    print("Testing get_all_subscribers...")
    subs = await get_all_subscribers()
    print("get_all_subscribers result:", subs)

if __name__ == "__main__":
    asyncio.run(main())
