from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.scholarship import Scholarship, ScholarshipRecommendation
from backend.app.models.user import StudentProfile

class ScholarshipService:
    @staticmethod
    def evaluate_scholarship_eligibility(
        student: StudentProfile,
        scholarship: Scholarship,
    ) -> Dict[str, Any]:
        """
        Transparent rule-based eligibility evaluator.
        Returns status ('Eligible', 'Potentially Eligible', 'Not Eligible'),
        match_score (0-100%), match_reasons, and missing_criteria.
        """
        match_reasons = []
        missing_criteria = []
        criteria_total = 0
        criteria_passed = 0

        # 1. Academic Performance (CGPA)
        criteria_total += 1
        if scholarship.min_cgpa == 0.0 or student.cgpa >= scholarship.min_cgpa:
            criteria_passed += 1
            if scholarship.min_cgpa > 0:
                match_reasons.append(f"CGPA ({student.cgpa}) meets minimum academic requirement of {scholarship.min_cgpa}")
            else:
                match_reasons.append("No minimum CGPA requirement")
        else:
            missing_criteria.append(f"Requires CGPA ≥ {scholarship.min_cgpa} (Current: {student.cgpa})")

        # 2. Family Income Limit
        criteria_total += 1
        if scholarship.max_family_income == 0.0 or student.annual_income <= scholarship.max_family_income:
            criteria_passed += 1
            match_reasons.append(f"Annual income (₹{student.annual_income:,.0f}) is within the ceiling of ₹{scholarship.max_family_income:,.0f}")
        else:
            missing_criteria.append(f"Income exceeds ₹{scholarship.max_family_income:,.0f} limit (Current: ₹{student.annual_income:,.0f})")

        # 3. Category / Reservation
        criteria_total += 1
        cat_lower = scholarship.eligible_categories.lower()
        if "all" in cat_lower or student.category.lower() in cat_lower:
            criteria_passed += 1
            match_reasons.append(f"Student category '{student.category}' matches eligible categories ({scholarship.eligible_categories})")
        else:
            missing_criteria.append(f"Eligible categories: {scholarship.eligible_categories} (Student category: {student.category})")

        # 4. State of Domicile
        criteria_total += 1
        domicile_lower = scholarship.eligible_domiciles.lower()
        if "all" in domicile_lower or student.state_of_domicile.lower() in domicile_lower:
            criteria_passed += 1
            match_reasons.append(f"Domicile '{student.state_of_domicile}' is eligible")
        else:
            missing_criteria.append(f"Restricted to {scholarship.eligible_domiciles} residents (Student domicile: {student.state_of_domicile})")

        # 5. Disability Requirement
        if scholarship.disability_required:
            criteria_total += 1
            if student.disability_status:
                criteria_passed += 1
                match_reasons.append("Disability criterion satisfied")
            else:
                missing_criteria.append("Specifically reserved for students with benchmark disabilities")

        # Calculate score and final status
        match_score = round((criteria_passed / criteria_total) * 100.0, 1) if criteria_total > 0 else 0.0

        if len(missing_criteria) == 0:
            status = "Eligible"
        elif len(missing_criteria) == 1 and match_score >= 70.0:
            status = "Potentially Eligible"
        else:
            status = "Not Eligible"

        # Days until deadline
        now = datetime.utcnow()
        days_left = max(0, (scholarship.application_deadline - now).days)

        return {
            "status": status,
            "match_score": match_score,
            "match_reasons": match_reasons,
            "missing_criteria": missing_criteria,
            "deadline_days_left": days_left,
        }

    @staticmethod
    def get_recommendations_for_student(db: Session, student_id: int) -> List[Dict[str, Any]]:
        """Evaluates and ranks all active scholarships for a given student."""
        student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
        if not student:
            return []

        scholarships = db.query(Scholarship).filter(Scholarship.is_active == True).all()
        results = []

        for sch in scholarships:
            eval_res = ScholarshipService.evaluate_scholarship_eligibility(student, sch)
            results.append({
                "scholarship": sch,
                "status": eval_res["status"],
                "match_score": eval_res["match_score"],
                "match_reasons": eval_res["match_reasons"],
                "missing_criteria": eval_res["missing_criteria"],
                "deadline_days_left": eval_res["deadline_days_left"],
            })

        # Rank: Eligible first, then Potentially Eligible, sorted by match_score descending
        status_priority = {"Eligible": 3, "Potentially Eligible": 2, "Not Eligible": 1}
        results.sort(key=lambda x: (status_priority.get(x["status"], 0), x["match_score"]), reverse=True)
        return results

