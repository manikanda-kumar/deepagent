"""
Result processor for handling Claude output, cloud uploads, and notifications.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ..config import get_settings
from ..db.models import Task

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Result of a cloud upload operation."""
    success: bool
    url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class NotificationResult:
    """Result of a notification operation."""
    success: bool
    error: Optional[str] = None


@dataclass
class ProcessingResult:
    """Combined result of all post-processing operations."""
    summary: Optional[str] = None
    cloud_links: Optional[Dict[str, str]] = None
    upload_errors: Optional[List[str]] = None
    notification_sent: bool = False
    notification_error: Optional[str] = None


class ResultProcessor:
    """
    Processes Claude output and handles result delivery.

    Features:
    - Extract summary from output files
    - Upload results to Google Drive (via gdcli)
    - Upload results to OneDrive (via onedrive-cli)
    - Send email notifications (via gmcli)
    """

    def __init__(self):
        self.settings = get_settings()

    async def process(self, task: Task, claude_output: Optional[str] = None) -> ProcessingResult:
        """
        Process task results and handle delivery.

        Args:
            task: The completed task
            claude_output: Raw output from Claude CLI

        Returns:
            ProcessingResult with summary, links, and notification status
        """
        result = ProcessingResult()

        outputs_path = Path(task.outputs_path)

        # Extract summary from output
        result.summary = await self._extract_summary(outputs_path, claude_output)

        # Handle cloud uploads if configured
        if task.delivery:
            storage = task.delivery.get("storage")
            folder = task.delivery.get("folder", "DeepAgent/Results")

            if storage:
                result.cloud_links = {}
                result.upload_errors = []

                if storage in ("google_drive", "both"):
                    upload = await self._upload_to_gdrive(outputs_path, folder, task.id)
                    if upload.success:
                        result.cloud_links["google_drive"] = upload.url
                    else:
                        result.upload_errors.append(f"Google Drive: {upload.error}")

                if storage in ("onedrive", "both"):
                    upload = await self._upload_to_onedrive(outputs_path, folder, task.id)
                    if upload.success:
                        result.cloud_links["onedrive"] = upload.url
                    else:
                        result.upload_errors.append(f"OneDrive: {upload.error}")

            # Send email notification
            email = task.delivery.get("email")
            if email:
                notification = await self._send_email(
                    to=email,
                    task=task,
                    summary=result.summary,
                    cloud_links=result.cloud_links,
                )
                result.notification_sent = notification.success
                result.notification_error = notification.error

        return result

    async def _extract_summary(
        self,
        outputs_path: Path,
        claude_output: Optional[str],
    ) -> Optional[str]:
        """Extract a summary from the task output."""
        # Look for common output files
        summary_files = [
            "README.md",
            "summary.md",
            "report.md",
            "output.md",
            "result.md",
        ]

        for filename in summary_files:
            filepath = outputs_path / filename
            if filepath.exists():
                content = filepath.read_text()
                return self._extract_first_section(content)

        # Look for any markdown file
        md_files = list(outputs_path.glob("*.md"))
        if md_files:
            content = md_files[0].read_text()
            return self._extract_first_section(content)

        # Fall back to Claude output
        if claude_output:
            return self._extract_first_section(claude_output)

        return None

    def _extract_first_section(self, content: str, max_length: int = 500) -> str:
        """Extract the first meaningful section from markdown content."""
        lines = content.strip().split("\n")
        summary_lines = []
        in_code_block = False

        for line in lines:
            # Track code blocks
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # Skip empty lines at the start
            if not summary_lines and not line.strip():
                continue

            # Stop at second heading
            if line.startswith("#") and summary_lines:
                break

            summary_lines.append(line)

            # Check length
            if sum(len(l) for l in summary_lines) > max_length:
                break

        summary = "\n".join(summary_lines).strip()

        # Truncate if too long
        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(" ", 1)[0] + "..."

        return summary

    async def _upload_to_gdrive(
        self,
        outputs_path: Path,
        folder: str,
        task_id: str,
    ) -> UploadResult:
        """Upload results to Google Drive using gdcli."""
        try:
            # Create task-specific folder
            target_folder = f"{folder}/{task_id}"

            # Upload each file in outputs directory
            files = list(outputs_path.glob("*"))
            files = [f for f in files if f.is_file() and not f.name.startswith(".")]

            if not files:
                return UploadResult(
                    success=False,
                    error="No files to upload",
                )

            # Upload files using gdcli
            for file in files:
                cmd = ["gdcli", "upload", str(file), target_folder]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    error = stderr.decode() if stderr else f"Exit code {process.returncode}"
                    logger.warning(f"Failed to upload {file.name} to Google Drive: {error}")
                    return UploadResult(success=False, error=error)

            # Get shareable link for the folder
            cmd = ["gdcli", "share", target_folder, "--anyone", "--role", "reader"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                # Parse the URL from output
                output = stdout.decode()
                url_match = re.search(r"https://drive\.google\.com/[^\s]+", output)
                url = url_match.group(0) if url_match else f"gdrive://{target_folder}"
            else:
                url = f"gdrive://{target_folder}"

            logger.info(f"Uploaded {len(files)} files to Google Drive: {target_folder}")
            return UploadResult(success=True, url=url)

        except FileNotFoundError:
            return UploadResult(
                success=False,
                error="gdcli not found. Is pi-skills installed?",
            )
        except Exception as e:
            logger.exception("Error uploading to Google Drive")
            return UploadResult(success=False, error=str(e))

    async def _upload_to_onedrive(
        self,
        outputs_path: Path,
        folder: str,
        task_id: str,
    ) -> UploadResult:
        """Upload results to OneDrive using onedrive-cli."""
        try:
            target_folder = f"{folder}/{task_id}"

            # Upload each file
            files = list(outputs_path.glob("*"))
            files = [f for f in files if f.is_file() and not f.name.startswith(".")]

            if not files:
                return UploadResult(
                    success=False,
                    error="No files to upload",
                )

            for file in files:
                target_path = f"{target_folder}/{file.name}"
                cmd = ["onedrive", "cp", str(file), target_path]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    error = stderr.decode() if stderr else f"Exit code {process.returncode}"
                    logger.warning(f"Failed to upload {file.name} to OneDrive: {error}")
                    return UploadResult(success=False, error=error)

            # Make folder shareable
            cmd = ["onedrive", "chmod", target_folder, "+r"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode()
                url_match = re.search(r"https://[^\s]+", output)
                url = url_match.group(0) if url_match else f"onedrive://{target_folder}"
            else:
                url = f"onedrive://{target_folder}"

            logger.info(f"Uploaded {len(files)} files to OneDrive: {target_folder}")
            return UploadResult(success=True, url=url)

        except FileNotFoundError:
            return UploadResult(
                success=False,
                error="onedrive-cli not found. Is it installed?",
            )
        except Exception as e:
            logger.exception("Error uploading to OneDrive")
            return UploadResult(success=False, error=str(e))

    async def _send_email(
        self,
        to: str,
        task: Task,
        summary: Optional[str],
        cloud_links: Optional[Dict[str, str]],
    ) -> NotificationResult:
        """Send email notification using gmcli."""
        try:
            subject = f"Task Complete: {task.title}"

            # Build email body
            body_parts = [
                f"Your task '{task.title}' has been completed.",
                "",
            ]

            if summary:
                body_parts.extend([
                    "## Summary",
                    summary,
                    "",
                ])

            if cloud_links:
                body_parts.append("## Results")
                for service, url in cloud_links.items():
                    service_name = "Google Drive" if service == "google_drive" else "OneDrive"
                    body_parts.append(f"- {service_name}: {url}")
                body_parts.append("")

            body_parts.extend([
                "---",
                "Generated by DeepAgent",
            ])

            body = "\n".join(body_parts)

            # Send via gmcli
            cmd = [
                "gmcli", "send",
                "--to", to,
                "--subject", subject,
                "--body", body,
            ]

            # Attach main output file if small enough
            outputs_path = Path(task.outputs_path)
            main_file = self._find_main_output(outputs_path)
            if main_file and main_file.stat().st_size < 10 * 1024 * 1024:  # < 10MB
                cmd.extend(["--attach", str(main_file)])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"Email notification sent to {to}")
                return NotificationResult(success=True)
            else:
                error = stderr.decode() if stderr else f"Exit code {process.returncode}"
                logger.warning(f"Failed to send email to {to}: {error}")
                return NotificationResult(success=False, error=error)

        except FileNotFoundError:
            return NotificationResult(
                success=False,
                error="gmcli not found. Is pi-skills installed?",
            )
        except Exception as e:
            logger.exception("Error sending email notification")
            return NotificationResult(success=False, error=str(e))

    def _find_main_output(self, outputs_path: Path) -> Optional[Path]:
        """Find the main output file for attachment."""
        # Priority order for main output
        candidates = [
            "report.pdf",
            "report.md",
            "output.pdf",
            "output.md",
            "README.md",
            "summary.md",
        ]

        for name in candidates:
            path = outputs_path / name
            if path.exists():
                return path

        # Fall back to first PDF or MD file
        for ext in ["*.pdf", "*.md"]:
            files = list(outputs_path.glob(ext))
            if files:
                return files[0]

        return None


# Global processor instance
_result_processor: Optional[ResultProcessor] = None


def get_result_processor() -> ResultProcessor:
    """Get or create the global result processor instance."""
    global _result_processor
    if _result_processor is None:
        _result_processor = ResultProcessor()
    return _result_processor
