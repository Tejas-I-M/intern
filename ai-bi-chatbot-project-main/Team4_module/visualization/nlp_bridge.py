"""
visualization/nlp_bridge.py

Team 4 integration layer.
Connects Team 2 (NLP) and Team 3 (Analytics Engine) to the Streamlit dashboard.

File lives at:
    ai-bi-chatbot-project/
    └── Team4_module/
        └── visualization/
            └── nlp_bridge.py   ← THIS FILE
"""

import sys
import os
import pickle
import requests
from typing import Dict, Any, Optional


# ── Resolve project root ───────────────────────────────────────────────────────
# This file lives at: <project_root>/Team4_module/visualization/nlp_bridge.py
# Go THREE levels up: nlp_bridge.py → visualization/ → Team4_module/ → project_root/

_THIS_FILE   = os.path.abspath(__file__)
_VISUAL_DIR  = os.path.dirname(_THIS_FILE)   # .../Team4_module/visualization/
_TEAM4_DIR   = os.path.dirname(_VISUAL_DIR)  # .../Team4_module/
PROJECT_ROOT = os.path.dirname(_TEAM4_DIR)   # .../ai-bi-chatbot-project/  ✅

print(f"[NLP Bridge] Project root resolved to: {PROJECT_ROOT}")


# ── Service config ────────────────────────────────────────────────────────────
ANALYTICS_URL = os.getenv("ANALYTICS_URL", "http://127.0.0.1:8000")

# Models live at: <project_root>/models/
NLP_MODELS_DIR = os.getenv(
    "NLP_MODELS_DIR",
    os.path.join(PROJECT_ROOT, "models")
)


# ── Load Team 2 NLP models ────────────────────────────────────────────────────
_model      = None
_vectorizer = None
_nlp_ok     = False

_intent_model_path = os.path.join(NLP_MODELS_DIR, "intent_model.pkl")
_vectorizer_path   = os.path.join(NLP_MODELS_DIR, "vectorizer.pkl")

try:
    with open(_intent_model_path, "rb") as f:
        _model = pickle.load(f)
    with open(_vectorizer_path, "rb") as f:
        _vectorizer = pickle.load(f)
    _nlp_ok = True
    print(f"[NLP Bridge] ✅ Models loaded from: {NLP_MODELS_DIR}")
except FileNotFoundError as e:
    print(f"[NLP Bridge] ❌ Model file not found: {e}")
    print(f"[NLP Bridge]    Looked in: {NLP_MODELS_DIR}")
except Exception as e:
    print(f"[NLP Bridge] ❌ Unexpected error loading models: {e}")


# ── Import Team 2 NLP utilities ───────────────────────────────────────────────
# Team 2 files live at: <project_root>/Team2_module/
_nlp_utils_ok = False

_team2_paths = [
    os.path.join(PROJECT_ROOT, "Team2_module"),
    os.path.join(PROJECT_ROOT, "Team2_module", "nlp"),
    os.path.join(PROJECT_ROOT, "nlp"),
]

for _path in _team2_paths:
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)
        print(f"[NLP Bridge] Added to sys.path: {_path}")

try:
    from entity_extractor   import extract_entities
    from query_builder      import build_query
    from response_generator import generate_response
    _nlp_utils_ok = True
    print("[NLP Bridge] ✅ Team 2 NLP utilities loaded.")
except ImportError as e:
    print(f"[NLP Bridge] ⚠️  Team 2 utilities not imported: {e}. Using fallback stubs.")

    def extract_entities(text):
        return {"metric": "sales", "group_by": None, "top_n": None, "filters": {}}

    def build_query(intent, entities):
        return {"intent": intent, **entities}

    def generate_response(result):
        data    = result.get("data", [])
        insight = result.get("insight", "")
        if not data:
            return "No data found for your query."
        if isinstance(data, list):
            rows = "\n".join(
                f"{i+1}. {' | '.join(str(v) for v in row.values())}"
                for i, row in enumerate(data[:5])
            )
            return f"✅ Top Results:\n{rows}" + (f"\n\n💡 Insight: {insight}" if insight else "")
        if isinstance(data, dict) and "forecast" in data:
            return f"📈 Forecast: {data['forecast']}"
        return str(data)


# ── Team 3 analytics client ───────────────────────────────────────────────────
def _call_analytics(structured_query: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = requests.post(
            f"{ANALYTICS_URL}/analyze",
            json=structured_query,
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Analytics API is offline. Run: python -m uvicorn api.main:app --reload"
        }
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Analytics API timed out (>5s)."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _check_analytics_health() -> bool:
    try:
        r = requests.get(f"{ANALYTICS_URL}/", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def ask_question(user_query: str) -> Dict[str, Any]:
    """
    Full NLP → Analytics → Response pipeline.

    Returns a dict:
        {
          "intent":      str,
          "confidence":  float,
          "entities":    dict,
          "raw_result":  dict,
          "response":    str,
          "chart_data":  list | None,
        }
    """
    if not _nlp_ok:
        return {
            "intent":     "unknown",
            "confidence": 0.0,
            "entities":   {},
            "raw_result": {},
            "response":   (
                f"❌ NLP models not found.\n"
                f"Expected location: {NLP_MODELS_DIR}\n"
                f"Fix: Run `python Team2_module/intent_classifier.py` from the project root."
            ),
            "chart_data": None,
        }

    # Step 1 — Intent classification (Team 2 model)
    X          = _vectorizer.transform([user_query])
    intent     = _model.predict(X)[0]
    confidence = float(_model.predict_proba(X).max())

    # Step 2 — Entity extraction (Team 2)
    entities = extract_entities(user_query)

    # Step 3 — Query building (Team 2)
    structured_query = build_query(intent, entities)

    # Step 4 — Analytics execution (Team 3 FastAPI)
    raw_result = _call_analytics(structured_query)

    # Step 5 — Response generation (Team 2)
    response_text = generate_response(raw_result)

    # Step 6 — Extract chart-ready data for Plotly visualizations
    chart_data = None
    if raw_result.get("status") == "success":
        data = raw_result.get("data")
        if isinstance(data, list) and len(data) > 0:
            chart_data = data

    return {
        "intent":     intent,
        "confidence": confidence,
        "entities":   entities,
        "raw_result": raw_result,
        "response":   response_text,
        "chart_data": chart_data,
    }


def get_bridge_status() -> Dict[str, str]:
    """
    Returns health status of each dependency for dashboard status badges.
    """
    return {
        "nlp_models":       "online" if _nlp_ok                  else "offline",
        "nlp_utils":        "online" if _nlp_utils_ok             else "offline",
        "analytics_engine": "online" if _check_analytics_health() else "offline",
    }


# Convenience export used in dashboard status bar
BRIDGE_STATUS = get_bridge_status()
