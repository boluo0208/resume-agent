# Resume Agent Backend

Run:

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The first version works without an API key and returns mock analysis.
To enable real LLM output, set:

```bash
set LLM_API_KEY=your_key
set LLM_BASE_URL=https://api.openai.com/v1
set LLM_MODEL=gpt-4.1-mini
```
