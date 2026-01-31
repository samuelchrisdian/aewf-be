"""
Retrain ML models with optimized threshold (min_threshold=0.40).

This script retrains the model with the updated threshold selection logic
that prevents overly aggressive thresholds (e.g., 0.30) which increase
false positives without benefit.

Based on audit findings (2024-01-24):
- Threshold 0.30: Recall=0.964, Precision=0.675, F1=0.794, FP=13
- Threshold 0.50: Recall=0.821, Precision=0.852, F1=0.836, FP=4
  
New min_threshold=0.40 ensures better precision/recall balance.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.app import create_app
from src.services.ml_service import MLService

def main():
    """Retrain models with optimized threshold."""
    print("=" * 70)
    print("RETRAINING ML MODELS WITH OPTIMIZED THRESHOLD")
    print("=" * 70)
    print("\nChanges:")
    print("  - min_threshold: 0.30 → 0.40")
    print("  - Expected optimal threshold: ~0.50 (based on audit)")
    print("  - Expected F1 improvement: 0.79 → 0.84 (+5%)")
    print("  - Expected FP reduction: 13 → 4 (-69%)")
    print("\nStarting training...\n")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Train models
        result = MLService.train_models()
        
        print("\n" + "=" * 70)
        print("TRAINING COMPLETE")
        print("=" * 70)
        print(f"\nModel Version: {result['model_version']}")
        print(f"Threshold: {result['threshold']} (previous: 0.30)")
        print(f"Threshold Source: {result['threshold_source']}")
        
        print("\n--- Cross-Validation Metrics (3-Fold) ---")
        cv = result['cv_metrics']
        print(f"  Recall: {cv['recall']:.3f} ± {cv.get('recall_std', 0):.3f}")
        print(f"  F1-Score: {cv['f1']:.3f} ± {cv.get('f1_std', 0):.3f}")
        print(f"  Precision: {cv['precision']:.3f} ± {cv.get('precision_std', 0):.3f}")
        
        print("\n--- Test Set Metrics ---")
        test = result['test_metrics']
        print(f"  Recall: {test['recall']:.3f}")
        print(f"  F1-Score: {test['f1']:.3f}")
        print(f"  Precision: {test['precision']:.3f}")
        print(f"  AUC-ROC: {test.get('auc_roc', 'N/A')}")
        
        if 'bootstrap_ci' in test:
            print("\n--- Bootstrap Confidence Intervals (95%) ---")
            ci = test['bootstrap_ci']
            for metric, bounds in ci.items():
                if isinstance(bounds, dict):
                    lower = bounds.get('lower', 0)
                    upper = bounds.get('upper', 0)
                    width = upper - lower
                    print(f"  {metric}: [{lower:.3f}, {upper:.3f}] (width={width:.3f})")
        
        print("\n--- Feature Importance (Top 5) ---")
        if 'feature_importance' in result:
            features = sorted(
                result['feature_importance'].items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:5]
            for feat, coef in features:
                direction = "↑" if coef > 0 else "↓"
                print(f"  {feat:25s}: {coef:+.3f} {direction}")
        
        print("\n--- Validation Checks ---")
        criteria = result.get('validation', {})
        if criteria:
            for criterion, passed in criteria.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"  {criterion}: {status}")
        
        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("1. Review threshold (should be ~0.50 based on audit)")
        print("2. Compare new metrics with old:")
        print("   - Old (threshold=0.30): F1=0.77, Precision=0.62")
        print("   - Expected improvement in precision and F1")
        print("3. Update documentation if needed")
        print("4. Commit changes to version control")
        print("\nModel saved to: models/model_metadata.json")
        print("=" * 70)

if __name__ == "__main__":
    main()
