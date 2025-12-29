# DeepAgent Progress Tracker

## Phase 1: Core Functionality

### Repository Setup
- [x] Create monorepo structure (`app/`, `orchestrator/`, `claude/`, `scripts/`)
- [x] Create `.gitignore` for Python, Flutter, and secrets
- [x] Write `README.md` with quick start guide
- [x] Write `SPEC.md` with full architecture documentation
- [x] Add data models to SPEC.md (SQLAlchemy + Pydantic schemas)
- [x] Add execution & resilience section (background worker, retry, limits)
- [x] Add security & operations section (dedicated user, permissions, secrets)
- [x] Add observability section (structured logging, metrics)
- [x] Add API error codes specification

### Claude Scaffolding (`claude/`)
- [x] Create `CLAUDE.md` project instructions
- [x] Write `prompts/researcher.md` template
- [x] Write `prompts/analyzer.md` template
- [x] Write `prompts/document_gen.md` template
- [x] Create `templates/research_task.json` schema
- [x] Create `templates/analysis_task.json` schema
- [x] Create `templates/document_task.json` schema
- [ ] Test prompts with Claude Code CLI locally

### Scripts (`scripts/`)
- [x] Create `init.sh` for VM initialization
- [x] Create `setup-oauth.sh` for OAuth authentication
- [x] Create `deploy.sh` for updates
- [ ] Update `init.sh` with dedicated user (deepagent)
- [ ] Update `init.sh` with proper permissions
- [ ] Add secrets setup to `init.sh` (/etc/deepagent/env)
- [ ] Test `init.sh` on iximiuz playground
- [ ] Test `setup-oauth.sh` flow

### Orchestrator (`orchestrator/`)

#### Configuration & Models
- [x] Create project structure with `__init__.py` files
- [x] Create `requirements.txt` with dependencies
- [ ] Create `config.py` with pydantic-settings
  - [ ] Environment variable loading
  - [ ] Default values
  - [ ] Validation
  - [ ] Unit tests
- [ ] Implement `db/models.py` (SQLAlchemy)
  - [ ] Task model with all fields (id, type, status, attempts, timestamps, etc.)
  - [ ] TaskLog model for structured logging
  - [ ] Status enum with all states
  - [ ] Unit tests
- [ ] Implement `api/models.py` (Pydantic)
  - [ ] TaskCreate, TaskResponse, TaskResult
  - [ ] ErrorResponse with error codes
  - [ ] Validation tests

#### Core Logic
- [ ] Implement `core/task_queue.py`
  - [ ] SQLite queue with row-level locking
  - [ ] Enqueue, dequeue, update operations
  - [ ] Retry logic with exponential backoff
  - [ ] Task state transitions
  - [ ] Unit tests for retry/backoff
- [ ] Implement `core/claude_runner.py`
  - [ ] Claude Code CLI wrapper
  - [ ] Task type → prompt mapping
  - [ ] Timeout enforcement per task type
  - [ ] Cancellation support (SIGTERM)
  - [ ] Partial result saving
  - [ ] Integration test (mock or real)
- [ ] Implement `core/result_processor.py`
  - [ ] Process Claude output
  - [ ] Upload to cloud storage (gdcli, onedrive)
  - [ ] Send email notification (gmcli)
  - [ ] Update task status
  - [ ] Handle upload/email failures

#### API Layer
- [ ] Implement `api/routes.py`
  - [ ] POST /tasks - submit task
  - [ ] GET /tasks - list tasks
  - [ ] GET /tasks/{id} - task details
  - [ ] GET /tasks/{id}/result - task result
  - [ ] DELETE /tasks/{id} - cancel task
  - [ ] GET /health - health check
- [ ] Add JWT authentication
  - [ ] POST /auth/register - device registration
  - [ ] POST /auth/token - get token
  - [ ] Token validation middleware
  - [ ] Refresh token support
- [ ] Add rate limiting middleware
- [ ] Add CORS configuration
- [ ] Add request/attachment size limits

#### Background Worker
- [ ] Implement background worker process
  - [ ] Separate from FastAPI request thread
  - [ ] Poll queue for pending tasks
  - [ ] Execute Claude runner
  - [ ] Handle graceful shutdown
- [ ] Add worker to systemd service

#### Observability
- [ ] Add structured logging with correlation IDs
- [ ] Add request ID middleware
- [ ] Log key events (task lifecycle)
- [ ] Add basic metrics logging

### Mobile App (`app/`)

> **Note**: Consider starting with minimal Flutter screens until orchestrator E2E path is solid.

- [ ] Initialize Flutter project (`flutter create`)
- [ ] Set up project dependencies in `pubspec.yaml`
- [ ] Create API service for backend communication
- [ ] Implement Home screen (quick task + recent tasks)
- [ ] Implement New Task screen (task form)
- [ ] Implement Task Detail screen (status, results)
- [ ] Implement History screen (all tasks)
- [ ] Implement Settings screen
- [ ] Add Firebase push notifications
- [ ] Build APK for testing

### Integration Testing

**Priority: E2E Happy Path First**

- [ ] Deploy to iximiuz VM with new init.sh
- [ ] Verify dedicated user setup and permissions
- [ ] Test secrets loading from /etc/deepagent/env
- [ ] Test end-to-end happy path:
  - [ ] Submit research task via API
  - [ ] Claude executes (mock or real)
  - [ ] Result saved to /data/outputs/
  - [ ] Upload to Google Drive via gdcli
  - [ ] Email notification via gmcli
  - [ ] Task status updated to COMPLETED
- [ ] Test failure scenarios:
  - [ ] Claude timeout → FAILED → RETRY
  - [ ] Max retries exceeded → DEAD
  - [ ] Upload failure → task still COMPLETED with error note
- [ ] Test mobile app → API flow

---

## Phase 2: Enhanced Experience

### Real-time Updates
- [ ] Implement WebSocket endpoint (`api/websocket.py`)
- [ ] Add progress streaming from Claude Code
- [ ] Update mobile app with real-time progress UI

### Scheduling
- [ ] Add APScheduler for recurring tasks
- [ ] Implement schedule API endpoints
- [ ] Add schedule UI to mobile app

### Additional Features
- [ ] Add `youtube-transcript` integration
- [ ] Add `transcribe` (audio-to-text) integration
- [ ] In-app result viewer
- [ ] Voice input for task submission

---

## Phase 3: Advanced Features

- [ ] Multi-step task workflows
- [ ] Reusable task templates library
- [ ] Multi-VM scaling for parallel tasks
- [ ] Usage analytics and cost tracking

---

## Definition of Done (DoD)

Each task must meet these criteria:

| Component | DoD Criteria |
|-----------|--------------|
| `config.py` | Loads/validates env vars, has defaults, unit test passes |
| `db/models.py` | All fields from spec, migrations work, unit tests pass |
| `api/models.py` | Validation works, error codes match spec, tests pass |
| `task_queue.py` | Retry/backoff works, state transitions correct, tests pass |
| `claude_runner.py` | Timeout works, cancellation works, integration test passes |
| `api/routes.py` | All endpoints work, auth enforced, rate limits work |
| `init.sh` | Validated on fresh iximiuz VM, all permissions correct |

---

## Summary

| Category | Done | Total | Progress |
|----------|------|-------|----------|
| Repository Setup | 9 | 9 | 100% |
| Claude Scaffolding | 7 | 8 | 88% |
| Scripts | 3 | 8 | 38% |
| Orchestrator (Config/Models) | 2 | 5 | 40% |
| Orchestrator (Core) | 0 | 3 | 0% |
| Orchestrator (API) | 0 | 4 | 0% |
| Orchestrator (Worker) | 0 | 2 | 0% |
| Orchestrator (Observability) | 0 | 4 | 0% |
| Mobile App | 0 | 10 | 0% |
| Integration Testing | 0 | 10 | 0% |
| **Phase 1 Total** | **21** | **63** | **33%** |

---

## Next Priority Tasks

**Focus: Orchestrator core + E2E happy path before mobile app**

1. [ ] `orchestrator/config.py` - Settings with pydantic-settings
2. [ ] `orchestrator/db/models.py` - SQLAlchemy Task/TaskLog models
3. [ ] `orchestrator/api/models.py` - Pydantic request/response models
4. [ ] `orchestrator/core/task_queue.py` - Queue with retry logic
5. [ ] `orchestrator/core/claude_runner.py` - CLI wrapper with timeout
6. [ ] `orchestrator/api/routes.py` - REST endpoints
7. [ ] Background worker implementation
8. [ ] E2E test on iximiuz VM

---

## Blockers / Notes

- **iximiuz account**: Need to verify playground access and VM limits
- **pi-skills OAuth**: Need to test `gdcli` and `gmcli` authentication flow
- **X.com scraping**: May need to handle anti-bot measures in `browser-tools`
- **Mobile scope**: Consider thinner client (minimal screens) until API/worker solid

---

## Review Recommendations Applied

Based on `review.md`, the following has been incorporated:

- [x] Background worker architecture (off request thread)
- [x] Per-task limits and cancellation hooks
- [x] Retry with exponential backoff + max attempts
- [x] Task lifecycle timestamps (created, queued, started, completed)
- [x] Dedicated user (deepagent), not root
- [x] Tightened permissions on /data directories
- [x] Secrets in /etc/deepagent/env (not in systemd unit)
- [x] JWT token TTL, rate limiting, CORS documented
- [x] Payload size limits, attachment validation
- [x] SQLAlchemy models with all required fields
- [x] Pydantic schemas with validation
- [x] Status transitions documented
- [x] Error codes specification
- [x] Structured logging with correlation IDs
- [x] Basic metrics specification
- [x] DoD per task defined
- [x] E2E happy path prioritized
- [ ] Lightweight integration checks for skills (pending)

---

*Last updated: 2024-12-29*
