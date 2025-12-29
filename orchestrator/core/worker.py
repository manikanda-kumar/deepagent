"""
Background worker for processing tasks from the queue.
"""

import asyncio
import logging
import signal
from typing import Optional

from ..config import get_settings
from ..db import init_db
from .claude_runner import get_claude_runner
from .result_processor import get_result_processor
from .task_queue import get_task_queue

logger = logging.getLogger(__name__)


class Worker:
    """
    Background worker that polls for tasks and processes them.

    Features:
    - Polls queue at configurable interval
    - Executes Claude runner for each task
    - Processes results (uploads, notifications)
    - Handles graceful shutdown
    """

    def __init__(self):
        self.settings = get_settings()
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._current_task_id: Optional[str] = None

    async def start(self) -> None:
        """Start the worker loop."""
        logger.info("Starting background worker")
        self._running = True
        self._shutdown_event.clear()

        # Initialize database
        await init_db(self.settings.database_url)

        # Get component instances
        queue = get_task_queue()
        runner = get_claude_runner()
        processor = get_result_processor()

        poll_interval = self.settings.worker_poll_interval_seconds

        while self._running:
            try:
                # Check for shutdown
                if self._shutdown_event.is_set():
                    break

                # Try to get next task
                task = await queue.dequeue()

                if task is None:
                    # No tasks available, wait before polling again
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=poll_interval,
                        )
                    except asyncio.TimeoutError:
                        pass
                    continue

                # Process the task
                self._current_task_id = task.id
                logger.info(
                    f"Processing task {task.id}: {task.title}",
                    extra={"task_id": task.id, "task_type": task.type},
                )

                try:
                    # Execute Claude
                    result = await runner.execute_task(task)

                    if result.success:
                        # Mark as processing
                        await queue.mark_processing(task.id)

                        # Process results (upload, notify)
                        processing = await processor.process(task, result.output)

                        # Mark as completed
                        await queue.mark_completed(
                            task_id=task.id,
                            summary=processing.summary,
                            cloud_links=processing.cloud_links,
                        )

                        logger.info(
                            f"Task {task.id} completed successfully",
                            extra={
                                "task_id": task.id,
                                "duration": result.duration_seconds,
                                "notification_sent": processing.notification_sent,
                            },
                        )
                    else:
                        # Mark as failed (will retry if attempts < max)
                        new_status = await queue.mark_failed(
                            task_id=task.id,
                            error=result.error or "Unknown error",
                            retry=not result.partial,  # Don't retry on cancellation
                        )

                        logger.warning(
                            f"Task {task.id} failed: {result.error}",
                            extra={
                                "task_id": task.id,
                                "new_status": new_status.value,
                                "partial": result.partial,
                            },
                        )

                except Exception as e:
                    logger.exception(f"Error processing task {task.id}")
                    await queue.mark_failed(
                        task_id=task.id,
                        error=str(e),
                        retry=True,
                    )

                finally:
                    self._current_task_id = None

            except Exception as e:
                logger.exception("Worker loop error")
                await asyncio.sleep(poll_interval)

        logger.info("Worker stopped")

    async def stop(self) -> None:
        """Signal the worker to stop gracefully."""
        logger.info("Stopping worker...")
        self._running = False
        self._shutdown_event.set()

        # Cancel current task if running
        if self._current_task_id:
            logger.info(f"Cancelling current task {self._current_task_id}")
            runner = get_claude_runner()
            await runner.cancel_task(self._current_task_id)


# Global worker instance
_worker: Optional[Worker] = None


def get_worker() -> Worker:
    """Get or create the global worker instance."""
    global _worker
    if _worker is None:
        _worker = Worker()
    return _worker


async def run_worker() -> None:
    """Run the worker as a standalone process."""
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    worker = get_worker()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        asyncio.create_task(worker.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await worker.start()
    except asyncio.CancelledError:
        pass
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
