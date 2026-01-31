"""
ML Validation Audit Script - Investigates Perfect Metrics

This script performs comprehensive audits to understand:
1. Why Recall = 1.0 with no variance
2. Why threshold = 0.3 (very low)
3. Feature importance imbalance (late_count dominance)
4. Label definition vs feature correlation

Run: py -m src.ml.audit_perfect_metrics
"""

import sys
import os

project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import Counter
import json

from src.ml.preprocessing import engineer_features_from_df, FEATURE_COLUMNS
from src.ml.training import create_target_labels, train_and_save_models
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def generate_mock_data(n_students=90, days_back=30):
    """Generate realistic mock attendance data."""
    np.random.seed(42)
    end_date = datetime.now().date()
    dates = [(end_date - timedelta(days=i)) for i in range(days_back)]

    records = []

    # 15 at-risk students with varying patterns
    for i in range(15):
        nis = f"ATRISK-{i+1:03d}"
        
        if i < 5:
            # Extreme late_count (8-12 lates)
            late_prob = 0.35
            absent_prob = 0.10
        elif i < 10:
            # Moderate late_count (4-6 lates)
            late_prob = 0.20
            absent_prob = 0.15
        else:
            # Low attendance ratio (<85%)
            late_prob = 0.10
            absent_prob = 0.25

        for date in dates:
            r = np.random.random()
            if r < absent_prob:
                status = "Absent"
            elif r < absent_prob + late_prob:
                status = "Late"
            elif r < absent_prob + late_prob + 0.05:
                status = "Sick"
            else:
                status = "Present"
            records.append({"nis": nis, "date": date, "status": status})

    # 75 normal students (mostly present, occasional late)
    for i in range(75):
        nis = f"NORMAL-{i+1:03d}"
        for date in dates:
            r = np.random.random()
            if r < 0.93:
                status = "Present"
            elif r < 0.97:
                status = "Late"
            else:
                status = "Sick"
            records.append({"nis": nis, "date": date, "status": status})

    return pd.DataFrame(records)


def audit_label_definition(features_df):
    """
    Audit 1: Analyze label definition vs feature correlation.
    """
    logger.info("\n" + "=" * 80)
    logger.info("AUDIT 1: LABEL DEFINITION vs FEATURE CORRELATION")
    logger.info("=" * 80)

    y = create_target_labels(features_df)
    
    logger.info(f"\nTotal students: {len(features_df)}")
    logger.info(f"At-risk: {y.sum()} ({y.sum()/len(y)*100:.1f}%)")
    logger.info(f"Normal: {(1-y).sum()} ({(1-y).sum()/len(y)*100:.1f}%)")

    # Analyze which rule triggers most
    late_rule = features_df["late_count"] > 3
    attendance_rule = features_df["attendance_ratio"] < 0.85
    trend_rule = features_df["trend_score"] < -0.2
    quality_rule = (features_df["recording_completeness"] < 0.5) & (features_df["present_count"] < 10)

    logger.info("\nLabel Trigger Analysis:")
    logger.info(f"  Triggered by late_count > 3:          {late_rule.sum():3d} ({late_rule.sum()/len(y)*100:5.1f}%)")
    logger.info(f"  Triggered by attendance_ratio < 0.85: {attendance_rule.sum():3d} ({attendance_rule.sum()/len(y)*100:5.1f}%)")
    logger.info(f"  Triggered by trend_score < -0.2:      {trend_rule.sum():3d} ({trend_rule.sum()/len(y)*100:5.1f}%)")
    logger.info(f"  Triggered by quality rule:            {quality_rule.sum():3d} ({quality_rule.sum()/len(y)*100:5.1f}%)")
    
    # Check overlap
    only_late = late_rule & ~attendance_rule & ~trend_rule & ~quality_rule
    logger.info(f"\n  ONLY late_count (no other rule):     {only_late.sum():3d} ({only_late.sum()/len(y)*100:5.1f}%)")

    # Feature distribution by label
    logger.info("\nFeature Distribution by Label:")
    for col in ["late_count", "attendance_ratio", "trend_score"]:
        at_risk_vals = features_df[y == 1][col]
        normal_vals = features_df[y == 0][col]
        
        logger.info(f"\n  {col}:")
        logger.info(f"    At-risk: mean={at_risk_vals.mean():.3f}, median={at_risk_vals.median():.3f}, std={at_risk_vals.std():.3f}")
        logger.info(f"    Normal:  mean={normal_vals.mean():.3f}, median={normal_vals.median():.3f}, std={normal_vals.std():.3f}")
        logger.info(f"    Separation: {abs(at_risk_vals.mean() - normal_vals.mean()):.3f}")

    return y


def audit_feature_ablation(features_df, y):
    """
    Audit 2: Ablation study - test model without late_count.
    """
    logger.info("\n" + "=" * 80)
    logger.info("AUDIT 2: FEATURE ABLATION STUDY")
    logger.info("=" * 80)

    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score, GroupKFold
    from sklearn.metrics import recall_score, f1_score
    from src.ml.preprocessing import prepare_features_for_model

    X = prepare_features_for_model(features_df)
    groups = features_df["nis"]

    # Test 1: All features (baseline)
    logger.info("\n[Baseline] All 10 features:")
    cv_scores = cross_val_score(
        LogisticRegression(class_weight='balanced', max_iter=1000),
        X, y, cv=GroupKFold(n_splits=3), groups=groups, scoring='recall'
    )
    logger.info(f"  CV Recall: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Test 2: Without late_count
    logger.info("\n[Ablation] WITHOUT late_count:")
    X_no_late = X.drop(columns=["late_count"])
    cv_scores_no_late = cross_val_score(
        LogisticRegression(class_weight='balanced', max_iter=1000),
        X_no_late, y, cv=GroupKFold(n_splits=3), groups=groups, scoring='recall'
    )
    logger.info(f"  CV Recall: {cv_scores_no_late.mean():.3f} ± {cv_scores_no_late.std():.3f}")
    drop = cv_scores.mean() - cv_scores_no_late.mean()
    logger.info(f"  Performance drop: {drop:.3f} ({drop/cv_scores.mean()*100:.1f}%)")

    if drop > 0.3:
        logger.warning("  ⚠️  ALERT: Large drop (>30%) suggests late_count is primary predictor!")
        logger.warning("  ⚠️  Model may be 'rule approximator' for late_count threshold")
    
    # Test 3: ONLY late_count
    logger.info("\n[Ablation] ONLY late_count:")
    X_only_late = X[["late_count"]]
    cv_scores_only_late = cross_val_score(
        LogisticRegression(class_weight='balanced', max_iter=1000),
        X_only_late, y, cv=GroupKFold(n_splits=3), groups=groups, scoring='recall'
    )
    logger.info(f"  CV Recall: {cv_scores_only_late.mean():.3f} ± {cv_scores_only_late.std():.3f}")
    
    if cv_scores_only_late.mean() > 0.95:
        logger.warning("  ⚠️  ALERT: late_count alone achieves >95% recall!")
        logger.warning("  ⚠️  Other features add minimal value")

    # Test 4: Only behavioral (no counts)
    logger.info("\n[Ablation] ONLY ratios/trends (no counts):")
    ratio_features = ["attendance_ratio", "trend_score", "recording_completeness"]
    X_ratios = X[ratio_features]
    cv_scores_ratios = cross_val_score(
        LogisticRegression(class_weight='balanced', max_iter=1000),
        X_ratios, y, cv=GroupKFold(n_splits=3), groups=groups, scoring='recall'
    )
    logger.info(f"  CV Recall: {cv_scores_ratios.mean():.3f} ± {cv_scores_ratios.std():.3f}")


def audit_threshold_decision(features_df, y):
    """
    Audit 3: Investigate why threshold = 0.3 (very low).
    """
    logger.info("\n" + "=" * 80)
    logger.info("AUDIT 3: THRESHOLD DECISION ANALYSIS")
    logger.info("=" * 80)

    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_predict, GroupKFold
    from sklearn.metrics import recall_score, precision_score, f1_score
    from src.ml.preprocessing import prepare_features_for_model

    X = prepare_features_for_model(features_df)
    groups = features_df["nis"]

    # Get OOF predictions
    model = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
    y_proba_oof = cross_val_predict(
        model, X, y, cv=GroupKFold(n_splits=3), groups=groups, method='predict_proba'
    )[:, 1]

    logger.info("\nThreshold Analysis (OOF predictions):")
    logger.info("  Threshold | Recall | Precision |   F1   | TP | FP | FN | TN")
    logger.info("  " + "-" * 65)
    
    for threshold in [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]:
        y_pred = (y_proba_oof >= threshold).astype(int)
        recall = recall_score(y, y_pred)
        precision = precision_score(y, y_pred, zero_division=0)
        f1 = f1_score(y, y_pred)
        
        tp = ((y == 1) & (y_pred == 1)).sum()
        fp = ((y == 0) & (y_pred == 1)).sum()
        fn = ((y == 1) & (y_pred == 0)).sum()
        tn = ((y == 0) & (y_pred == 0)).sum()
        
        marker = " ← OPTIMAL" if threshold == 0.3 else ""
        logger.info(f"     {threshold:.2f}  |  {recall:.3f} |   {precision:.3f}  | {f1:.3f} | {tp:2d} | {fp:2d} | {fn:2d} | {tn:2d}{marker}")

    # Check if threshold 0.5 already achieves target
    y_pred_50 = (y_proba_oof >= 0.5).astype(int)
    recall_50 = recall_score(y, y_pred_50)
    
    logger.info(f"\n✓ At threshold=0.5: Recall = {recall_50:.3f}")
    if recall_50 >= 1.0:
        logger.warning("  ⚠️  ALERT: Recall already 1.0 at threshold 0.5!")
        logger.warning("  ⚠️  Lowering to 0.3 is unnecessary and increases false positives")
    elif recall_50 >= 0.70:
        logger.info("  ✓ Target recall (≥0.70) already met at threshold 0.5")
        logger.warning("  ⚠️  Threshold 0.3 may be too aggressive")


def audit_test_set_size():
    """
    Audit 4: Analyze test set representativeness.
    """
    logger.info("\n" + "=" * 80)
    logger.info("AUDIT 4: TEST SET REPRESENTATIVENESS")
    logger.info("=" * 80)

    metadata_path = "models/model_metadata.json"
    if not os.path.exists(metadata_path):
        logger.warning("No metadata found. Run training first.")
        return

    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    test_metrics = metadata.get("test_metrics", {})
    cm = test_metrics.get("confusion_matrix", {})
    test_size = test_metrics.get("test_size", 0)
    
    tp = cm.get("tp", 0)
    fp = cm.get("fp", 0)
    fn = cm.get("fn", 0)
    tn = cm.get("tn", 0)

    total_atrisk = tp + fn
    total_normal = tn + fp

    logger.info(f"\nTest Set Composition:")
    logger.info(f"  Total: {test_size} students")
    logger.info(f"  At-risk: {total_atrisk} ({total_atrisk/test_size*100:.1f}%)")
    logger.info(f"  Normal: {total_normal} ({total_normal/test_size*100:.1f}%)")
    
    logger.info(f"\nConfusion Matrix:")
    logger.info(f"  True Positives:  {tp} (detected at-risk)")
    logger.info(f"  False Negatives: {fn} (missed at-risk) ← FN=0 = Perfect!")
    logger.info(f"  False Positives: {fp} (false alarms)")
    logger.info(f"  True Negatives:  {tn} (correct normal)")

    if fn == 0:
        logger.warning(f"\n  ⚠️  ALERT: Zero false negatives with only {total_atrisk} at-risk students!")
        logger.warning("  ⚠️  Perfect recall on small sample may not generalize")
    
    # Bootstrap CI analysis
    bootstrap_ci = test_metrics.get("bootstrap_ci", {})
    f1_ci = bootstrap_ci.get("f1", [0, 0])
    precision_ci = bootstrap_ci.get("precision", [0, 0])
    
    f1_range = f1_ci[1] - f1_ci[0]
    precision_range = precision_ci[1] - precision_ci[0]
    
    logger.info(f"\nBootstrap CI Analysis:")
    logger.info(f"  F1 range: [{f1_ci[0]:.2f}, {f1_ci[1]:.2f}] (width: {f1_range:.2f})")
    logger.info(f"  Precision range: [{precision_ci[0]:.2f}, {precision_ci[1]:.2f}] (width: {precision_range:.2f})")
    
    if f1_range > 0.4:
        logger.warning(f"  ⚠️  ALERT: Very wide F1 CI (>{0.4:.1f}) indicates high uncertainty!")
    if precision_range > 0.5:
        logger.warning(f"  ⚠️  ALERT: Very wide Precision CI (>{0.5:.1f}) indicates high uncertainty!")


def main():
    logger.info("\n" + "=" * 80)
    logger.info("ML VALIDATION AUDIT - Investigating Perfect Metrics")
    logger.info("=" * 80)

    # Generate data
    logger.info("\nGenerating mock data (90 students, 30 days)...")
    df = generate_mock_data()
    
    # Engineer features
    features_df = engineer_features_from_df(df)
    logger.info(f"Engineered features for {len(features_df)} students")

    # Run audits
    y = audit_label_definition(features_df)
    audit_feature_ablation(features_df, y)
    audit_threshold_decision(features_df, y)
    audit_test_set_size()

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("AUDIT SUMMARY & RECOMMENDATIONS")
    logger.info("=" * 80)
    logger.info("""
Based on the audits above, the following may explain perfect metrics:

1. If late_count dominates (coefficient ~1.94):
   → Model is primarily a 'late_count threshold classifier'
   → This is essentially a rule approximator, not complex pattern learning
   
2. If threshold=0.3 is unnecessary (Recall=1.0 at threshold=0.5):
   → Lowering threshold increases false positives without benefit
   → Should use threshold=0.5 for better precision
   
3. If test set has only 5 at-risk students:
   → Perfect recall (FN=0) can occur by chance
   → Wide bootstrap CI confirms high uncertainty
   
RECOMMENDATIONS:
- Disclose: "Model heavily relies on late_count feature (coef=1.94)"
- Consider: Remove late_count from features to force model to use other signals
- Update: Threshold to 0.5 if Recall already ≥0.70 at that level
- Report: Metrics with full bootstrap CI to show uncertainty
- Add: Limitation about small test set size and generalization concerns
""")


if __name__ == "__main__":
    main()
