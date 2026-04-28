import os
import json
from datetime import datetime
from typing import Dict, Any, List
import base64
import re
from html import unescape, escape
from io import BytesIO
import pandas as pd
import io
import contextlib

# Lazy-loaded to avoid startup warning noise when native libs are missing.
HTML = None
CSS = None
WEASYPRINT_AVAILABLE = None
import traceback

class ReportGenerator:
    """Generate executive PDF reports"""
    
    def __init__(self):
        self.report_data = {}

    def _get_team4_report_dir(self) -> str:
        return os.path.normpath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Team4_module', 'reports')
        )

    def _get_chart_entries(self) -> List[Dict[str, str]]:
        """Return chart entries from current analysis payload, fallback to known Team4 files."""
        payload_entries = []
        team4_payload = self.report_data.get('team4_visualization', {}) if isinstance(self.report_data, dict) else {}
        payload_charts = team4_payload.get('charts', []) if isinstance(team4_payload, dict) else []

        for chart in payload_charts:
            if not isinstance(chart, dict):
                continue

            path = chart.get('path')
            if not path:
                continue

            if not os.path.isabs(path):
                path = os.path.join(self._get_team4_report_dir(), path)

            if os.path.exists(path):
                title = chart.get('title') or chart.get('name', 'Chart').replace('_', ' ').title()
                payload_entries.append({'title': title, 'path': path})

        if payload_entries:
            return payload_entries

        # Legacy fallback for older analysis payloads.
        report_dir = self._get_team4_report_dir()
        known = [
            ('1_monthly_revenue.png', 'Monthly Revenue Trend'),
            ('2_country_revenue.png', 'Country-wise Revenue'),
            ('3_product_revenue.png', 'Product-wise Revenue'),
            ('4_top_customers.png', 'Top Customers by Revenue'),
        ]
        entries = []
        for fname, title in known:
            path = os.path.join(report_dir, fname)
            if os.path.exists(path):
                entries.append({'title': title, 'path': path})
        return entries

    def _image_to_data_uri(self, image_path: str) -> str:
        with open(image_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded}"

    def _ensure_weasyprint(self) -> bool:
        """Lazily import WeasyPrint with stderr suppression."""
        global HTML, CSS, WEASYPRINT_AVAILABLE

        if WEASYPRINT_AVAILABLE is not None:
            return WEASYPRINT_AVAILABLE

        try:
            with contextlib.redirect_stderr(io.StringIO()):
                from weasyprint import HTML as _HTML, CSS as _CSS
            HTML = _HTML
            CSS = _CSS
            WEASYPRINT_AVAILABLE = True
        except Exception:
            WEASYPRINT_AVAILABLE = False

        return WEASYPRINT_AVAILABLE
    
    def set_data(self, data: Dict[str, Any]):
        """Set the analysis data for report generation"""
        self.report_data = data

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _safe_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _get_dataset_summary(self) -> Dict[str, Any]:
        return self.report_data.get('dataset_summary', {}) if isinstance(self.report_data, dict) else {}

    def _get_snapshot(self) -> Dict[str, Any]:
        return self.report_data.get('business_snapshot', {}) if isinstance(self.report_data, dict) else {}

    def _get_data_quality(self) -> Dict[str, Any]:
        return self.report_data.get('data_quality', {}) if isinstance(self.report_data, dict) else {}

    def _get_mapping_summary(self) -> Dict[str, Any]:
        dataset_summary = self._get_dataset_summary()
        mapped_columns = dataset_summary.get('mapped_columns', {})
        mapped_display = ', '.join(f"{k}: {v}" for k, v in mapped_columns.items()) if mapped_columns else 'N/A'
        return {
            'mapped_columns': mapped_columns,
            'mapped_display': mapped_display,
            'mapping_confidence': self.report_data.get('mapping_confidence', 'N/A'),
            'mapping_issues': self.report_data.get('mapping_issues', []) or []
        }

    def _get_executive_insights(self) -> List[str]:
        snapshot = self._get_snapshot()
        data_quality = self._get_data_quality()
        customer_summary = self._get_customer_summary()
        top_categories = self.report_data.get('top_categories', []) if isinstance(self.report_data, dict) else []

        points = []

        quality_score = self._safe_float(data_quality.get('data_quality_score', 0))
        missing_pct = self._safe_float(data_quality.get('missing_percentage', 0))
        duplicate_pct = self._safe_float(data_quality.get('duplicate_percentage', 0))
        points.append(
            f"Data quality is {quality_score:.2f}/100, with {missing_pct:.2f}% missing values and {duplicate_pct:.2f}% duplicate rows."
        )

        total_revenue = self._safe_float(snapshot.get('total_revenue', 0))
        total_orders = self._safe_int(snapshot.get('total_orders', 0))
        avg_order_value = self._safe_float(snapshot.get('average_order_value', snapshot.get('avg_order_value', 0)))
        points.append(
            f"Revenue scale is ${total_revenue:,.2f} across {total_orders:,} orders, with an average order value of ${avg_order_value:,.2f}."
        )

        top_contributor = self._get_top_contributor_summary()
        if top_contributor:
            points.append(top_contributor)

        trend_summary = self._get_trend_summary()
        if trend_summary:
            points.append(trend_summary)
        if self._extract_trend_direction() == 'downward':
            points.append('Risk: Revenue shows a declining trend, indicating potential performance issues that should be investigated.')

        raw_insights = self.report_data.get('insights', []) if isinstance(self.report_data, dict) else []
        for item in raw_insights:
            text = str(item or '').strip()
            if text:
                points.append(text)

        cleaned = []
        seen = set()
        for item in points:
            key = item.lower()
            if key in seen:
                continue
            cleaned.append(item)
            seen.add(key)

        if len(cleaned) < 3:
            if customer_summary.get('top_customers'):
                leader = customer_summary['top_customers'][0]
                cleaned.append(
                    f"Top customer {leader.get('customer_id', 'Unknown')} generated ${self._safe_float(leader.get('total_revenue', 0)):,.2f} in revenue."
                )
            else:
                cleaned.append('The current dataset is ready for business review using the available analytics output.')

        return cleaned[:6]

    def _extract_trend_direction(self) -> str:
        trends = self.report_data.get('trends', []) if isinstance(self.report_data, dict) else []
        if len(trends) < 2:
            return 'stable'

        def _value(item):
            if not isinstance(item, dict):
                return 0.0
            for key in ['revenue', 'total_revenue', 'value', 'sales']:
                if key in item:
                    return self._safe_float(item.get(key))
            return 0.0

        first_value = _value(trends[0])
        last_value = _value(trends[-1])
        if last_value > first_value:
            return 'upward'
        if last_value < first_value:
            return 'downward'
        return 'stable'

    def _get_trend_summary(self) -> str:
        trends = self.report_data.get('trends', []) if isinstance(self.report_data, dict) else []
        if len(trends) < 2:
            return 'Trend direction is limited because only one reporting period is available.'

        first = trends[0] if isinstance(trends[0], dict) else {}
        last = trends[-1] if isinstance(trends[-1], dict) else {}
        first_label = first.get('date') or first.get('period') or 'the first period'
        last_label = last.get('date') or last.get('period') or 'the latest period'
        first_value = self._safe_float(first.get('revenue', first.get('total_revenue', first.get('value', first.get('sales', 0)))))
        last_value = self._safe_float(last.get('revenue', last.get('total_revenue', last.get('value', last.get('sales', 0)))))

        direction = self._extract_trend_direction()
        if direction == 'upward':
            return f"Trend direction is upward, with revenue rising from ${first_value:,.2f} in {first_label} to ${last_value:,.2f} in {last_label}."
        if direction == 'downward':
            return f"Trend direction is downward, with revenue moving from ${first_value:,.2f} in {first_label} to ${last_value:,.2f} in {last_label}."
        return f"Trend direction is stable, with revenue staying close between {first_label} and {last_label}."

    def _get_team4_insights(self) -> List[str]:
        payload = self.report_data.get('team4_visualization', {}) if isinstance(self.report_data, dict) else {}
        insights = payload.get('insights', []) if isinstance(payload, dict) else []
        cleaned = []
        for item in insights:
            text = str(item).strip()
            if not text:
                continue
            text = re.sub(r'^[^\w]+', '', text).strip()
            text = text.replace('nan%', 'the highest share')
            cleaned.append(text)
        return cleaned

    def _find_team4_insight(self, keywords: List[str]) -> str:
        for insight in self._get_team4_insights():
            lowered = insight.lower()
            if any(keyword in lowered for keyword in keywords):
                return insight
        return ''

    def _is_precise_contributor_insight(self, text: str) -> bool:
        if not text:
            return False
        lowered = text.lower()
        vague_tokens = [
            'top country contributes approximately',
            'top region contributes approximately',
            'highest share',
            'approximately',
        ]
        has_percentage = bool(re.search(r'\d+(\.\d+)?%', text))
        return has_percentage and not any(token in lowered for token in vague_tokens)

    def _get_top_contributor_summary(self) -> str:
        snapshot = self._get_snapshot()
        total_revenue = self._safe_float(snapshot.get('total_revenue', 0))
        top_categories = self.report_data.get('top_categories', []) if isinstance(self.report_data, dict) else []
        customer_summary = self._get_customer_summary()

        geo_insight = self._find_team4_insight(['country', 'region'])
        if self._is_precise_contributor_insight(geo_insight):
            return f"Top geographic contributor: {geo_insight}"

        if top_categories:
            top_entry = top_categories[0]
            label = top_entry.get('category') or top_entry.get('product_category') or top_entry.get('name') or 'Top category'
            revenue = self._safe_float(top_entry.get('revenue', top_entry.get('total_revenue', top_entry.get('value', 0))))
            share = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            return f"Top contributor is {label}, contributing ${revenue:,.2f} or {share:.1f}% of total revenue."

        if customer_summary.get('top_customers'):
            leader = customer_summary['top_customers'][0]
            revenue = self._safe_float(leader.get('total_revenue', 0))
            share = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            return f"Top contributor is customer {leader.get('customer_id', 'Unknown')}, contributing ${revenue:,.2f} or {share:.1f}% of total revenue."

        return ''

    def _get_top_three_customer_share(self) -> float:
        snapshot = self._get_snapshot()
        total_revenue = self._safe_float(snapshot.get('total_revenue', 0))
        top_customers = self._get_customer_summary().get('top_customers', [])
        top_three_revenue = sum(self._safe_float(item.get('total_revenue', 0)) for item in top_customers[:3])
        if total_revenue <= 0:
            return 0.0
        return (top_three_revenue / total_revenue) * 100

    def _get_precise_geography_recommendation(self) -> str:
        geo_insight = self._find_team4_insight(['country', 'region'])
        if self._is_precise_contributor_insight(geo_insight):
            return f'Use the strongest geography as a priority market, since {geo_insight.lower()}.'
        return ''

    def _get_visual_chart_insight(self, chart_title: str) -> str:
        title = (chart_title or '').lower()
        top_categories = self.report_data.get('top_categories', []) if isinstance(self.report_data, dict) else []
        customer_summary = self._get_customer_summary()

        if 'monthly' in title or 'trend' in title:
            return self._get_trend_summary()

        if 'country' in title or 'region' in title:
            geo_insight = self._find_team4_insight(['country', 'region'])
            if self._is_precise_contributor_insight(geo_insight):
                return geo_insight
            top_contributor = self._get_top_contributor_summary()
            if top_contributor:
                return top_contributor
            return 'Geographic signal: this view highlights the strongest revenue-contributing market.'

        if 'product' in title or 'category' in title:
            if top_categories:
                top_entry = top_categories[0]
                label = top_entry.get('category') or top_entry.get('product_category') or top_entry.get('name') or 'the leading category'
                value = self._safe_float(top_entry.get('revenue', top_entry.get('total_revenue', top_entry.get('value', 0))))
                total_revenue = self._safe_float(self._get_snapshot().get('total_revenue', 0))
                share = (value / total_revenue * 100) if total_revenue > 0 else 0
                return f'Category signal: {label} is the current leader with ${value:,.2f}, contributing {share:.1f}% of total revenue.'
            return 'Category signal: this chart highlights where product demand is concentrated.'

        if 'customer' in title:
            top_customers = customer_summary.get('top_customers', [])
            if top_customers:
                leader = top_customers[0]
                top_three_share = self._get_top_three_customer_share()
                return (
                    f"Customer signal: {leader.get('customer_id', 'Top customer')} leads the ranking with "
                    f"${self._safe_float(leader.get('total_revenue')):,.2f} in revenue, and the top 3 customers contribute {top_three_share:.1f}% of total revenue."
                )
            return 'Customer signal: this chart helps identify the highest-value customers.'

        if 'revenue' in title:
            return self._get_trend_summary()

        insights = self._get_executive_insights()
        return insights[0]

    def _build_visual_entries(self) -> List[Dict[str, str]]:
        entries = []
        for chart in self._get_chart_entries():
            entries.append({
                'title': chart.get('title', 'Chart'),
                'path': chart.get('path'),
                'insight': self._get_visual_chart_insight(chart.get('title', 'Chart'))
            })
        return entries

    def _get_customer_summary(self) -> Dict[str, Any]:
        summary = self.report_data.get('customer_summary', {}) if isinstance(self.report_data, dict) else {}
        snapshot = self._get_snapshot()
        segments = self.report_data.get('segments', {}) if isinstance(self.report_data, dict) else {}

        total_customers = self._safe_int(summary.get('total_customers', snapshot.get('unique_customers', 0)))
        top_customers = summary.get('top_customers', []) if isinstance(summary.get('top_customers', []), list) else []
        top_customers = top_customers[:5]

        top_segments = summary.get('top_segments', []) if isinstance(summary.get('top_segments', []), list) else []
        if not top_segments and isinstance(segments, dict):
            ranked_segments = sorted(
                segments.items(),
                key=lambda item: self._safe_float(item[1].get('total_revenue', item[1].get('revenue', 0))),
                reverse=True
            )
            top_segments = [
                {
                    'name': name,
                    'count': self._safe_int(data.get('count', data.get('customers', 0))),
                    'total_revenue': self._safe_float(data.get('total_revenue', data.get('revenue', 0)))
                }
                for name, data in ranked_segments[:5]
            ]

        return {
            'total_customers': total_customers,
            'top_customers': top_customers,
            'top_segments': top_segments[:5]
        }

    def _get_recommendations(self) -> List[str]:
        recommendations = []
        data_quality = self._get_data_quality()
        mapping = self._get_mapping_summary()
        customer_summary = self._get_customer_summary()
        top_categories = self.report_data.get('top_categories', []) if isinstance(self.report_data, dict) else []

        quality_score = self._safe_float(data_quality.get('data_quality_score', 100))
        if quality_score < 90:
            recommendations.append(
                f'Prioritize data cleanup before the next decision cycle, because the current quality score is only {quality_score:.2f}/100.'
            )

        if mapping.get('mapping_confidence') != 'HIGH' or mapping.get('mapping_issues'):
            recommendations.append(
                'Resolve the current mapping warnings before relying on customer or category level conclusions.'
            )

        trend_direction = self._extract_trend_direction()
        if trend_direction == 'downward':
            recommendations.append('Investigate the revenue decline immediately and review pricing, channel performance, and recent demand changes.')
        elif trend_direction == 'upward':
            recommendations.append('Double down on the factors driving the current upward trend so the recent growth continues.')

        geography_recommendation = self._get_precise_geography_recommendation()
        if geography_recommendation:
            recommendations.append(geography_recommendation)
        elif top_categories:
            top_entry = top_categories[0]
            label = top_entry.get('category') or top_entry.get('product_category') or top_entry.get('name') or 'the top category'
            revenue = self._safe_float(top_entry.get('revenue', top_entry.get('total_revenue', top_entry.get('value', 0))))
            total_revenue = self._safe_float(self._get_snapshot().get('total_revenue', 0))
            share = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            recommendations.append(
                f'Allocate near-term commercial focus to {label}, which contributes ${revenue:,.2f} or {share:.1f}% of total revenue.'
            )

        if customer_summary.get('top_customers'):
            leader = customer_summary['top_customers'][0]
            top_three_share = self._get_top_three_customer_share()
            recommendations.append(
                f'Protect top customer {leader.get("customer_id", "Unknown")} and the leading customer tier, which together drive {top_three_share:.1f}% of total revenue.'
            )

        if not recommendations:
            recommendations.append('Continue monitoring the current metrics and refresh this report after the next major data update.')

        deduped = []
        seen = set()
        for rec in recommendations:
            key = rec.lower()
            if key in seen:
                continue
            deduped.append(rec)
            seen.add(key)
        return deduped[:5]

    def _get_meaningful_qa_entries(self, chat_log: List[Dict] = None) -> List[Any]:
        qa_entries = []
        current_q = None
        seen_pairs = set()
        ignore_tokens = [
            'no chat history available',
            'no paired q&a entries',
            'i do not have enough',
            'please upload',
        ]

        for item in (chat_log or [])[-20:]:
            role = item.get('role')
            message = str(item.get('message', '')).strip()
            if role == 'user':
                current_q = message
            elif role == 'assistant' and current_q:
                normalized_answer = message.lower()
                pair_key = (current_q.lower(), normalized_answer)
                if (
                    len(message) >= 20
                    and pair_key not in seen_pairs
                    and not any(token in normalized_answer for token in ignore_tokens)
                ):
                    qa_entries.append((current_q, message))
                    seen_pairs.add(pair_key)
                current_q = None

        return qa_entries[:5]

    def _get_advanced_outputs(self) -> Dict[str, Any]:
        payload = self.report_data.get('advanced_outputs', {}) if isinstance(self.report_data, dict) else {}
        return payload if isinstance(payload, dict) else {}

    def _advanced_module_title(self, module_key: str) -> str:
        title_map = {
            'cohort': 'Cohort Analysis',
            'cohort-analysis': 'Cohort Analysis',
            'geographic': 'Geographic Analysis',
            'geographic-analysis': 'Geographic Analysis',
            'timeseries': 'Timeseries Analysis',
            'timeseries-analysis': 'Timeseries Analysis',
            'churn': 'Churn Prediction',
            'churn-prediction': 'Churn Prediction',
            'forecast': 'Sales Forecast',
            'sales-forecast': 'Sales Forecast',
            'affinity': 'Product Affinity',
            'product-affinity': 'Product Affinity',
            'clv': 'Customer Lifetime Value',
            'repeatpurchase': 'Repeat Purchase',
            'repeat-purchase': 'Repeat Purchase',
            'healthscore': 'Health Score',
            'health-score': 'Health Score',
            'anomalies': 'Anomalies',
            'productperformance': 'Product Performance',
            'product-performance': 'Product Performance',
            'promotionalimpact': 'Promotional Impact',
            'promotional-impact': 'Promotional Impact'
        }
        normalized = ''.join(ch for ch in str(module_key or '').lower() if ch.isalnum() or ch == '-')
        return title_map.get(normalized, str(module_key or 'Advanced Module').replace('_', ' ').replace('-', ' ').title())

    def _extract_advanced_payload(self, module_payload: Any) -> Any:
        if isinstance(module_payload, dict):
            analysis_payload = module_payload.get('analysis')
            if isinstance(analysis_payload, dict) and analysis_payload:
                return analysis_payload

            # Keep full payload when it already looks like an advanced analytics result.
            direct_result_keys = {
                'summary', 'statistics', 'effectiveness', 'insights', 'forecast', 'rules',
                'cohorts', 'regions', 'products', 'at_risk_customers', 'anomalies', 'components'
            }
            if any(key in module_payload for key in direct_result_keys):
                return module_payload

            for key in ['data', 'metrics', 'results', 'cohorts', 'anomalies', 'recommendations', 'insights']:
                if key in module_payload and module_payload.get(key) not in (None, ''):
                    return module_payload.get(key)
        return module_payload

    def _value_to_text(self, value: Any, limit: int = 180) -> str:
        if value is None:
            return 'N/A'
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, (int, bool)):
            return str(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return 'N/A'
            return text[:limit] + ('...' if len(text) > limit else '')
        if isinstance(value, (list, dict)):
            try:
                serialized = json.dumps(value, ensure_ascii=False)
            except Exception:
                serialized = str(value)
            serialized = serialized.strip()
            if not serialized:
                return 'N/A'
            return serialized[:limit] + ('...' if len(serialized) > limit else '')
        text = str(value).strip()
        if not text:
            return 'N/A'
        return text[:limit] + ('...' if len(text) > limit else '')

    def _build_advanced_rows(self, payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            rows = [item for item in payload if isinstance(item, dict)]
            if rows:
                return rows[:20]

        if isinstance(payload, dict):
            for key in ['rows', 'table', 'data', 'results', 'analysis', 'cohorts', 'items', 'predictions']:
                value = payload.get(key)
                if isinstance(value, list):
                    rows = [item for item in value if isinstance(item, dict)]
                    if rows:
                        return rows[:20]

            nested_rows = []
            for item_key, item_value in payload.items():
                if isinstance(item_value, dict):
                    row = {'name': item_key}
                    for k, v in item_value.items():
                        if isinstance(v, (str, int, float, bool)) or v is None:
                            row[k] = v
                    if len(row) > 1:
                        nested_rows.append(row)
            if nested_rows:
                return nested_rows[:20]

        return []

    def _build_advanced_scalar_pairs(self, payload: Any) -> List[Any]:
        if not isinstance(payload, dict):
            return []

        status_keys = {'success', 'message', 'status'}
        pairs = []
        for key, value in payload.items():
            normalized_key = ''.join(ch for ch in str(key).lower() if ch.isalnum())
            if normalized_key in status_keys:
                continue

            if isinstance(value, (str, int, float, bool)) or value is None:
                if isinstance(value, str) and self._looks_structured_text(value):
                    continue
                pairs.append((key, value))
        return pairs[:12]

    def _collect_advanced_metric_pairs(self, payload: Any, prefix: str = '', depth: int = 0, max_depth: int = 2) -> List[Any]:
        if not isinstance(payload, dict) or depth > max_depth:
            return []

        pairs = []
        for key, value in payload.items():
            key_text = str(key).strip()
            if not key_text:
                continue

            normalized_key = ''.join(ch for ch in key_text.lower() if ch.isalnum())
            if normalized_key in {'success', 'message', 'status'}:
                continue

            clean_key = key_text.replace('_', ' ').title()
            label = f"{prefix} {clean_key}".strip() if prefix else clean_key

            if isinstance(value, dict) and depth < max_depth:
                pairs.extend(self._collect_advanced_metric_pairs(value, label, depth=depth + 1, max_depth=max_depth))
                continue

            if isinstance(value, (str, int, float, bool)) or value is None:
                if isinstance(value, str):
                    text = value.strip()
                    if not text or self._looks_structured_text(text):
                        continue
                pairs.append((label, value))

        return pairs

    def _build_advanced_insight_points(self, payload: Any, max_points: int = 2) -> List[str]:
        if not isinstance(payload, dict):
            return []

        insights = payload.get('insights', [])
        if not isinstance(insights, list):
            return []

        points = []
        for item in insights:
            text = str(item or '').strip()
            if not text:
                continue
            text = re.sub(r'^[^\w]+', '', text).strip()
            if not text:
                continue
            points.append(text)
            if len(points) >= max_points:
                break

        return points

    def _build_markdown_table(self, rows: List[Dict[str, Any]]) -> List[str]:
        if not rows:
            return []

        columns = self._collect_advanced_columns(rows, row_limit=20, max_columns=8)
        if not columns:
            return []

        header = '| ' + ' | '.join(str(col).replace('|', '/').strip() for col in columns) + ' |'
        divider = '| ' + ' | '.join(['---'] * len(columns)) + ' |'

        lines = [header, divider]
        for row in rows[:20]:
            rendered = []
            for column in columns:
                rendered.append(self._advanced_cell_text(row.get(column, 'N/A')).replace('|', '/'))
            lines.append('| ' + ' | '.join(rendered) + ' |')
        return lines

    def _collect_advanced_columns(self, rows: List[Dict[str, Any]], row_limit: int = 20, max_columns: int = 8) -> List[str]:
        if not rows:
            return []

        sampled_rows = [row for row in rows[:row_limit] if isinstance(row, dict)]
        columns: List[str] = []
        for row in sampled_rows:
            for key in row.keys():
                if key not in columns:
                    columns.append(key)

        def has_scalar_value(column: str) -> bool:
            for row in sampled_rows:
                value = row.get(column)
                if value is None:
                    continue
                if isinstance(value, str):
                    if self._looks_structured_text(value):
                        continue
                    return True
                if isinstance(value, (int, float, bool)):
                    return True
            return False

        filtered_columns = [column for column in columns if has_scalar_value(column)]
        return filtered_columns[:max_columns]

    def _looks_structured_text(self, value: str) -> bool:
        text = str(value).strip()
        if not text:
            return False

        if (text.startswith('{') and text.endswith('}')) or (text.startswith('[') and text.endswith(']')):
            return True

        return ('{"' in text or "['" in text or '&quot;' in text) and (':' in text or ',' in text)

    def _advanced_cell_text(self, value: Any) -> str:
        if value is None:
            return 'N/A'
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, (int, bool)):
            return str(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return 'N/A'
            if self._looks_structured_text(text):
                return 'Structured text omitted'
            max_len = 120
            return text[:max_len] + ('...' if len(text) > max_len else '')
        if isinstance(value, list):
            return f"{len(value)} item(s)"
        if isinstance(value, dict):
            return f"{len(value.keys())} field(s)"
        return 'Structured value omitted'

    def _should_render_advanced_table(self, rows: List[Dict[str, Any]]) -> bool:
        if not rows:
            return False

        columns = self._collect_advanced_columns(rows, row_limit=20, max_columns=20)
        return len(rows) <= 8 and len(columns) <= 6

    def _build_advanced_summary_points(self, payload: Any, rows: List[Dict[str, Any]], module_message: str = '') -> List[str]:
        points: List[str] = []
        seen = set()

        def add_point(label: str, value: Any):
            if not label:
                return
            rendered = f"{label}: {self._value_to_text(value)}"
            key = rendered.lower()
            if key in seen:
                return
            seen.add(key)
            points.append(rendered)

        candidate_sections = []
        if isinstance(payload, dict):
            for section_key in ['summary', 'effectiveness', 'statistics', 'distribution', 'analysis_period']:
                section_value = payload.get(section_key)
                if isinstance(section_value, dict):
                    candidate_sections.append((section_key, section_value))

            candidate_sections.append(('payload', payload))

        for _, section_payload in candidate_sections:
            for label, value in self._collect_advanced_metric_pairs(section_payload, max_depth=2):
                add_point(label, value)
                if len(points) >= 4:
                    break
            if len(points) >= 4:
                break

        if len(points) < 4:
            for insight in self._build_advanced_insight_points(payload, max_points=2):
                key = insight.lower()
                if key in seen:
                    continue
                points.append(insight)
                seen.add(key)
                if len(points) >= 4:
                    break

        if not points:
            scalar_pairs = self._build_advanced_scalar_pairs(payload)
            for key, value in scalar_pairs[:3]:
                clean_key = str(key).replace('_', ' ').title()
                add_point(clean_key, value)

        if not points and rows:
            sampled_columns = self._collect_advanced_columns(rows, row_limit=20, max_columns=20)
            points.append(f"Sample output includes {len(rows)} row(s) across {len(sampled_columns)} field(s).")

        if not points and module_message:
            message_text = str(module_message).strip()
            is_generic_completion = bool(re.search(r'\b(completed|successful|successfully)\b', message_text, flags=re.IGNORECASE))
            if message_text and not is_generic_completion:
                points.append(message_text)

        return points

    def _render_advanced_markdown_section(self) -> List[str]:
        advanced_outputs = self._get_advanced_outputs()
        if not advanced_outputs:
            return ['No data for analysis for this module in the uploaded dataset.']

        lines = []
        for module_key, module_payload in advanced_outputs.items():
            lines.append(f"### {self._advanced_module_title(module_key)}")

            payload_wrapper = module_payload if isinstance(module_payload, dict) else {}
            module_success = bool(payload_wrapper.get('success', True))
            module_message = str(payload_wrapper.get('message', '')).strip()

            if not module_success:
                lines.append('- No data for analysis for this module in the uploaded dataset.')
                lines.append('')
                continue

            payload = self._extract_advanced_payload(module_payload)
            rows = self._build_advanced_rows(payload)
            summary_points = self._build_advanced_summary_points(payload, rows, module_message)

            if summary_points:
                for point in summary_points:
                    lines.append(f"- {point}")
            else:
                lines.append('- No data for analysis for this module in the uploaded dataset.')

            if rows and self._should_render_advanced_table(rows):
                lines.append('')
                lines.append('#### Sample Table')
                lines.extend(self._build_markdown_table(rows))

            lines.append('')

        return lines

    def _render_advanced_html_section(self) -> str:
        advanced_outputs = self._get_advanced_outputs()
        if not advanced_outputs:
            return '<p>No data for analysis for this module in the uploaded dataset.</p>'

        blocks = []
        for module_key, module_payload in advanced_outputs.items():
            module_title = escape(self._advanced_module_title(module_key))
            payload_wrapper = module_payload if isinstance(module_payload, dict) else {}
            module_success = bool(payload_wrapper.get('success', True))
            module_message = str(payload_wrapper.get('message', '')).strip()
            payload = self._extract_advanced_payload(module_payload)
            rows = self._build_advanced_rows(payload)
            summary_points = self._build_advanced_summary_points(payload, rows, module_message)

            block = [f'<article class="advanced-module-card"><h3 class="advanced-module-title">{module_title}</h3>']

            if not module_success:
                block.append('<p>No data for analysis for this module in the uploaded dataset.</p>')
                block.append('</article>')
                blocks.append(''.join(block))
                continue

            if summary_points:
                block.append('<ul class="summary-list">')
                for point in summary_points:
                    block.append(f'<li>{escape(point)}</li>')
                block.append('</ul>')
            else:
                block.append('<p>No data for analysis for this module in the uploaded dataset.</p>')
                block.append('</article>')
                blocks.append(''.join(block))
                continue

            if rows and self._should_render_advanced_table(rows):
                columns = self._collect_advanced_columns(rows, row_limit=20, max_columns=8)
                if columns:
                    block.append('<div class="advanced-table-wrap"><table class="data-table">')
                    block.append('<thead><tr>')
                    for column in columns:
                        block.append(f'<th>{escape(str(column).replace("_", " ").title())}</th>')
                    block.append('</tr></thead><tbody>')

                    for row in rows[:20]:
                        block.append('<tr>')
                        for column in columns:
                            value_text = escape(self._advanced_cell_text(row.get(column, 'N/A')))
                            block.append(f'<td>{value_text}</td>')
                        block.append('</tr>')

                    block.append('</tbody></table></div>')

            block.append('</article>')
            blocks.append(''.join(block))

        return ''.join(blocks)
    
    def generate_md_report(self, user_info: Dict[str, Any], chat_log: List[Dict] = None) -> str:
        """Generate Markdown format report"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        username = user_info.get('username', 'User')
        dataset_summary = self._get_dataset_summary()
        snapshot = self._get_snapshot()
        data_quality = self._get_data_quality()
        mapping = self._get_mapping_summary()
        customer_summary = self._get_customer_summary()
        visual_entries = self._build_visual_entries()
        qa_entries = self._get_meaningful_qa_entries(chat_log)
        recommendations = self._get_recommendations()
        advanced_section_lines = self._render_advanced_markdown_section()
        avg_order_value = self._safe_float(snapshot.get('average_order_value', snapshot.get('avg_order_value', 0)))
        date_range = snapshot.get('date_range', {}) if isinstance(snapshot.get('date_range', {}), dict) else {}

        md_lines = [
            '# EXECUTIVE BUSINESS ANALYSIS REPORT',
            '',
            f'**Generated**: {timestamp}  ',
            f'**User**: {username}  ',
            '**Report Type**: Comprehensive Analytics & Insights',
            '',
            '---',
            '',
            '## 1. Executive Summary',
            '',
        ]

        for insight in self._get_executive_insights():
            md_lines.append(f'- {insight}')

        md_lines.extend([
            '',
            '---',
            '',
            '## 2. Data Quality + Mapping',
            '',
            '| Field | Value |',
            '|------|-------|',
            f"| Data Quality Score | {self._safe_float(data_quality.get('data_quality_score', 0)):.2f}/100 |",
            f"| Missing Percentage | {self._safe_float(data_quality.get('missing_percentage', 0)):.2f}% |",
            f"| Duplicate Percentage | {self._safe_float(data_quality.get('duplicate_percentage', 0)):.2f}% |",
            f"| Dataset Shape | {dataset_summary.get('row_count', data_quality.get('dataset_shape', {}).get('row_count', 'N/A'))} rows x {dataset_summary.get('column_count', data_quality.get('dataset_shape', {}).get('column_count', 'N/A'))} columns |",
            f"| Mapping Confidence | {mapping.get('mapping_confidence', 'N/A')} |",
            f"| Column Mapping | {mapping.get('mapped_display', 'N/A')} |",
            '',
            '### Mapping Warnings',
            '',
        ])

        if mapping.get('mapping_issues'):
            for issue in mapping['mapping_issues']:
                md_lines.append(f'- {issue}')
        else:
            md_lines.append('- No mapping warnings were detected.')

        md_lines.extend([
            '',
            '---',
            '',
            '## 3. Business Snapshot',
            '',
            '| Metric | Value |',
            '|--------|-------|',
            f"| Total Revenue | ${self._safe_float(snapshot.get('total_revenue', 0)):,.2f} |",
            f"| Total Orders | {self._safe_int(snapshot.get('total_orders', 0)):,} |",
            f"| Average Order Value | ${avg_order_value:,.2f} |",
            f"| Unique Customers | {self._safe_int(snapshot.get('unique_customers', 0)):,} |",
            f"| Date Range | {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')} |",
            '',
            '---',
            '',
            '## 4. Visual Insights',
            '',
        ])

        if visual_entries:
            for chart in visual_entries:
                md_lines.extend([
                    f"### {chart['title']}",
                    f"- Chart: {chart['path']}",
                    f"- Insight: {chart['insight']}",
                    '',
                ])
        else:
            md_lines.append('No chart artifacts were available at report generation time.')
            md_lines.append('')

        md_lines.extend([
            '---',
            '',
            '## 5. Customer Summary',
            '',
            f"- Total Customers: {self._safe_int(customer_summary.get('total_customers', 0)):,}",
            '',
            '### Top 5 Customers',
            '',
        ])

        if customer_summary.get('top_customers'):
            for customer in customer_summary['top_customers']:
                md_lines.append(
                    f"- {customer.get('customer_id', 'Unknown')}: ${self._safe_float(customer.get('total_revenue', 0)):,.2f} across {self._safe_int(customer.get('order_count', 0))} orders"
                )
        else:
            md_lines.append('- Top customer details were not available for this report.')

        md_lines.extend([
            '',
            '### Segment Highlights',
            '',
        ])

        if customer_summary.get('top_segments'):
            for segment in customer_summary['top_segments']:
                md_lines.append(
                    f"- {segment.get('name', 'Segment')}: {self._safe_int(segment.get('count', 0))} customers, ${self._safe_float(segment.get('total_revenue', 0)):,.2f} revenue"
                )
        else:
            md_lines.append('- Segment summary was not available for this report.')

        md_lines.extend([
            '',
            '---',
            '',
            '## 6. Recommendations',
            '',
        ])

        for idx, recommendation in enumerate(recommendations, 1):
            md_lines.append(f'{idx}. {recommendation}')

        md_lines.extend([
            '',
            '---',
            '',
            '## 7. Questions & Answers Log',
            '',
        ])

        if qa_entries:
            for idx, (question, answer) in enumerate(qa_entries, 1):
                md_lines.extend([
                    f"### Q{idx}: {question}",
                    answer,
                    '',
                ])
        else:
            md_lines.append('No meaningful Q&A entries were captured for this session.')

        md_lines.extend([
            '',
            '---',
            '',
            '## 8. Advanced Summary Results',
            '',
        ])

        md_lines.extend(advanced_section_lines)

        md_lines.extend([
            '',
            '---',
            '',
            f'**Report Generated**: {timestamp}  ',
            '**Next Review**: Recommended within 30 days',
        ])

        return '\n'.join(md_lines)
    
    def generate_html_report(self, user_info: Dict[str, Any], chat_log: List[Dict] = None) -> str:
        """Generate HTML format report"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        username = user_info.get('username', 'User')
        dataset_summary = self._get_dataset_summary()
        snapshot = self._get_snapshot()
        data_quality = self._get_data_quality()
        mapping = self._get_mapping_summary()
        customer_summary = self._get_customer_summary()
        visual_entries = self._build_visual_entries()
        qa_entries = self._get_meaningful_qa_entries(chat_log)
        recommendations = self._get_recommendations()
        advanced_section_html = self._render_advanced_html_section()
        avg_order_value = self._safe_float(snapshot.get('average_order_value', snapshot.get('avg_order_value', 0)))
        date_start = snapshot.get('date_range', {}).get('start', 'N/A') if isinstance(snapshot.get('date_range', {}), dict) else 'N/A'
        date_end = snapshot.get('date_range', {}).get('end', 'N/A') if isinstance(snapshot.get('date_range', {}), dict) else 'N/A'

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Business Analysis Report</title>
    <style>
        :root {{
            --ink: #1f2937;
            --muted: #6b7280;
            --line: #d1d5db;
            --surface: #ffffff;
            --canvas: #f8fafc;
            --accent: #0f766e;
            --soft: #f1f5f9;
        }}

        html, body {{
            margin: 0;
            padding: 0;
            background: var(--canvas);
            color: var(--ink);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.55;
        }}

        .report-shell {{
            max-width: 980px;
            margin: 24px auto;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 28px 32px;
        }}

        .report-head {{
            border-bottom: 2px solid var(--accent);
            padding-bottom: 14px;
            margin-bottom: 20px;
        }}

        .report-head h1 {{
            margin: 0;
            font-size: 2rem;
            letter-spacing: 0.2px;
        }}

        .meta-row {{
            margin-top: 8px;
            color: var(--muted);
            font-size: 0.95rem;
        }}

        .report-block {{
            margin: 20px 0;
            background: var(--soft);
            border-left: 4px solid var(--accent);
            border-radius: 8px;
            padding: 14px 16px;
        }}

        .report-block h2 {{
            margin: 0 0 10px 0;
            font-size: 1.35rem;
        }}

        .report-block h3 {{
            margin: 10px 0 8px 0;
            font-size: 1.05rem;
        }}

        .summary-list,
        .warning-list,
        .recommendation-list {{
            margin: 0;
            padding-left: 20px;
        }}

        .summary-list li,
        .warning-list li,
        .recommendation-list li {{
            margin-bottom: 8px;
        }}

        .figure-frame {{
            width: 100%;
            border: 1px solid var(--line);
            border-radius: 8px;
            margin: 6px 0 16px 0;
            background: #fff;
        }}

        .figure-insight {{
            margin: 0 0 14px 0;
            padding: 10px 12px;
            border-radius: 8px;
            background: #ffffff;
            border: 1px solid var(--line);
            color: var(--muted);
        }}

        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(180px, 1fr));
            gap: 10px;
        }}

        .kpi-card {{
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #fff;
            padding: 10px 12px;
        }}

        .kpi-name {{
            color: var(--muted);
            font-size: 0.85rem;
            text-transform: uppercase;
        }}

        .kpi-number {{
            margin-top: 4px;
            color: var(--accent);
            font-size: 1.35rem;
            font-weight: 700;
            text-align: left;
        }}

        .data-table {{
            width: 100%;
            border-collapse: collapse;
            background: #fff;
            border: 1px solid var(--line);
        }}

        .data-table th,
        .data-table td {{
            border-bottom: 1px solid var(--line);
            padding: 9px 10px;
            text-align: left !important;
            vertical-align: top;
        }}

        .data-table th {{
            background: #e2e8f0;
            font-weight: 600;
        }}

        .advanced-module-card {{
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #ffffff;
            padding: 10px;
            margin-bottom: 12px;
        }}

        .advanced-module-title {{
            margin: 0 0 10px 0;
            text-align: center;
            color: var(--ink);
        }}

        .advanced-table-wrap {{
            overflow-x: auto;
        }}

        .qa-card {{
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #fff;
            padding: 10px;
            margin-bottom: 8px;
        }}

        .qa-user {{
            border-left: 3px solid #2563eb;
            padding-left: 8px;
            margin-bottom: 8px;
        }}

        .qa-ai {{
            border-left: 3px solid #059669;
            padding-left: 8px;
        }}

        .subtle-note {{
            color: var(--muted);
            margin-top: 8px;
        }}

        .report-foot {{
            margin-top: 24px;
            padding-top: 12px;
            border-top: 1px solid var(--line);
            color: var(--muted);
            font-size: 0.9rem;
        }}

        @media print {{
            body {{
                background: #fff;
            }}

            .report-shell {{
                margin: 0;
                border: none;
                border-radius: 0;
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    <main class="report-shell">
        <header class="report-head">
            <h1>Executive Business Analysis Report</h1>
            <div class="meta-row"><strong>Generated:</strong> {timestamp}</div>
            <div class="meta-row"><strong>User:</strong> {username}</div>
            <div class="meta-row"><strong>Report Type:</strong> Comprehensive Analytics and Insights</div>
        </header>

        <section class="report-block">
            <h2>1. Executive Summary</h2>
            <ul class="summary-list">
"""
        for insight in self._get_executive_insights():
            html_content += f"""
                <li>{escape(insight)}</li>
"""

        html_content += f"""
            </ul>
        </section>

        <section class="report-block">
            <h2>2. Data Quality + Mapping</h2>
            <table class="data-table">
                <tbody>
                    <tr><th>Data Quality Score</th><td>{self._safe_float(data_quality.get('data_quality_score', 0)):.2f}/100</td></tr>
                    <tr><th>Missing Percentage</th><td>{self._safe_float(data_quality.get('missing_percentage', 0)):.2f}%</td></tr>
                    <tr><th>Duplicate Percentage</th><td>{self._safe_float(data_quality.get('duplicate_percentage', 0)):.2f}%</td></tr>
                    <tr><th>Dataset Shape</th><td>{dataset_summary.get('row_count', data_quality.get('dataset_shape', {}).get('row_count', 'N/A'))} rows x {dataset_summary.get('column_count', data_quality.get('dataset_shape', {}).get('column_count', 'N/A'))} columns</td></tr>
                    <tr><th>Mapping Confidence</th><td>{escape(str(mapping.get('mapping_confidence', 'N/A')))}</td></tr>
                    <tr><th>Column Mapping</th><td>{escape(mapping.get('mapped_display', 'N/A'))}</td></tr>
                </tbody>
            </table>
            <h3>Mapping Warnings</h3>
            <ul class="warning-list">
"""
        if mapping.get('mapping_issues'):
            for issue in mapping['mapping_issues']:
                html_content += f"""
                <li>{escape(str(issue))}</li>
"""
        else:
            html_content += """
                <li>No mapping warnings were detected.</li>
"""

        html_content += f"""
            </ul>
        </section>

        <section class="report-block">
            <h2>3. Business Snapshot</h2>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-name">Total Revenue</div>
                    <div class="kpi-number">${self._safe_float(snapshot.get('total_revenue', 0)):,.2f}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-name">Total Orders</div>
                    <div class="kpi-number">{self._safe_int(snapshot.get('total_orders', 0)):,}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-name">Average Order Value</div>
                    <div class="kpi-number">${avg_order_value:.2f}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-name">Unique Customers</div>
                    <div class="kpi-number">{self._safe_int(snapshot.get('unique_customers', 0)):,}</div>
                </div>
            </div>
            <p><strong>Date Range:</strong> {date_start} to {date_end}</p>
            <p class="subtle-note"><strong>Dataset:</strong> {escape(str(dataset_summary.get('dataset_name', 'N/A')))} | <strong>Analysis Mode:</strong> {escape(str(dataset_summary.get('analysis_mode', self.report_data.get('analysis_mode', 'N/A'))))}</p>
        </section>

        <section class="report-block">
            <h2>4. Visual Insights</h2>
"""
        if visual_entries:
            for chart in visual_entries:
                data_uri = self._image_to_data_uri(chart['path'])
                html_content += f"""
            <h3>{escape(chart['title'])}</h3>
            <img src="{data_uri}" alt="{escape(chart['title'])}" class="figure-frame" />
            <p class="figure-insight">{escape(chart['insight'])}</p>
"""
        else:
            html_content += """
            <p>No chart images were available at report generation time.</p>
"""

        html_content += f"""
        </section>

        <section class="report-block">
            <h2>5. Customer Summary</h2>
            <p><strong>Total Customers:</strong> {self._safe_int(customer_summary.get('total_customers', 0)):,}</p>
            <h3>Top 5 Customers</h3>
"""
        if customer_summary.get('top_customers'):
            html_content += """
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Customer ID</th>
                        <th>Total Revenue</th>
                        <th>Order Count</th>
                    </tr>
                </thead>
                <tbody>
"""
            for customer in customer_summary['top_customers']:
                html_content += f"""
                    <tr>
                        <td>{escape(str(customer.get('customer_id', 'Unknown')))}</td>
                        <td>${self._safe_float(customer.get('total_revenue', 0)):,.2f}</td>
                        <td>{self._safe_int(customer.get('order_count', 0))}</td>
                    </tr>
"""
            html_content += """
                </tbody>
            </table>
"""
        else:
            html_content += """
            <p>Top customer details were not available for this report.</p>
"""

        html_content += """
            <h3>Segment Highlights</h3>
"""
        if customer_summary.get('top_segments'):
            html_content += """
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Segment</th>
                        <th>Customer Count</th>
                        <th>Total Revenue</th>
                    </tr>
                </thead>
                <tbody>
"""
            for segment in customer_summary['top_segments']:
                html_content += f"""
                    <tr>
                        <td>{escape(str(segment.get('name', 'Segment')))}</td>
                        <td>{self._safe_int(segment.get('count', 0))}</td>
                        <td>${self._safe_float(segment.get('total_revenue', 0)):,.2f}</td>
                    </tr>
"""
            html_content += """
                </tbody>
            </table>
"""
        else:
            html_content += """
            <p>Segment summary was not available for this report.</p>
"""

        html_content += """
        </section>

        <section class="report-block">
            <h2>6. Recommendations</h2>
            <ol class="recommendation-list">
"""
        for recommendation in recommendations:
            html_content += f"""
                <li>{escape(recommendation)}</li>
"""
        html_content += """
            </ol>
        </section>

        <section class="report-block">
            <h2>7. Questions &amp; Answers Log</h2>
"""
        if qa_entries:
            for idx, (q, a) in enumerate(qa_entries, 1):
                html_content += f"""
            <div class="qa-card">
                <div class="qa-user"><strong>Q{idx}:</strong> {escape(q)}</div>
                <div class="qa-ai"><strong>Answer:</strong> {escape(a)}</div>
            </div>
"""
        else:
            html_content += """
            <div class="qa-card">
                <div class="qa-ai"><strong>Answer:</strong> No meaningful Q&A entries were captured for this session.</div>
            </div>
"""

        html_content += """
        </section>

        <section class="report-block">
            <h2>8. Advanced Summary Results</h2>
"""
        html_content += advanced_section_html

        html_content += """
        </section>

        <footer class="report-foot">
            <p>This report was automatically generated by Nexus AI Analytics Platform.</p>
            <p>For additional analysis, upload a new dataset or ask follow-up questions in chat.</p>
        </footer>
    </main>
</body>
</html>
"""

        return html_content
    
    def save_report(self, report_content: str, filename: str, format: str = 'md') -> Dict[str, Any]:
        """Save report to file"""
        try:
            reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            if format == 'html':
                filepath = os.path.join(reports_dir, f"{filename}.html")
            else:
                filepath = os.path.join(reports_dir, f"{filename}.md")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            return {
                'success': True,
                'filepath': filepath,
                'filename': os.path.basename(filepath)
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    def export_to_pdf(self, html_content: str, filename: str, user_info: Dict[str, Any] = None, chat_log: List[Dict] = None) -> Dict[str, Any]:
        """Export report to PDF using WeasyPrint, with ReportLab fallback."""
        try:
            if self._ensure_weasyprint():
                reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
                os.makedirs(reports_dir, exist_ok=True)

                filepath = os.path.join(reports_dir, f"{filename}.pdf")

                # Convert HTML to PDF
                HTML(string=html_content).write_pdf(filepath)

                return {
                    'success': True,
                    'filepath': filepath,
                    'filename': os.path.basename(filepath),
                    'format': 'pdf',
                    'engine': 'weasyprint'
                }

            # Native WeasyPrint libs are unavailable. Produce a real PDF via ReportLab.
            fallback = self._export_to_pdf_reportlab(html_content, filename, user_info=user_info, chat_log=chat_log)
            if fallback.get('success'):
                fallback['message'] = 'WeasyPrint native dependencies unavailable; generated PDF with ReportLab fallback.'
            return fallback
        
        except Exception as e:
            traceback.print_exc()
            return {
                'success': False,
                'message': f'PDF export error: {str(e)}'
            }

    def _html_to_plain_text(self, html_content: str) -> str:
        """Convert basic HTML content into plain text suitable for PDF paragraph rendering."""
        if not html_content:
            return ''

        # Drop non-content blocks so CSS/JS do not leak into fallback PDF text.
        text = re.sub(r'(?is)<style[^>]*>.*?</style>', ' ', html_content)
        text = re.sub(r'(?is)<script[^>]*>.*?</script>', ' ', text)

        text = re.sub(r'(?i)<br\s*/?>', '\n', text)
        text = re.sub(r'(?i)</(p|h1|h2|h3|h4|h5|h6|li|tr|table|section|div)>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = unescape(text)

        # Normalize whitespace while preserving line boundaries for readable paragraphs.
        lines = [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines()]
        return '\n'.join(line for line in lines if line)

    def _get_chart_caption(self, title: str) -> str:
        """Return a short human-readable caption for a known chart title."""
        t = (title or '').lower()
        if 'monthly' in t or 'trend' in t:
            return 'Shows how revenue changes over time and highlights growth or decline periods.'
        if 'country' in t or 'region' in t:
            return 'Compares revenue contribution across geographic markets.'
        if 'product' in t or 'category' in t:
            return 'Ranks products or categories by revenue performance.'
        if 'customer' in t:
            return 'Highlights highest-value customers by total revenue.'
        return 'Visual summary generated from the latest analyzed dataset.'

    def _export_to_pdf_reportlab(self, html_content: str, filename: str, user_info: Dict[str, Any] = None, chat_log: List[Dict] = None) -> Dict[str, Any]:
        """Fallback PDF renderer that does not require system GTK dependencies."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle

            reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            filepath = os.path.join(reports_dir, f"{filename}.pdf")

            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                leftMargin=36,
                rightMargin=36,
                topMargin=36,
                bottomMargin=36,
            )

            styles = getSampleStyleSheet()
            body_style = ParagraphStyle(
                name='BodyTextWrapped',
                parent=styles['BodyText'],
                leading=13,
                spaceAfter=6,
            )
            caption_style = ParagraphStyle(
                name='ChartCaption',
                parent=styles['BodyText'],
                textColor='#4b5563',
                leading=12,
                spaceAfter=6,
            )

            story = [
                Paragraph('Executive Business Analysis Report', styles['Title']),
                Spacer(1, 10),
            ]

            username = (user_info or {}).get('username', 'User')
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            story.append(Paragraph(f'Generated: {timestamp}', body_style))
            story.append(Paragraph(f'User: {username}', body_style))
            story.append(Paragraph('Report Type: Comprehensive Analytics and Insights', body_style))
            story.append(Spacer(1, 6))

            executive_insights = self._get_executive_insights()
            data_quality = self._get_data_quality()
            mapping = self._get_mapping_summary()
            snapshot = self._get_snapshot()
            dataset_summary = self._get_dataset_summary()
            customer_summary = self._get_customer_summary()
            recommendations = self._get_recommendations()
            qa_entries = self._get_meaningful_qa_entries(chat_log)
            visual_entries = self._build_visual_entries()

            story.append(Paragraph('1. Executive Summary', styles['Heading2']))
            for insight in executive_insights:
                story.append(Paragraph(f"• {insight}", body_style))
            story.append(Spacer(1, 8))

            story.append(Paragraph('2. Data Quality + Mapping', styles['Heading2']))
            quality_rows = [
                ['Field', 'Value'],
                ['Data Quality Score', f"{self._safe_float(data_quality.get('data_quality_score', 0)):.2f}/100"],
                ['Missing Percentage', f"{self._safe_float(data_quality.get('missing_percentage', 0)):.2f}%"],
                ['Duplicate Percentage', f"{self._safe_float(data_quality.get('duplicate_percentage', 0)):.2f}%"],
                [
                    'Dataset Shape',
                    f"{dataset_summary.get('row_count', data_quality.get('dataset_shape', {}).get('row_count', 'N/A'))} rows x "
                    f"{dataset_summary.get('column_count', data_quality.get('dataset_shape', {}).get('column_count', 'N/A'))} columns"
                ],
                ['Mapping Confidence', str(mapping.get('mapping_confidence', 'N/A'))],
                ['Column Mapping', mapping.get('mapped_display', 'N/A')],
            ]
            quality_table = Table(quality_rows, colWidths=[2.2 * inch, 4.5 * inch], repeatRows=1, hAlign='LEFT')
            quality_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#cbd5e1')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(quality_table)
            story.append(Spacer(1, 6))
            story.append(Paragraph('Mapping Warnings', styles['Heading3']))
            if mapping.get('mapping_issues'):
                for issue in mapping['mapping_issues']:
                    story.append(Paragraph(f"• {issue}", body_style))
            else:
                story.append(Paragraph('No mapping warnings were detected.', body_style))
            story.append(Spacer(1, 8))

            story.append(Paragraph('3. Business Snapshot', styles['Heading2']))
            avg_order_value = snapshot.get('average_order_value', snapshot.get('avg_order_value', 0) or 0)
            date_range = snapshot.get('date_range', {}) if isinstance(snapshot.get('date_range', {}), dict) else {}
            snapshot_data = [
                ['Metric', 'Value'],
                ['Total Revenue', f"${float(snapshot.get('total_revenue', 0) or 0):,.2f}"],
                ['Total Orders', f"{int(snapshot.get('total_orders', 0) or 0):,}"],
                ['Average Order Value', f"${float(avg_order_value):,.2f}"],
                ['Unique Customers', f"{int(snapshot.get('unique_customers', 0) or 0):,}"],
                ['Date Range', f"{date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}"],
            ]
            snapshot_table = Table(snapshot_data, colWidths=[2.5 * inch, 4.2 * inch], repeatRows=1, hAlign='LEFT')
            snapshot_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#cbd5e1')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(snapshot_table)
            story.append(Spacer(1, 10))

            story.append(Paragraph('4. Visual Insights', styles['Heading2']))
            rendered_charts = 0
            missing_charts = []

            for chart in visual_entries:
                chart_path = chart.get('path')
                chart_title = chart.get('title', 'Chart')
                safe_title = chart_title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                if not chart_path or not os.path.exists(chart_path):
                    missing_charts.append(safe_title)
                    continue

                try:
                    story.append(Paragraph(safe_title, styles['Heading3']))
                    story.append(Paragraph(chart.get('insight', self._get_chart_caption(chart_title)), caption_style))

                    image = Image(chart_path)
                    image._restrictSize(6.8 * inch, 4.5 * inch)
                    story.append(image)
                    story.append(Spacer(1, 12))
                    rendered_charts += 1
                except Exception:
                    missing_charts.append(safe_title)

            if rendered_charts == 0:
                story.append(Paragraph(
                    'No chart images were available for embedding at PDF generation time.',
                    body_style,
                ))
                story.append(Spacer(1, 8))

            if missing_charts:
                story.append(Paragraph(
                    'Some charts could not be embedded: ' + ', '.join(missing_charts),
                    body_style,
                ))
                story.append(Spacer(1, 8))

            story.append(Paragraph('5. Customer Summary', styles['Heading2']))
            story.append(Paragraph(f"Total Customers: {self._safe_int(customer_summary.get('total_customers', 0)):,}", body_style))
            story.append(Paragraph('Top 5 Customers', styles['Heading3']))
            if customer_summary.get('top_customers'):
                customer_rows = [['Customer ID', 'Total Revenue', 'Order Count']]
                for customer in customer_summary['top_customers']:
                    customer_rows.append([
                        str(customer.get('customer_id', 'Unknown')),
                        f"${self._safe_float(customer.get('total_revenue', 0)):,.2f}",
                        str(self._safe_int(customer.get('order_count', 0)))
                    ])
                customer_table = Table(customer_rows, colWidths=[2.2 * inch, 2.0 * inch, 1.5 * inch], repeatRows=1, hAlign='LEFT')
                customer_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#cbd5e1')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(customer_table)
            else:
                story.append(Paragraph('Top customer details were not available for this report.', body_style))
            story.append(Spacer(1, 8))

            story.append(Paragraph('Segment Highlights', styles['Heading3']))
            if customer_summary.get('top_segments'):
                segment_rows = [['Segment', 'Customer Count', 'Total Revenue']]
                for segment in customer_summary['top_segments']:
                    segment_rows.append([
                        str(segment.get('name', 'Segment')),
                        str(self._safe_int(segment.get('count', 0))),
                        f"${self._safe_float(segment.get('total_revenue', 0)):,.2f}",
                    ])
                segment_table = Table(segment_rows, colWidths=[2.2 * inch, 1.8 * inch, 2.0 * inch], repeatRows=1, hAlign='LEFT')
                segment_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#cbd5e1')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(segment_table)
            else:
                story.append(Paragraph('Segment summary was not available for this report.', body_style))
            story.append(Spacer(1, 8))

            story.append(Paragraph('6. Recommendations', styles['Heading2']))
            for idx, rec in enumerate(recommendations, 1):
                story.append(Paragraph(f"{idx}. {rec}", body_style))
            story.append(Spacer(1, 8))

            story.append(Paragraph('7. Questions & Answers Log', styles['Heading2']))
            if qa_entries:
                for idx, (q, a) in enumerate(qa_entries, 1):
                    safe_q = q.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    safe_a = a.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(f"Q{idx}: {safe_q}", styles['Heading3']))
                    story.append(Paragraph(f"Answer: {safe_a}", body_style))
                    story.append(Spacer(1, 6))
            else:
                story.append(Paragraph('No meaningful Q&A entries were captured for this session.', body_style))

            story.append(Spacer(1, 8))

            story.append(Paragraph('8. Advanced Summary Results', styles['Heading2']))
            advanced_outputs = self._get_advanced_outputs()
            if advanced_outputs:
                for module_key, module_payload in advanced_outputs.items():
                    module_title = self._advanced_module_title(module_key)
                    story.append(Paragraph(escape(module_title), styles['Heading3']))

                    payload_wrapper = module_payload if isinstance(module_payload, dict) else {}
                    module_success = bool(payload_wrapper.get('success', True))
                    module_message = str(payload_wrapper.get('message', '')).strip()

                    if not module_success:
                        story.append(Paragraph('No data for analysis for this module in the uploaded dataset.', body_style))
                        story.append(Spacer(1, 6))
                        continue

                    payload = self._extract_advanced_payload(module_payload)
                    rows = self._build_advanced_rows(payload)
                    summary_points = self._build_advanced_summary_points(payload, rows, module_message)

                    if summary_points:
                        for point in summary_points:
                            story.append(Paragraph(f"• {escape(str(point))}", body_style))
                    else:
                        story.append(Paragraph('No data for analysis for this module in the uploaded dataset.', body_style))

                    if rows and self._should_render_advanced_table(rows):
                        columns = self._collect_advanced_columns(rows, row_limit=20, max_columns=6)
                        if columns:
                            table_rows = [[str(col).replace('_', ' ').title() for col in columns]]
                            for row in rows[:8]:
                                table_rows.append([
                                    self._advanced_cell_text(row.get(col, 'N/A'))
                                    for col in columns
                                ])

                            column_width = max(1.0 * inch, (6.6 * inch) / len(columns))
                            advanced_table = Table(
                                table_rows,
                                colWidths=[column_width] * len(columns),
                                repeatRows=1,
                                hAlign='LEFT'
                            )
                            advanced_table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#cbd5e1')),
                                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                                ('TOPPADDING', (0, 0), (-1, -1), 4),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                            ]))
                            story.append(Spacer(1, 4))
                            story.append(advanced_table)

                    story.append(Spacer(1, 6))
            else:
                story.append(Paragraph('No data for analysis for this module in the uploaded dataset.', body_style))

            story.append(Spacer(1, 8))
            story.append(Paragraph('This report was automatically generated by Nexus AI Analytics Platform.', body_style))
            story.append(Paragraph('For additional analysis, upload a new dataset or ask follow-up questions in chat.', body_style))

            doc.build(story)

            return {
                'success': True,
                'filepath': filepath,
                'filename': os.path.basename(filepath),
                'format': 'pdf',
                'engine': 'reportlab'
            }
        except Exception as e:
            traceback.print_exc()
            return {
                'success': False,
                'message': f'ReportLab PDF export error: {str(e)}'
            }
    
    def export_to_excel(self, filename: str) -> Dict[str, Any]:
        """Export analysis results to Excel multi-sheet workbook"""
        try:
            reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            filepath = os.path.join(reports_dir, f"{filename}.xlsx")
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                
                # Sheet 1: KPIs
                kpis = self.report_data.get('kpis', {})
                kpi_df = pd.DataFrame({
                    'Metric': ['Total Revenue', 'Average Order Value', 'Total Orders', 'Unique Customers', 'Date Range Start', 'Date Range End'],
                    'Value': [
                        kpis.get('total_revenue', 0),
                        kpis.get('average_order_value', 0),
                        kpis.get('total_orders', 0),
                        kpis.get('unique_customers', 0),
                        str(kpis.get('date_range', {}).get('start', 'N/A')),
                        str(kpis.get('date_range', {}).get('end', 'N/A'))
                    ]
                })
                kpi_df.to_excel(writer, sheet_name='KPIs', index=False)
                
                # Sheet 2: Revenue Trends
                trends = self.report_data.get('trends', [])
                if trends:
                    trends_df = pd.DataFrame(trends)
                    trends_df.to_excel(writer, sheet_name='Revenue Trends', index=False)
                
                # Sheet 3: Top Categories
                top_cats = self.report_data.get('top_categories', [])
                if top_cats:
                    cats_df = pd.DataFrame(top_cats)
                    cats_df.to_excel(writer, sheet_name='Top Categories', index=False)
                
                # Sheet 4: Customer Segments
                segments = self.report_data.get('segments', {})
                if segments:
                    segment_rows = []
                    for seg_name, seg_data in segments.items():
                        segment_rows.append({
                            'Segment': seg_name,
                            'Count': seg_data.get('count', 0),
                            'Percentage': seg_data.get('percent', 0),
                            'Revenue': seg_data.get('revenue', 0),
                            'Avg Recency': seg_data.get('avg_recency', 0),
                            'Avg Frequency': seg_data.get('avg_frequency', 0),
                            'Avg Monetary': seg_data.get('avg_monetary', 0)
                        })
                    seg_df = pd.DataFrame(segment_rows)
                    seg_df.to_excel(writer, sheet_name='Customer Segments', index=False)
                
                # Sheet 5: Forecast
                forecast = self.report_data.get('forecast', {})
                if forecast.get('success'):
                    forecast_rows = []
                    for pred in forecast.get('predictions', []):
                        forecast_rows.append({
                            'Month': pred.get('month', ''),
                            'Predicted Revenue': pred.get('predicted_revenue', 0),
                            'Confidence': pred.get('confidence', 0)
                        })
                    if forecast_rows:
                        forecast_df = pd.DataFrame(forecast_rows)
                        forecast_df.to_excel(writer, sheet_name='Forecast', index=False)
                
                # Sheet 6: Churn Prediction
                churn = self.report_data.get('churn', {})
                if churn.get('success') and churn.get('at_risk_customers'):
                    churn_rows = []
                    for customer in churn.get('at_risk_customers', []):
                        churn_rows.append({
                            'Customer ID': customer.get('customer_id', ''),
                            'Risk Score': customer.get('risk_score', 0),
                            'Days Since Purchase': customer.get('days_since_purchase', 0),
                            'Customer Value': customer.get('customer_value', 'Unknown')
                        })
                    if churn_rows:
                        churn_df = pd.DataFrame(churn_rows)
                        churn_df.to_excel(writer, sheet_name='At-Risk Customers', index=False)
                
                # Sheet 7: Report Metadata
                metadata_df = pd.DataFrame({
                    'Property': ['Report Type', 'Generated Date', 'Data Rows', 'Analysis Type'],
                    'Value': [
                        'Executive Business Analysis',
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        '≈1000',
                        'Comprehensive'
                    ]
                })
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            return {
                'success': True,
                'filepath': filepath,
                'filename': os.path.basename(filepath),
                'format': 'excel'
            }
        
        except Exception as e:
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Excel export error: {str(e)}'
            }
    
    def export_to_csv(self, filename: str) -> Dict[str, Any]:
        """Export analysis results to CSV"""
        try:
            reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            filepath = os.path.join(reports_dir, f"{filename}.csv")
            
            # Create a comprehensive CSV with KPIs and overview
            data_rows = []
            
            # Add KPIs
            data_rows.append(['BUSINESS SNAPSHOT', '', ''])
            data_rows.append(['Metric', 'Value', 'Date'])
            
            kpis = self.report_data.get('kpis', {})
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            data_rows.append(['Total Revenue', kpis.get('total_revenue', 0), timestamp])
            data_rows.append(['Average Order Value', kpis.get('average_order_value', 0), timestamp])
            data_rows.append(['Total Orders', kpis.get('total_orders', 0), timestamp])
            data_rows.append(['Unique Customers', kpis.get('unique_customers', 0), timestamp])
            
            # Add segments
            data_rows.append(['', '', ''])
            data_rows.append(['CUSTOMER SEGMENTS', '', ''])
            data_rows.append(['Segment', 'Count', 'Revenue', 'Percentage'])
            
            segments = self.report_data.get('segments', {})
            for seg_name, seg_data in segments.items():
                data_rows.append([
                    seg_name,
                    seg_data.get('count', 0),
                    seg_data.get('revenue', 0),
                    f"{seg_data.get('percent', 0):.1f}%"
                ])
            
            # Add trends summary
            data_rows.append(['', '', '', ''])
            data_rows.append(['REVENUE TRENDS', '', '', ''])
            data_rows.append(['Period', 'Revenue', 'Date', ''])
            
            trends = self.report_data.get('trends', [])
            for trend in trends[-12:]:  # Last 12 periods
                data_rows.append([
                    trend.get('period', ''),
                    trend.get('revenue', 0),
                    trend.get('date', ''),
                    ''
                ])
            
            # Write to CSV
            df = pd.DataFrame(data_rows)
            df.to_csv(filepath, index=False, header=False)
            
            return {
                'success': True,
                'filepath': filepath,
                'filename': os.path.basename(filepath),
                'format': 'csv'
            }
        
        except Exception as e:
            traceback.print_exc()
            return {
                'success': False,
                'message': f'CSV export error: {str(e)}'
            }
    
    def get_binary_export(self, export_type: str, user_info: Dict[str, Any] = None, chat_log: List[Dict] = None) -> Dict[str, Any]:
        """Get binary file data for download"""
        try:
            if export_type == 'pdf':
                # Generate HTML first
                html_report = self.generate_html_report(user_info or {'username': 'User'}, chat_log)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"analysis_report_{timestamp}"

                result = self.export_to_pdf(
                    html_report,
                    filename,
                    user_info=user_info,
                    chat_log=chat_log,
                )
                if result.get('success'):
                    with open(result['filepath'], 'rb') as f:
                        pdf_data = f.read()
                    return {
                        'success': True,
                        'data': pdf_data,
                        'filename': result.get('filename', f"{filename}.pdf"),
                        'mimetype': 'application/pdf'
                    }
                return result
            
            elif export_type == 'excel':
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"analysis_report_{timestamp}"
                result = self.export_to_excel(filename)
                
                if result['success']:
                    with open(result['filepath'], 'rb') as f:
                        excel_data = f.read()
                    return {
                        'success': True,
                        'data': excel_data,
                        'filename': result['filename'],
                        'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    }
            
            elif export_type == 'csv':
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"analysis_report_{timestamp}"
                result = self.export_to_csv(filename)
                
                if result['success']:
                    with open(result['filepath'], 'rb') as f:
                        csv_data = f.read()
                    return {
                        'success': True,
                        'data': csv_data,
                        'filename': result['filename'],
                        'mimetype': 'text/csv'
                    }
            
            return {
                'success': False,
                'message': f'Unknown export type: {export_type}'
            }
        
        except Exception as e:
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Export error: {str(e)}'
            }
