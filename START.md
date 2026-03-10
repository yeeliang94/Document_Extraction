# DocWeaver2 Enterprise Test App

Minimal version of DocWeaver2 for testing on Windows enterprise environment.
Simplified pipeline: PDF → images → LLM vision extraction → agent review.

## Quick Start (Windows)

### First time — run once:

```cmd
setup.bat
```

This will:
- Check Python is installed
- Download portable Node.js if not installed (no admin required)
- Create Python venv and install backend dependencies
- Install frontend npm dependencies
- Create `.env` file from template

After setup, **edit `backend\.env`** with your proxy URL and API key.

### Run the app:

```cmd
start.bat
```

This launches both backend and frontend in separate windows.
- Backend: http://localhost:8002
- Frontend: http://localhost:3000

### If behind a corporate proxy:

Set these **before** running `setup.bat`:

```cmd
set HTTP_PROXY=http://your-proxy:port
set HTTPS_PROXY=http://your-proxy:port
npm config set proxy http://your-proxy:port
npm config set https-proxy http://your-proxy:port
```

## Manual Setup (if scripts don't work)

### 1. Backend

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
:: Edit .env with your API key
python main.py
```

### 2. Frontend

```cmd
cd frontend
npm install
npm run dev
```

If `npm` is not found, download the portable zip from https://nodejs.org/en/download
and extract it. Then add it to PATH:

```cmd
set PATH=C:\path\to\extracted\node;%PATH%
```

## Use

1. Open http://localhost:3000
2. Upload a PDF (financial statements, 3-5 pages)
3. Watch progress bar (3 stages: render → extract → agent review)
4. View extracted fields with values
5. Click "Edit" to override any value
6. See agent corrections at the bottom

## Architecture

```
Browser (localhost:3000)
  ↓ Next.js proxy rewrite
FastAPI (localhost:8002)
  ├── POST /api/documents/upload     → Save PDF, start pipeline
  ├── GET  /api/documents/{id}       → Document status
  ├── GET  /api/documents/{id}/progress → Poll pipeline progress
  ├── GET  /api/documents/{id}/pages/{n}/image → Page PNG
  ├── GET  /api/documents/{id}/fields → Extracted values
  ├── PATCH /api/documents/{id}/fields/{n} → User override
  └── GET  /api/documents/{id}/corrections → Agent changes
```

Pipeline (3 stages):
1. **Render**: pymupdf converts PDF pages to PNG
2. **Extract**: LLM vision reads all pages, extracts 20 financial fields as JSON
3. **Agent Review**: ADK agent with LiteLlm verifies arithmetic (GP, PBT, net profit, balance sheet)
