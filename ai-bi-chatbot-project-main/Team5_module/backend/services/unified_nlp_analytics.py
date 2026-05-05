"""
Unified NLP + Analytics Engine Service
Integrates Team2_module (NLP) with analytics_engine (Advanced Analytics)
"""

import sys
import os
import pandas as pd
import re
from difflib import SequenceMatcher
from typing import Dict, Any, Optional

# Calculate correct paths
# __file__ = .../Team5_module/backend/services/unified_nlp_analytics.py
# We need to get to .../ai-bi-chatbot-project-main
current_file = os.path.abspath(__file__)  # Full path to this file
current_dir = os.path.dirname(current_file)  # services directory
backend_dir = os.path.dirname(current_dir)  # backend directory
team5_dir = os.path.dirname(backend_dir)  # Team5_module directory
project_root = os.path.dirname(team5_dir)  # ai-bi-chatbot-project-main

# Add project root to sys.path for package imports
sys.path.insert(0, project_root)

print("[PATH] Python import paths configured:")
print(f"   Project Root: {project_root}")
print(f"   Looking for Team2_module at: {os.path.join(project_root, 'Team2_module')}")

try:
    from Team2_module.intent_classifier import best_model, vectorizer
    from Team2_module.entity_extractor import extract_entities
    from Team2_module.query_builder import build_query
    from Team2_module.response_generator import generate_response
    TEAM2_AVAILABLE = True
    print("[OK] Team2_module imported successfully")
except ImportError as e:
    print(f"[WARN] Team2_module not fully available: {e}")
    TEAM2_AVAILABLE = False

try:
    from analytics_engine.core.engine import process_query
    from analytics_engine.insights.insight_generator import generate_insight
    ANALYTICS_ENGINE_AVAILABLE = True
    print("[OK] analytics_engine imported successfully")
except ImportError as e:
    print(f"[WARN] analytics_engine not fully available: {e}")
    ANALYTICS_ENGINE_AVAILABLE = False


class UnifiedNLPAnalytics:
    """Unified service combining NLP intent classification with advanced analytics"""
    
    def __init__(self, gemini_api_key=None):
        self.team2_available = TEAM2_AVAILABLE
        self.analytics_engine_available = ANALYTICS_ENGINE_AVAILABLE
        self.data_context = None
        self.dataframe = None
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY', '') or os.getenv('GOOGLE_API_KEY', '')
        
        print("[OK] Unified NLP Analytics Service Initialized")
        print(f"   Team2_module NLP: {'Available' if TEAM2_AVAILABLE else 'Not Available'}")
        print(f"   analytics_engine: {'Available' if ANALYTICS_ENGINE_AVAILABLE else 'Not Available'}")
        print(f"   Gemini API: {'Configured' if self.gemini_api_key else 'Not Configured'}")
    
    def set_context(self, dataframe: pd.DataFrame, data_summary: Dict[str, Any]):
        """Set the data context for analysis"""
        self.dataframe = dataframe
        self.data_context = data_summary
        print(f"[OK] Context set with {len(dataframe)} records")
    
    def classify_intent(self, question: str) -> Dict[str, Any]:
        """
        Classify user question intent using Team2's intent classifier
        
        Returns:
            {
                'intent': str,
                'confidence': float,
                'entities': dict
            }
        """
        if not self.team2_available:
            return {
                'intent': 'general_query',
                'confidence': 0.0,
                'entities': {},
                'source': 'fallback'
            }
        
        try:
            # Vectorize the input question
            question_vector = vectorizer.transform([question.lower()])
            
            # Predict intent
            intent = best_model.predict(question_vector)[0]
            
            # Get confidence score
            confidence = float(max(best_model.predict_proba(question_vector)[0]))
            
            # Extract entities from question
            entities = extract_entities(question)
            
            return {
                'intent': intent,
                'confidence': confidence,
                'entities': entities,
                'source': 'team2_nlp'
            }
        
        except Exception as e:
            print(f"[WARN] Intent classification error: {e}")
            return {
                'intent': 'general_query',
                'confidence': 0.0,
                'entities': {},
                'source': 'fallback',
                'error': str(e)
            }
    
    def build_analytics_query(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build an analytics query from intent and entities
        
        Uses Team2's query_builder
        """
        try:
            query = build_query(intent, entities)
            return {
                'success': True,
                'query': query,
                'source': 'team2_query_builder'
            }
        except Exception as e:
            print(f"[WARN] Query building error: {e}")
            return {
                'success': False,
                'error': str(e),
                'source': 'team2_query_builder'
            }
    
    def process_with_analytics_engine(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process query using analytics_engine
        """
        if not self.analytics_engine_available or self.dataframe is None:
            return {
                'success': False,
                'message': 'analytics_engine not available or no data context',
                'source': 'analytics_engine'
            }
        
        try:
            # Use the analytics engine to process the query
            result = process_query(query)
            return {
                'success': result.get('status') == 'success',
                'result': result,
                'source': 'analytics_engine'
            }
        except Exception as e:
            print(f"[WARN] Analytics engine error: {e}")
            return {
                'success': False,
                'error': str(e),
                'source': 'analytics_engine'
            }
    
    def extract_insights(self, metric: str = 'revenue') -> Dict[str, Any]:
        """
        Extract automatic insights from data using analytics_engine
        """
        if self.dataframe is None or not self.analytics_engine_available:
            return {
                'success': False,
                'insights': []
            }
        
        try:
            insights = []
            
            # Generate insight for the metric
            if metric in self.dataframe.columns:
                insight = generate_insight(self.dataframe, metric)
                insights.append({
                    'metric': metric,
                    'insight': insight
                })
            
            # Generate basic insights from data context
            if self.data_context:
                if 'business_snapshot' in self.data_context:
                    insights.append({
                        'type': 'business_snapshot',
                        'data': self.data_context['business_snapshot']
                    })
                
                if 'segments' in self.data_context:
                    insights.append({
                        'type': 'segmentation',
                        'data': self.data_context['segments']
                    })
                
                if 'churn' in self.data_context:
                    insights.append({
                        'type': 'churn_prediction',
                        'data': self.data_context['churn']
                    })
            
            return {
                'success': True,
                'insights': insights,
                'source': 'analytics_engine'
            }
        
        except Exception as e:
            print(f"[WARN] Insight extraction error: {e}")
            return {
                'success': False,
                'error': str(e),
                'insights': []
            }
    
    def process_question(self, question: str, use_gemini: bool = True) -> Dict[str, Any]:
        """
        Full pipeline: use deterministic analytics first, then Gemini for questions
        the analytics engine cannot answer confidently.
        """
        if self.dataframe is None:
            return {
                'success': False,
                'answer': 'Please upload your data first to ask questions.',
                'pipeline_source': 'validation'
            }

        # Step 1: Try NLP classification + analytics engine first.
        analytics_candidate = None
        if self.team2_available:
            intent_result = self.classify_intent(question)
            intent = intent_result['intent']
            confidence = intent_result['confidence']
            entities = intent_result['entities']
            
            # Build and process query
            query_result = self.build_analytics_query(intent, entities)
            
            if query_result['success'] and self.analytics_engine_available:
                analytics_result = self.process_with_analytics_engine(query_result['query'])
                
                if analytics_result['success']:
                    response = generate_response(analytics_result['result'])

                    analytics_candidate = {
                        'success': True,
                        'answer': response,
                        'intent': intent,
                        'confidence': confidence,
                        'pipeline_stages': ['intent_classification', 'entity_extraction', 'query_building', 'analytics_processing'],
                        'pipeline_source': 'unified_nlp_analytics'
                    }

                    if not self._should_escalate_to_gemini(analytics_candidate):
                        return analytics_candidate
        
        # Step 2: Use deterministic dataframe/keyword fallback without calling Gemini.
        fallback_candidate = self._fallback_analysis(question, use_gemini=False)
        if not self._should_escalate_to_gemini(fallback_candidate):
            return fallback_candidate

        # Step 3: Only now ask Gemini if enabled/configured.
        if use_gemini:
            gemini_answer = self._try_gemini_api(question)
            if gemini_answer:
                return gemini_answer

        return analytics_candidate or fallback_candidate

    def _should_escalate_to_gemini(self, result: Dict[str, Any]) -> bool:
        """Return True when the deterministic engine produced a weak/generic answer."""
        if not result or not result.get('success'):
            return True

        intent = str(result.get('intent', '') or '').lower()
        source = str(result.get('pipeline_source', result.get('source', '')) or '').lower()
        answer = str(result.get('answer', '') or '').strip().lower()
        try:
            confidence = float(result.get('confidence', 0) or 0)
        except (TypeError, ValueError):
            confidence = 0.0

        if intent in {'identity_query', 'dataset_ops_query'}:
            return False

        if intent in {
            'analysis_summary_query',
            'revenue_growth_query',
            'forecast_query',
            'revenue_trend_query',
            'geography_query',
            'geography_proxy_query',
            'demographic_query',
            'top_customers_query',
            'top_customers_proxy_query',
        }:
            return confidence < 0.62

        weak_markers = [
            'i can help with:',
            'no concise summary is available',
            'product performance data not available',
            'customer segmentation data not available',
            'revenue information not available',
        ]

        if any(marker in answer for marker in weak_markers):
            return True

        if intent in {'fallback_query', 'general_query', 'unknown', ''}:
            return confidence < 0.66 or source in {'fallback', 'fallback_analysis'}

        return confidence < 0.55
    
    def _try_gemini_api(self, question: str) -> Optional[Dict[str, Any]]:
        """Try to answer using Gemini API with enhanced error handling"""
        if not self.gemini_api_key:
            return None
        
        try:
            import google.generativeai as genai
            
            # Configure Gemini
            genai.configure(api_key=self.gemini_api_key)
            
            # Prefer newer models first and gracefully fallback for older environments.
            models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro']
            
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    
                    # Build context from data
                    context = self._build_gemini_context()
                    
                    # Create prompt
                    prompt = f"""{context}

User Question: {question}

Answer using this exact structure:

Answer:
- Give the direct answer in 1-2 bullets.

Evidence from Dataset:
- Use actual numbers from the provided context when available.
- If the dataset does not contain the requested personal or business field, clearly say it is not available in the uploaded dataset.

Recommended Next Step:
- Give one practical next step.

Keep the answer concise, business-focused, and suitable for inclusion in an executive report."""
                    
                    # Get response from Gemini
                    response = model.generate_content(prompt, stream=False)
                    
                    if response and hasattr(response, 'text') and response.text:
                        return {
                            'success': True,
                            'answer': response.text,
                            'intent': 'gemini_powered',
                            'confidence': 0.85,
                            'pipeline_source': f'gemini_api({model_name})'
                        }
                except Exception as model_err:
                    print(f"[DEBUG] Model {model_name} failed: {model_err}")
                    continue
                    
        except ImportError as e:
            print(f"[WARNING] Gemini library not available: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Gemini API error: {type(e).__name__}: {e}")
            return None
        
        return None
    
    def _build_gemini_context(self) -> str:
        """Build context string for Gemini with business data"""
        context = "Business Data Context:\n\n"

        def _short_text(value, limit=90):
            text = str(value or '').strip()
            if not text:
                return ''
            return text if len(text) <= limit else (text[:limit] + '...')

        def _num(val, default=0.0):
            try:
                if val is None:
                    return float(default)
                return float(val)
            except Exception:
                return float(default)

        def _int_num(val, default=0):
            try:
                if val is None:
                    return int(default)
                return int(float(val))
            except Exception:
                return int(default)
        
        if self.data_context:
            # Business metrics
            if 'business_snapshot' in self.data_context:
                snapshot = self.data_context['business_snapshot']
                context += "Key Metrics:\n"
                context += f"- Total Revenue: ${_num(snapshot.get('total_revenue')):,.2f}\n"
                context += f"- Average Order Value: ${_num(snapshot.get('average_order_value')):.2f}\n"
                context += f"- Total Orders: {_int_num(snapshot.get('total_orders'))}\n"
                context += f"- Unique Customers: {_int_num(snapshot.get('unique_customers'))}\n\n"
            
            # Top categories
            if 'top_categories' in self.data_context:
                categories = self.data_context['top_categories']
                context += "Top Product Categories:\n"
                for i, cat in enumerate(categories[:5], 1):
                    if isinstance(cat, dict):
                        context += f"{i}. {cat.get('category', 'Unknown')}: ${cat.get('revenue', 0):,.2f}\n"
                    else:
                        context += f"{i}. {cat}\n"
                context += "\n"
            
            # Customer segments
            if 'segments' in self.data_context:
                segments = self.data_context['segments']
                context += "Customer Segments:\n"
                if isinstance(segments, dict):
                    for seg_name, seg_data in list(segments.items())[:5]:
                        if isinstance(seg_data, dict):
                            context += f"- {seg_name}: {seg_data.get('count', 0)} customers, "
                            context += f"Avg Spend: ${_num(seg_data.get('avg_monetary')):.2f}\n"
                context += "\n"
            
            # Churn data
            if 'churn' in self.data_context:
                churn = self.data_context['churn']
                if isinstance(churn, dict) and churn.get('success'):
                    context += f"Churn Analysis: {len(churn.get('at_risk', []))} customers at risk\n\n"
            
            # Forecast data
            if 'forecast' in self.data_context:
                forecast = self.data_context['forecast']
                if isinstance(forecast, dict) and forecast.get('success'):
                    context += "Sales Forecast Available for Next Period\n\n"

            # Advanced module summary snippets for richer Gemini answers.
            advanced_outputs = self.data_context.get('advanced_outputs', {})
            if isinstance(advanced_outputs, dict) and advanced_outputs:
                context += "Advanced Analytics Summary:\n"
                added_modules = 0

                for module_key, module_payload in advanced_outputs.items():
                    if added_modules >= 8:
                        break

                    module_title = str(module_key).replace('-', ' ').replace('_', ' ').title()

                    payload = module_payload
                    if isinstance(module_payload, dict):
                        payload = module_payload.get('analysis', module_payload)

                    if not isinstance(payload, dict):
                        continue

                    summary_source = None
                    for section_name in ['summary', 'statistics', 'effectiveness']:
                        section_value = payload.get(section_name)
                        if isinstance(section_value, dict) and section_value:
                            summary_source = section_value
                            break

                    snippets = []
                    if isinstance(summary_source, dict):
                        for key, value in summary_source.items():
                            normalized = ''.join(ch for ch in str(key).lower() if ch.isalnum())
                            if normalized in {'success', 'message', 'status'}:
                                continue

                            if isinstance(value, (int, float, bool)):
                                snippets.append(f"{str(key).replace('_', ' ')}: {value}")
                            elif isinstance(value, str):
                                short_value = _short_text(value)
                                if short_value:
                                    snippets.append(f"{str(key).replace('_', ' ')}: {short_value}")

                            if len(snippets) >= 3:
                                break

                    if not snippets:
                        insights = payload.get('insights', [])
                        if isinstance(insights, list):
                            for insight in insights:
                                short_insight = _short_text(insight)
                                if short_insight:
                                    snippets.append(short_insight)
                                if len(snippets) >= 2:
                                    break

                    if not snippets:
                        continue

                    context += f"- {module_title}: {'; '.join(snippets)}\n"
                    added_modules += 1

                if added_modules > 0:
                    context += "\n"
        
        return context

    def _normalize_text(self, text: str) -> str:
        """Normalize free text for robust matching."""
        normalized = re.sub(r'[^a-z0-9 ]', ' ', str(text).lower())
        return re.sub(r'\s+', ' ', normalized).strip()

    def _contains_phrase(self, text: str, phrase: str) -> bool:
        """Check phrase match with token boundaries to avoid substring false positives."""
        if not text or not phrase:
            return False

        normalized_text = self._normalize_text(text)
        normalized_phrase = self._normalize_text(phrase)
        if not normalized_text or not normalized_phrase:
            return False

        # Multi-word phrase: keep strict boundary matching.
        if ' ' in normalized_phrase:
            return bool(re.search(rf'\b{re.escape(normalized_phrase)}\b', normalized_text))

        # Single-word phrase: allow common plural forms (product/products, category/categories).
        base = re.escape(normalized_phrase)
        if re.search(rf'\b{base}\b', normalized_text):
            return True

        if re.search(rf'\b{base}s\b', normalized_text):
            return True

        if normalized_phrase.endswith('y'):
            plural_y = re.escape(normalized_phrase[:-1] + 'ies')
            if re.search(rf'\b{plural_y}\b', normalized_text):
                return True

        return False

    def _pick_metric_column(self, question: str, numeric_cols):
        """Select the most relevant numeric metric column for aggregate questions."""
        if not numeric_cols:
            return None

        q = self._normalize_text(question)
        normalized_cols = {col: self._normalize_text(col) for col in numeric_cols}

        # Revenue-like questions should strongly prefer amount/sales/revenue columns.
        revenue_triggers = ['revenue', 'sales', 'order value', 'aov', 'amount', 'gmv', 'turnover']
        is_revenue_question = any(self._contains_phrase(q, token) for token in revenue_triggers)

        if is_revenue_question:
            preferred_patterns = [
                'total amount',
                'order amount',
                'sales amount',
                'sales value',
                'revenue',
                'sales',
                'amount',
                'order value',
                'price',
            ]
            for pattern in preferred_patterns:
                for col, norm_col in normalized_cols.items():
                    if self._contains_phrase(norm_col, pattern):
                        return col

        matched_col = self._find_best_column_match(question)
        if matched_col in numeric_cols:
            return matched_col

        if 'Total Amount' in numeric_cols:
            return 'Total Amount'

        return numeric_cols[0]

    def _find_best_column_match(self, question: str):
        """Return best matching dataframe column name for user question."""
        if self.dataframe is None or self.dataframe.empty:
            return None

        q = self._normalize_text(question)
        q_tokens = set(q.split())
        best_col = None
        best_score = 0.0

        for col in self.dataframe.columns:
            col_text = self._normalize_text(col)
            col_tokens = set(col_text.split())
            score = SequenceMatcher(None, q, col_text).ratio()

            if col_text and self._contains_phrase(q, col_text):
                score = max(score, 0.95)
            elif col_tokens and q_tokens:
                overlap = len(col_tokens.intersection(q_tokens)) / max(len(col_tokens), 1)
                score = max(score, overlap * 0.9)

            if score > best_score:
                best_score = score
                best_col = col

        if best_score >= 0.45:
            return best_col
        return None

    def _answer_with_dataframe_ops(self, question: str):
        """Handle broad user questions by computing direct answers from dataframe."""
        if self.dataframe is None or self.dataframe.empty:
            return None

        q = self._normalize_text(question)
        df = self.dataframe

        def has_any_phrase(*phrases: str) -> bool:
            return any(self._contains_phrase(q, phrase) for phrase in phrases)

        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        metric_col = self._pick_metric_column(question, numeric_cols)

        if has_any_phrase('missing', 'null', 'na', 'n a', 'blank'):
            missing = df.isna().sum().sort_values(ascending=False)
            parts = []
            for col, count in missing.head(5).items():
                pct = (float(count) / max(len(df), 1)) * 100
                parts.append(f"{col}: {int(count)} ({pct:.2f}%)")
            return f"Top missing-data columns are: {'; '.join(parts)}."

        if has_any_phrase('duplicate', 'duplicates', 'repeated'):
            dup_count = int(df.duplicated(keep='first').sum())
            dup_pct = (dup_count / max(len(df), 1)) * 100
            return f"Duplicate rows found: {dup_count} ({dup_pct:.2f}% of dataset)."

        has_total = has_any_phrase('total', 'sum', 'overall')
        has_average = has_any_phrase('average', 'avg', 'mean')

        if metric_col and has_total and has_average:
            numeric_series = pd.to_numeric(df[metric_col], errors='coerce')
            total_val = numeric_series.sum()
            avg_val = numeric_series.mean()
            return f"Total {metric_col} is {total_val:,.2f}, and average {metric_col} is {avg_val:,.2f}."

        if metric_col and has_total:
            total_val = pd.to_numeric(df[metric_col], errors='coerce').sum()
            return f"Total {metric_col} is {total_val:,.2f}."

        if metric_col and has_average:
            avg_val = pd.to_numeric(df[metric_col], errors='coerce').mean()
            return f"Average {metric_col} is {avg_val:,.2f}."

        if metric_col and has_any_phrase('max', 'highest', 'top value'):
            max_val = pd.to_numeric(df[metric_col], errors='coerce').max()
            return f"Maximum {metric_col} is {max_val:,.2f}."

        if metric_col and has_any_phrase('min', 'lowest'):
            min_val = pd.to_numeric(df[metric_col], errors='coerce').min()
            return f"Minimum {metric_col} is {min_val:,.2f}."

        if has_any_phrase('count', 'how many rows', 'rows', 'records'):
            return f"Dataset has {len(df):,} rows and {len(df.columns)} columns."

        if has_any_phrase('columns', 'schema', 'fields'):
            return f"Columns are: {', '.join(df.columns[:20])}."

        return None

    def _build_fallback_data_summary(self) -> str:
        """Return a concise data-driven summary when intent matching is weak."""
        parts = []

        def _num(val, default=0.0):
            try:
                if val is None:
                    return float(default)
                return float(val)
            except Exception:
                return float(default)

        if isinstance(self.data_context, dict):
            snapshot = self.data_context.get('business_snapshot')
            if isinstance(snapshot, dict):
                parts.append(
                    f"Total revenue is ${_num(snapshot.get('total_revenue')):,.2f} with "
                    f"average order value ${_num(snapshot.get('average_order_value')):,.2f}."
                )

            categories = self.data_context.get('top_categories')
            if isinstance(categories, list) and categories:
                first = categories[0]
                if isinstance(first, dict):
                    label = first.get('name') or first.get('category') or 'top category'
                    parts.append(f"Top category appears to be {label}.")

            churn = self.data_context.get('churn')
            if isinstance(churn, dict):
                at_risk = churn.get('at_risk_count')
                if at_risk is None and isinstance(churn.get('at_risk'), list):
                    at_risk = len(churn.get('at_risk', []))
                if at_risk:
                    parts.append(f"At-risk customers detected: {int(at_risk)}.")

            forecast = self.data_context.get('forecast')
            if isinstance(forecast, dict) and forecast.get('success'):
                points = forecast.get('forecast') or []
                if points:
                    next_value = _num(points[0].get('forecast'))
                    parts.append(f"Next-period forecast is about ${next_value:,.2f}.")

        if not parts and self.dataframe is not None:
            parts.append(f"Dataset has {len(self.dataframe):,} rows and {len(self.dataframe.columns)} columns.")

        if not parts:
            return (
                "No concise summary is available yet. Please run analysis first, then ask about "
                "revenue trends, top products, customer segments, churn risk, or forecast."
            )

        return " ".join(parts)
    
    def _fallback_analysis(self, question: str, use_gemini: bool = True) -> Dict[str, Any]:
        """Fallback analysis - tries multiple strategies to answer"""

        def _num(val, default=0.0):
            try:
                if val is None:
                    return float(default)
                return float(val)
            except Exception:
                return float(default)
        
        # FIRST: Optionally try Gemini API for richer responses.
        if use_gemini:
            print(f"[DEBUG-FALLBACK] Starting fallback for: {question[:50]}...")
            print(f"[DEBUG-FALLBACK] Gemini API Key configured: {bool(self.gemini_api_key)}")
            
            gemini_result = self._try_gemini_api(question)
            if gemini_result:
                print(f"[DEBUG-FALLBACK] Gemini returned answer")
                return gemini_result
            else:
                print(f"[DEBUG-FALLBACK] Gemini returned None, trying keywords")
        
        # SECOND: Keyword-based analysis for specific topics
        normalized_q = self._normalize_text(question)

        def has_any_phrase(*phrases: str) -> bool:
            return any(self._contains_phrase(normalized_q, phrase) for phrase in phrases)

        is_forecast_question = has_any_phrase('forecast', 'predict', 'next', 'future')
        asks_recommendation = has_any_phrase(
            'recommend',
            'recommendation',
            'recommendations',
            'suggest',
            'advice',
            'focus',
            'strategy',
            'strategies',
            'growth',
            'grow',
            'increase',
            'improve',
            'boost',
            'optimize',
            'action plan',
        )
        asks_summary = has_any_phrase(
            'summary',
            'summarize',
            'overview',
            'insight',
            'insights',
            'key insight',
            'key insights',
            'complete analysis',
            'analysis summary',
            'executive summary',
        )

        if has_any_phrase('who am i', 'what is my name', 'whats my name', 'my name'):
            return {
                'success': True,
                'answer': (
                    'Analysis Result: I do not have access to your personal profile details in this dataset session. '
                    'I can answer business questions about revenue, customers, products, risk, and forecasts.'
                ),
                'intent': 'identity_query',
                'confidence': 0.7,
                'pipeline_source': 'fallback_analysis'
            }

        computed_answer = self._answer_with_dataframe_ops(question)
        if computed_answer:
            return {
                'success': True,
                'answer': f"Analysis Result: {computed_answer}",
                'intent': 'dataset_ops_query',
                'confidence': 0.72,
                'pipeline_source': 'fallback_dataset_ops'
            }

        if asks_summary:
            return {
                'success': True,
                'answer': f"Analysis Result: Complete analysis summary: {self._build_fallback_data_summary()}",
                'intent': 'analysis_summary_query',
                'confidence': 0.76,
                'pipeline_source': 'fallback_analysis'
            }
        
        response = "Analysis Result: "

        if asks_recommendation or has_any_phrase('increase revenue', 'improve revenue', 'grow revenue', 'boost revenue', 'increase sales', 'grow sales'):
            recommendations = []

            if self.data_context and isinstance(self.data_context.get('top_categories'), list) and self.data_context['top_categories']:
                top_cat = self.data_context['top_categories'][0]
                if isinstance(top_cat, dict):
                    cat_name = top_cat.get('name') or top_cat.get('category') or 'top category'
                    cat_rev = _num(top_cat.get('revenue'))
                    recommendations.append(f"Double down on {cat_name}, currently contributing about ${cat_rev:,.2f}.")

            if self.data_context and isinstance(self.data_context.get('churn'), dict):
                churn_info = self.data_context['churn']
                at_risk = churn_info.get('at_risk_count')
                if at_risk is None and isinstance(churn_info.get('at_risk'), list):
                    at_risk = len(churn_info.get('at_risk', []))
                if at_risk:
                    recommendations.append(f"Run a retention campaign for {int(at_risk)} at-risk customers to protect recurring revenue.")

            if self.dataframe is not None and 'Total Amount' in self.dataframe.columns:
                aov = pd.to_numeric(self.dataframe['Total Amount'], errors='coerce').mean()
                if pd.notna(aov):
                    recommendations.append(f"Lift average order value above ${float(aov):,.2f} with bundles and threshold-based offers.")

            if not recommendations:
                recommendations = [
                    "Prioritize your highest-revenue product categories.",
                    "Retain high-value customers with targeted re-engagement offers.",
                    "Increase average order value with bundles and upsell prompts."
                ]

            response += "Revenue Growth Recommendations:\n"
            for idx, rec in enumerate(recommendations[:3], 1):
                response += f"{idx}. {rec}\n"

            return {
                'success': True,
                'answer': response.rstrip(),
                'intent': 'revenue_growth_query',
                'confidence': 0.74,
                'pipeline_source': 'fallback_analysis'
            }

        # Prioritize forecast intent so questions like "What will my sales be next month?"
        # don't get trapped by the generic sales/revenue branch.
        if is_forecast_question:
            if self.data_context and 'forecast' in self.data_context:
                forecast_data = self.data_context['forecast']
                if isinstance(forecast_data, dict) and forecast_data.get('success'):
                    points = forecast_data.get('forecast') or []
                    if points:
                        next_point = points[0]
                        next_value = _num(next_point.get('forecast'))
                        horizon_total = sum(_num(p.get('forecast')) for p in points)
                        response += (
                            f"Predicted sales for next period: ${next_value:,.2f}. "
                            f"Total projected sales across next {len(points)} periods: ${horizon_total:,.2f}."
                        )
                    else:
                        response += "Forecast is available, but projected points are empty."
                else:
                    response += forecast_data.get('message', 'Forecast data not available.') if isinstance(forecast_data, dict) else 'Forecast data not available.'
            else:
                response += "Forecast data not available. Please run analysis on a dataset with valid Date and Total Amount columns."

            return {
                'success': True,
                'answer': response,
                'intent': 'forecast_query',
                'confidence': 0.72,
                'pipeline_source': 'fallback_analysis'
            }

        if has_any_phrase('trend', 'monthly', 'month', 'weekly', 'week', 'daily', 'over time', 'time series'):
            if self.dataframe is not None and all(col in self.dataframe.columns for col in ['Date', 'Total Amount']):
                temp = self.dataframe[['Date', 'Total Amount']].copy()
                temp['Date'] = pd.to_datetime(temp['Date'], errors='coerce')
                temp['Total Amount'] = pd.to_numeric(temp['Total Amount'], errors='coerce')
                temp = temp.dropna(subset=['Date', 'Total Amount'])

                if not temp.empty:
                    monthly = (
                        temp.assign(period=temp['Date'].dt.to_period('M').astype(str))
                        .groupby('period', dropna=True)['Total Amount']
                        .sum()
                        .sort_index()
                    )
                    if not monthly.empty:
                        response += "Monthly Revenue Trend:\n"
                        for period, value in monthly.tail(6).items():
                            response += f"- {period}: ${_num(value):,.2f}\n"
                        return {
                            'success': True,
                            'answer': response.rstrip(),
                            'intent': 'revenue_trend_query',
                            'confidence': 0.73,
                            'pipeline_source': 'fallback_analysis'
                        }
            response += "Trend data requires valid Date and Total Amount columns."
            return {
                'success': True,
                'answer': response,
                'intent': 'revenue_trend_query',
                'confidence': 0.66,
                'pipeline_source': 'fallback_analysis'
            }

        if has_any_phrase('region', 'country', 'location', 'geography', 'geographic'):
            if self.dataframe is not None and 'Total Amount' in self.dataframe.columns:
                geo_col = None
                for candidate in ['Region', 'Country']:
                    if candidate in self.dataframe.columns:
                        geo_col = candidate
                        break
                if geo_col:
                    grouped = (
                        self.dataframe
                        .assign(_amount=pd.to_numeric(self.dataframe['Total Amount'], errors='coerce'))
                        .dropna(subset=[geo_col, '_amount'])
                        .groupby(geo_col, dropna=True)['_amount']
                        .sum()
                        .sort_values(ascending=False)
                        .head(5)
                    )
                    if not grouped.empty:
                        response += f"Top {geo_col} by Revenue:\n"
                        for idx, (name, amount) in enumerate(grouped.items(), 1):
                            response += f"{idx}. {name}: ${_num(amount):,.2f}\n"
                        return {
                            'success': True,
                            'answer': response.rstrip(),
                            'intent': 'geography_query',
                            'confidence': 0.72,
                            'pipeline_source': 'fallback_analysis'
                        }
            # Graceful proxy when geographic columns are missing.
            if self.dataframe is not None and all(col in self.dataframe.columns for col in ['Product Category', 'Total Amount']):
                grouped = (
                    self.dataframe
                    .assign(_amount=pd.to_numeric(self.dataframe['Total Amount'], errors='coerce'))
                    .dropna(subset=['Product Category', '_amount'])
                    .groupby('Product Category', dropna=True)['_amount']
                    .sum()
                    .sort_values(ascending=False)
                    .head(5)
                )
                if not grouped.empty:
                    response += "Geographic columns are unavailable. Top Product Categories by Revenue:\n"
                    for idx, (category, amount) in enumerate(grouped.items(), 1):
                        response += f"{idx}. {category}: ${_num(amount):,.2f}\n"
                    return {
                        'success': True,
                        'answer': response.rstrip(),
                        'intent': 'geography_proxy_query',
                        'confidence': 0.68,
                        'pipeline_source': 'fallback_analysis'
                    }

            response += "Geographic columns are unavailable in this dataset. Please upload a file with Region or Country for location-level insights."
            return {
                'success': True,
                'answer': response,
                'intent': 'geography_query',
                'confidence': 0.64,
                'pipeline_source': 'fallback_analysis'
            }

        if has_any_phrase('age', 'gender', 'demographic', 'demographics'):
            if self.dataframe is not None and 'Total Amount' in self.dataframe.columns:
                if has_any_phrase('gender') and 'Gender' in self.dataframe.columns:
                    grouped = (
                        self.dataframe
                        .assign(_amount=pd.to_numeric(self.dataframe['Total Amount'], errors='coerce'))
                        .dropna(subset=['Gender', '_amount'])
                        .groupby('Gender', dropna=True)['_amount']
                        .sum()
                        .sort_values(ascending=False)
                    )
                    if not grouped.empty:
                        response += "Revenue by Gender:\n"
                        for gender, amount in grouped.items():
                            response += f"- {gender}: ${_num(amount):,.2f}\n"
                        return {
                            'success': True,
                            'answer': response.rstrip(),
                            'intent': 'demographic_query',
                            'confidence': 0.71,
                            'pipeline_source': 'fallback_analysis'
                        }

                if 'Age' in self.dataframe.columns:
                    temp = self.dataframe[['Age', 'Total Amount']].copy()
                    temp['Age'] = pd.to_numeric(temp['Age'], errors='coerce')
                    temp['Total Amount'] = pd.to_numeric(temp['Total Amount'], errors='coerce')
                    temp = temp.dropna(subset=['Age', 'Total Amount'])
                    if not temp.empty:
                        temp['age_band'] = pd.cut(temp['Age'], bins=[0, 25, 35, 45, 200], labels=['18-25', '26-35', '36-45', '46+'])
                        grouped = temp.groupby('age_band', dropna=True)['Total Amount'].sum().sort_values(ascending=False)
                        if not grouped.empty:
                            response += "Revenue by Age Group:\n"
                            for band, amount in grouped.items():
                                response += f"- {band}: ${_num(amount):,.2f}\n"
                            return {
                                'success': True,
                                'answer': response.rstrip(),
                                'intent': 'demographic_query',
                                'confidence': 0.7,
                                'pipeline_source': 'fallback_analysis'
                            }

            response += "Demographic breakdown needs Age or Gender plus Total Amount columns."
            return {
                'success': True,
                'answer': response,
                'intent': 'demographic_query',
                'confidence': 0.64,
                'pipeline_source': 'fallback_analysis'
            }
        
        if has_any_phrase('revenue', 'sales', 'sale', 'earn', 'total sale', 'total sales'):
            if self.data_context and 'business_snapshot' in self.data_context:
                snapshot = self.data_context['business_snapshot']
                response += f"Total Revenue: ${_num(snapshot.get('total_revenue')):,.2f}. "
                response += f"Average Order Value: ${_num(snapshot.get('average_order_value')):.2f}."
            else:
                response += "Revenue information not available."
        
        elif has_any_phrase('product', 'category'):
            if self.data_context and 'top_categories' in self.data_context:
                categories = self.data_context['top_categories']
                response += "Top Products/Categories:\n"
                for i, cat in enumerate(categories[:5], 1):
                    if isinstance(cat, dict):
                        label = cat.get('name') or cat.get('category') or 'Unknown'
                        response += f"{i}. {label}: ${cat.get('revenue', 0):,.2f}\n"
                    else:
                        response += f"{i}. {cat}\n"
            else:
                response += "Product performance data not available."
        
        elif has_any_phrase('customer', 'client', 'buyer'):
            if has_any_phrase('top', 'best') and self.dataframe is not None and all(col in self.dataframe.columns for col in ['Customer ID', 'Total Amount']):
                grouped = (
                    self.dataframe
                    .groupby('Customer ID', dropna=True)['Total Amount']
                    .sum()
                    .sort_values(ascending=False)
                    .head(5)
                )
                response += "Top Customers by Revenue:\n"
                for idx, (cust_id, amount) in enumerate(grouped.items(), 1):
                    response += f"{idx}. {cust_id}: ${_num(amount):,.2f}\n"
                return {
                    'success': True,
                    'answer': response.rstrip(),
                    'intent': 'top_customers_query',
                    'confidence': 0.75,
                    'pipeline_source': 'fallback_analysis'
                }

            if has_any_phrase('top', 'best') and self.dataframe is not None and all(col in self.dataframe.columns for col in ['Product Category', 'Total Amount']):
                grouped = (
                    self.dataframe
                    .groupby('Product Category', dropna=True)['Total Amount']
                    .sum()
                    .sort_values(ascending=False)
                    .head(5)
                )
                response += "Customer identifier is not available in this dataset. Top categories by revenue are:\n"
                for idx, (category, amount) in enumerate(grouped.items(), 1):
                    response += f"{idx}. {category}: ${_num(amount):,.2f}\n"
                return {
                    'success': True,
                    'answer': response.rstrip(),
                    'intent': 'top_customers_proxy_query',
                    'confidence': 0.7,
                    'pipeline_source': 'fallback_analysis'
                }

            if self.data_context and 'segments' in self.data_context:
                segments = self.data_context['segments']
                response += "Customer Segments:\n"
                if isinstance(segments, dict):
                    emitted = 0
                    for seg_name, seg_data in list(segments.items())[:5]:
                        if isinstance(seg_data, dict):
                            seg_count = seg_data.get('count', seg_data.get('customers', 0))
                            response += f"- {seg_name}: {seg_count} customers\n"
                            emitted += 1
                        else:
                            response += f"- {seg_name}\n"
                            emitted += 1
                    if emitted == 0:
                        response += "- No customer segment records available for this dataset.\n"
                else:
                    response += str(segments)
            else:
                response += "Customer segmentation data not available."
        
        elif has_any_phrase('churn', 'risk', 'lose'):
            if self.data_context and 'churn' in self.data_context:
                churn_data = self.data_context['churn']
                response += "Churn Risk Analysis: At-risk customers detected."
            else:
                response += "Churn prediction data not available."
        
        elif has_any_phrase('forecast', 'predict', 'next', 'future'):
            if self.data_context and 'forecast' in self.data_context:
                response += "Sales forecast available for upcoming period."
            else:
                response += "Forecast data not available."
        
        else:
            response += self._build_fallback_data_summary()
        
        return {
            'success': True,
            'answer': response,
            'intent': 'fallback_query',
            'confidence': 0.6,
            'pipeline_source': 'fallback_analysis'
        }
    
    def get_predefined_questions(self) -> list:
        """Get list of predefined questions the chatbot can handle"""
        return [
            '📊 What are the key insights?',
            '💰 What\'s the revenue trend?',
            '👥 Customer segments breakdown?',
            '⚠️ Which customers are at risk?',
            '📈 What will sales be next month?',
            '🎯 Top performing products?',
            '🌍 Sales by country?',
            '📋 Complete analysis summary?'
        ]
    
    def generate_full_analysis_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive analysis report using all integrated services
        """
        if self.dataframe is None:
            return {
                'success': False,
                'message': 'No data context available'
            }
        
        report = {
            'success': True,
            'timestamp': pd.Timestamp.now().isoformat(),
            'data_summary': self.data_context,
            'automated_insights': [],
            'key_metrics': {}
        }
        
        # Extract insights
        insights = self.extract_insights()
        if insights['success']:
            report['automated_insights'] = insights['insights']
        
        # Generate key metrics
        if 'business_snapshot' in self.data_context:
            report['key_metrics'] = self.data_context['business_snapshot']
        
        return report


# Global instance
unified_service = None


def initialize_unified_service(gemini_api_key=None):
    """Initialize the unified NLP analytics service"""
    global unified_service
    unified_service = UnifiedNLPAnalytics(gemini_api_key=gemini_api_key)
    return unified_service


def get_unified_service() -> UnifiedNLPAnalytics:
    """Get the global unified service instance"""
    global unified_service
    if unified_service is None:
        unified_service = initialize_unified_service()
    return unified_service
