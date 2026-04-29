# Development Guide

This guide explains how to set up the development environment and run tests for Fakelytics.

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-org/fakelytics.git
cd fakelytics

# Create and activate virtual environment
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy configuration template
cp .env.example .env
```

### 2. Start Required Services

```bash
# Start Redis (required for Celery)
redis-server
# Redis will run on localhost:6379

# In another terminal, start the FastAPI server
python -m uvicorn src.api.main:app --reload

# API will be available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/contract/test_api_contract.py -v

# Run with coverage report
pytest --cov=src --cov-report=html

# Run only quick tests (skip slow tests)
pytest -m "not slow"
```

## API Testing

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Verify a URL
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Get report
curl http://localhost:8000/api/v1/verify/{request_id}
```

### Using Python

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Verify URL
response = requests.post(
    "http://localhost:8000/api/v1/verify",
    json={
        "url": "https://example.com",
        "options": {"async_mode": False}
    }
)
result = response.json()
print(result)

# Get report
request_id = result["request_id"]
response = requests.get(f"http://localhost:8000/api/v1/verify/{request_id}")
print(response.json())
```

### Using FastAPI Docs

Open http://localhost:8000/docs (Swagger UI) or http://localhost:8000/redoc (ReDoc) to explore the API interactively.

## Development Tasks

### Adding a New Endpoint

1. Create route handler in `src/api/routes/`
2. Add Pydantic models in `src/api/models/schemas.py`
3. Include router in `src/api/main.py`
4. Add tests in `tests/contract/`

### Adding a New Service

1. Create service module in `src/services/` or `src/core/`
2. Follow async patterns (use `async def` where appropriate)
3. Add comprehensive logging with trace IDs
4. Write unit tests in `tests/unit/`

### Running Celery Workers

```bash
# Start Celery worker
celery -A src.workers.celery_app worker --loglevel=info

# In another terminal, you can send tasks
celery -A src.workers.celery_app inspect active
```

## Code Quality

### Formatting

```bash
# Format code with Black
black src/ tests/

# Sort imports with isort
isort src/ tests/
```

### Linting

```bash
# Check code with flake8
flake8 src/ tests/

# Type checking with mypy
mypy src/
```

### Pre-commit Hooks (Optional)

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Debugging

### Enable Debug Logging

Set in `.env`:
```
DEBUG=true
LOG_LEVEL=DEBUG
```

### VS Code Debugging

Add to `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Debug",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["src.api.main:app", "--reload", "--port", "8000"],
            "console": "integratedTerminal",
        }
    ]
}
```

Then press F5 to start debugging.

### Inspect Requests/Responses

```python
# In any route handler
from fastapi import Request

@router.post("/verify")
async def verify(request: Request):
    trace_id = getattr(request.state, "trace_id", "unknown")
    print(f"Trace ID: {trace_id}")
    # ... rest of handler
```

## Database Migrations (Phase 2)

When PostgreSQL integration is added:

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Troubleshooting

### Redis Connection Error

If you get "connection refused" for Redis:
1. Ensure Redis is running: `redis-server`
2. Check Redis is on localhost:6379
3. Update REDIS_URL in .env if needed

### Import Errors

If imports fail:
1. Ensure virtual environment is activated
2. Run `pip install -r requirements.txt`
3. Check PYTHONPATH includes project root

### Test Failures

```bash
# Run with more verbose output
pytest -vv

# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Run only last failed
pytest --lf
```

## Performance Profiling

```bash
# Profile test execution
pytest --profile

# Profile specific function
import cProfile
cProfile.run('my_function()')
```

## Documentation

Generate docs:
```bash
# Using MkDocs (if installed)
mkdocs serve
```

Docs will be available at http://localhost:8000

## Release Checklist

Before merging to main:
- [ ] All tests pass: `pytest`
- [ ] Code formatted: `black src/ tests/`
- [ ] Imports sorted: `isort src/ tests/`
- [ ] Linting passes: `flake8 src/ tests/`
- [ ] Type checking passes: `mypy src/`
- [ ] Updated CHANGELOG.md
- [ ] Bumped version number
- [ ] Created release notes

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Celery Documentation](https://docs.celeryproject.io/)
- [Redis Documentation](https://redis.io/documentation)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)

## Getting Help

- Check existing issues on GitHub
- Review specification in `specs/001-fakelytics-platform/`
- Ask in team chat or create an issue
