from app.schemas.analysis import MatchResult, ParsedResume, RewriteResult, ReviewResult
from app.services.llm_service import LLMService


class ResumeRewriteAgent:
    name = "ResumeRewriteAgent"
    role = "根据诊断结果生成更适合投递的简历表达"

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def run(self, parsed: ParsedResume, match: MatchResult, review: ReviewResult) -> RewriteResult:
        if self.llm.available:
            data = await self.llm.complete_json(
                "你是简历润色 Agent。只返回 JSON，不要 Markdown。",
                f"""
请生成一段更适合求职投递的简历表达，并给出面试亮点。返回：
{{"optimized_resume":"...", "interview_highlights":[...]}}

解析结果：{parsed.model_dump()}
匹配结果：{match.model_dump()}
诊断结果：{review.model_dump()}
""".strip(),
            )
            return RewriteResult(**data)
        keywords = "、".join(match.matched_keywords[:5] or parsed.skills[:5])
        return RewriteResult(
            optimized_resume=f"基于 {keywords} 等技术实现简历分析 Agent 平台，完成简历结构化解析、岗位 JD 匹配、问题诊断和内容润色等核心流程；通过多 Agent 编排将复杂分析任务拆分为解析、匹配、诊断、改写多个阶段，提升分析结果的可解释性和可维护性。",
            interview_highlights=[
                "能讲清楚为什么要拆分多 Agent，而不是只调用一次大模型。",
                "能说明结构化 JSON 输出如何让前后端稳定展示分析报告。",
                "能扩展 PDF/Word 解析、RAG 岗位知识库和模拟面试 Agent。",
            ],
        )
