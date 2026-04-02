import os
import json
import asyncio
from datetime import datetime
from openai import AsyncOpenAI
from models.types import WorkerResult, ResearchReport
from agents.workers import (
    FinancialWorker, NewsWorker, CompetitorWorker,
    SentimentWorker, RiskWorker, EXTRA_WORKER_MAP
)
from agents.synthesizer import Synthesizer
from tools.search import USE_MOCK


def get_client():
    return AsyncOpenAI(
        api_key=os.getenv("QWEN_API_KEY", "sk-placeholder"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

WORKER_TIMEOUT = 30  # seconds
QUALITY_THRESHOLD = 3
MAX_RETRY = 1


class Supervisor:
    def __init__(self):
        self.synthesizer = Synthesizer()
        self.insufficient = False

    # ── Phase 1: Plan ─────────────────────────────────────────────────────────
    def plan(self, company: str) -> list:
        print(f"\n[Supervisor] Phase 1: Planning for '{company}'")
        workers = [
            FinancialWorker(),
            NewsWorker(),
            CompetitorWorker(),
            SentimentWorker(),
            RiskWorker(),
        ]
        print(f"[Supervisor] Dispatching {len(workers)} workers: {[w.name for w in workers]}")
        return workers

    # ── Phase 2: Parallel Execution ───────────────────────────────────────────
    async def _run_workers_parallel(self, workers: list, company: str) -> list:
        print(f"\n[Supervisor] Phase 2: Running {len(workers)} workers in parallel")

        async def run_with_timeout(worker):
            try:
                result = await asyncio.wait_for(worker.run(company), timeout=WORKER_TIMEOUT)
                print(f"  ✓ {worker.name}: {result.status}")
                return result
            except asyncio.TimeoutError:
                print(f"  ✗ {worker.name}: TIMEOUT (>{WORKER_TIMEOUT}s)")
                return WorkerResult(
                    worker_name=worker.name,
                    status="TIMEOUT",
                    content=f"Worker超时（>{WORKER_TIMEOUT}秒）"
                )
            except Exception as e:
                print(f"  ✗ {worker.name}: ERROR - {e}")
                return WorkerResult(
                    worker_name=worker.name,
                    status="ERROR",
                    content=f"Worker异常: {str(e)}"
                )

        tasks = [run_with_timeout(w) for w in workers]
        results = await asyncio.gather(*tasks)
        return list(results)

    # ── Phase 3: Quality Evaluation ───────────────────────────────────────────
    async def _evaluate_quality(self, result: WorkerResult) -> WorkerResult:
        if result.status != "SUCCESS":
            result.quality_score = 0
            result.quality_reason = f"Worker未成功执行（状态：{result.status}）"
            return result

        # Mock模式下跳过LLM质量评估，直接给4分
        if USE_MOCK:
            result.quality_score = 4
            result.quality_reason = "Mock模式，默认评分4/5"
            return result

        prompt = f"""请评估以下投资研究内容的质量。

内容来源：{result.worker_name}
内容：
{result.content[:2000]}

请从以下三个维度评估（各维度1-5分，综合给出最终1-5分整数）：
1. 信息密度：内容是否包含具体数据和有价值的信息（而非泛泛而谈）
2. 可信度：信息是否有据可查、来源可靠
3. 完整性：是否覆盖了该维度的核心分析要点

仅返回JSON，格式如下（不要有任何其他文字）：
{{"score": 4, "reason": "包含具体财务数据，来源可靠，但缺少估值分析"}}"""

        try:
            client = get_client()
            response = await client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown code blocks if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            result.quality_score = int(data.get("score", 3))
            result.quality_reason = data.get("reason", "")
        except Exception as e:
            result.quality_score = 3
            result.quality_reason = f"评分解析失败，默认3分: {e}"

        return result

    async def _evaluate_all(self, results: list) -> list:
        print(f"\n[Supervisor] Phase 3: Evaluating quality of {len(results)} results")
        evaluated = []
        for result in results:
            r = await self._evaluate_quality(result)
            score_str = f"{r.quality_score}/5" if r.quality_score > 0 else "N/A"
            print(f"  {r.worker_name}: score={score_str} | {r.quality_reason[:60]}")
            evaluated.append(r)
        return evaluated

    async def _retry_low_quality(self, results: list, company: str, original_workers: list) -> list:
        """Retry workers with quality score < threshold (max MAX_RETRY times)."""
        worker_map = {w.name: w for w in original_workers}
        final_results = []

        for result in results:
            if result.quality_score < QUALITY_THRESHOLD and result.quality_score > 0 and result.retry_count < MAX_RETRY:
                worker = worker_map.get(result.worker_name)
                if worker:
                    print(f"  ↻ Retrying {result.worker_name} (score was {result.quality_score})")
                    new_result = await worker.run(company)
                    new_result.retry_count = result.retry_count + 1
                    new_result = await self._evaluate_quality(new_result)
                    print(f"    → New score: {new_result.quality_score}/5")
                    if new_result.quality_score < QUALITY_THRESHOLD:
                        new_result.status = "INSUFFICIENT"
                    final_results.append(new_result)
                    continue
            elif result.quality_score > 0 and result.quality_score < QUALITY_THRESHOLD and result.retry_count >= MAX_RETRY:
                result.status = "INSUFFICIENT"
            final_results.append(result)

        return final_results

    # ── Phase 4: Dynamic Extra Workers ───────────────────────────────────────
    async def _decide_extra_workers(self, results: list, company: str) -> list:
        good_results = [r for r in results if r.quality_score >= QUALITY_THRESHOLD]
        if not good_results:
            print("\n[Supervisor] Phase 4: All workers insufficient — skipping extra dispatch")
            self.insufficient = True
            return []

        avg_score = sum(r.quality_score for r in results if r.quality_score > 0) / max(1, len([r for r in results if r.quality_score > 0]))

        if avg_score < 2:
            print(f"\n[Supervisor] Phase 4: Average quality too low ({avg_score:.1f}) — marking as insufficient")
            self.insufficient = True
            return []

        # Ask LLM to decide if extra workers are needed
        summary = "\n".join(
            f"- {r.worker_name} (score {r.quality_score}): {r.content[:300]}"
            for r in good_results
        )

        prompt = f"""你是一个投资研究协调者。基于以下初步研究结果，判断是否需要派遣额外的专项分析Agent。

公司：{company}
初步研究摘要：
{summary}

可用的额外Agent：
- MnAWorker：当发现重大并购、收购、合并相关信息时派遣
- LegalWorker：当发现重大诉讼、监管处罚、法律纠纷时派遣
- MarketExpansionWorker：当发现进入新市场、海外扩张计划时派遣

仅在内容中有明确信号时才派遣。如无需额外Agent，返回空列表。
仅返回JSON（不要有任何其他文字）：
{{"extra_workers": [], "reasons": []}}

或例如：
{{"extra_workers": ["MnAWorker"], "reasons": ["新闻中提到了重大海外收购事件"]}}"""

        try:
            client = get_client()
            response = await client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            extra_names = data.get("extra_workers", [])
            reasons = data.get("reasons", [])

            extra_workers = []
            for name, reason in zip(extra_names, reasons):
                if name in EXTRA_WORKER_MAP:
                    print(f"  + Dispatching extra worker: {name} — {reason}")
                    extra_workers.append(EXTRA_WORKER_MAP[name]())

            if not extra_workers:
                print(f"\n[Supervisor] Phase 4: No extra workers needed")

            return extra_workers
        except Exception as e:
            print(f"\n[Supervisor] Phase 4: Decision failed ({e}), skipping extra workers")
            return []

    # ── Main Run ──────────────────────────────────────────────────────────────
    async def run(self, company: str) -> ResearchReport:
        print(f"\n{'='*60}")
        print(f"[Supervisor] Starting research for: {company}")
        print(f"{'='*60}")

        # Phase 1
        workers = self.plan(company)

        # Phase 2
        raw_results = await self._run_workers_parallel(workers, company)

        # Phase 3
        evaluated = await self._evaluate_all(raw_results)
        final_results = await self._retry_low_quality(evaluated, company, workers)

        # Phase 4
        print(f"\n[Supervisor] Phase 4: Dynamic worker dispatch decision")
        extra_workers = await self._decide_extra_workers(final_results, company)
        if extra_workers:
            extra_raw = await self._run_workers_parallel(extra_workers, company)
            extra_evaluated = await self._evaluate_all(extra_raw)
            final_results.extend(extra_evaluated)

        if self.insufficient:
            return ResearchReport(
                company=company,
                generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
                data_completeness="0/5",
                raw_markdown=f"# 研究报告：{company}\n\n⚠️ 无法生成报告：相关信息严重不足，无法进行有效分析。",
                warnings=["所有维度数据质量过低，无法生成可靠报告"]
            )

        # Phase 5
        print(f"\n[Supervisor] Phase 5: Synthesizing report")
        report = await self.synthesizer.synthesize(company, final_results)
        return report
