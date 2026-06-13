import re
from collections import Counter

from app.schemas.analysis import AnalysisRequest, ParsedResume
from app.services.llm_service import LLMService


class ResumeParserAgent:
    name = "ResumeParserAgent"
    role = "将非结构化简历文本解析成结构化信息"

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def run(self, payload: AnalysisRequest) -> ParsedResume:
        if self.llm.available:
            data = await self.llm.complete_json(
                "你是简历解析 Agent。只返回 JSON，不要 Markdown。",
                f"""
请从简历文本中抽取结构化信息。返回格式：
{{"profile":"一句话概括", "skills":[...], "projects":[...], "work_experience":[...], "education":[...]}}

简历文本：
{payload.resume_text}
""".strip(),
            )
            return ParsedResume(**data)
        return self._mock(payload.resume_text)

    def _mock(self, resume_text: str) -> ParsedResume:
        keywords = [
            "Python", "FastAPI", "Vue", "Vue3", "MySQL", "PostgreSQL", "Docker",
            "YOLO", "SQLAlchemy", "Linux", "Java", "Agent", "AI", "Element Plus",
        ]
        skills = [word for word in keywords if word.lower() in resume_text.lower()]
        lines = [line.strip(" -•\t") for line in resume_text.splitlines() if line.strip()]
        project_lines = [line for line in lines if any(key in line for key in ["项目", "系统", "平台", "识别", "Agent"])]
        work_lines = [line for line in lines if any(key in line for key in ["负责", "参与", "独立", "维护", "开发"])]
        education = [line for line in lines if any(key in line for key in ["大学", "学院", "本科", "专科", "毕业"])]
        return ParsedResume(
            profile="候选人具备后端、前端、数据库和 AI 应用项目实践基础。",
            skills=skills or ["Python", "FastAPI", "Vue", "MySQL"],
            projects=project_lines[:5] or ["简历中包含可扩展的项目经历，但还需要进一步结构化表达。"],
            work_experience=work_lines[:5] or ["简历中暂未明显提取到工作职责，需要补充个人贡献。"],
            education=education[:3],
        )


def extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.]{1,}|[\u4e00-\u9fa5]{2,}", text)
    stopwords = {
        "岗位职责", "任职要求", "职位描述", "岗位要求", "工作职责",
        "负责", "要求", "熟悉", "掌握", "具备", "项目", "经验", "开发", "相关", "能力",
        "进行", "输出", "维护", "提升", "配合", "优先", "以上", "至少", "一种", "熟练掌握",
    }
    normalized = []
    for token in tokens:
        token = re.sub(r"^(负责|进行|设计|执行|编写|维护|输出|提升|配合|熟悉|熟练掌握|掌握|具备)", "", token)
        token = re.sub(r"(等|相关|优先)$", "", token)
        if token and token not in stopwords:
            normalized.append(token)
    counter = Counter(normalized)
    return [word for word, _ in counter.most_common(20)]
