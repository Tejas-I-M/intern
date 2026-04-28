import os
import re
import sys
import time
from typing import List, Tuple

import requests


BASE_URL = "http://127.0.0.1:5000"


def run() -> int:
    session = requests.Session()
    checks: List[Tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str):
        checks.append((name, ok, detail))

    def request(method: str, path: str, **kwargs):
        return session.request(method, f"{BASE_URL}{path}", timeout=90, **kwargs)

    # 1) Health
    health = request("GET", "/api/health")
    health_json = health.json() if health.headers.get("content-type", "").startswith("application/json") else {}
    record(
        "health_endpoint",
        health.status_code == 200 and health_json.get("status") == "healthy",
        f"status={health.status_code}, body_status={health_json.get('status')}"
    )

    # 2) Auth session
    email = f"final.signoff.{int(time.time())}@example.com"
    password = "12345678"
    signup = request(
        "POST",
        "/api/auth/signup",
        json={
            "firstName": "Final",
            "lastName": "Signoff",
            "email": email,
            "password": password,
        },
    )

    if signup.status_code == 201:
        record("auth_signup", True, f"status={signup.status_code}, email={email}")
    else:
        login = request("POST", "/api/auth/login", json={"email": email, "password": password})
        record("auth_signup_or_login", login.status_code == 200, f"signup={signup.status_code}, login={login.status_code}")

    # 3) Upload dataset
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(backend_dir, "sample_data.csv"),
        os.path.normpath(os.path.join(backend_dir, "..", "data", "retail_sales_dataset.csv")),
    ]
    dataset_path = next((p for p in candidates if os.path.exists(p)), None)
    if not dataset_path:
        record("dataset_exists", False, "No sample dataset file found")
        _print(checks)
        return 1

    with open(dataset_path, "rb") as f:
        upload = request(
            "POST",
            "/api/analysis/upload",
            files={"file": (os.path.basename(dataset_path), f, "text/csv")},
            data={"dataset_name": "final_signoff_dataset"},
        )

    upload_json = upload.json() if upload.headers.get("content-type", "").startswith("application/json") else {}
    file_id = upload_json.get("file_id")
    record(
        "upload_dataset",
        upload.status_code == 201 and bool(file_id),
        f"status={upload.status_code}, file_id={file_id}"
    )
    upload_quality = upload_json.get("data_quality", {}) if isinstance(upload_json, dict) else {}
    upload_insights = upload_json.get("insights", []) if isinstance(upload_json, dict) else []
    record(
        "upload_mapping_confidence_present",
        bool(upload_json.get("mapping_confidence")),
        f"mapping_confidence={upload_json.get('mapping_confidence')}"
    )
    record(
        "upload_data_quality_present",
        "data_quality_score" in upload_quality,
        f"data_quality_keys={sorted(list(upload_quality.keys())) if isinstance(upload_quality, dict) else []}"
    )
    record(
        "upload_insights_present",
        isinstance(upload_insights, list) and len(upload_insights) > 0,
        f"insight_count={len(upload_insights) if isinstance(upload_insights, list) else 0}"
    )
    if not file_id:
        _print(checks)
        return 1

    # 4) Analyze
    analyze = request("POST", f"/api/analysis/analyze/{file_id}")
    analyze_json = analyze.json() if analyze.headers.get("content-type", "").startswith("application/json") else {}
    snapshot = (analyze_json.get("results") or {}).get("business_snapshot", {})
    record(
        "analyze_dataset",
        analyze.status_code == 200 and analyze_json.get("success") is True,
        f"status={analyze.status_code}, mode={analyze_json.get('analysis_mode')}"
    )
    analyze_quality = analyze_json.get("data_quality", {}) if isinstance(analyze_json, dict) else {}
    analyze_insights = analyze_json.get("insights", []) if isinstance(analyze_json, dict) else []
    record(
        "analyze_mapping_confidence_present",
        bool(analyze_json.get("mapping_confidence")),
        f"mapping_confidence={analyze_json.get('mapping_confidence')}"
    )
    record(
        "analyze_data_quality_present",
        "data_quality_score" in analyze_quality,
        f"data_quality_keys={sorted(list(analyze_quality.keys())) if isinstance(analyze_quality, dict) else []}"
    )
    record(
        "analyze_insights_present",
        isinstance(analyze_insights, list) and len(analyze_insights) > 0,
        f"insight_count={len(analyze_insights) if isinstance(analyze_insights, list) else 0}"
    )
    record(
        "analysis_snapshot_core_keys",
        set(["total_revenue", "average_order_value", "unique_customers", "total_orders"]).issubset(set(snapshot.keys())),
        f"keys={sorted(list(snapshot.keys()))}"
    )

    # 5) Visualization payload / plots
    viz = request("GET", f"/api/analysis/team4-visualization/{file_id}")
    viz_json = viz.json() if viz.headers.get("content-type", "").startswith("application/json") else {}
    viz_payload = viz_json.get("team4_visualization", {}) if isinstance(viz_json, dict) else {}
    charts = viz_payload.get("charts", []) if isinstance(viz_payload, dict) else []
    record(
        "team4_visualization_payload",
        viz.status_code == 200 and viz_json.get("success") is True,
        f"status={viz.status_code}, charts={len(charts)}, enabled={viz_payload.get('enabled')}"
    )

    # 6) Chat Q&A
    chat = request(
        "POST",
        f"/api/analysis/chat/{file_id}",
        json={"question": "What is my revenue trend this month?", "use_gemini": False},
    )
    chat_json = chat.json() if chat.headers.get("content-type", "").startswith("application/json") else {}
    record(
        "chat_qa_response",
        chat.status_code == 200 and chat_json.get("success") is True and bool((chat_json.get("answer") or "").strip()),
        f"status={chat.status_code}, intent={chat_json.get('intent')}"
    )

    # 7) Generate report
    report = request("POST", f"/api/analysis/generate-report/{file_id}")
    report_json = report.json() if report.headers.get("content-type", "").startswith("application/json") else {}
    report_id = report_json.get("report_id")
    preview_url = report_json.get("preview_url")
    download_pdf_url = report_json.get("download_pdf_url")

    record(
        "report_generation",
        report.status_code == 201 and bool(report_id) and bool(preview_url) and bool(download_pdf_url),
        f"status={report.status_code}, report_id={report_id}"
    )
    if not preview_url or not download_pdf_url:
        _print(checks)
        return 1

    # 8) Preview content includes upgraded report sections and chart labels/images
    preview = request("GET", preview_url)
    preview_text = preview.text
    preview_is_html = preview.status_code == 200 and "<html" in preview_text.lower()
    required_sections = [
        "Executive Summary",
        "Data Quality",
        "Business Snapshot",
        "Visual Insights",
        "Customer Summary",
        "Recommendations",
        "Questions &amp; Answers Log",
    ]
    missing_sections = [section for section in required_sections if section not in preview_text]
    has_sections = len(missing_sections) == 0
    has_img = "<img" in preview_text.lower()
    has_img_label = bool(re.search(r"alt=\"[^\"]+\"", preview_text, flags=re.IGNORECASE))
    has_date_range = bool(re.search(r"Date\s*Range.*\d{4}-\d{2}-\d{2}", preview_text, flags=re.IGNORECASE | re.DOTALL))
    executive_match = re.search(
        r"<h2>1\. Executive Summary</h2>(.*?)<h2>2\. Data Quality \+ Mapping</h2>",
        preview_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    executive_points = re.findall(r"<li>.*?</li>", executive_match.group(1), flags=re.IGNORECASE | re.DOTALL) if executive_match else []
    visual_match = re.search(
        r"<h2>4\. Visual Insights</h2>(.*?)<h2>5\. Customer Summary</h2>",
        preview_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    visual_insight_lines = re.findall(r'figure-insight', visual_match.group(1), flags=re.IGNORECASE) if visual_match else []
    recommendations_match = re.search(
        r"<h2>6\. Recommendations</h2>(.*?)<h2>7\. Questions",
        preview_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    recommendation_items = re.findall(r"<li>.*?</li>", recommendations_match.group(1), flags=re.IGNORECASE | re.DOTALL) if recommendations_match else []

    record(
        "report_preview_html",
        preview_is_html,
        f"status={preview.status_code}, html={preview_is_html}"
    )
    record(
        "report_preview_sections",
        has_sections,
        f"missing_sections={missing_sections}"
    )
    record(
        "report_preview_plot_labels",
        has_img and has_img_label,
        f"has_img={has_img}, has_img_label={has_img_label}"
    )
    record(
        "report_preview_date_range",
        has_date_range,
        "date_range_present_in_preview"
    )
    record(
        "executive_summary_has_multiple_points",
        len(executive_points) >= 3,
        f"executive_points={len(executive_points)}"
    )
    record(
        "visual_insights_not_empty",
        len(visual_insight_lines) >= 1,
        f"visual_insight_lines={len(visual_insight_lines)}"
    )
    record(
        "recommendations_present",
        len(recommendation_items) >= 1,
        f"recommendation_items={len(recommendation_items)}"
    )

    # 9) PDF download checks
    pdf = request("GET", download_pdf_url)
    content_type = pdf.headers.get("content-type", "")
    pdf_bytes = pdf.content
    has_pdf_header = pdf_bytes.startswith(b"%PDF")
    has_embedded_image_marker = b"/Image" in pdf_bytes

    record(
        "pdf_download",
        pdf.status_code == 200 and "application/pdf" in content_type and has_pdf_header and len(pdf_bytes) > 1500,
        f"status={pdf.status_code}, content_type={content_type}, bytes={len(pdf_bytes)}"
    )
    record(
        "pdf_contains_plot_image_objects",
        has_embedded_image_marker,
        f"embedded_image_marker={has_embedded_image_marker}"
    )

    # 10) Report history endpoint includes generated report
    history = request("GET", "/api/analysis/reports")
    history_json = history.json() if history.headers.get("content-type", "").startswith("application/json") else {}
    reports = history_json.get("reports", []) if isinstance(history_json, dict) else []
    found_report = any(item.get("report_id") == report_id for item in reports)
    record(
        "report_history_listing",
        history.status_code == 200 and history_json.get("success") is True and found_report,
        f"status={history.status_code}, found_report={found_report}, count={len(reports)}"
    )

    # 11) PDF-only export policy
    csv_export = request("GET", f"/api/analysis/export/{file_id}/csv")
    csv_json = csv_export.json() if csv_export.headers.get("content-type", "").startswith("application/json") else {}
    record(
        "pdf_only_export_policy",
        csv_export.status_code == 400 and "pdf only" in (csv_json.get("message", "").lower()),
        f"status={csv_export.status_code}, message={csv_json.get('message')}"
    )

    _print(checks)
    failed = [name for name, ok, _ in checks if not ok]
    return 1 if failed else 0


def _print(checks: List[Tuple[str, bool, str]]):
    print("=== FINAL BACKEND SIGNOFF CHECK ===")
    for name, ok, detail in checks:
        state = "PASS" if ok else "FAIL"
        print(f"[{state}] {name}: {detail}")

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    print(f"SUMMARY: {passed}/{total} checks passed")
    if passed == total:
        print("ALL BACKEND + REPORT CHECKS PASSED")
    else:
        failed = [name for name, ok, _ in checks if not ok]
        print(f"FAILED CHECKS: {', '.join(failed)}")


if __name__ == "__main__":
    sys.exit(run())
