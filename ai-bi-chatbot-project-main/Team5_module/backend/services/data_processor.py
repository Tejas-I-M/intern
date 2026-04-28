import pandas as pd
import os
import joblib
from datetime import datetime
import traceback
import re
import warnings
from difflib import SequenceMatcher
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype
from services.insight_engine import DataQualityService, InsightBuilder

class DataProcessor:
    """Handle data loading, validation, and preprocessing"""
    
    def __init__(self, models_path, mapper_confidence_threshold=0.55):
        self.models_path = models_path
        self.mapper_confidence_threshold = float(mapper_confidence_threshold)
        self.segmentation_model = None
        self.scaler = None
        self.forecast_model = None
        self.churn_model = None
        self.churn_features = None
        self.column_mapper_model = None
        self.column_mapper_label_encoder = None
        self.data_quality_service = DataQualityService()
        self.insight_builder = InsightBuilder()
        self.load_models()
    
    def load_models(self):
        """Load pre-trained models from disk"""
        try:
            # Load segmentation model
            scaler_path = os.path.join(self.models_path, 'scaler.pkl')
            seg_model_path = os.path.join(self.models_path, 'segmentation_model.pkl')
            
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                print("✅ Scaler loaded")
            
            if os.path.exists(seg_model_path):
                self.segmentation_model = joblib.load(seg_model_path)
                print("✅ Segmentation model loaded")
            
            # Load forecast model
            forecast_path = os.path.join(self.models_path, 'forecast_model.pkl')
            if os.path.exists(forecast_path):
                self.forecast_model = joblib.load(forecast_path)
                print("✅ Forecast model loaded")
            
            # Load churn model
            churn_path = os.path.join(self.models_path, 'churn_model.pkl')
            churn_features_path = os.path.join(self.models_path, 'churn_features.pkl')
            
            if os.path.exists(churn_path):
                self.churn_model = joblib.load(churn_path)
                print("✅ Churn model loaded")
            
            if os.path.exists(churn_features_path):
                self.churn_features = joblib.load(churn_features_path)
                print("✅ Churn features loaded")

            # Optional: load trainable column mapper model for schema alignment.
            column_mapper_path = os.path.join(self.models_path, 'column_mapper_model.pkl')
            column_mapper_label_encoder_path = os.path.join(self.models_path, 'column_mapper_label_encoder.pkl')

            if os.path.exists(column_mapper_path):
                self.column_mapper_model = joblib.load(column_mapper_path)
                print("✅ Column mapper model loaded")

            if os.path.exists(column_mapper_label_encoder_path):
                self.column_mapper_label_encoder = joblib.load(column_mapper_label_encoder_path)
                print("✅ Column mapper label encoder loaded")
        
        except Exception as e:
            print(f"⚠️  Error loading models: {e}")
            traceback.print_exc()

    def _normalize_col_name(self, col_name):
        """Normalize column names for robust matching across datasets."""
        cleaned = str(col_name).strip().lower()
        cleaned = re.sub(r'blank', ' ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return re.sub(r'[^a-z0-9]', '', cleaned)

    def _sanitize_dataframe(self, df):
        """Normalize noisy placeholders in headers and text values."""
        clean_df = df.copy()

        # Normalize column names like TransactionblankDate -> Transaction Date.
        rename_cols = {}
        for col in clean_df.columns:
            new_col = str(col)
            new_col = re.sub(r'blank', ' ', new_col, flags=re.IGNORECASE)
            new_col = re.sub(r'\s+', ' ', new_col).strip()
            rename_cols[col] = new_col or str(col)
        clean_df = clean_df.rename(columns=rename_cols)

        # Normalize string placeholders and keep true missing values as NaN.
        object_cols = clean_df.select_dtypes(include=['object']).columns.tolist()
        for col in object_cols:
            series = clean_df[col].astype(str)
            series = series.str.replace(r'blank', ' ', regex=True, case=False)
            series = series.str.replace(r'\s+', ' ', regex=True).str.strip()
            series = series.replace({'': pd.NA, 'nan': pd.NA, 'none': pd.NA, 'null': pd.NA, 'na': pd.NA})
            clean_df[col] = series

        return clean_df

    def _build_column_aliases(self):
        """Canonical columns and accepted aliases for auto-mapping."""
        return {
            'Customer ID': [
                'customerid', 'customer', 'customer_id', 'clientid', 'client_id',
                'userid', 'user_id', 'buyerid', 'buyer_id', 'accountid',
                'memberid', 'member_id', 'shopperid', 'shopper_id'
            ],
            'Date': [
                'date', 'orderdate', 'order_date', 'transactiondate', 'transaction_date',
                'invoicedate', 'invoice_date', 'purchasedate', 'purchase_date', 'createdat', 'timestamp',
                'saledate', 'sale_date', 'transaction date', 'sale date'
            ],
            'Total Amount': [
                'totalamount', 'amount', 'revenue', 'sales', 'total', 'orderamount',
                'order_amount', 'netsales', 'price', 'finalamount', 'value',
                'salesamount', 'sales_amount', 'totalspent', 'total_spent', 'total spent', 'amountspent', 'spent'
            ],
            'Product Category': [
                'productcategory', 'category', 'product_type', 'producttype', 'itemcategory'
            ],
            'Gender': ['gender', 'sex'],
            'Age': ['age', 'customerage', 'customer_age'],
            'Country': ['country', 'nation'],
            'Region': ['region', 'state', 'province', 'city', 'location']
        }

    def _similarity_score(self, left, right):
        """String similarity score in [0, 1] for column-name matching."""
        return SequenceMatcher(None, self._normalize_col_name(left), self._normalize_col_name(right)).ratio()

    def _coerce_numeric_series(self, series):
        """Parse numeric data robustly from text-like values (currency, commas, spaces)."""
        if is_numeric_dtype(series):
            return pd.to_numeric(series, errors='coerce')

        text = series.astype(str).str.strip()
        text = text.str.replace(r'\(([^)]+)\)', r'-\1', regex=True)
        text = text.str.replace(r'[^0-9\.-]', '', regex=True)
        text = text.replace({'': pd.NA, '-': pd.NA, '.': pd.NA, '-.': pd.NA})
        return pd.to_numeric(text, errors='coerce')

    def _coerce_datetime_series(self, series):
        """Parse datetimes robustly by selecting the best parse strategy."""
        if is_datetime64_any_dtype(series):
            return pd.to_datetime(series, errors='coerce')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            parsed_default = pd.to_datetime(series, errors='coerce')
            parsed_dayfirst = pd.to_datetime(series, errors='coerce', dayfirst=True)

        default_rate = float(parsed_default.notna().mean())
        dayfirst_rate = float(parsed_dayfirst.notna().mean())
        if dayfirst_rate > default_rate:
            return parsed_dayfirst
        return parsed_default

    def _looks_like_amount_column(self, col_name, series):
        """Check whether a numeric column semantically looks like sales/revenue amount."""
        normalized_col = self._normalize_col_name(col_name)
        parsed = self._coerce_numeric_series(series)
        parse_rate = float(parsed.notna().mean())
        if parse_rate < 0.6:
            return False

        positive_tokens = [
            'amount', 'revenue', 'sale', 'sales', 'price', 'total', 'spent',
            'spend', 'cost', 'gross', 'net', 'invoice', 'order', 'value'
        ]
        negative_tokens = [
            'salary', 'wage', 'payroll', 'bonus', 'commission', 'age', 'qty',
            'quantity', 'count', 'number', 'score', 'rank', 'id', 'code'
        ]

        has_positive_token = any(token in normalized_col for token in positive_tokens)
        has_negative_token = any(token in normalized_col for token in negative_tokens)

        if has_positive_token:
            return True
        if has_negative_token:
            return False

        amount_aliases = ['total amount', 'amount', 'sales amount', 'revenue', 'sales', 'order amount', 'total spent']
        name_score = max(self._similarity_score(col_name, alias) for alias in amount_aliases)
        return name_score >= 0.75

    def _build_column_feature_text(self, col_name, series):
        """Build text features for model-based canonical-column prediction."""
        dtype = str(series.dtype)
        non_null = series.dropna().astype(str).head(8).tolist()
        sample_text = ' | '.join(non_null)
        normalized_name = self._normalize_col_name(col_name)
        return f"name:{col_name} normalized:{normalized_name} dtype:{dtype} samples:{sample_text}"

    def _normalize_predicted_role(self, role):
        """Map model labels from different training schemes to canonical backend roles."""
        if role is None:
            return None

        raw = str(role).strip()
        if not raw:
            return None

        normalized = self._normalize_col_name(raw)

        canonical_direct = {
            'customerid': 'Customer ID',
            'date': 'Date',
            'totalamount': 'Total Amount',
            'productcategory': 'Product Category',
            'gender': 'Gender',
            'age': 'Age',
            'country': 'Country',
            'region': 'Region',
        }
        if normalized in canonical_direct:
            return canonical_direct[normalized]

        synonym_map = {
            'id': 'Customer ID',
            'userid': 'Customer ID',
            'clientid': 'Customer ID',
            'datetime': 'Date',
            'timestamp': 'Date',
            'numeric': 'Total Amount',
            'amount': 'Total Amount',
            'revenue': 'Total Amount',
            'sales': 'Total Amount',
            'categorical': 'Product Category',
            'category': 'Product Category',
            'text': 'Product Category',
            'location': 'Region',
            'geo': 'Region',
            'city': 'Region',
            'state': 'Region',
            'province': 'Region',
        }
        return synonym_map.get(normalized)

    def _predict_raw_role(self, col_name, series):
        """Predict raw role label using either text-input or dataframe-input model shape."""
        feature_text = self._build_column_feature_text(col_name, series)

        # Path A: models trained on single text feature.
        try:
            return self.column_mapper_model.predict([feature_text])[0], 'text'
        except Exception:
            pass

        # Path B: notebook models trained on structured dataframe input.
        sample_text = ' | '.join(series.dropna().astype(str).head(8).tolist())
        model_input = pd.DataFrame([
            {
                'column_name': str(col_name),
                'sample_values': sample_text,
                'dtype': str(series.dtype)
            }
        ])
        return self.column_mapper_model.predict(model_input)[0], 'dataframe'

    def _predict_column_role(self, col_name, series):
        """Predict canonical role for a source column using optional trained mapper."""
        if self.column_mapper_model is None:
            return None, 0.0

        try:
            pred, input_mode = self._predict_raw_role(col_name, series)
            confidence = 0.0

            if hasattr(self.column_mapper_model, 'predict_proba'):
                if input_mode == 'text':
                    probs = self.column_mapper_model.predict_proba([self._build_column_feature_text(col_name, series)])[0]
                else:
                    sample_text = ' | '.join(series.dropna().astype(str).head(8).tolist())
                    proba_input = pd.DataFrame([
                        {
                            'column_name': str(col_name),
                            'sample_values': sample_text,
                            'dtype': str(series.dtype)
                        }
                    ])
                    probs = self.column_mapper_model.predict_proba(proba_input)[0]
                confidence = float(max(probs))
            else:
                # If model does not expose probabilities, keep a moderate default confidence.
                confidence = 0.6

            if self.column_mapper_label_encoder is not None:
                try:
                    pred = self.column_mapper_label_encoder.inverse_transform([pred])[0]
                except Exception:
                    # Model may already emit string labels.
                    pred = pred

            canonical_role = self._normalize_predicted_role(pred)
            return canonical_role, float(confidence)
        except Exception as e:
            print(f"⚠️  Column mapper prediction failed for '{col_name}': {e}")
            return None, 0.0

    def _model_map_columns(self, df, confidence_threshold=0.55):
        """Map source columns to canonical roles using trained model predictions."""
        if self.column_mapper_model is None:
            return {}

        aliases = self._build_column_aliases()
        valid_roles = set(aliases.keys())

        role_candidates = {}
        for col in df.columns:
            role, confidence = self._predict_column_role(col, df[col])
            if not role or role not in valid_roles:
                continue
            if confidence < confidence_threshold:
                continue

            existing = role_candidates.get(role)
            if existing is None or confidence > existing['confidence']:
                role_candidates[role] = {'source_col': col, 'confidence': confidence}

        mapped_columns = {}
        for role, meta in role_candidates.items():
            source_col = meta['source_col']
            if role in df.columns:
                mapped_columns[role] = role
            else:
                mapped_columns[role] = source_col

        return mapped_columns

    def _build_exploratory_capabilities(self):
        """Capabilities when core schema is not available for advanced analytics."""
        return {
            'upload': True,
            'kpis': False,
            'trends': False,
            'segmentation': False,
            'top_categories': False,
            'forecast': False,
            'churn_prediction': False,
            'product_affinity': False,
            'geographic_analysis': False,
            'report_generation': False,
            'chatbot': False,
            'exploratory_summary': True
        }

    def build_exploratory_summary(self, df):
        """Create useful fallback analytics for datasets without required canonical columns."""
        total_rows = len(df)
        total_cols = len(df.columns)

        missing = (df.isna().sum() / max(total_rows, 1) * 100).round(2)
        missing_summary = [
            {'column': col, 'missing_pct': float(pct)}
            for col, pct in missing.sort_values(ascending=False).head(10).items()
        ]

        numeric_summary = []
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        for col in numeric_cols[:8]:
            series = pd.to_numeric(df[col], errors='coerce')
            numeric_summary.append({
                'column': col,
                'count': int(series.notna().sum()),
                'mean': float(series.mean()) if series.notna().any() else None,
                'min': float(series.min()) if series.notna().any() else None,
                'max': float(series.max()) if series.notna().any() else None,
                'std': float(series.std()) if series.notna().sum() > 1 else None
            })

        categorical_summary = []
        object_cols = df.select_dtypes(exclude=['number']).columns.tolist()
        for col in object_cols[:8]:
            top_values = df[col].astype(str).value_counts(dropna=True).head(5)
            categorical_summary.append({
                'column': col,
                'unique_count': int(df[col].nunique(dropna=True)),
                'top_values': [
                    {'value': str(v), 'count': int(c)}
                    for v, c in top_values.items()
                ]
            })

        return {
            'row_count': total_rows,
            'column_count': total_cols,
            'missing_summary': missing_summary,
            'numeric_summary': numeric_summary,
            'categorical_summary': categorical_summary,
            'note': 'Exploratory fallback mode: core analytics disabled until mapping is completed.'
        }

    def _infer_column_type(self, series, threshold=0.8):
        """Infer user-facing column type label (text/number/date)."""
        if is_datetime64_any_dtype(series):
            return 'date'
        if is_numeric_dtype(series):
            return 'number'

        non_null = series.dropna()
        if non_null.empty:
            return 'text'

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            parsed_dates = pd.to_datetime(non_null, errors='coerce')
        date_parse_rate = float(parsed_dates.notna().mean())

        parsed_numbers = pd.to_numeric(non_null, errors='coerce')
        number_parse_rate = float(parsed_numbers.notna().mean())

        if date_parse_rate >= threshold and date_parse_rate >= number_parse_rate:
            return 'date'
        if number_parse_rate >= threshold:
            return 'number'
        return 'text'

    def build_data_health_snapshot(self, df):
        """Create a data health snapshot immediately after dataset upload."""
        total_rows = len(df)
        safe_total_rows = max(total_rows, 1)

        missing_value_tracker = []
        type_groups = {
            'text': [],
            'number': [],
            'date': []
        }

        for col in df.columns:
            series = df[col]
            missing_count = int(series.isna().sum())
            missing_pct = float((missing_count / safe_total_rows) * 100)
            inferred_type = self._infer_column_type(series)

            missing_value_tracker.append({
                'column': col,
                'missing_count': missing_count,
                'missing_percentage': missing_pct,
                'inferred_type': inferred_type
            })

            type_groups[inferred_type].append(col)

        duplicate_row_count = int(df.duplicated(keep='first').sum())
        duplicate_row_percentage = float((duplicate_row_count / safe_total_rows) * 100)

        return {
            'total_rows': total_rows,
            'total_columns': len(df.columns),
            'missing_value_tracker': missing_value_tracker,
            'duplicate_row_counter': {
                'duplicate_rows': duplicate_row_count,
                'duplicate_percentage': duplicate_row_percentage,
                'has_duplicates': duplicate_row_count > 0
            },
            'data_type_summary': {
                'text_columns': type_groups['text'],
                'number_columns': type_groups['number'],
                'date_columns': type_groups['date']
            }
        }

    def suggest_mapping_candidates(self, df, top_n=3):
        """Suggest canonical mapping candidates with confidence scores."""
        aliases = self._build_column_aliases()
        roles = ['Customer ID', 'Date', 'Total Amount', 'Product Category']
        suggestions = {}

        for role in roles:
            candidates = []
            role_aliases = [role] + aliases.get(role, [])

            for col in df.columns:
                name_score = max(self._similarity_score(col, alias) for alias in role_aliases)

                series = df[col]
                parse_score = 0.0
                reason = []

                if role == 'Date':
                    parsed = self._coerce_datetime_series(series)
                    parse_score = float(parsed.notna().mean())
                    reason.append(f"date_parse={round(parse_score * 100, 1)}%")
                elif role == 'Total Amount':
                    parsed = self._coerce_numeric_series(series)
                    parse_score = float(parsed.notna().mean())
                    reason.append(f"numeric_parse={round(parse_score * 100, 1)}%")
                elif role == 'Customer ID':
                    unique_ratio = series.astype(str).nunique(dropna=True) / max(len(series), 1)
                    normalized_col = self._normalize_col_name(col)
                    looks_transactional = any(
                        token in normalized_col for token in ['transaction', 'invoice', 'order', 'receipt', 'product']
                    )
                    parse_score = max(0.0, min(1.0, 1.0 - abs(unique_ratio - 0.45)))
                    if looks_transactional and unique_ratio > 0.9:
                        parse_score *= 0.15
                    reason.append(f"unique_ratio={round(unique_ratio * 100, 1)}%")
                elif role == 'Product Category':
                    unique_ratio = series.astype(str).nunique(dropna=True) / max(len(series), 1)
                    parse_score = max(0.0, min(1.0, 1.0 - abs(unique_ratio - 0.2)))
                    reason.append(f"category_ratio={round(unique_ratio * 100, 1)}%")

                confidence = round((name_score * 0.65 + parse_score * 0.35), 4)
                candidates.append({
                    'column': col,
                    'confidence': confidence,
                    'confidence_pct': round(confidence * 100, 1),
                    'name_score': round(name_score, 4),
                    'parse_score': round(parse_score, 4),
                    'reason': ', '.join(reason)
                })

            candidates = sorted(candidates, key=lambda x: x['confidence'], reverse=True)[:top_n]
            suggestions[role] = candidates

        return suggestions

    def _auto_map_columns(self, df):
        """Auto-map dataset columns into canonical schema names used by analytics."""
        aliases = self._build_column_aliases()
        normalized_to_original = {}

        for col in df.columns:
            normalized_to_original[self._normalize_col_name(col)] = col

        mapped_columns = self._model_map_columns(df, confidence_threshold=self.mapper_confidence_threshold)
        for canonical, alias_candidates in aliases.items():
            if canonical in mapped_columns:
                continue

            canonical_norm = self._normalize_col_name(canonical)

            if canonical in df.columns:
                mapped_columns[canonical] = canonical
                continue

            if canonical_norm in normalized_to_original:
                mapped_columns[canonical] = normalized_to_original[canonical_norm]
                continue

            for alias in alias_candidates:
                alias_norm = self._normalize_col_name(alias)
                if alias_norm in normalized_to_original:
                    mapped_columns[canonical] = normalized_to_original[alias_norm]
                    break

        # Heuristic fallback for mandatory fields if alias matching failed.
        if 'Date' not in mapped_columns:
            used_sources = set(mapped_columns.values())
            best_date_col = None
            best_date_score = -1.0
            for col in df.columns:
                if col in used_sources:
                    continue
                parsed = self._coerce_datetime_series(df[col])
                parse_rate = float(parsed.notna().mean())
                name_score = max(
                    self._similarity_score(col, alias)
                    for alias in ['date', 'sale_date', 'sale date', 'order_date', 'transaction_date']
                )
                score = parse_rate * 0.8 + name_score * 0.2
                if parse_rate >= 0.6 and score > best_date_score:
                    best_date_col = col
                    best_date_score = score
            if best_date_col:
                mapped_columns['Date'] = best_date_col

        if 'Total Amount' not in mapped_columns:
            used_sources = set(mapped_columns.values())
            best_amount_col = None
            best_amount_score = -1.0
            for col in df.columns:
                if col in used_sources:
                    continue
                parsed = self._coerce_numeric_series(df[col])
                parse_rate = float(parsed.notna().mean())
                if parse_rate < 0.6 or parsed.abs().sum() <= 0:
                    continue
                if not self._looks_like_amount_column(col, df[col]):
                    continue
                name_score = max(
                    self._similarity_score(col, alias)
                    for alias in ['amount', 'sales_amount', 'revenue', 'total_amount', 'sales']
                )
                variability = float(parsed.std()) if parsed.notna().sum() > 1 else 0.0
                variability_score = 1.0 if variability > 0 else 0.0
                score = parse_rate * 0.55 + name_score * 0.35 + variability_score * 0.10
                if score > best_amount_score:
                    best_amount_col = col
                    best_amount_score = score
            if best_amount_col:
                mapped_columns['Total Amount'] = best_amount_col

        if 'Customer ID' not in mapped_columns:
            used_sources = set(mapped_columns.values())
            best_col = None
            best_score = 0.0
            for col in df.columns:
                if col in used_sources:
                    continue
                unique_ratio = df[col].astype(str).nunique(dropna=True) / max(len(df), 1)
                normalized_col = self._normalize_col_name(col)
                name_hint = max(
                    self._similarity_score(col, alias)
                    for alias in ['customerid', 'customer', 'clientid', 'userid', 'memberid', 'accountid']
                )
                looks_transactional = any(
                    token in normalized_col for token in ['transaction', 'invoice', 'order', 'receipt', 'product']
                )

                # Prefer identifier-like columns with repeated entities.
                if unique_ratio < 0.01 or unique_ratio > 0.95:
                    continue

                score = (1.0 - abs(unique_ratio - 0.35)) * 0.7 + name_hint * 0.3
                if looks_transactional:
                    score *= 0.2

                if score > best_score:
                    best_col = col
                    best_score = score
            if best_col:
                mapped_columns['Customer ID'] = best_col

        # Ensure one source column maps to only one canonical field.
        role_priority = ['Date', 'Total Amount', 'Customer ID', 'Product Category', 'Region', 'Country', 'Gender', 'Age']
        deduped_mapping = {}
        used_sources = set()

        for role in role_priority:
            source_col = mapped_columns.get(role)
            if not source_col or source_col in used_sources:
                continue
            deduped_mapping[role] = source_col
            used_sources.add(source_col)

        for role, source_col in mapped_columns.items():
            if role in deduped_mapping:
                continue
            if not source_col or source_col in used_sources:
                continue
            deduped_mapping[role] = source_col
            used_sources.add(source_col)

        mapped_columns = deduped_mapping

        # Keep Customer ID only when confidence signals are strong enough.
        customer_col = mapped_columns.get('Customer ID')
        if customer_col and customer_col in df.columns:
            normalized_col = self._normalize_col_name(customer_col)
            unique_ratio = df[customer_col].astype(str).nunique(dropna=True) / max(len(df), 1)
            name_hint = max(
                self._similarity_score(customer_col, alias)
                for alias in ['customerid', 'customer', 'clientid', 'userid', 'memberid', 'accountid', 'buyerid']
            )
            conflicting_tokens = ['region', 'country', 'state', 'city', 'zone', 'location', 'category', 'segment', 'item', 'product']
            conflicts_with_non_customer = any(token in normalized_col for token in conflicting_tokens)

            weak_signal = name_hint < 0.45
            too_unique = unique_ratio > 0.95
            too_sparse = unique_ratio < 0.01

            if (weak_signal and (too_unique or too_sparse)) or (weak_signal and conflicts_with_non_customer):
                mapped_columns.pop('Customer ID', None)

        # Keep Total Amount only when semantic amount signals are strong enough.
        amount_col = mapped_columns.get('Total Amount')
        if amount_col and amount_col in df.columns:
            if not self._looks_like_amount_column(amount_col, df[amount_col]):
                mapped_columns.pop('Total Amount', None)

        renamed_df = df.copy()
        rename_map = {}
        for canonical, source_col in mapped_columns.items():
            if source_col != canonical and canonical not in renamed_df.columns:
                rename_map[source_col] = canonical

        if rename_map:
            renamed_df = renamed_df.rename(columns=rename_map)

        return renamed_df, mapped_columns

    def _read_csv_with_fallbacks(self, file_path):
        """Read CSV with encoding fallbacks for broader dataset compatibility."""
        encodings_to_try = [None, 'utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        last_error = None

        for enc in encodings_to_try:
            try:
                if enc is None:
                    return pd.read_csv(file_path), 'auto'
                return pd.read_csv(file_path, encoding=enc), enc
            except Exception as e:
                last_error = e

        raise last_error

    def _read_tabular_with_fallbacks(self, file_path):
        """Read supported tabular formats with fallbacks and return dataframe + metadata."""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.csv':
            df, encoding = self._read_csv_with_fallbacks(file_path)
            return df, {'format': 'csv', 'encoding': encoding}

        if ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            return df, {'format': 'excel', 'encoding': 'n/a'}

        if ext == '.json':
            df = pd.read_json(file_path)
            return df, {'format': 'json', 'encoding': 'n/a'}

        if ext == '.parquet':
            df = pd.read_parquet(file_path)
            return df, {'format': 'parquet', 'encoding': 'n/a'}

        raise ValueError(f"Unsupported file format: {ext}. Allowed: .csv, .xlsx, .xls, .json, .parquet")

    def _get_dataset_capabilities(self, df):
        """Detect what analyses are feasible for current mapped dataset."""
        cols = set(df.columns)

        has_basic = all(col in cols for col in ['Date', 'Total Amount'])
        has_customer = 'Customer ID' in cols
        has_product = 'Product Category' in cols
        has_demographic = any(col in cols for col in ['Age', 'Gender'])
        has_geo = any(col in cols for col in ['Region', 'Country'])

        return {
            'upload': True,
            'kpis': 'Total Amount' in cols,
            'trends': all(col in cols for col in ['Date', 'Total Amount']),
            'segmentation': has_customer and 'Total Amount' in cols,
            'top_categories': has_product and 'Total Amount' in cols,
            'forecast': all(col in cols for col in ['Date', 'Total Amount']),
            'churn_prediction': has_customer and has_basic and (has_demographic or has_product),
            'product_affinity': has_product and has_customer,
            'geographic_analysis': has_geo and 'Total Amount' in cols,
            'report_generation': has_basic,
            'chatbot': has_basic
        }

    def get_capability_requirements(self):
        """Return canonical column requirements for each analysis capability."""
        return {
            'kpis': ['Total Amount'],
            'trends': ['Date', 'Total Amount'],
            'segmentation': ['Customer ID', 'Total Amount'],
            'top_categories': ['Product Category', 'Total Amount'],
            'forecast': ['Date', 'Total Amount'],
            'churn_prediction': ['Customer ID', 'Date', 'Total Amount'],
            'product_affinity': ['Customer ID', 'Product Category'],
            'geographic_analysis': ['Total Amount', 'Region'],
            'report_generation': ['Date', 'Total Amount'],
            'chatbot': ['Date', 'Total Amount']
        }

    def build_analysis_plan(self, df):
        """Build analysis readiness matrix with missing-column diagnostics."""
        requirements = self.get_capability_requirements()
        capabilities = self._get_dataset_capabilities(df)
        present_cols = set(df.columns)

        plan = {}
        for capability, required_cols in requirements.items():
            missing = [col for col in required_cols if col not in present_cols]
            plan[capability] = {
                'enabled': bool(capabilities.get(capability, False)),
                'required_columns': required_cols,
                'missing_columns': missing
            }

        return plan

    def _profile_dataframe(self, df, source_columns=None, mapped_columns=None):
        """Build a data profile for UI/clients to understand schema and quality."""
        profile_columns = []

        for col in df.columns:
            series = df[col]
            dtype = str(series.dtype)
            null_count = int(series.isna().sum())
            total = max(len(series), 1)
            null_pct = round((null_count / total) * 100, 2)
            unique_count = int(series.nunique(dropna=True))
            sample = series.dropna().astype(str).head(3).tolist()

            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                as_date = pd.to_datetime(series, errors='coerce')
            date_parse_pct = round(float(as_date.notna().mean() * 100), 2)

            as_num = pd.to_numeric(series, errors='coerce')
            numeric_parse_pct = round(float(as_num.notna().mean() * 100), 2)

            profile_columns.append({
                'name': col,
                'dtype': dtype,
                'null_count': null_count,
                'null_pct': null_pct,
                'unique_count': unique_count,
                'sample_values': sample,
                'date_parse_pct': date_parse_pct,
                'numeric_parse_pct': numeric_parse_pct
            })

        mapping_validation = self.validate_mapped_columns(df)

        return {
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': profile_columns,
            'source_columns': source_columns or list(df.columns),
            'mapped_columns': mapped_columns or {},
            'mapping_issues': mapping_validation['mapping_issues'],
            'mapping_confidence': mapping_validation['mapping_confidence'],
            'capabilities': self._get_dataset_capabilities(df),
            'analysis_plan': self.build_analysis_plan(df)
        }

    def apply_manual_mapping(self, raw_df, mapping):
        """Apply user-provided canonical mapping and return validated canonical dataframe."""
        required = ['Date', 'Total Amount']
        missing_required = [c for c in required if c not in mapping]
        if missing_required:
            return {
                'success': False,
                'message': f"Missing mapping for required canonical columns: {', '.join(missing_required)}"
            }

        renamed_df = raw_df.copy()
        rename_map = {}

        for canonical, source in mapping.items():
            if source not in renamed_df.columns:
                return {
                    'success': False,
                    'message': f"Source column '{source}' not found in uploaded dataset"
                }
            if source != canonical and canonical not in renamed_df.columns:
                rename_map[source] = canonical

        if rename_map:
            renamed_df = renamed_df.rename(columns=rename_map)

        validation = self.validate_csv(renamed_df)
        if not validation['valid']:
            return {
                'success': False,
                'message': validation['error']
            }

        renamed_df['Date'] = self._coerce_datetime_series(renamed_df['Date'])
        renamed_df['Total Amount'] = self._coerce_numeric_series(renamed_df['Total Amount'])
        renamed_df['Month_Year'] = renamed_df['Date'].dt.to_period('M').astype(str)
        drop_cols = ['Total Amount', 'Date']
        if 'Customer ID' in renamed_df.columns:
            drop_cols.append('Customer ID')
        renamed_df = renamed_df.dropna(subset=drop_cols)
        mapping_validation = self.validate_mapped_columns(renamed_df)

        return {
            'success': True,
            'dataframe': renamed_df,
            'mapped_columns': mapping,
            'profile': self._profile_dataframe(renamed_df, list(raw_df.columns), mapping),
            'mapping_issues': mapping_validation['mapping_issues'],
            'mapping_confidence': mapping_validation['mapping_confidence'],
            'capabilities': self._get_dataset_capabilities(renamed_df),
            'analysis_plan': self.build_analysis_plan(renamed_df)
        }

    def profile_dataset(self, df, source_columns=None, mapped_columns=None):
        """Public helper to expose dataset profile and capabilities."""
        return self._profile_dataframe(df, source_columns, mapped_columns)

    def validate_mapped_columns(self, df):
        """Validate mapped canonical columns with simple rule-based checks."""
        issues = []
        major_issue = False
        minor_issue_count = 0

        def add_issue(message, severity='minor'):
            nonlocal major_issue, minor_issue_count
            issues.append(message)
            if severity == 'major':
                major_issue = True
            else:
                minor_issue_count += 1

        def _non_empty(series):
            clean = series.copy()
            if clean.dtype == object:
                clean = clean.replace(r'^\s*$', pd.NA, regex=True)
            return clean.dropna()

        if 'Date' in df.columns:
            date_values = _non_empty(df['Date'])
            if date_values.empty:
                add_issue('Date mapping is suspicious: column is empty after mapping.', severity='major')
            else:
                parsed_dates = self._coerce_datetime_series(date_values)
                date_parse_ratio = float(parsed_dates.notna().mean())
                if date_parse_ratio < 0.8:
                    severity = 'major' if date_parse_ratio < 0.5 else 'minor'
                    add_issue(
                        f'Date mapping is suspicious: only {date_parse_ratio:.0%} of values are parseable as dates.',
                        severity=severity
                    )
        else:
            add_issue('Date mapping is missing after column mapping.', severity='major')

        if 'Total Amount' in df.columns:
            amount_values = _non_empty(df['Total Amount'])
            if amount_values.empty:
                add_issue('Total Amount mapping is suspicious: column is empty after mapping.', severity='major')
            else:
                numeric_amounts = self._coerce_numeric_series(amount_values)
                numeric_ratio = float(numeric_amounts.notna().mean())
                if numeric_ratio < 0.95:
                    severity = 'major' if numeric_ratio < 0.75 else 'minor'
                    add_issue(
                        f'Total Amount mapping is suspicious: only {numeric_ratio:.0%} of values are numeric.',
                        severity=severity
                    )
                if numeric_amounts.dropna().lt(0).any():
                    add_issue('Total Amount contains negative values. Verify the mapped sales column.', severity='minor')
        else:
            add_issue('Total Amount mapping is missing after column mapping.', severity='major')

        if 'Customer ID' in df.columns:
            customer_values = _non_empty(df['Customer ID'].astype(str).str.strip())
            if customer_values.empty:
                add_issue('Customer ID mapping is suspicious: column is empty after mapping.', severity='major')
            else:
                uniqueness_ratio = float(customer_values.nunique(dropna=True) / max(len(customer_values), 1))
                if uniqueness_ratio <= 0.2:
                    add_issue(
                        f'Customer ID mapping is suspicious: uniqueness ratio is {uniqueness_ratio:.0%}, which is too low for an identifier.',
                        severity='major'
                    )
                elif uniqueness_ratio < 0.35:
                    add_issue(
                        f'Customer ID mapping may be weak: uniqueness ratio is {uniqueness_ratio:.0%}.',
                        severity='minor'
                    )

                single_char_ratio = float(customer_values.str.len().le(1).mean())
                if single_char_ratio > 0.8:
                    add_issue('Customer ID mapping is suspicious: most values are too short to be stable identifiers.', severity='minor')
        else:
            add_issue('Customer ID mapping is missing. Customer-level analysis may be unreliable.', severity='minor')

        if 'Product Category' in df.columns:
            category_values = _non_empty(df['Product Category'].astype(str).str.strip())
            total_rows = max(len(df), 1)
            non_empty_ratio = float(len(category_values) / total_rows)
            unique_categories = int(category_values.nunique(dropna=True))

            if non_empty_ratio < 0.5:
                add_issue(
                    f'Product Category mapping is suspicious: only {non_empty_ratio:.0%} of rows have category values.',
                    severity='minor'
                )
            if category_values.empty or unique_categories < 2:
                add_issue('Product Category mapping is suspicious: expected multiple non-empty category values.', severity='minor')
        else:
            add_issue('Product Category mapping is missing. Category analysis may be limited.', severity='minor')

        if major_issue or minor_issue_count > 2:
            mapping_confidence = 'LOW'
        elif minor_issue_count > 0:
            mapping_confidence = 'MEDIUM'
        else:
            mapping_confidence = 'HIGH'

        return {
            'mapping_issues': issues,
            'mapping_confidence': mapping_confidence
        }
    
    def validate_csv(self, df):
        """Validate CSV structure"""
        required_columns = ['Date', 'Total Amount']
        missing = [col for col in required_columns if col not in df.columns]
        
        if missing:
            return {
                'valid': False,
                'error': f"Missing required columns: {', '.join(missing)}"
            }
        
        # Check data types
        try:
            df['Date'] = self._coerce_datetime_series(df['Date'])
            df['Total Amount'] = self._coerce_numeric_series(df['Total Amount'])
            if 'Customer ID' in df.columns:
                df['Customer ID'] = df['Customer ID'].astype(str)

            if df['Date'].isna().all():
                return {
                    'valid': False,
                    'error': 'Date column could not be parsed. Provide a recognizable date format.'
                }

            if df['Total Amount'].isna().all():
                return {
                    'valid': False,
                    'error': 'Total Amount column could not be parsed as numeric values.'
                }
        except Exception as e:
            return {
                'valid': False,
                'error': f"Data type conversion error: {str(e)}"
            }
        
        return {'valid': True}
    
    def load_user_data(self, file_path):
        """Load and validate user CSV"""
        try:
            original_df, file_meta = self._read_tabular_with_fallbacks(file_path)
            original_df = self._sanitize_dataframe(original_df)
            data_health_snapshot = self.build_data_health_snapshot(original_df)
            data_quality = self.data_quality_service.calculate(original_df)

            # Auto-map schema for varied dataset column names.
            df, mapped_columns = self._auto_map_columns(original_df)
            mapping_validation = self.validate_mapped_columns(df)
            
            # Validate
            validation = self.validate_csv(df)
            if not validation['valid']:
                exploratory_summary = self.build_exploratory_summary(original_df)
                suggestions = self.suggest_mapping_candidates(original_df, top_n=3)
                capabilities = self._build_exploratory_capabilities()
                insights = self.insight_builder.build(original_df, data_quality, {'mode': 'exploratory_only'})

                return {
                    'success': True,
                    'mode': 'exploratory_only',
                    'message': f"{validation['error']} Switched to exploratory fallback mode.",
                    'dataframe': original_df,
                    'raw_dataframe': original_df,
                    'row_count': len(original_df),
                    'columns': original_df.columns.tolist(),
                    'source_columns': original_df.columns.tolist(),
                    'mapped_columns': mapped_columns,
                    'encoding': file_meta.get('encoding', 'auto'),
                    'format': file_meta.get('format', 'csv'),
                    'capabilities': capabilities,
                    'profile': self._profile_dataframe(original_df, original_df.columns.tolist(), mapped_columns),
                    'mapping_issues': mapping_validation['mapping_issues'],
                    'mapping_confidence': mapping_validation['mapping_confidence'],
                    'data_quality': data_quality,
                    'insights': insights,
                    'data_health_snapshot': data_health_snapshot,
                    'analysis_plan': self.build_analysis_plan(original_df),
                    'exploratory_summary': exploratory_summary,
                    'mapping_suggestions': suggestions,
                    'required_columns': ['Customer ID', 'Date', 'Total Amount'],
                    'detected_columns': original_df.columns.tolist()
                }
            
            # Clean data
            df['Date'] = self._coerce_datetime_series(df['Date'])
            df['Total Amount'] = self._coerce_numeric_series(df['Total Amount'])
            df['Month_Year'] = df['Date'].dt.to_period('M').astype(str)
            drop_cols = ['Total Amount', 'Date']
            if 'Customer ID' in df.columns:
                drop_cols.append('Customer ID')
            df = df.dropna(subset=drop_cols)

            capabilities = self._get_dataset_capabilities(df)
            profile = self._profile_dataframe(df, original_df.columns.tolist(), mapped_columns)
            analysis_plan = self.build_analysis_plan(df)
            insights = self.insight_builder.build(df, data_quality, {'mode': 'full_analytics'})
            
            return {
                'success': True,
                'mode': 'full_analytics',
                'dataframe': df,
                'raw_dataframe': original_df,
                'row_count': len(df),
                'columns': df.columns.tolist(),
                'source_columns': original_df.columns.tolist(),
                'mapped_columns': mapped_columns,
                'encoding': file_meta.get('encoding', 'auto'),
                'format': file_meta.get('format', 'csv'),
                'capabilities': capabilities,
                'profile': profile,
                'mapping_issues': mapping_validation['mapping_issues'],
                'mapping_confidence': mapping_validation['mapping_confidence'],
                'data_quality': data_quality,
                'insights': insights,
                'data_health_snapshot': data_health_snapshot,
                'analysis_plan': analysis_plan
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f"Error loading file: {str(e)}"
            }
    
    def calculate_rfm(self, df):
        """Calculate RFM metrics from dataframe"""
        try:
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
            
            return rfm
        
        except Exception as e:
            print(f"Error calculating RFM: {e}")
            return None
    
    def apply_segmentation(self, rfm):
        """Apply K-Means clustering for customer segmentation"""
        try:
            if self.scaler is None or self.segmentation_model is None:
                return {
                    'success': False,
                    'message': 'Segmentation model not loaded'
                }
            
            rfm_scaled = self.scaler.transform(rfm)
            rfm['Cluster'] = self.segmentation_model.predict(rfm_scaled)
            
            # Generate segment profiles
            segment_profiles = {}
            for cluster in sorted(rfm['Cluster'].unique()):
                subset = rfm[rfm['Cluster'] == cluster]
                segment_profiles[f'Segment_{cluster}'] = {
                    'count': len(subset),
                    'avg_recency': float(subset['Recency'].mean()),
                    'avg_frequency': float(subset['Frequency'].mean()),
                    'avg_monetary': float(subset['Monetary'].mean()),
                    'total_revenue': float(subset['Monetary'].sum())
                }
            
            return {
                'success': True,
                'segments': segment_profiles,
                'rfm_data': rfm.to_dict()
            }
        
        except Exception as e:
            print(f"Error in segmentation: {e}")
            return {
                'success': False,
                'message': f'Segmentation error: {str(e)}'
            }
    
    def apply_forecasting(self, df):
        """Apply time-series forecasting"""
        try:
            if self.forecast_model is None:
                return {
                    'success': False,
                    'message': 'Forecast model not loaded'
                }
            
            # Prepare time-series data
            df_time = df.copy()
            df_time.set_index('Date', inplace=True)
            
            weekly_sales = df_time['Total Amount'].resample('W').sum().reset_index()
            weekly_sales['Week_Number'] = weekly_sales['Date'].dt.isocalendar().week
            weekly_sales['Month'] = weekly_sales['Date'].dt.month
            weekly_sales['Lag_1'] = weekly_sales['Total Amount'].shift(1)
            weekly_sales = weekly_sales.dropna()

            if weekly_sales.empty:
                return {
                    'success': False,
                    'message': 'Insufficient time-series history for forecasting (need at least 2 periods).'
                }
            
            # Get last 12 weeks for display
            last_weeks = weekly_sales.tail(12)
            
            # Forecast next 4 weeks
            last_row = weekly_sales.iloc[-1]
            future_forecasts = []
            
            for i in range(1, 5):
                next_week_data = {
                    'Week_Number': (last_row['Week_Number'] + i - 1) % 52 + 1,
                    'Month': ((last_row['Month'] + (last_row['Week_Number'] + i - 1) // 4) - 1) % 12 + 1,
                    'Lag_1': weekly_sales.iloc[-1]['Total Amount'] if i == 1 else future_forecasts[-1]['forecast']
                }
                
                features_df = pd.DataFrame([next_week_data])
                forecast_value = float(self.forecast_model.predict(features_df)[0])
                
                future_forecasts.append({
                    'week': int(next_week_data['Week_Number']),
                    'forecast': forecast_value
                })
            
            return {
                'success': True,
                'historical': last_weeks[['Date', 'Total Amount']].to_dict('records'),
                'forecast': future_forecasts
            }
        
        except Exception as e:
            print(f"Error in forecasting: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Forecasting error: {str(e)}'
            }
    
    def apply_churn_prediction(self, df):
        """Predict customer churn risk"""
        try:
            if self.churn_model is None:
                return {
                    'success': False,
                    'message': 'Churn model not loaded'
                }
            
            # Prepare features
            max_date = df['Date'].max()
            df['Days_Since_Purchase'] = (max_date - df['Date']).dt.days
            df['Is_At_Risk'] = (df['Days_Since_Purchase'] > 180).astype(int)
            
            # Select features
            try:
                features = ['Age', 'Gender', 'Product Category']
                X = pd.get_dummies(df[features], drop_first=True)
            except KeyError:
                # If some features are missing, create dummy dataframe
                X = pd.DataFrame()
                if 'Age' in df.columns:
                    X['Age'] = df['Age']
                if 'Gender' in df.columns:
                    X = pd.concat([X, pd.get_dummies(df['Gender'], prefix='Gender')], axis=1)
                if 'Product Category' in df.columns:
                    X = pd.concat([X, pd.get_dummies(df['Product Category'], prefix='Category')], axis=1)

            # Align inference features with training schema if available.
            if self.churn_features:
                for col in self.churn_features:
                    if col not in X.columns:
                        X[col] = 0
                X = X[self.churn_features]
            
            # Get churn predictions
            churn_probs = self.churn_model.predict_proba(X)[:, 1]
            
            at_risk_customers = df.copy()
            at_risk_customers['churn_risk_score'] = churn_probs
            at_risk_customers = at_risk_customers[at_risk_customers['churn_risk_score'] > 0.5]
            
            high_risk_count = len(at_risk_customers)
            revenue_at_risk = float(at_risk_customers['Total Amount'].sum())
            
            return {
                'success': True,
                'at_risk_count': high_risk_count,
                'revenue_at_risk': revenue_at_risk,
                'high_risk_customers': at_risk_customers[['Customer ID', 'churn_risk_score']].head(10).to_dict('records')
            }
        
        except Exception as e:
            print(f"Error in churn prediction: {e}")
            return {
                'success': False,
                'message': f'Churn prediction error: {str(e)}'
            }
    
    def generate_business_snapshot(self, df):
        """Generate high-level KPIs"""
        return {
            'total_revenue': float(df['Total Amount'].sum()),
            'avg_order_value': float(df['Total Amount'].mean()),
            'unique_customers': int(df['Customer ID'].nunique()),
            'total_orders': len(df),
            'date_range': {
                'start': str(df['Date'].min().date()),
                'end': str(df['Date'].max().date())
            }
        }
