def detect_warnings(sbp, dbp, bs, hr):
    warnings = []

    if sbp >= 140 or dbp >= 90:
        warnings.append({
            "type": "bp_warning",
            "message": "High blood pressure detected",
            "severity": "high"
        })

    if bs >= 7.0:
        warnings.append({
            "type": "sugar_warning",
            "message": "High blood sugar detected",
            "severity": "medium"
        })

    if hr >= 100:
        warnings.append({
            "type": "heart_rate_warning",
            "message": "High heart rate detected",
            "severity": "medium"
        })

    return warnings