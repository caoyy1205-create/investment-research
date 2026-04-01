import asyncio
import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

from agents.supervisor import Supervisor

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/research", methods=["POST"])
def research():
    data = request.get_json()
    company = data.get("company", "").strip()

    if not company:
        return jsonify({"error": "请输入公司名称"}), 400

    try:
        supervisor = Supervisor()
        report = asyncio.run(supervisor.run(company))

        return jsonify({
            "report": report.raw_markdown,
            "completeness": report.data_completeness,
            "warnings": report.warnings,
            "generated_at": report.generated_at,
            "sections": [
                {
                    "title": s.title,
                    "worker_name": s.worker_name,
                    "quality_score": s.quality_score,
                    "has_warning": s.has_warning
                }
                for s in report.sections
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting server on http://localhost:{port}")
    app.run(debug=True, port=port)
