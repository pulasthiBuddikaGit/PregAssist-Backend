def calculate_health_score(confidence_percentage, risk_code):

    confidence = float(confidence_percentage)

    if risk_code == 0:  # low risk
        return int(80 + (confidence * 0.2))

    elif risk_code == 1:  # mid risk
        return int(50 + (confidence * 0.2))

    else:  # high risk
        return int(20 + (confidence * 0.1))