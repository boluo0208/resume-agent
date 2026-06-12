from app.agents.jd_match_agent import JDMatchAgent
from app.agents.resume_parser_agent import ResumeParserAgent
from app.agents.resume_rewrite_agent import ResumeRewriteAgent
from app.agents.resume_review_agent import ResumeReviewAgent
from app.schemas.analysis import AgentStep, AnalysisRequest, AnalysisResponse
from app.services.llm_service import LLMService, LLMServiceError


class ResumeAnalysisAgent:
    """Multi-agent orchestrator for resume analysis."""

    def __init__(self, llm: LLMService | None = None):
        self.llm = llm or LLMService()
        self.parser = ResumeParserAgent(self.llm)
        self.matcher = JDMatchAgent(self.llm)
        self.reviewer = ResumeReviewAgent(self.llm)
        self.rewriter = ResumeRewriteAgent(self.llm)

    async def run(self, payload: AnalysisRequest) -> AnalysisResponse:
        try:
            return await self._run_pipeline(payload)
        except LLMServiceError as exc:
            if not self.llm.available:
                raise
            fallback = ResumeAnalysisAgent(LLMService(api_key=""))
            response = await fallback._run_pipeline(payload)
            response.summary = f"LLM 调用失败，已自动切换为 mock 分析。{response.summary}"
            response.agent_steps.insert(0, AgentStep(
                name="LLMFallback",
                role="在模型服务不可用时保证分析流程可继续运行",
                status="completed",
                summary=str(exc),
                output={"fallback_mode": "mock"},
            ))
            return response

    async def _run_pipeline(self, payload: AnalysisRequest) -> AnalysisResponse:
        steps: list[AgentStep] = []

        parsed = await self.parser.run(payload)
        steps.append(AgentStep(
            name=self.parser.name,
            role=self.parser.role,
            summary=f"提取到 {len(parsed.skills)} 个技能关键词、{len(parsed.projects)} 条项目信息。",
            output=parsed.model_dump(),
        ))

        match = await self.matcher.run(payload, parsed)
        steps.append(AgentStep(
            name=self.matcher.name,
            role=self.matcher.role,
            summary=f"岗位匹配度 {match.match_score}%，命中 {len(match.matched_keywords)} 个关键词。",
            output=match.model_dump(),
        ))

        review = await self.reviewer.run(parsed, match)
        steps.append(AgentStep(
            name=self.reviewer.name,
            role=self.reviewer.role,
            summary=f"发现 {len(review.problems)} 个主要问题，生成 {len(review.suggestions)} 条优化建议。",
            output=review.model_dump(),
        ))

        rewrite = await self.rewriter.run(parsed, match, review)
        steps.append(AgentStep(
            name=self.rewriter.name,
            role=self.rewriter.role,
            summary="已生成投递导向的优化表达和面试亮点。",
            output=rewrite.model_dump(),
        ))

        score = self._score(match.match_score, review.problems, parsed.skills)
        return AnalysisResponse(
            mode="llm" if self.llm.available else "mock",
            model=self.llm.model if self.llm.available else None,
            score=score,
            summary=self._summary(score, match),
            strengths=review.strengths,
            problems=review.problems,
            suggestions=review.suggestions,
            optimized_resume=rewrite.optimized_resume,
            parsed_resume=parsed,
            match_result=match,
            interview_highlights=rewrite.interview_highlights,
            agent_steps=steps,
        )

    def _score(self, match_score: int, problems: list[str], skills: list[str]) -> int:
        score = match_score + min(len(skills) * 2, 8) - min(len(problems) * 3, 12)
        return max(35, min(score, 95))

    def _summary(self, score: int, match) -> str:
        if score >= 85:
            return f"简历与{match.target_role}匹配度较高，项目经历和技术关键词具备较好的投递基础。"
        if score >= 70:
            return f"简历具备一定基础，但需要围绕{match.target_role}补强成果表达和岗位关键词。"
        return f"简历当前与{match.target_role}匹配度一般，建议优先补充核心技能、项目难点和可量化成果。"
