import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.models.chatbot import KnowledgeBaseItem, ChatSession, ChatMessage
from backend.app.models.complaint import Complaint, ComplaintStatus, ComplaintTier
from backend.app.models.user import User, UserRole
from backend.app.models.scholarship import Scholarship
from backend.app.services.scholarship_service import ScholarshipService

class ChatbotService:
    @staticmethod
    def process_query(
        db: Session,
        query: str,
        current_user: Optional[User] = None,
        session_uuid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Unified Institutional RAG & Dynamic Database Query Processor for NIE Mysuru.
        1. Checks for personalized live database queries (e.g. status of my complaints).
        2. Performs TF-IDF RAG retrieval against institutional knowledge base.
        3. Generates accurate, verified, institutional response with source references.
        """
        q_clean = query.strip()
        q_lower = q_clean.lower()

        # -------------------------------------------------------------
        # STEP 1: PERSONALIZED LIVE DATABASE QUERIES (Authenticated)
        # -------------------------------------------------------------
        if current_user:
            # Check for specific grievance ID in query (e.g. NIE-2026-0001)
            id_match = re.search(r"\b(NIE-\d{4}-\d{4})\b", q_clean, re.IGNORECASE)
            target_grievance_id = id_match.group(1).upper() if id_match else None

            # Case A: User asks about a specific complaint ID
            if target_grievance_id:
                comp = db.query(Complaint).filter(Complaint.grievance_id == target_grievance_id).first()
                if comp:
                    # Enforce privacy: complainant or officer can view
                    is_authorized = (
                        comp.complainant_id == current_user.id
                        or current_user.role in [UserRole.DEPT_OFFICER, UserRole.GRIEVANCE_CELL, UserRole.PRINCIPAL, UserRole.SUPER_ADMIN]
                    )
                    if is_authorized:
                        days_pending = (datetime.utcnow() - comp.submission_date).days
                        tier_labels = {"tier_1": "Tier 1 (Department Level)", "tier_2": "Tier 2 (Grievance Cell)", "tier_3": "Tier 3 (Principal / Higher Authority)"}
                        
                        resp = (
                            f"**Grievance Status for {comp.grievance_id}:**\n\n"
                            f"- **Title:** {comp.title}\n"
                            f"- **Category:** {comp.category}\n"
                            f"- **Department:** {comp.department.name}\n"
                            f"- **Status:** `{comp.status.replace('_', ' ').title()}`\n"
                            f"- **Current Authority:** {tier_labels.get(comp.current_tier, comp.current_tier)}\n"
                            f"- **Assessed Priority:** {comp.final_priority} ({comp.priority_explanation or 'Standard criteria'})\n"
                            f"- **Days Pending:** {days_pending} days\n"
                            f"- **Expected Deadline:** {comp.expected_deadline.strftime('%d-%b-%Y') if comp.expected_deadline else 'N/A'}\n"
                        )
                        if comp.is_duplicate:
                            resp += f"- **Duplicate Link:** Associated with master case {comp.master_complaint_id}\n"
                        if comp.resolution_remarks:
                            resp += f"- **Officer Remarks:** {comp.resolution_remarks}\n"
                        
                        return {
                            "response": resp,
                            "sources": [f"Live NIE Database (Record: {comp.grievance_id})"],
                            "is_live_data": True,
                            "context_type": "complaint_status"
                        }
                    else:
                        return {
                            "response": f"Access restricted: You do not have authorization to view grievance {target_grievance_id}.",
                            "sources": ["NIE Access Control"],
                            "is_live_data": True,
                            "context_type": "auth_denied"
                        }

            # Case B: General status inquiry ("my complaints", "status of my complaint")
            if any(k in q_lower for k in ["my complaint", "status of my", "my grievances", "track my"]):
                user_complaints = (
                    db.query(Complaint)
                    .filter(Complaint.complainant_id == current_user.id)
                    .order_by(Complaint.submission_date.desc())
                    .limit(5)
                    .all()
                )
                if not user_complaints:
                    return {
                        "response": "You currently have no registered grievances in NIEresolve. You can raise a new complaint from your dashboard anytime.",
                        "sources": ["Live NIE Database"],
                        "is_live_data": True,
                        "context_type": "complaint_list"
                    }

                resp_lines = [f"**Your Recent Grievances ({len(user_complaints)}):**\n"]
                for c in user_complaints:
                    days = (datetime.utcnow() - c.submission_date).days
                    tier_str = c.current_tier.replace('_', ' ').upper()
                    resp_lines.append(
                        f"1. **{c.grievance_id}**: *{c.title}*\n"
                        f"   - **Status:** `{c.status.replace('_', ' ').title()}` | **Priority:** {c.final_priority} | **Level:** {tier_str}\n"
                        f"   - **Days Pending:** {days} days | **Department:** {c.department.code}\n"
                    )
                resp_lines.append("\nTip: Ask me *'What is the status of NIE-2026-XXXX?'* for in-depth details.")
                return {
                    "response": "\n".join(resp_lines),
                    "sources": ["Live NIE Database"],
                    "is_live_data": True,
                    "context_type": "complaint_list"
                }

            # Case C: Scholarship recommendations query
            if any(k in q_lower for k in ["my scholarship", "eligible scholarship", "scholarships for me"]) and current_user.student_profile:
                recs = ScholarshipService.get_recommendations_for_student(db, current_user.student_profile.id)
                eligible = [r for r in recs if r["status"] == "Eligible"]
                pot_eligible = [r for r in recs if r["status"] == "Potentially Eligible"]

                resp = f"**Scholarship Recommendations for USN {current_user.student_profile.usn}:**\n\n"
                if eligible:
                    resp += f"✅ **Fully Eligible ({len(eligible)}):**\n"
                    for r in eligible[:3]:
                        sch = r["scholarship"]
                        resp += f"- **{sch.name}** ({sch.provider}): {sch.financial_benefits}. Deadline: {sch.application_deadline.strftime('%d-%b-%Y')}\n"
                if pot_eligible:
                    resp += f"\n⚠️ **Potentially Eligible ({len(pot_eligible)}):**\n"
                    for r in pot_eligible[:2]:
                        sch = r["scholarship"]
                        missing = "; ".join(r["missing_criteria"])
                        resp += f"- **{sch.name}**: Needs attention: {missing}\n"

                resp += "\nVisit the **Scholarships** tab in your student portal to review complete requirements and direct application links."
                return {
                    "response": resp,
                    "sources": ["NIE Scholarship Engine"],
                    "is_live_data": True,
                    "context_type": "scholarship_recommendation"
                }

        # -------------------------------------------------------------
        # STEP 2: RAG OVER INSTITUTIONAL KNOWLEDGE BASE
        # -------------------------------------------------------------
        kb_items = db.query(KnowledgeBaseItem).filter(KnowledgeBaseItem.is_active == True).all()
        if not kb_items:
            return {
                "response": "The NIE Mysuru institutional knowledge base is currently being updated. Please check back shortly or contact the Grievance Cell at grievancecell@nie.ac.in.",
                "sources": [],
                "is_live_data": False,
                "context_type": "empty_kb"
            }

        # Build corpus with title, keywords, and content
        corpus = [f"{item.title} {item.keywords or ''} {item.content}" for item in kb_items]
        all_texts = [q_clean] + corpus

        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
            tfidf_mat = vectorizer.fit_transform(all_texts)
            sims = cosine_similarity(tfidf_mat[0:1], tfidf_mat[1:]).flatten()
            
            top_indices = sims.argsort()[::-1]
            best_idx = top_indices[0]
            best_score = float(sims[best_idx])
        except Exception as e:
            print(f"[ChatbotService] TFIDF error: {e}")
            best_score = 0.0
            best_idx = 0

        # Moderate match threshold for institutional documents
        if best_score >= 0.05:
            matched_item = kb_items[best_idx]
            response_text = f"**{matched_item.title}**\n\n{matched_item.content}"
            
            # Check if second item is also relevant
            if len(top_indices) > 1 and float(sims[top_indices[1]]) >= 0.25:
                second_item = kb_items[top_indices[1]]
                response_text += f"\n\n---\n**Related: {second_item.title}**\n{second_item.content}"

            source_ref = matched_item.source_reference or f"NIE Institutional KB ({matched_item.category.upper()})"
            return {
                "response": response_text,
                "sources": [source_ref],
                "is_live_data": False,
                "context_type": matched_item.category
            }

        # Fallback when institutional info is truly unavailable (No hallucinations!)
        return {
            "response": (
                "I could not locate specific verified information regarding your query in the current NIE Mysuru institutional handbook or records.\n\n"
                "For formal inquiries, please consult:\n"
                "- **Grievance Redressal Cell:** `grievancecell@nie.ac.in`\n"
                "- **Academic Office:** Administrative Block, NIE Mysuru\n"
                "- **Office Hours:** Monday to Friday, 9:00 AM – 5:00 PM\n\n"
                "You may also raise an official grievance under category 'Other' via your dashboard for personal assistance."
            ),
            "sources": ["NIE Mysuru Information Desk"],
            "is_live_data": False,
            "context_type": "unknown"
        }

