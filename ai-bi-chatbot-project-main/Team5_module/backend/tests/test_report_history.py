from conftest import register_and_login, upload_file


def test_report_history_lists_generated_reports(client, full_mode_df, write_dataset):
    register_and_login(client, email="report-history@example.com")

    csv_path = write_dataset(full_mode_df, "csv", "report_history_full")
    up = upload_file(client, csv_path)
    assert up.status_code == 201
    file_id = up.get_json()["file_id"]

    analyze = client.post(f"/api/analysis/analyze/{file_id}")
    assert analyze.status_code == 200

    generated = client.post(f"/api/analysis/generate-report/{file_id}")
    assert generated.status_code == 201
    generated_body = generated.get_json() or {}
    report_id = generated_body.get("report_id")
    assert report_id

    history = client.get("/api/analysis/reports")
    assert history.status_code == 200
    body = history.get_json() or {}

    assert body.get("success") is True
    assert body.get("count", 0) >= 1

    reports = body.get("reports", [])
    target = next((item for item in reports if item.get("report_id") == report_id), None)
    assert target is not None
    assert target.get("file_id") == file_id
    assert target.get("download_pdf_url") == f"/api/analysis/report-download/{report_id}/pdf"
    assert target.get("preview_url") == f"/api/analysis/report-preview/{report_id}"
