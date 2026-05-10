# Fakelytics API - Postman/cURL Test Examples

**API Base URL**: `http://127.0.0.1:8000`  
**API Key**: `dev-key-change-in-production`  
**API Version**: `v1`

---

## 1. Health Check

### cURL
```bash
curl -X GET "http://127.0.0.1:8000/health" \
  -H "Content-Type: application/json"
```

### Postman
- **Method**: GET
- **URL**: `http://127.0.0.1:8000/health`
- **Headers**: None required
- **Expected Response**: 200 OK

```json
{
    "status": "healthy",
    "version": "0.1.0",
    "timestamp": "2026-05-04T12:12:39.692351"
}
```

---

## 2. Root Endpoint

### cURL
```bash
curl -X GET "http://127.0.0.1:8000/" \
  -H "Content-Type: application/json"
```

### Postman
- **Method**: GET
- **URL**: `http://127.0.0.1:8000/`
- **Expected Response**: 200 OK

```json
{
    "name": "Fakelytics",
    "version": "0.1.0",
    "docs": "/docs",
    "api_prefix": "/api/v1"
}
```

---

## 3. Verify URL - Synchronous Mode (Default)

### cURL - Simple Request
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-change-in-production" \
  -d '{
    "url": "https://www.wikipedia.org/wiki/Water"
  }'
```

### cURL - With Request Options
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-change-in-production" \
  -d '{
    "url": "https://www.example.com",
    "options": {
      "async_mode": false,
      "timeout_seconds": 60,
      "pipelines": ["text", "image", "spam"]
    }
  }'
```

### Postman
- **Method**: POST
- **URL**: `http://127.0.0.1:8000/api/v1/verify`
- **Headers**:
  - `Content-Type: application/json`
  - `X-API-Key: dev-key-change-in-production`
- **Body** (JSON):
```json
{
  "url": "https://www.wikipedia.org/wiki/Water"
}
```

### Expected Response (200 OK)
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "url": "https://www.wikipedia.org/wiki/Water",
  "report": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://www.wikipedia.org/wiki/Water",
    "overall_credibility_score": 78,
    "summary": "Content appears credible with minor concerns",
    "findings": {
      "text": {
        "verdict": "Supported",
        "confidence": 85,
        "findings": [...]
      },
      "spam": {
        "verdict": "Supported",
        "confidence": 90,
        "findings": [...]
      }
    },
    "timestamp": "2026-05-04T12:15:30.123456"
  }
}
```

---

## 4. Verify URL - Asynchronous Mode with Webhook

### cURL
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-change-in-production" \
  -d '{
    "url": "https://www.bbc.com/news",
    "options": {
      "async_mode": true,
      "webhook_url": "https://your-server.com/webhook",
      "timeout_seconds": 120,
      "pipelines": ["text", "image", "audio_video", "spam"]
    }
  }'
```

### Postman
- **Method**: POST
- **URL**: `http://127.0.0.1:8000/api/v1/verify`
- **Headers**:
  - `Content-Type: application/json`
  - `X-API-Key: dev-key-change-in-production`
- **Body** (JSON):
```json
{
  "url": "https://www.bbc.com/news",
  "options": {
    "async_mode": true,
    "webhook_url": "https://your-webhook-endpoint.com/callback",
    "timeout_seconds": 120
  }
}
```

### Expected Response (202 Accepted)
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "processing",
  "url": "https://www.bbc.com/news",
  "message": "Verification in progress. Results will be sent to webhook."
}
```

---

## 5. Get Report by Request ID

### cURL
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/verify/550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-change-in-production"
```

### Postman
- **Method**: GET
- **URL**: `http://127.0.0.1:8000/api/v1/verify/{request_id}`
- **Example**: `http://127.0.0.1:8000/api/v1/verify/550e8400-e29b-41d4-a716-446655440000`
- **Headers**:
  - `X-API-Key: dev-key-change-in-production`

### Expected Response (200 OK - Completed)
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "report": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://www.wikipedia.org/wiki/Water",
    "overall_credibility_score": 78,
    "summary": "Content appears credible",
    "findings": {...}
  }
}
```

### Expected Response (202 Accepted - Still Processing)
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "processing",
  "message": "Verification still in progress"
}
```

### Expected Response (404 Not Found)
```json
{
  "detail": {
    "error": "not_found",
    "message": "Request not found"
  }
}
```

---

## 6. Error Cases

### Missing API Key

### cURL
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Expected Response (401 Unauthorized)
```json
{
  "detail": {
    "error": "unauthorized",
    "message": "Missing API key"
  }
}
```

---

### Invalid API Key

### cURL
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: invalid-key-12345" \
  -d '{"url": "https://example.com"}'
```

### Expected Response (401 Unauthorized)
```json
{
  "detail": {
    "error": "unauthorized",
    "message": "Invalid API key"
  }
}
```

---

### Invalid URL Format

### cURL
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-change-in-production" \
  -d '{"url": "not-a-url"}'
```

### Expected Response (400 Bad Request)
```json
{
  "detail": {
    "error": "validation_error",
    "message": "Invalid URL format"
  }
}
```

---

### Private IP Address (Security Block)

### cURL
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-change-in-production" \
  -d '{"url": "http://192.168.1.1"}'
```

### Expected Response (400 Bad Request)
```json
{
  "detail": {
    "error": "extraction_failed",
    "message": "Failed to extract content: Private/local IP addresses are not allowed"
  }
}
```

---

### Rate Limit Exceeded

### cURL
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-change-in-production" \
  -d '{"url": "https://example.com"}'
```

### Expected Response (429 Too Many Requests) - After exceeding daily limit
```json
{
  "detail": {
    "error": "rate_limit_exceeded",
    "message": "Rate limit exceeded for this API key",
    "details": {
      "tier": "free",
      "retry_after": 86400
    }
  }
}
```

---

## 7. Postman Collection Template

Save this as `fakelytics-postman-collection.json`:

```json
{
  "info": {
    "name": "Fakelytics API",
    "description": "Multimodal Content Verification Platform",
    "version": "1.0.0"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://127.0.0.1:8000/health",
          "protocol": "http",
          "host": ["127", "0", "0", "1"],
          "port": "8000",
          "path": ["health"]
        }
      }
    },
    {
      "name": "Verify URL - Sync",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          },
          {
            "key": "X-API-Key",
            "value": "dev-key-change-in-production"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"url\": \"https://www.wikipedia.org/wiki/Water\"}"
        },
        "url": {
          "raw": "http://127.0.0.1:8000/api/v1/verify",
          "protocol": "http",
          "host": ["127", "0", "0", "1"],
          "port": "8000",
          "path": ["api", "v1", "verify"]
        }
      }
    },
    {
      "name": "Verify URL - Async",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          },
          {
            "key": "X-API-Key",
            "value": "dev-key-change-in-production"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"url\": \"https://www.bbc.com/news\", \"options\": {\"async_mode\": true}}"
        },
        "url": {
          "raw": "http://127.0.0.1:8000/api/v1/verify",
          "protocol": "http",
          "host": ["127", "0", "0", "1"],
          "port": "8000",
          "path": ["api", "v1", "verify"]
        }
      }
    }
  ]
}
```

---

## 8. Quick Test Sequence

1. **Check API is running**:
   ```bash
   curl -X GET "http://127.0.0.1:8000/health"
   ```

2. **Submit verification request**:
   ```bash
   curl -X POST "http://127.0.0.1:8000/api/v1/verify" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev-key-change-in-production" \
     -d '{"url": "https://www.wikipedia.org/wiki/Water"}' > request.json
   ```

3. **Extract request_id from response and check status**:
   ```bash
   REQUEST_ID=$(jq -r '.request_id' request.json)
   curl -X GET "http://127.0.0.1:8000/api/v1/verify/$REQUEST_ID" \
     -H "X-API-Key: dev-key-change-in-production"
   ```

---

## API Response Headers

All responses include these headers:

```
Content-Type: application/json
X-Trace-ID: {trace-id-for-debugging}
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: {seconds-until-reset}
X-RateLimit-Tier: free
```

---

## Rate Limiting Tiers

| Tier | Daily Limit | Example API Key |
|------|-------------|-----------------|
| Free | 100 | `free_xxxxx` or `dev-key-change-in-production` |
| Pro | 10,000 | `pro_xxxxx` |
| Enterprise | 1,000,000 | `enterprise_xxxxx` or `ent_xxxxx` |

---

## Notes

- Replace `dev-key-change-in-production` with your actual API key
- Change `127.0.0.1:8000` to match your deployment URL
- Real URL fetching requires internet access; local testing may timeout
- Async mode requires webhook endpoint to receive results
- All responses include timestamps in ISO 8601 format
