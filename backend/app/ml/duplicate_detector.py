from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.app.config import settings

class DuplicateDetector:
    def __init__(self, threshold: float = None):
        self.threshold = threshold or settings.DUPLICATE_SIMILARITY_THRESHOLD

    def find_potential_duplicates(
        self,
        new_title: str,
        new_description: str,
        category: str,
        department_id: int,
        existing_complaints: List[Any],
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Calculates TF-IDF cosine similarity between new complaint and existing active complaints.
        Filters candidate pool to matching department or category for high precision.
        """
        if not existing_complaints:
            return []

        eff_threshold = threshold if threshold is not None else (self.threshold or 0.35)

        # Filter candidate pool
        candidates = [
            c for c in existing_complaints
            if c.category == category or c.department_id == department_id
        ]
        if not candidates:
            # Fallback to all active complaints if pool is small
            candidates = existing_complaints

        new_doc = f"{new_title} {new_description}"
        candidate_docs = [f"{c.title} {c.description}" for c in candidates]

        all_docs = [new_doc] + candidate_docs

        try:
            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words="english",
                sublinear_tf=True
            )
            tfidf_matrix = vectorizer.fit_transform(all_docs)
            similarity_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        except Exception as e:
            print(f"[DuplicateDetector] Error computing similarity: {e}")
            return []

        matches = []
        for idx, score in enumerate(similarity_scores):
            score_float = float(score)
            if score_float >= eff_threshold:
                cand = candidates[idx]
                matches.append({
                    "complaint_id": cand.id,
                    "grievance_id": cand.grievance_id,
                    "title": cand.title,
                    "category": cand.category,
                    "department_id": cand.department_id,
                    "similarity_score": round(score_float, 3),
                    "status": cand.status,
                    "current_tier": cand.current_tier,
                    "submission_date": cand.submission_date,
                    "affected_students_count": cand.affected_students_count
                })

        # Sort highest similarity first
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        return matches

duplicate_detector = DuplicateDetector()

