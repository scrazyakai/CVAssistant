# AI Resume Analysis Assistant

MVP project built with `FastAPI + LangChain + OpenAI + PyMuPDF + Vue`.
It supports PDF resume parsing, structured information extraction, and job-description matching.

## Features

- Upload a single PDF resume
- Extract text from multi-page PDFs with `PyMuPDF`
- Clean and normalize resume text
- Use `LangChain + OpenAI` to extract candidate information
- Match a resume against a job description and return structured scores
- Cache repeated parse and match results locally in `.cache/`
- Provide a simple Vue frontend for demo and review

## Project Structure

```text
.
|-- app
|   |-- api
|   |-- core
|   |-- models
|   `-- services
|-- frontend
`-- requirements.txt
```

## Backend Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy [`.env.example`](/C:/Users/AKai/Desktop/CVAnalysisAssistant/.env.example) to `.env`.

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
CORS_ORIGINS=["http://localhost:5173"]
```

### 3. Start the backend

```bash
uvicorn app.main:app --reload
```

Available endpoints:

- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health check: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

If needed, copy [`frontend/.env.example`](/C:/Users/AKai/Desktop/CVAnalysisAssistant/frontend/.env.example) to `frontend/.env`:

```env
VITE_API_BASE=http://127.0.0.1:8000/api/v1
```

## API Summary

### `POST /api/v1/resumes/parse`

Form data:

- `file`: PDF resume

Returns cleaned text and extracted candidate information.

### `POST /api/v1/resumes/match`

JSON body:

```json
{
  "job_description": "3+ years Python backend experience with FastAPI and LLM products",
  "resume_text": "cleaned resume text",
  "extracted_info": {}
}
```

Returns structured match scoring.

### `POST /api/v1/resumes/analyze`

Form data:

- `file`: PDF resume
- `job_description`: target job description

Returns parse result and match result in one request.

## Deployment

### Frontend

GitHub Pages workflow is provided in [`.github/workflows/deploy-frontend.yml`](/C:/Users/AKai/Desktop/CVAnalysisAssistant/.github/workflows/deploy-frontend.yml).

### Backend

A `Dockerfile` and `render.yaml` are included for deployment to Render or similar platforms.

## Fallback Behavior

If `OPENAI_API_KEY` is missing or the model call fails, the backend falls back to local heuristics so the demo flow still works.

## Next Improvements

- Add Redis cache
- Add OCR for scanned PDFs
- Improve Chinese resume heuristics
- Add authentication and persistence
- Deploy frontend and backend to public environments
