"""
SQLite-based task queue with retry logic and exponential backoff.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db.models import Task, TaskLog, TaskStatus, get_session


class TaskQueue:
    """
    Manages task lifecycle including enqueue, dequeue, status updates, and retries.
    Uses SQLite with row-level operations for simple queue semantics.
    """

    def __init__(self):
        self.settings = get_settings()

    async def enqueue(
        self,
        task_type: str,
        title: str,
        description: str,
        config: Optional[dict] = None,
        delivery: Optional[dict] = None,
        attachments: Optional[List[str]] = None,
        correlation_id: Optional[str] = None,
    ) -> Task:
        """
        Create and enqueue a new task.

        Returns the created Task with status QUEUED.
        """
        task_id = str(uuid.uuid4())
        outputs_path = str(self.settings.outputs_path / task_id)

        task = Task(
            id=task_id,
            type=task_type,
            title=title,
            description=description,
            config=config,
            delivery=delivery,
            attachment_refs=attachments,
            status=TaskStatus.QUEUED,
            attempts=0,
            max_attempts=self.settings.max_task_attempts,
            outputs_path=outputs_path,
            correlation_id=correlation_id,
            queued_at=datetime.utcnow(),
        )

        async with await get_session() as session:
            session.add(task)
            await self._log_event(
                session, task_id, "info", "task_queued",
                f"Task '{title}' queued for processing",
                correlation_id=correlation_id
            )
            await session.commit()
            await session.refresh(task)

        return task

    async def dequeue(self) -> Optional[Task]:
        """
        Fetch the next available task for processing.

        Returns a task with status RUNNING, or None if no tasks available.
        Tasks in RETRY state are checked for their retry delay.
        """
        now = datetime.utcnow()

        async with await get_session() as session:
            # Find next available task: QUEUED or RETRY with elapsed backoff
            stmt = (
                select(Task)
                .where(
                    (Task.status == TaskStatus.QUEUED) |
                    (
                        (Task.status == TaskStatus.RETRY) &
                        (Task.next_retry_at <= now)
                    )
                )
                .order_by(Task.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )

            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if task is None:
                return None

            # Update to RUNNING
            task.status = TaskStatus.RUNNING
            task.started_at = now
            task.attempts += 1

            await self._log_event(
                session, task.id, "info", "task_started",
                f"Task started (attempt {task.attempts}/{task.max_attempts})",
                correlation_id=task.correlation_id
            )

            await session.commit()
            await session.refresh(task)

        return task

    async def mark_processing(self, task_id: str) -> None:
        """Mark a task as processing (Claude complete, handling results)."""
        async with await get_session() as session:
            stmt = (
                update(Task)
                .where(Task.id == task_id)
                .values(status=TaskStatus.PROCESSING)
            )
            await session.execute(stmt)
            await self._log_event(
                session, task_id, "info", "task_processing",
                "Claude execution complete, processing results"
            )
            await session.commit()

    async def mark_completed(
        self,
        task_id: str,
        summary: Optional[str] = None,
        cloud_links: Optional[dict] = None,
    ) -> None:
        """Mark a task as successfully completed."""
        async with await get_session() as session:
            stmt = (
                update(Task)
                .where(Task.id == task_id)
                .values(
                    status=TaskStatus.COMPLETED,
                    completed_at=datetime.utcnow(),
                    result_summary=summary,
                    cloud_links=cloud_links,
                )
            )
            await session.execute(stmt)
            await self._log_event(
                session, task_id, "info", "task_completed",
                "Task completed successfully"
            )
            await session.commit()

    async def mark_failed(
        self,
        task_id: str,
        error: str,
        retry: bool = True,
    ) -> TaskStatus:
        """
        Mark a task as failed, optionally scheduling a retry.

        Returns the new status (RETRY, DEAD, or FAILED).
        """
        async with await get_session() as session:
            # Get current task state
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()

            if task is None:
                raise ValueError(f"Task {task_id} not found")

            if retry and task.attempts < task.max_attempts:
                # Schedule retry with exponential backoff
                delay = self._calculate_retry_delay(task.attempts)
                next_retry = datetime.utcnow() + timedelta(seconds=delay)

                task.status = TaskStatus.RETRY
                task.last_error = error
                task.next_retry_at = next_retry

                await self._log_event(
                    session, task_id, "warning", "task_retry_scheduled",
                    f"Task failed, retry scheduled in {delay}s: {error}",
                    data={"attempt": task.attempts, "next_retry": next_retry.isoformat()}
                )
            else:
                # Max retries exceeded or no retry requested
                task.status = TaskStatus.DEAD if retry else TaskStatus.FAILED
                task.last_error = error
                task.completed_at = datetime.utcnow()

                event = "task_dead" if retry else "task_failed"
                await self._log_event(
                    session, task_id, "error", event,
                    f"Task failed permanently: {error}",
                    data={"attempts": task.attempts}
                )

            await session.commit()
            return task.status

    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a task if possible.

        Returns True if cancelled, False if task was already completed/cancelled.
        """
        async with await get_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()

            if task is None:
                return False

            # Can only cancel pending/queued/retry tasks
            if task.status in (TaskStatus.COMPLETED, TaskStatus.DEAD, TaskStatus.FAILED):
                return False

            task.status = TaskStatus.FAILED
            task.last_error = "Cancelled by user"
            task.completed_at = datetime.utcnow()

            await self._log_event(
                session, task_id, "info", "task_cancelled",
                "Task cancelled by user"
            )

            await session.commit()
            return True

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        async with await get_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            return result.scalar_one_or_none()

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Task], int]:
        """
        List tasks with optional filtering.

        Returns (tasks, total_count).
        """
        async with await get_session() as session:
            # Build query
            query = select(Task)
            if status:
                query = query.where(Task.status == status)

            # Get total count
            from sqlalchemy import func
            count_query = select(func.count()).select_from(Task)
            if status:
                count_query = count_query.where(Task.status == status)
            count_result = await session.execute(count_query)
            total = count_result.scalar()

            # Get paginated results
            query = query.order_by(Task.created_at.desc()).limit(limit).offset(offset)
            result = await session.execute(query)
            tasks = list(result.scalars().all())

            return tasks, total

    async def get_task_logs(
        self,
        task_id: str,
        limit: int = 100,
    ) -> List[TaskLog]:
        """Get logs for a specific task."""
        async with await get_session() as session:
            result = await session.execute(
                select(TaskLog)
                .where(TaskLog.task_id == task_id)
                .order_by(TaskLog.timestamp.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def get_queue_stats(self) -> dict:
        """Get queue statistics."""
        async with await get_session() as session:
            from sqlalchemy import func

            # Count by status
            result = await session.execute(
                select(Task.status, func.count())
                .group_by(Task.status)
            )
            counts = {str(row[0].value): row[1] for row in result.all()}

            return {
                "queued": counts.get("queued", 0),
                "running": counts.get("running", 0),
                "processing": counts.get("processing", 0),
                "completed": counts.get("completed", 0),
                "failed": counts.get("failed", 0),
                "retry": counts.get("retry", 0),
                "dead": counts.get("dead", 0),
            }

    def _calculate_retry_delay(self, attempt: int) -> int:
        """
        Calculate retry delay with exponential backoff and jitter.

        Formula: min(base * 2^attempt, max) + random jitter (0-10%)
        """
        base = self.settings.retry_base_delay_seconds
        max_delay = self.settings.retry_max_delay_seconds

        delay = min(base * (2 ** attempt), max_delay)
        jitter = random.uniform(0, delay * 0.1)

        return int(delay + jitter)

    async def _log_event(
        self,
        session: AsyncSession,
        task_id: str,
        level: str,
        event: str,
        message: str,
        data: Optional[dict] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Add a log entry for a task."""
        log = TaskLog(
            task_id=task_id,
            level=level,
            event=event,
            message=message,
            data=data,
            correlation_id=correlation_id,
        )
        session.add(log)


# Global queue instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get or create the global task queue instance."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue
