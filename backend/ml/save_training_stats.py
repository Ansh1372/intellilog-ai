"""
Save training data class distribution stats.
Used by drift detection to compare against incoming predictions.
"""

import logging
import joblib
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

TRAINING_DATA_PATH = "data/advanced_train_logs.csv"
STATS_OUTPUT_PATH = "models/training_stats.pkl"


def save_stats():
    """Compute and save class distribution from training data."""

    logger.info("[STATS] Computing training data statistics")

    try:
        df = pd.read_csv(TRAINING_DATA_PATH)
        df = df.dropna(subset=["label"])

        class_counts = df["label"].value_counts()
        total = len(df)

        # Normalized distribution (proportions)
        distribution = (class_counts / total).to_dict()

        joblib.dump(distribution, STATS_OUTPUT_PATH)

        logger.info(f"[STATS] Saved distribution for {len(distribution)} classes")
        logger.info(f"[STATS] Output: {STATS_OUTPUT_PATH}")

        for cls, prop in sorted(distribution.items(), key=lambda x: -x[1]):
            logger.info(f"  {cls}: {prop:.4f} ({int(prop * total)} samples)")

        return {"status": "success", "classes": len(distribution)}

    except Exception as e:
        logger.error(f"[STATS] Failed: {e}")
        return {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    result = save_stats()
    print(f"\nResult: {result}")
