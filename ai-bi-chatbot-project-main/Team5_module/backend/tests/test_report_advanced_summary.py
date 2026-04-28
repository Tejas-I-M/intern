from api import analysis_routes
from conftest import register_and_login, upload_file
from services.report_generator import ReportGenerator


def test_advanced_summary_omits_status_boilerplate(client, full_mode_df, write_dataset):
    email = "advanced-summary@example.com"
    register_and_login(client, email=email)

    csv_path = write_dataset(full_mode_df, "csv", "advanced_summary_clean")
    up = upload_file(client, csv_path)
    assert up.status_code == 201
    file_id = up.get_json()["file_id"]

    analyze = client.post(f"/api/analysis/analyze/{file_id}")
    assert analyze.status_code == 200

    analysis_routes.user_analyses[email][file_id]["advanced_outputs"] = {
        "sales-forecast": {
            "success": True,
            "message": "Sales forecasting completed",
            "summary": {
                "forecast_period_days": 30,
                "total_forecasted_sales": 12345.67,
                "average_daily_forecast": 411.52,
                "trend": "Upward",
            },
            "forecast": [
                {
                    "date": "2024-03-01",
                    "forecast": 410.0,
                    "upper_bound_95": 520.0,
                    "lower_bound_95": 300.0,
                }
            ],
            "insights": ["Forecast: $12,346 total sales over 30 days"],
        }
    }

    report = client.post(
        f"/api/analysis/generate-report/{file_id}",
        json={"selected_advanced_modules": ["sales-forecast"]},
    )
    assert report.status_code == 201
    report_id = report.get_json().get("report_id")
    assert report_id

    preview = client.get(f"/api/analysis/report-preview/{report_id}")
    assert preview.status_code == 200
    html = preview.get_data(as_text=True)

    assert "Advanced Summary Results" in html
    assert "Sales Forecast" in html
    assert "Success: True" not in html
    assert "Message: Sales forecasting completed" not in html
    assert "Structured output detected with" not in html
    assert "Forecast Period Days: 30" in html


def test_reportlab_fallback_pdf_includes_advanced_summary(monkeypatch):
    generator = ReportGenerator()
    generator.set_data(
        {
            "advanced_outputs": {
                "sales-forecast": {
                    "success": True,
                    "analysis": {
                        "summary": {
                            "forecast_period_days": 30,
                            "average_daily_forecast": 411.52,
                            "trend": "Upward",
                        },
                        "forecast": [
                            {
                                "date": "2024-03-01",
                                "forecast": 410.0,
                                "upper_bound_95": 520.0,
                                "lower_bound_95": 300.0,
                            }
                        ],
                    },
                }
            }
        }
    )

    captured = {}

    class FakeDoc:
        def __init__(self, filepath, **kwargs):
            self.filepath = filepath
            captured["filepath"] = filepath

        def build(self, story):
            captured["story"] = story
            with open(self.filepath, "wb") as handle:
                handle.write(b"%PDF-1.4 test")

    import reportlab.platypus as platypus

    monkeypatch.setattr(platypus, "SimpleDocTemplate", FakeDoc)

    result = generator._export_to_pdf_reportlab(
        "<html><body><h2>8. Advanced Summary Results</h2></body></html>",
        "fallback_advanced_summary_test",
        user_info={"username": "qa-user"},
        chat_log=[],
    )

    assert result.get("success") is True

    story_text = []
    for flowable in captured.get("story", []):
        if hasattr(flowable, "getPlainText"):
            story_text.append(flowable.getPlainText())

    joined = "\n".join(story_text)
    assert "8. Advanced Summary Results" in joined
    assert "Sales Forecast" in joined
    assert "Forecast Period Days: 30" in joined


def test_report_download_fallback_keeps_advanced_summary(client, full_mode_df, write_dataset, monkeypatch):
    email = "advanced-download@example.com"
    register_and_login(client, email=email)

    csv_path = write_dataset(full_mode_df, "csv", "advanced_download_summary")
    up = upload_file(client, csv_path)
    assert up.status_code == 201
    file_id = up.get_json()["file_id"]

    analyze = client.post(f"/api/analysis/analyze/{file_id}")
    assert analyze.status_code == 200

    analysis_routes.user_analyses[email][file_id]["advanced_outputs"] = {
        "sales-forecast": {
            "success": True,
            "analysis": {
                "summary": {
                    "forecast_period_days": 30,
                    "average_daily_forecast": 411.52,
                },
                "forecast": [
                    {
                        "date": "2024-03-01",
                        "forecast": 410.0,
                    }
                ],
            },
        }
    }

    monkeypatch.setattr(analysis_routes.report_generator, "_ensure_weasyprint", lambda: False)

    captured = {}

    class FakeDoc:
        def __init__(self, filepath, **kwargs):
            self.filepath = filepath

        def build(self, story):
            captured["story"] = story
            with open(self.filepath, "wb") as handle:
                handle.write(b"%PDF-1.4 test")

    import reportlab.platypus as platypus

    monkeypatch.setattr(platypus, "SimpleDocTemplate", FakeDoc)

    report = client.post(
        f"/api/analysis/generate-report/{file_id}",
        json={"selected_advanced_modules": ["sales-forecast"]},
    )
    assert report.status_code == 201
    report_id = report.get_json().get("report_id")
    assert report_id

    download = client.get(f"/api/analysis/report-download/{report_id}/pdf")
    assert download.status_code == 200
    assert download.mimetype == "application/pdf"

    story_text = []
    for flowable in captured.get("story", []):
        if hasattr(flowable, "getPlainText"):
            story_text.append(flowable.getPlainText())

    joined = "\n".join(story_text)
    assert "8. Advanced Summary Results" in joined
    assert "Sales Forecast" in joined
    assert "Forecast Period Days: 30" in joined