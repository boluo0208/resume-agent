import asyncio
import json
import os
import re
from urllib import request
from urllib.error import HTTPError, URLError


class LLMServiceError(RuntimeError):
    """Raised when the configured LLM cannot return a usable response."""


class LLMService:
    """OpenAI-compatible chat completions client for all agents."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        self.api_key = (os.getenv("LLM_API_KEY", "") if api_key is None else api_key).strip()
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4.1-mini")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.25,
        }
        req = self._build_request(body)
        result = await self._send(req, timeout=90, label="LLM request")
        return self._parse_json(self._extract_content(result))

    async def complete_image(self, system_prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Send an image to the LLM with a text prompt and return the extracted text."""
        import base64

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{image_b64}"
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请提取这张图片中的招聘岗位描述文字，只返回提取的纯文本，不要添加任何额外说明。"},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "temperature": 0.15,
            "max_tokens": 4096,
        }
        req = self._build_request(body)
        result = await self._send(req, timeout=120, label="LLM vision request")
        return self._extract_content(result)

    def _build_request(self, body: dict) -> request.Request:
        data = json.dumps(body).encode("utf-8")
        return request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

    async def _send(self, req: request.Request, timeout: int, label: str) -> dict:
        try:
            return await asyncio.to_thread(self._send_sync, req, timeout)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
            raise LLMServiceError(f"{label} failed with HTTP {exc.code}: {detail[:500]}") from exc
        except URLError as exc:
            raise LLMServiceError(f"{label} failed: {exc}") from exc
        except TimeoutError as exc:
            raise LLMServiceError(f"{label} timed out") from exc
        except json.JSONDecodeError as exc:
            raise LLMServiceError(f"{label} returned invalid JSON") from exc

    def _send_sync(self, req: request.Request, timeout: int) -> dict:
        with request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _extract_content(self, result: dict) -> str:
        try:
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMServiceError("LLM response does not contain message content") from exc

    def _parse_json(self, content: str) -> dict:
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?", "", content).strip()
            content = re.sub(r"```$", "", content).strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMServiceError("LLM response is not valid JSON") from exc
