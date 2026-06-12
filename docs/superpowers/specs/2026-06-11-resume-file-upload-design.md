# Resume File Upload & Parse

Date: 2026-06-11 | Status: approved

## Purpose

Add PDF/DOCX resume upload with automatic text extraction, keeping paste as fallback. After upload, extracted text auto-fills the textarea, then runs through the existing multi-agent pipeline unchanged.

## Architecture

```
POST /api/resume/parse  (NEW — file upload + text extraction)
POST /api/analyze       (UNCHANGED — multi-agent pipeline)

Frontend: upload button → parse endpoint → auto-fill textarea → user can edit → analyze endpoint
```

## Backend

### New endpoint: `POST /api/resume/parse`

- Request: `multipart/form-data` with field `file`
- Response: `{ filename: str, resume_text: str, char_count: int }`
- Max file size: 10 MB (FastAPI middleware)
- Supported formats: `.pdf` (application/pdf), `.docx` (application/vnd.openxmlformats-officedocument.wordprocessingml.document)

### New service: `ResumeParserService` (`backend/app/services/resume_parser.py`)

```python
class ResumeParserService:
    async def parse(self, file: UploadFile) -> dict:
        # 1. detect format by extension + MIME
        # 2. read into BytesIO
        # 3. dispatch to parse_pdf() or parse_docx()
        # 4. validate result is non-empty
        # 5. return {filename, resume_text, char_count}
```

**PDF**: pdfplumber — iterate `page.extract_text()`, join with `\n\n`.
**DOCX**: python-docx — iterate `paragraph.text`, join with `\n`.

### Error handling

| Scenario | HTTP Status | Message |
|---|---|---|
| Unsupported format | 400 | "仅支持 .pdf 和 .docx 格式" |
| File too large | 413 | "文件大小不能超过 10MB" |
| Empty extracted text | 422 | "无法从文件中提取文本内容，请尝试手动粘贴" |
| Corrupted file | 500 | Internal, logged |

### Dependencies (added to requirements.txt)

- `pdfplumber`
- `python-docx`

## Frontend

### New API function (`frontend/src/api/index.js`)

```js
parseResumeFile(file) → POST /api/resume/parse as FormData
```

### UI changes (`frontend/src/views/Analyze.vue`)

Above the resume textarea, add a row with:
- Upload button (`el-upload` with custom request) — accepts `.pdf,.docx`
- File name display
- Clear button (reset file + textarea)

Behavior:
- Selecting a file → call `/api/resume/parse` → on success, set `form.resume_text` + show green toast
- On failure → red toast, textarea unchanged, user can paste manually
- Upload and paste are peers; neither disables the other

## Unchanged

- `/api/analyze` endpoint, all agents, LLM service, schemas — no changes
- The multi-agent pipeline stays: Parse → Match → Review → Rewrite
- The `resume_text` field in `AnalysisRequest` remains the source of truth

## Future

- OCR for scanned PDFs
- History of uploaded files
- PDF report generation
