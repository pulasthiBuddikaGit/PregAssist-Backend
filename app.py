from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from pymongo import MongoClient
import os

from model_core import analyze_maternal_health
from services.rules import detect_warnings
from services.score import calculate_health_score
from services.forecast import forecast_risk
from services.recommendation import build_recommendation

app = Flask(__name__)
CORS(app)

# 🔥 MONGODB CONNECTION
MONGO_URI = os.getenv("MONGO_URI") or "your_mongodb_connection_string"
client = MongoClient(MONGO_URI)
db = client["maternal_db"]
vitals_col = db["vitals"]


# ================= HEALTH CHECK =================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Flask API running"})


# ================= PREDICT =================
@app.route("/predict", methods=["POST"])
def predict():

    data = request.get_json()

    motherId = data.get("motherId")
    week = data.get("week")
    trimester = data.get("trimester", 1)
    vitals = data.get("vitals")

    if not vitals or len(vitals) != 6:
        return jsonify({"error": "Invalid input"}), 400

    # ================= 1. MODEL =================
    result = analyze_maternal_health(vitals, trimester=trimester)

    risk_code = result["risk_level"]
    risk_name = result["risk_name"]
    confidence = result["confidence_percentage"]

    age, sbp, dbp, bs, temp, hr = vitals

    # ================= 2. WARNINGS =================
    warnings = detect_warnings(sbp, dbp, bs, hr)

    # ================= 3. HEALTH SCORE =================
    health_score = calculate_health_score(confidence, risk_code)

    # ================= 4. FEATURE IMPORTANCE (🔥 FIX) =================
    importance = result.get("importance")

    # 🔥 fallback if model didn't return
    if not importance:
        feature_names = ["Age", "SystolicBP", "DiastolicBP", "BS", "BodyTemp", "HeartRate"]
        importance = {f: 0.1 for f in feature_names}

    print("IMPORTANCE:", importance)  # debug

    # ================= 5. SAVE TO MONGO =================
    record = {
        "motherId": motherId,
        "createdAt": datetime.utcnow(),
        "Week": week,
        "Age": age,
        "SystolicBP": sbp,
        "DiastolicBP": dbp,
        "BS": bs,
        "BodyTemp": temp,
        "HeartRate": hr,
        "risk_level": risk_name,
        "confidence": confidence,
    }

    try:
        vitals_col.insert_one(record)
        print("Saved to MongoDB:", record)
    except Exception as e:
        print("MongoDB error:", e)

    # ================= 6. HISTORY =================
    try:
        history_cursor = vitals_col.find({"motherId": motherId}).sort("createdAt", 1)
        history = []
        for doc in history_cursor:
            doc["_id"] = str(doc["_id"])
            if "createdAt" in doc:
                doc["createdAt"] = doc["createdAt"].isoformat()
            history.append(doc)
    except Exception as e:
        print("History fetch error:", e)
        history = []

    # ================= 7. FORECAST =================
    forecast = forecast_risk(history)

    # ================= 8. RECOMMENDATION =================
    recommendation = build_recommendation(risk_name, warnings, forecast)

    # ================= 9. ALERT =================
    doctor_alert = (
        risk_name == "high risk"
        or any(w["severity"] == "high" for w in warnings)
        or forecast.get("trend") == "increasing"
    )

    # ================= 10. RESPONSE =================
    return jsonify({
        "risk_level": risk_name,
        "confidence": confidence,
        "health_score": health_score,
        "warnings": warnings,
        "top_factor": result.get("top_contributor", "Unknown"),
        "importance": importance,  # 🔥 THIS FIXES YOUR SCREEN
        "forecast": forecast,
        "recommendation": recommendation,
        "doctor_alert": doctor_alert,
        "advice": result.get("advice", ""),
        "history": history,
    })

@app.route("/history/<motherId>", methods=["GET"])
def get_history(motherId):
    records = list(vitals_col.find({"motherId": motherId}).sort("createdAt", -1))

    for r in records:
        r["_id"] = str(r["_id"])
        if "createdAt" in r:
            r["createdAt"] = r["createdAt"].isoformat()

    return jsonify(records)


@app.route("/alerts/critical", methods=["GET"])
def get_critical_alerts():
    # Fetch all records with risk_level == "high risk", sorted by createdAt descending
    records = list(vitals_col.find({"risk_level": "high risk"}).sort("createdAt", -1))
    
    for r in records:
        r["_id"] = str(r["_id"])
        if "createdAt" in r:
            r["createdAt"] = r["createdAt"].isoformat()

    return jsonify(records)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)