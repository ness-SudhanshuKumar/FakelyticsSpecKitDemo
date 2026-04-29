# Run Fakelytics in WSL (Ubuntu) - Step by Step

This guide runs the project fully inside WSL.

## 1) Open WSL and go to the project

```bash
cd /mnt/c/Users/P7114330/Sudhanshu/AIHackathon/FakelyticsSpecKitDemo
```

## 2) Install required system packages (one-time)

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

If your distro asks for a versioned package:

```bash
sudo apt install -y python3.12-venv
```

## 3) Create and activate virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should now see `(.venv)` in your terminal prompt.

## 4) Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 5) Create environment file

```bash
cp .env.example .env
```

## 6) Configure API keys and runtime settings in `.env`

Open `.env` and set at least:

```env
# Required for API auth (used by X-API-Key header)
API_KEY=dev-key
API_KEYS=dev-key

# Optional but recommended
DEBUG=false
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
```

Optional external keys (only if you plan to use those integrations later):

```env
OPENAI_API_KEY=
SERPAPI_KEY=
```

## 7) Start the API server

```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Server URLs:
- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## 8) Test the API (new terminal tab in WSL)

### Health check

```bash
curl -sS http://localhost:8000/health
```

### Sync verification request

```bash
curl -sS -X POST "http://localhost:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key" \
  -d '{"url":"https://example.com","options":{"async_mode":false}}'
```

### Get report (replace `<REQUEST_ID>`)

```bash
curl -sS -H "X-API-Key: dev-key" \
  "http://localhost:8000/api/v1/report/<REQUEST_ID>"
```

## 9) Run tests

```bash
pytest -q
```

## 10) Deactivate environment when done

```bash
deactivate
```

---

## Common issues

### `ensurepip is not available`
Install venv package:

```bash
sudo apt install -y python3-venv
```

or

```bash
sudo apt install -y python3.12-venv
```

### `401 Unauthorized`
You must send header:

```bash
-H "X-API-Key: dev-key"
```

and ensure `.env` has matching `API_KEY` / `API_KEYS`.

### Port 8000 already in use

```bash
lsof -i :8000
kill -9 <PID>
```
