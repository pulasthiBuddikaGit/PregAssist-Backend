from flask import Flask, request, jsonify
from flask_cors import CORS
from model_core import analyze_maternal_health

app = Flask(__name__)
CORS(app)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Flask API running"})

@app.route("/predict", methods=["POST"])
def predict():
    try:
        req_data = request.json

        trimester = int(req_data.get("trimester", 1))

        if "vitals" in req_data:
            vitals_data = req_data["vitals"]
        else:
            vitals_data = [
                float(req_data.get("Age")),
                float(req_data.get("SystolicBP")),
                float(req_data.get("DiastolicBP")),
                float(req_data.get("BS")),
                float(req_data.get("BodyTemp")),
                float(req_data.get("HeartRate")),
            ]

        result = analyze_maternal_health(vitals_data, trimester=trimester)
        return jsonify(result)

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)