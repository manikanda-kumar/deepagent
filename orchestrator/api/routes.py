"""
FastAPI REST API endpoints for task management.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ..config import get_settings, Settings
from ..core import get_task_queue, TaskQueue
from ..db import TaskStatus as DBTaskStatus
from .models import (
    ErrorCode,
    ErrorResponse,
    HealthResponse,
    TaskCreate,
    TaskListResponse,
    TaskLogEntry,
    TaskResponse,
    TaskResult,
    TaskStatus,
    TaskType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["tasks"])


def get_correlation_id() -> str:
    """Generate a correlation ID for request tracing."""
    return str(uuid.uuid4())


# Health check
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        database="connected",
    )


# Task endpoints
@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
)
async def create_task(
    task_data: TaskCreate,
    queue: TaskQueue = Depends(get_task_queue),
    correlation_id: str = Depends(get_correlation_id),
):
    """
    Submit a new task for processing.

    The task will be queued and processed by a background worker.
    """
    logger.info(
        f"Creating task: {task_data.title}",
        extra={"correlation_id": correlation_id, "task_type": task_data.type.value},
    )

    try:
        task = await queue.enqueue(
            task_type=task_data.type.value,
            title=task_data.title,
            description=task_data.description,
            config=task_data.config,
            delivery=task_data.delivery.model_dump() if task_data.delivery else None,
            attachments=task_data.attachments,
            correlation_id=correlation_id,
        )

        return TaskResponse(
            id=task.id,
            type=TaskType(task.type),
            title=task.title,
            description=task.description,
            status=TaskStatus(task.status.value),
            attempts=task.attempts,
            max_attempts=task.max_attempts,
            created_at=task.created_at,
            queued_at=task.queued_at,
        )

    except Exception as e:
        logger.exception("Failed to create task")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "code": ErrorCode.INTERNAL_ERROR.value},
        )


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    queue: TaskQueue = Depends(get_task_queue),
):
    """List all tasks with optional filtering."""
    offset = (page - 1) * page_size

    # Convert API status to DB status if provided
    db_status = None
    if status_filter:
        db_status = DBTaskStatus(status_filter.value)

    tasks, total = await queue.list_tasks(
        status=db_status,
        limit=page_size,
        offset=offset,
    )

    return TaskListResponse(
        tasks=[
            TaskResponse(
                id=task.id,
                type=TaskType(task.type),
                title=task.title,
                description=task.description,
                status=TaskStatus(task.status.value),
                attempts=task.attempts,
                max_attempts=task.max_attempts,
                created_at=task.created_at,
                queued_at=task.queued_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                last_error=task.last_error,
            )
            for task in tasks
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_task(
    task_id: str,
    queue: TaskQueue = Depends(get_task_queue),
):
    """Get task details by ID."""
    task = await queue.get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": f"Task {task_id} not found",
                "code": ErrorCode.TASK_NOT_FOUND.value,
            },
        )

    return TaskResponse(
        id=task.id,
        type=TaskType(task.type),
        title=task.title,
        description=task.description,
        status=TaskStatus(task.status.value),
        attempts=task.attempts,
        max_attempts=task.max_attempts,
        created_at=task.created_at,
        queued_at=task.queued_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        last_error=task.last_error,
    )


@router.get(
    "/tasks/{task_id}/result",
    response_model=TaskResult,
    responses={404: {"model": ErrorResponse}},
)
async def get_task_result(
    task_id: str,
    include_logs: bool = Query(False),
    queue: TaskQueue = Depends(get_task_queue),
):
    """Get task result including output summary and cloud links."""
    task = await queue.get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": f"Task {task_id} not found",
                "code": ErrorCode.TASK_NOT_FOUND.value,
            },
        )

    logs = None
    if include_logs:
        log_entries = await queue.get_task_logs(task_id)
        logs = [
            {
                "id": log.id,
                "level": log.level,
                "event": log.event,
                "message": log.message,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in log_entries
        ]

    return TaskResult(
        task_id=task.id,
        status=TaskStatus(task.status.value),
        summary=task.result_summary,
        outputs_path=task.outputs_path,
        cloud_links=task.cloud_links,
        logs=logs,
    )


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def cancel_task(
    task_id: str,
    queue: TaskQueue = Depends(get_task_queue),
):
    """
    Cancel a pending or running task.

    Cannot cancel already completed tasks.
    """
    task = await queue.get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": f"Task {task_id} not found",
                "code": ErrorCode.TASK_NOT_FOUND.value,
            },
        )

    if task.status in (DBTaskStatus.COMPLETED, DBTaskStatus.DEAD, DBTaskStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Cannot cancel completed task",
                "code": ErrorCode.TASK_ALREADY_COMPLETED.value,
            },
        )

    # Cancel the task
    cancelled = await queue.cancel(task_id)

    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Failed to cancel task",
                "code": ErrorCode.TASK_ALREADY_COMPLETED.value,
            },
        )

    # If task is running, also cancel the Claude process
    if task.status == DBTaskStatus.RUNNING:
        from ..core import get_claude_runner
        runner = get_claude_runner()
        await runner.cancel_task(task_id)

    return None


@router.get("/tasks/{task_id}/logs", response_model=list[TaskLogEntry])
async def get_task_logs(
    task_id: str,
    limit: int = Query(100, ge=1, le=500),
    queue: TaskQueue = Depends(get_task_queue),
):
    """Get logs for a specific task."""
    task = await queue.get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": f"Task {task_id} not found",
                "code": ErrorCode.TASK_NOT_FOUND.value,
            },
        )

    logs = await queue.get_task_logs(task_id, limit=limit)

    return [
        TaskLogEntry(
            id=log.id,
            task_id=log.task_id,
            level=log.level,
            event=log.event,
            message=log.message,
            data=log.data,
            timestamp=log.timestamp,
            correlation_id=log.correlation_id,
        )
        for log in logs
    ]


# Stats endpoint
@router.get("/stats")
async def get_stats(
    queue: TaskQueue = Depends(get_task_queue),
):
    """Get queue statistics."""
    return await queue.get_queue_stats()
