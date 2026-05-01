from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime, timedelta
from model_core import analyze_maternal_health
import os
from services.rules import detect_warnings
from services.score import calculate_health_score
from services.forecast import forecast_risk
from services.recommendation import build_recommendation
from dotenv import load_dotenv

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PregAssist Trends API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# MongoDB Atlas connection
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI is not set")

client = MongoClient(MONGO_URI)
db = client["maternal_db"]
vitals_col = db["vitals"]


class VitalsSave(BaseModel):
    motherId: str
    Age: float
    SystolicBP: float
    DiastolicBP: float
    BS: float
    BodyTemp: float
    HeartRate: float
    trimester: int | None = None
    risk_level: str | None = None
    confidence: float | None = None


class PredictRequest(BaseModel):
    motherId: str
    trimester: int = 1
    vitals: list[float]


@app.post("/predict")
def predict(req: PredictRequest):

    # 1. MODEL OUTPUT
    result = analyze_maternal_health(req.vitals, trimester=req.trimester)

    risk_code = result["risk_level"]
    risk_name = result["risk_name"]
    confidence = result["confidence_percentage"]

    age, sbp, dbp, bs, temp, hr = req.vitals

    # 2. WARNING DETECTION
    warnings = detect_warnings(sbp, dbp, bs, hr)

    # 3. HEALTH SCORE
    health_score = calculate_health_score(confidence, risk_code)

    # 4. FETCH HISTORY (temporary user)
    history = []

    try:
        history_cursor = vitals_col.find(
            {"motherId": req.motherId}, {"_id": 0}
        ).sort("createdAt", 1)
        history = list(history_cursor)
    except Exception as e:
        print("Mongo history read failed:", e)
        history = []

    # 5. FORECAST
    forecast = forecast_risk(history)

    # 6. RECOMMENDATION
    recommendation = build_recommendation(risk_name, warnings, forecast)

    # 7. ALERT LOGIC
    doctor_alert = (
        risk_name == "high risk"
        or any(w["severity"] == "high" for w in warnings)
        or forecast["trend"] == "increasing"
    )

    # 8. SAVE CURRENT RECORD TO MONGODB
    record = {
        "motherId": "temp_user",   # later replace with real logged user id
        "createdAt": datetime.utcnow(),
        "Age": age,
        "SystolicBP": sbp,
        "DiastolicBP": dbp,
        "BS": bs,
        "BodyTemp": temp,
        "HeartRate": hr,
        "trimester": req.trimester,
        "risk_level": risk_name,
        "confidence": confidence,
        "health_score": health_score,
        "warnings": warnings,
        "forecast": forecast,
        "recommendation": recommendation,
        "doctor_alert": doctor_alert,
        "top_factor": result["top_contributor"],
        "advice": result["advice"]
    }

    try:
        vitals_col.insert_one(record)
    except Exception as e:
        print("Mongo save failed:", e)

    # 9. FINAL RESPONSE
    return {
        "risk_level": risk_name,
        "confidence": confidence,
        "health_score": health_score,
        "warnings": warnings,
        "top_factor": result["top_contributor"],
        "forecast": forecast,
        "recommendation": recommendation,
        "doctor_alert": doctor_alert,
        "advice": result["advice"]
    }


@app.get("/health")
def health():
    try:
        db.command("ping")
        return {"status": "ok", "mongo": "connected"}
    except Exception as e:
        return {"status": "ok", "mongo": "error", "details": str(e)}


@app.post("/vitals/save")
def save_vitals(v: VitalsSave):
    doc = v.model_dump()
    doc["createdAt"] = datetime.utcnow()
    vitals_col.insert_one(doc)
    return {"message": "saved"}


@app.get("/vitals/history")
def vitals_history(motherId: str, period: str = "weekly"):
    now = datetime.utcnow()

    if period == "weekly":
        start = now - timedelta(days=7)
    elif period == "monthly":
        start = now - timedelta(days=30)
    else:
        start = now - timedelta(days=7)

    cursor = vitals_col.find(
        {"motherId": motherId, "createdAt": {"$gte": start, "$lte": now}}, {"_id": 0}
    ).sort("createdAt", 1)

    data = []
    for r in cursor:
        r["createdAt"] = r["createdAt"].isoformat()
        data.append(r)

    return data
