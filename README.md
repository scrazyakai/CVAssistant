# AI Resume Analysis Assistant

MVP project built with `FastAPI + DashScope(Qwen) + Vue`.
It uploads resume PDFs directly to Qwen for structured extraction and JD matching.

## Features

- Upload a single PDF resume
- Upload resume PDFs directly to Qwen through DashScope's OpenAI-compatible API
- Let Qwen read the PDF and extract candidate information
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
LLM_API_KEY=your_dashscope_api_key
LLM_MODEL=qwen-doc-turbo
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
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

Form data:

- `file`: PDF resume
- `job_description`: target job description

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

The backend uses Qwen through DashScope's OpenAI-compatible endpoint and sends the uploaded PDF directly to the model. If the model call fails, the API returns an error instead of falling back to local heuristics.

## Next Improvements

- Add Redis cache
- Add OCR for scanned PDFs
- Improve Chinese resume heuristics
- Add authentication and persistence
- Deploy frontend and backend to public environments
