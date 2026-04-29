# Implementation Plan: Fakelytics Platform

**Branch**: `001-fakelytics-platform` | **Date**: 2026-04-27 | **Spec**: [spec.md](specs/001-fakelytics-platform/spec.md)

**Input**: Feature specification from `/specs/001-fakelytics-platform/spec.md`

## Summary

Fakelytics is a unified multimodal content verification platform that accepts a URL and returns a comprehensive credibility report. The system extracts text, images, audio, and video from submitted URLs, runs parallel AI-powered verification pipelines (text, image, audio/video, spam), and aggregates results into a single report with an overall credibility score (0-100). Each finding includes confidence score, verdict (Supported/Disputed/Unverifiable), and cited evidence. The platform supports both synchronous API requests and asynchronous webhook callbacks.

**Technical Approach**: Multi-agent pipeline architecture with isolated, independently testable modules for each modality. All pipelines execute concurrently using async/await patterns. The system uses a queue-based architecture for scalability with Redis for state management and PostgreSQL for audit logging.

## Technical Context

**Language/Version**: Python 3.11+ (primary), TypeScript (API layer)  
**Primary Dependencies**: FastAPI, Celery, Redis, PostgreSQL, Pydantic, LangChain/OpenAI SDK  
**Storage**: PostgreSQL (audit logs, user data), Redis (queue state, caching), S3 (extracted media)  
**Testing**: pytest, pytest-asyncio, Factory Boy, Locust  
**Target Platform**: Linux server (API + workers), containerized deployment  
**Project Type**: Web service with background workers  
**Performance Goals**: <60s overall report generation, <30s per pipeline, 100+ concurrent requests  
**Constraints**: <500MB memory per worker, rate limiting for source websites, evidence URL validation  
**Scale/Scope**: 10k+ users, 100k+ verifications/day (Phase 3 target)

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Modular Pipeline Architecture | ✅ PASS | Each modality (text, image, audio/video, spam) is an isolated module |
| II. Concurrent Processing | ✅ PASS | All pipelines run concurrently; failure isolation built in |
| III. Evidence-Based Verdict | ✅ PASS | Every finding requires confidence, verdict, and evidence |
| IV. Dual Output Format | ✅ PASS | Both human-readable summary and JSON output required |
| V. API-First Design | ✅ PASS | API-first with sync/async support, versioned schemas |

**GATE**: All constitution principles satisfied. Proceeding to Phase 0 research.

## Project Structure

### Documentation (this feature)

```
specs/001-fakelytics-platform/
├── plan.md              # This file
├── research.md          # Phase 0 output (to be generated)
├── data-model.md        # Phase 1 output (to be generated)
├── quickstart.md        # Phase 1 output (to be generated)
├── contracts/           # Phase 1 output (to be generated)
│   └── api-v1.yaml      # OpenAPI specification
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── api/                 # FastAPI application
│   ├── routes/         # API endpoints
│   ├── models/         # Pydantic request/response models
│   └── middleware/     # Auth, rate limiting, logging
├── workers/            # Celery workers for pipeline execution
│   ├── tasks/         # Celery tasks
│   └── pipelines/     # Pipeline implementations
│       ├── text/      # Text verification module
│       ├── image/     # Image verification module
│       ├── audio_video/ # Audio/video verification module
│       └── spam/      # Spam detection module
├── core/               # Shared utilities
│   ├── config/        # Configuration management
│   ├── storage/       # Database and cache clients
│   └── extraction/    # Content extraction from URLs
├── services/           # Business logic services
│   ├── orchestration/ # Pipeline coordination
│   ├── scoring/       # Credibility score calculation
│   └── evidence/      # Evidence validation and storage
└── lib/                # Shared libraries

tests/
├── unit/              # Unit tests per module
├── integration/       # Integration tests
├── contract/          # API contract tests
└── fixtures/          # Test fixtures and factories

scripts/
├── deployment/        # Deployment scripts
└── maintenance/       # Maintenance scripts
```

**Structure Decision**: Single project with modular pipeline packages. Each pipeline (text, image, audio_video, spam) is a self-contained Python package under `src/workers/pipelines/` with its own dependencies and test suite.

---

# Phased Implementation Plan

## Phase 1: MVP (Weeks 1-6)

**Goal**: Core platform with basic verification capabilities and API

### 1.1 Core Infrastructure

| Component | Description | Dependencies |
|-----------|-------------|--------------|
| API Layer | FastAPI application with `/api/v1/verify` and `/api/v1/report/{id}` endpoints | FastAPI, Pydantic, Uvicorn |
| Request Validation | URL validation, schema validation, rate limiting | Pydantic, slowapi |
| Database Schema | PostgreSQL tables for requests, reports, audit logs | SQLAlchemy, Alembic |
| Queue System | Celery with Redis broker for async task processing | Celery, Redis |
| Configuration | Environment-based config with validation | Pydantic Settings |

### 1.2 Content Extraction

| Component | Description | Dependencies |
|-----------|-------------|--------------|
| HTML Parser | Extract text, images, audio, video from URLs | BeautifulSoup, requests |
| Media Downloader | Download and store extracted media | aiohttp, aiofiles |
| Content Normalizer | Standardize extracted content for pipeline input | Pillow, pydub |

### 1.3 Pipeline Modules (MVP)

Each pipeline is an isolated module with its own interface:

```
Pipeline Interface:
- input: ContentExtract
- output: PipelineResult (findings[], status, duration_ms)
- timeout: 30 seconds
- error handling: Returns partial results or empty findings on failure
```

| Pipeline | Description | Key Dependencies |
|----------|-------------|------------------|
| Text Pipeline | Claim detection, cross-reference with web sources | LangChain, OpenAI, SerpAPI |
| Image Pipeline | AI-generated detection, out-of-context detection | CLIP, torchvision |
| Audio/Video Pipeline | Deepfake detection, audio-visual mismatch | Resemblyzer, FFmpeg |
| Spam Pipeline | Low-credibility source patterns, spam signals | Custom ML model |

### 1.4 Orchestration Layer

| Component | Description |
|-----------|-------------|
| Pipeline Coordinator | Spawns all pipelines concurrently, aggregates results |
| Timeout Manager | Enforces 30s per-pipeline timeout, tracks overall 60s limit |
| Fallback Handler | Returns partial results if any pipeline fails |
| Score Calculator | Weighted aggregation of pipeline scores into overall credibility |

### 1.5 API Contracts

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/verify` | POST | Submit URL for verification (sync/async) |
| `/api/v1/report/{request_id}` | GET | Retrieve verification report |
| `/api/v1/webhook` | POST | Webhook callback for async results |
| `/health` | GET | Health check endpoint |

### 1.6 Observability (MVP)

| Component | Description |
|-----------|-------------|
| Structured Logging | JSON logs with request_id, pipeline_id, duration |
| Error Tracking | Sentry integration for exception tracking |
| Basic Metrics | Request count, pipeline duration, success rate |

### Phase 1 Deliverables

- [ ] Functional API with `/api/v1/verify` and `/api/v1/report/{id}`
- [ ] Content extraction from URLs
- [ ] All four pipeline modules (text, image, audio_video, spam)
- [ ] Concurrent pipeline execution with timeout handling
- [ ] Basic credibility scoring
- [ ] Dual output (JSON + human-readable summary)
- [ ] Unit tests for each pipeline module
- [ ] API contract tests

---

## Phase 2: Production Hardening (Weeks 7-12)

**Goal**: Production-ready with reliability, security, and observability

### 2.1 Reliability Improvements

| Component | Description |
|-----------|-------------|
| Retry Logic | Exponential backoff for transient failures |
| Circuit Breakers | Prevent cascade failures from downstream services |
| Dead Letter Queue | Capture failed tasks for manual review |
| Health Checks | Deep health checks for all dependencies |

### 2.2 Security & Abuse Mitigation

| Component | Description |
|-----------|-------------|
| Authentication | API key-based authentication for enterprise users |
| Rate Limiting | Per-user rate limits with Redis-backed counters |
| Input Sanitization | Sanitize URLs and content to prevent injection |
| Content Size Limits | Enforce max content size to prevent resource exhaustion |
| DDoS Protection | Rate limiting at API gateway level |

### 2.3 Enhanced Observability

| Component | Description |
|-----------|-------------|
| Distributed Tracing | OpenTelemetry integration for request tracing |
| Custom Metrics | Pipeline-specific metrics (confidence distribution, verdict breakdown) |
| Dashboards | Grafana dashboards for monitoring |
| Alerting | PagerDuty/Slack alerts for critical issues |

### 2.4 Evidence Validation

| Component | Description |
|-----------|-------------|
| URL Accessibility Check | Validate evidence URLs before citation |
| Cache Evidence | Cache validated evidence to reduce redundant checks |
| Evidence Freshness | Re-validate evidence for old reports |

### 2.5 Performance Optimization

| Component | Description |
|-----------|-------------|
| Caching | Cache extraction results and common verifications |
| Connection Pooling | Optimize database and Redis connections |
| Pipeline Optimization | Profile and optimize slow pipelines |

### Phase 2 Deliverables

- [ ] Authentication and API key management
- [ ] Rate limiting and abuse prevention
- [ ] Distributed tracing with OpenTelemetry
- [ ] Enhanced metrics and Grafana dashboards
- [ ] Evidence validation and caching
- [ ] Retry logic and circuit breakers
- [ ] Integration tests for pipeline coordination
- [ ] Load testing with Locust

---

## Phase 3: Scale and Partnerships (Weeks 13-20)

**Goal**: Enterprise-ready with multi-tenant support and partner integrations

### 3.1 Multi-Tenancy

| Component | Description |
|-----------|-------------|
| Tenant Isolation | Logical separation of tenant data |
| Tenant-Specific Pipelines | Custom pipeline configurations per tenant |
| Quota Management | Per-tenant request quotas and billing |
| Custom Branding | White-label options for enterprise partners |

### 3.2 Partner Integrations

| Component | Description |
|-----------|-------------|
| Webhook System | Rich webhook events for workflow integration |
| Bulk API | Batch verification for high-volume users |
| SDKs | Official SDKs for Python, JavaScript, Go |
| Zapier Integration | No-code integration with partner tools |

### 3.3 Advanced Features

| Component | Description |
|-----------|-------------|
| Historical Analysis | Track URL credibility over time |
| Comparison API | Compare multiple URLs side-by-side |
| Custom Rules | Tenant-specific verification rules |
| Report Export | PDF export of credibility reports |

### 3.4 Scale Infrastructure

| Component | Description |
|-----------|-------------|
| Horizontal Scaling | Auto-scaling worker pools based on queue depth |
| Geographic Distribution | Regional API endpoints for latency reduction |
| CDN Integration | Cache static content and common responses |
| Database Sharding | Shard by tenant for horizontal scale |

### 3.5 Enterprise Features

| Component | Description |
|-----------|-------------|
| SSO/SAML | Enterprise single sign-on |
| Audit Logs | Detailed audit trail for compliance |
| SLA Monitoring | Uptime and performance SLAs |
| Dedicated Support | Priority support channels |

### Phase 3 Deliverables

- [ ] Multi-tenant architecture
- [ ] Partner webhook system
- [ ] Official SDKs
- [ ] Auto-scaling infrastructure
- [ ] SSO/SAML authentication
- [ ] Comprehensive audit logging
- [ ] Geographic distribution

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              URL INGESTION                                   │
│  POST /api/v1/verify { url: "https://...", options: {...} }                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           REQUEST VALIDATION                                 │
│  - URL format validation                                                    │
│  - Rate limit check                                                         │
│  - Authentication                                                           │
│  - Create VerificationRequest in DB                                        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTENT EXTRACTION (Async)                          │
│  - Fetch URL content                                                        │
│  - Parse HTML for text, images, audio, video                               │
│  - Download media to storage                                               │
│  - Create ContentExtract entity                                            │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   TEXT PIPELINE  │  │  IMAGE PIPELINE  │  │  A/V PIPELINE    │
│   (30s timeout)  │  │   (30s timeout)  │  │   (30s timeout)  │
│                  │  │                  │  │                  │
│ - Claim extraction│ │ - AI-gen detect │  │ - Deepfake detect│
│ - Web cross-ref  │  │ - OOC detection │  │ - AV mismatch    │
│ - Return findings│  │ - Return findings│  │ - Return findings│
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                                    │
│  - Wait for all pipelines (or timeout)                                     │
│  - Aggregate findings                                                       │
│  - Calculate overall credibility score                                     │
│  - Generate human-readable summary                                         │
│  - Create CredibilityReport                                                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RESPONSE DELIVERY                                 │
│  - Sync: Return report directly                                            │
│  - Async: POST to webhook_url                                              │
│  - Store in DB for retrieval via /api/v1/report/{id}                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Concurrency Model

### Parallel Execution

```
                    ┌─────────────────────┐
                    │  VerificationRequest │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
   │ Text Task   │      │ Image Task  │      │ A/V Task    │
   │ (async)     │      │ (async)     │      │ (async)     │
   └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Aggregation Task   │
                    │  (depends on all)   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   CredibilityReport │
                    └─────────────────────┘
```

### Timeout Strategy

| Stage | Timeout | Behavior |
|-------|---------|----------|
| Content Extraction | 15s | Fail pipeline, continue with available content |
| Individual Pipeline | 30s | Return partial results, log timeout |
| Overall Request | 60s | Return partial report, mark status |
| Evidence Validation | 10s per URL | Skip invalid evidence, continue |

### Fallback Behavior

| Failure Mode | Fallback |
|--------------|----------|
| Pipeline timeout | Return empty findings, log warning |
| Pipeline exception | Return error finding, log exception |
| No content extracted | Return "Unverifiable" for all pipelines |
| Evidence URL invalid | Remove from finding, mark as unverified |
| Database unavailable | Return 503, queue for retry |

---

## Evidence and Citation Storage

### Evidence Entity

```python
class Evidence(Base):
    url: str              # Source URL
    snippet: str          # Relevant text snippet
    validated: bool       # URL accessibility validated
    validated_at: datetime
    cache_key: str        # For deduplication
```

### Storage Strategy

| Data Type | Storage | Retention |
|-----------|---------|-----------|
| Verification requests | PostgreSQL | 90 days |
| Credibility reports | PostgreSQL | 90 days |
| Evidence citations | PostgreSQL + Redis cache | 30 days |
| Extracted media | S3 (temp) | 24 hours |
| Audit logs | PostgreSQL | 1 year |
| Pipeline logs | JSON files + S3 | 30 days |

### Evidence Validation Flow

```
1. Pipeline returns finding with evidence URLs
2. For each evidence URL:
   a. Check Redis cache for recent validation
   b. If not cached, fetch URL (HEAD request)
   c. If accessible, cache result for 24h
   d. If inaccessible, mark as invalid
3. Filter invalid evidence from finding
4. If no valid evidence remains, set verdict to "Unverifiable"
```

---

## Security & Abuse Mitigation

### Authentication

| Tier | Method | Limits |
|------|--------|--------|
| Free | API key | 100 requests/day |
| Pro | API key | 10,000 requests/day |
| Enterprise | API key + SSO | Custom quotas |

### Rate Limiting

```
Rate Limit Strategy:
- Sliding window algorithm per API key
- Separate limits for:
  - Requests/minute (burst)
  - Requests/day (sustained)
  - Concurrent requests
- Redis-backed for distributed deployments
```

### Input Validation

| Check | Action |
|-------|--------|
| URL format | Reject invalid URLs |
| URL scheme | Allow http/https only |
| URL domain | Block known malicious domains |
| Content size | Reject if >50MB |
| Request size | Reject if >1MB |

---

## Complexity Tracking

> **No Constitution violations to justify.**

All architecture decisions align with the core principles:
- Modular pipeline architecture: Each pipeline is isolated
- Concurrent processing: Built into orchestration layer
- Evidence-based verdict: Core to all pipeline outputs
- Dual output: API returns both JSON and summary
- API-first: All features accessible via API

---

## Next Steps

1. **Phase 0**: Generate `research.md` with technology decisions
2. **Phase 1**: Generate `data-model.md`, `contracts/api-v1.yaml`, `quickstart.md`
3. **Phase 2**: Generate `tasks.md` via `/speckit.tasks` command