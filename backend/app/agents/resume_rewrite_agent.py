from app.schemas.analysis import JDProfile, MatchResult, ParsedResume, RewriteResult, ReviewResult
from app.services.llm_service import LLMService


class ResumeRewriteAgent:
    name = "ResumeRewriteAgent"
    role = "根据诊断结果生成更适合投递的简历表达"

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def run(self, parsed: ParsedResume, match: MatchResult, review: ReviewResult, jd_profile: JDProfile | None = None) -> RewriteResult:
        if self.llm.available:
            return await self._run_llm(parsed, match, review, jd_profile)
        return self._run_mock(parsed, match, review, jd_profile)

    async def _run_llm(self, parsed: ParsedResume, match: MatchResult, review: ReviewResult, jd_profile: JDProfile | None) -> RewriteResult:
        jd_block = ""
        if jd_profile:
            jd_block = f"""
结构化 JD：
- 岗位：{jd_profile.target_role}（类型：{jd_profile.job_type}）
- 核心要求：{jd_profile.must_have}
- 加分项：{jd_profile.nice_to_have}
- 职责：{jd_profile.responsibilities}
"""
        data = await self.llm.complete_json(
            "你是简历润色 Agent。只返回 JSON，不要 Markdown。",
            f"""
请生成一段更适合求职投递的简历表达，并给出面试亮点。注意：

1. 不要胡编用户没有的经历。只能基于简历中已有的经验进行表达优化。
2. 如果简历方向和 JD 方向差异很大（如 AI/后端简历投 Amazon 运营）：
   - optimized_resume 应区分"可迁移表达"（数据分析、工具使用、流程优化、沟通协作）和"不可伪造"（Amazon 账户运营、Listing 编辑、广告投放等）。
   - 不可编造跨境电商实操经验。
3. 面试亮点应该是简历中真实经历的可发挥方向。

返回 JSON：
{{"optimized_resume":"...", "interview_highlights":[...]}}

解析结果：{parsed.model_dump()}
匹配结果：{match.model_dump()}
诊断结果：{review.model_dump()}
{jd_block}
""".strip(),
        )
        return RewriteResult(**data)

    def _run_mock(self, parsed: ParsedResume, match: MatchResult, review: ReviewResult, jd_profile: JDProfile | None) -> RewriteResult:
        keywords = "、".join(match.matched_keywords[:5] or parsed.skills[:5])
        target_role = match.target_role
        job_type = (jd_profile.job_type or "") if jd_profile else ""

        # Cross-domain case
        resume_tech = set(w.lower() for w in parsed.skills)
        is_tech = any(t in resume_tech for t in ["python", "java", "fastapi", "vue", "react", "ai", "agent"])
        is_ecommerce = job_type == "跨境电商运营"

        if is_tech and is_ecommerce:
            optimized = (
                f"目标岗位 {target_role} 与当前简历技术方向（{keywords}）差异较大。"
                f"\n\n可迁移表达："
                f"\n• 数据分析能力：使用 Python/SQL 进行数据处理和统计分析，可为 Amazon 销售数据分析和决策提供基础。"
                f"\n• 工具使用与学习能力：快速掌握了 FastAPI、Vue、Docker 等工具链，说明具备快速学习新平台（如 Amazon Seller Central）的能力。"
                f"\n• 流程优化意识：在项目开发中涉及需求分析→架构设计→部署上线的全流程，可迁移到运营流程的 SOP 化和自动化。"
                f"\n• 跨团队沟通协作：技术项目开发需要与多方协调，可迁移到与供应链、物流、广告团队的协作中。"
                f"\n\n不可伪造（需真实经验积累）："
                f"\n• Amazon 账户运营、Listing 编辑和优化、PPC 广告投放、FBA/FBM 库存管理、账户绩效维护、好评率管理"
                f"\n\n若确实想转跨境电商方向，建议先从 Amazon 运营助理入手积累实操经验。"
            )
            highlights = [
                "数据分析能力：可强调 Python/SQL 在销售数据分析中的应用思路。",
                "快速学习能力：讲解如何快速上手新技术和新平台。",
                "流程化思维：展示从开发中学到的流程设计和自动化意识。",
                "⚠️ 面试官很可能追问：'你有 Amazon 实操经验吗？' 建议如实回答并展示学习能力。",
            ]
        else:
            optimized = (
                f"基于 {keywords} 等技术实现简历分析 Agent 平台，"
                f"完成简历结构化解析、岗位 JD 匹配、问题诊断和内容润色等核心流程；"
                f"通过多 Agent 编排将复杂分析任务拆分为解析、匹配、诊断、改写多个阶段，"
                f"提升分析结果的可解释性和可维护性。"
            )
            highlights = [
                "能讲清楚为什么要拆分多 Agent，而不是只调用一次大模型。",
                "能说明结构化 JSON 输出如何让前后端稳定展示分析报告。",
                "能扩展 PDF/Word 解析、RAG 岗位知识库和模拟面试 Agent。",
            ]

        return RewriteResult(
            optimized_resume=optimized,
            interview_highlights=highlights,
        )
