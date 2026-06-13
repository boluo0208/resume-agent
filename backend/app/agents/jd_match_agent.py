from app.agents.resume_parser_agent import extract_keywords
from app.schemas.analysis import AnalysisRequest, JDProfile, MatchResult, ParsedResume
from app.services.llm_service import LLMService


class JDMatchAgent:
    name = "JDMatchAgent"
    role = "对比简历和结构化 JD，计算匹配点与缺失点"

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def run(self, payload: AnalysisRequest, parsed: ParsedResume, jd_profile: JDProfile) -> MatchResult:
        if self.llm.available:
            return await self._run_llm(payload, parsed, jd_profile)
        return self._run_mock(payload, parsed, jd_profile)

    async def _run_llm(self, payload: AnalysisRequest, parsed: ParsedResume, jd_profile: JDProfile) -> MatchResult:
        data = await self.llm.complete_json(
            "你是岗位匹配 Agent。只返回 JSON，不要 Markdown。",
            f"""
请基于结构化 JD 和结构化简历，计算匹配度。注意：

1. target_role 和 job_type 必须使用系统提供的 JDProfile 中的值，严禁根据简历改写。
2. matched_keywords：从 JD 的 keywords + must_have + nice_to_have 中，找出简历 skills/projects/work_experience/resume_text 中已体现的项。
3. missing_keywords：JD 要求但简历没有体现的项。
4. risk_items：从 JD 的 risk_items 中，挑出简历确实缺失的硬性风险项。
5. match_breakdown：分项打分，总和应接近 match_score：
   - 核心要求 (0-40)
   - 加分项 (0-20)
   - 项目相关性 (0-25)
   - 表达质量 (0-15)
6. match_score：综合评分 0-100，基于 breakdown 求和。
7. 不允许编造简历没有的经历。

返回 JSON：
{{
  "matched_keywords": [...],
  "missing_keywords": [...],
  "match_score": 0-100,
  "target_role": "{jd_profile.target_role}",
  "job_type": "{jd_profile.job_type}",
  "match_breakdown": {{"核心要求": 0-40, "加分项": 0-20, "项目相关性": 0-25, "表达质量": 0-15}},
  "risk_items": [...]
}}

识别岗位：{jd_profile.target_role}
岗位类型：{jd_profile.job_type}
JD 核心要求：{jd_profile.must_have}
JD 加分项：{jd_profile.nice_to_have}
JD 关键词：{jd_profile.keywords}
JD 风险项：{jd_profile.risk_items}
JD 职责：{jd_profile.responsibilities}

用户目标岗位（仅作求职方向参考）：{payload.target_role or "未填写"}
简历结构：{parsed.model_dump()}
简历原文（前 3000 字）：{payload.resume_text[:3000]}
""".strip(),
        )
        data["target_role"] = jd_profile.target_role
        data["job_type"] = jd_profile.job_type
        return MatchResult(**data)

    def _run_mock(self, payload: AnalysisRequest, parsed: ParsedResume, jd_profile: JDProfile) -> MatchResult:
        resume_text = payload.resume_text.lower()
        resume_words = set(
            word.lower() for word in
            parsed.skills + extract_keywords(payload.resume_text) +
            " ".join(parsed.projects).split() + " ".join(parsed.work_experience).split()
        )

        all_jd_terms = jd_profile.keywords + jd_profile.must_have + jd_profile.nice_to_have

        matched = []
        for term in all_jd_terms:
            term_lower = term.lower()
            if term_lower in resume_words or any(term_lower in w for w in resume_words) or any(w in term_lower for w in resume_words if len(w) > 3):
                matched.append(term)

        matched = list(dict.fromkeys(matched))[:12]
        missing = [term for term in all_jd_terms if term not in matched][:10]

        # Check risk items against resume
        risk_missing = []
        for risk in jd_profile.risk_items:
            risk_lower = risk.lower()
            # Extract key terms from risk item and check if resume covers them
            key_term = risk_lower.replace("学历要求：", "").replace("证书要求：", "").replace("语言要求：", "")
            key_term = key_term.split("经验")[0] + "经验" if "经验" in key_term else key_term
            if not any(term.strip() in resume_text for term in key_term.split("、") if len(term.strip()) > 1):
                risk_missing.append(risk)

        risk_missing = risk_missing[:5]

        # Calculate breakdown
        must_have_count = len(jd_profile.must_have)
        must_matched = sum(1 for mh in jd_profile.must_have if any(
            mh.lower() in w or w in mh.lower()
            for w in resume_words if len(w) > 2
        ))
        must_score = min(40, int((must_matched / max(must_have_count, 1)) * 40))

        nice_count = len(jd_profile.nice_to_have)
        nice_matched = sum(1 for nh in jd_profile.nice_to_have if any(
            nh.lower() in w or w in nh.lower()
            for w in resume_words if len(w) > 2
        ))
        nice_score = min(20, int((nice_matched / max(nice_count, 1)) * 20))

        project_score = min(25, len(parsed.projects) * 5 + len(parsed.work_experience) * 3)
        quality_score = min(15, 8 + min(len(parsed.skills) // 2, 7))

        breakdown = {
            "核心要求": must_score,
            "加分项": nice_score,
            "项目相关性": project_score,
            "表达质量": quality_score,
        }
        match_score = max(30, min(95, sum(breakdown.values())))

        return MatchResult(
            matched_keywords=matched or parsed.skills[:6],
            missing_keywords=missing or jd_profile.must_have[:5],
            match_score=match_score,
            target_role=jd_profile.target_role,
            job_type=jd_profile.job_type,
            match_breakdown=breakdown,
            risk_items=risk_missing,
        )
