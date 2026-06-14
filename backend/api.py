import logging
import json
import os
import shutil
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database.crud import save_log_prediction
from backend.database.db import get_db
from backend.database.feedback import save_feedback, get_feedback_stats
from backend.database.search import search_logs
from backend.database.stats import get_source_stats, get_all_sources
from backend.router import LogRouter
from backend.database.metrics import get_metrics
from backend.dashboard import DashboardService
from backend.ml.retrain import retrain_model
from backend.ml.retrain_from_file import retrain_from_uploaded_file
from backend.alerts.email_alerts import EmailAlertService
from backend.alerts.webhook import WebhookService
from backend.middleware.rate_limit import RateLimitMiddleware, rate_limiter
from backend.utils.json_parser import try_parse_json_log
from backend.tasks.correlation import detect_incidents, get_recent_incidents
from backend.tasks.retention import cleanup_old_logs
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

# =========================================
# APP INITIALIZATION
# =========================================

logger.info("[API] Starting IntelliLog AI application")

app = FastAPI(title="IntelliLog AI", version="1.0.0")

# CORS for frontend
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

try:
    router = LogRouter()
    logger.info("[API] LogRouter initialized successfully")
except Exception as e:
    logger.error(f"[API] Failed to initialize LogRouter: {e}")
    router = None

# Alert services
email_service = EmailAlertService()
webhook_service = WebhookService()

# Semantic Search Engine (lazy init)
embedding_search = None

# Track app start time for health check
APP_START_TIME = datetime.now()


def get_embedding_search():
    """Lazy initialization of embedding search engine."""
    global embedding_search
    if embedding_search is None:
        try:
            from backend.ml.embeddings import LogEmbeddingSearch
            embedding_search = LogEmbeddingSearch()
        except Exception as e:
            logger.warning(f"[API] Failed to initialize embedding search: {e}")
    return embedding_search


# =========================================
# REQUEST MODELS
# =========================================

class LogRequest(BaseModel):
    log: str
    source: str = None


class SimilarLogsRequest(BaseModel):
    log: str
    top_k: int = 5


class FeedbackRequest(BaseModel):
    log_id: int
    correct_label: str


class AlertConfigRequest(BaseModel):
    source: str = None
    min_severity: str = "critical"
    email: str = None
    webhook_url: str = None


# =========================================
# HEALTH & STATUS ENDPOINTS
# =========================================

@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Enhanced health check — DB status, model loaded, disk usage, uptime."""
    logger.info("[API] Health check requested")

    # DB connectivity
    db_connected = False
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        pass

    # Disk usage
    try:
        import shutil
        disk = shutil.disk_usage("/")
        disk_info = {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "usage_percent": round(disk.used / disk.total * 100, 1)
        }
    except Exception:
        disk_info = None

    # Uptime
    uptime_seconds = (datetime.now() - APP_START_TIME).total_seconds()

    return {
        "status": "healthy" if (router is not None and db_connected) else "degraded",
        "service": "IntelliLog AI",
        "version": "1.0.0",
        "uptime_seconds": int(uptime_seconds),
        "db_connected": db_connected,
        "router_ready": router is not None,
        "model_loaded": router.ml_engine is not None if router else False,
        "regex_engine": router.regex_engine is not None if router else False,
        "anomaly_detection": (
            router.anomaly_detector.is_available()
            if router and router.anomaly_detector else False
        ),
        "drift_detection": router.drift_detector is not None if router else False,
        "email_alerts": email_service.is_available(),
        "semantic_search": get_embedding_search() is not None and get_embedding_search().is_available(),
        "disk": disk_info,
        "rate_limit": rate_limiter.get_stats()
    }


# =========================================
# CLASSIFICATION ENDPOINTS
# =========================================

@app.post("/classify")
def classify_log(request: LogRequest, db: Session = Depends(get_db)):
    logger.info(f"[API] /classify — received log: {request.log[:80]}...")

    if router is None:
        logger.error("[API] /classify — router not available")
        raise HTTPException(
            status_code=503,
            detail="Classification service unavailable. ML model may not be loaded."
        )

    # JSON auto-parsing: extract message and source from structured JSON logs
    log_text = request.log
    source = request.source
    parsed_message, parsed_source = try_parse_json_log(log_text)
    if parsed_source and not source:
        source = parsed_source
    if parsed_message != log_text:
        log_text = parsed_message

    try:
        result = router.process_log(log_text)
        logger.info(f"[API] /classify — result source: {result.get('source')}")

    except Exception as e:
        logger.error(f"[API] /classify — classification error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to classify log"
        )

    try:
        save_log_prediction(log_text, result, source=source, db=db)
        logger.info("[API] /classify — prediction saved to database")

    except Exception as e:
        logger.warning(f"[API] /classify — failed to save prediction to DB: {e}")

    # Trigger alerts if severity is high
    severity = result.get("severity", "")
    classification = result.get("classification", "")
    if email_service.should_alert(source, classification, severity):
        # Check alert configs (future: load from DB)
        alert_email = os.getenv("ALERT_EMAIL")
        if alert_email:
            email_service.send_alert(
                to_email=alert_email,
                log_text=log_text,
                classification=classification,
                severity=severity,
                source=source,
                confidence=result.get("confidence")
            )

    # Add source info to response
    if source:
        result["log_source"] = source

    return result


@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    logger.info(f"[API] /upload-csv — file received: {file.filename}")

    if router is None:
        logger.error("[API] /upload-csv — router not available")
        raise HTTPException(
            status_code=503,
            detail="Classification service unavailable."
        )

    try:
        df = pd.read_csv(file.file)
        logger.info(f"[API] /upload-csv — CSV loaded with {len(df)} rows")

    except Exception as e:
        logger.error(f"[API] /upload-csv — failed to parse CSV: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid CSV file"
        )

    if "log_text" not in df.columns:
        logger.error("[API] /upload-csv — CSV missing 'log_text' column")
        raise HTTPException(
            status_code=400,
            detail="CSV must contain a 'log_text' column"
        )

    results = []

    for idx, row in df.iterrows():
        log_text = row["log_text"]
        source = row.get("source") if "source" in df.columns else None

        try:
            result = router.process_log(log_text)
            save_log_prediction(log_text, result, source=source, db=db)

        except Exception as e:
            logger.warning(f"[API] /upload-csv — error processing row {idx}: {e}")
            result = {"error": "Failed to classify", "log": log_text}

        results.append({"log": log_text, "result": result})

    logger.info(f"[API] /upload-csv — processed {len(results)} logs")

    return {
        "total_logs": len(results),
        "results": results
    }


# =========================================
# SEARCH & EXPORT ENDPOINTS
# =========================================

@app.get("/logs")
def search_logs_endpoint(
    q: str = Query(None, description="Text search query"),
    source: str = Query(None, description="Filter by source"),
    severity: str = Query(None, description="Filter by severity"),
    classification: str = Query(None, description="Filter by classification"),
    last: str = Query(None, description="Time range: 1h, 24h, 7d, 30d"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Full-text log search with filters. Also serves as export API."""
    logger.info(f"[API] /logs — q={q}, source={source}, severity={severity}, last={last}")
    return search_logs(
        q=q, source=source, severity=severity,
        classification=classification, last=last,
        page=page, limit=limit, db=db
    )


# =========================================
# FEEDBACK ENDPOINTS
# =========================================

@app.post("/feedback")
def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """Submit a correction for a classified log (Mark Wrong)."""
    logger.info(f"[API] /feedback — log_id={request.log_id}, correct_label={request.correct_label}")
    result = save_feedback(request.log_id, request.correct_label, db=db)
    if result["status"] == "failed":
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to save feedback"))
    return result


@app.get("/feedback/stats")
def feedback_stats(db: Session = Depends(get_db)):
    """Get feedback statistics."""
    return get_feedback_stats(db=db)


# =========================================
# STATS & DASHBOARD ENDPOINTS
# =========================================

@app.get("/stats")
def source_stats(
    source: str = Query(None, description="Source to get stats for"),
    db: Session = Depends(get_db)
):
    """Get per-source statistics."""
    return get_source_stats(source=source, db=db)


@app.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    """Get all unique log sources."""
    return {"sources": get_all_sources(db=db)}


@app.get("/metrics")
def metrics():
    logger.info("[API] /metrics — fetching metrics")
    try:
        data = get_metrics()
        return data
    except Exception as e:
        logger.error(f"[API] /metrics — error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@app.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    logger.info("[API] /dashboard — fetching dashboard data")
    try:
        service = DashboardService()
        data = service.get_metrics(db=db)
        return data
    except Exception as e:
        logger.error(f"[API] /dashboard — error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard data")


@app.get("/recent-logs")
def recent_logs(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Logs per page"),
    db: Session = Depends(get_db)
):
    logger.info(f"[API] /recent-logs — page={page}, limit={limit}")
    try:
        service = DashboardService()
        data = service.get_recent_logs(db=db, page=page, limit=limit)
        return data
    except Exception as e:
        logger.error(f"[API] /recent-logs — error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent logs")


# =========================================
# INCIDENT / CORRELATION ENDPOINTS
# =========================================

@app.get("/incidents")
def incidents(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get recent correlated incidents."""
    return {"incidents": get_recent_incidents(limit=limit, db=db)}


@app.post("/incidents/detect")
def detect_incidents_endpoint(db: Session = Depends(get_db)):
    """Run incident detection (correlate critical errors across sources)."""
    return detect_incidents(db=db)


# =========================================
# ALERT CONFIGURATION ENDPOINTS
# =========================================

@app.post("/alerts/webhook")
def send_test_webhook(config: AlertConfigRequest):
    """Test a webhook URL with a sample payload."""
    if not config.webhook_url:
        raise HTTPException(status_code=400, detail="webhook_url is required")

    success = webhook_service.send_webhook(
        url=config.webhook_url,
        log_text="[TEST] IntelliLog webhook test message",
        classification="Test Alert",
        severity="Medium",
        source=config.source or "test"
    )

    if success:
        return {"status": "success", "message": "Webhook sent successfully"}
    else:
        raise HTTPException(status_code=502, detail="Failed to send webhook")


# =========================================
# RETENTION ENDPOINTS
# =========================================

@app.post("/retention/cleanup")
def run_cleanup(
    days: int = Query(None, description="Override retention days")
):
    """Manually trigger log retention cleanup."""
    logger.info(f"[API] /retention/cleanup — days={days}")
    result = cleanup_old_logs(retention_days=days)
    return result


# =========================================
# RETRAIN ENDPOINTS
# =========================================

@app.post("/retrain")
def retrain():
    """Retrain ML model using classified logs from the database (feedback loop)."""
    logger.info("[API] /retrain — starting model retraining")

    try:
        result = retrain_model()
        logger.info(f"[API] /retrain — result: {result['status']}")

        if result["status"] == "success":
            if router and router.ml_engine:
                try:
                    from backend.ml.inference import MLInference
                    router.ml_engine = MLInference()
                    logger.info("[API] /retrain — ML engine reloaded with new model")
                    result["model_reloaded"] = True
                except Exception as e:
                    logger.warning(f"[API] /retrain — failed to reload ML engine: {e}")
                    result["model_reloaded"] = False
                    result["reload_note"] = "Restart server to use new model"

        return result

    except Exception as e:
        logger.error(f"[API] /retrain — error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrain model")


# =========================================
# ANOMALY DETECTION ENDPOINTS
# =========================================

@app.post("/anomaly-score")
def anomaly_score(request: LogRequest):
    """Get anomaly score for a log without full classification."""
    logger.info(f"[API] /anomaly-score — received log: {request.log[:80]}...")

    if not router or not router.anomaly_detector:
        raise HTTPException(status_code=503, detail="Anomaly detection not available")

    if not router.anomaly_detector.is_available():
        raise HTTPException(
            status_code=503,
            detail="Anomaly model not trained. Run: python -m backend.ml.train_anomaly"
        )

    try:
        result = router.anomaly_detector.score(request.log)
        return result
    except Exception as e:
        logger.error(f"[API] /anomaly-score — error: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute anomaly score")


# =========================================
# SEMANTIC SEARCH ENDPOINTS
# =========================================

@app.post("/similar-logs")
def similar_logs(request: SimilarLogsRequest):
    """Find semantically similar historical logs."""
    logger.info(f"[API] /similar-logs — query: {request.log[:80]}...")

    search = get_embedding_search()

    if not search or not search.is_available():
        raise HTTPException(
            status_code=503,
            detail="Semantic search not available. Install sentence-transformers."
        )

    try:
        result = search.search(request.log, top_k=request.top_k)
        if "error" in result and not result["results"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] /similar-logs — error: {e}")
        raise HTTPException(status_code=500, detail="Failed to search similar logs")


@app.post("/build-index")
def build_index():
    """Build semantic search index from training data."""
    logger.info("[API] /build-index — building embeddings index")

    search = get_embedding_search()

    if not search or not search.is_available():
        raise HTTPException(
            status_code=503,
            detail="Semantic search not available. Install sentence-transformers."
        )

    try:
        df = pd.read_csv("data/advanced_train_logs.csv")
        df = df.dropna(subset=["log_text", "label"])

        log_texts = df["log_text"].tolist()
        metadata = [{"classification": row["label"]} for _, row in df.iterrows()]

        result = search.build_index(log_texts, metadata)

        if result["status"] == "failed":
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

        logger.info(f"[API] /build-index — indexed {result['total_indexed']} logs")
        return result

    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Training data not found")
    except Exception as e:
        logger.error(f"[API] /build-index — error: {e}")
        raise HTTPException(status_code=500, detail="Failed to build index")


# =========================================
# DRIFT DETECTION ENDPOINTS
# =========================================

@app.get("/drift-report")
def drift_report():
    """Get model drift detection report."""
    logger.info("[API] /drift-report — generating report")

    if not router or not router.drift_detector:
        raise HTTPException(status_code=503, detail="Drift detection not available")

    try:
        report = router.drift_detector.get_report()
        return report
    except Exception as e:
        logger.error(f"[API] /drift-report — error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate drift report")


# =========================================
# RATE LIMIT INFO
# =========================================

@app.get("/rate-limit")
def rate_limit_info():
    """Get current rate limit stats."""
    return {
        "max_per_second": rate_limiter.max_per_second,
        "current_stats": rate_limiter.get_stats()
    }


# =========================================
# UPLOAD & CUSTOM TRAINING ENDPOINTS
# =========================================

MAX_FILE_SIZE_MB = 10
REGEX_RULES_PATH = "data/regex_rules.json"
UPLOAD_DIR = "data/uploads"


@app.get("/regex-rules")
def get_regex_rules():
    """Get current regex rules."""
    try:
        with open(REGEX_RULES_PATH, "r") as f:
            rules = json.load(f)
        return {"total_rules": len(rules), "rules": rules}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Regex rules file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to load regex rules")


@app.post("/upload-regex-rules")
async def upload_regex_rules(file: UploadFile = File(...)):
    """Upload custom regex rules JSON file. Replaces current rules."""
    logger.info(f"[API] /upload-regex-rules — file: {file.filename}")

    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a .json file")

    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_FILE_SIZE_MB}MB")
        rules = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    if not isinstance(rules, list):
        raise HTTPException(status_code=400, detail="JSON must be an array of rule objects")

    required_fields = {"pattern", "classification", "severity", "solution"}
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise HTTPException(status_code=400, detail=f"Rule at index {i} must be an object")
        missing = required_fields - set(rule.keys())
        if missing:
            raise HTTPException(status_code=400, detail=f"Rule at index {i} missing: {', '.join(missing)}")
        import re
        try:
            re.compile(rule["pattern"])
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"Rule at index {i} invalid regex: {e}")

    # Backup and save
    if os.path.exists(REGEX_RULES_PATH):
        shutil.copy2(REGEX_RULES_PATH, f"{REGEX_RULES_PATH}.backup")

    with open(REGEX_RULES_PATH, "w") as f:
        json.dump(rules, f, indent=2)

    # Reload regex engine
    if router and router.regex_engine:
        try:
            from backend.stages.regex_engine import RegexEngine
            router.regex_engine = RegexEngine()
        except Exception as e:
            logger.warning(f"[API] /upload-regex-rules — reload failed: {e}")

    return {"status": "success", "total_rules": len(rules)}


@app.post("/upload-training-data")
async def upload_training_data(file: UploadFile = File(...)):
    """Upload a CSV dataset and retrain the model on it."""
    logger.info(f"[API] /upload-training-data — file: {file.filename}")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv file")

    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_FILE_SIZE_MB}MB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    try:
        from io import BytesIO
        df = pd.read_csv(BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file: {e}")

    required_columns = {"log_text", "label"}
    missing_cols = required_columns - set(df.columns)
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing columns: {', '.join(missing_cols)}. Need 'log_text' and 'label'."
        )

    df = df.dropna(subset=["log_text", "label"])
    if len(df) < 20:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 20 valid rows. Got {len(df)}."
        )

    # Save uploaded file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_path = os.path.join(UPLOAD_DIR, f"training_{timestamp}.csv")
    df.to_csv(saved_path, index=False)

    # Retrain
    try:
        result = retrain_from_uploaded_file(saved_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {e}")

    # Reload ML engine
    if result["status"] == "success" and router and router.ml_engine:
        try:
            from backend.ml.inference import MLInference
            router.ml_engine = MLInference()
            result["model_reloaded"] = True
        except Exception as e:
            logger.warning(f"[API] /upload-training-data — reload failed: {e}")
            result["model_reloaded"] = False

    return result
