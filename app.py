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

# 🔥 MONGODB CONNECTION (ADD THIS)
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

    # 1. MODEL OUTPUT
    result = analyze_maternal_health(vitals, trimester=trimester)

    risk_code = result["risk_level"]
    risk_name = result["risk_name"]
    confidence = result["confidence_percentage"]

    age, sbp, dbp, bs, temp, hr = vitals

    # 2. WARNINGS
    warnings = detect_warnings(sbp, dbp, bs, hr)

    # 3. HEALTH SCORE
    health_score = calculate_health_score(confidence, risk_code)

    # 🔥 4. SAVE TO MONGODB (NEW)

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
    vitals_col.insert_one(record)
    print("Saved to MongoDB:", record)

    #  5. FETCH HISTORY (NEW)
    history_cursor = vitals_col.find({"motherId": motherId}).sort("createdAt", 1)

    history = list(history_cursor)

    #  6. REAL FORECAST (NEW)
    forecast = forecast_risk(history)

    # 7. RECOMMENDATION
    recommendation = build_recommendation(risk_name, warnings, forecast)

    # 8. ALERT LOGIC
    doctor_alert = (
        risk_name == "high risk"
        or any(w["severity"] == "high" for w in warnings)
        or forecast.get("trend") == "increasing"
    )

    # 9. RESPONSE
    return jsonify(
        {
            "risk_level": risk_name,
            "confidence": confidence,
            "health_score": health_score,
            "warnings": warnings,
            "top_factor": result["top_contributor"],
            "forecast": forecast,
            "recommendation": recommendation,
            "doctor_alert": doctor_alert,
            "advice": result["advice"],
        }
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)
