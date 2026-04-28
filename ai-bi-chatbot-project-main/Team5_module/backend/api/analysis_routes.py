from flask import Blueprint, request, jsonify, session, send_file, current_app, g
import os
import re
import secrets
import pandas as pd
import io
import json
import math
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from werkzeug.utils import secure_filename
from datetime import datetime
from services.data_processor import DataProcessor
from services.chatbot_service import ChatbotService
from services.report_generator import ReportGenerator
from services.insight_engine import DataQualityService, InsightBuilder
from services.unified_nlp_analytics import initialize_unified_service, get_unified_service
from services.real_analytics_service import get_real_analytics_service
from services.team4_visualization_adapter import initialize_team4_adapter, get_team4_adapter
from auth.auth_handler import add_report_to_user

analysis_bp = Blueprint('analysis', __name__, url_prefix='/api/analysis')

NO_ADVANCED_DATA_MESSAGE = 'No data for analysis for this module in the uploaded dataset.'


def _sanitize_report_output(text):
    """Normalize report wording by removing deprecated/overly-technical advanced-module messages."""
    if not isinstance(text, str) or not text:
        return text

    cleaned = text.replace('Table omitted intentionally to keep this report concise.', '')
    cleaned = re.sub(r'(?im)^-\s*details:\s*required columns not found[^\n]*\n?', '', cleaned)
    cleaned = re.sub(r'(?im)^-\s*success:\s*true\s*\n?', '', cleaned)
    cleaned = re.sub(r'(?im)^-\s*message:\s*[^\n]*(completed|successful|successfully)[^\n]*\n?', '', cleaned)
    cleaned = re.sub(r'(?im)^-\s*structured output detected with[^\n]*\n?', '', cleaned)
    cleaned = re.sub(r'(?is)<p\s+class="subtle-note">\s*Details:\s*Required columns not found.*?</p>', '', cleaned)
    cleaned = re.sub(r'(?is)<li>\s*Success:\s*True\s*</li>', '', cleaned)
    cleaned = re.sub(r'(?is)<li>\s*Message:\s*[^<]*(completed|successful|successfully)[^<]*</li>', '', cleaned)
    cleaned = re.sub(r'(?is)<li>\s*Structured output detected with[^<]*</li>', '', cleaned)
    cleaned = re.sub(r'(?im)^-\s*$', '', cleaned)
    cleaned = cleaned.replace('<li></li>', '')
    return cleaned


def _sanitize_for_json(value):
    """Recursively sanitize payload values so responses are strict JSON compatible."""
    if isinstance(value, dict):
        return {str(k): _sanitize_for_json(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_sanitize_for_json(item) for item in value]

    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()

    # pandas / numpy scalar fallback (e.g. np.int64, np.float64)
    if hasattr(value, 'item') and callable(getattr(value, 'item')):
        try:
            return _sanitize_for_json(value.item())
        except Exception:
            pass

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    return value


def _load_json_loose(raw_text):
    """Try to parse JSON-ish text that may include non-standard constants like NaN."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None
    try:
        return json.loads(raw_text)
    except Exception:
        return None


@analysis_bp.after_request
def save_advanced_outputs(response):
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
        
        path = request.path
        if '/api/analysis/' in path and response.is_json:
            payload = response.get_json(silent=True)
            if payload is None:
                payload = _load_json_loose(response.get_data(as_text=True))

            if payload is not None:
                sanitized_payload = _sanitize_for_json(payload)
                response.set_data(json.dumps(sanitized_payload, ensure_ascii=False, allow_nan=False))
                response.mimetype = 'application/json'

            path_parts = path.strip('/').split('/')
            
            advanced_keys = [
               'cohort-analysis', 'geographic-analysis', 'timeseries-analysis', 'churn-prediction',
               'sales-forecast', 'product-affinity', 'clv', 'repeat-purchase',
               'health-score', 'anomalies', 'product-performance', 'promotional-impact'
            ]
            
            for key in advanced_keys:
                if key in path_parts:
                    file_id = None
                    for part in path_parts:
                        if len(part) >= 15:  # heuristic for file_id
                            file_id = part
                            break
                    if file_id and user_id in user_analyses and file_id in user_analyses[user_id]:
                        if 'advanced_outputs' not in user_analyses[user_id][file_id]:
                            user_analyses[user_id][file_id]['advanced_outputs'] = {}
                        
                        dict_key = path.split('/api/analysis/')[-1].split('/')[0]
                        stored_payload = response.get_json(silent=True)
                        if stored_payload is not None:
                            user_analyses[user_id][file_id]['advanced_outputs'][dict_key] = stored_payload
    except Exception as e:
        import traceback
        traceback.print_exc()
        pass
    return response


# Global instances
data_processor = None
chatbot_service = None
report_generator = ReportGenerator()
data_quality_service = DataQualityService()
insight_builder = InsightBuilder()
unified_nlp_analytics = None  # Unified NLP + Analytics engine service
team4_visualization_adapter = None  # Team4 visualization bridge
user_datasets = {}  # Store user's uploaded data in memory {user_id: {file_id: dataframe}}
user_analyses = {}  # Store analysis results {user_id: {file_id: analysis_results}}
chat_histories = {}  # Store chat histories {user_id: [{role, message, timestamp}]}
analysis_jobs = {}  # Store async analysis jobs by job_id
analysis_jobs_lock = threading.Lock()
analysis_executor = ThreadPoolExecutor(max_workers=2)

ANALYSIS_JOB_TIMEOUT_SECONDS = 180
ANALYSIS_JOB_MAX_RETRIES = 1


ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.json', '.parquet'}
RECENT_ANALYSIS_FILE = os.path.join(os.path.dirname(__file__), '..', 'recent_analyses.json')

PUBLIC_ANALYSIS_ENDPOINTS = {
    'analysis.get_predefined_questions',
    'analysis.get_nlp_status'
}


def build_preview_payload(df, rows=10):
    """Return compact preview payload safe for JSON responses."""
    preview_df = df.head(rows).copy()
    preview_df = preview_df.where(pd.notna(preview_df), None)

    return {
        'rows': preview_df.to_dict(orient='records'),
        'row_count': min(len(df), rows),
        'total_rows': len(df),
        'columns': list(df.columns)
    }


def load_recent_analyses():
    """Load persisted recent analyses from local JSON."""
    try:
        if os.path.exists(RECENT_ANALYSIS_FILE):
            with open(RECENT_ANALYSIS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading recent analyses: {e}")
    return {}


def save_recent_analyses(data):
    """Save persisted recent analyses to local JSON."""
    try:
        os.makedirs(os.path.dirname(RECENT_ANALYSIS_FILE), exist_ok=True)
        with open(RECENT_ANALYSIS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving recent analyses: {e}")
        return False


def persist_recent_analysis(user_id, file_id, dataset_name, analysis_results):
    """Store analysis summary and keep last 5 entries per user."""
    all_recent = load_recent_analyses()
    user_recent = all_recent.get(user_id, [])

    kpis = analysis_results.get('kpis', {})
    entry = {
        'file_id': file_id,
        'dataset_name': dataset_name,
        'analyzed_at': datetime.now().isoformat(),
        'summary': {
            'total_revenue': kpis.get('total_revenue'),
            'average_order_value': kpis.get('average_order_value'),
            'unique_customers': kpis.get('unique_customers'),
            'total_orders': kpis.get('total_orders')
        },
        'capabilities': analysis_results.get('analysis_status', {})
    }

    user_recent.insert(0, entry)
    all_recent[user_id] = user_recent[:5]
    save_recent_analyses(all_recent)


def generate_suggested_questions(capabilities):
    """Generate simple user-friendly suggested questions based on dataset capabilities."""
    suggestions = []

    if capabilities.get('kpis'):
        suggestions.append("What are my key KPIs for this dataset?")
    if capabilities.get('trends'):
        suggestions.append("Show me the revenue trend for the last periods.")
    if capabilities.get('segmentation'):
        suggestions.append("Who are my top customer segments?")
    if capabilities.get('top_categories'):
        suggestions.append("Which product category performs best?")
    if capabilities.get('forecast'):
        suggestions.append("What can we expect in future sales?")
    if capabilities.get('churn_prediction'):
        suggestions.append("Which customers look at risk of churn?")

    if not suggestions:
        suggestions.append("What columns should I map to unlock deeper analysis?")

    return suggestions[:5]


@analysis_bp.before_request
def _enforce_analysis_authentication():
    """Require authenticated sessions for analysis endpoints.

    Demo fallback can be explicitly enabled using ALLOW_DEMO_USER_FALLBACK.
    """
    # Browser CORS preflight should not require authenticated cookies.
    if request.method == 'OPTIONS':
        return None

    endpoint = request.endpoint or ''
    if endpoint in PUBLIC_ANALYSIS_ENDPOINTS:
        return None

    user_id = session.get('user_id')
    if not user_id and current_app.config.get('ALLOW_DEMO_USER_FALLBACK', False):
        user_id = 'demo_user_testing'
        session['user_id'] = user_id

    if not user_id:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401

    g.user_id = user_id
    return None


def get_analysis_mode(capabilities, dataset_mode='full_analytics'):
    """Determine analysis mode for UI guidance."""
    if dataset_mode == 'exploratory_only':
        return 'exploratory_only'

    core_flags = [
        capabilities.get('kpis', False),
        capabilities.get('trends', False),
        capabilities.get('segmentation', False)
    ]
    if all(core_flags):
        return 'full_analytics'
    if any(core_flags):
        return 'partial_analytics'
    return 'exploratory_only'


ADVANCED_CANONICAL_KEY_MAP = {
    'cohort': 'cohort',
    'cohortanalysis': 'cohort',
    'geographic': 'geographic',
    'geographicanalysis': 'geographic',
    'timeseries': 'timeseries',
    'timeseriesanalysis': 'timeseries',
    'churn': 'churn',
    'churnprediction': 'churn',
    'forecast': 'forecast',
    'salesforecast': 'forecast',
    'affinity': 'affinity',
    'productaffinity': 'affinity',
    'clv': 'clv',
    'repeatpurchase': 'repeatpurchase',
    'healthscore': 'healthscore',
    'anomalies': 'anomalies',
    'productperformance': 'productperformance',
    'promotionalimpact': 'promotionalimpact'
}


def _normalize_advanced_key(key_value):
    token = ''.join(ch for ch in str(key_value or '').lower() if ch.isalnum())
    return ADVANCED_CANONICAL_KEY_MAP.get(token, token)


ADVANCED_CANONICAL_TO_ROUTE_KEY = {
    'cohort': 'cohort-analysis',
    'geographic': 'geographic-analysis',
    'timeseries': 'timeseries-analysis',
    'churn': 'churn-prediction',
    'forecast': 'sales-forecast',
    'affinity': 'product-affinity',
    'clv': 'clv',
    'repeatpurchase': 'repeat-purchase',
    'healthscore': 'health-score',
    'anomalies': 'anomalies',
    'productperformance': 'product-performance',
    'promotionalimpact': 'promotional-impact'
}


def _resolve_requested_advanced_route_keys(selected_advanced_modules):
    selected = selected_advanced_modules or []
    normalized = [
        _normalize_advanced_key(item)
        for item in selected
        if isinstance(item, str) and item.strip()
    ]

    if not normalized:
        return list(ADVANCED_CANONICAL_TO_ROUTE_KEY.values())

    resolved = []
    for token in normalized:
        route_key = ADVANCED_CANONICAL_TO_ROUTE_KEY.get(token)
        if route_key:
            resolved.append(route_key)
    return resolved


def _build_advanced_module_payload(module_result, default_message=NO_ADVANCED_DATA_MESSAGE):
    if not isinstance(module_result, dict):
        module_result = {'success': False, 'message': default_message}

    module_success = bool(module_result.get('success'))
    module_message = module_result.get('message') or (default_message if not module_success else 'Analysis completed successfully.')

    return {
        'success': module_success,
        'message': module_message,
        'analysis': module_result
    }


def _compute_advanced_module_output(route_key, dataset_df):
    analytics = get_real_analytics_service()

    if route_key == 'cohort-analysis':
        return _build_advanced_module_payload(analytics.analyze_customer_cohorts(dataset_df))
    if route_key == 'geographic-analysis':
        return _build_advanced_module_payload(analytics.analyze_geography(dataset_df))
    if route_key == 'timeseries-analysis':
        return _build_advanced_module_payload(analytics.analyze_timeseries(dataset_df, period=12))
    if route_key == 'churn-prediction':
        return _build_advanced_module_payload(analytics.predict_churn(dataset_df, days_threshold=90))
    if route_key == 'sales-forecast':
        return _build_advanced_module_payload(analytics.analyze_forecast(dataset_df, periods=30))
    if route_key == 'product-affinity':
        return _build_advanced_module_payload(
            analytics.analyze_product_affinity(dataset_df, min_support=0.02, min_confidence=0.3)
        )
    if route_key == 'clv':
        return _build_advanced_module_payload(analytics.calculate_customer_lifetime_value(dataset_df))
    if route_key == 'repeat-purchase':
        return _build_advanced_module_payload(analytics.calculate_repeat_purchase_analysis(dataset_df))
    if route_key == 'health-score':
        return _build_advanced_module_payload(analytics.calculate_customer_health_score(dataset_df))
    if route_key == 'anomalies':
        return _build_advanced_module_payload(analytics.detect_anomalies(dataset_df, sensitivity=2.0))
    if route_key == 'product-performance':
        return _build_advanced_module_payload(analytics.analyze_product_performance(dataset_df))
    if route_key == 'promotional-impact':
        return _build_advanced_module_payload(analytics.analyze_promotional_impact(dataset_df))

    return {
        'success': False,
        'message': NO_ADVANCED_DATA_MESSAGE,
        'analysis': {
            'success': False,
            'message': f'Unsupported advanced module key: {route_key}'
        }
    }


def _ensure_advanced_outputs_available(user_id, file_id, selected_advanced_modules=None):
    if user_id not in user_datasets or file_id not in user_datasets[user_id]:
        return {}

    if user_id not in user_analyses or file_id not in user_analyses[user_id]:
        return {}

    analysis_payload = user_analyses[user_id][file_id]
    existing = analysis_payload.get('advanced_outputs', {})
    if not isinstance(existing, dict):
        existing = {}

    requested_route_keys = _resolve_requested_advanced_route_keys(selected_advanced_modules)
    dataset_df = user_datasets[user_id][file_id].get('dataframe')

    for route_key in requested_route_keys:
        if route_key in existing and isinstance(existing.get(route_key), dict):
            continue

        try:
            computed = _compute_advanced_module_output(route_key, dataset_df)
        except Exception as exc:
            computed = {
                'success': False,
                'message': NO_ADVANCED_DATA_MESSAGE,
                'analysis': {
                    'success': False,
                    'message': str(exc)
                }
            }

        existing[route_key] = _sanitize_for_json(computed)

    analysis_payload['advanced_outputs'] = existing
    return existing


def _filter_advanced_outputs(advanced_outputs, selected_advanced_modules):
    if not isinstance(advanced_outputs, dict):
        return {}

    selected = selected_advanced_modules or []
    selected_tokens = {
        _normalize_advanced_key(item)
        for item in selected
        if isinstance(item, str) and item.strip()
    }

    if not selected_tokens:
        return advanced_outputs

    filtered = {}
    for key, value in advanced_outputs.items():
        if _normalize_advanced_key(key) in selected_tokens:
            filtered[key] = value
    return filtered


def _build_report_payload(user_id, file_id, include_advanced_modules=True, selected_advanced_modules=None):
    """Build report payload that combines analysis results with dataset metadata."""
    dataset = user_datasets[user_id][file_id]
    analysis_results = dict(user_analyses[user_id][file_id])

    df = dataset.get('dataframe')
    columns = list(df.columns) if df is not None else dataset.get('columns', [])

    dataset_summary = {
        'dataset_name': dataset.get('filename', 'uploaded_dataset'),
        'row_count': int(len(df)) if df is not None else int(dataset.get('row_count', 0)),
        'column_count': int(len(columns)),
        'columns': columns,
        'source_columns': dataset.get('source_columns', []),
        'mapped_columns': dataset.get('mapped_columns', {}),
        'mapping_issues': dataset.get('mapping_issues', []),
        'mapping_confidence': dataset.get('mapping_confidence', 'HIGH'),
        'data_quality': dataset.get('data_quality', {}),
        'analysis_mode': analysis_results.get('analysis_mode', dataset.get('mode', 'full_analytics')),
        'capabilities': dataset.get('capabilities', {}),
        'analysis_plan': dataset.get('analysis_plan', {})
    }

    analysis_results['dataset_summary'] = dataset_summary
    analysis_results['mapping_confidence'] = dataset.get('mapping_confidence', analysis_results.get('mapping_confidence', 'HIGH'))
    analysis_results['mapping_issues'] = dataset.get('mapping_issues', analysis_results.get('mapping_issues', []))
    analysis_results['data_quality'] = dataset.get('data_quality', analysis_results.get('data_quality', {}))
    analysis_results['insights'] = analysis_results.get('insights', dataset.get('insights', []))

    snapshot = analysis_results.get('business_snapshot', {})
    if not isinstance(snapshot, dict):
        snapshot = {}

    kpis = analysis_results.get('kpis', {})
    if not isinstance(kpis, dict):
        kpis = {}

    date_range = snapshot.get('date_range', {})
    if not isinstance(date_range, dict) or not date_range.get('start') or not date_range.get('end'):
        date_range = {'start': 'N/A', 'end': 'N/A'}
        if df is not None and 'Date' in df.columns and not df.empty:
            parsed_dates = pd.to_datetime(df['Date'], errors='coerce').dropna()
            if not parsed_dates.empty:
                date_range = {
                    'start': str(parsed_dates.min().date()),
                    'end': str(parsed_dates.max().date())
                }

    analysis_results['business_snapshot'] = {
        'total_revenue': snapshot.get('total_revenue', kpis.get('total_revenue')),
        'average_order_value': snapshot.get('average_order_value', kpis.get('average_order_value')),
        'unique_customers': snapshot.get('unique_customers', kpis.get('unique_customers')),
        'total_orders': snapshot.get('total_orders', kpis.get('total_orders')),
        'date_range': date_range
    }

    customer_summary = {
        'total_customers': analysis_results['business_snapshot'].get('unique_customers'),
        'top_customers': [],
        'top_segments': []
    }

    if df is not None and 'Customer ID' in df.columns and 'Total Amount' in df.columns:
        customer_frame = df[['Customer ID', 'Total Amount']].copy()
        customer_frame['Total Amount'] = pd.to_numeric(customer_frame['Total Amount'], errors='coerce')
        customer_frame = customer_frame.dropna(subset=['Customer ID', 'Total Amount'])
        if not customer_frame.empty:
            top_customers = (
                customer_frame
                .groupby('Customer ID', as_index=False)
                .agg(total_revenue=('Total Amount', 'sum'), order_count=('Customer ID', 'size'))
                .sort_values(by='total_revenue', ascending=False)
                .head(5)
            )
            customer_summary['top_customers'] = [
                {
                    'customer_id': str(row['Customer ID']),
                    'total_revenue': float(row['total_revenue']),
                    'order_count': int(row['order_count'])
                }
                for _, row in top_customers.iterrows()
            ]

    segments = analysis_results.get('segments', {})
    if isinstance(segments, dict) and segments:
        ranked_segments = sorted(
            segments.items(),
            key=lambda item: float(item[1].get('total_revenue', item[1].get('revenue', 0)) or 0),
            reverse=True
        )[:5]
        customer_summary['top_segments'] = [
            {
                'name': name,
                'count': int(data.get('count', data.get('customers', 0)) or 0),
                'total_revenue': float(data.get('total_revenue', data.get('revenue', 0)) or 0)
            }
            for name, data in ranked_segments
        ]

    analysis_results['customer_summary'] = customer_summary

    advanced_outputs = _ensure_advanced_outputs_available(
        user_id,
        file_id,
        selected_advanced_modules=selected_advanced_modules
    )
    if not include_advanced_modules:
        analysis_results['advanced_outputs'] = {}
    else:
        analysis_results['advanced_outputs'] = _filter_advanced_outputs(advanced_outputs, selected_advanced_modules)

    analysis_results['advanced_modules_selected'] = [
        item for item in (selected_advanced_modules or [])
        if isinstance(item, str) and item.strip()
    ]


    return analysis_results


def _now_iso():
    return datetime.now().isoformat()


def _resolve_user_report(user_id, report_id):
    """Return a stored report entry for the authenticated user."""
    from auth.auth_handler import get_user

    user = get_user(user_id) or {}
    reports = user.get('reports', [])
    for report in reports:
        if report.get('report_id') == report_id:
            return report
    return None


def _ensure_report_path(path):
    """Allow only files under backend reports directory."""
    if not path:
        return None

    reports_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'reports'))
    allowed_prefix = reports_root + os.sep

    # Primary candidate: provided path as-is.
    candidates = [os.path.abspath(path)]

    # Legacy fallback: old absolute paths may point to another workspace root.
    # In that case, keep only the filename and remap into current reports directory.
    basename = os.path.basename(path)
    if basename:
        candidates.append(os.path.abspath(os.path.join(reports_root, basename)))

    for candidate in candidates:
        if candidate == reports_root or candidate.startswith(allowed_prefix):
            return candidate

    return None


def _build_report_download_name(report_id, report_entry):
    """Build a stable and user-friendly PDF filename for downloads."""
    dataset_name = report_entry.get('dataset_name') if isinstance(report_entry, dict) else None
    safe_name = secure_filename(dataset_name or '')
    if not safe_name:
        safe_name = f"report_{report_id}"
    if not safe_name.lower().endswith('.pdf'):
        safe_name = f"{safe_name}.pdf"
    return safe_name


def _set_job_state(job_id, **updates):
    with analysis_jobs_lock:
        if job_id in analysis_jobs:
            analysis_jobs[job_id].update(updates)
            analysis_jobs[job_id]['updated_at'] = _now_iso()


def _run_analysis_pipeline(user_id, file_id):
    """Shared analysis pipeline used by both sync and async analysis endpoints."""
    if user_id not in user_datasets or file_id not in user_datasets[user_id]:
        raise ValueError('File not found')

    dataset = user_datasets[user_id][file_id]
    df = dataset['dataframe']
    capabilities = dataset.get('capabilities', {})
    analysis_plan = dataset.get('analysis_plan', data_processor.build_analysis_plan(df))
    analysis_mode = get_analysis_mode(capabilities, dataset.get('mode', 'full_analytics'))
    suggested_questions = generate_suggested_questions(capabilities)
    data_quality = dataset.get('data_quality') or data_quality_service.calculate(
        dataset.get('raw_dataframe') if dataset.get('raw_dataframe') is not None else df
    )
    dataset['data_quality'] = data_quality

    real_analytics = get_real_analytics_service()
    analysis_results = {}
    analysis_status = {}

    def mark_skipped(key, reason):
        analysis_status[key] = {
            'status': 'skipped',
            'reason': reason,
            'missing_columns': analysis_plan.get(key, {}).get('missing_columns', [])
        }

    def mark_completed(key):
        analysis_status[key] = {
            'status': 'completed',
            'missing_columns': []
        }

    if capabilities.get('kpis'):
        analysis_results['kpis'] = real_analytics.get_real_kpis(df)
        mark_completed('kpis')
    else:
        analysis_results['kpis'] = {}
        mark_skipped('kpis', 'Required columns missing for KPI analysis')

    # Keep a stable KPI payload shape for all clients, including exploratory datasets.
    kpis = analysis_results.get('kpis', {}) or {}
    normalized_snapshot = {
        'total_revenue': kpis.get('total_revenue'),
        'average_order_value': kpis.get('average_order_value'),
        'unique_customers': kpis.get('unique_customers'),
        'total_orders': kpis.get('total_orders')
    }
    analysis_results['kpis'] = normalized_snapshot

    if capabilities.get('trends'):
        analysis_results['trends'] = real_analytics.get_revenue_trends(df, 'month')
        mark_completed('trends')
    else:
        analysis_results['trends'] = []
        mark_skipped('trends', 'Required columns missing for trend analysis')

    if capabilities.get('top_categories'):
        analysis_results['top_categories'] = real_analytics.get_top_categories(df, top_n=4)
        mark_completed('top_categories')
    else:
        analysis_results['top_categories'] = []
        mark_skipped('top_categories', 'Product/category columns missing for category analysis')

    if capabilities.get('segmentation'):
        analysis_results['segments'] = real_analytics.get_customer_segments(df)
        mark_completed('segmentation')
    else:
        analysis_results['segments'] = {}
        mark_skipped('segmentation', 'Customer and amount columns missing for segmentation')

    analysis_results['business_snapshot'] = dict(analysis_results.get('kpis', {}))

    try:
        if capabilities.get('forecast'):
            forecast_result = data_processor.apply_forecasting(df)
            if forecast_result['success']:
                analysis_results['forecast'] = forecast_result
                mark_completed('forecast')
            else:
                mark_skipped('forecast', forecast_result.get('message', 'Forecast unavailable'))
        else:
            mark_skipped('forecast', 'Date and amount columns missing for forecasting')
    except Exception:
        mark_skipped('forecast', 'Forecasting unavailable due to runtime error')

    try:
        if capabilities.get('churn_prediction'):
            churn_result = data_processor.apply_churn_prediction(df)
            if churn_result['success']:
                analysis_results['churn'] = churn_result
                mark_completed('churn_prediction')
            else:
                mark_skipped('churn_prediction', churn_result.get('message', 'Churn prediction unavailable'))
        else:
            mark_skipped('churn_prediction', 'Core columns plus demographic or product columns are required')
    except Exception:
        mark_skipped('churn_prediction', 'Churn prediction unavailable due to runtime error')

    analysis_results['analysis_status'] = analysis_status
    analysis_results['exploratory_summary'] = dataset.get('exploratory_summary') or data_processor.build_exploratory_summary(df)
    analysis_results['data_quality'] = data_quality
    analysis_results['analysis_mode'] = analysis_mode
    analysis_results['insights'] = insight_builder.build(df, data_quality, analysis_results)
    if team4_visualization_adapter:
        analysis_results['team4_visualization'] = team4_visualization_adapter.build_payload(df)
    else:
        analysis_results['team4_visualization'] = {
            'enabled': False,
            'message': 'Team4 visualization adapter is not initialized',
            'insights': [],
            'charts': []
        }

    # Keep latest Team4 visualization payload with dataset for dashboard/API consumers.
    dataset['team4_visualization'] = analysis_results.get('team4_visualization', {})

    if user_id not in user_analyses:
        user_analyses[user_id] = {}
    user_analyses[user_id][file_id] = analysis_results
    persist_recent_analysis(user_id, file_id, dataset.get('filename', 'uploaded_dataset'), analysis_results)

    chatbot_service.set_data_context(analysis_results)
    if unified_nlp_analytics:
        unified_nlp_analytics.set_context(df, analysis_results)

    chat_key = f"{user_id}_{file_id}"
    if chat_key not in chat_histories:
        chat_histories[chat_key] = []

    return {
        'results': analysis_results,
        'analysis_mode': analysis_mode,
        'capabilities': capabilities,
        'analysis_plan': analysis_plan,
        'mapped_columns': dataset.get('mapped_columns', {}),
        'source_columns': dataset.get('source_columns', []),
        'mapping_issues': dataset.get('mapping_issues', []),
        'mapping_confidence': dataset.get('mapping_confidence', 'HIGH'),
        'data_quality': data_quality,
        'insights': analysis_results.get('insights', []),
        'suggested_questions': suggested_questions,
        'predefined_questions': unified_nlp_analytics.get_predefined_questions() if unified_nlp_analytics else chatbot_service.get_predefined_questions()
    }


def _run_async_analysis_job(job_id):
    """Background worker for async analysis jobs with retry and timeout policy."""
    _set_job_state(job_id, status='running', started_at=_now_iso())

    with analysis_jobs_lock:
        job = analysis_jobs.get(job_id, {}).copy()

    if not job:
        return

    user_id = job.get('user_id')
    file_id = job.get('file_id')
    timeout_seconds = int(job.get('timeout_seconds', ANALYSIS_JOB_TIMEOUT_SECONDS))
    max_retries = int(job.get('max_retries', ANALYSIS_JOB_MAX_RETRIES))

    attempt = 0
    while attempt <= max_retries:
        attempt += 1
        _set_job_state(job_id, attempt=attempt)
        started = time.time()

        try:
            payload = _run_analysis_pipeline(user_id, file_id)
            elapsed = time.time() - started
            if elapsed > timeout_seconds:
                raise TimeoutError(f'Analysis exceeded timeout of {timeout_seconds} seconds')

            _set_job_state(
                job_id,
                status='completed',
                completed_at=_now_iso(),
                duration_seconds=round(elapsed, 3),
                result={
                    'analysis_mode': payload.get('analysis_mode'),
                    'capabilities': payload.get('capabilities', {}),
                    'analysis_plan': payload.get('analysis_plan', {}),
                    'mapped_columns': payload.get('mapped_columns', {}),
                    'source_columns': payload.get('source_columns', []),
                    'mapping_issues': payload.get('mapping_issues', []),
                    'mapping_confidence': payload.get('mapping_confidence', 'HIGH'),
                    'data_quality': payload.get('data_quality', {}),
                    'insights': payload.get('insights', []),
                    'results': payload.get('results', {}),
                    'predefined_questions': payload.get('predefined_questions', []),
                    'suggested_questions': payload.get('suggested_questions', [])
                },
                error=None
            )
            return

        except Exception as e:
            if attempt > max_retries:
                _set_job_state(
                    job_id,
                    status='failed',
                    completed_at=_now_iso(),
                    error=str(e)
                )
                return
            _set_job_state(job_id, status='retrying', error=str(e))


def initialize_services(models_path, gemini_api_key=None, mapper_confidence_threshold=0.55):
    """Initialize services with configurations"""
    global data_processor, chatbot_service, unified_nlp_analytics, team4_visualization_adapter
    
    data_processor = DataProcessor(models_path, mapper_confidence_threshold=mapper_confidence_threshold)
    chatbot_service = ChatbotService(gemini_api_key)
    unified_nlp_analytics = initialize_unified_service(gemini_api_key=gemini_api_key)
    team4_visualization_adapter = initialize_team4_adapter()
    
    print("✅ Services initialized")
    print("✅ Unified NLP + Analytics Engine initialized")
    print(f"✅ Team4 visualization integration: {'Enabled' if team4_visualization_adapter and team4_visualization_adapter.available else 'Partial/Unavailable'}")


@analysis_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle tabular dataset upload (csv/excel/json/parquet)."""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if file is provided
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No file provided'
            }), 400
        
        file = request.files['file']
        dataset_name = request.form.get('dataset_name', file.filename)
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            }), 400
        
        # Validate file extension
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({
                'success': False,
                'message': f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            }), 400
        
        # Create upload directory if not exists
        upload_folder = os.path.join(os.path.dirname(__file__), '..', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generate unique filename
        file_id = secrets.token_hex(8)
        filename = secure_filename(f"{file_id}_{file.filename}")
        filepath = os.path.join(upload_folder, filename)
        
        # Save file
        file.save(filepath)
        
        # Load and validate data
        result = data_processor.load_user_data(filepath)
        
        if not result['success']:
            os.remove(filepath)  # Delete invalid file
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
        
        # Store dataframe in memory
        if user_id not in user_datasets:
            user_datasets[user_id] = {}
        
        user_datasets[user_id][file_id] = {
            'dataframe': result['dataframe'],
            'raw_dataframe': result.get('raw_dataframe'),
            'filepath': filepath,
            'filename': dataset_name,
            'uploaded_at': datetime.now().isoformat(),
            'row_count': result['row_count'],
            'columns': result['columns'],
            'source_columns': result.get('source_columns', []),
            'mapped_columns': result.get('mapped_columns', {}),
            'encoding': result.get('encoding', 'auto'),
            'format': result.get('format', ext.replace('.', '')),
            'mode': result.get('mode', 'full_analytics'),
            'capabilities': result.get('capabilities', {}),
            'profile': result.get('profile', {}),
            'mapping_issues': result.get('mapping_issues', []),
            'mapping_confidence': result.get('mapping_confidence', 'HIGH'),
            'data_quality': result.get('data_quality', {}),
            'insights': result.get('insights', []),
            'data_health_snapshot': result.get('data_health_snapshot', {}),
            'analysis_plan': result.get('analysis_plan', {}),
            'exploratory_summary': result.get('exploratory_summary', {}),
            'mapping_suggestions': result.get('mapping_suggestions', {})
        }

        preview = build_preview_payload(result['dataframe'])
        
        # Clear previous analyses for this user
        if user_id in user_analyses:
            del user_analyses[user_id]
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file_id': file_id,
            'dataset_name': dataset_name,
            'row_count': result['row_count'],
            'columns': result['columns'],
            'source_columns': result.get('source_columns', []),
            'mapped_columns': result.get('mapped_columns', {}),
            'encoding': result.get('encoding', 'auto'),
            'format': result.get('format', ext.replace('.', '')),
            'mode': result.get('mode', 'full_analytics'),
            'capabilities': result.get('capabilities', {}),
            'analysis_plan': result.get('analysis_plan', {}),
            'mapping_issues': result.get('mapping_issues', []),
            'mapping_confidence': result.get('mapping_confidence', 'HIGH'),
            'data_quality': result.get('data_quality', {}),
            'insights': result.get('insights', []),
            'data_health_snapshot': result.get('data_health_snapshot', {}),
            'preview': preview,
            'mapping_suggestions': result.get('mapping_suggestions', {}),
            'exploratory_summary': result.get('exploratory_summary', {})
        }), 201
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Upload error: {str(e)}'
        }), 500


@analysis_bp.route('/profile/<file_id>', methods=['GET'])
def get_dataset_profile(file_id):
    """Return dataset profiling details and analysis capability matrix."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id

        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404

        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe']
        source_columns = dataset.get('source_columns', list(df.columns))
        mapped_columns = dataset.get('mapped_columns', {})

        profile = data_processor.profile_dataset(df, source_columns, mapped_columns)
        data_health_snapshot = dataset.get('data_health_snapshot') or data_processor.build_data_health_snapshot(
            dataset.get('raw_dataframe') if dataset.get('raw_dataframe') is not None else df
        )
        data_quality = dataset.get('data_quality') or data_quality_service.calculate(
            dataset.get('raw_dataframe') if dataset.get('raw_dataframe') is not None else df
        )
        insights = dataset.get('insights') or insight_builder.build(df, data_quality, {'analysis_mode': dataset.get('mode')})

        return jsonify({
            'success': True,
            'file_id': file_id,
            'dataset_name': dataset.get('filename', 'uploaded_dataset'),
            'format': dataset.get('format', 'csv'),
            'encoding': dataset.get('encoding', 'auto'),
            'profile': profile,
            'mapping_issues': dataset.get('mapping_issues', profile.get('mapping_issues', [])),
            'mapping_confidence': dataset.get('mapping_confidence', profile.get('mapping_confidence', 'HIGH')),
            'data_quality': data_quality,
            'insights': insights,
            'data_health_snapshot': data_health_snapshot,
            'capabilities': profile.get('capabilities', {}),
            'analysis_plan': profile.get('analysis_plan', {})
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Profile error: {str(e)}'
        }), 500


@analysis_bp.route('/preview/<file_id>', methods=['GET'])
def get_dataset_preview(file_id):
    """Return first N rows for quick UI preview after upload."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id

        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404

        try:
            rows = int(request.args.get('rows', 10))
        except ValueError:
            rows = 10

        rows = max(1, min(rows, 50))

        dataset = user_datasets[user_id][file_id]
        preview = build_preview_payload(dataset['dataframe'], rows)

        return jsonify({
            'success': True,
            'file_id': file_id,
            'dataset_name': dataset.get('filename', 'uploaded_dataset'),
            'preview': preview,
            'mapped_columns': dataset.get('mapped_columns', {}),
            'source_columns': dataset.get('source_columns', [])
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Preview error: {str(e)}'
        }), 500


@analysis_bp.route('/mapping-suggestions/<file_id>', methods=['GET'])
def get_mapping_suggestions(file_id):
    """Return confidence-scored auto-remap suggestions for canonical columns."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id

        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404

        dataset = user_datasets[user_id][file_id]
        df_for_suggestions = dataset.get('raw_dataframe') if dataset.get('raw_dataframe') is not None else dataset['dataframe']
        suggestions = data_processor.suggest_mapping_candidates(df_for_suggestions, top_n=3)

        return jsonify({
            'success': True,
            'file_id': file_id,
            'dataset_name': dataset.get('filename', 'uploaded_dataset'),
            'suggestions': suggestions,
            'mapped_columns': dataset.get('mapped_columns', {}),
            'source_columns': dataset.get('source_columns', [])
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Mapping suggestion error: {str(e)}'
        }), 500


@analysis_bp.route('/remap/<file_id>', methods=['POST'])
def remap_dataset_columns(file_id):
    """Apply manual canonical mapping (canonical -> source column) and re-validate dataset."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id

        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404

        payload = request.get_json() or {}
        mapping = payload.get('mapping', {})

        if not mapping or not isinstance(mapping, dict):
            return jsonify({
                'success': False,
                'message': 'Mapping payload is required. Expected: {"mapping": {"Customer ID": "<source_col>", "Date": "<source_col>", "Total Amount": "<source_col>"}}'
            }), 400

        dataset = user_datasets[user_id][file_id]
        raw_df = dataset.get('raw_dataframe')
        if raw_df is None:
            # Fallback safety if legacy upload data exists without raw dataframe.
            raw_df, _ = data_processor._read_tabular_with_fallbacks(dataset['filepath'])

        remap_result = data_processor.apply_manual_mapping(raw_df, mapping)
        if not remap_result.get('success'):
            return jsonify({
                'success': False,
                'message': remap_result.get('message', 'Manual mapping failed')
            }), 400

        dataset['dataframe'] = remap_result['dataframe']
        dataset['raw_dataframe'] = raw_df
        dataset['columns'] = list(remap_result['dataframe'].columns)
        dataset['mapped_columns'] = remap_result.get('mapped_columns', mapping)
        dataset['source_columns'] = list(raw_df.columns)
        dataset['profile'] = remap_result.get('profile', {})
        dataset['mapping_issues'] = remap_result.get('mapping_issues', [])
        dataset['mapping_confidence'] = remap_result.get('mapping_confidence', 'HIGH')
        dataset['data_quality'] = data_quality_service.calculate(raw_df)
        dataset['insights'] = insight_builder.build(remap_result['dataframe'], dataset['data_quality'], {})
        dataset['capabilities'] = remap_result.get('capabilities', {})
        dataset['analysis_plan'] = remap_result.get('analysis_plan', {})
        dataset['data_health_snapshot'] = data_processor.build_data_health_snapshot(raw_df)

        # Clear stale analyses because schema interpretation changed.
        if user_id in user_analyses and file_id in user_analyses[user_id]:
            del user_analyses[user_id][file_id]

        return jsonify({
            'success': True,
            'message': 'Column mapping applied successfully',
            'file_id': file_id,
            'mapped_columns': dataset['mapped_columns'],
            'profile': dataset['profile'],
            'mapping_issues': dataset.get('mapping_issues', []),
            'mapping_confidence': dataset.get('mapping_confidence', 'HIGH'),
            'data_quality': dataset.get('data_quality', {}),
            'insights': dataset.get('insights', []),
            'data_health_snapshot': dataset.get('data_health_snapshot', {}),
            'capabilities': dataset['capabilities'],
            'analysis_plan': dataset.get('analysis_plan', {})
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Remap error: {str(e)}'
        }), 500


@analysis_bp.route('/analyze/<file_id>', methods=['POST'])
def analyze_data(file_id):
    """Run full analysis on uploaded data"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if file exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        payload = _run_analysis_pipeline(user_id, file_id)

        return jsonify({
            'success': True,
            'message': 'Analysis completed successfully',
            'results': payload.get('results', {}),
            'predefined_questions': payload.get('predefined_questions', []),
            'suggested_questions': payload.get('suggested_questions', []),
            'analysis_mode': payload.get('analysis_mode'),
            'capabilities': payload.get('capabilities', {}),
            'analysis_plan': payload.get('analysis_plan', {}),
            'mapped_columns': payload.get('mapped_columns', {}),
            'source_columns': payload.get('source_columns', []),
            'mapping_issues': payload.get('mapping_issues', []),
            'mapping_confidence': payload.get('mapping_confidence', 'HIGH'),
            'data_quality': payload.get('data_quality', {}),
            'insights': payload.get('insights', [])
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Analysis error: {str(e)}'
        }), 500


@analysis_bp.route('/analyze-async/<file_id>', methods=['POST'])
def analyze_data_async(file_id):
    """Submit async analysis job and return immediately with job id."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id

        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404

        dataset = user_datasets[user_id][file_id]
        req = request.get_json(silent=True) or {}
        timeout_seconds = int(req.get('timeout_seconds', ANALYSIS_JOB_TIMEOUT_SECONDS))
        max_retries = int(req.get('max_retries', ANALYSIS_JOB_MAX_RETRIES))

        timeout_seconds = max(30, min(timeout_seconds, 900))
        max_retries = max(0, min(max_retries, 3))

        job_id = secrets.token_hex(12)
        created_at = _now_iso()

        with analysis_jobs_lock:
            analysis_jobs[job_id] = {
                'job_id': job_id,
                'status': 'queued',
                'created_at': created_at,
                'updated_at': created_at,
                'user_id': user_id,
                'file_id': file_id,
                'dataset_name': dataset.get('filename', 'uploaded_dataset'),
                'attempt': 0,
                'max_retries': max_retries,
                'timeout_seconds': timeout_seconds,
                'result': None,
                'error': None
            }

        analysis_executor.submit(_run_async_analysis_job, job_id)

        return jsonify({
            'success': True,
            'message': 'Analysis job queued',
            'job_id': job_id,
            'status': 'queued',
            'file_id': file_id,
            'dataset_name': dataset.get('filename', 'uploaded_dataset'),
            'timeout_seconds': timeout_seconds,
            'max_retries': max_retries
        }), 202

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Async submit error: {str(e)}'
        }), 500


@analysis_bp.route('/jobs/<job_id>', methods=['GET'])
def get_analysis_job_status(job_id):
    """Poll async analysis job status and result payload when completed."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id

        with analysis_jobs_lock:
            job = analysis_jobs.get(job_id)
            if not job:
                return jsonify({
                    'success': False,
                    'message': 'Job not found'
                }), 404

            if job.get('user_id') != user_id:
                return jsonify({
                    'success': False,
                    'message': 'Unauthorized for this job'
                }), 403

            payload = {
                'job_id': job.get('job_id'),
                'status': job.get('status'),
                'file_id': job.get('file_id'),
                'dataset_name': job.get('dataset_name'),
                'created_at': job.get('created_at'),
                'updated_at': job.get('updated_at'),
                'started_at': job.get('started_at'),
                'completed_at': job.get('completed_at'),
                'attempt': job.get('attempt'),
                'max_retries': job.get('max_retries'),
                'timeout_seconds': job.get('timeout_seconds'),
                'duration_seconds': job.get('duration_seconds'),
                'error': job.get('error'),
                'result': job.get('result') if job.get('status') == 'completed' else None
            }

        return jsonify({
            'success': True,
            'job': payload
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Job status error: {str(e)}'
        }), 500


@analysis_bp.route('/recent-analyses', methods=['GET'])
def get_recent_analyses():
    """Return locally persisted recent analyses (last 5) for current user."""
    try:
        user_id = session.get('user_id')

        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id

        all_recent = load_recent_analyses()
        return jsonify({
            'success': True,
            'user_id': user_id,
            'recent_analyses': all_recent.get(user_id, [])
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Recent analyses error: {str(e)}'
        }), 500


@analysis_bp.route('/dashboard-data/<file_id>', methods=['GET'])
def get_dashboard_data(file_id):
    """Get real dashboard data for visualization"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if file exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Get real analytics service
        real_analytics = get_real_analytics_service()
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe']
        capabilities = dataset.get('capabilities', {})
        analysis_plan = dataset.get('analysis_plan', data_processor.build_analysis_plan(df))
        
        # Extract real data
        kpis = real_analytics.get_real_kpis(df) if capabilities.get('kpis') else {}
        trends = real_analytics.get_revenue_trends(df, 'month') if capabilities.get('trends') else []
        top_categories = real_analytics.get_top_categories(df, top_n=4) if capabilities.get('top_categories') else []
        segments = real_analytics.get_customer_segments(df) if capabilities.get('segmentation') else {}
        
        return jsonify({
            'success': True,
            'data': {
                'kpis': kpis,
                'trends': trends,
                'top_categories': top_categories,
                'segments': segments,
                'team4_visualization': (dataset.get('team4_visualization') or (team4_visualization_adapter.build_payload(df) if team4_visualization_adapter else {'enabled': False, 'insights': [], 'charts': []})),
                'file_name': dataset.get('filename', 'dataset.csv'),
                'uploaded_at': dataset.get('uploaded_at', 'Recently'),
                'row_count': len(df),
                'columns': list(df.columns),
                'source_columns': dataset.get('source_columns', []),
                'mapped_columns': dataset.get('mapped_columns', {}),
                'capabilities': capabilities,
                'analysis_plan': analysis_plan
            }
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Dashboard data error: {str(e)}'
        }), 500


@analysis_bp.route('/team4-visualization/<file_id>', methods=['GET'])
def get_team4_visualization(file_id):
    """Return Team4 visualization payload (insights + chart paths) for uploaded dataset."""
    try:
        user_id = session.get('user_id')

        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id

        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404

        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe']

        adapter = team4_visualization_adapter or get_team4_adapter()
        payload = adapter.build_payload(df) if adapter else {
            'enabled': False,
            'message': 'Team4 visualization adapter unavailable',
            'insights': [],
            'charts': []
        }

        return jsonify({
            'success': True,
            'file_id': file_id,
            'dataset_name': dataset.get('filename', 'uploaded_dataset'),
            'team4_visualization': payload
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Team4 visualization error: {str(e)}'
        }), 500


@analysis_bp.route('/chat/<file_id>', methods=['POST'])
def chat(file_id):
    """Handle chatbot questions using unified NLP + Analytics Engine"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        # Check if analysis exists
        if user_id not in user_analyses or file_id not in user_analyses[user_id]:
            return jsonify({
                'success': False,
                'message': 'Please run analysis first'
            }), 400
        
        data = request.get_json()
        question = data.get('question', '').strip()
        use_gemini = data.get('use_gemini', False)
        
        if not question:
            return jsonify({
                'success': False,
                'message': 'Question cannot be empty'
            }), 400
        
        # Get answer using unified NLP + Analytics service (primary)
        if unified_nlp_analytics:
            latest_df = user_datasets.get(user_id, {}).get(file_id, {}).get('dataframe')
            latest_context = user_analyses[user_id][file_id]
            if latest_df is not None:
                unified_nlp_analytics.set_context(latest_df, latest_context)
            answer_result = unified_nlp_analytics.process_question(question, use_gemini=use_gemini)
        else:
            # Fallback to original chatbot service
            chatbot_service.set_data_context(user_analyses[user_id][file_id])
            answer_result = chatbot_service.process_question(question, use_gemini)
        
        # Store in chat history
        chat_key = f"{user_id}_{file_id}"
        if chat_key not in chat_histories:
            chat_histories[chat_key] = []
        
        chat_histories[chat_key].append({
            'role': 'user',
            'message': question,
            'timestamp': datetime.now().isoformat()
        })
        
        chat_histories[chat_key].append({
            'role': 'assistant',
            'message': answer_result['answer'],
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'intent': answer_result.get('intent', 'unknown'),
                'confidence': answer_result.get('confidence', 0.0),
                'source': answer_result.get('pipeline_source', answer_result.get('source', 'unknown'))
            }
        })
        
        return jsonify({
            'success': True,
            'answer': answer_result['answer'],
            'confidence': answer_result.get('confidence', 0),
            'source': answer_result.get('pipeline_source', answer_result.get('source', 'unknown')),
            'intent': answer_result.get('intent', 'unknown')
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Chat error: {str(e)}'
        }), 500


@analysis_bp.route('/generate-report/<file_id>', methods=['POST'])
def generate_report(file_id):
    """Generate and save analysis report"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        # Check if analysis exists
        if user_id not in user_analyses or file_id not in user_analyses[user_id]:
            return jsonify({
                'success': False,
                'message': 'Please run analysis first'
            }), 400
        
        analysis_results = user_analyses[user_id][file_id]
        dataset_name = user_datasets[user_id][file_id]['filename']

        request_payload = request.get_json(silent=True) or {}
        include_advanced_modules = request_payload.get('include_advanced_modules', True)
        selected_advanced_modules = request_payload.get('selected_advanced_modules', [])

        include_advanced_modules = bool(include_advanced_modules)
        if not isinstance(selected_advanced_modules, list):
            selected_advanced_modules = []
        
        # Get user info
        from auth.auth_handler import get_user
        user = get_user(user_id)
        
        # Get chat history
        chat_key = f"{user_id}_{file_id}"
        chat_log = chat_histories.get(chat_key, [])
        
        # Set report data
        report_generator.set_data(
            _build_report_payload(
                user_id,
                file_id,
                include_advanced_modules=include_advanced_modules,
                selected_advanced_modules=selected_advanced_modules
            )
        )
        
        # Generate both MD and HTML
        md_report = report_generator.generate_md_report(user, chat_log)
        html_report = report_generator.generate_html_report(user, chat_log)

        # Final cleanup pass so reports never expose deprecated advanced-module wording.
        md_report = _sanitize_report_output(md_report)
        html_report = _sanitize_report_output(html_report)
        
        # Generate unique report ID
        report_id = secrets.token_hex(8)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{report_id}_{timestamp}"
        
        # Save both formats
        md_result = report_generator.save_report(md_report, filename, 'md')
        html_result = report_generator.save_report(html_report, filename, 'html')
        
        if not md_result['success'] or not html_result['success']:
            return jsonify({
                'success': False,
                'message': 'Error saving report'
            }), 500
        
        # Add to user's report list
        report_info = {
            'report_id': report_id,
            'file_id': file_id,
            'file_path': md_result['filepath'],
            'md_file_path': md_result['filepath'],
            'html_file_path': html_result['filepath'],
            'dataset_name': dataset_name
        }
        add_report_to_user(user_id, report_info)

        preview_url = f"/api/analysis/report-preview/{report_id}"
        download_pdf_url = f"/api/analysis/report-download/{report_id}/pdf"
        
        return jsonify({
            'success': True,
            'message': 'Report generated successfully',
            'report_id': report_id,
            'file_id': file_id,
            'dataset_name': dataset_name,
            'md_file': md_result['filename'],
            'html_file': html_result['filename'],
            'preview_url': preview_url,
            'download_pdf_url': download_pdf_url,
            'download_format': 'pdf'
        }), 201
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Report generation error: {str(e)}'
        }), 500


@analysis_bp.route('/report-preview/<report_id>', methods=['GET'])
def preview_report(report_id):
    """Render a saved HTML report in-browser before PDF download."""
    try:
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401

        report_entry = _resolve_user_report(user_id, report_id)
        if not report_entry:
            return jsonify({
                'success': False,
                'message': 'Report not found'
            }), 404

        html_path = report_entry.get('html_file_path')
        if not html_path:
            base_path = report_entry.get('md_file_path') or report_entry.get('file_path', '')
            if base_path:
                html_path = os.path.splitext(base_path)[0] + '.html'

        safe_path = _ensure_report_path(html_path)
        if not safe_path or not os.path.exists(safe_path):
            return jsonify({
                'success': False,
                'message': 'Preview file not found'
            }), 404

        return send_file(safe_path, mimetype='text/html', as_attachment=False)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Report preview error: {str(e)}'
        }), 500


@analysis_bp.route('/report-download/<report_id>/<format>', methods=['GET'])
def download_report(report_id, format):
    """Download a saved report as PDF using persistent report metadata."""
    try:
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401

        output_format = (format or '').lower()
        if output_format != 'pdf':
            return jsonify({
                'success': False,
                'message': f'Invalid format: {output_format}. Use pdf only.'
            }), 400

        report_entry = _resolve_user_report(user_id, report_id)
        if not report_entry:
            return jsonify({
                'success': False,
                'message': 'Report not found'
            }), 404

        html_path = report_entry.get('html_file_path')
        if not html_path:
            base_path = report_entry.get('md_file_path') or report_entry.get('file_path', '')
            if base_path:
                html_path = os.path.splitext(base_path)[0] + '.html'

        safe_html_path = _ensure_report_path(html_path)
        if not safe_html_path or not os.path.exists(safe_html_path):
            return jsonify({
                'success': False,
                'message': 'Report file not found'
            }), 404

        stored_pdf_path = _ensure_report_path(report_entry.get('pdf_file_path'))
        derived_pdf_path = _ensure_report_path(os.path.splitext(safe_html_path)[0] + '.pdf')
        cached_pdf_path = stored_pdf_path if stored_pdf_path and os.path.exists(stored_pdf_path) else derived_pdf_path

        if cached_pdf_path and os.path.exists(cached_pdf_path):
            return send_file(
                cached_pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=_build_report_download_name(report_id, report_entry)
            )

        with open(safe_html_path, 'r', encoding='utf-8') as source:
            html_content = source.read()

        base_name = os.path.splitext(os.path.basename(safe_html_path))[0]
        pdf_result = report_generator.export_to_pdf(
            html_content,
            base_name,
            user_info={'username': user_id},
            chat_log=[]
        )

        if not pdf_result.get('success'):
            return jsonify({
                'success': False,
                'message': pdf_result.get('message', 'PDF export failed')
            }), 500

        generated_pdf_path = _ensure_report_path(pdf_result.get('filepath'))
        if not generated_pdf_path or not os.path.exists(generated_pdf_path):
            return jsonify({
                'success': False,
                'message': 'Generated PDF file not found'
            }), 500

        try:
            from auth.auth_handler import load_users, save_users

            users = load_users()
            user_reports = users.get(user_id, {}).get('reports', [])
            for item in user_reports:
                if item.get('report_id') == report_id:
                    item['pdf_file_path'] = generated_pdf_path
                    break
            save_users(users)
        except Exception:
            # Do not fail download flow if metadata persistence fails.
            pass

        return send_file(
            generated_pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=_build_report_download_name(report_id, report_entry)
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Report download error: {str(e)}'
        }), 500


@analysis_bp.route('/reports', methods=['GET'])
def get_report_history():
    """List generated reports for the authenticated user."""
    try:
        user_id = session.get('user_id')

        from auth.auth_handler import get_user

        user = get_user(user_id) or {}
        stored_reports = user.get('reports', [])

        ordered_reports = sorted(
            stored_reports,
            key=lambda item: item.get('created_at', ''),
            reverse=True
        )

        reports = []
        for item in ordered_reports:
            report_id = item.get('report_id')
            file_id = item.get('file_id')
            if not report_id:
                continue

            reports.append({
                'report_id': report_id,
                'file_id': file_id,
                'dataset_name': item.get('dataset_name'),
                'created_at': item.get('created_at'),
                'preview_url': f"/api/analysis/report-preview/{report_id}",
                'download_pdf_url': f"/api/analysis/report-download/{report_id}/pdf",
                'download_format': 'pdf'
            })

        return jsonify({
            'success': True,
            'count': len(reports),
            'reports': reports
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Report history error: {str(e)}'
        }), 500


@analysis_bp.route('/predefined-questions', methods=['GET'])
def get_predefined_questions():
    """Get list of predefined questions from unified NLP analytics"""
    if unified_nlp_analytics:
        questions = unified_nlp_analytics.get_predefined_questions()
    else:
        questions = chatbot_service.get_predefined_questions()
    
    return jsonify({
        'success': True,
        'questions': questions
    }), 200


@analysis_bp.route('/suggested-questions/<file_id>', methods=['GET'])
def get_suggested_questions(file_id):
    """Return simple capability-based suggested questions for the dataset."""
    try:
        user_id = session.get('user_id')

        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id

        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404

        dataset = user_datasets[user_id][file_id]
        capabilities = dataset.get('capabilities', {})

        return jsonify({
            'success': True,
            'file_id': file_id,
            'questions': generate_suggested_questions(capabilities),
            'capabilities': capabilities
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Suggested questions error: {str(e)}'
        }), 500


@analysis_bp.route('/insights/<file_id>', methods=['GET'])
def get_insights(file_id):
    """Get automatic insights using analytics engine and NLP"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        # Check if analysis exists
        if user_id not in user_analyses or file_id not in user_analyses[user_id]:
            return jsonify({
                'success': False,
                'message': 'Please run analysis first'
            }), 400

        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404

        dataset = user_datasets[user_id][file_id]
        analysis_payload = user_analyses[user_id][file_id]
        df = dataset.get('dataframe')

        def _extract_highlights(items):
            highlights = []
            for item in items or []:
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        highlights.append(text)
                    continue

                if not isinstance(item, dict):
                    continue

                text = str(item.get('insight', '') or item.get('message', '')).strip()
                if text:
                    metric = str(item.get('metric', '')).strip()
                    if metric:
                        highlights.append(f"{metric}: {text}")
                    else:
                        highlights.append(text)
                    continue

                insight_type = str(item.get('type', '')).replace('_', ' ').title().strip()
                payload = item.get('data') if isinstance(item.get('data'), dict) else item
                # Custom summary for business_snapshot
                if item.get('type') == 'business_snapshot' and isinstance(payload, dict):
                    kpis = payload
                    if kpis:
                        if 'total_revenue' in kpis:
                            highlights.append(f"Total Revenue: ${kpis['total_revenue']:,.0f}")
                        if 'unique_customers' in kpis:
                            highlights.append(f"Unique Customers: {kpis['unique_customers']}")
                        if 'average_order_value' in kpis:
                            highlights.append(f"Avg Order Value: ${kpis['average_order_value']:,.0f}")
                        if 'total_orders' in kpis:
                            highlights.append(f"Total Orders: {kpis['total_orders']}")
                    continue
                # Custom summary for segmentation
                if item.get('type') == 'segmentation' and isinstance(payload, dict):
                    for seg in ['Premium', 'Standard', 'Basic']:
                        segdata = payload.get(seg)
                        if segdata and isinstance(segdata, dict):
                            highlights.append(f"{seg}: {segdata.get('count',0)} customers, ${segdata.get('revenue',0):,.0f} revenue")
                    continue
                # Custom summary for churn
                if item.get('type') == 'churn_prediction' and isinstance(payload, dict):
                    if 'at_risk_count' in payload:
                        highlights.append(f"At-risk customers: {payload['at_risk_count']}")
                    if 'revenue_at_risk' in payload:
                        highlights.append(f"Revenue at risk: ${payload['revenue_at_risk']:,.0f}")
                    continue

                # Fallback: up to 3 scalar pairs
                if isinstance(payload, dict):
                    scalar_pairs = []
                    for key, value in payload.items():
                        if isinstance(value, (str, int, float, bool)) and str(value).strip():
                            scalar_pairs.append(f"{str(key).replace('_', ' ').title()}: {value}")
                        if len(scalar_pairs) >= 3:
                            break
                    if scalar_pairs:
                        prefix = f"{insight_type}: " if insight_type else ""
                        highlights.append(prefix + ' | '.join(scalar_pairs))

            deduped = []
            seen = set()
            for text in highlights:
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(text)
            return deduped
        
        if not unified_nlp_analytics:
            return jsonify({
                'success': False,
                'message': 'Analytics engine not available'
            }), 500

        # Always refresh NLP context for the active file before extracting insights.
        if df is not None:
            unified_nlp_analytics.set_context(df, analysis_payload)
        
        # Extract automatic insights
        insights_result = unified_nlp_analytics.extract_insights()

        model_highlights = _extract_highlights(insights_result.get('insights', []))
        fallback_highlights = _extract_highlights(
            analysis_payload.get('insights', []) or dataset.get('insights', [])
        )

        merged_highlights = model_highlights or fallback_highlights
        merged_highlights = merged_highlights[:12]
        source = insights_result.get('source', 'unknown') if model_highlights else 'analysis_fallback'
        
        return jsonify({
            'success': bool(merged_highlights),
            'insights': merged_highlights,
            'source': source,
            'analysis': {
                'highlights': merged_highlights,
                'source': source,
                'count': len(merged_highlights)
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Insights error: {str(e)}'
        }), 500


@analysis_bp.route('/full-report/<file_id>', methods=['GET'])
def get_full_analysis_report(file_id):
    """Get comprehensive analysis report with all insights and metrics"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        # Check if analysis exists
        if user_id not in user_analyses or file_id not in user_analyses[user_id]:
            return jsonify({
                'success': False,
                'message': 'Please run analysis first'
            }), 400
        
        if not unified_nlp_analytics:
            return jsonify({
                'success': False,
                'message': 'Analytics engine not available'
            }), 500
        
        # Generate full report
        report = unified_nlp_analytics.generate_full_analysis_report()
        
        return jsonify({
            'success': report['success'],
            'report': report
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Report error: {str(e)}'
        }), 500


@analysis_bp.route('/nlp-status', methods=['GET'])
def get_nlp_status():
    """Get status of NLP and Analytics Engine integration"""
    if not unified_nlp_analytics:
        return jsonify({
            'success': False,
            'message': 'NLP service not initialized'
        }), 500
    
    return jsonify({
        'success': True,
        'status': 'NLP & Analytics Engine integrated',
        'capabilities': {
            'intent_classification': unified_nlp_analytics.team2_available,
            'entity_extraction': unified_nlp_analytics.team2_available,
            'query_building': unified_nlp_analytics.team2_available,
            'advanced_analytics': unified_nlp_analytics.analytics_engine_available,
            'insight_generation': unified_nlp_analytics.analytics_engine_available,
            'unified_pipeline': unified_nlp_analytics.team2_available and unified_nlp_analytics.analytics_engine_available
        }
    }), 200


@analysis_bp.route('/metrics/<file_id>/<time_range>', methods=['GET'])
def get_metrics_by_time(file_id, time_range):
    """Get filtered metrics by time range (all, month, quarter, year)"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()

        required_cols = ['Date', 'Total Amount', 'Customer ID']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return jsonify({
                'success': False,
                'message': f"Metrics unavailable. Missing required columns: {', '.join(missing_cols)}"
            }), 400
        
        # Apply time filter
        if time_range != 'all':
            from datetime import datetime, timedelta
            max_date = df['Date'].max()
            
            if time_range == 'month':
                filter_date = max_date - pd.Timedelta(days=30)
            elif time_range == 'quarter':
                filter_date = max_date - pd.Timedelta(days=90)
            elif time_range == 'year':
                filter_date = max_date - pd.Timedelta(days=365)
            else:
                filter_date = df['Date'].min()
            
            df = df[df['Date'] >= filter_date]
        
        # Calculate metrics
        metrics = {
            'total_revenue': float(df['Total Amount'].sum()),
            'unique_customers': int(df['Customer ID'].nunique()),
            'average_order_value': float(df['Total Amount'].mean()),
            'total_orders': len(df),
            'date_range': {
                'start': str(df['Date'].min().date()) if len(df) > 0 else 'N/A',
                'end': str(df['Date'].max().date()) if len(df) > 0 else 'N/A'
            }
        }
        
        return jsonify({
            'success': True,
            'time_range': time_range,
            'metrics': metrics
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching metrics: {str(e)}'
        }), 500


@analysis_bp.route('/capabilities/<file_id>', methods=['GET'])
def get_capabilities(file_id):
    """Return capability matrix + analysis readiness for a dataset."""
    try:
        user_id = session.get('user_id')

        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id

        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404

        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe']
        capabilities = dataset.get('capabilities', data_processor._get_dataset_capabilities(df))
        analysis_plan = dataset.get('analysis_plan', data_processor.build_analysis_plan(df))

        return jsonify({
            'success': True,
            'file_id': file_id,
            'dataset_name': dataset.get('filename', 'uploaded_dataset'),
            'capabilities': capabilities,
            'analysis_plan': analysis_plan,
            'mapped_columns': dataset.get('mapped_columns', {}),
            'source_columns': dataset.get('source_columns', [])
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Capability error: {str(e)}'
        }), 500


# ==================== ADVANCED ANALYTICS ENDPOINTS ====================

@analysis_bp.route('/cohort-analysis/<file_id>', methods=['GET'])
def analyze_cohorts(file_id):
    """Perform cohort analysis on customer data"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe']
        
        # Get real analytics service
        real_analytics = get_real_analytics_service()
        
        # Perform cohort analysis
        cohort_result = real_analytics.analyze_customer_cohorts(df)
        
        return jsonify({
            'success': cohort_result.get('success', False),
            'message': cohort_result.get('message', ''),
            'analysis': cohort_result
        }), 200 if cohort_result.get('success') else 400
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Cohort analysis error: {str(e)}'
        }), 500


@analysis_bp.route('/geographic-analysis/<file_id>', methods=['GET'])
def analyze_geography(file_id):
    """Perform geographic analysis on data by region/location"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe']
        
        # Get real analytics service
        real_analytics = get_real_analytics_service()
        
        # Perform geographic analysis
        geo_result = real_analytics.analyze_geography(df)
        
        return jsonify({
            'success': geo_result.get('success', False),
            'message': geo_result.get('message', ''),
            'analysis': geo_result
        }), 200 if geo_result.get('success') else 400
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Geographic analysis error: {str(e)}'
        }), 500


@analysis_bp.route('/timeseries-analysis/<file_id>', methods=['GET'])
def analyze_timeseries(file_id):
    """Perform time-series decomposition (trend, seasonal, residual analysis)"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe']
        
        # Get seasonality period from query params (default 12 for monthly data = yearly)
        period = request.args.get('period', 12, type=int)
        
        # Get real analytics service
        real_analytics = get_real_analytics_service()
        
        # Perform time-series analysis
        ts_result = real_analytics.analyze_timeseries(df, period=period)
        
        return jsonify({
            'success': ts_result.get('success', False),
            'message': ts_result.get('message', ''),
            'analysis': ts_result
        }), 200 if ts_result.get('success') else 400
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Time-series analysis error: {str(e)}'
        }), 500


@analysis_bp.route('/churn-prediction/<file_id>', methods=['GET'])
def predict_churn(file_id):
    """Predict which customers are at risk of churning"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe']
        
        # Get threshold from query params (default 90 days)
        days_threshold = request.args.get('days_threshold', 90, type=int)
        
        # Get real analytics service
        real_analytics = get_real_analytics_service()
        
        # Predict churn
        churn_result = real_analytics.predict_churn(df, days_threshold=days_threshold)
        
        return jsonify({
            'success': churn_result.get('success', False),
            'message': churn_result.get('message', ''),
            'analysis': churn_result
        }), 200 if churn_result.get('success') else 400
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Churn prediction error: {str(e)}'
        }), 500


@analysis_bp.route('/sales-forecast/<file_id>', methods=['GET'])
def sales_forecast(file_id):
    """Forecast future sales using exponential smoothing"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe']
        
        # Get parameters from query params
        periods = request.args.get('periods', 30, type=int)
        
        # Get real analytics service
        real_analytics = get_real_analytics_service()
        
        # Forecast sales
        forecast_result = real_analytics.analyze_forecast(df, periods=periods)
        
        return jsonify({
            'success': forecast_result.get('success', False),
            'message': forecast_result.get('message', ''),
            'analysis': forecast_result
        }), 200 if forecast_result.get('success') else 400
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Sales forecast error: {str(e)}'
        }), 500


@analysis_bp.route('/product-affinity/<file_id>', methods=['GET'])
def analyze_product_affinity(file_id):
    """Analyze product affinity and cross-sell opportunities"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe']
        
        # Get parameters from query params
        min_support = request.args.get('min_support', 0.02, type=float)
        min_confidence = request.args.get('min_confidence', 0.3, type=float)
        
        # Get real analytics service
        real_analytics = get_real_analytics_service()
        
        # Analyze affinity
        affinity_result = real_analytics.analyze_product_affinity(
            df, 
            min_support=min_support, 
            min_confidence=min_confidence
        )
        
        return jsonify({
            'success': affinity_result.get('success', False),
            'message': affinity_result.get('message', ''),
            'analysis': affinity_result
        }), 200 if affinity_result.get('success') else 400
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Product affinity error: {str(e)}'
        }), 500


# ==================== EXPORT ENDPOINTS ====================

@analysis_bp.route('/export/<file_id>/<format>', methods=['GET'])
def export_analysis(file_id, format):
    """Download analysis report in PDF format only."""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Check if analysis exists
        if user_id not in user_analyses or file_id not in user_analyses[user_id]:
            return jsonify({
                'success': False,
                'message': 'Please run analysis first before exporting'
            }), 400
        
        # Validate format: report downloads are PDF-only.
        format = format.lower()
        if format != 'pdf':
            return jsonify({
                'success': False,
                'message': f'Invalid format: {format}. Use pdf only.'
            }), 400
        
        dataset = user_datasets[user_id][file_id]
        
        # Get chat history for context
        chat_key = f"{user_id}_{file_id}"
        chat_history = chat_histories.get(chat_key, [])
        
        # Generate filename
        base_name = dataset.get('filename', 'analysis').replace('.csv', '')
        
        try:
            # Set report data on the report generator
            report_generator.report_data = _build_report_payload(user_id, file_id)

            # Generate HTML report first, then render into PDF
            html_content = report_generator.generate_html_report(
                user_info={'username': user_id},
                chat_log=chat_history
            )

            result = report_generator.export_to_pdf(
                html_content,
                base_name,
                user_info={'username': user_id},
                chat_log=chat_history,
            )

            if not result.get('success'):
                return jsonify({
                    'success': False,
                    'message': result.get('message', 'PDF export failed')
                }), 500

            filepath = result.get('filepath')
            filename = result.get('filename')

            with open(filepath, 'rb') as f:
                file_data = io.BytesIO(f.read())

            file_data.seek(0)
            return send_file(
                file_data,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Export error: {str(e)}'
            }), 500
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error processing export request: {str(e)}'
        }), 500


@analysis_bp.route('/export-status/<file_id>/<export_id>', methods=['GET'])
def check_export_status(file_id, export_id):
    """Check status of an export (for progress tracking)"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        # In a real implementation, you would track export jobs
        # For now, return a simple status response
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'export_id': export_id,
            'file_id': file_id
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error checking export status: {str(e)}'
        }), 500


# ==================== FILTERING ENDPOINTS ====================

@analysis_bp.route('/filter/category/<file_id>', methods=['GET'])
def filter_by_category(file_id):
    """Filter analysis by product category"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Get category from query parameter
        category = request.args.get('category', '').strip()
        if not category:
            return jsonify({
                'success': False,
                'message': 'Category parameter required'
            }), 400
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        # Filter by category
        if 'Product Category' in df.columns:
            df_filtered = df[df['Product Category'].str.lower() == category.lower()]
        else:
            return jsonify({
                'success': False,
                'message': 'Product Category column not found in dataset'
            }), 400
        
        if len(df_filtered) == 0:
            return jsonify({
                'success': False,
                'message': f'No data found for category: {category}'
            }), 404
        
        # Get analytics service
        real_analytics = get_real_analytics_service()
        
        # Calculate filtered metrics
        filtered_kpis = real_analytics.get_real_kpis(df_filtered)
        filtered_trends = real_analytics.get_revenue_trends(df_filtered, 'month')
        filtered_categories = real_analytics.get_top_categories(df_filtered, top_n=10)
        filtered_segments = real_analytics.get_customer_segments(df_filtered)
        
        return jsonify({
            'success': True,
            'filter': {
                'type': 'category',
                'value': category,
                'records_matched': len(df_filtered),
                'records_total': len(df)
            },
            'kpis': filtered_kpis,
            'trends': filtered_trends,
            'categories': filtered_categories,
            'segments': filtered_segments
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Category filtering error: {str(e)}'
        }), 500


@analysis_bp.route('/filter/segment/<file_id>', methods=['GET'])
def filter_by_segment(file_id):
    """Filter analysis by customer segment"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Check if analysis has been run
        if user_id not in user_analyses or file_id not in user_analyses[user_id]:
            return jsonify({
                'success': False,
                'message': 'Please run analysis first'
            }), 400
        
        # Get segment from query parameter
        segment = request.args.get('segment', '').strip()
        if not segment:
            return jsonify({
                'success': False,
                'message': 'Segment parameter required (e.g., "Loyal Customers", "Regular Customers", "At-Risk Customers")'
            }), 400
        
        dataset = user_datasets[user_id][file_id]
        analysis = user_analyses[user_id][file_id]
        df = dataset['dataframe'].copy()

        required_cols = ['Customer ID', 'Date', 'Total Amount']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            return jsonify({
                'success': False,
                'message': f"Segment filtering unavailable. Missing required columns: {', '.join(missing_cols)}",
                'missing_columns': missing_cols
            }), 400
        
        # Calculate RFM for this dataset
        snapshot_date = df['Date'].max() + pd.Timedelta(days=1)
        rfm = df.groupby('Customer ID').agg({
            'Date': lambda x: (snapshot_date - x.max()).days,
            'Customer ID': 'size',
            'Total Amount': 'sum'
        }).rename(columns={
            'Date': 'Recency',
            'Customer ID': 'Frequency',
            'Total Amount': 'Monetary'
        })
        
        # Simple segmentation logic
        def get_segment_customers(rfm_data, segment_name):
            """Get customer IDs for a specific segment"""
            customers = []
            
            if segment_name.lower() == 'loyal customers':
                # High frequency and high monetary value
                threshold_freq = rfm_data['Frequency'].quantile(0.66)
                threshold_monetary = rfm_data['Monetary'].quantile(0.66)
                customers = rfm_data[
                    (rfm_data['Frequency'] >= threshold_freq) & 
                    (rfm_data['Monetary'] >= threshold_monetary)
                ].index.tolist()
            
            elif segment_name.lower() == 'regular customers':
                # Medium frequency and monetary
                threshold_freq_low = rfm_data['Frequency'].quantile(0.33)
                threshold_freq_high = rfm_data['Frequency'].quantile(0.66)
                threshold_monetary_low = rfm_data['Monetary'].quantile(0.33)
                threshold_monetary_high = rfm_data['Monetary'].quantile(0.66)
                customers = rfm_data[
                    ((rfm_data['Frequency'] >= threshold_freq_low) & (rfm_data['Frequency'] < threshold_freq_high)) |
                    ((rfm_data['Monetary'] >= threshold_monetary_low) & (rfm_data['Monetary'] < threshold_monetary_high))
                ].index.tolist()
            
            elif segment_name.lower() == 'at-risk customers':
                # High recency (haven't purchased recently) or low frequency
                threshold_recency = rfm_data['Recency'].quantile(0.66)
                threshold_freq = rfm_data['Frequency'].quantile(0.33)
                customers = rfm_data[
                    (rfm_data['Recency'] >= threshold_recency) | 
                    (rfm_data['Frequency'] <= threshold_freq)
                ].index.tolist()
            
            return customers
        
        segment_customers = get_segment_customers(rfm, segment)
        
        if not segment_customers:
            return jsonify({
                'success': False,
                'message': f'No customers found in segment: {segment}'
            }), 404
        
        # Filter dataframe to segment customers only
        df_filtered = df[df['Customer ID'].isin(segment_customers)]
        
        # Get analytics service
        real_analytics = get_real_analytics_service()
        
        # Calculate filtered metrics
        filtered_kpis = real_analytics.get_real_kpis(df_filtered)
        filtered_trends = real_analytics.get_revenue_trends(df_filtered, 'month')
        filtered_categories = real_analytics.get_top_categories(df_filtered, top_n=4)
        
        return jsonify({
            'success': True,
            'filter': {
                'type': 'segment',
                'value': segment,
                'customer_count': len(segment_customers),
                'records_matched': len(df_filtered),
                'records_total': len(df)
            },
            'kpis': filtered_kpis,
            'trends': filtered_trends,
            'categories': filtered_categories
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Segment filtering error: {str(e)}'
        }), 500


@analysis_bp.route('/filter/transactions/<file_id>', methods=['GET'])
def filter_transactions(file_id):
    """Get transaction-level drill-down data"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()

        required_cols = ['Date', 'Customer ID', 'Total Amount']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            return jsonify({
                'success': False,
                'message': f"Transaction drill-down unavailable. Missing required columns: {', '.join(missing_cols)}",
                'missing_columns': missing_cols
            }), 400
        
        # Get optional filters
        category = request.args.get('category', '').strip()
        customer_id = request.args.get('customer_id', '').strip()
        date_start = request.args.get('date_start', '').strip()
        date_end = request.args.get('date_end', '').strip()
        limit = request.args.get('limit', 100, type=int)
        
        # Apply filters
        if category and 'Product Category' in df.columns:
            df = df[df['Product Category'].str.lower() == category.lower()]
        
        if customer_id:
            df = df[df['Customer ID'].str.lower() == customer_id.lower()]
        
        if date_start:
            try:
                df = df[df['Date'] >= pd.to_datetime(date_start)]
            except:
                pass
        
        if date_end:
            try:
                df = df[df['Date'] <= pd.to_datetime(date_end)]
            except:
                pass
        
        if len(df) == 0:
            return jsonify({
                'success': False,
                'message': 'No transactions found matching filters'
            }), 404
        
        # Sort by date descending and limit
        df = df.sort_values('Date', ascending=False).head(limit)
        
        # Prepare transaction data
        transactions = []
        for idx, row in df.iterrows():
            transactions.append({
                'transaction_id': str(row.get('Transaction ID', 'N/A')),
                'date': str(row['Date'].date()) if 'Date' in row else 'N/A',
                'customer_id': str(row.get('Customer ID', 'N/A')),
                'category': str(row.get('Product Category', 'N/A')),
                'quantity': int(row.get('Quantity', 0)),
                'price_per_unit': float(row.get('Price per Unit', 0)),
                'total_amount': float(row.get('Total Amount', 0)),
                'gender': str(row.get('Gender', 'N/A')),
                'age': int(row.get('Age', 0)) if row.get('Age') else 0
            })
        
        # Summary stats for transactions
        summary = {
            'total_transactions': len(transactions),
            'total_revenue': float(df['Total Amount'].sum()),
            'average_transaction': float(df['Total Amount'].mean()),
            'date_range': {
                'start': str(df['Date'].min().date()),
                'end': str(df['Date'].max().date())
            }
        }
        
        # Add filters applied info
        filters_applied = {}
        if category:
            filters_applied['category'] = category
        if customer_id:
            filters_applied['customer_id'] = customer_id
        if date_start:
            filters_applied['date_start'] = date_start
        if date_end:
            filters_applied['date_end'] = date_end
        
        return jsonify({
            'success': True,
            'filters_applied': filters_applied,
            'summary': summary,
            'transactions': transactions,
            'showing': len(transactions),
            'available': len(df)
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Transaction filtering error: {str(e)}'
        }), 500


@analysis_bp.route('/filter/available-values/<file_id>', methods=['GET'])
def get_available_filter_values(file_id):
    """Get available values for filtering (categories, segments, etc.)"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        # Get available categories
        available_categories = []
        if 'Product Category' in df.columns:
            available_categories = df['Product Category'].unique().tolist()
        
        # Available segments (standard)
        available_segments = [
            'Loyal Customers',
            'Regular Customers',
            'At-Risk Customers'
        ]
        
        # Date range in dataset
        if 'Date' in df.columns:
            date_range = {
                'min': str(df['Date'].min().date()),
                'max': str(df['Date'].max().date())
            }
        else:
            date_range = {
                'min': None,
                'max': None
            }
        
        return jsonify({
            'success': True,
            'available_filters': {
                'categories': available_categories,
                'segments': available_segments,
                'date_range': date_range
            }
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching available filter values: {str(e)}'
        }), 500


# ==================== CUSTOMER LIFETIME VALUE (CLV) ENDPOINTS ====================

@analysis_bp.route('/clv/<file_id>', methods=['GET'])
def get_customer_lifetime_value(file_id):
    """Calculate and return Customer Lifetime Value (CLV) for each customer
    
    CLV is the total revenue expected from each customer over their lifetime.
    """
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        # Get analytics service
        real_analytics = get_real_analytics_service()
        
        # Calculate CLV
        clv_results = real_analytics.calculate_customer_lifetime_value(df)
        
        if not clv_results.get('success'):
            return jsonify(clv_results), 400
        
        return jsonify({
            'success': True,
            'data': clv_results
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'CLV calculation error: {str(e)}'
        }), 500


@analysis_bp.route('/clv/<file_id>/top/<int:limit>', methods=['GET'])
def get_top_clv_customers(file_id, limit):
    """Get top N customers by CLV (default limit=10)"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        if limit < 1 or limit > 100:
            return jsonify({
                'success': False,
                'message': 'Limit must be between 1 and 100'
            }), 400
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        # Get analytics service
        real_analytics = get_real_analytics_service()
        
        # Calculate CLV
        clv_results = real_analytics.calculate_customer_lifetime_value(df)
        
        if not clv_results.get('success'):
            return jsonify(clv_results), 400
        
        # Get top N customers
        top_customers = clv_results['customers'][:limit]
        
        return jsonify({
            'success': True,
            'limit': limit,
            'count': len(top_customers),
            'summary': clv_results['summary'],
            'distribution': clv_results['distribution'],
            'customers': top_customers
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching top CLV customers: {str(e)}'
        }), 500


@analysis_bp.route('/clv/<file_id>/segment/<segment_name>', methods=['GET'])
def get_clv_by_segment(file_id, segment_name):
    """Get CLV metrics for a specific customer segment"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        # Get analytics service
        real_analytics = get_real_analytics_service()
        
        # Calculate full CLV
        clv_results = real_analytics.calculate_customer_lifetime_value(df)
        
        if not clv_results.get('success'):
            return jsonify(clv_results), 400
        
        # Map segment_name to CLV tier
        segment_lower = segment_name.lower()
        if segment_lower in ['high-value', 'high_value', 'highvalue']:
            clv_threshold = 75  # Top 25%
        elif segment_lower in ['medium-value', 'medium_value', 'mediumvalue']:
            clv_threshold = 50  # Middle 50%
        elif segment_lower in ['low-value', 'low_value', 'lowvalue']:
            clv_threshold = 25  # Bottom 25%
        else:
            return jsonify({
                'success': False,
                'message': f'Unknown segment: {segment_name}. Use high-value, medium-value, or low-value'
            }), 400
        
        # Filter customers by segment
        segment_customers = [c for c in clv_results['customers'] 
                            if c['rank'] <= int(len(clv_results['customers']) * (100 - clv_threshold) / 100)]
        
        if not segment_customers:
            segment_customers = clv_results['customers'][:1] if clv_results['customers'] else []
        
        segment_clv_total = sum(c['clv'] for c in segment_customers)
        segment_clv_avg = segment_clv_total / len(segment_customers) if segment_customers else 0
        
        return jsonify({
            'success': True,
            'segment': segment_name,
            'customer_count': len(segment_customers),
            'total_clv': float(segment_clv_total),
            'average_clv': float(segment_clv_avg),
            'customers': segment_customers
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching CLV by segment: {str(e)}'
        }), 500


# ==================== REPEAT PURCHASE ANALYSIS ENDPOINTS ====================

@analysis_bp.route('/repeat-purchase/<file_id>', methods=['GET'])
def get_repeat_purchase_analysis(file_id):
    """Analyze repeat purchase frequency and customer retention patterns"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        # Get analytics service
        real_analytics = get_real_analytics_service()
        
        # Calculate repeat purchase analysis
        rpa_results = real_analytics.calculate_repeat_purchase_analysis(df)
        
        if not rpa_results.get('success'):
            return jsonify(rpa_results), 400
        
        return jsonify({
            'success': True,
            'data': rpa_results
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Repeat purchase analysis error: {str(e)}'
        }), 500


@analysis_bp.route('/repeat-purchase/<file_id>/cohort', methods=['GET'])
def get_repeat_purchase_cohorts(file_id):
    """Get repeat purchase frequency cohorts"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        # Get analytics service
        real_analytics = get_real_analytics_service()
        
        # Calculate repeat purchase analysis
        rpa_results = real_analytics.calculate_repeat_purchase_analysis(df)
        
        if not rpa_results.get('success'):
            return jsonify(rpa_results), 400
        
        return jsonify({
            'success': True,
            'summary': rpa_results['summary'],
            'frequency_cohorts': rpa_results['frequency_cohorts']
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching repeat purchase cohorts: {str(e)}'
        }), 500


# ==================== CUSTOMER HEALTH SCORE (RFM) ENDPOINTS ====================

@analysis_bp.route('/health-score/<file_id>', methods=['GET'])
def get_customer_health_score(file_id):
    """Calculate RFM-based Customer Health Score for all customers"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        # Get analytics service
        real_analytics = get_real_analytics_service()
        
        # Calculate health score
        health_results = real_analytics.calculate_customer_health_score(df)
        
        if not health_results.get('success'):
            return jsonify(health_results), 400
        
        return jsonify({
            'success': True,
            'data': health_results
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Customer health score error: {str(e)}'
        }), 500


@analysis_bp.route('/health-score/<file_id>/summary', methods=['GET'])
def get_health_score_summary(file_id):
    """Get summary of customer health scores by status"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        # Get analytics service
        real_analytics = get_real_analytics_service()
        
        # Calculate health score
        health_results = real_analytics.calculate_customer_health_score(df)
        
        if not health_results.get('success'):
            return jsonify(health_results), 400
        
        return jsonify({
            'success': True,
            'summary': health_results['summary'],
            'top_customers': health_results['top_customers'][:5],
            'at_risk_customers': health_results['at_risk_customers'][:5]
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching health score summary: {str(e)}'
        }), 500


@analysis_bp.route('/health-score/<file_id>/status/<status_type>', methods=['GET'])
def get_health_score_by_status(file_id, status_type):
    """Get customers by health status (Excellent, Good, Fair, Poor)"""
    try:
        user_id = session.get('user_id')
        
        # For development/testing - use demo user if not authenticated
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Check if dataset exists
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({
                'success': False,
                'message': 'File not found'
            }), 404
        
        # Validate status type
        valid_statuses = ['excellent', 'good', 'fair', 'poor']
        if status_type.lower() not in valid_statuses:
            return jsonify({
                'success': False,
                'message': f'Invalid status. Use one of: {", ".join(valid_statuses)}'
            }), 400
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        # Get analytics service
        real_analytics = get_real_analytics_service()
        
        # Calculate health score
        health_results = real_analytics.calculate_customer_health_score(df)
        
        if not health_results.get('success'):
            return jsonify(health_results), 400
        
        # Map status to range
        status_lower = status_type.lower()
        if status_lower == 'excellent':
            filtered_customers = [c for c in health_results['top_customers'] if c['health_status'] == 'Excellent']
        elif status_lower == 'good':
            filtered_customers = [c for c in health_results['top_customers'] if c['health_status'] == 'Good']
        elif status_lower == 'fair':
            at_risk = health_results.get('at_risk_customers', [])
            all_customers = health_results['top_customers'] + at_risk
            filtered_customers = [c for c in all_customers if c['health_status'] == 'Fair']
        else:  # poor
            filtered_customers = [c for c in health_results['at_risk_customers'] if c['health_status'] == 'Poor']
        
        return jsonify({
            'success': True,
            'status': status_type,
            'count': len(filtered_customers),
            'customers': filtered_customers
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching customers by health status: {str(e)}'
        }), 500


# ==================== ANOMALY DETECTION ENDPOINTS ====================

@analysis_bp.route('/anomalies/<file_id>', methods=['GET'])
def detect_anomalies(file_id):
    """Detect unusual spikes or drops in sales using Z-score analysis"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        sensitivity = request.args.get('sensitivity', 2.0, type=float)
        
        real_analytics = get_real_analytics_service()
        anomaly_results = real_analytics.detect_anomalies(df, sensitivity=sensitivity)
        
        if not anomaly_results.get('success'):
            return jsonify(anomaly_results), 400
        
        return jsonify({'success': True, 'data': anomaly_results}), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Anomaly detection error: {str(e)}'}), 500


# ==================== PRODUCT PERFORMANCE ENDPOINTS ====================

@analysis_bp.route('/product-performance/<file_id>', methods=['GET'])
def analyze_product_performance(file_id):
    """Analyze product performance by profitability and volume"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        real_analytics = get_real_analytics_service()
        perf_results = real_analytics.analyze_product_performance(df)
        
        if not perf_results.get('success'):
            return jsonify(perf_results), 400
        
        return jsonify({'success': True, 'data': perf_results}), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Product performance error: {str(e)}'}), 500


@analysis_bp.route('/product-performance/<file_id>/category/<category>', methods=['GET'])
def get_products_by_category(file_id, category):
    """Get products filtered by performance category (Star, Workhorse, Premium, Standard)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        valid_categories = ['Star', 'Workhorse', 'Premium', 'Standard']
        if category not in valid_categories:
            return jsonify({'success': False, 'message': f'Invalid category. Use: {", ".join(valid_categories)}'}), 400
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        real_analytics = get_real_analytics_service()
        perf_results = real_analytics.analyze_product_performance(df)
        
        if not perf_results.get('success'):
            return jsonify(perf_results), 400
        
        category_products = [p for p in perf_results['products'] if p['performance_category'] == category]
        
        return jsonify({
            'success': True,
            'category': category,
            'count': len(category_products),
            'products': category_products
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error fetching products by category: {str(e)}'}), 500


# ==================== PROMOTIONAL IMPACT ENDPOINTS ====================

@analysis_bp.route('/promotional-impact/<file_id>', methods=['GET'])
def analyze_promotional_impact(file_id):
    """Measure effectiveness of promotions/discounts on sales"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        if user_id not in user_datasets or file_id not in user_datasets[user_id]:
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        dataset = user_datasets[user_id][file_id]
        df = dataset['dataframe'].copy()
        
        real_analytics = get_real_analytics_service()
        impact_results = real_analytics.analyze_promotional_impact(df)
        
        if not impact_results.get('success'):
            return jsonify(impact_results), 400
        
        return jsonify({'success': True, 'data': impact_results}), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Promotional impact error: {str(e)}'}), 500
