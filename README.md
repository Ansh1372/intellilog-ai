# IntelliLog AI

A self-hosted log classification and alerting system. Deploy on any server, point your logs at it, and it automatically classifies, stores, alerts, and shows everything in a dashboard.

## Quick Start

```bash
git clone https://github.com/your-repo/intellilog-ai.git
cd intellilog-ai
cp .env.example .env
# Add your GROQ_API_KEY to .env
docker-compose up --build
```

- Dashboard: http://localhost:3001
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## How It Works

3-stage classification pipeline that minimizes cost:

```
Log Input → Regex Engine ($0) → ML Model ($0) → LLM (only if needed)
               ↓ 60%              ↓ 30%              ↓ 10%
```

1. **Regex** catches known patterns (auth failures, OOM, timeouts) — free, instant
2. **ML Model** (TF-IDF + Logistic Regression) classifies with confidence — free, fast
3. **LLM** (Groq API) handles only ambiguous logs below 0.70 confidence — costs pennies

## Features

| Feature | Endpoint | Status |
|---------|----------|--------|
| Log Classification | `POST /classify` | ✅ |
| CSV Bulk Upload | `POST /upload-csv` | ✅ |
| Full-text Search | `GET /logs?q=...&source=...&last=7d` | ✅ |
| Feedback (Mark Wrong) | `POST /feedback` | ✅ |
| Model Retrain | `POST /retrain` | ✅ |
| Per-source Stats | `GET /stats?source=postgres` | ✅ |
| Health Check | `GET /health` | ✅ |
| Anomaly Detection | `POST /anomaly-score` | ✅ |
| Drift Report | `GET /drift-report` | ✅ |
| Incident Correlation | `GET /incidents` | ✅ |
| Email Alerts | Auto on High/Critical | ✅ |
| Webhook Alerts | `POST /alerts/webhook` | ✅ |
| Rate Limiting | Middleware (1000/sec) | ✅ |
| Log Retention | `POST /retention/cleanup` | ✅ |
| Syslog Input | UDP :5514 | ✅ |
| React Dashboard | http://localhost:3001 | ✅ |

## Classify a Log

```bash
# Basic
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"log": "authentication failed for admin user", "source": "nginx"}'

# JSON log (auto-parsed)
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"log": "{\"level\": \"error\", \"msg\": \"connection timeout\", \"service\": \"auth\"}"}'
```

## Search Logs

```bash
# Text search with filters
curl "http://localhost:8000/logs?q=timeout&source=postgres&severity=High&last=24h"

# Export all critical logs from last 7 days
curl "http://localhost:8000/logs?severity=Critical&last=7d&limit=200"
```

## Feedback Loop

```bash
# Submit correction
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"log_id": 42, "correct_label": "Database Error"}'

# Retrain model with corrections
curl -X POST http://localhost:8000/retrain
```

## Syslog Integration

Point rsyslog or Docker log driver at IntelliLog:

```bash
# rsyslog.conf
*.* @intellilog-server:5514

# Docker log driver
docker run --log-driver=syslog --log-opt syslog-address=udp://localhost:5514 myapp
```

## Environment Variables

```env
GROQ_API_KEY=your_key          # Required for LLM fallback
DATABASE_URL=postgresql://...   # Auto-configured in Docker
SMTP_HOST=smtp.gmail.com       # Optional: email alerts
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=app_password
ALERT_EMAIL=team@company.com
RATE_LIMIT_PER_SECOND=1000     # Max logs/sec per source
LOG_RETENTION_DAYS=30          # Auto-cleanup after N days
```

## Train on Real Data

```bash
# 1. Download Loghub datasets
git clone https://github.com/logpai/loghub.git data/loghub

# 2. Preprocess and label
python data/prepare_loghub.py

# 3. Train model
python -m backend.ml.train_model
```

## Architecture

```
Docker Compose
├── postgres:16     — classified logs, predictions, feedback
├── backend:8000    — FastAPI + ML pipeline + alerts
└── frontend:3001   — React dashboard (Tailwind + Recharts)
```

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, scikit-learn, Groq API
- **Frontend**: React, Vite, Tailwind CSS, Recharts
- **Database**: PostgreSQL
- **ML**: TF-IDF + Logistic Regression, Isolation Forest (anomaly)
- **Infra**: Docker Compose, Nginx
