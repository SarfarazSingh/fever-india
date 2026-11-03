"""Apply ownership-correct table restrictions and create private document storage."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from sqlalchemy import text
from app.config import get_settings
from app.database import engine


async def main():
    settings = get_settings()
    if not settings.production or not settings.supabase_service_role_key:
        raise RuntimeError("Private database setup requires production settings")
    sql = Path(__file__).with_name("supabase_security.sql").read_text()
    async with engine.begin() as db:
        await db.execute(text(sql))
    url = settings.supabase_url.rstrip("/") + "/storage/v1/bucket"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": "Bearer " + settings.supabase_service_role_key,
    }
    bucket = {
        "id": "travel-documents", "name": "travel-documents", "public": False,
        "file_size_limit": 10_000_000, "allowed_mime_types": ["application/pdf"],
    }
    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        response = await client.get(url + "/travel-documents")
        if response.status_code == 404 or (
            response.status_code == 400 and response.json().get("statusCode") == "404"
        ):
            response = await client.post(url, json=bucket)
            if response.status_code == 409:
                response = await client.get(url + "/travel-documents")
        elif response.status_code == 200:
            response = await client.put(url + "/travel-documents", json=bucket)
        if response.status_code >= 400:
            raise RuntimeError("Could not configure the private document bucket")
    await engine.dispose()
    print("Private tables and document storage configured")


if __name__ == "__main__":
    asyncio.run(main())
