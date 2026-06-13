import re
from collections import Counter

from app.agents.resume_parser_agent import extract_keywords
from app.schemas.analysis import AnalysisRequest, JDProfile
from app.services.llm_service import LLMService


class JDParserAgent:
    name = "JDParserAgent"
    role = "解析岗位 JD，识别岗位类型、核心要求和风险项"

    def __init__(self, llm: LLMService):
        self.llm = llm

    async def run(self, payload: AnalysisRequest) -> JDProfile:
        if self.llm.available:
            return await self._run_llm(payload)
        return self._run_mock(payload)

    async def _run_llm(self, payload: AnalysisRequest) -> JDProfile:
        jd_text = payload.jd_text or ""
        data = await self.llm.complete_json(
            "你是岗位 JD 解析 Agent。只根据岗位 JD 文本解析，不受简历内容影响。只返回 JSON，不要 Markdown。",
            f"""
请从以下岗位 JD 中提取结构化信息。注意：

1. 只根据 JD 文本解析，不要参考任何简历内容。
2. target_role 必须是中文岗位名，例如：
   - Amazon Operations Specialist → "亚马逊运营专员"
   - Data Testing Engineer → "数据测试工程师"
   - Software Test Engineer → "软件测试工程师"
   - Python Backend Developer → "Python 后端开发工程师"
   - Java Backend Developer → "Java 后端开发工程师"
   - Frontend Developer → "前端开发工程师"
   - AI Application Engineer → "AI应用工程师"
3. job_type 必须是以下之一：后端开发、前端开发、软件测试、数据测试、跨境电商运营、AI应用、其他
   - 如果 JD 涉及 Amazon、跨境电商、Listing、库存管理、广告投放、评价管理、账户运营，job_type 应为 "跨境电商运营"
   - 如果 JD 涉及数据核对、数据一致性、SQL 验证、数据库测试、数据质量，job_type 应为 "数据测试"
   - 如果 JD 涉及接口开发、API、微服务、后端框架（FastAPI/Django/Spring），job_type 应为 "后端开发"
4. responsibilities：提取岗位的核心职责（3-8条）
5. must_have：硬性要求，候选人必须满足的条件（3-8条）
6. nice_to_have：加分项，有更好但没有也可以（2-5条）
7. keywords：JD 中出现的核心技术/业务关键词（5-15个）
8. risk_items：如果简历中缺失会明显扣分的硬性要求，如：
   - 学历要求（"本科"、"硕士"、"计算机相关专业"）
   - 经验要求（"3年以上"、"有XX行业经验"）
   - 证书要求（"PMP"、"CPA"）
   - 特定平台经验（"Amazon 账户运营经验"、"银行系统测试经验"）

返回 JSON：
{{"target_role":"...", "job_type":"...", "responsibilities":[...], "must_have":[...], "nice_to_have":[...], "keywords":[...], "risk_items":[...]}}

岗位 JD：
{jd_text if jd_text.strip() else (payload.target_role or "未提供")}
""".strip(),
        )
        return JDProfile(**data)

    def _run_mock(self, payload: AnalysisRequest) -> JDProfile:
        jd_text = payload.jd_text or ""
        target_role, job_type = self._classify_role(jd_text, payload.target_role)
        raw_keywords = extract_keywords(jd_text)

        # Filter noise words and keep meaningful keywords
        noise = {"岗位职责", "任职要求", "职位描述", "岗位要求", "工作职责", "工作内容",
                 "进行", "输出", "维护", "提升", "配合", "优先", "以上", "至少", "一种",
                 "熟练掌握", "欢迎", "加入", "我们", "公司", "团队", "提供", "五险一金",
                 "薪资", "待遇", "福利", "地点", "地址", "联系", "方式", "邮箱", "电话"}
        keywords = [w for w in raw_keywords if w not in noise][:15]

        responsibilities = self._extract_responsibilities(jd_text, job_type)
        must_have, nice_to_have = self._extract_requirements(jd_text, job_type)
        risk_items = self._extract_risk_items(jd_text, target_role, job_type)

        return JDProfile(
            target_role=target_role,
            job_type=job_type,
            responsibilities=responsibilities,
            must_have=must_have,
            nice_to_have=nice_to_have,
            keywords=keywords,
            risk_items=risk_items,
        )

    # ===== Role classification =====

    def _classify_role(self, jd_text: str, fallback_role: str | None) -> tuple[str, str]:
        text = jd_text.lower()
        role_hints = [
            # (target_role, job_type, [keywords])
            ("亚马逊运营专员", "跨境电商运营",
             ["amazon operations specialist", "amazon operation specialist",
              "amazon运营", "亚马逊运营", "amazon seller", "amazon account",
              "listing", "账户运营", "好评率", "fba", "fbm", "ppc广告",
              "欧洲站", "北美站", "日本站", "asin", "sku"]),
            ("跨境电商运营", "跨境电商运营",
             ["跨境电商", "店铺运营", "平台运营", "电商运营", "海外店铺",
              "listing优化", "库存管理", "广告投放", "跨境物流",
              "shopee", "lazada", "wish", "ebay", "aliexpress"]),
            ("数据测试工程师", "数据测试",
             ["数据测试", "数据核对", "数据一致性", "数据库测试", "数据质量",
              "data testing", "data validation", "data quality", "etl测试",
              "数据验证", "数据比对", "数据迁移测试"]),
            ("软件测试工程师", "软件测试",
             ["测试用例", "test case", "bug", "缺陷管理", "回归测试",
              "功能测试", "性能测试", "自动化测试", "接口测试",
              "qa engineer", "test engineer", "软件测试"]),
            ("Python 后端开发工程师", "后端开发",
             ["python", "fastapi", "django", "flask", "后端开发",
              "api开发", "接口开发", "python后端"]),
            ("Java 后端开发工程师", "后端开发",
             ["java", "spring boot", "spring cloud", "微服务",
              "mybatis", "java后端", "jvm"]),
            ("前端开发工程师", "前端开发",
             ["vue", "react", "angular", "前端开发", "页面开发",
              "web前端", "h5", "css", "javascript", "typescript"]),
            ("AI应用工程师", "AI应用",
             ["ai应用", "llm", "agent", "rag", "大模型", "机器学习",
              "深度学习", "自然语言处理", "计算机视觉", "prompt"]),
            ("运营专员", "跨境电商运营",
             ["operations specialist", "operation specialist",
              "账号运营", "账户运营", "日常运营", "销售分析",
              "广告投放", "促销活动"]),
        ]
        for role, jtype, hints in role_hints:
            if any(hint in text for hint in hints):
                return role, jtype

        # Try regex for explicit role patterns
        patterns = [
            r"招聘岗位[:：\s]*([^\n，,。；;]{2,30})",
            r"岗位名称[:：\s]*([^\n，,。；;]{2,30})",
            r"职位名称[:：\s]*([^\n，,。；;]{2,30})",
            r"职位[:：\s]*([^\n，,。；;]{2,30})",
            r"position[:：\s]*([^\n，,。；;]{2,50})",
            r"job title[:：\s]*([^\n，,。；;]{2,50})",
        ]
        for pattern in patterns:
            match = re.search(pattern, jd_text)
            if match:
                extracted = match.group(1).strip()
                if re.search(r"[一-鿿]", extracted):
                    return extracted, "其他"
                # English role -> translate
                role_lower = extracted.lower()
                if "amazon" in role_lower or "operation" in role_lower:
                    return "亚马逊运营专员", "跨境电商运营"
                if "test" in role_lower or "qa" in role_lower:
                    if "data" in role_lower:
                        return "数据测试工程师", "数据测试"
                    return "软件测试工程师", "软件测试"
                if "python" in role_lower or "backend" in role_lower:
                    return "Python 后端开发工程师", "后端开发"
                if "java" in role_lower:
                    return "Java 后端开发工程师", "后端开发"
                if "frontend" in role_lower or "front-end" in role_lower:
                    return "前端开发工程师", "前端开发"
                if "ai" in role_lower or "ml" in role_lower or "agent" in role_lower:
                    return "AI应用工程师", "AI应用"
                return extracted, "其他"

        if fallback_role and (not jd_text.strip()):
            return fallback_role, "其他"

        return "岗位待确认", "其他"

    # ===== Responsibility extraction =====

    def _extract_responsibilities(self, jd_text: str, job_type: str) -> list[str]:
        lines = [line.strip(" -•·\t\r") for line in jd_text.splitlines()]
        lines = [line for line in lines if line and len(line) > 4]
        if not lines:
            return []

        duty_markers = [
            "岗位职责", "工作职责", "工作内容", "职责描述", "responsibilities",
            "你需要做什么", "你要做什么", "职位描述", "role description",
        ]
        in_section = False
        duties: list[str] = []

        for line in lines:
            lower_line = line.lower()
            if any(marker in lower_line for marker in duty_markers):
                in_section = True
                continue
            if in_section:
                if any(marker in lower_line for marker in
                       ["任职要求", "岗位要求", "要求", "qualification", "requirements",
                        "加分项", "优先", "我们希望你", "福利", "关于我们", "公司介绍"]):
                    in_section = False
                    continue
                # Clean numbered prefixes
                cleaned = re.sub(r"^[\d]+[\.、)）\s]+", "", line)
                if len(cleaned) > 4:
                    duties.append(cleaned)

        if not duties:
            duties = [line for line in lines if
                      any(verb in line for verb in
                          ["负责", "参与", "独立", "设计", "开发", "维护", "编写", "管理",
                           "优化", "测试", "分析", "协调", "跟进", "输出"])
                      and len(line) < 120]

        return duties[:8] if duties else ["根据 JD 自动提取的岗位职责"]

    # ===== Requirement extraction =====

    def _extract_requirements(self, jd_text: str, job_type: str) -> tuple[list[str], list[str]]:
        lines = [line.strip(" -•·\t\r") for line in jd_text.splitlines()]
        lines = [line for line in lines if line and len(line) > 3]

        req_markers = [
            "任职要求", "岗位要求", "资格要求", "qualification", "requirements",
            "你需要具备", "我们希望你", "基本要求", "硬性要求",
        ]
        nice_markers = [
            "加分项", "优先", "nice to have", "bonus", "preferred",
            "有以下经验优先", "特别加分",
        ]

        must_have: list[str] = []
        nice_to_have: list[str] = []
        current_section: str | None = None

        for line in lines:
            lower_line = line.lower()
            if any(marker in lower_line for marker in req_markers):
                current_section = "must"
                continue
            if any(marker in lower_line for marker in nice_markers):
                current_section = "nice"
                continue
            if current_section and any(marker in lower_line for marker in
                                        ["岗位职责", "工作内容", "福利", "关于我们"]):
                current_section = None
                continue

            if current_section:
                cleaned = re.sub(r"^[\d]+[\.、)）\s]+", "", line)
                if current_section == "must":
                    if len(cleaned) > 3:
                        must_have.append(cleaned)
                else:
                    if len(cleaned) > 3:
                        nice_to_have.append(cleaned)

        return must_have[:8] or ["根据 JD 提取的核心要求"], nice_to_have[:5]

    # ===== Risk items =====

    def _extract_risk_items(self, jd_text: str, target_role: str, job_type: str) -> list[str]:
        risks: list[str] = []

        # Education
        edu_match = re.search(
            r"(本科|硕士|博士|大专|计算机相关专业|软件工程|电子信息|数学|统计|金融|会计)",
            jd_text
        )
        if edu_match:
            edu = edu_match.group(1)
            risks.append(f"学历要求：{edu}")

        # Experience years
        exp_match = re.search(r"(\d+)[\s\-]*年(以上|经验|相关经验|工作经验|行业经验)", jd_text)
        if exp_match:
            risks.append(f"{exp_match.group(1)}年以上相关工作经验")

        # Industry experience
        industry_hints = {
            "银行": "银行系统测试经验",
            "金融": "金融行业经验",
            "电商": "电商行业经验",
            "amazon": "Amazon 平台运营经验",
            "亚马逊": "亚马逊平台运营经验",
            "跨境电商": "跨境电商经验",
            "游戏": "游戏行业经验",
            "医疗": "医疗行业经验",
        }
        for hint, desc in industry_hints.items():
            if hint.lower() in jd_text.lower() and desc not in risks:
                if "经验" in desc:
                    risks.append(desc)

        # Certificates
        cert_hints = {
            "pmp": "PMP 证书",
            "cpa": "CPA 证书",
            "cfa": "CFA 证书",
            "acca": "ACCA 证书",
        }
        for hint, desc in cert_hints.items():
            if hint in jd_text.lower():
                risks.append(f"证书要求：{desc}")

        # Language requirements
        lang_match = re.search(r"(英语|日语|韩语|德语|法语)\s*([四六]级|专业[四八]级|[A-C]ET[- ]?\d|N\d|TOPIK)", jd_text)
        if lang_match:
            risks.append(f"语言要求：{lang_match.group(0)}")

        # Platform-specific experience
        platform_hints = {
            "amazon": "Amazon 账户运营实操经验",
            "aws": "AWS 平台实操经验",
            "azure": "Azure 平台实操经验",
            "alibaba": "阿里巴巴平台经验",
            "listing": "Listing 编辑和优化经验",
            "广告投放": "广告投放实操经验",
            "库存管理": "库存管理经验",
        }
        for hint, desc in platform_hints.items():
            if hint in jd_text.lower() and desc not in risks:
                risks.append(desc)

        return risks[:6]
