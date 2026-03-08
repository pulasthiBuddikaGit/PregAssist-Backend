import pandas as pd
import numpy as np
import shap
import json
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix
from xgboost import XGBClassifier, plot_importance

# 1 LOAD DATASET

try:
    df = pd.read_csv("maternal_health_data.csv")
    df.columns = df.columns.str.strip()
    print("Dataset loaded successfully!")
except Exception as e:
    print("Dataset loading error:", e)

# 2 PREPROCESSING

risk_mapping_names = {
    0: "low risk",
    1: "mid risk",
    2: "high risk"
}

df["RiskLevel"] = df["RiskLevel"].map({
    "low risk": 0,
    "mid risk": 1,
    "high risk": 2
})

feature_cols = [
    "Age",
    "SystolicBP",
    "DiastolicBP",
    "BS",
    "BodyTemp",
    "HeartRate"
]

X = df[feature_cols]
y = df["RiskLevel"]

# 3 TRAIN MODEL

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    stratify=y,
    random_state=42
)

model = XGBClassifier(
    n_estimators=1200,
    learning_rate=0.05,
    max_depth=10,
    subsample=0.9,
    colsample_bytree=0.9,
    random_state=42,
    eval_metric="mlogloss"
)

model.fit(X_train, y_train)

print("Model trained successfully")

# 4 SHAP EXPLAINER

explainer = shap.TreeExplainer(model)


# UNIT CONVERSION FUNCTIONS

def celsius_to_fahrenheit(c):
    return (c * 9/5) + 32


def mgdl_to_mmol(value):
    return value / 18



# CORE PREDICTION FUNCTION


def analyze_maternal_health(input_list,
                            trimester=1,
                            temp_unit="C",
                            sugar_unit="mmol"):

    age, sbp, dbp, bs, temp, hr = input_list

    # Convert temperature if Celsius
    if temp_unit == "C":
        temp = celsius_to_fahrenheit(temp)

    # Convert sugar if mg/dL
    if sugar_unit == "mgdl":
        bs = mgdl_to_mmol(bs)

    processed_input = [age, sbp, dbp, bs, temp, hr]

    data_df = pd.DataFrame(
        [processed_input],
        columns=feature_cols
    )
   
    # MODEL PREDICTION


    risk_code = int(model.predict(data_df)[0])
    risk_name = risk_mapping_names[risk_code]

    probabilities = model.predict_proba(data_df)[0]

    confidence = float(np.max(probabilities) * 100)

    # SAFETY OVERRIDE RULES

    if sbp >= 180 or dbp >= 120:
        risk_code = 2
        risk_name = "high risk"

    if hr >= 140:
        risk_code = 2
        risk_name = "high risk"

    if temp >= 101:
        risk_code = 2
        risk_name = "high risk"

    if bs >= 11:
        risk_code = 2
        risk_name = "high risk"
   
    # SHAP ANALYSIS
    
    shap_values = explainer(data_df)

    if len(shap_values.values.shape) == 3:
        impacts = shap_values.values[0, :, risk_code]
    else:
        impacts = shap_values.values[0]

    shap_data = [(feature_cols[i], float(impacts[i])) for i in range(len(feature_cols))]

    shap_data = sorted(
        shap_data,
        key=lambda x: abs(x[1]),
        reverse=True
    )
   
    # MEDICAL GUIDELINES
    
    advice = []
    abnormal_found = False

    # Trimester context
    if trimester == 1:
        advice.append(
            "Trimester 1: Focus on folic acid intake and adequate rest."
        )

    elif trimester == 2:
        advice.append(
            "Trimester 2: Monitor fetal movement and maintain calcium intake."
        )

    elif trimester == 3:
        advice.append(
            "Trimester 3: Practice kick counting and monitor swelling."
        )

    # Blood pressure
    if sbp > 140 or dbp > 90:
        abnormal_found = True

        if trimester == 3:
            advice.append(
                "High BP in third trimester may indicate preeclampsia. Consult your doctor immediately."
            )
        else:
            advice.append(
                "Hypertension detected. Reduce salt intake and rest on left side."
            )

    elif sbp < 90 or dbp < 60:
        abnormal_found = True
        advice.append(
            "Low blood pressure detected. Increase hydration and stand slowly."
        )

    # Blood sugar
    if bs > 7.8:
        abnormal_found = True
        advice.append(
            "Elevated blood sugar detected. Follow a low glycemic diet and maintain light physical activity."
        )

    elif bs < 3.9:
        abnormal_found = True
        advice.append(
            "Low blood sugar detected. Consume a healthy snack immediately."
        )

    # Temperature
    if temp > 100.4:
        abnormal_found = True
        advice.append(
            "Fever detected. Possible infection. Please contact your healthcare provider."
        )

    elif temp < 95:
        abnormal_found = True
        advice.append(
            "Low body temperature detected. Keep warm and monitor symptoms."
        )

    # Heart rate
    if hr > 100:
        abnormal_found = True
        advice.append(
            "High heart rate detected. Avoid caffeine and practice deep breathing."
        )

    elif hr < 60:
        abnormal_found = True
        advice.append(
            "Low heart rate detected. Consult your doctor if dizziness occurs."
        )

    # Age
    if age > 35:
        abnormal_found = True
        advice.append(
            "Advanced maternal age. Regular monitoring is recommended."
        )

    elif age < 18:
        abnormal_found = True
        advice.append(
            "Adolescent pregnancy. Ensure proper nutrition and regular checkups."
        )

    # Safe range advice
    if not abnormal_found and risk_code != 2:
        advice.append(
            "Your current vitals appear to be within a safe range. Continue regular prenatal checkups, healthy meals, hydration, and adequate rest."
        )

    # Emergency rule
    if risk_code == 2:
        advice.append(
            "Emergency: High pregnancy risk detected. Seek medical attention immediately."
        )

    
    # RETURN RESULT

    return {
        "risk_level": risk_code,
        "risk_name": risk_name,
        "confidence_percentage": round(confidence, 2),
        "top_contributor": shap_data[0][0],
        "importance": {k: float(v) for k, v in shap_data},
        "advice": advice
    }


# TEST RUN

if __name__ == "__main__":

    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)

    print("\nModel Accuracy:", round(accuracy * 100, 2), "%")

    # Confusion Matrix

    cm = confusion_matrix(y_test, y_pred)

    plt.figure(figsize=(8,6))

    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="RdPu",
        xticklabels=["Low","Mid","High"],
        yticklabels=["Low","Mid","High"]
    )

    plt.title("Model Confusion Matrix")

    plt.xlabel("Predicted")
    plt.ylabel("Actual")

    plt.show()

    # Feature Importance

    plt.figure(figsize=(10,6))

    plot_importance(model)

    plt.title("XGBoost Feature Importance")

    plt.show()

    # Sample prediction

    sample_patient = [
        38,
        200,
        100,
        5,
        37,     # Celsius input
        200
    ]

    result = analyze_maternal_health(
        sample_patient,
        trimester=3,
        temp_unit="C"
    )

    print("\nPrediction Result:\n")

    print(json.dumps(result, indent=4))