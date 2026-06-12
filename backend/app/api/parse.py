from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.services.resume_parser import ResumeParserService, EmptyContentError, UnsupportedFormatError

router = APIRouter(prefix="/api", tags=["parse"])
service = ResumeParserService()


@router.post("/resume/parse")
async def parse_resume_file(file: UploadFile = File(...)):
    """Upload a PDF or DOCX resume file and extract its text content."""
    try:
        result = await service.parse(file)
        return result
    except UnsupportedFormatError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except EmptyContentError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"detail": f"文件解析失败: {exc}"})


@router.post("/resume/parse-image")
async def parse_jd_image(file: UploadFile = File(...)):
    """Upload a job description image and extract text via Tesseract OCR."""
    try:
        result = await service.parse_image(file)
        return result
    except UnsupportedFormatError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except EmptyContentError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except RuntimeError as exc:
        return JSONResponse(status_code=503, content={"detail": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"detail": f"图片解析失败: {exc}"})
