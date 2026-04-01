# AI 投资研究助手 — 系统设计 Spec

**日期**：2026-04-01  
**状态**：草稿，待 review

---

## 1. 目标

输入一个公司名，输出一份结构化投资研究报告。

核心学习目标：通过真实项目掌握 Multi-Agent 主从架构的三个核心挑战：
1. 并发控制 + 容错
2. 质量评估 + 动态过滤
3. Supervisor 动态派发额外 Worker

---

## 2. 系统架构

```
用户输入（公司名）
        ↓
  Supervisor Agent
  │
  ├── 阶段1：规划
  │     分析公司名，决定初始 Worker 列表和搜索策略
  │
  ├── 阶段2：并行执行
  │     asyncio.gather 同时跑以下 Worker：
  │     ├── FinancialWorker   财务数据（营收/利润/估值）
  │     ├── NewsWorker        近期重大新闻和事件
  │     ├── CompetitorWorker  主要竞争对手分析
  │     ├── SentimentWorker   市场情绪/分析师观点
  │     └── RiskWorker        行业风险和政策风险
  │
  ├── 阶段3：质量评估
  │     Supervisor 逐个审核 Worker 结果：
  │     - 打分 1-5（信息密度 + 可信度 + 完整性）
  │     - 分数 ≥ 3：通过，进入合成
  │     - 分数 1-2：触发重试（换搜索词重跑，最多1次）
  │     - 重试后仍不合格：标记 INSUFFICIENT，报告中注明
  │     - Worker 超时（>30s）：标记 TIMEOUT，降级处理
  │     - Worker 异常：标记 ERROR，记录原因
  │
  ├── 阶段4：动态补充（Supervisor 二次决策）
  │     根据第一轮结果，Supervisor 判断是否需要额外 Worker：
  │     - 财务数据严重不足 → 派 AlternativeFinanceWorker
  │     - 发现重大并购/诉讼 → 派专项 Worker（MnAWorker / LegalWorker）
  │     - 发现进入新市场   → 派 NewMarketWorker
  │     - 整体质量均分 < 2  → 直接返回"信息不足"错误
  │
  └── 阶段5：合成
        SynthesizerAgent 整合所有通过质量评估的结果，
        生成最终 Markdown 报告
```

---

## 3. 模块设计

### 3.1 数据结构

```python
@dataclass
class WorkerResult:
    worker_name: str          # e.g. "FinancialWorker"
    status: str               # SUCCESS | TIMEOUT | ERROR | INSUFFICIENT
    content: str              # 原始搜索+分析内容
    quality_score: int        # 1-5，Supervisor 打分
    quality_reason: str       # 打分理由
    sources: list[str]        # 来源 URL 列表
    retry_count: int          # 重试次数

@dataclass  
class ResearchReport:
    company: str
    generated_at: str
    data_completeness: str    # e.g. "4/5 维度高质量"
    sections: list[ReportSection]
    warnings: list[str]       # 数据不足的维度警告
```

### 3.2 Supervisor Agent

职责：规划 → 调度 → 质量评估 → 动态派发 → 触发合成

关键方法：
- `plan(company)` → 返回初始 Worker 列表
- `evaluate_worker(result)` → 调用 LLM 打质量分，返回 WorkerResult（带 score）
- `decide_extra_workers(results)` → 分析第一轮结果，返回需要额外派发的 Worker 列表
- `run(company)` → 主调度循环

### 3.3 Worker Agent（基类 + 5个子类）

每个 Worker：
- 接收搜索任务描述
- 用 Tavily 搜索相关信息
- 用 Qwen 对搜索结果做结构化分析
- 返回 WorkerResult（status=SUCCESS/ERROR）

超时控制：每个 Worker 用 `asyncio.wait_for(worker.run(), timeout=30)` 包裹

### 3.4 Synthesizer Agent

输入：所有通过质量评估的 WorkerResult 列表  
输出：完整 Markdown 格式投资研究报告

---

## 4. 报告格式

```markdown
# 投资研究报告：{公司名}

**生成时间**：{datetime}  
**数据完整性**：{N}/5 个维度高质量

---

## 1. 公司概况
{内容}（来源：FinancialWorker，质量分：4/5）

## 2. 财务表现
{内容}

## 3. 近期动态
{内容}

## 4. 竞争格局
{内容}

## 5. 市场情绪
{内容} ⚠️（数据有限，质量分：2/5）

## 6. 风险提示
{内容}

## 7. 综合结论
{内容}

---
⚠️ 警告：以下维度数据不足，结论仅供参考：{维度列表}
```

---

## 5. 技术栈

| 组件 | 选型 |
|---|---|
| 语言 | Python 3.11+ |
| 并发 | asyncio |
| LLM | Qwen API（qwen-plus） |
| 搜索 | Tavily Search API |
| 输出 | Markdown 文件 + 简单 Web UI（Flask） |
| 无框架 | 手写 Supervisor 调度逻辑（不用 LangGraph/CrewAI） |

---

## 6. 目录结构

```
investment-research/
├── agents/
│   ├── supervisor.py       # Supervisor Agent（核心调度）
│   ├── workers.py          # 所有 Worker Agent（基类+5个子类）
│   └── synthesizer.py      # Synthesizer Agent
├── tools/
│   └── search.py           # Tavily 搜索封装
├── models/
│   └── types.py            # WorkerResult, ResearchReport 等数据类
├── main.py                 # 入口：python main.py "美团"
├── .env                    # QWEN_API_KEY, TAVILY_API_KEY（占位）
└── requirements.txt
```

---

## 7. 环境变量

```env
QWEN_API_KEY=sk-xxx
TAVILY_API_KEY=tvly-xxx   # 待补充（明日注册后填入）
```

---

## 8. 成功标准

- [ ] 5个 Worker 真正并行跑（asyncio.gather）
- [ ] 单个 Worker 超时/报错不影响其他 Worker
- [ ] Supervisor 能识别低质量结果并触发重试
- [ ] 至少1次动态补充 Worker 被触发（可通过故意构造低质量场景测试）
- [ ] 最终报告包含数据完整性评级和不足维度警告
- [ ] 全程运行时间 < 60s（5个 Worker 并行）
