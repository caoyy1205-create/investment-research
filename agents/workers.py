import os
import json
from openai import AsyncOpenAI
from models.types import WorkerResult
from tools.search import search


def get_client():
    return AsyncOpenAI(
        api_key=os.getenv("QWEN_API_KEY", "sk-placeholder"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )


def is_chinese(text: str) -> bool:
    return any('\u4e00' <= c <= '\u9fff' for c in text)


class BaseWorker:
    name = "BaseWorker"
    search_type = "general"

    def get_search_query(self, company: str) -> str:
        raise NotImplementedError

    def get_analysis_prompt(self, company: str, search_results: str) -> str:
        raise NotImplementedError

    async def run(self, company: str) -> WorkerResult:
        try:
            query = self.get_search_query(company)
            results = await search(query, self.search_type, company)
            search_text = "\n\n".join(
                f"[{r['title']}]\n{r['content']}" for r in results
            )
            sources = [r["url"] for r in results if r.get("url")]

            prompt = self.get_analysis_prompt(company, search_text)
            client = get_client()
            response = await client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "你是一位专业的投资研究分析师，擅长对公司进行深度分析。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            content = response.choices[0].message.content

            return WorkerResult(
                worker_name=self.name,
                status="SUCCESS",
                content=content,
                sources=sources
            )
        except Exception as e:
            print(f"  [ERROR] {self.name} failed: {type(e).__name__}: {e}")
            return WorkerResult(
                worker_name=self.name,
                status="ERROR",
                content=f"Worker执行失败: {str(e)}"
            )


class FinancialWorker(BaseWorker):
    name = "FinancialWorker"
    search_type = "financial"

    def get_search_query(self, company: str) -> str:
        if is_chinese(company):
            return f"{company} 财务数据 营收 利润 2023 2024"
        return f"{company} financial results revenue profit 2023 2024"

    def get_analysis_prompt(self, company: str, search_results: str) -> str:
        return f"""基于以下搜索结果，对{company}的财务状况进行结构化分析：

{search_results}

请分析：
1. 营收规模及增长趋势
2. 盈利能力（毛利率、净利率）
3. 资产负债状况
4. 现金流情况
5. 估值水平（如有数据）

用简洁的要点格式输出，重点突出关键财务指标。"""


class NewsWorker(BaseWorker):
    name = "NewsWorker"
    search_type = "news"

    def get_search_query(self, company: str) -> str:
        if is_chinese(company):
            return f"{company} 最新动态 新闻 2024"
        return f"{company} latest news events 2024"

    def get_analysis_prompt(self, company: str, search_results: str) -> str:
        return f"""基于以下搜索结果，总结{company}的近期重大事件和动态：

{search_results}

请分析：
1. 近3-6个月重大新闻事件（按时间倒序）
2. 业务拓展或收缩动向
3. 管理层变动
4. 监管/政策相关事项
5. 市场反应

突出影响公司价值的关键事件。"""


class CompetitorWorker(BaseWorker):
    name = "CompetitorWorker"
    search_type = "competitor"

    def get_search_query(self, company: str) -> str:
        if is_chinese(company):
            return f"{company} 竞争对手 市场份额 竞争格局"
        return f"{company} competitors market share competitive landscape"

    def get_analysis_prompt(self, company: str, search_results: str) -> str:
        return f"""基于以下搜索结果，分析{company}的竞争格局：

{search_results}

请分析：
1. 主要竞争对手列表及各自市场份额
2. 竞争优势与劣势对比
3. 近期竞争动态变化
4. 行业整体竞争烈度评估
5. 公司的护城河分析

用对比格式呈现，突出关键竞争要素。"""


class SentimentWorker(BaseWorker):
    name = "SentimentWorker"
    search_type = "sentiment"

    def get_search_query(self, company: str) -> str:
        if is_chinese(company):
            return f"{company} 分析师评级 机构观点 股价目标价"
        return f"{company} analyst rating target price institutional view"

    def get_analysis_prompt(self, company: str, search_results: str) -> str:
        return f"""基于以下搜索结果，分析{company}的市场情绪和机构观点：

{search_results}

请分析：
1. 主流券商/机构评级汇总（买入/中性/卖出比例）
2. 目标价区间及平均目标价
3. 机构持仓变化趋势
4. 市场整体情绪（乐观/中性/悲观）
5. 值得关注的少数派观点

客观呈现多方观点，不做个人判断。"""


class RiskWorker(BaseWorker):
    name = "RiskWorker"
    search_type = "risk"

    def get_search_query(self, company: str) -> str:
        if is_chinese(company):
            return f"{company} 风险 监管 政策 挑战"
        return f"{company} risks regulatory policy challenges"

    def get_analysis_prompt(self, company: str, search_results: str) -> str:
        return f"""基于以下搜索结果，识别{company}面临的主要风险：

{search_results}

请分析：
1. 监管与政策风险
2. 竞争与市场风险
3. 运营与执行风险
4. 宏观经济风险
5. 公司特有风险

按风险程度（高/中/低）标注，并说明潜在影响。"""


# Extra workers for dynamic dispatch
class MnAWorker(BaseWorker):
    name = "MnAWorker"
    search_type = "news"

    def get_search_query(self, company: str) -> str:
        if is_chinese(company):
            return f"{company} 并购 收购 合并 战略投资"
        return f"{company} merger acquisition M&A strategic investment"

    def get_analysis_prompt(self, company: str, search_results: str) -> str:
        return f"""基于以下搜索结果，深度分析{company}的并购/收购动态：

{search_results}

请分析：
1. 近期并购/被收购事件详情
2. 交易金额及战略意图
3. 对公司业务版图的影响
4. 市场反应及分析师解读
5. 后续整合进展"""


class LegalWorker(BaseWorker):
    name = "LegalWorker"
    search_type = "risk"

    def get_search_query(self, company: str) -> str:
        if is_chinese(company):
            return f"{company} 诉讼 法律纠纷 监管处罚"
        return f"{company} lawsuit legal dispute regulatory penalty"

    def get_analysis_prompt(self, company: str, search_results: str) -> str:
        return f"""基于以下搜索结果，分析{company}的法律风险：

{search_results}

请分析：
1. 重大诉讼案件列表及进展
2. 监管调查或处罚情况
3. 潜在财务影响估算
4. 公司应对措施"""


class MarketExpansionWorker(BaseWorker):
    name = "MarketExpansionWorker"
    search_type = "news"

    def get_search_query(self, company: str) -> str:
        if is_chinese(company):
            return f"{company} 新市场 海外扩张 新业务 战略布局"
        return f"{company} new market expansion international strategy"

    def get_analysis_prompt(self, company: str, search_results: str) -> str:
        return f"""基于以下搜索结果，分析{company}的市场扩张战略：

{search_results}

请分析：
1. 新进入的市场或地区
2. 扩张规模及投入
3. 当地竞争格局
4. 盈利预期时间线
5. 扩张风险评估"""


EXTRA_WORKER_MAP = {
    "MnAWorker": MnAWorker,
    "LegalWorker": LegalWorker,
    "MarketExpansionWorker": MarketExpansionWorker,
}
