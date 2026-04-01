import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from agents.supervisor import Supervisor


async def main(company: str):
    supervisor = Supervisor()
    report = await supervisor.run(company)

    print(f"\n{'='*60}")
    print(f"REPORT GENERATED")
    print(f"{'='*60}")
    print(report.raw_markdown)

    if report.warnings:
        print(f"\n⚠️ Warnings:")
        for w in report.warnings:
            print(f"  - {w}")

    # Save to file
    filename = f"report_{company}_{report.generated_at.replace(':', '-').replace(' ', '_')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report.raw_markdown)
        if report.warnings:
            f.write("\n\n---\n## ⚠️ 数据局限性说明\n")
            for w in report.warnings:
                f.write(f"- {w}\n")
    print(f"\n✓ Report saved to: {filename}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <company_name>")
        print("Example: python main.py 美团")
        sys.exit(1)

    company = sys.argv[1]
    asyncio.run(main(company))
