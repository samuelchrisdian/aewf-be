"""
Model Interpretation Module for Early Warning System (EWS)

This module provides natural language explanations for ML predictions
by combining Logistic Regression coefficients and Decision Tree rules.

The explanations are generated in Indonesian to be suitable for teachers.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# =============================================================================
# FEATURE NAME MAPPING (English → Indonesian)
# =============================================================================

FEATURE_NAME_MAP = {
    "absent_count": "Total Ketidakhadiran",
    "absent_ratio": "Rasio Absensi",
    "late_count": "Total Keterlambatan",
    "late_ratio": "Rasio Keterlambatan",
    "present_count": "Total Kehadiran",
    "permission_count": "Total Izin",
    "sick_count": "Total Sakit",
    "total_days": "Total Hari Sekolah",
    "attendance_ratio": "Rasio Kehadiran",
    "trend_score": "Tren Kehadiran (Mingguan)",
    "is_rule_triggered": "Batas Aturan Terlampaui",
}


# =============================================================================
# MODEL INTERPRETER CLASS
# =============================================================================


class ModelInterpreter:
    """
    Interprets ML predictions and generates human-readable explanations.

    Combines:
    1. Logistic Regression coefficient weights to identify top contributing factors
    2. Decision Tree decision path to extract IF-THEN rules

    Outputs professional Indonesian text suitable for teachers.
    """

    def __init__(
        self,
        lr_model: Any,
        dt_model: Optional[Any],
        feature_names: List[str],
    ):
        """
        Initialize the interpreter with loaded models.

        Args:
            lr_model: Trained LogisticRegression model
            dt_model: Trained DecisionTreeClassifier model (optional)
            feature_names: List of feature column names in order
        """
        self.lr_model = lr_model
        self.dt_model = dt_model
        self.feature_names = feature_names

        # Extract LR coefficients
        if hasattr(lr_model, "coef_"):
            self.coefficients = lr_model.coef_[0]
        else:
            self.coefficients = None
            logger.warning("LR model has no coefficients, LR explanation disabled")

    def _get_indonesian_name(self, feature_name: str) -> str:
        """Get Indonesian name for a feature, fallback to original if not found."""
        return FEATURE_NAME_MAP.get(feature_name, feature_name)

    def _analyze_lr_contributions(
        self, student_data: Dict[str, float], top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Calculate weighted contributions (feature_value × coefficient)
        and return top N factors pushing risk UP.

        Args:
            student_data: Dict of feature_name -> feature_value
            top_n: Number of top contributing factors to return

        Returns:
            List of dicts with feature info, sorted by contribution (descending)
        """
        if self.coefficients is None:
            return []

        contributions = []

        for i, feature_name in enumerate(self.feature_names):
            value = student_data.get(feature_name, 0)
            coef = self.coefficients[i]
            contribution = value * coef  # Positive = increases risk probability

            contributions.append(
                {
                    "feature": feature_name,
                    "feature_indo": self._get_indonesian_name(feature_name),
                    "value": value,
                    "coefficient": coef,
                    "contribution": contribution,
                }
            )

        # Sort by contribution (descending) to get factors pushing risk UP
        contributions.sort(key=lambda x: x["contribution"], reverse=True)

        # Return only positive contributors (pushing risk up)
        positive_contributors = [c for c in contributions if c["contribution"] > 0]

        return positive_contributors[:top_n]

    def _extract_dt_rules(self, student_data: Dict[str, float]) -> List[str]:
        """
        Extract the decision path rules used for this student.

        Uses the Decision Tree's tree_ structure to trace the path
        and extract the threshold conditions.

        Args:
            student_data: Dict of feature_name -> feature_value

        Returns:
            List of rule strings in Indonesian (e.g., "Rasio Absensi > 0.12")
        """
        if self.dt_model is None:
            return []

        try:
            # Prepare feature array in correct order
            feature_values = np.array(
                [[student_data.get(f, 0) for f in self.feature_names]]
            )

            # Get decision path
            node_indicator = self.dt_model.decision_path(feature_values)

            # Get the node indices for this sample
            node_indices = node_indicator.indices[
                node_indicator.indptr[0] : node_indicator.indptr[1]
            ]

            tree = self.dt_model.tree_
            rules = []

            for node_id in node_indices:
                # Skip leaf nodes (no split)
                if tree.feature[node_id] < 0:
                    continue

                feature_idx = tree.feature[node_id]
                threshold = tree.threshold[node_id]
                feature_name = self.feature_names[feature_idx]
                feature_value = student_data.get(feature_name, 0)
                feature_indo = self._get_indonesian_name(feature_name)

                # Determine which direction (left = <=, right = >)
                if feature_value <= threshold:
                    operator = "≤"
                else:
                    operator = ">"

                # Format threshold nicely
                if threshold < 1 and threshold > 0:
                    threshold_str = f"{threshold:.2f}"
                else:
                    threshold_str = f"{threshold:.0f}"

                rule_str = f"{feature_indo} {operator} {threshold_str}"
                rules.append(rule_str)

            return rules

        except Exception as e:
            logger.error(f"Error extracting DT rules: {e}")
            return []

    def _format_factor_description(self, factor: Dict[str, Any]) -> str:
        """
        Format a contributing factor as a readable Indonesian sentence.

        Args:
            factor: Dict with feature info from _analyze_lr_contributions

        Returns:
            Indonesian sentence describing the factor
        """
        feature_name = factor["feature"]
        feature_indo = factor["feature_indo"]
        value = factor["value"]

        # Special formatting based on feature type
        if feature_name == "absent_count":
            return f"{feature_indo} tergolong tinggi ({int(value)} hari)."
        elif feature_name == "late_count":
            return f"{feature_indo} tergolong tinggi ({int(value)} kali)."
        elif feature_name == "trend_score":
            if value < 0:
                return f"{feature_indo} memburuk dalam 7 hari terakhir."
            else:
                return f"{feature_indo} menunjukkan perbaikan."
        elif feature_name == "absent_ratio":
            return f"{feature_indo} mencapai {value:.1%}."
        elif feature_name == "late_ratio":
            return f"{feature_indo} mencapai {value:.1%}."
        elif feature_name == "attendance_ratio":
            return f"{feature_indo} hanya {value:.1%}."
        elif feature_name == "is_rule_triggered":
            if value > 0:
                return "Batas absensi kritis telah terlampaui."
            return ""
        else:
            return f"{feature_indo}: {value:.2f}."

    def generate_natural_language_explanation(
        self, student_data: Dict[str, float]
    ) -> str:
        """
        Generate a complete natural language explanation in Indonesian.

        Combines:
        1. Top contributing factors from LR coefficients
        2. Decision rules from the DT path

        Args:
            student_data: Dict of feature_name -> feature_value

        Returns:
            Formatted Indonesian text suitable for teachers
        """
        sections = []

        # =================================================================
        # SECTION 1: Top Contributing Factors (from LR)
        # =================================================================
        top_factors = self._analyze_lr_contributions(student_data, top_n=3)

        if top_factors:
            factor_lines = []
            for factor in top_factors:
                desc = self._format_factor_description(factor)
                if desc:  # Skip empty descriptions
                    factor_lines.append(f"- {desc}")

            if factor_lines:
                factors_text = "Faktor Utama Risiko (Berdasarkan Bobot):\n" + "\n".join(
                    factor_lines
                )
                sections.append(factors_text)

        # =================================================================
        # SECTION 2: Detection Logic (from DT)
        # =================================================================
        dt_rules = self._extract_dt_rules(student_data)

        if dt_rules:
            rules_lines = [f"- {rule}" for rule in dt_rules[:4]]  # Max 4 rules
            rules_text = "Logika Deteksi (Aturan):\n" + "\n".join(rules_lines)
            sections.append(rules_text)

        # =================================================================
        # COMBINE SECTIONS
        # =================================================================
        if sections:
            return "\n\n".join(sections)
        else:
            return "Tidak ada penjelasan tersedia untuk prediksi ini."
