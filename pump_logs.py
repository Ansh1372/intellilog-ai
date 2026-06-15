import requests
import json
import time
import random
from datetime import datetime, timedelta
import threading

URL = "https://ansh1372-intellilog-backend.hf.space/classify"

log_templates = [
    # ===== ERROR LOGS (30%) =====
    # Authentication Failures
    {"msg": "Authentication failed for user admin@company.com — invalid credentials", "sev": "ERROR", "svc": "AuthService"},
    {"msg": "Login denied: too many failed attempts from IP 10.0.{ip}.{ip2}", "sev": "ERROR", "svc": "AuthService"},
    {"msg": "JWT token expired during authentication for session SES-{id}", "sev": "ERROR", "svc": "AuthService"},

    # Database Errors
    {"msg": "Database connection timeout after 30s — postgres pool exhausted", "sev": "ERROR", "svc": "DatabaseService"},
    {"msg": "MySQL deadlock detected on transaction TXN-{id}", "sev": "ERROR", "svc": "DatabaseService"},
    {"msg": "Database node db-replica-{node} unreachable — failover initiated", "sev": "ERROR", "svc": "DatabaseService"},

    # HTTP 500
    {"msg": "500 Internal Server Error on /api/v2/orders — NullPointerException", "sev": "ERROR", "svc": "APIGateway"},
    {"msg": "Fatal runtime error in payment processing module", "sev": "ERROR", "svc": "PaymentGateway"},

    # Memory Leak
    {"msg": "Java heap space out of memory — container worker-{node} terminated by OOM killer", "sev": "CRITICAL", "svc": "WorkerService"},
    {"msg": "Memory leak suspected in connection pool — usage at 98%", "sev": "ERROR", "svc": "WorkerService"},

    # Kubernetes CrashLoop
    {"msg": "Pod api-gateway-{id} entered CrashLoopBackOff state after 5 restarts", "sev": "CRITICAL", "svc": "K8sCluster"},
    {"msg": "Container terminated unexpectedly — exit code 137 on node-{node}", "sev": "CRITICAL", "svc": "K8sCluster"},

    # SSL Error
    {"msg": "SSL certificate expired for domain api.company.com", "sev": "ERROR", "svc": "APIGateway"},
    {"msg": "TLS handshake failure detected on port 443", "sev": "ERROR", "svc": "LoadBalancer"},

    # DNS Failure
    {"msg": "DNS resolution failed for service payment-svc.internal — timeout after 10s", "sev": "ERROR", "svc": "NetworkService"},

    # Redis Failure
    {"msg": "Redis cache unavailable — connection refused on redis-master:{id}", "sev": "ERROR", "svc": "CacheService"},
    {"msg": "Redis connection timeout after 5000ms on cache node-{node}", "sev": "ERROR", "svc": "CacheService"},

    # Kafka Failure
    {"msg": "Kafka consumer lag exceeded threshold — 50000 messages behind on topic orders", "sev": "ERROR", "svc": "StreamProcessor"},
    {"msg": "Failed to publish event to Kafka — broker unavailable", "sev": "ERROR", "svc": "StreamProcessor"},

    # Payment Failure
    {"msg": "Payment transaction declined for order ORD-{id} — card authorization failed", "sev": "ERROR", "svc": "PaymentGateway"},
    {"msg": "Payment gateway timeout occurred — Stripe API unresponsive", "sev": "ERROR", "svc": "PaymentGateway"},

    # React Component Error
    {"msg": "React component crash: TypeError: Cannot read property 'map' of undefined in OrderList", "sev": "ERROR", "svc": "FrontendUI"},
    {"msg": "Unhandled React error: Maximum update depth exceeded in Dashboard component", "sev": "ERROR", "svc": "FrontendUI"},

    # API Timeout
    {"msg": "API gateway request timeout exceeded — upstream /api/search took 45s", "sev": "ERROR", "svc": "APIGateway"},
    {"msg": "Microservice communication timeout between auth-svc and user-svc", "sev": "ERROR", "svc": "APIGateway"},

    # Disk Full
    {"msg": "Disk usage exceeded 95% threshold on production server prod-{node}", "sev": "CRITICAL", "svc": "InfraMonitor"},
    {"msg": "Filesystem full — unable to write logs on /var/log partition", "sev": "CRITICAL", "svc": "InfraMonitor"},

    # CPU Spike
    {"msg": "CPU usage exceeded 95% critical threshold on node-{node}", "sev": "WARNING", "svc": "InfraMonitor"},

    # HTTP 403 / 404
    {"msg": "403 Forbidden access to /admin/settings from IP 192.168.{ip}.{ip2}", "sev": "WARNING", "svc": "AuthService"},
    {"msg": "404 page not found: /api/v1/deprecated-endpoint", "sev": "WARNING", "svc": "APIGateway"},

    # ===== WARNING LOGS (25%) =====
    {"msg": "Slow query detected: {ms}ms execution time on users table", "sev": "WARNING", "svc": "DatabaseService"},
    {"msg": "Slow query detected: SELECT * FROM orders took {ms}ms", "sev": "WARNING", "svc": "DatabaseService"},
    {"msg": "API rate limit approaching for user USR-{id} — 950/1000 requests used", "sev": "WARNING", "svc": "APIGateway"},
    {"msg": "Rate limit warning triggered for IP 10.0.{ip}.{ip2}", "sev": "WARNING", "svc": "APIGateway"},
    {"msg": "Memory usage exceeded 85% threshold on node-{node}", "sev": "WARNING", "svc": "InfraMonitor"},
    {"msg": "Memory usage exceeded 90% threshold on worker-{node}", "sev": "WARNING", "svc": "WorkerService"},

    # ===== INFO / SUCCESS LOGS (45%) =====
    {"msg": "User login successful from IP 192.168.{ip}.{ip2}", "sev": "INFO", "svc": "AuthService"},
    {"msg": "User authentication completed successfully for admin@company.com", "sev": "INFO", "svc": "AuthService"},
    {"msg": "Payment processed successfully for order ORD-{id}", "sev": "INFO", "svc": "PaymentGateway"},
    {"msg": "Transaction completed — payment approved for $1{ip}.{ip2}", "sev": "INFO", "svc": "PaymentGateway"},
    {"msg": "Frontend component rendered successfully in {ms}ms", "sev": "INFO", "svc": "FrontendUI"},
    {"msg": "Dashboard component loaded successfully in {ms}ms", "sev": "INFO", "svc": "FrontendUI"},
    {"msg": "Search index updated for {id} items", "sev": "INFO", "svc": "SearchEngine"},
    {"msg": "Search index refreshed — 5{id} documents indexed", "sev": "INFO", "svc": "SearchEngine"},
    {"msg": "Data sync completed between primary and replica databases", "sev": "INFO", "svc": "DatabaseService"},
    {"msg": "Data synchronization finished — 1{id} records synced", "sev": "INFO", "svc": "WorkerService"},
]

def send_log(index):
    template = random.choice(log_templates)

    message = template["msg"].format(
        ip=random.randint(2, 254),
        ip2=random.randint(2, 254),
        id=random.randint(1000, 9999),
        ms=random.randint(100, 3000),
        node=random.randint(1, 10)
    )

    # Spread timestamps over the last 24 hours
    timestamp = (datetime.utcnow() - timedelta(minutes=random.randint(0, 1440))).strftime("%Y-%m-%dT%H:%M:%SZ")

    log = {
        "message": message,
        "service_name": template["svc"],
        "severity": template["sev"],
        "timestamp": timestamp
    }

    try:
        resp = requests.post(
            URL,
            headers={"Content-Type": "application/json"},
            json={"log": json.dumps(log), "source": log["service_name"]},
            timeout=15
        )
        return resp.status_code
    except Exception as e:
        return str(e)

print(f"\n{'='*60}")
print(f"  IntelliLog AI — Log Pump")
print(f"  Target: {URL}")
print(f"  Sending 300 realistic logs...")
print(f"{'='*60}\n")

TOTAL_LOGS = 300
BATCH_SIZE = 15

for batch in range(TOTAL_LOGS // BATCH_SIZE):
    threads = []
    for i in range(BATCH_SIZE):
        t = threading.Thread(target=send_log, args=(batch * BATCH_SIZE + i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    sent = (batch + 1) * BATCH_SIZE
    pct = int(sent / TOTAL_LOGS * 100)
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    print(f"  [{bar}] {sent}/{TOTAL_LOGS} logs sent ({pct}%)")
    time.sleep(0.3)

print(f"\n{'='*60}")
print(f"  ✅ Done! {TOTAL_LOGS} logs pumped successfully.")
print(f"  Check your dashboard at: https://intellilog-ai.vercel.app")
print(f"{'='*60}\n")
