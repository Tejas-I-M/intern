#!/usr/bin/env python3
"""Train a column-mapper model for canonical schema alignment.

Input CSV schema (required columns):
- column_name: original source column name
- sample_values: pipe-separated sample values from that column
- dtype: source dtype string (example: object, float64, datetime64[ns])
- label: canonical target label

Supported labels (recommended):
- Customer ID
- Date
- Total Amount
- Product Category
- Gender
- Age
- Country
- Region

Usage:
python scripts/train_column_mapper.py \
  --training-data scripts/column_mapper_training_data.csv \
  --models-dir ../models
"""

import argparse
import os
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder


def _build_feature_text(df: pd.DataFrame) -> pd.Series:
    """Combine name, dtype and sample text into one string feature."""
    col_name = df["column_name"].astype(str)
    sample_values = df["sample_values"].fillna("").astype(str)
    dtypes = df["dtype"].fillna("unknown").astype(str)
    return (
        "name:" + col_name
        + " dtype:" + dtypes
        + " samples:" + sample_values
    )


def _load_training_data(training_data_files):
    """Load and merge one or more labeled training CSV files."""
    required_cols = ["column_name", "sample_values", "dtype", "label"]
    frames = []

    for path in training_data_files:
        df = pd.read_csv(path)
        missing = set(required_cols) - set(df.columns)
        if missing:
            raise ValueError(
                f"Training CSV '{path}' missing columns: {', '.join(sorted(missing))}"
            )

        frame = df[required_cols].copy()
        frame["column_name"] = frame["column_name"].astype(str).str.strip()
        frame["sample_values"] = frame["sample_values"].fillna("").astype(str).str.strip()
        frame["dtype"] = frame["dtype"].fillna("unknown").astype(str).str.strip()
        frame["label"] = frame["label"].astype(str).str.strip()
        frames.append(frame)

    merged = pd.concat(frames, ignore_index=True)
    merged = merged[merged["column_name"] != ""]
    merged = merged[merged["label"] != ""]
    merged = merged.drop_duplicates(subset=required_cols).reset_index(drop=True)

    if merged.empty:
        raise ValueError("No valid labeled rows found after merge/cleanup.")

    return merged


def train(training_data_files, models_dir: str, test_size: float = 0.2, random_state: int = 42, calibrate: bool = True):
    data = _load_training_data(training_data_files)

    class_counts = data["label"].value_counts().sort_values(ascending=False)
    print(f"Rows after cleanup: {len(data)}")
    print("Label distribution:")
    for label, count in class_counts.items():
        print(f"  - {label}: {count}")

    X_df = data[["column_name", "sample_values", "dtype"]].copy()
    X = _build_feature_text(X_df)
    y_raw = data["label"].astype(str)

    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    label_counts = pd.Series(y).value_counts()
    stratify_target = y if int(label_counts.min()) >= 2 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_target,
    )

    base_classifier = LogisticRegression(max_iter=2000, class_weight="balanced")
    classifier = base_classifier

    if calibrate:
        min_class_count_train = int(pd.Series(y_train).value_counts().min())
        if min_class_count_train >= 2:
            cv_folds = min(3, min_class_count_train)
            classifier = CalibratedClassifierCV(estimator=base_classifier, method="sigmoid", cv=cv_folds)
            print(f"Calibration enabled (method=sigmoid, cv={cv_folds})")
        else:
            print("Calibration skipped: each class needs at least 2 train samples.")

    pipeline = Pipeline([
        ("vectorizer", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("classifier", classifier)
    ])

    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)

    acc = accuracy_score(y_test, preds)
    print(f"Accuracy: {acc:.4f}")
    print("\nClassification report:")
    all_labels = list(range(len(le.classes_)))
    print(
        classification_report(
            y_test,
            preds,
            labels=all_labels,
            target_names=le.classes_,
            zero_division=0,
        )
    )

    recommended_threshold = None
    if hasattr(pipeline, "predict_proba"):
        probs = pipeline.predict_proba(X_test)
        max_probs = probs.max(axis=1)
        correct_mask = preds == y_test
        if bool(np.any(correct_mask)):
            recommended_threshold = float(np.quantile(max_probs[correct_mask], 0.25))
            print(f"\nRecommended confidence threshold: {recommended_threshold:.3f}")
            print("(Set COLUMN_MAPPER_CONFIDENCE_THRESHOLD to this value and tune +/-0.05)")

    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "column_mapper_model.pkl")
    encoder_path = os.path.join(models_dir, "column_mapper_label_encoder.pkl")
    metadata_path = os.path.join(models_dir, "column_mapper_metadata.json")

    joblib.dump(pipeline, model_path)
    joblib.dump(le, encoder_path)

    metadata = {
        "training_rows": int(len(data)),
        "label_counts": {str(k): int(v) for k, v in class_counts.items()},
        "calibrated": bool(calibrate),
        "recommended_confidence_threshold": round(recommended_threshold, 3) if recommended_threshold is not None else None,
        "random_state": int(random_state),
        "test_size": float(test_size),
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved model to: {model_path}")
    print(f"Saved label encoder to: {encoder_path}")
    print(f"Saved metadata to: {metadata_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train canonical column mapper model")
    parser.add_argument(
        "--training-data",
        required=True,
        nargs="+",
        help="One or more labeled training CSV files (space-separated)",
    )
    parser.add_argument("--models-dir", default="../models", help="Output directory for model artifacts")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test split ratio")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed")
    parser.add_argument("--no-calibration", action="store_true", help="Disable probability calibration")
    args = parser.parse_args()

    train(
        training_data_files=args.training_data,
        models_dir=args.models_dir,
        test_size=args.test_size,
        random_state=args.random_state,
        calibrate=not args.no_calibration,
    )
