"""
IntelliLog AI — Pipeline Evaluation Script

Evaluates the multi-stage classification pipeline against
labeled test data and reports per-stage performance.
"""

import pandas as pd
from backend.stages.regex_engine import RegexEngine
from backend.ml.inference import MLInference


def evaluate_pipeline():
    # Load labeled test data
    df = pd.read_csv("data/advanced_train_logs.csv")

    # Sample a subset for evaluation
    test_df = df.sample(n=min(1500, len(df)), random_state=42).reset_index(drop=True)

    regex_engine = RegexEngine()
    ml_engine = MLInference()

    # Counters
    regex_correct = 0
    regex_total = 0
    ml_high_correct = 0
    ml_high_total = 0
    ml_medium_correct = 0
    ml_medium_total = 0
    ml_low_total = 0
    llm_total = 0

    total = len(test_df)

    for _, row in test_df.iterrows():
        log_text = row["log_text"]
        true_label = row["label"]

        # Stage 1: Regex
        regex_result = regex_engine.classify(log_text)

        if regex_result["matched"]:
            regex_total += 1
            if regex_result["classification"] == true_label:
                regex_correct += 1
            continue

        # Stage 2: ML
        ml_result = ml_engine.predict(log_text)
        confidence = ml_result["confidence"]

        if confidence >= 0.90:
            ml_high_total += 1
            if ml_result["prediction"] == true_label:
                ml_high_correct += 1

        elif confidence >= 0.70:
            ml_medium_total += 1
            if ml_result["prediction"] == true_label:
                ml_medium_correct += 1

        elif confidence >= 0.40:
            ml_low_total += 1

        else:
            # Would go to LLM
            llm_total += 1

    # Results
    ml_total = ml_high_total + ml_medium_total
    ml_correct = ml_high_correct + ml_medium_correct

    print("\n" + "=" * 50)
    print("   IntelliLog AI — Pipeline Evaluation")
    print("=" * 50)
    print(f"\nTotal logs evaluated: {total}")

    print(f"\n{'Stage':<25} {'Routed':<10} {'Accuracy':<12} {'% of Total'}")
    print("-" * 60)

    regex_acc = (regex_correct / regex_total * 100) if regex_total > 0 else 0
    print(f"{'Regex Engine':<25} {regex_total:<10} {regex_acc:.1f}%{'':<6} {regex_total/total*100:.1f}%")

    ml_high_acc = (ml_high_correct / ml_high_total * 100) if ml_high_total > 0 else 0
    print(f"{'ML (High Conf >=0.90)':<25} {ml_high_total:<10} {ml_high_acc:.1f}%{'':<6} {ml_high_total/total*100:.1f}%")

    ml_med_acc = (ml_medium_correct / ml_medium_total * 100) if ml_medium_total > 0 else 0
    print(f"{'ML (Medium Conf >=0.70)':<25} {ml_medium_total:<10} {ml_med_acc:.1f}%{'':<6} {ml_medium_total/total*100:.1f}%")

    print(f"{'ML (Low Conf >=0.40)':<25} {ml_low_total:<10} {'N/A':<12} {ml_low_total/total*100:.1f}%")
    print(f"{'LLM Fallback (<0.40)':<25} {llm_total:<10} {'N/A':<12} {llm_total/total*100:.1f}%")

    # Overall
    total_correct = regex_correct + ml_correct
    total_classified = regex_total + ml_total
    overall_acc = (total_correct / total_classified * 100) if total_classified > 0 else 0

    print(f"\n{'=' * 50}")
    print(f"Overall Accuracy (Regex + ML): {overall_acc:.1f}%")
    print(f"Resolved without LLM: {(regex_total + ml_total + ml_low_total) / total * 100:.1f}%")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    evaluate_pipeline()
