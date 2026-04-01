import os
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "tvly-xxx")
USE_MOCK = not TAVILY_API_KEY or TAVILY_API_KEY == "tvly-xxx"

# Mock data: realistic-looking search results for common companies
MOCK_DATA = {
    "financial": {
        "美团": """
美团2023年全年营收2767亿元，同比增长25.8%。经营利润147亿元，较上年扭亏为盈。
核心本地商业分部营收2094亿元，经营利润389亿元，利润率18.6%。
新业务分部营收673亿元，经营亏损减窄至242亿元。
现金及等价物约741亿元，负债率健康。
市值约7500亿港元（2024年初）。
""",
        "default": """
该公司近三年营收保持稳定增长，年复合增长率约15%。
毛利率维持在35-45%区间，净利润率约8-12%。
资产负债率约45%，流动比率1.8，财务状况健康。
现金储备充足，支撑未来1-2年扩张计划。
"""
    },
    "news": {
        "美团": """
2024年Q1：美团宣布与OpenAI合作探索AI客服解决方案，计划将大模型应用于外卖配送调度优化。
2024年Q2：美团优选宣布在华东五省盈利，标志着社区团购业务进入收割期。
2024年Q3：美团在香港推出外卖服务Keeta，首月日均订单突破10万单。
监管：国家市监总局对平台骑手权益保障开展专项检查，美团配合整改。
""",
        "default": """
近期重大事件：公司宣布完成新一轮融资，估值较上轮提升30%。
产品端推出AI驱动的新功能，用户日活增长12%。
管理层变动：COO离职，由内部晋升接替。
监管方面暂无重大合规风险。
"""
    },
    "competitor": {
        "美团": """
主要竞争对手：
1. 饿了么（阿里巴巴旗下）：外卖市场份额约30%，近期在一线城市发力补贴战
2. 抖音团购：依托短视频流量，到店业务快速增长，2023年GMV超1500亿
3. 滴滴：跑腿业务与美团闪购存在竞争
4. 叮咚买菜/朴朴超市：即时零售赛道直接竞争
竞争格局：美团外卖市场份额约70%，护城河较深；到店业务受抖音冲击明显。
""",
        "default": """
行业TOP3竞争格局：
- 第一名（本公司）：市场份额约35%，品牌认知度最高
- 第二名：市场份额约28%，价格优势突出
- 第三名：市场份额约18%，专注细分市场
近期第二名加大研发投入，差距有收窄趋势。
"""
    },
    "sentiment": {
        "美团": """
分析师观点：
- 高盛：维持"买入"评级，目标价185港元，看好AI赋能降本增效
- 摩根士丹利：评级"增持"，认为海外扩张是新增长极
- 中金公司：目标价160港元，关注新业务亏损收窄节奏
社交媒体情绪：骑手权益话题持续发酵，消费者对配送时效满意度较高。
机构持仓：外资近3个月净买入，南向资金持续流入。
""",
        "default": """
市场情绪中性偏正面。
主流券商中，6家给予买入/增持评级，3家中性，1家卖出。
平均目标价较当前股价溢价约15%。
近期机构调研频繁，显示机构关注度上升。
"""
    },
    "risk": {
        "美团": """
主要风险：
1. 监管风险：平台经济反垄断监管持续，历史罚款34亿元，未来合规成本上升
2. 竞争风险：抖音持续加码本地生活，分流到店业务流量
3. 骑手成本：骑手社保政策落地将提升每单配送成本约0.5-1元
4. 海外扩张：香港、中东市场盈利周期较长，短期拖累整体利润
5. 宏观风险：消费降级趋势下客单价承压
""",
        "default": """
主要风险因素：
1. 宏观经济下行压力影响消费需求
2. 行业竞争加剧导致获客成本上升
3. 监管政策不确定性
4. 核心管理团队稳定性风险
5. 汇率波动风险（如有海外业务）
"""
    }
}


def _get_mock_data(company: str, search_type: str) -> list:
    """Return mock search results with realistic content."""
    data = MOCK_DATA.get(search_type, {})
    content = data.get(company, data.get("default", "暂无相关信息"))
    return [
        {
            "title": f"{company} {search_type} 分析",
            "url": f"https://example.com/{search_type}",
            "content": content.strip()
        }
    ]


async def search(query: str, search_type: str = "general", company: str = "") -> list:
    """
    Search for information. Uses mock data if TAVILY_API_KEY is not set.
    Returns list of {title, url, content} dicts.
    """
    if USE_MOCK:
        print(f"  [MOCK] Searching: {query}")
        return _get_mock_data(company or query, search_type)

    # Real Tavily search
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(query, max_results=5)
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")
            }
            for r in response.get("results", [])
        ]
    except Exception as e:
        print(f"  [ERROR] Tavily search failed: {e}")
        return []
