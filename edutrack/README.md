# EduTrack Pro 🎓

**Smart Tuition Centre Management with Python ML/DL Backend**

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask |
| Machine Learning | scikit-learn (Random Forest, Logistic Regression) |
| Deep Learning | TensorFlow/Keras (LSTM, Dense Neural Networks) |
| Database | SQLite (via Python `sqlite3`) |
| Frontend | Pure HTML5, CSS3, Vanilla JavaScript |
| AI Chatbot | Anthropic Claude API (server-side) + rule-based fallback |

---

## Features

### Tutor Dashboard
- 👥 Student management (add/delete)
- 📅 Attendance marking with modal
- 📊 Test marks entry and tracking
- 📈 Weekly performance analysis
- 📝 Notes with file attachments
- 📢 Announcements
- 💰 Fees due date tracking with alerts
- 🤖 AI chatbot (Anthropic API or rule-based)
- 🧠 ML Analysis page (grade prediction + attendance risk)

### Student Portal
- View own attendance, marks, notes, announcements
- Personal dashboard with stats

### ML / Deep Learning
- **Grade Predictor**: Random Forest + Keras LSTM ensemble
- **Attendance Risk**: Logistic Regression + Dense Neural Net ensemble
- **Class Insights**: ML-powered summary for all students

---

## Setup & Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> If you don't need TensorFlow (deep learning), you can remove it from requirements.txt — the app gracefully falls back to scikit-learn only.

### 2. Run the app

```bash
python app.py
```

### 3. Open in browser

```
http://localhost:5000
```

### 4. Login

| Role | Username | Password |
|------|----------|----------|
| Tutor | `admin` | `1234` |
| Student | (student name) | (set by tutor) |

---

## Chatbot Setup (Optional)

1. Go to **⚙️ Settings** in the app
2. Paste your Anthropic API key (`sk-ant-...`)
3. Click **Save API Key**

Without an API key, the chatbot uses intelligent rule-based responses.

---

## Project Structure

```
edutrack/
├── app.py                  # Flask backend + all API routes
├── requirements.txt        # Python dependencies
├── edutrack.db             # SQLite database (auto-created on first run)
├── models/                 # Saved ML model files (auto-created)
│   ├── grade_model.json
│   ├── grade_dl_model.weights.h5
│   ├── attendance_model.json
│   └── attendance_dl_model.weights.h5
├── ml/
│   ├── __init__.py
│   ├── performance_predictor.py   # Random Forest + LSTM grade predictor
│   ├── attendance_risk.py         # Logistic Regression + Neural Net risk
│   └── chatbot.py                 # Anthropic API + rule-based fallback
├── templates/
│   └── index.html          # Single-page HTML/CSS frontend
└── static/
    └── js/
        └── app.js          # Frontend JavaScript (API calls, UI logic)
```

---

## ML Models Detail

### Grade Predictor (`ml/performance_predictor.py`)
- **Features**: rolling mean, trend, last score, test index
- **scikit-learn**: `RandomForestRegressor(n_estimators=100)`
- **Deep Learning**: Keras `LSTM(32) → Dense(16) → Dense(1)` on sequential score windows
- **Ensemble**: 50% RF + 50% LSTM when DL model available

### Attendance Risk (`ml/attendance_risk.py`)
- **Features**: overall attendance rate, recent rate, trend, avg marks, mark trend, consecutive absences
- **scikit-learn**: `LogisticRegression` (trained on real + synthetic data)
- **Deep Learning**: Keras `Dense(32) → Dropout(0.3) → Dense(16) → Sigmoid`
- **Ensemble**: 40% LR + 60% Neural Net

### Training
Click **🏋️ Retrain Models** on the ML Analysis page, or call `POST /api/ml/train`.
