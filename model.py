"""model.py - load the trained XGBoost model and make predictions."""

from pathlib import Path
import joblib
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"


@st.cache_resource
def load_artifacts():
    """Load model + encoder + feature list once and cache them."""
    model = joblib.load(MODELS_DIR / "xgb_model.pkl")
    label_encoder = joblib.load(MODELS_DIR / "label_encoder.pkl")
    feature_columns = joblib.load(MODELS_DIR / "feature_columns.pkl")
    return model, label_encoder, feature_columns


def predict(user_inputs: dict):
    """
    user_inputs: dict of the fields the form collected
                 (age, sex, TSH, T3, TT4, T4U, FTI).
    Any model feature not supplied (the 14 clinical flags) defaults to 0.
    Returns: (predicted_label, confidence_percent, prob_dict)
    """
    model, label_encoder, feature_columns = load_artifacts()

    # Build a single-row frame in the exact training column order.
    row = {col: user_inputs.get(col, 0) for col in feature_columns}
    X = pd.DataFrame([row], columns=feature_columns)

    probs = model.predict_proba(X)[0]
    best_idx = int(probs.argmax())
    label = label_encoder.inverse_transform([best_idx])[0]
    # Never report absolute 100% certainty - an ML prediction always carries
    # some residual uncertainty, so we cap the displayed confidence at 99.9%.
    confidence = min(round(float(probs[best_idx]) * 100, 1), 99.9)
    prob_dict = {cls: round(float(p) * 100, 1)
                 for cls, p in zip(label_encoder.classes_, probs)}
    return label, confidence, prob_dict