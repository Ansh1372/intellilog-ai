"""
prepare_loghub.py — Preprocesses raw Loghub datasets into training CSV format.

Usage:
    1. Download Loghub datasets into data/loghub/ folder:
       git clone https://github.com/logpai/loghub.git data/loghub
       (or just download specific folders: Linux, Apache, OpenSSH, Zookeeper, Hadoop)

    2. Run this script:
       python data/prepare_loghub.py

    3. Output: data/real_train_logs.csv (log_text, label)

    4. Train model:
       python -m backend.ml.train_model
"""

import os
import re
import pandas as pd
from pathlib import Path


# =========================================
# CONFIG
# =========================================

LOGHUB_DIR = os.path.join("data", "loghub")
OUTPUT_CSV = os.path.join("data", "real_train_logs.csv")
MAX_SAMPLES_PER_DATASET = 2000
MIN_LOG_LENGTH = 10


# =========================================
# LABELING RULES PER DATASET
# =========================================

# Each dataset has keyword-based rules to assign labels.
# If no rule matches, the log is labeled "Normal Operation" or skipped.

LABEL_RULES = {
    "authentication": [
        (r"(?i)(failed|invalid|illegal).*(password|login|user|auth)", "Authentication Failure"),
        (r"(?i)(denied|refused|rejected).*(access|connection|session)", "Authentication Failure"),
        (r"(?i)authentication failure", "Authentication Failure"),
        (r"(?i)unauthorized", "Authentication Failure"),
    ],
    "database": [
        (r"(?i)(database|db|postgres|mysql|mongo).*(timeout|refused|error|fail|unreachable)", "Database Error"),
        (r"(?i)(connection|query).*(timeout|refused|fail)", "Database Error"),
        (r"(?i)deadlock", "Database Error"),
    ],
    "http": [
        (r"(?i)\b404\b.*not found", "HTTP 404"),
        (r"(?i)file does not exist", "HTTP 404"),
        (r"(?i)\b403\b.*forbidden", "HTTP 403"),
        (r"(?i)\b500\b.*internal", "HTTP 500"),
        (r"(?i)internal server error", "HTTP 500"),
    ],
    "memory": [
        (r"(?i)(out of memory|oom|memory.*exhaust|heap.*full)", "Memory Leak"),
        (r"(?i)oom.?killer", "Memory Leak"),
        (r"(?i)memory allocation fail", "Memory Leak"),
    ],
    "disk": [
        (r"(?i)(disk|filesystem|storage).*(full|no space|exceeded|quota)", "Disk Full"),
        (r"(?i)no space left on device", "Disk Full"),
    ],
    "network": [
        (r"(?i)(dns).*(fail|timeout|unable|unreachable)", "DNS Failure"),
        (r"(?i)(ssl|tls|certificate).*(expired|fail|invalid|error)", "SSL Error"),
        (r"(?i)(timeout|timed out).*(connect|request|response)", "API Timeout"),
    ],
    "kubernetes": [
        (r"(?i)(crashloop|crash.*loop)", "Kubernetes CrashLoop"),
        (r"(?i)pod.*(restart|terminated|killed|fail)", "Kubernetes CrashLoop"),
        (r"(?i)container.*died", "Kubernetes CrashLoop"),
    ],
    "redis_kafka": [
        (r"(?i)(redis|cache).*(unavailable|timeout|fail|error)", "Redis Failure"),
        (r"(?i)(kafka|broker|consumer).*(fail|timeout|lag|error)", "Kafka Failure"),
    ],
    "cpu": [
        (r"(?i)(cpu).*(spike|exceeded|threshold|overload|throttl)", "CPU Spike"),
    ],
}


# =========================================
# PREPROCESSING FUNCTIONS
# =========================================

def is_valid_log(line: str) -> bool:
    """Check if a line is a valid log (not garbage)."""
    line = line.strip()
    if len(line) < MIN_LOG_LENGTH:
        return False
    if line.startswith("#") or line.startswith("//"):
        return False
    if set(line) <= set("-=_ \t"):
        return False
    # Skip lines that are purely numeric
    if re.match(r"^[\d\s.,:]+$", line):
        return False
    return True


def label_log(log_text: str) -> str:
    """Assign a label to a log line based on keyword rules."""
    for category_rules in LABEL_RULES.values():
        for pattern, label in category_rules:
            if re.search(pattern, log_text):
                return label
    return None  # No match — will be skipped or labeled Normal


def process_log_file(filepath: str, dataset_name: str) -> list:
    """Process a single raw log file."""
    logs = []
    seen = set()

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()

                if not is_valid_log(line):
                    continue

                # Deduplicate
                if line in seen:
                    continue
                seen.add(line)

                logs.append(line)
    except Exception as e:
        print(f"  [WARN] Could not read {filepath}: {e}")

    return logs


def process_dataset(dataset_path: str, dataset_name: str) -> pd.DataFrame:
    """Process all log files in a dataset folder."""
    print(f"\n[PROCESSING] {dataset_name} — {dataset_path}")

    all_logs = []

    # Find log files (common extensions)
    log_extensions = [".log", ".txt", ".csv_structured"]
    log_files = []

    for root, dirs, files in os.walk(dataset_path):
        for f in files:
            # Only process raw log files, skip structured/parsed ones
            if f.endswith("_structured.csv") or f.endswith("_templates.csv"):
                continue
            if any(f.endswith(ext) for ext in [".log", ".txt"]):
                log_files.append(os.path.join(root, f))
            # Some loghub datasets have the raw logs in a file without extension
            # or with .log extension inside the folder
            if f.endswith(".log") or (f == f"{dataset_name}.log"):
                log_files.append(os.path.join(root, f))

    # Deduplicate file paths
    log_files = list(set(log_files))

    if not log_files:
        # Try to find any text-like files
        for root, dirs, files in os.walk(dataset_path):
            for f in files:
                full = os.path.join(root, f)
                if os.path.getsize(full) > 100:  # Not empty
                    if not f.endswith((".csv", ".png", ".jpg", ".json", ".py", ".md")):
                        log_files.append(full)
        log_files = list(set(log_files))

    print(f"  Found {len(log_files)} log file(s)")

    for lf in log_files:
        logs = process_log_file(lf, dataset_name)
        all_logs.extend(logs)
        print(f"  {os.path.basename(lf)}: {len(logs)} unique lines")

    # Deduplicate across files
    all_logs = list(set(all_logs))
    print(f"  Total unique logs: {len(all_logs)}")

    # Sample if too many
    if len(all_logs) > MAX_SAMPLES_PER_DATASET:
        import random
        random.seed(999)
        all_logs = random.sample(all_logs, MAX_SAMPLES_PER_DATASET)
        print(f"  Sampled down to: {MAX_SAMPLES_PER_DATASET}")

    # Label logs
    labeled = []
    skipped = 0

    for log in all_logs:
        label = label_log(log)
        if label:
            labeled.append({"log_text": log, "label": label})
        else:
            skipped += 1

    print(f"  Labeled: {len(labeled)}, Skipped (no match): {skipped}")

    return pd.DataFrame(labeled)


# =========================================
# MAIN
# =========================================

def main():
    print("=" * 60)
    print("LOGHUB DATA PREPARATION")
    print("=" * 60)

    if not os.path.exists(LOGHUB_DIR):
        print(f"\n[ERROR] Loghub directory not found: {LOGHUB_DIR}")
        print(f"Download it first:")
        print(f"  git clone https://github.com/logpai/loghub.git {LOGHUB_DIR}")
        print(f"\nOr download specific folders (Linux, Apache, OpenSSH, etc.) into {LOGHUB_DIR}/")
        return

    # Find available datasets
    datasets = []
    target_datasets = ["Linux", "Apache", "OpenSSH", "Zookeeper", "Hadoop",
                       "HDFS", "OpenStack", "Spark", "BGL", "HPC",
                       "Thunderbird", "Windows", "Mac", "Android",
                       "HealthApp", "Proxifier"]

    for name in os.listdir(LOGHUB_DIR):
        full_path = os.path.join(LOGHUB_DIR, name)
        if os.path.isdir(full_path) and not name.startswith("."):
            datasets.append((name, full_path))

    if not datasets:
        print(f"\n[ERROR] No dataset folders found in {LOGHUB_DIR}/")
        print(f"Expected folders like: Linux/, Apache/, OpenSSH/, etc.")
        return

    print(f"\nFound {len(datasets)} dataset(s): {[d[0] for d in datasets]}")

    # Process each dataset
    all_frames = []

    for name, path in datasets:
        df = process_dataset(path, name)
        if not df.empty:
            all_frames.append(df)

    if not all_frames:
        print("\n[ERROR] No labeled logs produced. Check your Loghub data.")
        return

    # Merge all
    final_df = pd.concat(all_frames, ignore_index=True)

    # Final dedup
    final_df = final_df.drop_duplicates(subset=["log_text"])

    print("\n" + "=" * 60)
    print("FINAL DATASET SUMMARY")
    print("=" * 60)
    print(f"Total labeled logs: {len(final_df)}")
    print(f"\nLabel distribution:")
    print(final_df["label"].value_counts().to_string())

    # Save
    final_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved to: {OUTPUT_CSV}")
    print(f"\nNext step: python -m backend.ml.train_model")
    print(f"(Update train_model.py to use '{OUTPUT_CSV}' or merge with existing data)")


if __name__ == "__main__":
    main()
