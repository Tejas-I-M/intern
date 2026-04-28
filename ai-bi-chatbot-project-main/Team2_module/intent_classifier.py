import os
import sys
import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model            import LogisticRegression
from sklearn.ensemble                import RandomForestClassifier
from sklearn.model_selection         import train_test_split, cross_val_score
from sklearn.metrics                 import classification_report, accuracy_score

sys.path.append(os.path.dirname(__file__))
from training_data import training_data

#TF-IDF Vectorization

texts  = [item[0] for item in training_data]
labels = [item[1] for item in training_data]

vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    min_df=1,
    stop_words="english"
)

X = vectorizer.fit_transform(texts)

X_train, X_test, y_train, y_test = train_test_split(
    X, labels,
    test_size=0.2,
    random_state=42,
    stratify=labels
)


# Training Classifiers
# Both Logistic Regression and Random Forest are trained.
# The model with higher test accuracy is selected automatically.


lr = LogisticRegression(max_iter=1000, random_state=42)
rf = RandomForestClassifier(n_estimators=100, random_state=42)

lr.fit(X_train, y_train)
rf.fit(X_train, y_train)

lr_acc = accuracy_score(y_test, lr.predict(X_test))
rf_acc = accuracy_score(y_test, rf.predict(X_test))

if lr_acc >= rf_acc:
    best_model, best_name, best_acc = lr, "Logistic Regression", lr_acc
else:
    best_model, best_name, best_acc = rf, "Random Forest", rf_acc


# Evaluating Accuracy
# Two evaluation methods are used:
#   Test accuracy    - performance on the held-out 20% test split.
#   Cross-validation - 5-fold CV averages results across different splits,
#                      giving a more reliable estimate of real-world accuracy.

y_pred    = best_model.predict(X_test)
cv_scores = cross_val_score(best_model, X, labels, cv=5)
report    = classification_report(y_test, y_pred)


# Saving accuracy report

BASE_DIR    = os.path.join(os.path.dirname(__file__), "..")
reports_dir = os.path.join(BASE_DIR, "reports")
os.makedirs(reports_dir, exist_ok=True)

with open(os.path.join(reports_dir, "intent_accuracy.txt"), "w", encoding="utf-8") as f:
    f.write("Phase 2 - Intent Classifier Accuracy Report\n")
    f.write("=" * 50 + "\n\n")
    f.write(f"Training examples       : {len(texts)}\n")
    f.write(f"Train / Test split      : 80% / 20%\n")
    f.write(f"Vectorizer              : TF-IDF  ngram_range=(1,2)\n\n")
    f.write(f"Logistic Regression     : {lr_acc * 100:.1f}%\n")
    f.write(f"Random Forest           : {rf_acc * 100:.1f}%\n")
    f.write(f"Selected model          : {best_name}\n\n")
    f.write(f"Test accuracy           : {best_acc * 100:.1f}%\n")
    f.write(f"Cross-val accuracy      : {cv_scores.mean() * 100:.1f}% "
            f"(+/- {cv_scores.std() * 100:.1f}%)\n\n")
    f.write("Intents covered:\n")
    f.write("  sales_query      - sales, month_id, qtr_id, year_id, revenue, profit\n")
    f.write("  ranking_query    - productline, country, customername, dealsize, territory\n")
    f.write("  comparison_query - year_id, territory, productline side-by-side\n")
    f.write("  forecast_query   - predict next month, quarter, or year\n")
    f.write("  hr_query         - attrition, headcount, salary (requires HR merge)\n\n")
    f.write("Per-intent breakdown:\n")
    f.write("-" * 50 + "\n")
    f.write(report)


# Saving model deliverables

models_dir = os.path.join(BASE_DIR, "models")
os.makedirs(models_dir, exist_ok=True)

with open(os.path.join(models_dir, "intent_model.pkl"), "wb") as f:
    pickle.dump(best_model, f)

with open(os.path.join(models_dir, "vectorizer.pkl"), "wb") as f:
    pickle.dump(vectorizer, f)