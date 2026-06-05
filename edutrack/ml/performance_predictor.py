"""
Performance Grade Predictor
- scikit-learn: LinearRegression + RandomForestRegressor (ensemble)
- Deep Learning: Keras LSTM for sequential grade prediction
"""

import os, json
import numpy as np

MODEL_PATH = "models/grade_model.json"
DL_MODEL_PATH = "models/grade_dl_model.weights.h5"

# ─── Lightweight persisted model (JSON) ───────────────────────────────────────
def _save_model(params):
    os.makedirs("models", exist_ok=True)
    with open(MODEL_PATH, "w") as f:
        json.dump(params, f)

def _load_model():
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH) as f:
            return json.load(f)
    return None

# ─── Simple Linear + Polynomial feature engineering ───────────────────────────
def _features_from_marks(marks_list):
    """Convert list of {pct} dicts into feature vectors."""
    pcts = [m["pct"] for m in marks_list]
    X, y = [], []
    for i in range(1, len(pcts)):
        window = pcts[max(0, i-3):i]
        mean_ = np.mean(window)
        trend = pcts[i-1] - pcts[max(0,i-2)] if i >= 2 else 0
        X.append([mean_, trend, pcts[i-1], i])
        y.append(pcts[i])
    return np.array(X, dtype=float), np.array(y, dtype=float)

# ─── Train: Random Forest + optional DL ───────────────────────────────────────
def train_grade_model(all_marks_data):
    """
    Train Random Forest on ALL students' marks data.
    all_marks_data: list of {student_name, pct, marks, total, week, subject}
    Returns training summary.
    """
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import mean_absolute_error

        # Build global dataset
        all_X, all_y = [], []
        by_student = {}
        for m in all_marks_data:
            sn = m["student_name"]
            by_student.setdefault(sn, []).append(m)

        for sn, marks in by_student.items():
            if len(marks) >= 3:
                X, y = _features_from_marks(marks)
                all_X.extend(X.tolist())
                all_y.extend(y.tolist())

        if len(all_X) < 4:
            return {"status": "skipped", "reason": "Not enough data"}

        X = np.array(all_X)
        y = np.array(all_y)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X_scaled, y)

        preds = rf.predict(X_scaled)
        mae = float(mean_absolute_error(y, preds))

        # Persist model params (feature importances + scaler stats)
        params = {
            "feature_importances": rf.feature_importances_.tolist(),
            "scaler_mean": scaler.mean_.tolist(),
            "scaler_std": scaler.scale_.tolist(),
            "train_mae": mae,
            "n_samples": len(X),
            "n_estimators": 100
        }
        _save_model(params)

        # Try DL model (LSTM)
        dl_result = _train_dl_model(by_student)

        return {"status": "ok", "mae": mae, "n_samples": len(X), "dl": dl_result}

    except ImportError as e:
        return {"status": "error", "reason": f"Missing library: {e}"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

def _train_dl_model(by_student):
    """Train a simple Keras LSTM on sequential grade data."""
    try:
        import tensorflow as tf
        from tensorflow import keras

        SEQ_LEN = 3
        X_seq, y_seq = [], []
        for sn, marks in by_student.items():
            pcts = [m["pct"] for m in marks]
            if len(pcts) >= SEQ_LEN + 1:
                for i in range(len(pcts) - SEQ_LEN):
                    X_seq.append(pcts[i:i+SEQ_LEN])
                    y_seq.append(pcts[i+SEQ_LEN])

        if len(X_seq) < 4:
            return {"status": "skipped", "reason": "Not enough sequential data"}

        X_arr = np.array(X_seq, dtype=float).reshape(-1, SEQ_LEN, 1) / 100.0
        y_arr = np.array(y_seq, dtype=float) / 100.0

        model = keras.Sequential([
            keras.layers.LSTM(32, input_shape=(SEQ_LEN, 1)),
            keras.layers.Dense(16, activation="relu"),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(1)
        ])
        model.compile(optimizer="adam", loss="mse")
        model.fit(X_arr, y_arr, epochs=30, batch_size=4, verbose=0)

        os.makedirs("models", exist_ok=True)
        model.save_weights(DL_MODEL_PATH)
        return {"status": "ok", "architecture": "LSTM(32) → Dense(16) → Dense(1)"}

    except Exception as e:
        return {"status": "error", "reason": str(e)}

# ─── Predict ──────────────────────────────────────────────────────────────────
def predict_grade(marks_list):
    """
    Predict next test percentage for a student.
    marks_list: list of {marks, total, pct} dicts in order.
    Returns: {predicted_pct, confidence, method, trend}
    """
    pcts = [m["pct"] for m in marks_list]

    # Always have a simple fallback
    simple_trend = pcts[-1] - pcts[-2] if len(pcts) >= 2 else 0
    simple_pred  = max(0, min(100, pcts[-1] + simple_trend * 0.5))

    # Try sklearn Random Forest
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import StandardScaler
        import numpy as np

        if len(marks_list) >= 3:
            X, y = _features_from_marks(marks_list)
            if len(X) >= 2:
                scaler = StandardScaler()
                X_sc = scaler.fit_transform(X)
                rf = RandomForestRegressor(n_estimators=100, random_state=42)
                rf.fit(X_sc, y)

                # Predict next
                window = pcts[-3:]
                mean_ = np.mean(window)
                trend = pcts[-1] - pcts[-2] if len(pcts) >= 2 else 0
                feat  = np.array([[mean_, trend, pcts[-1], len(pcts)]])
                feat_sc = scaler.transform(feat)
                pred_rf = float(rf.predict(feat_sc)[0])
                pred_rf = max(0, min(100, pred_rf))

                # Try DL prediction
                pred_dl = _predict_dl(pcts)

                if pred_dl is not None:
                    final_pred = round(0.5 * pred_rf + 0.5 * pred_dl, 1)
                    method = "Ensemble (Random Forest + LSTM)"
                    confidence = "High"
                else:
                    final_pred = round(pred_rf, 1)
                    method = "Random Forest"
                    confidence = "Medium"

                trend_label = "improving" if final_pred > pcts[-1] else "declining" if final_pred < pcts[-1] else "stable"
                return {
                    "predicted_pct": final_pred,
                    "confidence": confidence,
                    "method": method,
                    "trend": trend_label,
                    "recent_avg": round(np.mean(pcts[-3:]), 1),
                    "history": pcts
                }
    except Exception:
        pass

    # Fallback
    trend_label = "improving" if simple_pred > pcts[-1] else "declining" if simple_pred < pcts[-1] else "stable"
    return {
        "predicted_pct": round(simple_pred, 1),
        "confidence": "Low",
        "method": "Moving Average",
        "trend": trend_label,
        "recent_avg": round(sum(pcts[-3:]) / len(pcts[-3:]), 1) if pcts else 0,
        "history": pcts
    }

def _predict_dl(pcts):
    """Use Keras LSTM for sequential prediction if model exists."""
    try:
        import tensorflow as tf
        from tensorflow import keras
        import numpy as np

        SEQ_LEN = 3
        if len(pcts) < SEQ_LEN or not os.path.exists(DL_MODEL_PATH):
            return None

        model = keras.Sequential([
            keras.layers.LSTM(32, input_shape=(SEQ_LEN, 1)),
            keras.layers.Dense(16, activation="relu"),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(1)
        ])
        model.compile(optimizer="adam", loss="mse")
        model.load_weights(DL_MODEL_PATH)

        seq = np.array(pcts[-SEQ_LEN:], dtype=float).reshape(1, SEQ_LEN, 1) / 100.0
        pred = float(model.predict(seq, verbose=0)[0][0]) * 100.0
        return max(0, min(100, pred))
    except Exception:
        return None
