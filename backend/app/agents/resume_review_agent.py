from app.schemas.analysis import MatchResult, ParsedResume, ReviewResult
from app.services.llm_service import LLMService


class ResumeReviewAgent:
    name = "ResumeReviewAgent"
    role = "诊断简历表达质量，找出优势、问题和改进方向"

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def run(self, parsed: ParsedResume, match: MatchResult) -> ReviewResult:
        if self.llm.available:
            data = await self.llm.complete_json(
                "你是简历诊断 Agent。只返回 JSON，不要 Markdown。",
                f"""
请根据解析结果和岗位匹配结果诊断简历质量。返回：
{{"strengths":[...], "problems":[...], "suggestions":[...]}}

解析结果：{parsed.model_dump()}
匹配结果：{match.model_dump()}
""".strip(),
            )
            return ReviewResult(**data)
        return ReviewResult(
            strengths=[
                "项目经历覆盖后端、前端、数据库和 AI 模型接入，具备全栈开发潜力。",
                "简历中有完整系统项目，便于面试围绕技术架构和实现细节展开。",
                "目标岗位方向明确，可以围绕 Python/FastAPI/AI 应用进一步强化表达。",
            ],
            problems=[
                "部分内容偏职责描述，缺少难点、解决方案和最终结果。",
                "岗位关键词与 JD 的对应关系还不够直接，需要增强命中率。",
                "项目成果缺少量化表达，例如接口数量、识别类别、部署方式、性能指标等。",
            ],
            suggestions=[
                "每段经历按照 技术栈 + 负责内容 + 难点 + 结果 的结构重写。",
                "优先突出 FastAPI、Vue、MySQL、Docker、YOLO、Agent 编排等关键词。",
                "为每个项目准备 2-3 个可被面试官追问的技术细节。",
            ],
        )
