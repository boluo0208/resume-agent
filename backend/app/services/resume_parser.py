import io
import re

from fastapi import UploadFile

from app.services.llm_service import LLMService, LLMServiceError


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
READ_CHUNK_SIZE = 1024 * 1024


class ResumeParserService:
    """Extract text from PDF/DOCX resume files and images via Tesseract OCR."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

    async def parse(self, file: UploadFile) -> dict:
        filename = file.filename or "unknown"
        self._validate_format(filename, file.content_type)
        content = await self._read_limited(file)

        ext = self._get_extension(filename)
        self._validate_signature(ext, content)
        if ext == ".pdf":
            text = self._parse_pdf(content)
        else:
            text = self._parse_docx(content)

        if not text.strip():
            raise EmptyContentError(
                "无法从文件中提取文本内容，请确认文件包含文字而非扫描图片，或尝试手动粘贴。"
            )

        return {
            "filename": filename,
            "resume_text": text.strip(),
            "char_count": len(text),
        }

    def _validate_format(self, filename: str, content_type: str | None):
        ext = self._get_extension(filename)
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(
                f"仅支持 .pdf 和 .docx 格式，当前文件: {ext or '未知'}"
            )

    def _get_extension(self, filename: str) -> str:
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ""

    def _parse_pdf(self, content: bytes) -> str:
        import pdfplumber

        pages: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
        return "\n\n".join(pages)

    def _parse_docx(self, content: bytes) -> str:
        from docx import Document

        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    async def parse_image(self, file: UploadFile) -> dict:
        """Extract text from an image via LLM vision first, then local OCR."""
        filename = file.filename or "unknown"

        self._validate_image_format(filename, file.content_type)

        content = await self._read_limited(file)
        text = await self._parse_image_with_llm(content, file.content_type or "image/png")
        source = "llm_vision" if text.strip() else "local_ocr"
        if not text.strip():
            text = self._parse_image_ocr(content)
        text = self._clean_ocr_text(text)

        if not text.strip():
            raise EmptyContentError(
                "无法从图片中提取文字，请确认图片清晰且包含文字内容，或尝试手动粘贴。"
            )

        return {
            "filename": filename,
            "text": text.strip(),
            "char_count": len(text),
            "source": source,
        }

    async def _parse_image_with_llm(self, content: bytes, mime_type: str) -> str:
        llm = LLMService()
        if not llm.available:
            return ""
        try:
            return await llm.complete_image(
                "你是 OCR 文本提取助手。请完整提取图片中的招聘 JD 文本，保留自然段落和编号，修正常见 OCR 错字，不要添加解释。",
                content,
                mime_type=mime_type,
            )
        except LLMServiceError:
            return ""

    def _parse_image_ocr(self, content: bytes) -> str:
        """Run Tesseract OCR on image bytes. Supports Chinese + English, falls back to English."""
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        import os
        import sys

        # Tesseract installed by winget may not be on PATH
        if sys.platform == "win32":
            default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            if os.path.exists(default_path):
                pytesseract.pytesseract.tesseract_cmd = default_path

        try:
            image = Image.open(io.BytesIO(content))
            image.verify()
            image = Image.open(io.BytesIO(content))
        except Exception as exc:
            raise UnsupportedFormatError("图片文件无法识别，请上传清晰的 PNG/JPG/WEBP 图片。") from exc

        image = ImageOps.exif_transpose(image).convert("L")
        if image.width < 1400:
            ratio = 1400 / image.width
            image = image.resize((int(image.width * ratio), int(image.height * ratio)))
        image = ImageOps.autocontrast(image)
        image = ImageEnhance.Contrast(image).enhance(1.4)
        image = image.filter(ImageFilter.SHARPEN)

        # User tessdata dir for custom language packs (avoids admin permission issues)
        user_tessdata = os.path.expanduser(r"~\.tesseract\tessdata")
        tessdata_config = ""
        if os.path.isdir(user_tessdata):
            tessdata_config = f'--tessdata-dir {user_tessdata}'

        candidates: list[str] = []
        configs = [
            "--psm 6 -c preserve_interword_spaces=0",
            "--psm 4 -c preserve_interword_spaces=0",
            "--psm 3 -c preserve_interword_spaces=0",
        ]
        for lang in ("chi_sim+eng", "eng"):
            try:
                for config in configs:
                    text = pytesseract.image_to_string(image, lang=lang, config=f"{tessdata_config} {config}".strip())
                    if text.strip():
                        candidates.append(text)
            except pytesseract.TesseractNotFoundError:
                raise RuntimeError(
                    "Tesseract OCR 引擎未安装。请在 https://github.com/UB-Mannheim/tesseract/wiki 下载安装，"
                    "安装时勾选中文语言包 (Chinese Simplified)。"
                )
            except Exception:
                continue

        if candidates:
            return max(candidates, key=self._ocr_quality_score)

        return ""

    def _ocr_quality_score(self, text: str) -> int:
        cleaned = self._clean_ocr_text(text)
        cjk = len(re.findall(r"[\u4e00-\u9fff]", cleaned))
        ascii_words = len(re.findall(r"[A-Za-z]{2,}", cleaned))
        useful_marks = len(re.findall(r"[，。；：、,.();:0-9]", cleaned))
        suspicious = len(re.findall(r"[|{}\[\]‖〕〔_`~^]", cleaned))
        return cjk * 3 + ascii_words * 2 + useful_marks - suspicious * 8

    def _clean_ocr_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)

        # Tesseract often separates every Chinese character with spaces.
        previous = None
        while previous != text:
            previous = text
            text = re.sub(r"([\u4e00-\u9fff])\s+([\u4e00-\u9fff])", r"\1\2", text)

        text = re.sub(r"\s+([，。；：、！？])", r"\1", text)
        text = re.sub(r"([（《“])\s+", r"\1", text)
        text = re.sub(r"\s+([）》”])", r"\1", text)
        text = re.sub(r"([0-9])\s*[、,.]\s*", r"\1、", text)
        text = re.sub(r"\b([A-Za-z])\s+(?=[A-Za-z]\b)", r"\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return "\n".join(line.strip() for line in text.splitlines()).strip()

    def _validate_image_format(self, filename: str, content_type: str | None):
        ext = self._get_extension(filename)
        if ext not in self.IMAGE_EXTENSIONS:
            raise UnsupportedFormatError(
                f"仅支持图片格式 ({', '.join(self.IMAGE_EXTENSIONS)})，当前文件: {ext or '未知'}"
            )

    async def _read_limited(self, file: UploadFile) -> bytes:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(READ_CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise UnsupportedFormatError("文件大小不能超过 10MB。")
            chunks.append(chunk)
        return b"".join(chunks)

    def _validate_signature(self, ext: str, content: bytes):
        if ext == ".pdf" and not content.startswith(b"%PDF"):
            raise UnsupportedFormatError("文件扩展名是 .pdf，但内容不是有效 PDF。")
        if ext == ".docx" and not content.startswith(b"PK"):
            raise UnsupportedFormatError("文件扩展名是 .docx，但内容不是有效 DOCX。")


class UnsupportedFormatError(ValueError):
    """Raised when the uploaded file format is not supported."""
    pass


class EmptyContentError(ValueError):
    """Raised when the file contains no extractable text."""
    pass
