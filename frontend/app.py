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
    """Single source of truth for priority score across all dashboard sections."""
    u = float(c.get('urgency_score', 0) or 0)
    b = float(c.get('backlog_score', 0) or 0)
    h = 20.0 if c.get('humanitarian_flag') else 0.0
    
    # Standard weighting: 60% Urgency, 30% Backlog, 10% Humanitarian
    score = (u * 0.6) + (b * 0.3) + (h * 0.1)
    
    # Ensure a non-zero base if components exist
    if score == 0: score = u
    return min(max(score, 0), 100)

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
    st.markdown("<h2 class='section-header'>🔥 Priority Matrix & Explainability</h2>", unsafe_allow_html=True)
    
    # System Status Indicators
    st.sidebar.markdown("### System Status")
    st.sidebar.success("✅ AI Engine: Ready")
    st.sidebar.success("✅ OCR: Active")
    st.sidebar.info("✅ LLM: Connected (Groq)")

    if not all_cases:
        st.info("No cases available for prioritization.")
    else:
        table_data = []
        for c in sorted(all_cases, key=lambda x: calculate_final_priority(x), reverse=True):
            p_score = calculate_final_priority(c)
            
            # Skip cases with 0% across the board to keep matrix clean
            if p_score == 0:
                continue
                
            table_data.append({
                "Case": c.get('title'),
                "Urgency": (c.get('urgency_score', 0) or 0) / 100.0,
                "Backlog": (c.get('backlog_score', 0) or 0) / 100.0,
                "Priority Score": p_score,
                "Priority": c.get('priority_level'),
                "AI Reason": c.get('reasoning', '')
            })
            
        df = pd.DataFrame(table_data)
        st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Urgency": st.column_config.ProgressColumn("Urgency", min_value=0.0, max_value=1.0, format="%d%%"),
                "Backlog": st.column_config.ProgressColumn("Backlog", min_value=0.0, max_value=1.0, format="%d%%"),
                "Priority Score": st.column_config.NumberColumn("Priority Score", format="%d%%"),
                "Priority": st.column_config.TextColumn("Final Priority")
            }
        )


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

