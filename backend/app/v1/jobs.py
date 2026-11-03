"""Durable production tasks; development runs the same handlers without PostgreSQL."""

import asyncio
import logging
from datetime import timedelta

import procrastinate
from sqlalchemy import select, update

from app.config import get_settings
from app.database import SessionLocal
from app.models import utcnow
from app.v1.flights import fetch_offers, rank_offers
from app.v1.models import Account, Checkout, SearchRecord, MailConnection, Trip
from app.v1.schemas import SearchRequest

logger = logging.getLogger(__name__)
dsn = get_settings().psycopg_dsn
queue = procrastinate.App(
    connector=procrastinate.PsycopgConnector(
        conninfo=dsn
        if dsn.startswith("postgresql")
        else "postgresql://localhost/concierge",
        options="-c search_path=jobs,public",
    )
)


async def run_search(search_id: str):
    async with SessionLocal() as db:
        claimed = await db.execute(
            update(SearchRecord)
            .where(SearchRecord.id == search_id, SearchRecord.status == "queued")
            .values(status="searching")
        )
        await db.commit()
        if claimed.rowcount != 1:
            return
        row = await db.get(SearchRecord, search_id)
        account = await db.get(Account, row.account_id)
        try:
            req = SearchRequest.model_validate(row.request)
            offers, coverage, partial = await asyncio.wait_for(
                fetch_offers(req, account.is_demo), timeout=55
            )
            # Snapshot inventory before grouping mutates explanations/fare options.
            inventory = [o.model_dump(mode="json") for o in offers]
            ranked, exclusions, adjustments = rank_offers(offers, req.preferences)
            row.result = {
                "results": [o.model_dump(mode="json") for o in ranked],
                "inventory": inventory,
                "total_offers": len(offers),
                "coverage": coverage,
                "exclusions": exclusions,
                "adjustments": adjustments,
                "live_mode": bool(offers and all(o.live_mode for o in offers)),
            }
            row.status = "partial" if partial else "complete"
        except Exception as exc:
            row.status = "failed"
            row.error = (
                "Airline inventory is temporarily unavailable. Please try again."
            )
            logger.warning("Search failed (%s)", type(exc).__name__)
        await db.commit()


@queue.task(name="search", queue="travel", retry=2)
async def search_task(search_id: str):
    await run_search(search_id)


async def dispatch_search(search_id: str):
    if get_settings().production:
        # A periodic sweep recovers a commit/queue gap after a process crash.
        try:
            await search_task.defer_async(search_id=search_id)
        except Exception as exc:
            logger.error("Search enqueue pending recovery (%s)", type(exc).__name__)
    else:
        await run_search(search_id)


@queue.periodic(cron="*/2 * * * *")
@queue.task(name="maintenance", queue="travel", lock="maintenance", retry=2)
async def maintenance(timestamp: int):
    from app.v1.integrations import sync_mailbox, send_reminders, store_documents
    from app.v1.checkout import finish_order
    from app.services.duffel import DuffelClient

    async with SessionLocal() as db:
        queued = (
            (
                await db.execute(
                    select(SearchRecord.id).where(SearchRecord.status == "queued")
                )
            )
            .scalars()
            .all()
        )
        await db.execute(
            update(SearchRecord)
            .where(
                SearchRecord.status == "searching",
                SearchRecord.created_at < utcnow() - timedelta(minutes=3),
            )
            .values(status="failed", error="The search timed out. Please search again.")
        )
        await db.commit()
        for search_id in queued:
            await search_task.defer_async(search_id=search_id)
        connections = (
            (
                await db.execute(
                    select(MailConnection).where(MailConnection.status == "connected")
                )
            )
            .scalars()
            .all()
        )
        for connection in connections:
            try:
                await sync_mailbox(db, connection)
            except Exception as exc:
                logger.warning("Mailbox sync needs retry (%s)", type(exc).__name__)
        pending = (
            (
                await db.execute(
                    select(Checkout).where(
                        Checkout.state.in_(["confirming", "submitting", "confirmed"]),
                        Checkout.created_at < utcnow() - timedelta(seconds=60),
                    )
                )
            )
            .scalars()
            .all()
        )
        provider = None
        for checkout in pending:
            account = await db.get(Account, checkout.account_id)
            if account.is_demo:
                continue
            if checkout.state == "confirmed":
                from datetime import datetime

                last_sync = checkout.data.get("last_provider_sync")
                if last_sync and datetime.fromisoformat(
                    last_sync
                ) > utcnow() - timedelta(minutes=15):
                    continue
                latest = max(
                    datetime.fromisoformat(s["arrival_at"].replace("Z", "+00:00"))
                    for slc in checkout.offer["slices"]
                    for s in slc["segments"]
                )
                if latest < utcnow() - timedelta(days=2):
                    continue
            try:
                provider = provider or DuffelClient(get_settings())
                order = None
                if checkout.provider_order_id:
                    order = (
                        await provider._request(
                            "GET", "/air/orders/" + checkout.provider_order_id
                        )
                    )["data"]
                else:
                    # Reconcile by the persisted metadata key; never submit an order a second time.
                    after = None
                    for _ in range(20):
                        page = await provider._request(
                            "GET",
                            "/air/orders",
                            params={
                                "limit": 200,
                                **({"after": after} if after else {}),
                            },
                        )
                        order = next(
                            (
                                o
                                for o in page.get("data", [])
                                if (o.get("metadata") or {}).get(
                                    "concierge_checkout_id"
                                )
                                == checkout.id
                            ),
                            None,
                        )
                        after = (page.get("meta") or {}).get("after")
                        if order or not after:
                            break
                if order:
                    await finish_order(db, checkout, account, order)
                if checkout.trip_id:
                    await store_documents(db, await db.get(Trip, checkout.trip_id))
            except Exception as exc:
                logger.warning("Order reconciliation pending (%s)", type(exc).__name__)
        await send_reminders(db)
        # Limit retained search data and drafts; never delete unresolved booking attempts.
        from sqlalchemy import delete
        from app.v1.models import ImportDraft, LoginSession, OAuthLoginAttempt

        await db.execute(
            delete(SearchRecord).where(
                SearchRecord.created_at < utcnow() - timedelta(days=7)
            )
        )
        await db.execute(
            delete(ImportDraft).where(
                ImportDraft.created_at < utcnow() - timedelta(days=30)
            )
        )
        await db.execute(delete(LoginSession).where(LoginSession.expires_at < utcnow()))
        await db.execute(
            delete(OAuthLoginAttempt).where(OAuthLoginAttempt.expires_at < utcnow())
        )
        await db.commit()


async def main():
    if not get_settings().production:
        raise RuntimeError(
            "Set ENVIRONMENT=staging or production and DATABASE_URL to PostgreSQL for the worker"
        )
    async with queue.open_async():
        await queue.run_worker_async(queues=["travel"], concurrency=4)


if __name__ == "__main__":
    asyncio.run(main())
