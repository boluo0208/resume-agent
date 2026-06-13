from app.schemas.analysis import JDProfile, MatchResult, ParsedResume, ReviewResult
from app.services.llm_service import LLMService


class ResumeReviewAgent:
    name = "ResumeReviewAgent"
    role = "诊断简历表达质量，找出优势、问题和改进方向"

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def run(self, parsed: ParsedResume, match: MatchResult, jd_profile: JDProfile | None = None) -> ReviewResult:
        if self.llm.available:
            return await self._run_llm(parsed, match, jd_profile)
        return self._run_mock(parsed, match, jd_profile)

    async def _run_llm(self, parsed: ParsedResume, match: MatchResult, jd_profile: JDProfile | None) -> ReviewResult:
        jd_block = ""
        if jd_profile:
            jd_block = f"""
结构化 JD：
- 岗位：{jd_profile.target_role}（类型：{jd_profile.job_type}）
- 核心要求：{jd_profile.must_have}
- 加分项：{jd_profile.nice_to_have}
- 风险项：{jd_profile.risk_items}
- 职责：{jd_profile.responsibilities}
"""
        data = await self.llm.complete_json(
            "你是简历诊断 Agent。只返回 JSON，不要 Markdown。",
            f"""
请根据解析结果、匹配结果和 JD 结构诊断简历质量。注意：

1. 如果简历方向与 JD job_type 差异很大（如 AI/后端简历投 Amazon 运营），要明确指 "岗位方向不匹配"。
2. 区分"可迁移能力"（如数据分析、工具使用、流程优化、沟通协作）和"不可强行包装的经历"（如 Amazon 账户运营、Listing 编辑等实操经验）。
3. 对缺失的 risk_items 给出具体提示。
4. strengths：简历中与目标岗位相关的真实优势（3-5条）。
5. problems：需要指出的问题（3-6条），包括方向不匹配、缺失关键经验、表达不够量化等。
6. suggestions：可操作的改进建议（3-6条），区分可迁移包装和需要真补经验的。

返回 JSON：
{{"strengths":[...], "problems":[...], "suggestions":[...]}}

解析结果：{parsed.model_dump()}
匹配结果：{match.model_dump()}
{jd_block}
""".strip(),
        )
        return ReviewResult(**data)

    def _run_mock(self, parsed: ParsedResume, match: MatchResult, jd_profile: JDProfile | None) -> ReviewResult:
        job_type = (jd_profile.job_type or "") if jd_profile else ""
        target_role = (jd_profile.target_role or "") if jd_profile else ""

        # Base strengths/problems/suggestions
        strengths = [
            "项目经历覆盖后端、前端、数据库和 AI 模型接入，具备全栈开发潜力。",
            "简历中有完整系统项目，便于面试围绕技术架构和实现细节展开。",
            "目标岗位方向明确，可以围绕对应技术栈进一步强化表达。",
        ]
        problems = [
            "部分内容偏职责描述，缺少难点、解决方案和最终量化结果。",
            "岗位关键词与 JD 的对应关系还不够直接，需要增强命中率。",
            "项目成果缺少量化表达，例如接口数量、识别类别、部署方式、性能指标等。",
        ]
        suggestions = [
            "每段经历按照 技术栈 + 负责内容 + 难点 + 结果 的结构重写。",
            "优先突出与目标岗位匹配的关键词和技术栈。",
            "为每个项目准备 2-3 个可被面试官追问的技术细节。",
        ]

        # Direction mismatch detection
        resume_tech = set(w.lower() for w in parsed.skills)
        job_type_lower = job_type.lower()
        resume_direction = "tech"
        if any(t in resume_tech for t in ["python", "java", "fastapi", "vue", "react", "spring", "django", "mysql"]):
            resume_direction = "tech"

        misaligned = False
        if job_type_lower == "跨境电商运营" and resume_direction == "tech":
            misaligned = True
            problems = [
                f"⚠️ 岗位方向不匹配：简历方向偏技术开发（Python/Vue/AI），目标岗位是{target_role}（跨境电商运营），两个方向差异很大。",
                f"缺少 Amazon/跨境电商平台实操经验：Listing 编辑、广告投放、库存管理、账户绩效维护等。",
                "简历中的技术项目经历对于跨境电商运营岗位几乎没有直接加分。",
                "部分内容偏职责描述，缺少可量化的业务成果。",
            ]
            suggestions = [
                "如果确实想转跨境电商方向：建议补充 Amazon 运营相关知识（可参考 Amazon Seller Central 官方文档），学习 Listing 撰写、PPC 广告投放、FBA 库存管理。",
                "可迁移表达：数据分析能力、工具使用、流程优化意识、跨团队沟通协作 —— 这些是技术和运营都需要的。",
                "不可伪造：Amazon 账户运营经验、Listing 编辑、广告投放、库存管理、好评率维护等实操经验 —— 不要编造。",
                "如果要继续做技术方向，建议重新选择匹配的 JD 进行分析。",
            ]

        if job_type_lower == "数据测试" and resume_direction == "tech":
            if not any(t in resume_tech for t in ["sql", "mysql", "数据库", "oracle", "postgresql"]):
                misaligned = False  # may still be relevant
                problems.insert(0, "简历中缺少数据库/SQL 相关技能关键词，而数据测试岗位通常要求 SQL 熟练。")

        # Risk item warnings
        if jd_profile and jd_profile.risk_items:
            for risk in jd_profile.risk_items[:3]:
                if risk not in " ".join(problems):
                    problems.append(f"存在风险项：{risk}，简历中未充分体现。")

        return ReviewResult(
            strengths=strengths,
            problems=problems,
            suggestions=suggestions,
        )
