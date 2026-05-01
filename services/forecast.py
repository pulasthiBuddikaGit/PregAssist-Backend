def forecast_risk(history):

    if len(history) < 3:
        return {
            "trend": "insufficient_data",
            "message": "Not enough data for trend analysis",
            "details": {}
        }

    last3 = history[-3:]

    try:
        bp = [h.get("SystolicBP", 0) for h in last3]
        sugar = [h.get("BS", 0) for h in last3]
        hr = [h.get("HeartRate", 0) for h in last3]

        score = 0

        # 🔥 PARAMETER LEVEL ANALYSIS
        bp_trend = "increasing" if bp[2] > bp[0] else "stable"
        sugar_trend = "increasing" if sugar[2] > sugar[0] else "stable"
        hr_trend = "increasing" if hr[2] > hr[0] else "stable"

        if bp_trend == "increasing":
            score += 1
        if sugar_trend == "increasing":
            score += 1
        if hr_trend == "increasing":
            score += 1

        # 🔥 FINAL DECISION
        if score >= 2:
            trend = "increasing"
            message = "Multiple health indicators rising"
        elif score == 1:
            trend = "slightly_increasing"
            message = "Some indicators increasing"
        else:
            trend = "stable"
            message = "No significant trend"

        return {
            "trend": trend,
            "message": message,
            "details": {
                "blood_pressure": bp_trend,
                "blood_sugar": sugar_trend,
                "heart_rate": hr_trend
            }
        }

    except Exception as e:
        print("Forecast error:", e)
        return {
            "trend": "stable",
            "message": "Trend analysis error",
            "details": {}
        }