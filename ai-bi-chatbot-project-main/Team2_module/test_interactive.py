import pickle
import sys
import os

sys.path.append(os.path.dirname(__file__))

# ---------------- EXISTING (UNCHANGED) ----------------
with open("models/intent_model.pkl", "rb") as f:
    model = pickle.load(f)

with open("models/vectorizer.pkl", "rb") as f:
    vec = pickle.load(f)

print("Intent Classifier - Interactive Tester")
print("Type any query to see the predicted intent.")
print("Type 'quit' to exit.")
print("-" * 45)

# ---------------- NEW IMPORTS ----------------
try:
    from entity_extractor import extract_entities
    from query_builder import build_query
    from analytics_client import AnalyticsClient
    from response_generator import generate_response

    analytics_client = AnalyticsClient()

    ADVANCED_PIPELINE = True
except Exception as e:
    print(f"[WARNING] Advanced modules not loaded: {e}")
    ADVANCED_PIPELINE = False

# ---------------- LOOP ----------------
while True:
    query = input("\nYour query: ").strip()

    if query.lower() == "quit":
        print("Exiting.")
        break

    if not query:
        continue

    intent = model.predict(vec.transform([query]))[0]
    confidence = model.predict_proba(vec.transform([query])).max()

    if confidence >= 0.80:
        level = "High"
    elif confidence >= 0.50:
        level = "Medium"
    else:
        level = "Low - consider adding more training examples"

    print(f" Intent     : {intent}")
    print(f" Confidence : {confidence:.0%} ({level})")

    # ---------------- ADVANCED PIPELINE ----------------
    if ADVANCED_PIPELINE:
        try:
            # ✅ Step 1: Entity Extraction
            entities = extract_entities(query)
            print(f" Entities   : {entities}")

            # ✅ Step 2: Query Building
            structured_query = build_query(intent, entities)
            print(f" Structured Query : {structured_query}")
            # Step 1: Entity Extraction
            entities = extract_entities(query)

            # Step 2: Query Building
            structured_query = build_query(intent, entities)

            # 🔍 DEBUG BLOCK (ADD HERE)
            print("\n🔍 NLP DEBUG")
            print(f" Query      : {query}")
            print(f" Intent     : {intent}")
            print(f" Confidence : {confidence:.2f}")
            print(f" Entities   : {entities}")
            print(f" Structured : {structured_query}")

            # ✅ Step 3: Analytics Execution (API call)
            result = analytics_client.analyze(structured_query)
            print(f" Raw Result : {result}")

            # ✅ Step 4: Response Generation
            final_response = generate_response(result)
            print(f" Response   : {final_response}")

        except Exception as pipeline_error:
            print(f"[ERROR] Pipeline failed: {pipeline_error}")