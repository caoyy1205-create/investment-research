import os
from datetime import datetime
from openai import AsyncOpenAI
from models.types import WorkerResult, ResearchReport, ReportSection

client = AsyncOpenAI(
    api_key=os.getenv("QWEN_API_KEY", "sk-placeholder"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

SECTION_MAP = {
    "FinancialWorker": "财务表现",
    "NewsWorker": "近期动态",
    "CompetitorWorker": "竞争格局",
    "SentimentWorker": "市场情绪",
    "RiskWorker": "风险提示",
    "MnAWorker": "并购分析",
    "LegalWorker": "法律风险",
    "MarketExpansionWorker": "市场扩张",
}


class Synthesizer:
    async def synthesize(self, company: str, results: list) -> ResearchReport:
        good = [r for r in results if r.quality_score >= 3]
        poor = [r for r in results if 0 < r.quality_score < 3]
        failed = [r for r in results if r.status in ("TIMEOUT", "ERROR", "INSUFFICIENT") or r.quality_score == 0]

        completeness = f"{len(good)}/{len(results)} 个维度高质量"
        warnings = []
        for r in poor:
            warnings.append(f"{r.worker_name}（质量分 {r.quality_score}/5）数据有限，结论仅供参考")
        for r in failed:
            warnings.append(f"{r.worker_name} 数据获取失败（{r.status}），该维度未纳入报告")

        # Build content summary for LLM
        content_parts = []
        for r in good + poor:
            section_title = SECTION_MAP.get(r.worker_name, r.worker_name)
            content_parts.append(
                f"=== {section_title}（来源：{r.worker_name}，质量分：{r.quality_score}/5）===\n{r.content}"
            )

        combined = "\n\n".join(content_parts)

        warning_note = ""
        if warnings:
            warning_note = "\n注意以下维度数据存在局限性：\n" + "\n".join(f"- {w}" for w in warnings)

        prompt = f"""你是一位资深投资研究分析师。请基于以下各维度的分析结果，为{company}撰写一份完整的投资研究报告。

{combined}

{warning_note}

请按以下结构撰写报告（Markdown格式）：

# 投资研究报告：{company}

**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}
**数据完整性**：{completeness}

---

## 1. 公司概况
（基于所有可用信息，概括公司基本情况）

## 2. 财务表现
（如有数据）

## 3. 近期动态
（如有数据）

## 4. 竞争格局
（如有数据）

## 5. 市场情绪
（如有数据，注明数据局限性）

## 6. 风险提示
（如有数据）

## 7. 综合结论
（基于以上分析，给出综合判断：公司亮点、主要风险、投资逻辑）

---

每个章节末尾用斜体注明数据来源，例如：*数据来源：FinancialWorker，质量分：4/5*

如某维度数据不足，在该章节末尾加⚠️标注并说明局限性。"""

        response = await client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "你是专业的投资研究分析师，善于整合多维度信息生成结构化研究报告。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=3000,
        )

        markdown = response.choices[0].message.content

        # Build sections for structured access
        sections = []
        for r in good + poor:
            section_title = SECTION_MAP.get(r.worker_name, r.worker_name)
            sections.append(ReportSection(
                title=section_title,
                content=r.content,
                worker_name=r.worker_name,
                quality_score=r.quality_score,
                has_warning=(r.quality_score < 3)
            ))

        return ResearchReport(
            company=company,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            data_completeness=completeness,
            sections=sections,
            warnings=warnings,
            raw_markdown=markdown
        )
