import re
from typing import Dict, List, Any, Tuple
from backend.app.models.complaint import Complaint, ComplaintStatus, ComplaintPriority

# Smart classification rules based on category, title, and description keywords
ISSUE_PATTERNS = [
    # Water Cooler & Drinking Water
    (
        r"\b(water\s*cooler|drinking\s*water|water\s*dispenser|cooler\s*tap|cold\s*water|water\s*filter|aquaguard)\b",
        "Water Cooler & Drinking Water Issues",
        "🚰",
    ),
    # Washroom & Sanitation
    (
        r"\b(washroom|restroom|toilet|urinal|commode|flush|washbasin|sanitation|rest\s*room)\b",
        "Washroom & Sanitation Issues",
        "🚽",
    ),
    # Electrical & Lighting
    (
        r"\b(fan\s*not\s*working|ceiling\s*fan|tube\s*light|bulb|lighting|electric\s*switch|socket|power\s*cut|power\s*tripping|short\s*circuit|wiring)\b",
        "Electrical & Power Supply Issues",
        "⚡",
    ),
    # Classroom Infrastructure & Furniture
    (
        r"\b(bench|benches|desk|desks|chair|chairs|podium|blackboard|whiteboard|marker|projector|classroom\s*furniture|screen|audio\s*system)\b",
        "Classroom Infrastructure & Furniture",
        "🪑",
    ),
    # Computer Lab & Workstations
    (
        r"\b(computer\s*lab|workstation|workstations|desktop|pc\s*crashing|pc\s*shutting|cpu|monitor|lan\s*cable|system\s*tripping)\b",
        "Computer Lab & Workstations",
        "💻",
    ),
    # Laboratory Apparatus & Equipment
    (
        r"\b(laboratory|lathe|oscilloscope|multimeter|spectrophotometer|apparatus|pipette|burette|lab\s*machine|calibration)\b",
        "Laboratory Equipment & Apparatus",
        "🔬",
    ),
    # Hostel Water & Plumbing
    (
        r"\b(hostel\s*water|water\s*pressure|geyser|solar\s*water|hostel\s*tap|hostel\s*pipe|hostel\s*tank)\b",
        "Hostel Water & Plumbing Issues",
        "🚿",
    ),
    # Hostel Mess & Dining
    (
        r"\b(mess\s*food|hostel\s*mess|dining\s*hall|mess\s*hygiene|mess\s*caterer|hostel\s*food)\b",
        "Hostel Mess & Dining Issues",
        "🍽️",
    ),
    # Hostel Room Maintenance
    (
        r"\b(hostel\s*room|hostel\s*bed|hostel\s*cot|hostel\s*fan|hostel\s*window|warden|hostel\s*lock)\b",
        "Hostel Room Maintenance",
        "🛏️",
    ),
    # Campus Safety Hazards
    (
        r"\b(live\s*wire|high\s*voltage|electrocution|fire\s*hazard|hazardous|chemical\s*spill|danger|emergency)\b",
        "Critical Safety Hazards & Danger",
        "⚠️",
    ),
    # Campus Security & Access
    (
        r"\b(security\s*guard|gate\s*pass|cctv|surveillance|id\s*card\s*scanner|campus\s*entry|night\s*patrol)\b",
        "Campus Security & Access Control",
        "🛡️",
    ),
    # Placement Portal & Registration
    (
        r"\b(placement\s*portal|company\s*registration|tier\s*1\s*company|resume\s*upload|t&p\s*cell|placement\s*drive|aptitude\s*test)\b",
        "Placement Portal & Registration",
        "💼",
    ),
    # Campus Wi-Fi & Internet
    (
        r"\b(wifi|wi-fi|internet|campus\s*network|broadband|slow\s*internet|router|nie\s*connect)\b",
        "Campus Wi-Fi & Network Issues",
        "📶",
    ),
    # Campus Transportation
    (
        r"\b(bus|bus\s*route|bus\s*pass|transport|college\s*bus|driver|bus\s*stop)\b",
        "Campus Bus & Transportation",
        "🚌",
    ),
    # Examination & Hall Tickets
    (
        r"\b(hall\s*ticket|revaluation|grade\s*card|exam\s*schedule|marks\s*card|supplementary|semester\s*end\s*exam)\b",
        "Examination & Grading Services",
        "📝",
    ),
    # Library & Digital Resources
    (
        r"\b(library\s*book|digital\s*library|reference\s*section|journal|reading\s*room|library\s*card)\b",
        "Library Books & Digital Access",
        "📖",
    ),
    # Scholarships & Financial Aid
    (
        r"\b(ssp|nsp|scholarship\s*portal|fee\s*concession|income\s*certificate|fee\s*refund)\b",
        "Scholarship & Financial Aid Inquiries",
        "🎓",
    ),
]

def classify_complaint_issue(category: str, title: str, description: str) -> Tuple[str, str]:
    """
    Classifies a complaint into a normalized, human-friendly smart issue group
    without modifying database records.
    Returns (group_name, icon).
    """
    search_text = f"{title} {description}".lower()

    for pattern, group_name, icon in ISSUE_PATTERNS:
        if re.search(pattern, search_text, re.IGNORECASE):
            return group_name, icon

    # Category-based default fallbacks
    cat_fallbacks = {
        "Infrastructure and Maintenance": ("General Infrastructure & Facilities", "🔧"),
        "Infrastructure and Facilities": ("General Infrastructure & Facilities", "🔧"),
        "Hostel and Accommodation": ("General Hostel Maintenance", "🛏️"),
        "Hostel Issues": ("General Hostel Maintenance", "🛏️"),
        "Laboratory Equipment": ("General Laboratory Facilities", "🔬"),
        "Laboratory": ("General Laboratory Facilities", "🔬"),
        "Campus Safety": ("Campus Safety & Maintenance", "🛡️"),
        "Placement and Career Services": ("Career Services & Placement", "💼"),
        "Transportation": ("Transportation & Transit Services", "🚌"),
        "Academic and Curriculum": ("Academic & Curriculum Concerns", "📚"),
        "Academic Issues": ("Academic & Curriculum Concerns", "📚"),
        "Examination and Results": ("Examination & Results Inquiries", "📝"),
        "Faculty-related Issues": ("Faculty & Academic Mentorship", "👨‍🏫"),
        "Faculty-related Grievances": ("Faculty & Academic Mentorship", "👨‍🏫"),
        "Library": ("Library Services & Facilities", "📖"),
        "Scholarship and Financial Aid": ("Scholarship & Financial Aid", "🎓"),
        "Scholarships and Financial Aid": ("Scholarship & Financial Aid", "🎓"),
        "Fees and Administration": ("Administrative & Fee Inquiries", "🏛️"),
        "IT and Network Issues": ("IT, Systems & Connectivity", "💻"),
        "Other": ("Miscellaneous College Matters", "📌"),
    }

    return cat_fallbacks.get(category, (f"{category} Inquiries", "📌"))


def group_complaints_by_issue(complaints: List[Complaint]) -> List[Dict[str, Any]]:
    """
    Non-destructively organizes a list of Complaint models into categorized,
    expandable smart groups.
    Preserves every individual complaint, its unique grievance ID, dates, and full metadata.
    """
    groups_dict: Dict[str, Dict[str, Any]] = {}

    for comp in complaints:
        group_name, icon = classify_complaint_issue(comp.category, comp.title, comp.description or "")

        group_key = f"{comp.category}::{group_name}"

        if group_key not in groups_dict:
            groups_dict[group_key] = {
                "group_id": group_key.lower().replace(" ", "-").replace("::", "_").replace("&", "and"),
                "group_name": group_name,
                "category": comp.category,
                "icon": icon,
                "total_count": 0,
                "pending_count": 0,
                "resolved_count": 0,
                "complaints": [],
            }

        group = groups_dict[group_key]
        group["total_count"] += 1

        is_resolved = comp.status in [
            ComplaintStatus.RESOLVED,
            ComplaintStatus.CLOSED,
            ComplaintStatus.CONFIRMED_RESOLVED,
            ComplaintStatus.AUTO_CONFIRMED_RESOLVED,
        ]

        if is_resolved:
            group["resolved_count"] += 1
        else:
            group["pending_count"] += 1

        # Attach original complaint
        group["complaints"].append(comp)

    # Sort groups: groups with active/pending complaints first, then by total count descending
    sorted_groups = sorted(
        groups_dict.values(),
        key=lambda g: (g["pending_count"] == 0, -g["pending_count"], -g["total_count"])
    )

    return sorted_groups

