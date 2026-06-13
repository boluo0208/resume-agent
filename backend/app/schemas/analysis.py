from typing import Any

from pydantic import BaseModel, Field, field_validator



def stringify_item(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = []
        for key in ["name", "company", "position", "role", "title", "description", "responsibility", "result"]:
            item = value.get(key)
            if item:
                if isinstance(item, list):
                    item = "?".join(str(x) for x in item)
                parts.append(str(item))
        if parts:
            return "?".join(parts)
        return "?".join(f"{k}: {v}" for k, v in value.items())
    if isinstance(value, list):
        return "?".join(stringify_item(item) for item in value)
    return str(value)


def stringify_list(value) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    return [stringify_item(item) for item in value if item is not None]


class AnalysisRequest(BaseModel):
    resume_text: str = Field(..., min_length=10, description="Resume text pasted by the user")
    jd_text: str | None = Field(default=None, description="Optional job description")
    target_role: str | None = Field(default=None, description="Optional target role")


class AgentStep(BaseModel):
    name: str
    role: str
    status: str = "completed"
    summary: str
    output: dict[str, Any]


class ParsedResume(BaseModel):
    profile: str
    skills: list[str]
    projects: list[str]
    work_experience: list[str]
    education: list[str]

    @field_validator("skills", "projects", "work_experience", "education", mode="before")
    @classmethod
    def coerce_string_lists(cls, value):
        return stringify_list(value)


class JDProfile(BaseModel):
    """Structured job description extracted by JDParserAgent."""
    target_role: str
    job_type: str = "其他"
    responsibilities: list[str] = []
    must_have: list[str] = []
    nice_to_have: list[str] = []
    keywords: list[str] = []
    risk_items: list[str] = []

    @field_validator("responsibilities", "must_have", "nice_to_have", "keywords", "risk_items", mode="before")
    @classmethod
    def coerce_jd_lists(cls, value):
        return stringify_list(value)

    @field_validator("target_role", mode="before")
    @classmethod
    def coerce_target_role(cls, value):
        return stringify_item(value)


class MatchResult(BaseModel):
    matched_keywords: list[str]
    missing_keywords: list[str]

    @field_validator("matched_keywords", "missing_keywords", mode="before")
    @classmethod
    def coerce_keyword_lists(cls, value):
        return stringify_list(value)
    match_score: int = Field(..., ge=0, le=100)
    target_role: str
    job_type: str | None = None
    match_breakdown: dict[str, int] = {}
    risk_items: list[str] = []

    @field_validator("risk_items", mode="before")
    @classmethod
    def coerce_risk_items(cls, value):
        return stringify_list(value)


class ReviewResult(BaseModel):
    strengths: list[str]
    problems: list[str]
    suggestions: list[str]

    @field_validator("strengths", "problems", "suggestions", mode="before")
    @classmethod
    def coerce_review_lists(cls, value):
        return stringify_list(value)


class RewriteResult(BaseModel):
    optimized_resume: str
    interview_highlights: list[str]

    @field_validator("interview_highlights", mode="before")
    @classmethod
    def coerce_highlights(cls, value):
        return stringify_list(value)

    @field_validator("optimized_resume", mode="before")
    @classmethod
    def coerce_resume_text(cls, value):
        return stringify_item(value)


class AnalysisResponse(BaseModel):
    mode: str = "mock"
    model: str | None = None
    score: int = Field(..., ge=0, le=100)
    summary: str
    strengths: list[str]
    problems: list[str]
    suggestions: list[str]
    optimized_resume: str
    parsed_resume: ParsedResume | None = None
    jd_profile: JDProfile | None = None
    match_result: MatchResult | None = None
    interview_highlights: list[str] = []
    agent_steps: list[AgentStep] = []
