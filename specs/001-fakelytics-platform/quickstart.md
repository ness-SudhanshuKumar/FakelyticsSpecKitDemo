# Quickstart: Fakelytics Platform

**Version**: 1.0.0  
**Last Updated**: 2026-04-27

---

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (for local development)
- Redis 7.0+ (for task queue)
- API key (get from [dashboard](https://dashboard.fakelytics.io))

---

## Installation

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/fakelytics.git
cd fakelytics

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/fakelytics

# Redis
REDIS_URL=redis://localhost:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=your_api_key_here

# External Services
OPENAI_API_KEY=sk-...
SERPAPI_KEY=your_serpapi_key

# Optional: Webhook secret for signature verification
WEBHOOK_SECRET=your_webhook_secret
```

### 3. Database Setup

```bash
# Run migrations
alembic upgrade head

# Seed initial data (optional)
python -m scripts.seed_db
```

### 4. Start Services

```bash
# Start Redis (if not running)
redis-server

# Start Celery worker
celery -A src.workers.celery worker --loglevel=info

# Start API server
uvicorn src.api.main:app --reload
```

---

## Quick Start

### Verify a URL (Synchronous)

```bash
curl -X POST https://api.fakelytics.io/v1/verify \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"url": "https://example.com/article"}'
```

**Response**:

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "report": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://example.com/article",
    "overall_credibility_score": 72,
    "summary": "The content shows moderate credibility with some concerns about source transparency. Text analysis found no disputed claims, but image analysis detected potential manipulation.",
    "findings": {
      "text": {
        "verdict": "Supported",
        "confidence": 85,
        "findings": [
          {
            "id": "f1",
            "summary": "Claims are consistent with known sources",
            "verdict": "Supported",
            "confidence": 85,
            "evidence": [...]
          }
        ]
      },
      "image": {
        "verdict": "Disputed",
        "confidence": 68,
        "findings": [...]
      },
      "audio_video": {
        "verdict": "Unverifiable",
        "confidence": 30,
        "findings": []
      },
      "spam": {
        "verdict": "Supported",
        "confidence": 78,
        "findings": [...]
      }
    },
    "timestamp": "2026-04-27T12:00:00Z"
  }
}
```

### Verify a URL (Asynchronous)

```bash
curl -X POST https://api.fakelytics.io/v1/verify \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "url": "https://example.com/article",
    "options": {
      "async_mode": true,
      "webhook_url": "https://your-app.com/webhooks/fakelytics"
    }
  }'
```

**Response**:

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2026-04-27T12:00:00Z"
}
```

When complete, the report is POSTed to your webhook URL.

### Retrieve Report by ID

```bash
curl -X GET https://api.fakelytics.io/v1/report/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: your_api_key"
```

---

## Python SDK

### Installation

```bash
pip install fakelytics-sdk
```

### Usage

```python
from fakelytics import FakelyticsClient

# Initialize client
client = FakelyticsClient(api_key="your_api_key")

# Synchronous verification
result = client.verify("https://example.com/article")
print(f"Credibility Score: {result.report.overall_credibility_score}")
print(f"Summary: {result.report.summary}")

# Asynchronous verification with webhook
result = client.verify(
    "https://example.com/article",
    async_mode=True,
    webhook_url="https://your-app.com/webhooks"
)
print(f"Request ID: {result.request_id}")

# Retrieve report later
report = client.get_report(result.request_id)
```

---

## Understanding Results

### Credibility Score (0-100)

| Score Range | Interpretation |
|-------------|----------------|
| 0-30 | Low credibility - significant concerns |
| 31-60 | Moderate credibility - some concerns |
| 61-100 | High credibility - generally reliable |

### Verdict Meanings

| Verdict | Meaning |
|---------|---------|
| **Supported** | Evidence supports the content's claims |
| **Disputed** | Evidence contradicts or raises concerns |
| **Unverifiable** | Insufficient evidence to determine |

### Confidence Score

The confidence score (0-100) indicates how certain the pipeline is about its verdict:
- **High (71-100)**: Strong evidence for the verdict
- **Medium (31-70)**: Moderate evidence
- **Low (0-30)**: Weak or insufficient evidence

---

## Error Handling

```python
from fakelytics import FakelyticsClient
from fakelytics.exceptions import (
    FakelyticsError,
    RateLimitError,
    ValidationError
)

try:
    result = client.verify("https://example.com/article")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}")
except ValidationError as e:
    print(f"Invalid request: {e.details}")
except FakelyticsError as e:
    print(f"API error: {e.message}")
```

---

## Rate Limits

| Tier | Requests/Day | Concurrent |
|------|--------------|------------|
| Free | 100 | 1 |
| Pro | 10,000 | 5 |
| Enterprise | Custom | Custom |

---

## Next Steps

- [API Reference](contracts/api-v1.yaml) - Full API documentation
- [Data Model](data-model.md) - Entity definitions
- [Architecture](plan.md) - System design details

---

## Support

- **Documentation**: https://docs.fakelytics.io
- **Dashboard**: https://dashboard.fakelytics.io
- **Support**: support@fakelytics.io