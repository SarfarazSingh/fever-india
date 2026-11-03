"""Initialize the pinned Procrastinate schema once; safe to repeat on deploy."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.v1.jobs import queue


async def main():
    async with queue.open_async():
        async with queue.connector.pool.connection() as conn:
            # Serialize competing deployment hooks before checking schema presence.
            await conn.execute("SELECT pg_advisory_xact_lock(746812390)")
            await conn.execute("CREATE SCHEMA IF NOT EXISTS jobs")
            await conn.execute("REVOKE ALL ON SCHEMA jobs FROM PUBLIC")
            await conn.execute("SET LOCAL search_path=jobs,public")
            cursor = await conn.execute("SELECT to_regclass('jobs.procrastinate_jobs')")
            exists = (await cursor.fetchone())[0]
            if exists is None:
                await conn.execute(queue.schema_manager.get_schema())
                print("Initialized durable job schema")
            else:
                print("Durable job schema already initialized")


if __name__ == "__main__":
    asyncio.run(main())
