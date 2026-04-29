# Data Model: Fakelytics Platform

**Feature**: Fakelytics - Unified Multimodal Content Verification Platform  
**Date**: 2026-04-27

---

## Entity Relationship Diagram

```
┌─────────────────────────┐       ┌─────────────────────────┐
│   VerificationRequest   │       │     ContentExtract      │
├─────────────────────────┤       ├─────────────────────────┤
│ id: UUID                │──1:1──│ id: UUID                │
│ url: string             │       │ request_id: UUID (FK)   │
│ status: RequestStatus   │       │ text_content: text      │
│ created_at: datetime    │       │ images: MediaItem[]     │
│ completed_at: datetime  │       │ audio: MediaItem[]      │
│ options: RequestOptions │       │ video: MediaItem[]      │
└─────────────────────────┘       └─────────────────────────┘
              │                              │
              │ 1:N                          │ 1:N
              ▼                              ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│    CredibilityReport    │       │       MediaItem         │
├─────────────────────────┤       ├─────────────────────────┤
│ id: UUID                │       │ id: UUID                │
│ request_id: UUID (FK)   │       │ url: string             │
│ overall_score: int      │       │ local_path: string      │
│ summary: string         │       │ mime_type: string       │
│ findings: Findings      │       │ size_bytes: int         │
│ timestamp: datetime     │       │ extracted_at: datetime  │
└─────────────────────────┘       └─────────────────────────┘
              │
              │ 1:N
              ▼
┌─────────────────────────┐
│        Finding          │
├─────────────────────────┤
│ id: UUID                │
│ pipeline: PipelineType  │
│ verdict: Verdict        │
│ confidence: int         │
│ summary: string         │
│ evidence: Evidence[]    │
│ details: JSON           │
└─────────────────────────┘
              │
              │ 1:N
              ▼
┌─────────────────────────┐
│       Evidence          │
├─────────────────────────┤
│ id: UUID                │
│ finding_id: UUID (FK)   │
│ url: string             │
│ snippet: text           │
│ validated: bool         │
│ validated_at: datetime  │
└─────────────────────────┘
```

---

## Core Entities

### VerificationRequest

Represents a single URL verification request.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique identifier |
| `url` | string | Yes | URL to verify (max 2048 chars) |
| `status` | RequestStatus | Yes | Current status of the request |
| `created_at` | datetime | Yes | Request creation timestamp |
| `completed_at` | datetime | No | Request completion timestamp |
| `options` | RequestOptions | No | Request options (async, webhook) |
| `error_message` | string | No | Error message if request failed |

**RequestStatus Enum**:
- `pending` - Request queued for processing
- `processing` - Content extraction in progress
- `completed` - Report ready
- `failed` - Processing failed

**RequestOptions**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `async_mode` | bool | false | Run asynchronously |
| `webhook_url` | string | null | Callback URL for async results |
| `timeout_seconds` | int | 60 | Max processing time |
| `pipelines` | PipelineType[] | all | Which pipelines to run |

---

### ContentExtract

Represents extracted content from a URL.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique identifier |
| `request_id` | UUID | Yes | Foreign key to VerificationRequest |
| `text_content` | text | No | Extracted text content |
| `images` | MediaItem[] | No | Extracted images |
| `audio` | MediaItem[] | No | Extracted audio files |
| `video` | MediaItem[] | No | Extracted video files |
| `extracted_at` | datetime | Yes | Extraction timestamp |

---

### MediaItem

Represents a single media item extracted from content.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique identifier |
| `url` | string | Yes | Original URL of media |
| `local_path` | string | Yes | Local storage path |
| `mime_type` | string | Yes | MIME type (image/*, audio/*, video/*) |
| `size_bytes` | int | Yes | File size in bytes |
| `width` | int | No | For images/video: width |
| `height` | int | No | For images/video: height |
| `duration_seconds` | float | No | For audio/video: duration |
| `extracted_at` | datetime | Yes | Extraction timestamp |

---

### CredibilityReport

The main output - a complete credibility assessment.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique identifier |
| `request_id` | UUID | Yes | Foreign key to VerificationRequest |
| `url` | string | Yes | Verified URL |
| `overall_credibility_score` | int | Yes | Score from 0-100 |
| `summary` | string | Yes | Human-readable summary |
| `findings` | Findings | Yes | Per-pipeline findings |
| `timestamp` | datetime | Yes | Report generation timestamp |

**Findings Structure**:
```json
{
  "text": { "verdict": "Supported", "confidence": 85, "findings": [...] },
  "image": { "verdict": "Disputed", "confidence": 92, "findings": [...] },
  "audio_video": { "verdict": "Unverifiable", "confidence": 30, "findings": [...] },
  "spam": { "verdict": "Supported", "confidence": 78, "findings": [...] }
}
```

---

### Finding

A single finding from a verification pipeline.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique identifier |
| `pipeline` | PipelineType | Yes | Which pipeline generated this |
| `verdict` | Verdict | Yes | Supported/Disputed/Unverifiable |
| `confidence` | int | Yes | Confidence score 0-100 |
| `summary` | string | Yes | Brief description of finding |
| `evidence` | Evidence[] | Yes | Supporting evidence |
| `details` | JSON | No | Additional pipeline-specific data |

**PipelineType Enum**:
- `text` - Text verification pipeline
- `image` - Image verification pipeline
- `audio_video` - Audio/video verification pipeline
- `spam` - Spam detection pipeline

**Verdict Enum**:
- `Supported` - Evidence supports the claim/content
- `Disputed` - Evidence contradicts or raises concerns
- `Unverifiable` - Insufficient evidence to determine

---

### Evidence

A cited source supporting or contradicting a finding.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique identifier |
| `finding_id` | UUID | Yes | Foreign key to Finding |
| `url` | string | Yes | Source URL |
| `snippet` | text | Yes | Relevant text from source |
| `title` | string | No | Title of source page |
| `validated` | bool | Yes | URL was accessible |
| `validated_at` | datetime | No | Last validation timestamp |
| `cache_key` | string | No | Cache key for deduplication |

---

## Validation Rules

### URL Validation
- Must be valid URL format (RFC 3986)
- Scheme must be `http` or `https`
- Max length: 2048 characters
- Domain must be resolvable (optional check)

### Confidence Score
- Must be integer 0-100
- 0-30: Low confidence
- 31-70: Medium confidence
- 71-100: High confidence

### Content Size Limits
- Text content: Max 1MB
- Individual image: Max 10MB
- Individual audio: Max 50MB
- Individual video: Max 100MB
- Total request size: Max 500MB

---

## State Transitions

### VerificationRequest State Machine

```
pending → processing → completed
              ↓
            failed
```

### Finding Verdict Rules

| Condition | Verdict |
|-----------|---------|
| Evidence supports claim | Supported |
| Evidence contradicts claim | Disputed |
| No evidence available | Unverifiable |
| Confidence < 20 | Unverifiable |
| Evidence URL invalid | Remove from finding |

---

## Database Schema (PostgreSQL)

```sql
-- Verification Requests
CREATE TABLE verification_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url VARCHAR(2048) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    options JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Content Extracts
CREATE TABLE content_extracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES verification_requests(id),
    text_content TEXT,
    images JSONB,
    audio JSONB,
    video JSONB,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Media Items
CREATE TABLE media_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_extract_id UUID REFERENCES content_extracts(id),
    url VARCHAR(2048) NOT NULL,
    local_path VARCHAR(512) NOT NULL,
    mime_type VARCHAR(50) NOT NULL,
    size_bytes BIGINT NOT NULL,
    width INTEGER,
    height INTEGER,
    duration_seconds FLOAT,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Credibility Reports
CREATE TABLE credibility_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES verification_requests(id),
    url VARCHAR(2048) NOT NULL,
    overall_credibility_score INTEGER NOT NULL,
    summary TEXT NOT NULL,
    findings JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Findings
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID REFERENCES credibility_reports(id),
    pipeline VARCHAR(20) NOT NULL,
    verdict VARCHAR(20) NOT NULL,
    confidence INTEGER NOT NULL,
    summary TEXT NOT NULL,
    evidence JSONB,
    details JSONB
);

-- Evidence
CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID REFERENCES findings(id),
    url VARCHAR(2048) NOT NULL,
    snippet TEXT NOT NULL,
    title VARCHAR(512),
    validated BOOLEAN NOT NULL DEFAULT false,
    validated_at TIMESTAMP WITH TIME ZONE,
    cache_key VARCHAR(128)
);

-- Indexes
CREATE INDEX idx_requests_status ON verification_requests(status);
CREATE INDEX idx_requests_created ON verification_requests(created_at);
CREATE INDEX idx_reports_request ON credibility_reports(request_id);
CREATE INDEX idx_findings_report ON findings(report_id);
CREATE INDEX idx_evidence_finding ON evidence(finding_id);
```