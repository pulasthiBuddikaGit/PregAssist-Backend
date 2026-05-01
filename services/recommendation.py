def build_recommendation(risk_name, warnings, forecast):
    messages = []

    if risk_name == "high risk":
        messages.append("Immediate medical consultation required.")

    for w in warnings:
        if w["type"] == "bp_warning":
            messages.append("Monitor blood pressure daily.")
        elif w["type"] == "sugar_warning":
            messages.append("Control sugar intake.")
        elif w["type"] == "heart_rate_warning":
            messages.append("Avoid stress and monitor heart rate.")

    if forecast["trend"] == "increasing":
        messages.append("Recent data shows worsening trend.")

    if not messages:
        messages.append("Continue routine prenatal care.")

    return " ".join(set(messages))