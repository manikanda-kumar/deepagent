# DeepAgent - Personal Research Agent

## Overview

A personal AI-powered research agent that performs automated document generation, reporting, and deep research tasks. Inspired by Abacus AI's DeepAgent, built for individual use with Claude Code CLI as the AI backbone.

## Repository Structure

```
deepagent/
├── SPEC.md
├── README.md
├── .gitignore
│
├── app/                          # Flutter mobile app
│   ├── pubspec.yaml
│   ├── lib/
│   │   ├── main.dart
│   │   ├── models/
│   │   ├── screens/
│   │   ├── services/
│   │   └── widgets/
│   ├── android/
│   ├── ios/
│   └── test/
│
├── orchestrator/                 # FastAPI backend
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── models.py
│   │   └── websocket.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── task_queue.py
│   │   ├── claude_runner.py
│   │   └── result_processor.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── models.py
│   └── tests/
│
├── claude/                       # Claude Code scaffolding
│   ├── prompts/
│   │   ├── researcher.md
│   │   ├── document_gen.md
│   │   └── analyzer.md
│   ├── skills/                   # Symlinks to pi-skills
│   │   └── .gitkeep
│   ├── CLAUDE.md                 # Project instructions for Claude
│   └── templates/
│       ├── research_task.json
│       ├── analysis_task.json
│       └── document_task.json
│
├── scripts/                      # Deployment & setup scripts
│   ├── init.sh                   # VM initialization
│   ├── setup-oauth.sh            # OAuth setup helper
│   └── deploy.sh                 # Deployment script
│
└── docs/                         # Additional documentation
    ├── API.md
    ├── DEPLOYMENT.md
    └── CONTRIBUTING.md
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Mobile App (Flutter)                        │
│                    Task Submission + Notifications                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   iximiuz Playground VM (via labctl)                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Orchestrator Service (FastAPI)                  │   │
│  │              - Task Queue (SQLite)                           │   │
│  │              - Claude Code Session Manager                   │   │
│  │              - Result Processor                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                │                                    │
│                                ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      Claude Code CLI                         │   │
│  │                                                              │   │
│  │   ┌─────────────────── pi-skills ───────────────────────┐   │   │
│  │   │  browser-tools  gdcli  gmcli  brave-search         │   │   │
│  │   │  youtube-transcript  transcribe                     │   │   │
│  │   └─────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │   ┌─────────────────────────────────────────────────────┐   │   │
│  │   │              onedrive-cli                            │   │   │
│  │   └─────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │   ┌─────────────────────────────────────────────────────┐   │   │
│  │   │         Agent Prompts (researcher, analyzer)         │   │   │
│  │   └─────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## External Dependencies

### GitHub Repositories

| Repository | Purpose | Integration |
|------------|---------|-------------|
| [iximiuz/labctl](https://github.com/iximiuz/labctl) | VM lifecycle management | Start/stop VMs, SSH access, port forwarding |
| [badlogic/pi-skills](https://github.com/badlogic/pi-skills) | CLI tools for Claude Code | Browser, Google Drive, Gmail, Search, YouTube |
| [lionello/onedrive-cli](https://github.com/lionello/onedrive-cli) | OneDrive file operations | Upload/download results to OneDrive |
| [steipete/agent-scripts](https://github.com/steipete/agent-scripts) | Utility helpers | Optional: committer, docs-list utilities |

### pi-skills Tools Used

| Tool | Purpose | Commands |
|------|---------|----------|
| `browser-tools` | Web browsing via CDP | Navigate, screenshot, execute JS, scrape |
| `gdcli` | Google Drive | Upload, download, list, share files |
| `gmcli` | Gmail | Send emails with attachments |
| `brave-search` | Web search | Structured search results |
| `youtube-transcript` | Video research | Extract transcripts from YouTube |
| `transcribe` | Audio processing | Audio-to-text via Whisper |

---

## Components

### 1. Mobile App (Flutter)

**Purpose**: User interface for task submission and result notifications

**Phase 1 Features**:
- Task submission form with natural language input
- Task type selection (Research / Document Generation / Analysis)
- Attachment support (upload reference files)
- Push notifications on task completion
- Task history and status view
- Result preview with cloud storage links

**Phase 2 Features**:
- Real-time progress updates (WebSocket)
- Scheduled/recurring task creation
- In-app result viewer
- Voice input for task submission

### 2. Orchestrator Service (Python)

**Purpose**: Lightweight backend running on iximiuz VM that manages task lifecycle

**Location**: `orchestrator/`

**Structure**:
```
orchestrator/
├── pyproject.toml             # Python project config
├── requirements.txt           # Dependencies
├── config.py                  # Configuration
├── api/
│   ├── __init__.py
│   ├── routes.py              # REST API endpoints
│   ├── models.py              # Pydantic models
│   └── websocket.py           # Real-time updates (Phase 2)
├── core/
│   ├── __init__.py
│   ├── task_queue.py          # SQLite-based task management
│   ├── claude_runner.py       # Claude Code CLI session manager
│   └── result_processor.py    # Process and store results
├── db/
│   ├── __init__.py
│   └── models.py              # SQLAlchemy models
└── tests/
    └── __init__.py
```

**Task States**:
```
PENDING → QUEUED → RUNNING → PROCESSING → COMPLETED
                           ↘ FAILED → RETRY (max 3) → DEAD
```

**State Transitions**:
| From | To | Trigger |
|------|-----|---------|
| PENDING | QUEUED | Task accepted, validated |
| QUEUED | RUNNING | Worker picks up task |
| RUNNING | PROCESSING | Claude execution complete, processing results |
| PROCESSING | COMPLETED | Results uploaded, notification sent |
| RUNNING | FAILED | Claude error, timeout, or skill failure |
| FAILED | RETRY | Attempt < max_attempts |
| RETRY | QUEUED | Backoff elapsed |
| FAILED | DEAD | max_attempts exceeded |

#### Data Models

**SQLAlchemy Task Model** (`db/models.py`):
```python
from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime

Base = declarative_base()

class TaskStatus(enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    DEAD = "dead"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)  # UUID
    type = Column(String, nullable=False)  # research, analysis, document
    title = Column(String, nullable=False)
    description = Column(String)
    config = Column(JSON)  # Task-specific configuration
    delivery = Column(JSON)  # Email, storage preferences

    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_error = Column(String)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    queued_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Output references
    outputs_path = Column(String)  # /data/outputs/{task_id}/
    result_summary = Column(String)
    cloud_links = Column(JSON)  # {"gdrive": "...", "onedrive": "..."}

    # Attachments
    attachment_refs = Column(JSON)  # List of uploaded file paths

class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, nullable=False)
    level = Column(String)  # info, warning, error
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    correlation_id = Column(String)  # For request tracing
```

**Pydantic Request/Response Models** (`api/models.py`):
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TaskType(str, Enum):
    RESEARCH = "research"
    ANALYSIS = "analysis"
    DOCUMENT = "document"

class TaskCreate(BaseModel):
    type: TaskType
    title: str = Field(..., max_length=200)
    description: str
    config: Optional[Dict[str, Any]] = None
    delivery: Optional[Dict[str, Any]] = None
    attachments: Optional[List[str]] = None

class TaskResponse(BaseModel):
    id: str
    type: TaskType
    title: str
    status: str
    attempts: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

class TaskResult(BaseModel):
    task_id: str
    status: str
    summary: Optional[str]
    outputs_path: Optional[str]
    cloud_links: Optional[Dict[str, str]]
    logs: Optional[List[Dict[str, Any]]]

class ErrorResponse(BaseModel):
    error: str
    code: str  # e.g., "TASK_NOT_FOUND", "VALIDATION_ERROR"
    details: Optional[Dict[str, Any]] = None
```

#### Execution & Resilience

**Background Worker Architecture**:
- Claude execution runs in a background worker process, not on the request thread
- FastAPI handles task submission and status queries only
- Worker picks tasks from SQLite queue with row-level locking

**Task Limits**:
| Task Type | Max Runtime | Max Turns | Timeout Action |
|-----------|-------------|-----------|----------------|
| research | 30 min | 100 | Cancel + partial save |
| analysis | 20 min | 50 | Cancel + partial save |
| document | 15 min | 30 | Cancel + partial save |

**Retry Strategy**:
```python
# Exponential backoff with jitter
def get_retry_delay(attempt: int) -> int:
    base_delay = 60  # 1 minute
    max_delay = 900  # 15 minutes
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter
```

**Cancellation**:
- Tasks can be cancelled via `DELETE /api/v1/tasks/{id}`
- Running Claude processes terminated via SIGTERM
- Partial results saved before cleanup

#### Observability

**Structured Logging**:
```python
# All logs include correlation IDs
{
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "info",
    "request_id": "req-abc123",
    "task_id": "task-xyz789",
    "event": "task_started",
    "message": "Starting Claude execution for research task"
}
```

**Key Events**:
- `task_accepted`: Task submitted and validated
- `task_queued`: Added to worker queue
- `task_started`: Worker began processing
- `claude_invoked`: Claude CLI started
- `claude_completed`: Claude CLI finished
- `upload_success` / `upload_failed`: Cloud storage result
- `email_success` / `email_failed`: Notification result
- `task_completed` / `task_failed`: Final status

**Metrics** (logged to stdout for systemd):
- `tasks_queued`: Current queue depth
- `tasks_running`: Active worker count
- `tasks_completed_total`: Cumulative successes
- `tasks_failed_total`: Cumulative failures
- `claude_duration_seconds`: Execution time histogram
- `retry_count`: Retries per task

### 3. Claude Code Scaffolding

**Purpose**: Agent prompts, task templates, and skill configuration for Claude Code CLI

**Location**: `claude/`

**Structure**:
```
claude/
├── CLAUDE.md                    # Project instructions for Claude Code
├── prompts/
│   ├── researcher.md            # Deep research agent prompt
│   ├── document_gen.md          # Document generation prompt
│   └── analyzer.md              # Data analysis prompt
├── skills/                      # Symlinks to pi-skills (created on VM)
│   └── .gitkeep
└── templates/
    ├── research_task.json       # Research task schema
    ├── analysis_task.json       # Analysis task schema
    └── document_task.json       # Document generation schema
```

**CLAUDE.md** - Project context for Claude Code sessions:
```markdown
# DeepAgent Project

You are running as part of the DeepAgent research automation system.

## Available Tools
- browser-tools: Web browsing via CDP
- gdcli: Google Drive operations
- gmcli: Gmail operations
- brave-search: Web search
- youtube-transcript: YouTube transcript extraction
- onedrive: OneDrive file operations

## Output Requirements
- Save all outputs to /data/outputs/{task_id}/
- Generate markdown reports by default
- Include source citations for all research
- Upload final results to cloud storage
```

### 4. Claude Code CLI Integration

**Execution Model** (in `orchestrator/core/claude_runner.py`):
```python
import subprocess
import json
import os
from pathlib import Path

class ClaudeRunner:
    def __init__(self, claude_path: str = "/app/deepagent/claude"):
        self.claude_path = Path(claude_path)
        self.prompts_path = self.claude_path / "prompts"
        self.skills_path = self.claude_path / "skills"

    def execute_task(self, task: Task) -> Result:
        # Load prompt template
        prompt_file = self.prompts_path / f"{task.type}.md"
        base_prompt = prompt_file.read_text()

        # Build full prompt with task context
        prompt = self.build_prompt(base_prompt, task)

        # Execute via Claude Code CLI
        result = subprocess.run([
            "claude", "-p", prompt,
            "--output-format", "json",
            "--max-turns", "50",
            "--allowedTools", self.get_allowed_tools(task)
        ],
        capture_output=True,
        cwd=str(self.claude_path),
        env={**os.environ, "CLAUDE_CODE_SKILLS_PATH": str(self.skills_path)}
        )

        return self.parse_result(result)

    def get_allowed_tools(self, task: Task) -> str:
        """Return comma-separated list of allowed tools based on task type"""
        base_tools = ["Read", "Write", "Bash", "Glob", "Grep"]

        if task.type == "research":
            return ",".join(base_tools + ["WebFetch", "WebSearch"])
        elif task.type == "analysis":
            return ",".join(base_tools + ["WebFetch"])
        else:
            return ",".join(base_tools)
```

### 5. Tool Capabilities (via pi-skills)

#### browser-tools (CDP-based)
```bash
# Managed Chrome instance with DevTools Protocol
browser-tools navigate "https://example.com"
browser-tools screenshot output.png
browser-tools execute "document.title"
browser-tools search "query" --engine brave
```

- Navigate and scrape web pages
- Handle JavaScript-rendered content
- Screenshot capture for reports
- X.com/Twitter data extraction
- RSS feed parsing

#### gdcli (Google Drive)
```bash
# OAuth handled automatically
gdcli upload report.pdf "DeepAgent/Reports/"
gdcli download "DeepAgent/Inputs/data.csv" ./
gdcli list "DeepAgent/Reports/"
gdcli share report.pdf --anyone --role reader
```

#### gmcli (Gmail)
```bash
# Send task completion emails
gmcli send \
  --to user@example.com \
  --subject "Research Complete: AI Trends" \
  --body "Your research is ready..." \
  --attach report.pdf
```

#### brave-search
```bash
# Structured web search results
brave-search "Bitter Lesson AI Engineering 2024" --count 10
```

#### youtube-transcript
```bash
# Extract transcripts for research
youtube-transcript "https://youtube.com/watch?v=..." --output transcript.txt
```

#### onedrive-cli
```bash
# OneDrive file operations
onedrive login
onedrive cp report.pdf "DeepAgent/Reports/"
onedrive ls "DeepAgent/"
onedrive chmod report.pdf +r  # Make shareable
```

### 6. Cloud Storage Integration

#### Google Drive (via gdcli)
- OAuth 2.0 authentication (handled by gdcli)
- File upload/download
- Folder organization: `DeepAgent/{Tasks,Reports,Inputs}/`
- Shared link generation

#### OneDrive (via onedrive-cli)
- OAuth 2.0 authentication (handled by onedrive-cli)
- File upload/download
- Folder organization: `DeepAgent/{Tasks,Reports,Inputs}/`
- Shared link generation

### 7. Email Delivery (via gmcli)
- Task completion notifications
- Result summary in email body
- Cloud storage links embedded
- Attachment support (< 25MB Gmail limit)

---

## Use Cases

### Use Case 1: RSS Feed Daily Summary

**Input**:
```json
{
  "type": "research",
  "title": "Daily Tech News Summary",
  "description": "From list of RSS feeds, create daily summary of new articles",
  "config": {
    "feeds": [
      "https://news.ycombinator.com/rss",
      "https://feeds.arstechnica.com/arstechnica/technology-lab",
      "https://www.theverge.com/rss/index.xml"
    ],
    "lookback_hours": 24,
    "output_format": "markdown"
  }
}
```

**Execution Flow**:
1. Claude Code fetches each RSS feed
2. Parses and filters articles from last 24 hours
3. Uses `brave-search` for additional context on key stories
4. Generates categorized markdown summary
5. Uploads to Google Drive via `gdcli`
6. Sends email notification via `gmcli`

**Output**: Markdown document with categorized article summaries, key insights, and source links.

### Use Case 2: Technical Research

**Input**:
```json
{
  "type": "research",
  "title": "macOS/iOS App Development for labctl",
  "description": "Research how to build macOS/iOS app as front-end interface for labctl CLI utility",
  "config": {
    "topics": [
      "SwiftUI app architecture",
      "CLI wrapper patterns in Swift",
      "macOS menu bar apps",
      "iOS companion apps"
    ],
    "depth": "comprehensive",
    "include_code_examples": true
  }
}
```

**Execution Flow**:
1. `brave-search` for each topic
2. `browser-tools` to navigate and scrape Apple documentation
3. `youtube-transcript` for relevant WWDC sessions
4. Claude synthesizes findings into comprehensive document
5. Upload and notify via `gdcli` + `gmcli`

**Output**: Comprehensive research document with architecture recommendations, code examples, and implementation roadmap.

### Use Case 3: Social Media Trend Analysis

**Input**:
```json
{
  "type": "analysis",
  "title": "Bitter Lesson Trends on X.com",
  "description": "Analyze recent trends on 'Bitter Lesson' in AI Engineering from X.com",
  "config": {
    "platform": "x.com",
    "search_terms": ["Bitter Lesson", "AI Engineering", "Rich Sutton"],
    "timeframe": "last_7_days",
    "analysis_type": ["sentiment", "key_themes", "influential_voices"]
  }
}
```

**Execution Flow**:
1. `browser-tools` navigates to X.com search
2. Scrapes tweets matching search terms
3. Claude analyzes sentiment and extracts themes
4. Generates analysis report with embedded screenshots
5. Upload and notify

**Output**: Analysis report with key discussion themes, notable tweets, and sentiment breakdown.

---

## Technical Specifications

### iximiuz VM Setup

**Init Script** (`scripts/init.sh`):
```bash
#!/bin/bash
set -e

# System dependencies
apt-get update && apt-get install -y \
    python3.11 python3.11-venv python3-pip \
    nodejs npm \
    chromium-browser \
    git curl jq

# Create dedicated user for orchestrator
useradd -r -m -s /bin/bash deepagent || true

# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Install onedrive-cli
pip install onedrive-cli

# Clone pi-skills
git clone https://github.com/badlogic/pi-skills.git /opt/pi-skills
cd /opt/pi-skills && npm install

# Setup browser-tools Chrome profile
/opt/pi-skills/browser-tools/setup.sh

# Clone deepagent monorepo
git clone $DEEPAGENT_REPO_URL /app/deepagent
chown -R deepagent:deepagent /app/deepagent

# Setup orchestrator as deepagent user
su - deepagent -c "
cd /app/deepagent/orchestrator
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
"

# Symlink pi-skills into claude/ directory
ln -sf /opt/pi-skills/browser-tools /app/deepagent/claude/skills/
ln -sf /opt/pi-skills/gdcli /app/deepagent/claude/skills/
ln -sf /opt/pi-skills/gmcli /app/deepagent/claude/skills/
ln -sf /opt/pi-skills/brave-search /app/deepagent/claude/skills/
ln -sf /opt/pi-skills/youtube-transcript /app/deepagent/claude/skills/

# Setup persistence directories with proper permissions
mkdir -p /data/{db,outputs,logs,tokens}
chown -R deepagent:deepagent /data
chmod 700 /data/db /data/tokens
chmod 755 /data/outputs /data/logs

# Create secrets directory
mkdir -p /etc/deepagent
touch /etc/deepagent/env
chmod 600 /etc/deepagent/env
chown deepagent:deepagent /etc/deepagent/env

# Configure systemd service
cat > /etc/systemd/system/deepagent.service << 'EOF'
[Unit]
Description=DeepAgent Orchestrator
After=network.target

[Service]
Type=simple
User=deepagent
Group=deepagent
WorkingDirectory=/app/deepagent/orchestrator
EnvironmentFile=/etc/deepagent/env
ExecStart=/app/deepagent/orchestrator/venv/bin/uvicorn api.routes:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/data

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable deepagent
systemctl start deepagent

echo "DeepAgent initialized successfully!"
echo "Next steps:"
echo "  1. Add secrets to /etc/deepagent/env"
echo "  2. Run: su - deepagent -c '/app/deepagent/scripts/setup-oauth.sh'"
```

**labctl Commands**:
```bash
# Start playground with init script
labctl playground start ubuntu --init-script scripts/init.sh

# SSH into VM
labctl ssh

# Run OAuth setup (first time only)
/app/deepagent/scripts/setup-oauth.sh

# Expose API to internet
labctl expose port 8000 --https

# Port forward for local development
labctl port-forward 8000:8000

# Stop (preserves state)
labctl playground stop

# Restart
labctl playground start  # Resumes with persistence
```

**Persistence**:
- SQLite database: `/data/db/deepagent.db`
- Task outputs: `/data/outputs/`
- Logs: `/data/logs/`
- OAuth tokens: `/data/tokens/` (encrypted)

### API Endpoints

```
POST   /api/v1/tasks              # Submit new task
GET    /api/v1/tasks              # List all tasks
GET    /api/v1/tasks/{id}         # Get task details
GET    /api/v1/tasks/{id}/result  # Get task result
DELETE /api/v1/tasks/{id}         # Cancel task

POST   /api/v1/auth/register      # Register device
POST   /api/v1/auth/token         # Get auth token

GET    /api/v1/health             # Health check

# Phase 2
WS     /api/v1/tasks/{id}/stream  # Real-time progress
POST   /api/v1/schedules          # Create scheduled task
```

### Mobile App Screens

1. **Home** - Quick task submission + recent tasks
2. **New Task** - Task creation form with templates
3. **Task Detail** - Status, progress, results
4. **History** - All past tasks with search/filter
5. **Settings** - Cloud accounts, notifications, preferences

### Security & Operations

#### Process Isolation
- **Dedicated user**: Orchestrator runs as `deepagent` user, not root
- **Permissions**: Tight access control on `/data/` directories
  ```
  /data/db/       → 700 deepagent:deepagent
  /data/outputs/  → 755 deepagent:deepagent
  /data/logs/     → 755 deepagent:deepagent
  /data/tokens/   → 700 deepagent:deepagent
  ```

#### Secrets Management
- **Environment variables**: Load from `/etc/deepagent/env` (mode 600)
- **Never embed secrets** in systemd unit files or code
- **OAuth tokens**: Stored in user home, not world-readable

#### API Security
- **JWT Authentication**:
  - Token TTL: 24 hours (configurable)
  - Refresh token: 7 days
  - Signing key rotation: Document procedure
- **Rate Limiting**:
  - 10 requests/second per device
  - 100 tasks/hour per device
- **CORS**: Restrict to mobile app origins
- **Payload Limits**:
  - Request body: 10MB max
  - Attachments: 25MB per file, 100MB total per task

#### Input Validation
- **Attachment types**: Whitelist (pdf, docx, txt, md, csv, json, png, jpg)
- **URL validation**: Reject internal/private IPs in config
- **Task config**: Schema validation against templates

#### Cloud OAuth
- Tokens managed by gdcli/onedrive-cli (stored in `/home/deepagent/.config/`)
- **VM Access**: SSH key authentication via labctl
- **API Exposure**: HTTPS via labctl expose

### API Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `TASK_NOT_FOUND` | 404 | Task ID does not exist |
| `TASK_ALREADY_COMPLETED` | 409 | Cannot modify completed task |
| `VALIDATION_ERROR` | 400 | Invalid request payload |
| `ATTACHMENT_TOO_LARGE` | 413 | File exceeds size limit |
| `UNSUPPORTED_FILE_TYPE` | 415 | File type not allowed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `UNAUTHORIZED` | 401 | Invalid or expired token |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## Development Phases

### Phase 1: Core Functionality

| Component | Deliverables |
|-----------|-------------|
| VM Setup | Init script with pi-skills, onedrive-cli, Claude Code |
| Orchestrator | Task queue, Claude CLI wrapper, result processor |
| Skills Config | browser-tools, gdcli, gmcli, brave-search setup |
| Agent Prompts | researcher.md, document_gen.md, analyzer.md |
| Mobile App | Task submission, push notifications, history view |
| Integrations | Google Drive + OneDrive + Gmail via CLI tools |

### Phase 2: Enhanced Experience

| Component | Deliverables |
|-----------|-------------|
| Real-time | WebSocket progress streaming |
| Scheduling | Cron-based recurring tasks (APScheduler) |
| App | In-app result viewer, voice input |
| Tools | youtube-transcript, transcribe integration |
| Multi-VM | Scale to multiple VMs for parallel tasks |

### Phase 3: Advanced Features

| Component | Deliverables |
|-----------|-------------|
| Workflows | Multi-step task chains |
| Templates | Reusable task templates library |
| Collaboration | Shared tasks, team features |
| Analytics | Usage stats, cost tracking |

---

## Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Mobile App | Flutter (Dart) |
| Backend API | FastAPI (Python) |
| AI Engine | Claude Code CLI |
| Task Queue | SQLite + background workers |
| Web Automation | pi-skills/browser-tools (CDP) |
| Web Search | pi-skills/brave-search |
| Google Drive | pi-skills/gdcli |
| Gmail | pi-skills/gmcli |
| OneDrive | onedrive-cli |
| VM Platform | iximiuz Playground (labctl) |
| Notifications | Firebase Cloud Messaging |

---

## Configuration

### Environment Variables

```bash
# Claude Code
ANTHROPIC_API_KEY=sk-ant-...

# Brave Search (for pi-skills/brave-search)
BRAVE_API_KEY=...

# Groq (for pi-skills/transcribe)
GROQ_API_KEY=...

# Firebase (Push Notifications)
FIREBASE_PROJECT_ID=...
FIREBASE_CREDENTIALS_PATH=/data/firebase-credentials.json

# App (set in systemd service)
API_SECRET_KEY=...
DATABASE_URL=sqlite:////data/db/deepagent.db
OUTPUTS_PATH=/data/outputs
CLAUDE_PATH=/app/deepagent/claude
SKILLS_PATH=/app/deepagent/claude/skills

# OAuth tokens stored by respective CLIs
# gdcli: ~/.config/gdcli/token.json
# gmcli: ~/.config/gmcli/token.json
# onedrive-cli: ~/.config/onedrive-cli/token.json
```

### First-Time OAuth Setup

**OAuth Setup Script** (`scripts/setup-oauth.sh`):
```bash
#!/bin/bash
echo "=== DeepAgent OAuth Setup ==="

echo "1. Authenticating Google Drive..."
gdcli auth login

echo "2. Authenticating Gmail..."
gmcli auth login

echo "3. Authenticating OneDrive..."
onedrive login

echo "4. Setting up Brave Search API key..."
read -p "Enter your Brave Search API key: " BRAVE_KEY
echo "export BRAVE_API_KEY=$BRAVE_KEY" >> /etc/environment

echo "=== OAuth setup complete! ==="
echo "Restart the service: systemctl restart deepagent"
```

**Manual Setup**:
```bash
# SSH into VM
labctl ssh

# Run the setup script
/app/deepagent/scripts/setup-oauth.sh

# Or manually:
gdcli auth login
gmcli auth login
onedrive login
export BRAVE_API_KEY=your-key
```

---

## Open Questions

1. **Rate Limiting**: How to handle Claude Code CLI rate limits during heavy usage?
2. **VM Uptime**: iximiuz VM hibernation policy - need keep-alive mechanism?
3. **X.com Scraping**: Need to handle X.com login/anti-bot measures via browser-tools
4. **Document Formats**: Should we support LaTeX output for academic reports?
5. **Offline Mode**: Should mobile app queue tasks when offline?

---

## Next Steps

### Repository Setup
1. [ ] Initialize monorepo structure (`app/`, `orchestrator/`, `claude/`, `scripts/`)
2. [ ] Create `.gitignore` for Python, Flutter, and secrets
3. [ ] Write `README.md` with quick start guide

### Orchestrator (`orchestrator/`)
4. [ ] Create FastAPI project with `pyproject.toml` and `requirements.txt`
5. [ ] Implement task queue with SQLite (`core/task_queue.py`)
6. [ ] Implement Claude Code CLI wrapper (`core/claude_runner.py`)
7. [ ] Create REST API endpoints (`api/routes.py`)

### Claude Scaffolding (`claude/`)
8. [ ] Write agent prompts (`prompts/researcher.md`, `prompts/analyzer.md`)
9. [ ] Create task templates (`templates/*.json`)
10. [ ] Write `CLAUDE.md` project instructions

### Scripts (`scripts/`)
11. [ ] Finalize `init.sh` for VM setup
12. [ ] Create `setup-oauth.sh` for first-time authentication
13. [ ] Create `deploy.sh` for updates

### Mobile App (`app/`)
14. [ ] Create Flutter project scaffold
15. [ ] Implement task submission screen
16. [ ] Add Firebase push notification support
17. [ ] Build task history and results view

### Integration Testing
18. [ ] Test VM setup with labctl
19. [ ] Test end-to-end: task → Claude → skills → result → notification

---

## References

- [labctl Documentation](https://github.com/iximiuz/labctl)
- [pi-skills Repository](https://github.com/badlogic/pi-skills)
- [onedrive-cli Repository](https://github.com/lionello/onedrive-cli)
- [agent-scripts Repository](https://github.com/steipete/agent-scripts)
- [Claude Code CLI Documentation](https://docs.anthropic.com/claude-code)
