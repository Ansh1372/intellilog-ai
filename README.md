<div align="center">
  <h1>🧠 IntelliLog AI</h1>
  <p><strong>Intelligent, Self-Hosted Log Classification & Anomaly Alerting System</strong></p>
  
  [![Vercel](https://img.shields.io/badge/Deployed_on-Vercel-black?logo=vercel)](#)
  [![Hugging Face](https://img.shields.io/badge/Backend-Hugging_Face-yellow?logo=huggingface)](#)
  [![Database](https://img.shields.io/badge/Database-Neon_Postgres-00E599?logo=postgresql)](#)
  [![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi)](#)
  [![React](https://img.shields.io/badge/Frontend-React+Vite-61DAFB?logo=react)](#)
</div>

---

## 📸 Dashboard & Alerts

> **[Insert your beautiful Vercel Dashboard screenshot here]**
> *(Tip: Take a screenshot showing the colorful charts, System Health badges, and the populated log table)*

<br/>

> **[Insert a screenshot of the automated Email Alert you received here]**
> *(Tip: Show the email inbox with the [TEST ALERT] or CRITICAL alert from IntelliLog AI)*

---

## 🚀 Live Demo
**Frontend:** `https://intellilog-ai.vercel.app/`  
**Backend API:** `https://ansh1372-intellilog-backend.hf.space`

---

## 🏗️ Cloud Architecture

IntelliLog AI is built as a fully decoupled microservices architecture, completely deployed on modern serverless cloud infrastructure:

1. **Frontend (Vercel):** A blazing-fast React + Vite dashboard displaying real-time metrics, system health, and a searchable log explorer.
2. **Backend (Hugging Face Spaces):** A FastAPI server running the intelligent classification engine, anomaly detection, and SMTP email alerts.
3. **Database (Neon Serverless Postgres):** A cloud database storing all logs, model predictions, feedback loops, and metrics.
4. **LLM Engine (Groq API):** Lightning-fast LLaMA-3 inference for ambiguous log classification.

---

## 🧠 The 3-Stage Classification Pipeline

To minimize latency and LLM API costs, IntelliLog uses a cascading fallback pipeline:

```text
Log Input → ⚡ Regex Engine ($0) → 🤖 ML Model ($0) → 🧠 Groq LLM (Cost pennies)
                 ↓ 60%                  ↓ 30%                  ↓ 10%
            Instant Match          TF-IDF Inference       Complex Analysis
```

1. **Stage 1 (Regex Engine):** Instantly catches known patterns (e.g., Auth Failures, OOM crashes, Timeouts) using pre-defined rules.
2. **Stage 2 (Machine Learning):** Uses a custom-trained `TF-IDF + Logistic Regression` model to classify logs with high confidence.
3. **Stage 3 (Groq LLM):** If the ML model's confidence is below `0.70`, the log is sent to an ultra-fast LLaMA-3 model for contextual understanding and semantic classification.

---

## 🛡️ Key Features

- **Automated Anomaly Detection:** Real-time monitoring of log velocity and error rates.
- **Instant SMTP Email Alerts:** Automatically sends email warnings to the engineering team the second a `HIGH` or `CRITICAL` severity log (like a DB crash) hits the pipeline.
- **Feedback Loop:** Built-in dashboard capability to correct AI misclassifications, saving data to Postgres for future ML retrain loops.
- **Full-Text Search:** Instantly query logs by severity, source, or text.
- **Real-Time System Health:** Dashboard actively monitors the connection status of the DB, ML engine, and Email SMTP servers.

---

## 💻 Local Development Setup

If you want to run the entire stack locally on your own machine:

```bash
# 1. Clone the repository
git clone https://github.com/your-username/intellilog-ai.git
cd intellilog-ai

# 2. Set up environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY, Database URL, and SMTP credentials

# 3. Spin up the infrastructure via Docker
docker-compose up --build
```

- **Frontend Dashboard:** `http://localhost:3001`
- **Backend API:** `http://localhost:8000`
- **API Swagger Docs:** `http://localhost:8000/docs`

### Testing the Pipeline
You can simulate a live production environment by sending a test log directly via terminal:
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"log": "CRITICAL: Main Postgres database went offline. Connection timed out.", "source": "DatabaseService"}'
```
*(If your SMTP is configured, this will instantly trigger an email alert!)*

---
*Built by **[Your Name]** as an exploration of scalable AI infrastructure and modern web deployment.*
