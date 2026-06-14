import random
import pandas as pd


LOG_TEMPLATES = {

    "Authentication Failure": [

        "invalid login credentials for user",
        "jwt token expired during authentication",
        "unauthorized access attempt detected",
        "oauth token validation failed",
        "authentication failed for admin user",
        "session token expired unexpectedly",
        "access denied due to invalid api key",
        "failed password verification"
    ],

    "Database Error": [

        "postgres connection timeout",
        "database connection pool exhausted",
        "mysql deadlock detected",
        "database node unreachable",
        "query execution timeout exceeded",
        "replication lag detected in database cluster",
        "database transaction rollback occurred",
        "primary database server unavailable"
    ],

    "API Timeout": [

        "gateway request timeout exceeded",
        "api response delayed beyond threshold",
        "upstream service timeout occurred",
        "http request timeout detected",
        "api latency spike observed",
        "microservice communication timeout",
        "request exceeded timeout limit",
        "external api timeout failure"
    ],

    "Disk Full": [

        "filesystem full on production server",
        "disk usage exceeded threshold",
        "storage volume unavailable due to full capacity",
        "unable to write logs due to disk exhaustion",
        "critical storage shortage detected",
        "server disk space critically low",
        "persistent volume capacity exceeded",
        "disk allocation failure"
    ],

    "HTTP 403": [

        "403 forbidden access",
        "user forbidden from accessing resource",
        "authorization failed with 403",
        "http 403 returned from server",
        "permission denied while accessing endpoint",
        "forbidden api access detected"
    ],

    "HTTP 404": [

        "404 page not found",
        "resource endpoint missing",
        "http 404 returned from service",
        "requested api endpoint unavailable",
        "missing route detected",
        "url not found on server"
    ],

    "HTTP 500": [

        "500 internal server error",
        "application crashed with 500 response",
        "unexpected backend exception occurred",
        "server encountered fatal runtime error",
        "internal application failure detected",
        "null pointer exception generated 500"
    ],

    "Memory Leak": [

        "java heap space out of memory",
        "memory leak suspected in application",
        "container memory usage continuously increasing",
        "oom killer terminated process",
        "high memory utilization detected",
        "memory allocation failure occurred"
    ],

    "CPU Spike": [

        "cpu usage exceeded critical threshold",
        "unexpected processor spike detected",
        "high cpu load on production node",
        "container cpu throttling activated",
        "system under heavy computational load",
        "cpu saturation warning triggered"
    ],

    "Kubernetes CrashLoop": [

        "pod entered crashloopbackoff state",
        "kubernetes pod restarting repeatedly",
        "deployment failed due to pod crash",
        "container terminated unexpectedly",
        "pod healthcheck failed continuously",
        "orchestrator detected unstable container"
    ],

    "SSL Error": [

        "ssl certificate expired",
        "tls handshake failure detected",
        "certificate validation failed",
        "secure connection could not be established",
        "invalid ssl chain detected",
        "https certificate mismatch error"
    ],

    "DNS Failure": [

        "dns resolution failed",
        "hostname lookup timeout",
        "unable to resolve service hostname",
        "dns server unavailable",
        "service discovery resolution failed",
        "network dns lookup failure"
    ],

    "Redis Failure": [

        "redis cache unavailable",
        "redis connection timeout",
        "cache node unreachable",
        "redis cluster synchronization failed",
        "cache lookup operation failed",
        "redis memory eviction triggered"
    ],

    "Kafka Failure": [

        "kafka consumer lag exceeded threshold",
        "message broker unavailable",
        "kafka partition leader missing",
        "stream processing interrupted",
        "failed to publish event to kafka",
        "consumer group rebalance failed"
    ],

    "Payment Failure": [

        "payment transaction declined",
        "credit card authorization failed",
        "payment gateway timeout occurred",
        "unable to process customer payment",
        "financial transaction rollback detected",
        "payment service unavailable"
    ]
}


SYSTEMS = [
    "auth-service",
    "payment-service",
    "prod-server-1",
    "prod-server-2",
    "k8s-node-4",
    "api-gateway",
    "db-cluster",
    "redis-cache",
    "kafka-broker",
    "frontend-app"
]


ROWS = []


for label, templates in LOG_TEMPLATES.items():

    for _ in range(700):

        template = random.choice(templates)

        system = random.choice(SYSTEMS)

        log = f"{template} on {system}"

        ROWS.append({

            "log_text": log,
            "label": label
        })


df = pd.DataFrame(ROWS)

df.to_csv("data/advanced_train_logs.csv", index=False)

print("Advanced dataset generated successfully!")
print(f"Total logs: {len(df)}")