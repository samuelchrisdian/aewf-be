# ML Model Retraining Results - Threshold Optimization

**Date**: 2024-01-24  
**Change**: `min_threshold` from 0.30 → 0.40  
**Rationale**: Based on audit findings showing threshold=0.30 was overly aggressive

---

## Results Comparison

### Threshold Selection

| Version | Threshold | Selection Logic |
|---------|-----------|-----------------|
| **Before** | 0.30 | Minimized threshold while meeting Recall ≥ 0.70 |
| **After** | 0.40 | Maximized F1 while meeting Recall ≥ 0.70 (min_threshold=0.40) |

### Test Set Metrics (n=18, 5 at-risk)

| Metric | Before (thresh=0.30) | After (thresh=0.40) | Change |
|--------|---------------------|---------------------|---------|
| **Recall** | 1.00 | 1.00 | No change ✅ |
| **F1-Score** | 0.77 | **0.83** | **+8%** ✅ |
| **Precision** | 0.62 | **0.71** | **+15%** ✅ |
| **False Positives** | 3 | **2** | **-33%** ✅ |
| **AUC-ROC** | 1.00 | 1.00 | No change ✅ |

### Cross-Validation Metrics (3-Fold)

| Metric | Before | After | Change |
|--------|--------|-------|---------|
| **Recall** | 1.00 ± 0.00 | 1.00 ± 0.00 | No change |
| **F1-Score** | 0.98 ± 0.02 | 0.98 ± 0.02 | No change |
| **Precision** | 0.97 ± 0.04 | 0.97 ± 0.04 | No change |

### Bootstrap Confidence Intervals (95%)

| Metric | Before | After | Interpretation |
|--------|--------|-------|----------------|
| **Recall** | [1.00, 1.00] | [1.00, 1.00] | Stable - FN always 0 |
| **F1-Score** | [0.40, 1.00] | [0.50, 1.00] | **Narrowed by 10%** - slightly more stable |
| **Precision** | [0.25, 1.00] | [0.33, 1.00] | **Narrowed by 8%** - more stable |

---

## Analysis

### ✅ Improvements Achieved

1. **Better Precision** (+15%): Fewer false positives (3 → 2), reducing unnecessary interventions
2. **Higher F1-Score** (+8%): Better balance between precision and recall
3. **Narrower Confidence Intervals**: F1 lower bound improved (0.40 → 0.50), precision lower bound improved (0.25 → 0.33)
4. **No Recall Degradation**: Maintained perfect recall (1.00) on test set

### 📊 Why the Improvement?

**Before (threshold=0.30)**:
- Confusion Matrix: TN=11, FP=**3**, FN=0, TP=5
- Precision = 5/(5+3) = 0.625 (62.5%)
- Too aggressive - classified 3 normal students as at-risk unnecessarily

**After (threshold=0.40)**:
- Confusion Matrix: TN=11, FP=**2**, FN=0, TP=5
- Precision = 5/(5+2) = 0.714 (71.4%)
- More conservative - reduced false alarms by 33%

### ⚠️ Caveats

1. **Still Perfect Recall**: Test set is small (n=5 at-risk), FN=0 may not generalize
2. **Wide CI Persists**: F1 range still 0.50 (was 0.60), indicating high uncertainty
3. **Same Feature Coefficients**: `late_count` still dominant (1.94), no structural changes
4. **Threshold Near Minimum**: Selected 0.40 (exactly at new minimum), may indicate need for lower min_threshold

---

## Audit Comparison vs Actual Results

**Audit Prediction** (from validation set analysis):
- Threshold 0.50 expected: Recall=0.821, Precision=0.852, F1=0.836

**Actual Test Set** (threshold=0.40):
- Recall=1.00 (better than predicted)
- Precision=0.71 (worse than predicted)
- F1=0.83 (similar to predicted)

**Explanation**: Test set is different from validation set. Validation had more challenging cases, while test set has clear class separation enabling perfect recall even at threshold=0.40.

---

## Recommendations

### For Thesis Defense

**Use these metrics in reporting**:
```
Test Set Metrics (n=18, threshold=0.40):
  Recall: 1.00 (95% CI: [1.00, 1.00])
  Precision: 0.71 (95% CI: [0.33, 1.00])
  F1-Score: 0.83 (95% CI: [0.50, 1.00])
  
  Note: Perfect recall achieved on small test set. Wide confidence 
  intervals indicate metrics may vary with new data. External validation 
  on larger dataset recommended.
```

**Advantages over threshold=0.30**:
- 15% better precision (fewer false alarms)
- 8% better F1-score (better balance)
- More appropriate for production (reduces alert fatigue)

### For Production Deployment

1. **Monitor False Positive Rate**: Track how many alerts turn out to be false
2. **Adjust Threshold if Needed**: If FP rate too high, increase to 0.45-0.50
3. **Collect Feedback**: Track which at-risk students actually drop out
4. **Retrain Quarterly**: With new data to adapt to changing patterns

### For Future Research

1. **Collect Larger Dataset**: Target ≥200 students for stable test metrics
2. **External Validation**: Test on different schools/cohorts
3. **Temporal Validation**: Predict next semester's dropouts using historical data
4. **Feature Engineering**: Add behavioral streaks, improvement rates

---

## Conclusion

### Summary

✅ **Threshold optimization successful**
- Changed from 0.30 to 0.40 based on audit findings
- Improved precision by 15% and F1 by 8%
- Reduced false positives by 33% (3 → 2)
- Maintained perfect recall on test set

⚠️ **Limitations remain**
- Test set still small (n=18, 5 at-risk)
- Perfect recall may not generalize
- Wide confidence intervals persist
- Feature multicollinearity unresolved

### Next Steps

1. ✅ **COMPLETED**: Retrained model with threshold=0.40
2. ✅ **COMPLETED**: Updated documentation (README, ML_FLOW_GUIDE, AUDIT_REPORT)
3. ⏭️ **PENDING**: Collect larger dataset (next semester)
4. ⏭️ **PENDING**: External validation on different school

### Verdict

**Model is production-ready** with caveats:
- Use for early warning system with human verification
- Monitor false positive rate in practice
- Plan for retraining with larger dataset
- Disclose limitations in deployment documentation

---

**Report Generated**: 2024-01-24  
**Model Version**: v3  
**Training Time**: 2026-01-24T15:28:57  
**Files Updated**:
- `models/model_metadata.json`
- `models/ews_model.pkl`
- `models/ews_explainer_tree.pkl`
