from app.agents.resume_parser_agent import extract_keywords
from app.schemas.analysis import AnalysisRequest, MatchResult, ParsedResume
from app.services.llm_service import LLMService


class JDMatchAgent:
    name = "JDMatchAgent"
    role = "对比简历和岗位 JD，计算匹配点与缺失点"

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def run(self, payload: AnalysisRequest, parsed: ParsedResume) -> MatchResult:
        if self.llm.available:
            data = await self.llm.complete_json(
                "你是岗位匹配 Agent。只返回 JSON，不要 Markdown。",
                f"""
请对比简历结构化信息和岗位 JD，返回：
{{"matched_keywords":[...], "missing_keywords":[...], "match_score":0-100, "target_role":"..."}}

目标岗位：{payload.target_role or "未指定"}
简历结构：{parsed.model_dump()}
岗位 JD：{payload.jd_text or "未提供"}
""".strip(),
            )
            return MatchResult(**data)
        return self._mock(payload, parsed)

    def _mock(self, payload: AnalysisRequest, parsed: ParsedResume) -> MatchResult:
        resume_words = set(word.lower() for word in parsed.skills + extract_keywords(payload.resume_text))
        jd_keywords = extract_keywords(payload.jd_text or payload.target_role or "Python FastAPI Vue MySQL")
        matched = [word for word in jd_keywords if word.lower() in resume_words or word in parsed.skills]
        missing = [word for word in jd_keywords if word not in matched][:8]
        base = 55 + min(len(matched) * 6, 35) - min(len(missing) * 2, 15)
        return MatchResult(
            matched_keywords=matched[:10] or parsed.skills[:6],
            missing_keywords=missing or ["量化成果", "岗位关键词", "业务指标"],
            match_score=max(45, min(base, 92)),
            target_role=payload.target_role or "目标岗位未指定",
        )
