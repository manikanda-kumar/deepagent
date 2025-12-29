"""
SQLAlchemy database models for task management.
"""

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class TaskStatus(str, enum.Enum):
    """Task lifecycle states."""
    PENDING = "pending"        # Task submitted, not yet validated
    QUEUED = "queued"          # Validated and waiting for worker
    RUNNING = "running"        # Worker executing Claude
    PROCESSING = "processing"  # Claude done, processing results
    COMPLETED = "completed"    # Success - results delivered
    FAILED = "failed"          # Execution failed
    RETRY = "retry"            # Waiting for retry attempt
    DEAD = "dead"              # Max retries exceeded


class TaskType(str, enum.Enum):
    """Supported task types."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    DOCUMENT = "document"


class Task(Base):
    """
    Main task model representing a user-submitted task.

    State transitions:
    PENDING -> QUEUED -> RUNNING -> PROCESSING -> COMPLETED
                                 -> FAILED -> RETRY -> QUEUED
                                           -> DEAD (max attempts)
    """
    __tablename__ = "tasks"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID

    # Task definition
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    delivery: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Task state
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Retry scheduling
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Output references
    outputs_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cloud_links: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)

    # Attachments (list of file paths)
    attachment_refs: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Correlation ID for request tracing
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, type={self.type}, status={self.status.value})>"


class TaskLog(Base):
    """
    Structured log entries for task execution.
    Enables detailed debugging and audit trails.
    """
    __tablename__ = "task_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Log details
    level: Mapped[str] = mapped_column(String(10), nullable=False)  # info, warning, error
    event: Mapped[str] = mapped_column(String(50), nullable=False)  # task_started, claude_invoked, etc.
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional structured data
    data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Timing and tracing
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    def __repr__(self) -> str:
        return f"<TaskLog(task_id={self.task_id}, event={self.event}, level={self.level})>"


class Device(Base):
    """
    Registered devices for authentication.
    """
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Authentication
    hashed_secret: Mapped[str] = mapped_column(String(256), nullable=False)

    # FCM for push notifications
    fcm_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Integer, default=True)  # SQLite doesn't have bool

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, name={self.name})>"


# Database connection helpers

_async_engine = None
_async_session_factory = None


async def init_db(database_url: str) -> None:
    """Initialize async database connection and create tables."""
    global _async_engine, _async_session_factory

    _async_engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
    )

    _async_session_factory = async_sessionmaker(
        _async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create all tables
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Get a database session."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _async_session_factory()


async def close_db() -> None:
    """Close database connections."""
    global _async_engine, _async_session_factory
    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
