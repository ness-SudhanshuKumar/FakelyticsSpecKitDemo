"""
CURL Test Payloads for Fakelytics Platform

The API is running at: http://localhost:8000

All endpoints are available with these test cases.
"""

# ============================================================
# 1. HEALTH CHECK
# ============================================================

# Check if the API is running
curl -X GET http://localhost:8000/health

# Expected Response (200 OK):
# {
#   "status": "healthy",
#   "version": "0.1.0",
#   "timestamp": "2026-04-29T14:30:45.123456"
# }


# ============================================================
# 2. ROOT ENDPOINT
# ============================================================

# Get API information
curl -X GET http://localhost:8000/

# Expected Response (200 OK):
# {
#   "name": "Fakelytics",
#   "version": "0.1.0",
#   "docs": "/docs",
#   "api_prefix": "/api/v1"
# }


# ============================================================
# 3. SUBMIT URL FOR VERIFICATION (POST /verify)
# ============================================================

# Test Case 3a: Basic URL verification (sync mode)
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.wikipedia.org/wiki/Water",
    "options": {
      "async_mode": false
    }
  }'

# Expected Response (200 OK):
# {
#   "request_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "completed",
#   "report": {
#     "url": "https://www.wikipedia.org/wiki/Water",
#     "overall_credibility_score": 78,
#     "summary": "URL content appears credible based on source reputation",
#     "findings": [...],
#     "timestamp": "2026-04-29T14:30:45.123456"
#   }
# }


# Test Case 3b: Longer news article URL
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.bbc.com/news/world",
    "options": {
      "async_mode": false,
      "timeout_seconds": 60
    }
  }'


# Test Case 3c: Async mode with webhook callback
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article",
    "options": {
      "async_mode": true,
      "webhook_url": "https://your-server.com/callback",
      "timeout_seconds": 60
    }
  }'

# Expected Response (202 Accepted):
# {
#   "request_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "processing",
#   "message": "Verification in progress. Results will be posted to webhook."
# }


# Test Case 3d: With specific pipelines
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.cnn.com/article",
    "options": {
      "async_mode": false,
      "pipelines": ["text", "image", "spam"]
    }
  }'


# Test Case 3e: Invalid URL (should return 400)
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "not-a-valid-url"
  }'

# Expected Response (400 Bad Request):
# {
#   "error": "validation_error",
#   "message": "Invalid URL format",
#   "details": { ... }
# }


# Test Case 3f: Very long URL (over 2048 chars - should be rejected)
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/very/long/path/that/exceeds/2048/characters/...",
    "options": {
      "async_mode": false
    }
  }'


# ============================================================
# 4. GET REPORT BY REQUEST ID
# ============================================================

# Replace REQUEST_ID with actual ID from verify response

# Test Case 4a: Get completed report
curl -X GET http://localhost:8000/api/v1/verify/550e8400-e29b-41d4-a716-446655440000

# Expected Response (200 OK):
# {
#   "request_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "completed",
#   "report": {
#     "url": "https://www.wikipedia.org/wiki/Water",
#     "overall_credibility_score": 78,
#     "summary": "...",
#     "findings": [
#       {
#         "pipeline": "text_factcheck",
#         "verdict": "Supported",
#         "confidence": 85,
#         "evidence": [
#           {
#             "url": "https://source.com/fact",
#             "snippet": "Water freezes at 0°C",
#             "validated": true
#           }
#         ]
#       }
#     ],
#     "timestamp": "2026-04-29T14:30:45.123456"
#   }
# }


# Test Case 4b: Get report that's still processing (async)
curl -X GET http://localhost:8000/api/v1/verify/550e8400-e29b-41d4-a716-446655440001

# Expected Response (202 Accepted):
# {
#   "request_id": "550e8400-e29b-41d4-a716-446655440001",
#   "status": "processing",
#   "message": "Report is being processed"
# }


# Test Case 4c: Get report for non-existent request ID
curl -X GET http://localhost:8000/api/v1/verify/00000000-0000-0000-0000-000000000000

# Expected Response (404 Not Found):
# {
#   "error": "not_found",
#   "message": "Request not found",
#   "details": { "trace_id": "..." }
# }


# Test Case 4d: Invalid request ID format (not a valid UUID)
curl -X GET http://localhost:8000/api/v1/verify/not-a-uuid

# Expected Response (422 Unprocessable Entity):
# {
#   "error": "validation_error",
#   "message": "Invalid request ID format",
#   "details": { ... }
# }


# ============================================================
# 5. INTERACTIVE TESTING
# ============================================================

# Use the interactive API documentation:
# - Swagger UI: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
# - OpenAPI JSON: http://localhost:8000/openapi.json


# ============================================================
# 6. COMPLETE WORKFLOW TEST
# ============================================================

# Step 1: Submit URL for verification
REQUEST_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.wikipedia.org/wiki/Climate_change",
    "options": {
      "async_mode": false,
      "timeout_seconds": 60
    }
  }')

# Extract request_id (requires jq for JSON parsing)
REQUEST_ID=$(echo $REQUEST_RESPONSE | jq -r '.request_id')

echo "Submitted verification request: $REQUEST_ID"

# Step 2: Get the report
curl -s -X GET http://localhost:8000/api/v1/verify/$REQUEST_ID | jq '.'


# ============================================================
# 7. ERROR HANDLING TESTS
# ============================================================

# Test 7a: Missing required field
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "options": {
      "async_mode": false
    }
  }'

# Expected Response (422 Unprocessable Entity)


# Test 7b: Invalid JSON
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d 'this is not json'

# Expected Response (422 Unprocessable Entity)


# Test 7c: Private IP (should be blocked)
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://192.168.1.1/admin",
    "options": {
      "async_mode": false
    }
  }'

# Expected Response (400 Bad Request) - "Private IP address not allowed"


# ============================================================
# 8. ADVANCED TESTING WITH SPECIFIC CLAIMS
# ============================================================

# Test with URL containing factual claims
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/science-facts",
    "options": {
      "async_mode": false,
      "pipelines": ["text", "spam"],
      "timeout_seconds": 60
    }
  }'

# This will:
# 1. Extract text from the URL
# 2. Preprocess and clean it
# 3. Extract claims (T-302)
# 4. Fact-check each claim (T-302)
# 5. Return findings with verdicts


# ============================================================
# 9. RESPONSE ANALYSIS
# ============================================================

# Finding Verdict Values: "Supported", "Disputed", "Unverifiable"
# Confidence Scores: 0-100 (higher = more confident)
# Overall Score: 0-100 (higher = more credible)

# Example Finding:
# {
#   "pipeline": "text_factcheck",
#   "verdict": "Supported",
#   "confidence": 85,
#   "evidence": [
#     {
#       "url": "https://en.wikipedia.org/wiki/...",
#       "snippet": "Claim supported by this text...",
#       "validated": true
#     }
#   ],
#   "summary": "Claim supported by reliable sources"
# }

