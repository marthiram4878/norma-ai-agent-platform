"""Redis consumer that executes Launch Strategy workflow runs."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.core.logging import configure_logging
from app.database.session import SessionFactory
from app.rag.container import retriever
from app.services.knowledge import KnowledgeService
from app.services.launch_strategy import KnowledgeIngestAdapter, LaunchStrategyService
from app.services.llm import OpenRouterConfigurationError
from app.services.memory import MemoryService
from app.services.queue import LAUNCH_STRATEGY_JOB, JobQueue
from app.workflows.launch_strategy import LaunchStrategyWorkflow

logger = logging.getLogger(__name__)


async def process_job(payload: dict[str, object]) -> None:
    if payload.get("type") != LAUNCH_STRATEGY_JOB:
        logger.warning("Ignoring unknown job type: %s", payload.get("type"))
        return
    run_id = UUID(str(payload["run_id"]))
    async with SessionFactory() as session:
        knowledge = KnowledgeService(session)
        memory = MemoryService(session)
        try:
            from uuid import uuid4

            # Persister is rebound inside execute_run with the run's real space_id.
            workflow = LaunchStrategyWorkflow(
                retriever,
                KnowledgeIngestAdapter(knowledge, space_id=uuid4()),
            )
        except OpenRouterConfigurationError:
            logger.exception("OpenRouter is not configured for worker")
            return
        service = LaunchStrategyService(
            session,
            workflow=workflow,
            knowledge=knowledge,
            memory=memory,
        )
        try:
            await service.execute_run(run_id=run_id)
        finally:
            await workflow.client.close()


async def run_forever() -> None:
    configure_logging()
    queue = JobQueue()
    logger.info("Launch Strategy worker started")
    try:
        while True:
            payload = await queue.dequeue(timeout_seconds=5)
            if payload is None:
                continue
            try:
                await process_job(payload)
            except Exception:
                logger.exception("Failed to process launch strategy job: %s", payload)
    finally:
        await queue.close()


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
