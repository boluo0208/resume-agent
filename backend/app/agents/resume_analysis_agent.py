import json

from app.agents.jd_match_agent import JDMatchAgent
from app.agents.jd_parser_agent import JDParserAgent
from app.agents.resume_parser_agent import ResumeParserAgent
from app.agents.resume_review_agent import ResumeReviewAgent
from app.agents.resume_rewrite_agent import ResumeRewriteAgent
from app.schemas.analysis import AgentStep, AnalysisRequest, AnalysisResponse
from app.services.llm_service import LLMService, LLMServiceError

# Agent display order for progress
AGENT_STEPS_INFO = [
    {"key": "JDParserAgent",      "name": "JDParserAgent",      "label": "解析岗位 JD，识别岗位类型与核心要求"},
    {"key": "ResumeParserAgent",  "name": "ResumeParserAgent",  "label": "解析简历，提取技能、项目与经历"},
    {"key": "JDMatchAgent",       "name": "JDMatchAgent",       "label": "计算岗位匹配度、命中项与缺口"},
    {"key": "ResumeReviewAgent",  "name": "ResumeReviewAgent",  "label": "诊断简历问题与投递风险"},
    {"key": "ResumeRewriteAgent", "name": "ResumeRewriteAgent", "label": "生成优化表达与面试亮点"},
]

TOTAL_STEPS = len(AGENT_STEPS_INFO)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


class ResumeAnalysisAgent:
    """Multi-agent orchestrator for resume analysis."""

    def __init__(self, llm: LLMService | None = None):
        self.llm = llm or LLMService()
        self.parser = ResumeParserAgent(self.llm)
        self.jd_parser = JDParserAgent(self.llm)
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
                summary=str(exc)[:200],
                output={"fallback_mode": "mock"},
            ))
            return response

    async def run_stream(self, payload: AnalysisRequest):
        """SSE streaming pipeline — yields progress events as each agent completes, then the result."""
        try:
            async for event in self._run_pipeline_stream(payload):
                yield event
        except LLMServiceError as exc:
            if not self.llm.available:
                yield _sse({"event": "error", "data": {"message": str(exc)}})
                return
            fallback = ResumeAnalysisAgent(LLMService(api_key=""))
            response = await fallback._run_pipeline(payload)
            response.summary = f"LLM 调用失败，已自动切换为 mock 分析。{response.summary}"
            yield _sse({"event": "result", "data": response.model_dump()})

    async def _run_pipeline_stream(self, payload: AnalysisRequest):
        steps: list[AgentStep] = []

        # Step 1: JDParserAgent
        yield _sse({"event": "step", "data": {"key": "JDParserAgent", "status": "running", "progress": 5}})
        jd_profile = await self.jd_parser.run(payload)
        jd_step = AgentStep(
            name=self.jd_parser.name,
            role=self.jd_parser.role,
            summary=(
                f"识别岗位为 {jd_profile.target_role}（{jd_profile.job_type}），"
                f"提取 {len(jd_profile.must_have)} 个核心要求、{len(jd_profile.nice_to_have)} 个加分项。"
            ),
            output=jd_profile.model_dump(),
        )
        steps.append(jd_step)
        yield _sse({"event": "step", "data": {"key": "JDParserAgent", "status": "completed", "progress": 18, "summary": jd_step.summary}})

        # Step 2: ResumeParserAgent
        yield _sse({"event": "step", "data": {"key": "ResumeParserAgent", "status": "running", "progress": 22}})
        parsed = await self.parser.run(payload)
        parser_step = AgentStep(
            name=self.parser.name,
            role=self.parser.role,
            summary=f"提取到 {len(parsed.skills)} 个技能关键词、{len(parsed.projects)} 条项目信息。",
            output=parsed.model_dump(),
        )
        steps.append(parser_step)
        yield _sse({"event": "step", "data": {"key": "ResumeParserAgent", "status": "completed", "progress": 38, "summary": parser_step.summary}})

        # Step 3: JDMatchAgent
        yield _sse({"event": "step", "data": {"key": "JDMatchAgent", "status": "running", "progress": 42}})
        match = await self.matcher.run(payload, parsed, jd_profile)
        match_step = AgentStep(
            name=self.matcher.name,
            role=self.matcher.role,
            summary=(
                f"岗位匹配度 {match.match_score}%，命中 {len(match.matched_keywords)} 个关键词，"
                f"缺失 {len(match.missing_keywords)} 个关键词。"
            ),
            output=match.model_dump(),
        )
        steps.append(match_step)
        yield _sse({"event": "step", "data": {"key": "JDMatchAgent", "status": "completed", "progress": 58, "summary": match_step.summary}})

        # Step 4: ResumeReviewAgent
        yield _sse({"event": "step", "data": {"key": "ResumeReviewAgent", "status": "running", "progress": 62}})
        review = await self.reviewer.run(parsed, match, jd_profile)
        review_step = AgentStep(
            name=self.reviewer.name,
            role=self.reviewer.role,
            summary=f"发现 {len(review.problems)} 个主要问题，生成 {len(review.suggestions)} 条优化建议。",
            output=review.model_dump(),
        )
        steps.append(review_step)
        yield _sse({"event": "step", "data": {"key": "ResumeReviewAgent", "status": "completed", "progress": 78, "summary": review_step.summary}})

        # Step 5: ResumeRewriteAgent
        yield _sse({"event": "step", "data": {"key": "ResumeRewriteAgent", "status": "running", "progress": 82}})
        rewrite = await self.rewriter.run(parsed, match, review, jd_profile)
        rewrite_step = AgentStep(
            name=self.rewriter.name,
            role=self.rewriter.role,
            summary="已生成投递导向的优化表达和面试亮点。",
            output=rewrite.model_dump(),
        )
        steps.append(rewrite_step)
        yield _sse({"event": "step", "data": {"key": "ResumeRewriteAgent", "status": "completed", "progress": 95, "summary": rewrite_step.summary}})

        score = self._score(match.match_score, review.problems, parsed.skills)
        response = AnalysisResponse(
            mode="llm" if self.llm.available else "mock",
            model=self.llm.model if self.llm.available else None,
            score=score,
            summary=self._summary(score, match),
            strengths=review.strengths,
            problems=review.problems,
            suggestions=review.suggestions,
            optimized_resume=rewrite.optimized_resume,
            parsed_resume=parsed,
            jd_profile=jd_profile,
            match_result=match,
            interview_highlights=rewrite.interview_highlights,
            agent_steps=steps,
        )
        yield _sse({"event": "result", "data": response.model_dump()})

    async def _run_pipeline(self, payload: AnalysisRequest) -> AnalysisResponse:
        steps: list[AgentStep] = []

        # Step 1: JDParserAgent
        jd_profile = await self.jd_parser.run(payload)
        steps.append(AgentStep(
            name=self.jd_parser.name,
            role=self.jd_parser.role,
            summary=(
                f"识别岗位为 {jd_profile.target_role}（{jd_profile.job_type}），"
                f"提取 {len(jd_profile.must_have)} 个核心要求、{len(jd_profile.nice_to_have)} 个加分项。"
            ),
            output=jd_profile.model_dump(),
        ))

        # Step 2: ResumeParserAgent
        parsed = await self.parser.run(payload)
        steps.append(AgentStep(
            name=self.parser.name,
            role=self.parser.role,
            summary=f"提取到 {len(parsed.skills)} 个技能关键词、{len(parsed.projects)} 条项目信息。",
            output=parsed.model_dump(),
        ))

        # Step 3: JDMatchAgent
        match = await self.matcher.run(payload, parsed, jd_profile)
        steps.append(AgentStep(
            name=self.matcher.name,
            role=self.matcher.role,
            summary=(
                f"岗位匹配度 {match.match_score}%，命中 {len(match.matched_keywords)} 个关键词，"
                f"缺失 {len(match.missing_keywords)} 个关键词。"
            ),
            output=match.model_dump(),
        ))

        # Step 4: ResumeReviewAgent
        review = await self.reviewer.run(parsed, match, jd_profile)
        steps.append(AgentStep(
            name=self.reviewer.name,
            role=self.reviewer.role,
            summary=f"发现 {len(review.problems)} 个主要问题，生成 {len(review.suggestions)} 条优化建议。",
            output=review.model_dump(),
        ))

        # Step 5: ResumeRewriteAgent
        rewrite = await self.rewriter.run(parsed, match, review, jd_profile)
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
            jd_profile=jd_profile,
            match_result=match,
            interview_highlights=rewrite.interview_highlights,
            agent_steps=steps,
        )

    def _score(self, match_score: int, problems: list[str], skills: list[str]) -> int:
        score = match_score + min(len(skills) * 2, 8) - min(len(problems) * 3, 12)
        return max(35, min(score, 95))

    def _summary(self, score: int, match) -> str:
        target_role = match.target_role
        if score >= 85:
            return f"简历与{target_role}匹配度较高，项目经历和技术关键词具备较好的投递基础。"
        if score >= 70:
            return f"简历具备一定基础，但需要围绕{target_role}补强成果表达和岗位关键词。"
        return f"简历当前与{target_role}匹配度一般，建议优先补充核心技能、项目难点和可量化成果。"
