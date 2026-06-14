<div align="center">
  <h1>IntelliLog AI</h1>
  <p><strong>Self-Hosted Log Classification & Anomaly Alerting System</strong></p>
  
  [![Vercel](https://img.shields.io/badge/Deployed_on-Vercel-black?logo=vercel)](#)
  [![Hugging Face](https://img.shields.io/badge/Backend-Hugging_Face-yellow?logo=huggingface)](#)
  [![Database](https://img.shields.io/badge/Database-Neon_Postgres-00E599?logo=postgresql)](#)
  [![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi)](#)
  [![React](https://img.shields.io/badge/Frontend-React+Vite-61DAFB?logo=react)](#)
</div>

---

## 🚀 Live Demo
**Frontend:** `https://intellilog-ai.vercel.app/`  
**Backend API:** `https://ansh1372-intellilog-backend.hf.space`

---

## 📸 Dashboard & Alerts

*(Add your dashboard screenshot here by replacing this line with `![Dashboard](link-to-image)`)*

*(Add your email alert screenshot here by replacing this line with `![Alert](link-to-image)`)*

---

## 🏗️ Architecture

IntelliLog AI is designed as a decoupled microservices architecture, currently deployed on serverless cloud infrastructure:

1. **Frontend (Vercel):** React + Vite dashboard displaying real-time metrics, system health, and a searchable log explorer.
2. **Backend (Hugging Face Spaces):** FastAPI server handling classification routing, anomaly detection, and SMTP email alerts.
3. **Database (Neon Serverless Postgres):** Cloud database storing logs, model predictions, feedback loops, and system metrics.
4. **LLM Engine (Groq API):** LLaMA-3 inference for ambiguous log classification.

---

## 🧠 Classification Pipeline

To optimize for latency and reduce LLM API costs, the system uses a cascading fallback pipeline:

```text
Log Input → Regex Engine ($0) → ML Model ($0) → Groq LLM (High Latency/Cost)
                 ↓ 60%               ↓ 30%               ↓ 10%
            Instant Match       TF-IDF Inference    Semantic Analysis
```

1. **Stage 1 (Regex Engine):** Catches known patterns (e.g., Auth Failures, OOM crashes, Timeouts) using pre-defined rules.
2. **Stage 2 (Machine Learning):** Uses a custom-trained `TF-IDF + Logistic Regression` model to classify logs with high confidence.
3. **Stage 3 (Groq LLM):** If the ML model's confidence falls below `0.70`, the log is routed to a LLaMA-3 model for contextual understanding.

---

## 🛡️ Key Features

- **Anomaly Detection:** Real-time monitoring of log velocity and error rates.
- **Automated Alerts:** Triggers SMTP email warnings when a `HIGH` or `CRITICAL` severity log enters the pipeline.
- **Feedback Loop:** Dashboard capability to manually correct misclassifications, saving updated labels to Postgres for future ML retrain loops.
- **Log Explorer:** Query logs by severity, source, or full-text search.
- **System Health:** Active monitoring of database connections, ML engine status, and SMTP server availability.

---

## 💻 Local Development Setup

To run the stack locally using Docker:

```bash
# 1. Clone the repository
git clone https://github.com/Ansh1372/intellilog-ai.git
cd intellilog-ai

# 2. Set up environment variables
cp .env.example .env
# Edit .env and configure your GROQ_API_KEY, Database URL, and SMTP credentials

# 3. Spin up the infrastructure
docker-compose up --build
```

- **Frontend Dashboard:** `http://localhost:3001`
- **Backend API:** `http://localhost:8000`
- **API Swagger Docs:** `http://localhost:8000/docs`

### Testing the Pipeline
You can simulate a production event by sending a test log directly via curl:
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"log": "CRITICAL: Main Postgres database went offline. Connection timed out.", "source": "DatabaseService"}'
```
*(If SMTP is configured, this will trigger an email alert)*

---
*Built by **Ansh Srivastava**.*
