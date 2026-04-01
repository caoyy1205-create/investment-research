# AI 投资研究助手

Multi-Agent 主从架构实践项目。输入公司名，自动调度多个并行 Worker Agent 收集分析，Supervisor 质量评估 + 动态补充，最终生成完整投资研究报告。

## 架构

```
用户输入
  → Supervisor（规划/调度/质量评估/动态派发）
    → [并行] FinancialWorker / NewsWorker / CompetitorWorker / SentimentWorker / RiskWorker
    → 质量评估（LLM打分1-5，<3触发重试）
    → 动态补充（按需派发 MnAWorker / LegalWorker / MarketExpansionWorker）
  → Synthesizer（整合生成报告）
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入：
# QWEN_API_KEY=sk-你的通义千问key
# TAVILY_API_KEY=tvly-你的Tavilykey（注册：https://tavily.com）

# 3. 启动 Web UI
python app.py
# 打开 http://localhost:5000

# 或命令行模式
python main.py 美团
python main.py Tesla
```

## 无 Tavily Key 时的 Mock 模式

如果 `TAVILY_API_KEY` 未配置或为 `tvly-xxx`，系统自动切换到 Mock 模式：
- 使用预设的真实感数据（美团有专属数据，其他公司用通用模板）
- Qwen API 仍会调用，LLM 会对 mock 数据做真实分析
- 适合开发和演示用途

## 文件结构

```
├── agents/
│   ├── supervisor.py    # 核心调度逻辑（5阶段）
│   ├── workers.py       # Worker Agent（5+3个）
│   └── synthesizer.py   # 报告合成
├── tools/
│   └── search.py        # Tavily 搜索（含 Mock）
├── models/
│   └── types.py         # 数据结构定义
├── templates/
│   └── index.html       # Web UI
├── app.py               # Flask 入口
└── main.py              # CLI 入口
```
