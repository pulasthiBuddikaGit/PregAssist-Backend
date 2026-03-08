from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime, timedelta
from model_core import analyze_maternal_health
import os

app = FastAPI(title="PregAssist Trends API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# MongoDB Atlas connection
MONGO_URI = os.getenv("MONGO_URI")
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
    trimester: int = 1
    vitals: list[float]


@app.post("/predict")
def predict(req: PredictRequest):
    result = analyze_maternal_health(req.vitals, trimester=req.trimester)
    return result


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
