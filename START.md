# DocWeaver2 Enterprise Test App

Minimal version of DocWeaver2 for testing on Windows enterprise environment.
Simplified pipeline: PDF → images → LLM vision extraction → agent review.

## Quick Start (Windows)

### 1. Backend

```cmd
cd app\backend

:: Create virtual environment
python -m venv .venv
.venv\Scripts\activate

:: Install dependencies
pip install -r requirements.txt

:: Configure
copy .env.example .env
:: Edit .env with your proxy URL and API key

:: Run
python main.py
```

Backend will start on http://localhost:8002

### 2. Frontend

```cmd
cd app\frontend

:: Install dependencies
npm install

:: Run
npm run dev
```

Frontend will start on http://localhost:3000

### 3. Use

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

## What this tests

- pymupdf on Windows (file paths, image rendering)
- OpenAI SDK → enterprise proxy (chat completions, vision, JSON mode)
- ADK LlmAgent + LiteLlm + tool calling through proxy
- SQLite database on Windows
- FastAPI + Next.js full stack on Windows
- Background thread pipeline execution
