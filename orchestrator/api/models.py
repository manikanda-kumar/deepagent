"""
Pydantic models for API request/response validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TaskType(str, Enum):
    """Supported task types."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    DOCUMENT = "document"


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    DEAD = "dead"


class ErrorCode(str, Enum):
    """API error codes."""
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_ALREADY_COMPLETED = "TASK_ALREADY_COMPLETED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    ATTACHMENT_TOO_LARGE = "ATTACHMENT_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    UNAUTHORIZED = "UNAUTHORIZED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Allowed attachment types
ALLOWED_ATTACHMENT_TYPES = {
    "pdf", "docx", "doc", "txt", "md", "csv", "json", "png", "jpg", "jpeg", "gif"
}


# Request Models

class DeliveryConfig(BaseModel):
    """Delivery preferences for task results."""
    email: Optional[str] = Field(default=None, description="Email address for notifications")
    storage: Optional[str] = Field(
        default=None,
        description="Cloud storage: 'google_drive' or 'onedrive'"
    )
    folder: Optional[str] = Field(
        default=None,
        description="Target folder in cloud storage"
    )

    @field_validator("storage")
    @classmethod
    def validate_storage(cls, v):
        if v is not None and v not in ("google_drive", "onedrive"):
            raise ValueError("storage must be 'google_drive' or 'onedrive'")
        return v


class TaskCreate(BaseModel):
    """Request model for creating a new task."""
    type: TaskType = Field(..., description="Task type")
    title: str = Field(..., max_length=200, description="Task title")
    description: str = Field(..., description="Task description/prompt")
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Task-specific configuration"
    )
    delivery: Optional[DeliveryConfig] = Field(
        default=None,
        description="Delivery preferences"
    )
    attachments: Optional[List[str]] = Field(
        default=None,
        description="List of attachment file paths"
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("description cannot be empty")
        return v.strip()

    @field_validator("attachments")
    @classmethod
    def validate_attachments(cls, v):
        if v is None:
            return v
        for attachment in v:
            ext = attachment.rsplit(".", 1)[-1].lower() if "." in attachment else ""
            if ext not in ALLOWED_ATTACHMENT_TYPES:
                raise ValueError(f"Unsupported file type: {ext}")
        return v


class TaskUpdate(BaseModel):
    """Request model for updating a task (limited fields)."""
    status: Optional[TaskStatus] = None
    delivery: Optional[DeliveryConfig] = None


# Response Models

class TaskResponse(BaseModel):
    """Response model for task details."""
    id: str
    type: TaskType
    title: str
    description: Optional[str] = None
    status: TaskStatus
    attempts: int
    max_attempts: int
    created_at: datetime
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_error: Optional[str] = None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """Response model for listing tasks."""
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


class TaskResult(BaseModel):
    """Response model for task results."""
    task_id: str
    status: TaskStatus
    summary: Optional[str] = None
    outputs_path: Optional[str] = None
    cloud_links: Optional[Dict[str, str]] = None
    logs: Optional[List[Dict[str, Any]]] = None


class TaskLogEntry(BaseModel):
    """Response model for a single log entry."""
    id: int
    task_id: str
    level: str
    event: str
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime
    correlation_id: Optional[str] = None

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Human-readable error message")
    code: ErrorCode = Field(..., description="Machine-readable error code")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    database: str = "connected"
    worker: Optional[str] = None


# Authentication Models

class DeviceRegister(BaseModel):
    """Request model for device registration."""
    name: str = Field(..., max_length=100, description="Device name")
    fcm_token: Optional[str] = Field(
        default=None,
        description="Firebase Cloud Messaging token"
    )

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()


class DeviceRegisterResponse(BaseModel):
    """Response model for device registration."""
    device_id: str
    secret: str  # One-time display of the device secret


class TokenRequest(BaseModel):
    """Request model for token generation."""
    device_id: str
    secret: str


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str
