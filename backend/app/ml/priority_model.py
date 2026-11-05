import os
import re
import joblib
import numpy as np
from typing import Dict, Any, Tuple, List
from backend.app.config import settings

# Safety critical keywords that trigger mandatory urgent override
SAFETY_KEYWORDS = {
    "live wire", "high voltage", "electrocution", "fire", "gas leak", "lpg leak",
    "structural collapse", "ceiling fall", "ragging", "assault", "harassment",
    "blackmail", "extortion", "poison", "contamination", "jaundice", "epidemic",
    "elevator fall", "trapped", "brake failure", "hornet", "explosion", "toxic",
    "acid leak", "molestation", "threat", "violence"
}

# High impact keywords
HIGH_IMPACT_KEYWORDS = {
    "fiber cut", "placement", "hall ticket withheld", "exam today", "server down",
    "attendance 0%", "sewage overflow", "power outage", "overheating", "spoilage",
    "spoiled food", "worms", "tire burst", "leakage soaking"
}

class PriorityPredictor:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(settings.MODEL_STORAGE_PATH) and os.path.exists(settings.VECTORIZER_STORAGE_PATH):
            try:
                self.model = joblib.load(settings.MODEL_STORAGE_PATH)
                self.vectorizer = joblib.load(settings.VECTORIZER_STORAGE_PATH)
            except Exception as e:
                print(f"[PriorityPredictor] Error loading model: {e}")
                self.model = None
                self.vectorizer = None

    def predict(self, category: str, title: str, description: str) -> Dict[str, Any]:
        """
        Analyzes grievance text and category.
        Returns:
            - predicted_priority: str ("Critical", "High", "Medium", "Low")
            - final_priority: str (accounts for safety override)
            - confidence: float (0.0 - 1.0)
            - is_safety_critical: bool
            - explanation: str
            - top_factors: List[str]
        """
        text_lower = f"{category} {title} {description}".lower()
        
        # 1. Check for immediate safety critical terms using word boundaries
        matched_safety = [
            kw for kw in SAFETY_KEYWORDS 
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
        ]
        is_safety_critical = len(matched_safety) > 0 or category in ["Campus Safety", "Harassment and Misconduct"]

        # 2. Check for high impact terms using word boundaries
        matched_high = [
            kw for kw in HIGH_IMPACT_KEYWORDS 
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
        ]

        # 3. Model inference
        ml_priority = "Medium"
        confidence = 0.65
        top_factors = []

        if self.model is not None and self.vectorizer is not None:
            try:
                combined_text = f"{category} {title} {description}"
                vec = self.vectorizer.transform([combined_text])
                probs = self.model.predict_proba(vec)[0]
                classes = self.model.classes_
                pred_idx = np.argmax(probs)
                ml_priority = classes[pred_idx]
                confidence = float(probs[pred_idx])

                # Extract top contributing n-grams from vectorizer
                feature_names = np.array(self.vectorizer.get_feature_names_out())
                feature_indices = vec.indices
                if len(feature_indices) > 0:
                    coefs = self.model.coef_[pred_idx]
                    top_feat_indices = sorted(feature_indices, key=lambda idx: coefs[idx], reverse=True)[:5]
                    top_factors = [str(feature_names[i]) for i in top_feat_indices if coefs[i] > 0]
            except Exception as e:
                print(f"[PriorityPredictor] Inference warning: {e}")
                ml_priority = "Medium"
                confidence = 0.5

        # 4. Apply Safety & Urgency Override rules
        final_priority = ml_priority
        override_reason = None

        if is_safety_critical:
            final_priority = "Critical"
            override_reason = f"Safety-Critical Override: detected high-risk factors ({', '.join(matched_safety or [category])})"
            if "Critical" not in top_factors:
                top_factors.insert(0, f"Safety hazard terms: {', '.join(matched_safety[:3])}")
        elif len(matched_high) > 0 and final_priority in ["Low", "Medium"]:
            final_priority = "High"
            override_reason = f"Institutional Impact Override: high-stakes academic/placement/health factors ({', '.join(matched_high)})"

        # Construct explanation
        explanation_parts = []
        if override_reason:
            explanation_parts.append(override_reason)
        explanation_parts.append(f"ML Classifier score: {confidence * 100:.1f}% for class '{ml_priority}'")
        if top_factors:
            explanation_parts.append(f"Key contributing keywords: {', '.join(top_factors[:4])}")

        return {
            "predicted_priority": ml_priority,
            "final_priority": final_priority,
            "confidence": round(confidence, 3),
            "is_safety_critical": is_safety_critical,
            "explanation": " | ".join(explanation_parts),
            "top_factors": top_factors,
            "override_applied": final_priority != ml_priority
        }

priority_predictor = PriorityPredictor()

