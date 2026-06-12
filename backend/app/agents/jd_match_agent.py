import re

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

分析规则：
1. 岗位 JD 是主要判断依据，请优先从 JD 中识别真实招聘岗位和核心要求。
2. 用户填写的目标岗位只是辅助参考；如果它和 JD 冲突，以 JD 为准。
3. 如果用户未填写目标岗位，请根据 JD 自动生成 target_role。

用户目标岗位（可选参考）：{payload.target_role or "未填写"}
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
            target_role=self._infer_target_role(payload),
        )

    def _infer_target_role(self, payload: AnalysisRequest) -> str:
        jd_text = payload.jd_text or ""
        role_patterns = [
            r"招聘岗位[:：\s]*([^\n，,。；;]{2,30})",
            r"岗位名称[:：\s]*([^\n，,。；;]{2,30})",
            r"职位名称[:：\s]*([^\n，,。；;]{2,30})",
            r"职位[:：\s]*([^\n，,。；;]{2,30})",
        ]
        for pattern in role_patterns:
            match = re.search(pattern, jd_text)
            if match:
                return match.group(1).strip()

        role_hints = [
            ("数据测试工程师", ["数据测试", "数据核对", "数据一致性", "数据库测试", "数据质量"]),
            ("软件测试工程师", ["测试用例", "缺陷", "测试报告", "功能测试"]),
            ("Python 后端开发工程师", ["Python", "FastAPI", "Django", "Flask", "接口开发"]),
            ("Java 后端开发工程师", ["Java", "Spring", "Spring Boot", "微服务"]),
            ("前端开发工程师", ["Vue", "React", "前端", "页面开发"]),
        ]
        for role, keywords in role_hints:
            if any(keyword.lower() in jd_text.lower() for keyword in keywords):
                return role

        return payload.target_role or "根据岗位 JD 自动识别"
