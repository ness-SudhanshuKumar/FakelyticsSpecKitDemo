# Research: Fakelytics Platform

**Date**: 2026-04-27  
**Feature**: Fakelytics - Unified Multimodal Content Verification Platform

---

## Research Questions

### RQ1: Content Extraction from URLs

**Question**: What are the best practices for extracting text, images, audio, and video from arbitrary URLs?

**Decision**: Use a combination of:
- **BeautifulSoup4** for HTML parsing and content extraction
- **Playwright** for JavaScript-rendered pages
- **aiohttp** for async HTTP requests
- Custom media downloaders for each content type

**Rationale**: 
- BeautifulSoup is mature and well-supported for static content
- Playwright handles dynamic content (SPAs, lazy-loaded media)
- Async libraries essential for concurrent processing

**Alternatives Considered**:
- Scrapy: Good but overkill for single-URL extraction
- Selenium: Too slow for production use
- curl-based: Doesn't handle JavaScript

---

### RQ2: Text Verification Pipeline

**Question**: How to detect false/misleading claims and cross-reference against live web sources?

**Decision**: Use **LangChain** with **OpenAI GPT-4** for claim extraction and verification, combined with **SerpAPI** for live web search.

**Rationale**:
- LangChain provides structured prompt management
- GPT-4 has strong reasoning capabilities for claim analysis
- SerpAPI gives reliable access to search results

**Alternatives Considered**:
- Fine-tuned BERT models: Require training data, harder to maintain
- Claude API: Good alternative, can be added as option
- Local models (LLaMA): Too slow for production latency requirements

---

### RQ3: Image Verification Pipeline

**Question**: How to detect AI-generated or manipulated images?

**Decision**: Use **CLIP** (Contrastive Language-Image Pre-Training) for similarity detection, combined with **AI-image-detection** models (e.g., DINOv2, specialized detectors).

**Rationale**:
- CLIP is well-tested for image analysis
- Multiple detection models available for ensemble
- Can be run locally for cost control

**Alternatives Considered**:
- Cloud APIs (AWS Rekognition, Google Vision): Cost-prohibitive at scale
- Only AI detection: Add metadata analysis for out-of-context detection

---

### RQ4: Audio/Video Verification Pipeline

**Question**: How to detect deepfakes and audio-visual mismatches?

**Decision**: Use **Resemblyzer** for voice analysis, **FFmpeg** for video frame extraction, and specialized deepfake detection models.

**Rationale**:
- Resemblyzer provides voice embedding and similarity
- FFmpeg is the gold standard for media processing
- Multiple open-source deepfake detectors available

**Alternatives Considered**:
- Cloud services (AWS, Azure): Cost and latency concerns
- Single model approach: Ensemble provides better accuracy

---

### RQ5: Spam/Low-Credibility Detection

**Question**: How to detect spam signals and low-credibility source patterns?

**Decision**: Custom ML model using features:
- Domain reputation scores
- URL structure analysis
- Content pattern matching
- Known spam domain lists

**Rationale**:
- Domain reputation can be sourced from threat intelligence feeds
- URL structure reveals certain attack patterns
- Custom model allows tuning to specific use cases

**Alternatives Considered**:
- Pure rule-based: Too many false positives
- Third-party spam APIs: Dependency and cost concerns

---

### RQ6: Concurrent Pipeline Execution

**Question**: How to ensure pipelines run concurrently and handle failures gracefully?

**Decision**: Use **Python asyncio** with **Celery** for distributed task queue.

**Rationale**:
- asyncio provides native concurrent execution
- Celery handles distributed worker management
- Redis as message broker is reliable and fast

**Alternatives Considered**:
- ThreadPoolExecutor: Doesn't scale beyond single instance
- Airflow: Too heavy for this use case
- Temporal: Good but complex for MVP

---

### RQ7: Evidence Validation

**Question**: How to validate evidence URLs before citation?

**Decision**: 
- HEAD request to check URL accessibility
- Redis cache with 24-hour TTL
- Async validation to not block pipeline

**Rationale**:
- HEAD is faster than GET
- Caching reduces redundant checks
- Async prevents blocking report generation

---

### RQ8: API Design

**Question**: What API framework and design patterns to use?

**Decision**: **FastAPI** with **Pydantic** for request/response validation.

**Rationale**:
- FastAPI is high-performance and async-native
- Pydantic provides automatic validation and OpenAPI generation
- Built-in support for async responses

**Alternatives Considered**:
- Flask: Not async-native, more boilerplate
- Django: Too heavy for this use case
- Express.js: Good but prefer Python for ML pipelines

---

### RQ9: Database Choice

**Question**: What database to use for audit logs and report storage?

**Decision**: **PostgreSQL** with **SQLAlchemy** ORM.

**Rationale**:
- PostgreSQL is reliable and well-understood
- SQLAlchemy provides flexibility and testing support
- JSONB columns useful for flexible report schemas

**Alternatives Considered**:
- MongoDB: Less structured, harder to enforce schema
- DynamoDB: AWS lock-in, complex pricing
- SQLite: Not suitable for production scale

---

### RQ10: Observability Stack

**Question**: What observability tools to use?

**Decision**:
- **Structured Logging**: Python `logging` with JSON formatter
- **Metrics**: **Prometheus** + **Grafana**
- **Tracing**: **OpenTelemetry**
- **Error Tracking**: **Sentry**

**Rationale**:
- All are open-source and widely supported
- OpenTelemetry is vendor-neutral
- Grafana provides good visualization

---

## Technology Stack Summary

| Layer | Technology | Version |
|-------|------------|---------|
| API Framework | FastAPI | 0.100+ |
| Validation | Pydantic | 2.0+ |
| Task Queue | Celery | 5.3+ |
| Message Broker | Redis | 7.0+ |
| Database | PostgreSQL | 15+ |
| ORM | SQLAlchemy | 2.0+ |
| Content Extraction | BeautifulSoup4 | 4.12+ |
| Browser Automation | Playwright | 1.40+ |
| LLM Framework | LangChain | 0.1+ |
| Text Analysis | OpenAI GPT-4 | Latest |
| Image Analysis | CLIP, DINOv2 | Latest |
| Audio Analysis | Resemblyzer | Latest |
| Media Processing | FFmpeg | Latest |
| Logging | Python logging + JSON | Built-in |
| Metrics | Prometheus client | Latest |
| Tracing | OpenTelemetry | Latest |

---

## Best Practices Applied

1. **Modular Architecture**: Each pipeline is isolated with clear interfaces
2. **Async-First**: All I/O operations are async for concurrency
3. **Graceful Degradation**: Pipelines fail independently without blocking
4. **Evidence-Based**: All findings require verifiable evidence
5. **API-First**: All features accessible via well-documented API
6. **Observability**: Structured logging, metrics, and tracing from day one