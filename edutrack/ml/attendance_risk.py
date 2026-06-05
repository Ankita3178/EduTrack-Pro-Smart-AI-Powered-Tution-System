"""
Attendance Risk Predictor
- scikit-learn: Logistic Regression + feature engineering
- Deep Learning: Keras Dense network for risk scoring
"""

import os, json
import numpy as np

MODEL_PATH = "models/attendance_model.json"
DL_MODEL_PATH = "models/attendance_dl_model.weights.h5"

def _compute_features(statuses, mark_pcts):
    """
    statuses: list of 'P' | 'A'
    mark_pcts: list of float percentages
    Returns feature vector [att_rate, recent_att_rate, trend, avg_marks, mark_trend, streak_abs]
    """
    total = len(statuses)
    if total == 0:
        return None

    present = statuses.count("P")
    att_rate = present / total

    recent = statuses[-10:] if len(statuses) >= 10 else statuses
    recent_att = recent.count("P") / len(recent)

    trend = recent_att - att_rate  # positive = improving

    # Consecutive absences (streak)
    streak_abs = 0
    for s in reversed(statuses):
        if s == "A": streak_abs += 1
        else: break

    avg_marks = sum(mark_pcts) / len(mark_pcts) if mark_pcts else 50.0
    mark_trend = (mark_pcts[-1] - mark_pcts[-2]) if len(mark_pcts) >= 2 else 0.0

    return [att_rate, recent_att, trend, avg_marks / 100.0, mark_trend / 100.0, streak_abs / 10.0]

def train_attendance_model(all_att_data):
    """
    Synthetic training: create labelled examples from real patterns.
    all_att_data: list of {student_name, date, status}
    """
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score

        # Group by student
        by_student = {}
        for r in all_att_data:
            by_student.setdefault(r["student_name"], []).append(r["status"])

        X, y = [], []
        for sn, statuses in by_student.items():
            if len(statuses) < 5:
                continue
            total = len(statuses)
            present = statuses.count("P")
            att_rate = present / total
            recent = statuses[-5:]
            recent_rate = recent.count("P") / 5
            streak = sum(1 for s in reversed(statuses) if s == "A")
            # Label: 1 = at risk (att < 75% or recent 3 consecutive absences)
            label = 1 if att_rate < 0.75 or streak >= 3 else 0
            feats = [att_rate, recent_rate, att_rate - recent_rate, 0.5, 0, streak / 10.0]
            X.append(feats)
            y.append(label)

        if len(X) < 4:
            # Augment with synthetic data
            X, y = _synthetic_training_data()

        X = np.array(X, dtype=float)
        y = np.array(y)

        scaler = StandardScaler()
        X_sc = scaler.fit_transform(X)

        clf = LogisticRegression(random_state=42, max_iter=200)
        clf.fit(X_sc, y)
        acc = float(accuracy_score(y, clf.predict(X_sc)))

        params = {
            "coef": clf.coef_.tolist(),
            "intercept": clf.intercept_.tolist(),
            "scaler_mean": scaler.mean_.tolist(),
            "scaler_std": scaler.scale_.tolist(),
            "accuracy": acc
        }
        os.makedirs("models", exist_ok=True)
        with open(MODEL_PATH, "w") as f:
            json.dump(params, f)

        dl_res = _train_dl_attendance(X, y)
        return {"status": "ok", "accuracy": acc, "n_samples": len(X), "dl": dl_res}

    except Exception as e:
        return {"status": "error", "reason": str(e)}

def _synthetic_training_data():
    """Generate synthetic training examples for attendance risk."""
    rng = np.random.default_rng(42)
    X, y = [], []
    for _ in range(200):
        att = rng.uniform(0.4, 1.0)
        recent = max(0, min(1, att + rng.normal(0, 0.1)))
        trend = recent - att
        avg_m = rng.uniform(0.3, 1.0)
        m_trend = rng.normal(0, 0.05)
        streak = rng.integers(0, 8) if att < 0.75 else rng.integers(0, 3)
        label = 1 if att < 0.75 or streak >= 3 else 0
        X.append([att, recent, trend, avg_m, m_trend, streak / 10.0])
        y.append(label)
    return X, y

def _train_dl_attendance(X, y):
    """Train a simple Keras Dense neural net for risk classification."""
    try:
        import tensorflow as tf
        from tensorflow import keras

        model = keras.Sequential([
            keras.layers.Dense(32, activation="relu", input_shape=(6,)),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(16, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid")
        ])
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        model.fit(X, y, epochs=50, batch_size=8, verbose=0)
        model.save_weights(DL_MODEL_PATH)
        return {"status": "ok", "architecture": "Dense(32)→Dense(16)→Sigmoid"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

def predict_attendance_risk(statuses, mark_pcts):
    """
    Predict attendance risk for a single student.
    Returns: {risk_level, risk_score, recommendation, method}
    """
    feats = _compute_features(statuses, mark_pcts)
    if feats is None:
        return {"risk_level": "Unknown", "risk_score": None, "recommendation": "Insufficient data", "method": "none"}

    att_rate = feats[0]
    streak_abs = feats[5] * 10

    # Rule-based baseline
    if att_rate < 0.60 or streak_abs >= 5:
        base_risk = 0.90
    elif att_rate < 0.75 or streak_abs >= 3:
        base_risk = 0.65
    else:
        base_risk = 0.20

    # Try sklearn logistic regression
    risk_score = base_risk
    method = "Rule-based"

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        import numpy as np

        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH) as f:
                params = json.load(f)
            # Manual logistic regression prediction
            x = np.array(feats, dtype=float)
            mean_ = np.array(params["scaler_mean"])
            std_  = np.array(params["scaler_std"])
            x_sc  = (x - mean_) / std_
            coef  = np.array(params["coef"][0])
            intercept = params["intercept"][0]
            logit = np.dot(coef, x_sc) + intercept
            risk_lr = float(1 / (1 + np.exp(-logit)))

            # Try DL
            risk_dl = _predict_dl_risk(feats)
            if risk_dl is not None:
                risk_score = 0.4 * risk_lr + 0.6 * risk_dl
                method = "Ensemble (Logistic Regression + Neural Net)"
            else:
                risk_score = risk_lr
                method = "Logistic Regression"
        else:
            # Synthetic model
            X_syn, y_syn = _synthetic_training_data()
            scaler = StandardScaler()
            X_sc = scaler.fit_transform(X_syn)
            clf = LogisticRegression(random_state=42, max_iter=200)
            clf.fit(X_sc, y_syn)
            x_sc2 = scaler.transform([feats])
            risk_score = float(clf.predict_proba(x_sc2)[0][1])
            method = "Logistic Regression (synthetic)"
    except Exception:
        pass

    risk_score = round(max(0, min(1, risk_score)), 3)

    if risk_score >= 0.7:
        level = "High"
        rec   = "Urgent: Contact parents. Student may need intervention."
    elif risk_score >= 0.4:
        level = "Medium"
        rec   = "Monitor closely. Consider a counselling session."
    else:
        level = "Low"
        rec   = "Attendance looks healthy. Keep encouraging!"

    return {
        "risk_level": level,
        "risk_score": risk_score,
        "risk_pct": f"{round(risk_score * 100)}%",
        "recommendation": rec,
        "method": method,
        "attendance_rate": f"{round(att_rate * 100, 1)}%",
        "consecutive_absences": int(streak_abs)
    }

def _predict_dl_risk(feats):
    """Use Keras Dense neural net for risk score."""
    try:
        import tensorflow as tf
        from tensorflow import keras
        import numpy as np

        if not os.path.exists(DL_MODEL_PATH):
            return None

        model = keras.Sequential([
            keras.layers.Dense(32, activation="relu", input_shape=(6,)),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(16, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid")
        ])
        model.compile(optimizer="adam", loss="binary_crossentropy")
        model.load_weights(DL_MODEL_PATH)
        x = np.array(feats, dtype=float).reshape(1, -1)
        return float(model.predict(x, verbose=0)[0][0])
    except Exception:
        return None
