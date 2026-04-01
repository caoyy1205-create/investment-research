from dataclasses import dataclass, field


@dataclass
class WorkerResult:
    worker_name: str
    status: str  # SUCCESS | TIMEOUT | ERROR | INSUFFICIENT
    content: str
    quality_score: int = 0
    quality_reason: str = ""
    sources: list = field(default_factory=list)
    retry_count: int = 0


@dataclass
class ReportSection:
    title: str
    content: str
    worker_name: str
    quality_score: int
    has_warning: bool = False


@dataclass
class ResearchReport:
    company: str
    generated_at: str
    data_completeness: str
    sections: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    raw_markdown: str = ""
