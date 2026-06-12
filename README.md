# Resume Agent

A Vue + FastAPI MVP for resume analysis agents.

## Run Backend

```powershell
cd F:\resume-agent\backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run Frontend

```powershell
cd F:\resume-agent\frontend
npm.cmd install
npm.cmd run dev
```

Open http://localhost:5173

## Deploy With Docker

On an Ubuntu server with Docker and Docker Compose:

```bash
git clone https://github.com/boluo0208/resume-agent.git
cd resume-agent
cp backend/.env.example backend/.env
nano backend/.env
docker compose up -d --build
```

Then open:

```text
http://your-server-public-ip
```

The frontend container listens on port 80 and proxies `/api` requests to the backend container.

## API

- Health: http://localhost:8000/api/health
- LLM status: http://localhost:8000/api/llm/status
- Analyze: `POST /api/analyze`
- Parse resume file: `POST /api/resume/parse`
- Parse JD image: `POST /api/resume/parse-image`

## Enable Real LLM

By default the project can run in `mock` mode without an API key. To enable real model output, create `F:\resume-agent\backend\.env` from `F:\resume-agent\backend\.env.example`:

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

Then restart the backend.

If the configured LLM is unavailable, `/api/analyze` automatically falls back to mock analysis so the workflow remains usable.

## Agent Roadmap

1. ResumeAnalysisAgent: orchestrate the analysis pipeline.
2. ResumeParserAgent: parse resume into JSON.
3. JDMatchAgent: compare resume with job description.
4. RewriteAgent: rewrite weak resume content.
5. InterviewAgent: generate interview questions from resume.
