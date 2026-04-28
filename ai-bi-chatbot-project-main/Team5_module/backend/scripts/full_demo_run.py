import os
import sys
import time
from typing import List, Tuple

import requests


BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:5000")
TIMEOUT_SECONDS = 90
REQUIRED_SNAPSHOT_FIELDS = {"total_revenue", "average_order_value", "unique_customers", "total_orders"}
REQUIRED_REPORT_SECTIONS = [
    "Executive Summary",
    "Data Quality",
    "Visual Insights",
    "Recommendations",
]
CUSTOM_QUESTIONS = [
    "What is my revenue trend this month?",
    "Which product category performs best?",
]
FALLBACK_PATTERNS = [
    "please upload",
    "please run analysis first",
    "error",
    "unable to",
    "not available",
    "unavailable",
    "no data context",
    "question cannot be empty",
]


def run() -> int:
    checks: List[Tuple[str, bool, str]] = []
    anonymous_session = requests.Session()
    session = requests.Session()

    def record(name: str, ok: bool, detail: str):
        checks.append((name, ok, detail))

    def request(active_session: requests.Session, method: str, path: str, **kwargs):
        url = path if path.startswith("http://") or path.startswith("https://") else f"{BASE_URL}{path}"
        return active_session.request(method, url, timeout=TIMEOUT_SECONDS, **kwargs)

    def stop_if_failed() -> int | None:
        failed = [name for name, ok, _ in checks if not ok]
        if failed:
            _print(checks)
            return 1
        return None

    # 1) Health
    health = request(anonymous_session, "GET", "/api/health")
    health_json = _json_body(health)
    record(
        "health_endpoint",
        health.status_code == 200 and health_json.get("status") == "healthy",
        f"status={health.status_code}, body_status={health_json.get('status')}",
    )
    early_exit = stop_if_failed()
    if early_exit is not None:
        return early_exit

    # 2) Clean auth flow: signup, then login with a fresh session
    email = f"full.demo.{int(time.time())}@example.com"
    password = "12345678"
    signup = request(
        anonymous_session,
        "POST",
        "/api/auth/signup",
        json={
            "firstName": "Full",
            "lastName": "Demo",
            "email": email,
            "password": password,
        },
    )
    record(
        "auth_signup",
        signup.status_code == 201,
        f"status={signup.status_code}, email={email}",
    )
    early_exit = stop_if_failed()
    if early_exit is not None:
        return early_exit

    login = request(
        session,
        "POST",
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    login_json = _json_body(login)
    record(
        "auth_login",
        login.status_code == 200 and login_json.get("success") is True,
        f"status={login.status_code}, success={login_json.get('success')}",
    )
    early_exit = stop_if_failed()
    if early_exit is not None:
        return early_exit

    # 3) Dataset discovery and upload
    dataset_path = _resolve_dataset_path()
    record(
        "sample_dataset_exists",
        bool(dataset_path),
        f"path={dataset_path or 'NOT_FOUND'}",
    )
    early_exit = stop_if_failed()
    if early_exit is not None:
        return early_exit

    with open(dataset_path, "rb") as dataset_file:
        upload = request(
            session,
            "POST",
            "/api/analysis/upload",
            files={"file": (os.path.basename(dataset_path), dataset_file, "text/csv")},
            data={"dataset_name": "full_demo_dataset"},
        )

    upload_json = _json_body(upload)
    file_id = upload_json.get("file_id")
    upload_quality = upload_json.get("data_quality", {}) if isinstance(upload_json, dict) else {}
    upload_insights = upload_json.get("insights", []) if isinstance(upload_json, dict) else []
    record(
        "upload_dataset",
        upload.status_code == 201 and bool(file_id),
        f"status={upload.status_code}, file_id={file_id}",
    )
    record(
        "upload_validation_fields",
        bool(upload_json.get("mapping_confidence")) and "data_quality_score" in upload_quality and isinstance(upload_insights, list) and len(upload_insights) > 0,
        f"mapping_confidence={upload_json.get('mapping_confidence')}, data_quality_keys={sorted(list(upload_quality.keys())) if isinstance(upload_quality, dict) else []}, insights={len(upload_insights) if isinstance(upload_insights, list) else 0}",
    )
    early_exit = stop_if_failed()
    if early_exit is not None:
        return early_exit

    # 4) Analyze
    analyze = request(session, "POST", f"/api/analysis/analyze/{file_id}")
    analyze_json = _json_body(analyze)
    results = analyze_json.get("results", {}) if isinstance(analyze_json, dict) else {}
    snapshot = results.get("business_snapshot", {}) if isinstance(results, dict) else {}
    analyze_insights = analyze_json.get("insights", []) if isinstance(analyze_json, dict) else []
    record(
        "analyze_dataset",
        analyze.status_code == 200 and analyze_json.get("success") is True,
        f"status={analyze.status_code}, mode={analyze_json.get('analysis_mode')}",
    )
    record(
        "analysis_business_snapshot",
        REQUIRED_SNAPSHOT_FIELDS.issubset(set(snapshot.keys())),
        f"keys={sorted(list(snapshot.keys())) if isinstance(snapshot, dict) else []}",
    )
    record(
        "analysis_insights_present",
        isinstance(analyze_insights, list) and len(analyze_insights) > 0,
        f"insight_count={len(analyze_insights) if isinstance(analyze_insights, list) else 0}",
    )
    early_exit = stop_if_failed()
    if early_exit is not None:
        return early_exit

    # 5) Visualization payload
    visualization = request(session, "GET", f"/api/analysis/team4-visualization/{file_id}")
    visualization_json = _json_body(visualization)
    visualization_payload = visualization_json.get("team4_visualization", {}) if isinstance(visualization_json, dict) else {}
    charts = visualization_payload.get("charts", []) if isinstance(visualization_payload, dict) else []
    chart_paths = [_resolve_chart_path(chart.get("path", "")) for chart in charts if isinstance(chart, dict)]
    record(
        "visualization_payload",
        visualization.status_code == 200 and visualization_json.get("success") is True,
        f"status={visualization.status_code}, charts={len(charts)}",
    )
    record(
        "visualization_charts_generated",
        len(charts) > 0 and all(path and os.path.exists(path) for path in chart_paths),
        f"chart_count={len(charts)}, existing_chart_files={sum(1 for path in chart_paths if path and os.path.exists(path))}",
    )
    early_exit = stop_if_failed()
    if early_exit is not None:
        return early_exit

    # 6) Predefined questions
    predefined = request(session, "GET", "/api/analysis/predefined-questions")
    predefined_json = _json_body(predefined)
    predefined_questions = predefined_json.get("questions", []) if isinstance(predefined_json, dict) else []
    selected_predefined = [str(item).strip() for item in predefined_questions if str(item).strip()][:3]
    record(
        "predefined_questions_available",
        predefined.status_code == 200 and len(selected_predefined) >= 3,
        f"status={predefined.status_code}, available={len(predefined_questions) if isinstance(predefined_questions, list) else 0}",
    )
    early_exit = stop_if_failed()
    if early_exit is not None:
        return early_exit

    for index, question in enumerate(selected_predefined, start=1):
        answer_ok, detail = _ask_chat_question(session, file_id, question)
        record(f"predefined_chat_{index}", answer_ok, detail)

    # 7) Custom questions
    for index, question in enumerate(CUSTOM_QUESTIONS, start=1):
        answer_ok, detail = _ask_chat_question(session, file_id, question)
        record(f"custom_chat_{index}", answer_ok, detail)

    early_exit = stop_if_failed()
    if early_exit is not None:
        return early_exit

    # 8) Report generation and preview validation
    report = request(session, "POST", f"/api/analysis/generate-report/{file_id}")
    report_json = _json_body(report)
    report_id = report_json.get("report_id")
    preview_url = report_json.get("preview_url")
    download_pdf_url = report_json.get("download_pdf_url")
    record(
        "report_generation",
        report.status_code == 201 and bool(report_id) and bool(preview_url) and bool(download_pdf_url),
        f"status={report.status_code}, report_id={report_id}",
    )
    early_exit = stop_if_failed()
    if early_exit is not None:
        return early_exit

    preview = request(session, "GET", preview_url)
    preview_text = preview.text
    missing_sections = [section for section in REQUIRED_REPORT_SECTIONS if section not in preview_text]
    record(
        "report_preview_loads",
        preview.status_code == 200 and "<html" in preview_text.lower(),
        f"status={preview.status_code}, html={'<html' in preview_text.lower()}",
    )
    record(
        "report_preview_sections",
        len(missing_sections) == 0,
        f"missing_sections={missing_sections}",
    )
    early_exit = stop_if_failed()
    if early_exit is not None:
        return early_exit

    pdf = request(session, "GET", download_pdf_url)
    pdf_bytes = pdf.content
    content_type = pdf.headers.get("content-type", "")
    record(
        "report_pdf_download",
        pdf.status_code == 200 and "application/pdf" in content_type and pdf_bytes.startswith(b"%PDF"),
        f"status={pdf.status_code}, content_type={content_type}, bytes={len(pdf_bytes)}",
    )

    _print(checks)
    failed = [name for name, ok, _ in checks if not ok]
    return 1 if failed else 0


def _resolve_dataset_path() -> str:
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    upload_dir = os.path.join(backend_dir, "uploads")
    upload_candidates = []
    if os.path.isdir(upload_dir):
        upload_candidates = sorted(
            [
                os.path.join(upload_dir, filename)
                for filename in os.listdir(upload_dir)
                if filename.lower().endswith((".csv", ".xlsx", ".json")) and "sample" in filename.lower()
            ]
        )

    candidates = [
        os.path.join(backend_dir, "sample_data.csv"),
        *upload_candidates,
        os.path.normpath(os.path.join(backend_dir, "..", "data", "retail_sales_dataset.csv")),
    ]
    return next((path for path in candidates if os.path.exists(path)), "")


def _resolve_chart_path(chart_path: str) -> str:
    if not chart_path:
        return ""
    if os.path.isabs(chart_path):
        return chart_path

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    team4_report_dir = os.path.normpath(os.path.join(backend_dir, "..", "..", "Team4_module", "reports"))
    return os.path.normpath(os.path.join(team4_report_dir, chart_path))


def _ask_chat_question(session: requests.Session, file_id: str, question: str) -> Tuple[bool, str]:
    response = session.post(
        f"{BASE_URL}/api/analysis/chat/{file_id}",
        json={"question": question, "use_gemini": False},
        timeout=TIMEOUT_SECONDS,
    )
    payload = _json_body(response)
    answer = str(payload.get("answer", "")).strip()
    answer_ok = (
        response.status_code == 200
        and payload.get("success") is True
        and _is_meaningful_answer(answer)
    )
    detail = f"status={response.status_code}, intent={payload.get('intent')}, question={question!r}, answer_preview={answer[:90]!r}"
    return answer_ok, detail


def _is_meaningful_answer(answer: str) -> bool:
    if len(answer.strip()) < 12:
        return False
    lowered = answer.lower()
    return not any(pattern in lowered for pattern in FALLBACK_PATTERNS)


def _json_body(response: requests.Response) -> dict:
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return {}


def _print(checks: List[Tuple[str, bool, str]]):
    print("=== FULL SYSTEM DEMO RUN ===")
    for name, ok, detail in checks:
        state = "PASS" if ok else "FAIL"
        print(f"[{state}] {name}: {detail}")

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    print(f"SUMMARY: {passed}/{total} checks passed")
    if passed == total:
        print("FULL SYSTEM DEMO PASSED")
    else:
        failed = [name for name, ok, _ in checks if not ok]
        print(f"FAILED STEPS: {', '.join(failed)}")


if __name__ == "__main__":
    sys.exit(run())
