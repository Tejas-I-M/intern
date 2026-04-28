import pandas as pd

from api import analysis_routes
from conftest import register_and_login, upload_file


def _custom_chat_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            'Transaction ID': [f'T{i:04d}' for i in range(1, 13)],
            'Date': [
                '2024-01-01', '2024-01-05', '2024-01-10', '2024-01-15',
                '2024-01-20', '2024-01-25', '2024-02-01', '2024-02-05',
                '2024-02-10', '2024-02-15', '2024-02-20', '2024-02-25',
            ],
            'Customer ID': ['C001', 'C002', 'C001', 'C003', 'C002', 'C004', 'C005', 'C001', 'C006', 'C002', 'C004', 'C007'],
            'Gender': ['M', 'F', 'M', 'F', 'F', None, 'M', 'F', 'M', 'F', 'M', 'F'],
            'Age': [30, 28, 30, 35, 28, 41, 33, None, 29, 28, 41, 45],
            'Product Category': ['Electronics', 'Beauty', 'Electronics', 'Grocery', 'Beauty', 'Home', 'Electronics', 'Beauty', 'Grocery', 'Electronics', 'Home', 'Beauty'],
            'Region': ['North', 'South', 'North', 'West', None, 'East', 'North', 'South', 'West', 'South', 'East', 'North'],
            'Country': ['US'] * 12,
            'Total Amount': [220.0, 180.0, 340.0, 90.0, 210.0, 140.0, 500.0, 260.0, 120.0, 330.0, 170.0, 290.0],
        }
    )


def test_chatbot_custom_questions_and_integrated_endpoints(client, write_dataset):
    register_and_login(client, email='customchat-e2e@example.com')

    csv_path = write_dataset(_custom_chat_df(), 'csv', 'custom_chat_e2e')
    up = upload_file(client, csv_path)
    assert up.status_code == 201

    file_id = up.get_json()['file_id']

    analyze = client.post(f'/api/analysis/analyze/{file_id}')
    assert analyze.status_code == 200
    analyze_body = analyze.get_json() or {}
    assert analyze_body.get('success') is True
    assert analyze_body.get('analysis_mode') == 'full_analytics'

    # Validate summary payload exists after analysis.
    results = analyze_body.get('results', {})
    assert 'business_snapshot' in results

    questions = [
        ('whats my name?', 'identity_query'),
        ('Give me top 3 recommendations.', 'revenue_growth_query'),
        ('What should I focus on first for growth?', 'revenue_growth_query'),
        ('What is my total and average sales?', 'dataset_ops_query'),
        ('Which columns have missing values?', 'dataset_ops_query'),
    ]

    for question, expected_intent in questions:
        chat = client.post(
            f'/api/analysis/chat/{file_id}',
            json={'question': question, 'use_gemini': True},
        )
        assert chat.status_code == 200
        body = chat.get_json() or {}
        assert body.get('success') is True
        assert isinstance(body.get('answer'), str)
        assert body.get('answer', '').strip() != ''
        if body.get('source', '').startswith('gemini_api('):
            # If Gemini answered directly, accept model response and skip fallback-intent checks.
            continue
        assert body.get('intent') == expected_intent

    # Plot/visualization integration
    viz = client.get(f'/api/analysis/team4-visualization/{file_id}')
    assert viz.status_code == 200
    viz_body = viz.get_json() or {}
    assert viz_body.get('success') is True
    assert 'team4_visualization' in viz_body

    dashboard = client.get(f'/api/analysis/dashboard-data/{file_id}')
    assert dashboard.status_code == 200
    dashboard_body = dashboard.get_json() or {}
    assert dashboard_body.get('success') is True

    # Final report flow
    report = client.post(f'/api/analysis/generate-report/{file_id}')
    assert report.status_code == 201
    report_body = report.get_json() or {}
    assert report_body.get('success') is True
    report_id = report_body.get('report_id')
    assert report_id

    preview = client.get(f'/api/analysis/report-preview/{report_id}')
    assert preview.status_code == 200
    assert preview.mimetype == 'text/html'

    reports = client.get('/api/analysis/reports')
    assert reports.status_code == 200
    reports_body = reports.get_json() or {}
    assert reports_body.get('success') is True
    assert reports_body.get('count', 0) >= 1

    pdf = client.get(f'/api/analysis/export/{file_id}/pdf')
    assert pdf.status_code == 200
    assert len(pdf.data or b'') > 100


def test_chatbot_prefers_gemini_when_available(client, full_mode_df, write_dataset, monkeypatch):
    register_and_login(client, email='gemini-pref@example.com')

    csv_path = write_dataset(full_mode_df, 'csv', 'gemini_pref')
    up = upload_file(client, csv_path)
    assert up.status_code == 201
    file_id = up.get_json()['file_id']

    analyze = client.post(f'/api/analysis/analyze/{file_id}')
    assert analyze.status_code == 200

    service = analysis_routes.unified_nlp_analytics
    assert service is not None

    def fake_gemini(_question: str):
        return {
            'success': True,
            'answer': 'Gemini mock response for test.',
            'intent': 'gemini_powered',
            'confidence': 0.91,
            'pipeline_source': 'gemini_api(mock)',
        }

    monkeypatch.setattr(service, '_try_gemini_api', fake_gemini)

    chat = client.post(
        f'/api/analysis/chat/{file_id}',
        json={'question': 'Give me a growth strategy', 'use_gemini': True},
    )
    assert chat.status_code == 200
    body = chat.get_json() or {}
    assert body.get('success') is True
    assert body.get('source') == 'gemini_api(mock)'
    assert body.get('intent') == 'gemini_powered'


def test_chatbot_fallback_answers_broader_business_questions(client, write_dataset, monkeypatch):
    register_and_login(client, email='fallback-broad@example.com')

    csv_path = write_dataset(_custom_chat_df(), 'csv', 'fallback_broad')
    up = upload_file(client, csv_path)
    assert up.status_code == 201
    file_id = up.get_json()['file_id']

    analyze = client.post(f'/api/analysis/analyze/{file_id}')
    assert analyze.status_code == 200

    service = analysis_routes.unified_nlp_analytics
    assert service is not None

    # Force fallback path so this test validates non-Gemini behavior.
    monkeypatch.setattr(service, '_try_gemini_api', lambda _question: None)

    checks = [
        ('Which region drives most sales?', 'top region by revenue'),
        ('Show monthly trend for my sales', 'monthly revenue trend'),
        ('Give me demographic split by gender', 'revenue by gender'),
        ('give me a quick executive summary from this dataset', 'complete analysis summary:'),
    ]

    for question, expected_snippet in checks:
        chat = client.post(
            f'/api/analysis/chat/{file_id}',
            json={'question': question, 'use_gemini': True},
        )
        assert chat.status_code == 200
        body = chat.get_json() or {}
        assert body.get('success') is True
        answer = (body.get('answer') or '').lower()
        assert 'i can help with:' not in answer
        assert expected_snippet in answer