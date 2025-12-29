"""
Configuration management using pydantic-settings.
Loads settings from environment variables with validation and defaults.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file="/etc/deepagent/env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:////data/db/deepagent.db",
        description="SQLAlchemy database URL",
    )

    # Paths
    outputs_path: Path = Field(
        default=Path("/data/outputs"),
        description="Directory for task output files",
    )
    logs_path: Path = Field(
        default=Path("/data/logs"),
        description="Directory for application logs",
    )
    claude_path: Path = Field(
        default=Path("/app/deepagent/claude"),
        description="Path to Claude scaffolding directory",
    )
    skills_path: Path = Field(
        default=Path("/app/deepagent/claude/skills"),
        description="Path to pi-skills directory",
    )

    # API Security
    api_secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for JWT signing",
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(
        default=1440, description="Access token TTL (24 hours)"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, description="Refresh token TTL"
    )

    # Rate Limiting
    rate_limit_requests_per_second: int = Field(
        default=10, description="Max requests per second per device"
    )
    rate_limit_tasks_per_hour: int = Field(
        default=100, description="Max tasks per hour per device"
    )

    # Payload Limits
    max_request_size_mb: int = Field(
        default=10, description="Max request body size in MB"
    )
    max_attachment_size_mb: int = Field(
        default=25, description="Max single attachment size in MB"
    )
    max_total_attachments_mb: int = Field(
        default=100, description="Max total attachments per task in MB"
    )

    # Task Limits
    research_timeout_minutes: int = Field(
        default=30, description="Max runtime for research tasks"
    )
    analysis_timeout_minutes: int = Field(
        default=20, description="Max runtime for analysis tasks"
    )
    document_timeout_minutes: int = Field(
        default=15, description="Max runtime for document tasks"
    )
    research_max_turns: int = Field(
        default=100, description="Max Claude turns for research tasks"
    )
    analysis_max_turns: int = Field(
        default=50, description="Max Claude turns for analysis tasks"
    )
    document_max_turns: int = Field(
        default=30, description="Max Claude turns for document tasks"
    )

    # Retry Configuration
    max_task_attempts: int = Field(
        default=3, description="Max retry attempts before task is marked dead"
    )
    retry_base_delay_seconds: int = Field(
        default=60, description="Base delay for exponential backoff"
    )
    retry_max_delay_seconds: int = Field(
        default=900, description="Max delay for exponential backoff (15 min)"
    )

    # External Services
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key for Claude"
    )
    brave_api_key: Optional[str] = Field(
        default=None, description="Brave Search API key"
    )
    groq_api_key: Optional[str] = Field(
        default=None, description="Groq API key for transcription"
    )

    # Firebase
    firebase_project_id: Optional[str] = Field(
        default=None, description="Firebase project ID"
    )
    firebase_credentials_path: Optional[Path] = Field(
        default=None, description="Path to Firebase credentials JSON"
    )

    # Server
    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8000, description="Server bind port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Worker
    worker_poll_interval_seconds: int = Field(
        default=5, description="How often worker polls for tasks"
    )
    worker_max_concurrent_tasks: int = Field(
        default=1, description="Max concurrent tasks per worker"
    )

    @field_validator("outputs_path", "logs_path", "claude_path", "skills_path", mode="before")
    @classmethod
    def parse_path(cls, v):
        if isinstance(v, str):
            return Path(v)
        return v

    @field_validator("firebase_credentials_path", mode="before")
    @classmethod
    def parse_optional_path(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return Path(v)
        return v

    def get_task_timeout(self, task_type: str) -> int:
        """Get timeout in seconds for a task type."""
        timeouts = {
            "research": self.research_timeout_minutes * 60,
            "analysis": self.analysis_timeout_minutes * 60,
            "document": self.document_timeout_minutes * 60,
        }
        return timeouts.get(task_type, self.document_timeout_minutes * 60)

    def get_task_max_turns(self, task_type: str) -> int:
        """Get max Claude turns for a task type."""
        turns = {
            "research": self.research_max_turns,
            "analysis": self.analysis_max_turns,
            "document": self.document_max_turns,
        }
        return turns.get(task_type, self.document_max_turns)


# Global settings instance - lazily loaded
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings (useful for testing)."""
    global _settings
    _settings = None
