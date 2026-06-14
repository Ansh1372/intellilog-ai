import pandas as pd
import random

categories = {
    "Authentication Failure": [
        "authentication failed for user {}",
        "invalid login credentials for {}",
        "access denied for account {}",
        "token expired during login for {}"
    ],

    "Database Error": [
        "database connection timeout on {}",
        "connection refused to postgres database {}",
        "db pool exhausted on service {}",
        "unable to connect to mysql instance {}"
    ],

    "API Timeout": [
        "api request timeout on endpoint {}",
        "gateway timeout from service {}",
        "request exceeded timeout limit for {}",
        "upstream api timeout detected in {}"
    ],

    "Disk Full": [
        "disk space exceeded on server {}",
        "no storage left on device {}",
        "filesystem full on instance {}",
        "unable to write log due to disk full {}"
    ]
}

systems = [
    "auth-service",
    "payment-service",
    "user-service",
    "prod-server-1",
    "db-cluster",
    "gateway-api"
]

dataset = []

for category, templates in categories.items():

    for _ in range(250):

        template = random.choice(templates)

        system = random.choice(systems)

        log = template.format(system)

        dataset.append({
            "log_text": log,
            "label": category
        })

df = pd.DataFrame(dataset)

df = df.sample(frac=1).reset_index(drop=True)

df.to_csv("data/train_logs.csv", index=False)

print("Synthetic dataset generated successfully!")
print(f"Total logs generated: {len(df)}")