import streamlit as st
import requests
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import numpy as np

# API Base URL
API_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(
    page_title="Judicial AI Platform",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Judiciary Theme & CSS
st.markdown("""
<style>
    /* Global Styles */
    .main { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { color: #0f172a; font-weight: 600; }
    
    /* Modern Cards */
    .metric-card {
        background: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    .metric-card h3 { margin: 0; font-size: 28px; color: #1e3a8a; }
    .metric-card p { margin: 0; color: #64748b; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Badges */
    .status-badge {
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
        margin-right: 5px;
        margin-bottom: 5px;
    }
    .badge-critical { background-color: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
    .badge-high { background-color: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
    .badge-medium { background-color: #fefce8; color: #a16207; border: 1px solid #fef08a; }
    .badge-low { background-color: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
    .badge-info { background-color: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
    
    /* Typography */
    .clean-title { font-size: 24px; font-weight: 700; color: #0f172a; margin: 0 0 5px 0; }
    .clean-subtitle { font-size: 14px; color: #64748b; margin-bottom: 15px; }
    
    .section-header {
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 10px;
        margin-bottom: 20px;
        color: #1e293b;
    }
    
    /* Scrollable Text Area */
    .scrollable-text {
        max-height: 400px;
        overflow-y: auto;
        background: #f1f5f9;
        padding: 15px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 12px;
        white-space: pre-wrap;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
@st.cache_data(ttl=10)
def fetch_cases():
    try:
        res = requests.get(f"{API_URL}/cases/", timeout=10)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return []

# Sidebar Navigation
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Emblem_of_India.svg/200px-Emblem_of_India.svg.png", width=60)
    st.title("Judicial AI")
    st.markdown("<p style='color:#64748b; font-size:14px; margin-top:-15px;'>Decision Support System</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    menu = st.radio(
        "NAVIGATION",
        [
            "📋 Case Registry",
            "📤 Upload & Processing", 
            "🔥 Priority Matrix", 
            "🚨 Humanitarian Triage",
            "🧬 Similar Clustering", 
            "📚 Precedent Intelligence", 
            "📅 Schedule Optimizer", 
            "📊 Analytics Dashboard",
        ]
    )
    st.markdown("---")
    st.caption("v3.0.0 | Enterprise Edition")

# Fetch global data
all_cases = fetch_cases()

from fpdf import FPDF
import io

def generate_case_pdf(case_data, raw_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"Legal Intelligence Report: {case_data.get('title', 'Unknown')}", ln=True, align="C")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 10, f"Case ID: {case_data.get('case_number')} | Generated on {datetime.now().strftime('%Y-%m-%d')}", ln=True, align="C")
    pdf.ln(10)
    
    sections = [
        ("Case Summary", case_data.get('summary')),
        ("Legal Issue", case_data.get('legal_issue')),
        ("Relief Requested", case_data.get('relief_sought')),
        ("Final Outcome", raw_data.get('legal_outcome')),
        ("Priority Analysis", case_data.get('reasoning'))
    ]
    
    for title, content in sections:
        pdf.set_font("helvetica", "B", 12)
        pdf.set_fill_color(240, 242, 246)
        pdf.cell(0, 8, title, ln=True, fill=True)
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 6, str(content) if content else "Not Available")
        pdf.ln(4)
    
    return bytes(pdf.output())

# --- SHARED ANALYTICS LOGIC ---
def calculate_final_priority(c):
    """
    Computes priority score dynamically from actual extracted case metadata:
    - Case age / pending duration
    - Case category (Criminal vs Civil vs Constitutional)
    - Humanitarian keywords in case summary/text
    - Appeal / review status
    - Inactivity / delays
    """
    # 1. Backlog Factor (based on Case Age / Pending Duration)
    age_days = c.get('case_age_days', 0) or 0
    if not age_days and c.get('filing_date'):
        try:
            from datetime import datetime
            fd = c.get('filing_date')
            if isinstance(fd, str):
                fd = datetime.fromisoformat(fd.replace("Z", ""))
            elif isinstance(fd, datetime):
                pass
            else:
                fd = None
            if fd:
                age_days = (datetime.now() - fd).days
        except:
            pass
            
    if age_days > 365 * 15:
        b = 100.0
    elif age_days > 365 * 10:
        b = 90.0
    elif age_days > 365 * 5:
        b = 75.0
    elif age_days > 365 * 3:
        b = 60.0
    elif age_days > 365 * 1:
        b = 40.0
    else:
        b = 15.0

    # 2. Urgency Factor
    u = 30.0
    ct = str(c.get('case_type', '')).lower()
    
    if c.get('constitutional_flag') or 'constitutional' in ct or 'writ' in ct or 'pil' in ct:
        u += 25.0
    elif 'criminal' in ct or 'bail' in ct:
        u += 20.0
    elif 'appeal' in ct or 'review' in ct:
        u += 15.0
    else:
        u += 10.0
        
    title = str(c.get('title', '')).lower()
    summary = str(c.get('summary', '')).lower()
    if 'appeal' in title or 'review' in title or 'special leave' in title:
        u += 10.0
        
    inactivity = c.get('inactivity_days', 0) or 0
    if inactivity > 365:
        u += 15.0
    elif inactivity > 180:
        u += 10.0
        
    u = min(u, 100.0)

    # 3. Humanitarian Boost
    h = 0.0
    hum_keywords = ["elderly", "senior citizen", "medical", "custody", "liberty", "personal liberty", "undertrial", "bail", "juvenile", "widow", "handicap", "disable", "pension"]
    text_to_search = (title + " " + summary).lower()
    has_hum_keyword = any(kw in text_to_search for kw in hum_keywords)
    
    if c.get('humanitarian_flag') or has_hum_keyword:
        h = 20.0
        
    # Weightings: 60% Urgency, 30% Backlog, 10% Humanitarian
    score = (u * 0.6) + (b * 0.3) + (h * 0.1)
    return min(max(score, 0), 100)

def get_priority_breakdown(c):
    """
    Computes case priority components dynamically from metadata for explanation panels.
    """
    # 1. Backlog Factor (based on Case Age / Pending Duration)
    age_days = c.get('case_age_days', 0) or 0
    if not age_days and c.get('filing_date'):
        try:
            from datetime import datetime
            fd = c.get('filing_date')
            if isinstance(fd, str):
                fd = datetime.fromisoformat(fd.replace("Z", ""))
            elif isinstance(fd, datetime):
                pass
            else:
                fd = None
            if fd:
                age_days = (datetime.now() - fd).days
        except:
            pass
            
    if age_days > 365 * 15:
        b = 100.0
        age_str = f"{age_days // 365} years old"
    elif age_days > 365 * 10:
        b = 90.0
        age_str = f"{age_days // 365} years old"
    elif age_days > 365 * 5:
        b = 75.0
        age_str = f"{age_days // 365} years old"
    elif age_days > 365 * 3:
        b = 60.0
        age_str = f"{age_days // 365} years old"
    elif age_days > 365 * 1:
        b = 40.0
        age_str = "over 1 year old"
    else:
        b = 15.0
        age_str = f"{age_days} days old"

    # 2. Urgency Factor
    u = 30.0
    ct = str(c.get('case_type', '')).lower()
    ct_name = c.get('case_type') or "Unspecified"
    
    if c.get('constitutional_flag') or 'constitutional' in ct or 'writ' in ct or 'pil' in ct:
        u += 25.0
        cat_desc = "constitutional/writ status"
    elif 'criminal' in ct or 'bail' in ct:
        u += 20.0
        cat_desc = "criminal appeal"
    elif 'appeal' in ct or 'review' in ct:
        u += 15.0
        cat_desc = "appeal/review"
    else:
        u += 10.0
        cat_desc = f"{ct_name}"
        
    title = str(c.get('title', '')).lower()
    summary = str(c.get('summary', '')).lower()
    has_appeal = 'appeal' in title or 'review' in title or 'special leave' in title
    if has_appeal:
        u += 10.0
        
    inactivity = c.get('inactivity_days', 0) or 0
    if inactivity > 365:
        u += 15.0
    elif inactivity > 180:
        u += 10.0
        
    u = min(u, 100.0)

    # 3. Humanitarian Boost
    h = 0.0
    hum_keywords = ["elderly", "senior citizen", "medical", "custody", "liberty", "personal liberty", "undertrial", "bail", "juvenile", "widow", "handicap", "disable", "pension"]
    text_to_search = (title + " " + summary).lower()
    found_kws = [kw for kw in hum_keywords if kw in text_to_search]
    
    if c.get('humanitarian_flag') or found_kws:
        h = 20.0
        
    score = (u * 0.6) + (b * 0.3) + (h * 0.1)
    score = min(max(score, 0), 100)
    
    # Determine level
    if score >= 60:
        level = "High"
    elif score >= 40:
        level = "Medium"
    else:
        level = "Low"
        
    # Build explanation sentence
    reasons = []
    if age_days > 0:
        years = age_days // 365
        if years > 0:
            reasons.append(f"case is {years} years old")
        else:
            reasons.append(f"case is {age_days} days old")
    if 'criminal' in ct:
        reasons.append("criminal appeal")
    elif c.get('constitutional_flag') or 'constitutional' in ct or 'writ' in ct:
        reasons.append("constitutional/writ status")
    if found_kws:
        reasons.append(f"contains humanitarian concern keywords ('{found_kws[0]}')")
    elif c.get('humanitarian_flag'):
        reasons.append("contains humanitarian concern keywords")
        
    if not reasons:
        explanation = f"Routine {ct_name} case with standard priority."
    else:
        explanation = f"High score because " + ", ".join(reasons) + "."
        explanation = explanation[0].upper() + explanation[1:]
        
    return {
        "score": score,
        "urgency_factor": u,
        "backlog_factor": b,
        "humanitarian_boost": h,
        "level": level,
        "explanation": explanation,
        "age_days": age_days,
        "age_str": age_str
    }
def calculate_complexity_impact(c):
    """
    Dynamically computes Legal Impact / Complexity based on case features:
    - constitutional_flag (constitutional issues = high impact)
    - case_type (criminal, civil, writ etc)
    - statutes (extracted_statutes acts and sections count)
    - citations (citations count)
    Returns: (score, level) where level is "High", "Medium", or "Low"
    """
    score = 30.0 # baseline low-medium complexity
    
    # 1. Constitutional or PIL flag boost
    if c.get('constitutional_flag') or 'pil' in str(c.get('case_type', '')).lower() or 'constitution' in str(c.get('case_type', '')).lower():
        score += 40.0
        
    # 2. Case Type complexity weights
    ct = str(c.get('case_type', '')).lower()
    if 'criminal' in ct:
        score += 20.0
    elif 'writ' in ct:
        score += 15.0
    elif 'civil' in ct:
        score += 10.0
        
    # 3. Statutes count boost
    try:
        statutes_str = c.get('extracted_statutes') or '[]'
        if isinstance(statutes_str, str):
            if statutes_str.startswith('['):
                import json
                statutes_list = json.loads(statutes_str)
            else:
                statutes_list = [s for s in statutes_str.split(',') if s.strip()]
        elif isinstance(statutes_str, list):
            statutes_list = statutes_str
        else:
            statutes_list = []
        score += min(len(statutes_list) * 5, 20)
    except:
        pass
        
    # 4. Citations count boost
    try:
        citations_str = c.get('citations') or '[]'
        if isinstance(citations_str, str):
            if citations_str.startswith('['):
                import json
                citations_list = json.loads(citations_str)
            else:
                citations_list = [cit for cit in citations_str.split(',') if cit.strip()]
        elif isinstance(citations_str, list):
            citations_list = citations_str
        else:
            citations_list = []
        score += min(len(citations_list) * 5, 20)
    except:
        pass
        
    score = min(max(score, 0), 100)
    
    if score >= 70:
        return score, "High"
    elif score >= 40:
        return score, "Medium"
    else:
        return score, "Low"



# Initialize session state for watchlist
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []

# Metadata Sanitization Engine
def sanitize_metadata_field(value, field_type="general"):
    """
    Standardizes and validates metadata fields to prevent raw text contamination.
    Returns 'Not Available' if the content is malformed or too long.
    """
    if not value or str(value).lower() in ["none", "null", "", "nan", "not available", "unknown"]:
        return "Not Available"
    
    # 1. Universal String Cleaning
    v = str(value).strip()
    
    # Remove pipes and concatenated placeholders (e.g. "Case ID | Not Available")
    v = v.split('|')[0].strip()
    v = v.replace("Not Available", "").replace("not available", "").strip()
    
    # Remove dates (e.g. "on 5 December 1975" or "on 05/12/1975")
    import re
    date_patterns = [
        r'\s+on\s+\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^,]*\d{4}',
        r'\s+on\s+\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
        r'\s+on\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^,]*\d{1,2},?\s+\d{4}'
    ]
    for pattern in date_patterns:
        v = re.sub(pattern, '', v, flags=re.IGNORECASE)

    # Remove legal noise
    v = re.sub(r'Equivalent citations.*$', '', v, flags=re.IGNORECASE)
    v = re.sub(r'https?://\S+', '', v)
    v = re.sub(r'www\.\S+', '', v)
    v = re.sub(r'\.{2,}', '', v) # Remove repeated dots
    
    v = v.strip()
    if not v or v.lower() in ["none", "null", "not available"]:
        return "Not Available"
    
    # 2. Strict Field Validation
    limits = {
        "court": 120,
        "case_id": 60,
        "party": 150,
        "bench": 150,
        "title": 200,
        "general": 255
    }
    limit = limits.get(field_type, 255)
    
    if len(v) > limit:
        return "Not Available"
        
    # Case ID Specific: Reject if contains paragraph-like characters or symbols
    if field_type == "case_id":
        if any(c in v for c in [":", "{", "}", "[", "]"]) or len(v.split()) > 10:
            return "Not Available"

    # Paragraph Detection
    if v.count('\n') > 0 or v.count('.') > 2:
        return "Not Available"
        
    # Keyword triggers
    triggers = ["judgment", "appeal", "section", "article", "court observed", "held", "indiankanoon"]
    if any(t in v.lower() for t in triggers) and len(v) > 50:
        return "Not Available"
            
    return v

@st.dialog("Legal Intelligence Report", width="large")
def show_case_details(case_data):
    # --- ROBUST RAW CONTENT PARSING ---
    raw = {}
    try:
        import json, ast
        raw_str = case_data.get('raw_content', '{}')
        if isinstance(raw_str, str):
            # Try JSON first, fallback to literal_eval for single-quoted dicts
            try: raw = json.loads(raw_str)
            except: raw = ast.literal_eval(raw_str)
        else: raw = raw_str
    except: pass

    # --- SECTION 0: CASE HEADER ---
    st.markdown(f"<div style='background: #f0f2f6; padding: 1.5rem; border-radius: 10px; margin-bottom: 1rem;'>"
                f"<h2 style='margin:0; color: #1e3a8a;'>{sanitize_metadata_field(case_data.get('title'), 'title')}</h2>"
                f"<p style='margin:0; color: #64748b;'>Case ID: {sanitize_metadata_field(case_data.get('case_number'), 'case_id')} | {sanitize_metadata_field(case_data.get('court_name'), 'court')}</p></div>", 
                unsafe_allow_html=True)
    
    # Priority Metrics Header
    def safe_float(val, default=0.0):
        try:
            if isinstance(val, str):
                import re
                nums = re.findall(r'\d+\.?\d*', val)
                return float(nums[0]) if nums else default
            return float(val or default)
        except: return default

    priority_score = calculate_final_priority(case_data)
    
    h1, h2, h3 = st.columns(3)
    h1.metric("Final Priority", case_data.get('priority_level', 'Medium'))
    h2.metric("Priority Score", f"{priority_score:.0f}/100")
    h3.metric("Case Status", case_data.get('status', 'Processed'))

    st.markdown("---")

    # --- 1. Intelligence Summary ---
    st.markdown("### 📝 Intelligence Summary")
    summary = case_data.get('summary', '')
    # Handle both old 'legal_summary' and new 'summary' fields
    if not summary: summary = case_data.get('legal_summary', '')
    
    if not summary or "pending full summarization" in str(summary).lower() or len(str(summary)) < 30:
        st.write("Not Available")
    else:
        st.write(summary)

    # --- 2. Core Legal Issue ---
    st.markdown("### ⚖️ Core Legal Issue")
    with st.container(border=True):
        issue = case_data.get('legal_issue')
        if not issue: issue = case_data.get('core_legal_issue')
        st.write(issue or "Not Available")

    # --- 3. Relief Requested ---
    st.markdown("### 📜 Relief Requested")
    with st.container(border=True):
        st.write(case_data.get('relief_sought') or "Not Available")

    # --- 4. Final Decision / Outcome ---
    st.markdown("### ✅ Final Decision / Outcome")
    outcome = case_data.get('legal_outcome')
    if not outcome: outcome = raw.get('legal_outcome', '')
    
    if not outcome or "not available" in str(outcome).lower() or "pending review" in str(outcome).lower():
        st.warning("🕒 Outcome Pending Review")
    else:
        st.success(f"Outcome: {outcome}")

    st.markdown("---")
    col1, col2 = st.columns(2)

    # --- 5. Parties & Bench ---
    with col1:
        st.markdown("### 👥 Parties & Bench")
        with st.container(border=True):
            st.markdown(f"**Petitioner/Appellant:** {sanitize_metadata_field(case_data.get('petitioner'), 'party')}")
            st.markdown(f"**Respondent:** {sanitize_metadata_field(case_data.get('respondent'), 'party')}")
            st.markdown(f"**Bench/Judges:** {sanitize_metadata_field(case_data.get('bench'), 'bench')}")
            st.markdown(f"**Court:** {sanitize_metadata_field(case_data.get('court_name'), 'court')}")

    # --- 6. Timeline Analysis ---
    with col2:
        st.markdown("### 📅 Timeline Analysis")
        with st.container(border=True):
            # Dynamic date resolution
            f_val = case_data.get('filing_date') or raw.get('filing_date')
            j_val = case_data.get('judgment_date') or raw.get('judgment_date')
            h_val = case_data.get('hearing_date') or raw.get('hearing_date')
            
            import dateparser
            def format_legal_date(val):
                if not val or str(val).lower() in ["not available", "none", "unknown", "", "n/a"]: 
                    return "N/A", None
                try:
                    # If it's already a datetime object
                    if hasattr(val, "year"):
                        return val.strftime("%d %b %Y"), val
                        
                    s_val = str(val).strip()
                    
                    # Handle year-only strings (e.g., '1975')
                    if len(s_val) == 4 and s_val.isdigit():
                        return f"Year {s_val} (Approx)", datetime(int(s_val), 1, 1)
                    
                    # Only accept strict YYYY-MM-DD format from the backend
                    from datetime import datetime
                    # Truncate time if it's a full ISO string
                    if " " in s_val: s_val = s_val.split(" ")[0]
                    if "T" in s_val: s_val = s_val.split("T")[0]
                    
                    dt = datetime.strptime(s_val, "%Y-%m-%d")
                    return dt.strftime("%d %b %Y"), dt
                except Exception as e: 
                    return "N/A", None

            f_str, f_dt = format_legal_date(f_val)
            j_str, j_dt = format_legal_date(j_val)
            h_str, h_dt = format_legal_date(h_val)
            
            # Precise Age Calculation (STRICTLY FROM FILING DATE)
            age_str = "Not Available"
            if f_dt:
                from dateutil.relativedelta import relativedelta
                diff = relativedelta(datetime.utcnow(), f_dt)
                if diff.years > 0 or diff.months > 0 or diff.days > 0:
                    age_str = f"{diff.years} years, {diff.months} months, {diff.days} days old"
                else:
                    age_str = "Recent Ingestion"
            
            st.write(f"**Filing Date:** {f_str}")
            st.write(f"**Judgment Date:** {j_str}")
            st.write(f"**Hearing Date:** {h_str}")
            st.write(f"**Computed Case Age:** {age_str}")

    # --- 7. Statutes & Citations ---
    st.markdown("### 📚 Statutes & Citations")
    with st.container(border=True):
        statutes = case_data.get('extracted_statutes') or case_data.get('statutes_sections')
        citations = case_data.get('citations')
        st.write(f"**Statutes:** {statutes or 'Not Available'}")
        st.write(f"**Case Citations:** {citations or 'Not Available'}")

    # --- 8. Priority Analysis ---
    st.markdown("### 🚨 Priority Analysis")
    with st.container(border=True):
        st.write(f"**Reasoning:** {case_data.get('reasoning') or case_data.get('priority_reasoning_summary') or 'Standard prioritization applied.'}")

    # --- 9. Similar Matter Analysis ---
    st.markdown("### 🧬 Similar Matter Analysis")
    current_id = case_data.get('case_number')
    
    # Filter for VALID similar cases only (hide garbage)
    all_sim = [c for c in all_cases if c.get('case_number') != current_id and c.get('cluster_label') == case_data.get('cluster_label')]
    similar_cases = []
    for sc in all_sim:
        sc_id = sanitize_metadata_field(sc.get('case_number'), 'case_id')
        sc_title = sanitize_metadata_field(sc.get('title'), 'title')
        if sc_id != "Not Available" and sc_title != "Not Available":
            similar_cases.append(sc)

    if similar_cases:
        st.success(f"Found {len(similar_cases)} cases with high similarity.")
        for sc in similar_cases[:3]:
            st.caption(f"• {sc.get('title')} (ID: {sc.get('case_number')})")
    else:
        st.info("No high-similarity precedents found in current dataset.")

    # --- 10. View Full Case Text ---
    st.markdown("---")
    with st.expander("📄 View Full Extracted Case Text"):
        full_text = raw.get('full_text', case_data.get('raw_content', 'Raw content not available.'))
        st.markdown(f"<div class='scrollable-text' style='height: 300px; overflow-y: auto; background: #f8fafc; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 5px; font-family: monospace; white-space: pre-wrap;'>{full_text}</div>", unsafe_allow_html=True)

    # --- Action Bar at Bottom ---
    st.markdown("### 🛠️ Professional Actions")
    a1, a2 = st.columns(2)
    with a1:
        try:
            pdf_data = bytes(generate_case_pdf(case_data, raw))
            st.download_button("📄 Download PDF", pdf_data, f"Case_{current_id}.pdf", "application/pdf", use_container_width=True)
        except: st.button("📄 PDF Error", disabled=True, use_container_width=True)
    with a2:
        st.download_button("📤 Export JSON", json.dumps(case_data, indent=2, default=str), f"Case_{current_id}.json", "application/json", use_container_width=True)




# ────────────────────────────────────────────────────────
# 1. Case Registry (Enterprise Table Layout)
# ────────────────────────────────────────────────────────
if menu == "📋 Case Registry":
    st.markdown("<h2 class='section-header'>📋 Processed Case Registry</h2>", unsafe_allow_html=True)
    
    rc1, rc2, rc3 = st.columns([7, 1.5, 1.5])
    with rc3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with rc2:
        if st.button("🗑️ Clear Registry", use_container_width=True, type="secondary", help="Delete ALL cases from database"):
            try:
                res = requests.delete(f"{API_URL}/upload/cases/clear/all")
                if res.status_code == 200:
                    st.success("Registry Cleared")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to clear registry")
            except Exception as e:
                st.error(f"Error: {e}")
    
    if not all_cases:
        st.info("Registry is empty. Please upload cases in the 'Upload & Processing' tab to begin.")
    else:
        # 6. KPI Summary Cards
        total_cases = len(all_cases)
        high_priority = len([c for c in all_cases if c.get('priority_level') in ['High', 'Critical']])
        clusters = len(set(c.get('clustering_compatibility', 'General') for c in all_cases))
        
        st.markdown("""
        <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px;'>
            <div class='metric-card'>
                <h3>{0}</h3><p>Total Processed</p>
            </div>
            <div class='metric-card'>
                <h3 style='color:#dc2626;'>{1}</h3><p>High Priority</p>
            </div>
            <div class='metric-card'>
                <h3 style='color:#3b82f6;'>{2}</h3><p>Active Clusters</p>
            </div>
            <div class='metric-card'>
                <h3 style='color:#10b981;'>1.2s</h3><p>Avg Processing Time</p>
            </div>
        </div>
        """.format(total_cases, high_priority, clusters), unsafe_allow_html=True)
        
        # 5. Search and Filters
        with st.container():
            sc1, sc2, sc3, sc4 = st.columns([2, 1, 1, 1])
            search_q = sc1.text_input("Search Case Title or ID", placeholder="e.g. Amadalavalasa Cooperative...")
            filter_pri = sc2.selectbox("Priority", ["All", "Critical", "High", "Medium", "Low"])
            filter_cat = sc3.selectbox("Category", ["All"] + list(set(c.get('case_type', '') for c in all_cases if c.get('case_type'))))
            filter_status = sc4.selectbox("Status", ["Processed", "Pending Review", "Scheduled", "Archived"])

        filtered = all_cases
        if search_q: filtered = [c for c in filtered if search_q.lower() in str(c).lower()]
        if filter_pri != "All": filtered = [c for c in filtered if c.get('priority_level') == filter_pri]
        if filter_cat != "All": filtered = [c for c in filtered if c.get('case_type') == filter_cat]

        # Prepare Table Data (Synchronized with Header)
        table_data = []
        for c in filtered:
            # Use Shared Truth Logic
            p_score = calculate_final_priority(c)
            
            # Safely extract Year
            year_val = str(c.get('filing_date', 'N/A')).strip()
            if not year_val or year_val.lower() in ["not available", "n/a", "none", "unknown"]:
                year = "N/A"
            else:
                year = year_val[:4] if len(year_val) >= 4 else "N/A"
                
            table_data.append({
                "InternalID": c.get('id'),
                "Case ID": sanitize_metadata_field(c.get('case_number'), 'case_id'),
                "Case Title": sanitize_metadata_field(c.get('title'), 'title'),
                "Court": sanitize_metadata_field(c.get('court_name'), 'court'),
                "Year": year,
                "Category": c.get('case_type'),
                "Priority Score": p_score,
                "Cluster": c.get('cluster_label', 'UC-01'),
                "Status": "Processed",
                "Select": False,
                "Delete": False
            })
            
        df = pd.DataFrame(table_data)
        
        st.markdown("### Processed Document Index")
        
        col_btn1, col_btn2 = st.columns([6, 2])
        with col_btn1:
            st.caption(f"Select a row to open deep-dive Case Details or mark for deletion.")
        
        # Interactive DataFrame
        edited_df = st.data_editor(
            df,
            column_config={
                "InternalID": None, # Hide internal ID
                "Priority Score": st.column_config.NumberColumn("Score", help="Calculated Priority Score", format="%d%%"),
                "Select": st.column_config.CheckboxColumn("View", help="Select to open case details", default=False),
                "Delete": st.column_config.CheckboxColumn("🗑️", help="Mark for deletion", default=False),
            },
            disabled=["Case ID", "Case Title", "Court", "Year", "Category", "Priority Score", "Cluster", "Status"],
            hide_index=True,
            use_container_width=True,
            key="registry_editor"
        )

        # Handle Deletion
        to_delete_internal_ids = edited_df[edited_df["Delete"] == True]["InternalID"].tolist()
        if to_delete_internal_ids:
            with col_btn2:
                if st.button(f"🗑️ Delete ({len(to_delete_internal_ids)})", type="primary", use_container_width=True):
                    success_count = 0
                    for db_id in to_delete_internal_ids:
                        try:
                            res = requests.delete(f"{API_URL}/upload/cases/{db_id}")
                            if res.status_code == 200: success_count += 1
                        except: pass
                    
                    if success_count > 0:
                        st.session_state.last_deleted_ids = to_delete_internal_ids
                        st.success(f"Deleted {success_count} cases.")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()

        # Undo Button
        if 'last_deleted_ids' in st.session_state and st.session_state.last_deleted_ids:
            with col_btn2:
                if st.button(f"↩️ Undo ({len(st.session_state.last_deleted_ids)})", use_container_width=True):
                    undo_count = 0
                    for db_id in st.session_state.last_deleted_ids:
                        try:
                            res = requests.post(f"{API_URL}/upload/cases/{db_id}/undo")
                            if res.status_code == 200: undo_count += 1
                        except: pass
                    if undo_count > 0:
                        st.toast(f"Restored {undo_count} cases.", icon="↩️")
                        st.session_state.last_deleted_ids = []
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()

        # --- High-Fidelity Selection Mapping ---
        # Get all currently selected Internal IDs (Immutable Database Primary Keys)
        selected_ids = edited_df[edited_df["Select"] == True]["InternalID"].tolist()
        
        # Track previous selection to detect the NEW selection
        if 'last_selected_ids' not in st.session_state:
            st.session_state.last_selected_ids = []
            
        new_selections = list(set(selected_ids) - set(st.session_state.last_selected_ids))
        
        # If a new row was just checked, focus on it
        if new_selections:
            st.session_state.active_case_id = new_selections[0]
        elif not selected_ids:
            st.session_state.active_case_id = None
        elif st.session_state.get('active_case_id') not in selected_ids:
            # If the currently active case was unchecked, pick the next available one
            st.session_state.active_case_id = selected_ids[0] if selected_ids else None
            
        st.session_state.last_selected_ids = selected_ids
        
        # Render Deep Dive for the SPECIFIC active Case ID only
        if st.session_state.get('active_case_id'):
            # Lookup via immutable DB ID, immune to string formatting mutations
            target_case = next((c for c in all_cases if c.get('id') == st.session_state.active_case_id), None)
            if target_case:
                show_case_details(target_case)
            else:
                st.error("Error: Selected case data mismatch. Please refresh.")

# ────────────────────────────────────────────────────────
# 2. Upload & Processing
# ────────────────────────────────────────────────────────
elif menu == "📤 Upload & Processing":
    st.markdown("<h2 class='section-header'>📤 Document Ingestion & Processing</h2>", unsafe_allow_html=True)
    st.markdown("Upload Legal Documents (PDF, PNG, JPG). System will extract metadata and populate the Case Registry.")
    
    files = st.file_uploader("Select documents to process", type=["pdf", "png", "jpg"], accept_multiple_files=True)
    process_btn = st.button("Process Documents", type="primary", use_container_width=True)
    
    if process_btn and files:
        with st.spinner("Extracting intelligence & analyzing legal features..."):
            payload = [("files", (f.name, f.getvalue(), f.type)) for f in files]
            try:
                res = requests.post(f"{API_URL}/upload/bulk", files=payload, timeout=600)
                if res.status_code == 200:
                    data = res.json()
                    results = data.get('results', [])
                    success = [r for r in results if 'error' not in r]
                    errors  = [r for r in results if 'error' in r]
                    if success:
                        if len(success) == len(files):
                            st.success(f"✅ Successfully processed ALL {len(success)} document(s).")
                        else:
                            st.warning(f"⚠️ Processed {len(success)} out of {len(files)} uploaded document(s). Some files may have failed or timed out.")
                        
                        # Force refresh
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    if errors:
                        for e in errors:
                            st.error(f"❌ {e['file']}: {e['error']}")
                else:
                    st.error(f"Ingestion failed. Status: {res.status_code}")

            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. The LLM is taking too long. The case may still have been saved — check the Case Registry.")
                st.cache_data.clear()
            except Exception as ex:
                st.error(f"Connection error: {ex}")

# ────────────────────────────────────────────────────────
# 3. Priority Matrix
# ────────────────────────────────────────────────────────
elif menu == "🔥 Priority Matrix":
    st.markdown("<h2 class='section-header'>🔥 Priority Matrix & Operational Decision Dashboard</h2>", unsafe_allow_html=True)
    
    # System Status Indicators
    st.sidebar.markdown("### System Status")
    st.sidebar.success("✅ AI Engine: Ready")
    st.sidebar.success("✅ OCR: Active")
    st.sidebar.info("✅ LLM: Connected (Groq)")

    if not all_cases:
        st.info("No cases available for prioritization.")
    else:
        # Precompute breakdowns for all cases
        case_breakdowns = {}
        for c in all_cases:
            case_breakdowns[c.get('id')] = get_priority_breakdown(c)

        # A. Summary Cards (Priority Distribution only)
        total_cases = len(all_cases)
        high_cases = len([c for c in all_cases if case_breakdowns[c.get('id')]["level"] == 'High'])
        medium_cases = len([c for c in all_cases if case_breakdowns[c.get('id')]["level"] == 'Medium'])
        low_cases = len([c for c in all_cases if case_breakdowns[c.get('id')]["level"] == 'Low'])
        avg_score = np.mean([case_breakdowns[c.get('id')]["score"] for c in all_cases]) if all_cases else 0.0

        st.markdown(f"""
        <div style='display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin-bottom: 25px;'>
            <div class='metric-card' style='border-left: 5px solid #3b82f6;'>
                <p style='color:#64748b; font-size:12px; margin:0;'>TOTAL CASES</p>
                <h3 style='color:#1e3a8a; font-size:24px; margin:5px 0 0 0;'>{total_cases}</h3>
            </div>
            <div class='metric-card' style='border-left: 5px solid #dc2626;'>
                <p style='color:#64748b; font-size:12px; margin:0;'>HIGH PRIORITY</p>
                <h3 style='color:#dc2626; font-size:24px; margin:5px 0 0 0;'>{high_cases}</h3>
            </div>
            <div class='metric-card' style='border-left: 5px solid #ea580c;'>
                <p style='color:#64748b; font-size:12px; margin:0;'>MEDIUM PRIORITY</p>
                <h3 style='color:#ea580c; font-size:24px; margin:5px 0 0 0;'>{medium_cases}</h3>
            </div>
            <div class='metric-card' style='border-left: 5px solid #10b981;'>
                <p style='color:#64748b; font-size:12px; margin:0;'>LOW PRIORITY</p>
                <h3 style='color:#059669; font-size:24px; margin:5px 0 0 0;'>{low_cases}</h3>
            </div>
            <div class='metric-card' style='border-left: 5px solid #6366f1;'>
                <p style='color:#64748b; font-size:12px; margin:0;'>AVG PRIORITY SCORE</p>
                <h3 style='color:#4f46e5; font-size:24px; margin:5px 0 0 0;'>{avg_score:.1f}%</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Split page: Left Column (70%) for Matrix and Ranked Table, Right Column (30%) for Breakdown & Actions
        col_left, col_right = st.columns([7, 3])

        # Prepare Matrix Data with Jittering for visual display
        matrix_data = []
        import hashlib
        for c in all_cases:
            bd = case_breakdowns[c.get('id')]
            p_score = bd["score"]
            u_score = bd["urgency_factor"]
            comp_score, comp_level = calculate_complexity_impact(c)
            
            # Determine Urgency Level Coordinate
            if u_score >= 70:
                u_level = "High"
                x_coord = 3.0
            elif u_score >= 40:
                u_level = "Medium"
                x_coord = 2.0
            else:
                u_level = "Low"
                x_coord = 1.0
                
            # Determine Complexity Coordinate
            if comp_level == "High":
                y_coord = 3.0
            elif comp_level == "Medium":
                y_coord = 2.0
            else:
                y_coord = 1.0
                
            # Stable Jitter coordinate generation based on case ID hash
            h_val = int(hashlib.md5(str(c.get('id', '')).encode()).hexdigest(), 16)
            jitter_x = ((h_val % 100) / 100.0 - 0.5) * 0.35
            jitter_y = (((h_val // 100) % 100) / 100.0 - 0.5) * 0.35
            
            matrix_data.append({
                "Case ID": sanitize_metadata_field(c.get('case_number'), 'case_id'),
                "Case Title": sanitize_metadata_field(c.get('title'), 'title'),
                "Priority Score": p_score,
                "Priority Level": bd["level"],
                "Urgency Score": u_score,
                "Urgency Level": u_level,
                "Complexity Score": comp_score,
                "Complexity Level": comp_level,
                "Case Age": bd["age_str"],
                "X": x_coord + jitter_x,
                "Y": y_coord + jitter_y,
            })
            
        df_matrix = pd.DataFrame(matrix_data)

        # Ranked Priority Table Data Preparation
        table_rows = []
        for idx, c in enumerate(sorted(all_cases, key=lambda x: case_breakdowns[x.get('id')]["score"], reverse=True)):
            bd = case_breakdowns[c.get('id')]
            p_score = bd["score"]
            
            # Filing Year
            filing_year = "N/A"
            fd = c.get('filing_date')
            if fd:
                try:
                    from datetime import datetime
                    if isinstance(fd, str):
                        filing_year = str(datetime.fromisoformat(fd.replace("Z", "")).year)
                    elif isinstance(fd, datetime):
                        filing_year = str(fd.year)
                except:
                    pass
            
            age_days = bd["age_days"]
            if age_days >= 365:
                case_age = f"{age_days // 365} yrs"
            else:
                case_age = f"{age_days} days"
                
            table_rows.append({
                "Rank": idx + 1,
                "InternalID": c.get('id'),
                "Case ID": sanitize_metadata_field(c.get('case_number'), 'case_id'),
                "Case Title": sanitize_metadata_field(c.get('title'), 'title'),
                "Filing Year": filing_year,
                "Case Age": case_age,
                "Score": f"{p_score:.0f}%",
                "Final Priority": bd["level"],
                "Urgency Reason": bd["explanation"],
                "Select": False
            })
        df_ranked = pd.DataFrame(table_rows)

        # Active case selection handling
        if 'active_matrix_case_id' not in st.session_state:
            st.session_state.active_matrix_case_id = None

        with col_left:
            # B. Priority Heatmap / Matrix
            st.markdown("### 🗺️ Priority Analytics Matrix")
            st.caption("Visual representation of Urgency (X-axis) vs. Legal Impact/Complexity (Y-axis). Plots all active judicial workload cases.")
            
            fig = go.Figure()
            
            # Quadrant boundary lines
            fig.add_shape(type="line", x0=1.5, y0=0.5, x1=1.5, y1=3.5, line=dict(color="#cbd5e1", width=1.5, dash="dash"))
            fig.add_shape(type="line", x0=2.5, y0=0.5, x1=2.5, y1=3.5, line=dict(color="#cbd5e1", width=1.5, dash="dash"))
            fig.add_shape(type="line", x0=0.5, y0=1.5, x1=3.5, y1=1.5, line=dict(color="#cbd5e1", width=1.5, dash="dash"))
            fig.add_shape(type="line", x0=0.5, y0=2.5, x1=3.5, y1=2.5, line=dict(color="#cbd5e1", width=1.5, dash="dash"))
            
            # Quadrant Labels (Annotations)
            fig.add_annotation(x=1.0, y=3.4, text="🏛️ High Legal Impact", showarrow=False, font=dict(size=11, color="#475569", weight="bold"), bgcolor="rgba(241,245,249,0.9)", bordercolor="#cbd5e1", borderwidth=1, borderpad=4)
            fig.add_annotation(x=3.0, y=3.4, text="🚨 Critical Priority", showarrow=False, font=dict(size=11, color="#991b1b", weight="bold"), bgcolor="rgba(254,242,242,0.9)", bordercolor="#fecaca", borderwidth=1, borderpad=4)
            fig.add_annotation(x=1.0, y=0.6, text="📋 Routine Cases", showarrow=False, font=dict(size=11, color="#166534", weight="bold"), bgcolor="rgba(240,253,244,0.9)", bordercolor="#bbf7d0", borderwidth=1, borderpad=4)
            fig.add_annotation(x=3.0, y=0.6, text="⚡ Operational Urgency", showarrow=False, font=dict(size=11, color="#c2410c", weight="bold"), bgcolor="rgba(255,247,237,0.9)", bordercolor="#fed7aa", borderwidth=1, borderpad=4)
            
            colors_map = {
                'High': '#dc2626',
                'Medium': '#ea580c',
                'Low': '#22c55e'
            }
            
            # Add scatter markers grouped by priority
            for prio, color in colors_map.items():
                sub_df = df_matrix[df_matrix["Priority Level"] == prio]
                if not sub_df.empty:
                    fig.add_trace(go.Scatter(
                        x=sub_df["X"],
                        y=sub_df["Y"],
                        mode="markers+text" if len(sub_df) < 8 else "markers",
                        name=prio,
                        text=sub_df["Case ID"],
                        textposition="top center",
                        marker=dict(
                            size=22, # Slightly larger plotted points
                            color=color,
                            opacity=0.85,
                            line=dict(width=1.5, color="#ffffff")
                        ),
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "ID: %{text}<br>"
                            "Priority Score: %{customdata[1]:.0f}%<br>"
                            "Age: %{customdata[7]}"
                            "<extra></extra>"
                        ),
                        customdata=sub_df[["Case Title", "Priority Score", "Priority Level", "Urgency Score", "Urgency Level", "Complexity Score", "Complexity Level", "Case Age"]].values
                    ))
            
            fig.update_layout(
                xaxis=dict(
                    title="Urgency Level",
                    tickmode="array",
                    tickvals=[1, 2, 3],
                    ticktext=["Low (<40%)", "Medium (40-70%)", "High (≥70%)"],
                    range=[0.5, 3.5],
                    gridcolor="#f1f5f9",
                    zeroline=False
                ),
                yaxis=dict(
                    title="Legal Impact & Complexity",
                    tickmode="array",
                    tickvals=[1, 2, 3],
                    ticktext=["Low (<40%)", "Medium (40-70%)", "High (≥70%)"],
                    range=[0.5, 3.5],
                    gridcolor="#f1f5f9",
                    zeroline=False
                ),
                plot_bgcolor="rgba(248, 250, 252, 0.6)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=10, b=20), # Reduced excessive whitespace
                height=380,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True) # Better spacing
            
            # C. Ranked Priority Table
            st.markdown("### 🏆 Ranked Priority Table")
            st.caption("Cases sorted dynamically by computed priority. Use **Select** to inspect scoring components.")
            
            edited_df = st.data_editor(
                df_ranked,
                column_config={
                    "InternalID": None,
                    "Rank": st.column_config.NumberColumn("Rank", width="small"),
                    "Filing Year": st.column_config.TextColumn("Filing Year", width="small"),
                    "Case Age": st.column_config.TextColumn("Case Age", width="small"),
                    "Score": st.column_config.TextColumn("Score", width="small"),
                    "Select": st.column_config.CheckboxColumn("Select", help="Check to inspect score breakdown", default=False),
                },
                disabled=["Rank", "Case ID", "Case Title", "Filing Year", "Case Age", "Score", "Final Priority", "Urgency Reason"],
                hide_index=True,
                use_container_width=True,
                key="priority_matrix_editor"
            )
            
            # Capture selection
            selected_ids = edited_df[edited_df["Select"] == True]["InternalID"].tolist()
            if selected_ids:
                st.session_state.active_matrix_case_id = selected_ids[0]

        # Determine active case for right-hand analytical panels
        active_case_id = st.session_state.active_matrix_case_id
        if not active_case_id and not df_ranked.empty:
            active_case_id = df_ranked.iloc[0]["InternalID"]
            
        active_case = next((c for c in all_cases if c.get('id') == active_case_id), None)

        with col_right:
            # D. Score Breakdown Panel
            if active_case:
                st.markdown("### 📊 Score Breakdown")
                st.markdown(f"**Case ID:** {sanitize_metadata_field(active_case.get('case_number'), 'case_id')}")
                st.markdown(f"<p style='font-size:14px; color:#475569; font-weight:600; margin-top:-5px;'>{sanitize_metadata_field(active_case.get('title'), 'title')}</p>", unsafe_allow_html=True)
                
                bd = case_breakdowns[active_case.get('id')]
                p_score = bd["score"]
                u = bd["urgency_factor"]
                b = bd["backlog_factor"]
                h = bd["humanitarian_boost"]
                
                p_color = colors_map.get(bd["level"], '#22c55e')
                
                st.markdown(f"""
                <div style='background: #ffffff; border: 1px solid #e2e8f0; border-left: 6px solid {p_color}; padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);'>
                    <p style='margin:0; font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:0.5px;'>Weighted Priority Score</p>
                    <h2 style='margin:5px 0 0 0; color:#1e3a8a; font-size:38px; font-weight:700;'>{p_score:.0f}/100</h2>
                    <span style='background-color:{p_color}18; color:{p_color}; border: 1px solid {p_color}40; padding:3px 12px; border-radius:20px; font-size:11px; font-weight:700; display:inline-block; margin-top:5px; text-transform:uppercase;'>
                        {bd["level"]} Priority
                    </span>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("**Scoring Breakdown Weights**")
                st.caption("Formula: 60% Urgency + 30% Backlog + 10% Humanitarian")
                
                st.markdown(f"**Urgency Factor** ({u:.0f}/100)")
                st.progress(u / 100.0)
                
                st.markdown(f"**Backlog Factor** ({b:.0f}/100)")
                st.progress(b / 100.0)
                
                st.markdown(f"**Humanitarian Boost** ({h:.0f}/20)")
                st.progress(h / 20.0)
                
                st.markdown("<p style='font-weight:600; margin-bottom:5px; font-size:13px; color:#1e293b;'>Why Score Was Assigned</p>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:12px; color:#475569; margin-bottom:8px; line-height:1.4; background:#f8fafc; padding:10px; border-radius:6px; border:1px solid #e2e8f0;'>{bd['explanation']}</div>", unsafe_allow_html=True)
            else:
                st.info("Select a case in the Ranked Table to view its breakdown.")

            # E. Operational Alerts Section
            st.markdown("### 🚨 Operational Alerts")
            
            # Dynamic calculations for operational issues across the active workload
            missing_date = len([c for c in all_cases if not c.get('filing_date') or str(c.get('filing_date')).lower() in ['not available', 'none', 'null', '']])
            ocr_incomplete = len([c for c in all_cases if c.get('extraction_method') == 'OCR' and (not c.get('title') or str(c.get('title')).lower() in ['not available', 'none', 'null', ''])])
            missing_meta = len([c for c in all_cases if not c.get('petitioner') or str(c.get('petitioner')).lower() in ['not available', 'none', 'null', '']])
            parsing_issues = len([c for c in all_cases if not c.get('summary') or str(c.get('summary')).lower() in ['not available', 'none', 'null', '']])
            
            op_alerts = []
            if missing_date > 0:
                op_alerts.append(f"⚠ <b>{missing_date} case(s)</b> missing filing date")
            if ocr_incomplete > 0:
                op_alerts.append(f"⚠ <b>{ocr_incomplete} case(s)</b> OCR extraction incomplete")
            if missing_meta > 0:
                op_alerts.append(f"⚠ <b>{missing_meta} case(s)</b> missing metadata (petitioner/respondent)")
            if parsing_issues > 0:
                op_alerts.append(f"⚠ <b>{parsing_issues} case(s)</b> AI parsing issues detected")
                
            if not op_alerts:
                st.success("🟢 No critical operational alerts.")
            else:
                for alert in op_alerts:
                    st.markdown(f"""
                    <div style='background-color:#fffbeb; border:1px solid #fef3c7; border-left:4px solid #f59e0b; border-radius:6px; padding:10px; margin-bottom:8px; font-size:12px; color:#b45309; line-height:1.3;'>
                        {alert}
                    </div>
                    """, unsafe_allow_html=True)

            # F. Recommended Actions
            st.markdown("### 🛠️ Recommended Actions")
            actions = []
            
            high_critical = [c for c in all_cases if case_breakdowns[c.get('id')]["level"] in ['High']]
            if high_critical:
                top_priority_case = sorted(high_critical, key=lambda x: case_breakdowns[x.get('id')]["score"], reverse=True)[0]
                actions.append(f"⚡ **Prioritize Top Urgent Matters**: Fast-track <i>{sanitize_metadata_field(top_priority_case.get('title'), 'title')}</i> ({sanitize_metadata_field(top_priority_case.get('case_number'), 'case_id')}) for immediate hearing.")
                
            humanitarian_all = [c for c in all_cases if c.get('humanitarian_flag')]
            if humanitarian_all:
                actions.append(f"🏥 **Review Humanitarian Cases First**: Triage the {len(humanitarian_all)} pending humanitarian case(s) to address personal liberties.")
                
            low_priority_all = [c for c in all_cases if case_breakdowns[c.get('id')]["level"] == 'Low']
            if low_priority_all:
                actions.append(f"📅 **Schedule Low-Priority Later**: Defer the {len(low_priority_all)} low-priority matter(s) to clear current backlog congestion.")
                
            if not actions:
                actions.append("✅ **Regular Ingestion**: Backlog pressure is healthy; continue normal court operations.")
                
            for action in actions:
                st.markdown(f"<div style='font-size:12px; color:#334155; margin-bottom:8px; line-height:1.4;'>{action}</div>", unsafe_allow_html=True)



# ────────────────────────────────────────────────────────
# 4. Similar Case Clusters
# ────────────────────────────────────────────────────────
elif menu == "🧬 Similar Clustering":
    st.markdown("<h2 class='section-header'>🧬 Intelligent Legal Clustering</h2>", unsafe_allow_html=True)
    st.markdown("Group pending matters by semantic similarity to optimize bench assignments.")
    
    if not all_cases:
        st.info("Upload cases to view clusters.")
    else:
        # Fetch clusters from API
        res = requests.post(f"{API_URL}/cases/cluster")
        if res.status_code == 200:
            clusters = res.json()
            
            if isinstance(clusters, dict) and "message" in clusters:
                st.info(clusters["message"])
            else:
                for cl in clusters:
                    with st.container():
                        st.markdown(f"""
                        <div style="background:#ffffff; padding:20px; border-radius:10px; border:1px solid #e2e8f0; border-left:6px solid #3b82f6; margin-bottom:20px;">
                            <h4 style="margin:0;">{cl['topic']} (Cluster {cl['cluster_id']})</h4>
                            <p style="color:#64748b; font-size:14px; margin-bottom:10px;">{cl['reason']}</p>
                            <div style="font-weight:600; font-size:13px;">{cl['total_cases']} Similar Cases Found</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with st.expander("View Grouped Cases"):
                            for item in cl['cases']:
                                st.markdown(f"**{item['title']}**")
                                st.caption(f"{item['priority']} Priority | Urgency: {item['urgency']}% | Year: {item['year']}")
                                st.divider()
        else:
            st.error("Could not fetch clustering data.")


# ────────────────────────────────────────────────────────
# 5. Precedent Retrieval
# ────────────────────────────────────────────────────────
elif menu == "📚 Precedent Intelligence":
    st.markdown("<h2 class='section-header'>📚 Precedent Retrieval (RAG)</h2>", unsafe_allow_html=True)
    st.info("Module ready. Select a case from the Registry to view matching historical precedents.")

# ────────────────────────────────────────────────────────
# 6. Humanitarian Alerts
# ────────────────────────────────────────────────────────
elif menu == "🚨 Humanitarian Triage":
    st.markdown("<h2 class='section-header'>🚨 Humanitarian & Emergency Alerts</h2>", unsafe_allow_html=True)
    urgent_cases = [c for c in all_cases if c.get('humanitarian_flag') or c.get('urgency_score', 0) >= 80]
    
    if not urgent_cases: st.success("No critical humanitarian alerts.")
    else:
        for c in urgent_cases:
            st.error(f"**URGENT:** {c.get('title')} (Case {c.get('case_number')}) - Needs immediate attention.")

# ────────────────────────────────────────────────────────
# 7. Schedule Optimizer
# ────────────────────────────────────────────────────────
elif menu == "📅 Schedule Optimizer":
    st.markdown("<h2 class='section-header'>📅 AI Schedule Optimizer</h2>", unsafe_allow_html=True)
    
    court_date = st.date_input("Target Hearing Date", datetime.now().date())
    if st.button("Generate Cause List", type="primary"):
        with st.spinner("Optimizing schedule..."):
            res = requests.post(f"{API_URL}/schedule/generate", params={"court_date": court_date.isoformat()})
            if res.status_code == 200:
                data = res.json()
                st.success(f"Optimized hearing schedule generated for {data['date']}.")
                
                sched_data = []
                for h in data['cause_list']:
                    sched_data.append({
                        "Date": data['date'],
                        "Time Slot": h['time_slot'],
                        "Courtroom": "Court 1", # Mocked
                        "Judge": h['judge'],
                        "Cases Assigned": f"{h['title']} ({h['case_number']})",
                        "Estimated Duration": h['estimated_duration']
                    })
                st.dataframe(pd.DataFrame(sched_data), use_container_width=True, hide_index=True)

# ────────────────────────────────────────────────────────
# 8. Analytics Dashboard
# ────────────────────────────────────────────────────────
elif menu == "📊 Analytics Dashboard":
    st.markdown("<h2 class='section-header'>📊 Judicial Analytics & Backlog Intelligence</h2>", unsafe_allow_html=True)
    
    if not all_cases:
        st.info("Ingest cases to view analytics.")
    else:
        # 1. KPI Metrics
        total = len(all_cases)
        critical = len([c for c in all_cases if c.get('priority_level') == 'Critical'])
        avg_backlog = np.mean([c.get('backlog_score', 0) for c in all_cases])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Documents", total)
        c2.metric("Critical Matters", critical, delta=f"{critical} Emergency")
        c3.metric("Avg Backlog Score", f"{avg_backlog:.1f}%")
        
        st.divider()
        
        # 2. Visualizations
        v1, v2 = st.columns(2)
        
        with v1:
            st.markdown("#### Priority Distribution")
            p_counts = pd.Series([c.get('priority_level', 'Low') for c in all_cases]).value_counts().reset_index()
            p_counts.columns = ['Priority', 'Count']
            fig1 = px.pie(p_counts, values='Count', names='Priority', hole=0.4, 
                         color_discrete_map={'Critical':'#dc2626', 'High':'#ea580c', 'Medium':'#f59e0b', 'Low':'#10b981'})
            st.plotly_chart(fig1, use_container_width=True)
            
        with v2:
            st.markdown("#### Backlog Age Distribution")
            ages = [c.get('case_age_days', 0) / 365 for c in all_cases]
            fig2 = px.histogram(x=ages, labels={'x':'Years Old', 'y':'Count'}, nbins=10, color_discrete_sequence=['#3b82f6'])
            st.plotly_chart(fig2, use_container_width=True)

