"""
Claude Code CLI wrapper with timeout enforcement and cancellation support.
"""

import asyncio
import json
import logging
import os
import signal
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import get_settings
from ..db.models import Task

logger = logging.getLogger(__name__)


@dataclass
class ClaudeResult:
    """Result from Claude Code CLI execution."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    turns_used: int = 0
    partial: bool = False  # True if execution was interrupted


class ClaudeRunner:
    """
    Manages Claude Code CLI execution for tasks.

    Features:
    - Task type to prompt mapping
    - Timeout enforcement per task type
    - Graceful cancellation via SIGTERM
    - Partial result saving on timeout/cancel
    """

    def __init__(self):
        self.settings = get_settings()
        self.prompts_path = self.settings.claude_path / "prompts"
        self.skills_path = self.settings.skills_path
        self._active_processes: Dict[str, asyncio.subprocess.Process] = {}

    async def execute_task(self, task: Task) -> ClaudeResult:
        """
        Execute a task using Claude Code CLI.

        Args:
            task: The Task to execute

        Returns:
            ClaudeResult with success status and output/error
        """
        start_time = datetime.utcnow()

        # Ensure output directory exists
        outputs_path = Path(task.outputs_path)
        outputs_path.mkdir(parents=True, exist_ok=True)

        # Build the prompt
        prompt = self._build_prompt(task)

        # Get task-specific settings
        timeout = self.settings.get_task_timeout(task.type)
        max_turns = self.settings.get_task_max_turns(task.type)

        # Build Claude CLI command
        cmd, prompt_text = self._build_command(task, prompt, max_turns, outputs_path)

        logger.info(
            f"Executing Claude for task {task.id}",
            extra={
                "task_id": task.id,
                "task_type": task.type,
                "timeout": timeout,
                "max_turns": max_turns,
            }
        )

        try:
            result = await self._run_claude(
                task_id=task.id,
                cmd=cmd,
                prompt=prompt_text,
                timeout=timeout,
                cwd=outputs_path,
            )

            duration = (datetime.utcnow() - start_time).total_seconds()
            result.duration_seconds = duration

            if result.success:
                logger.info(
                    f"Claude completed task {task.id} in {duration:.1f}s",
                    extra={"task_id": task.id, "duration": duration}
                )
            else:
                logger.warning(
                    f"Claude failed task {task.id}: {result.error}",
                    extra={"task_id": task.id, "error": result.error}
                )

            return result

        except asyncio.CancelledError:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Claude execution cancelled for task {task.id}",
                extra={"task_id": task.id, "duration": duration}
            )
            return ClaudeResult(
                success=False,
                error="Execution cancelled",
                duration_seconds=duration,
                partial=True,
            )

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task by sending SIGTERM to its Claude process.

        Returns True if a process was found and signaled.
        """
        process = self._active_processes.get(task_id)
        if process is None:
            return False

        try:
            # Send SIGTERM for graceful shutdown
            process.send_signal(signal.SIGTERM)
            logger.info(f"Sent SIGTERM to Claude process for task {task_id}")

            # Wait briefly for graceful shutdown
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # Force kill if still running
                process.kill()
                logger.warning(f"Force killed Claude process for task {task_id}")

            return True
        except ProcessLookupError:
            # Process already terminated
            return True
        finally:
            self._active_processes.pop(task_id, None)

    def _build_prompt(self, task: Task) -> str:
        """Build the full prompt for Claude from task details."""
        # Load base prompt template if it exists
        prompt_file = self.prompts_path / f"{task.type}.md"
        if prompt_file.exists():
            base_prompt = prompt_file.read_text()
        else:
            base_prompt = self._get_default_prompt(task.type)

        # Build task-specific context
        task_context = f"""
## Task Details
- **Title**: {task.title}
- **Description**: {task.description}
- **Output Directory**: {task.outputs_path}
"""

        # Add config if present
        if task.config:
            task_context += f"\n## Configuration\n```json\n{json.dumps(task.config, indent=2)}\n```\n"

        # Add attachment references if present
        if task.attachment_refs:
            task_context += "\n## Attachments\n"
            for ref in task.attachment_refs:
                task_context += f"- {ref}\n"

        # Add delivery instructions if present
        if task.delivery:
            delivery = task.delivery
            task_context += "\n## Delivery Instructions\n"
            if delivery.get("email"):
                task_context += f"- Send notification to: {delivery['email']}\n"
            if delivery.get("storage"):
                folder = delivery.get("folder", "DeepAgent/Results")
                task_context += f"- Upload to {delivery['storage']}: {folder}\n"

        return f"{base_prompt}\n\n{task_context}"

    def _get_default_prompt(self, task_type: str) -> str:
        """Get default prompt for a task type if no template exists."""
        prompts = {
            "research": """# Research Task

You are a research agent. Your job is to thoroughly research the given topic and produce a comprehensive report.

## Instructions
1. Use web search and browser tools to gather information
2. Cite all sources with URLs
3. Organize findings into clear sections
4. Save the final report as markdown in the output directory
5. Include a summary at the beginning
""",
            "analysis": """# Analysis Task

You are a data analysis agent. Your job is to analyze the given data or topic and produce insights.

## Instructions
1. Gather relevant data using available tools
2. Analyze patterns and trends
3. Create visualizations if appropriate
4. Save the analysis report as markdown in the output directory
5. Include key findings at the beginning
""",
            "document": """# Document Generation Task

You are a document generation agent. Your job is to create professional documents based on the given requirements.

## Instructions
1. Follow the provided template or format requirements
2. Research any needed information
3. Generate clear, well-structured content
4. Save the document in the output directory
5. Review for accuracy and formatting
""",
        }
        return prompts.get(task_type, prompts["research"])

    def _build_command(
        self,
        task: Task,
        prompt: str,
        max_turns: int,
        outputs_path: Path,
    ) -> tuple[List[str], str]:
        """Build the Claude CLI command and return (cmd, prompt)."""
        cmd = [
            "claude",
            "--print",  # Non-interactive mode
            "--output-format", "json",
            "--dangerously-skip-permissions",  # For automation
        ]

        # Add allowed tools based on task type
        allowed_tools = self._get_allowed_tools(task.type)
        if allowed_tools:
            cmd.extend(["--allowedTools", allowed_tools])

        # Prompt will be passed via stdin
        return cmd, prompt

    def _get_allowed_tools(self, task_type: str) -> str:
        """Get comma-separated list of allowed tools for task type."""
        base_tools = ["Read", "Write", "Bash", "Glob", "Grep", "Edit"]

        if task_type == "research":
            tools = base_tools + ["WebFetch", "WebSearch", "Task"]
        elif task_type == "analysis":
            tools = base_tools + ["WebFetch", "Task"]
        else:
            tools = base_tools

        return ",".join(tools)

    async def _run_claude(
        self,
        task_id: str,
        cmd: List[str],
        prompt: str,
        timeout: int,
        cwd: Path,
    ) -> ClaudeResult:
        """Run Claude CLI with timeout and process tracking."""
        env = os.environ.copy()

        # Set Claude-specific environment
        if self.settings.anthropic_api_key:
            env["ANTHROPIC_API_KEY"] = self.settings.anthropic_api_key
        env["CLAUDE_CODE_SKILLS_PATH"] = str(self.skills_path)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd),
                env=env,
            )

            # Track active process for cancellation
            self._active_processes[task_id] = process

            try:
                # Pass prompt via stdin
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=prompt.encode("utf-8")),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(f"Claude timed out for task {task_id} after {timeout}s")
                await self.cancel_task(task_id)
                return ClaudeResult(
                    success=False,
                    error=f"Execution timed out after {timeout} seconds",
                    partial=True,
                )
            finally:
                self._active_processes.pop(task_id, None)

            stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

            if process.returncode == 0:
                # Try to parse JSON output
                try:
                    output_data = json.loads(stdout_text)
                    turns_used = output_data.get("turns", 0)
                except json.JSONDecodeError:
                    output_data = stdout_text
                    turns_used = 0

                return ClaudeResult(
                    success=True,
                    output=stdout_text,
                    turns_used=turns_used,
                )
            else:
                error_msg = stderr_text or f"Claude exited with code {process.returncode}"
                return ClaudeResult(
                    success=False,
                    error=error_msg,
                    output=stdout_text if stdout_text else None,
                )

        except FileNotFoundError:
            return ClaudeResult(
                success=False,
                error="Claude CLI not found. Is it installed?",
            )
        except Exception as e:
            logger.exception(f"Unexpected error running Claude for task {task_id}")
            return ClaudeResult(
                success=False,
                error=str(e),
            )


# Global runner instance
_claude_runner: Optional[ClaudeRunner] = None


def get_claude_runner() -> ClaudeRunner:
    """Get or create the global Claude runner instance."""
    global _claude_runner
    if _claude_runner is None:
        _claude_runner = ClaudeRunner()
    return _claude_runner
