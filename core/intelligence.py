import io
import json
import pdfplumber
import pytesseract
import fitz  # PyMuPDF
import re
import dateparser
from PIL import Image
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.config import settings

from langchain_ollama import OllamaLLM
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

from core.research import legal_research

class CaseSchema(BaseModel):
    case_title: str = Field(description="Descriptive case title inferred from parties or matter (e.g., 'Amir Hussain vs State of U.P.')")
    petitioner: str = Field(description="Name of the petitioner or appellant")
    respondent: str = Field(description="Name of the respondent")
    court_name: str = Field(description="Name of the court (e.g., Allahabad High Court)")
    filing_date: str = Field(description="Date of filing if available, or 'Inferred from context'")
    case_type: str = Field(description="One of: Bail, Criminal, Civil, Domestic Violence, Property, Juvenile, Writ, Constitutional")
    relief_sought: str = Field(description="The primary relief or prayer requested by the petitioner")
    legal_issue: str = Field(description="The core legal issue or question of law involved")
    statutes_sections: List[str] = Field(description="List of relevant Statutes, Acts, or IPC Sections mentioned")
    legal_summary: str = Field(description="A concise legal summary generated from the extracted text")
    priority_reasoning: str = Field(description="Case-specific reasoning for prioritization (e.g., 'Bail delay and personal liberty issue')")
    clustering_compatibility: str = Field(description="Type of cases this can be grouped with (e.g., 'Bail/Criminal')")
    scheduling_compatibility: str = Field(description="Urgency/Type for scheduling (e.g., 'Urgent/Constitutional')")
    urgency_score: int = Field(description="0-100 based on legal features")
    confidence_score: int = Field(description="0-100 based on extraction completeness")
    recommended_priority: str = Field(description="High, Medium, or Low")

class IntelligenceEngine:
    def __init__(self):
        self.ollama_llm = None
        try:
            self.ollama_llm = OllamaLLM(
                model=settings.LLM_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                format="json"
            )
        except Exception as e:
            print(f"[IntelligenceEngine] Ollama unavailable: {e}")

        self.groq_llm = None
        try:
            if settings.GROQ_API_KEY:
                self.groq_llm = ChatGroq(
                    groq_api_key=settings.GROQ_API_KEY,
                    model_name=settings.GROQ_MODEL,
                    response_format={"type": "json_object"}
                )
        except Exception as e:
            print(f"[IntelligenceEngine] Groq unavailable: {e}")

        self.llm = self.groq_llm if self.groq_llm else self.ollama_llm

    async def extract_case_info(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """High-fidelity multi-stage extraction pipeline."""
        text, method = self._robust_extract_text(file_content, file_name)
        text = self._clean_text(text)
        
        if len(text.strip()) < 50:
            extracted = self._fallback_regex_extraction(text)
            return self._ensure_metadata_integrity(extracted, text)

        # Smart Truncation: Focus on first 2 pages (approx 6000 chars) and last page (approx 3000 chars)
        llm_input = text[:6000]
        if len(text) > 7000:
            llm_input += "\n\n[... DOCUMENT MID-SECTION OMITTED ...]\n\n[... FINAL CHAPTERS / CONCLUSION ...]\n\n" + text[-3000:]
        
        prompt = PromptTemplate(
            template="""
            You are a senior Indian Judicial Analyst. Perform a deep-dive analysis on the provided case text.
            
            CRITICAL INSTRUCTIONS:
            1. FILING DATE: Extract only if explicitly stated. If not found, return 'Not Available'. NEVER guess or use today's date.
            2. SUMMARY: Generate a unique, document-specific summary including Facts, Dispute, Issue, and Decision.
            3. LEGAL ISSUE: Extract exactly ONE concise sentence.
            4. FINAL DECISION: Detect the final legal outcome from ending paragraphs.
            5. PRIORITY: Unique reasoning based on case nature.
            
            Return valid JSON only:
            {{
             "case_title": "Short descriptive title",
             "case_number_extracted": "e.g. WP 123/2023",
             "petitioner": "Full Name",
             "respondent": "Full Name",
             "court_name": "Full Name of Court",
             "bench": "Judges",
             "case_type_inferred": "e.g. Criminal, Tax, Civil",
             "filing_date": "YYYY-MM-DD or Not Available",
             "judgment_date": "YYYY-MM-DD or Not Available",
             "relief_sought": "Detected prayer/relief",
             "core_legal_issue": "ONE concise sentence",
             "legal_outcome": "Final result of the case",
             "acts": ["Act 1"],
             "sections": ["Section X"],
             "citations": ["Citation 1"],
             "summary": "Detailed 4-6 line case-specific intelligence summary",
             "urgency_score": 85,
             "priority_reasoning_summary": "Unique reasoning"
            }}

            ### DOCUMENT EXTRACT:
            {text}
            """,
            input_variables=["text"]
        )

        extracted = None
        if self.llm:
            try:
                response = self.llm.invoke(prompt.format(text=llm_input))
                res_text = response.content if hasattr(response, 'content') else str(response)
                
                # Cleanup JSON
                res_text = res_text.strip()
                if "```json" in res_text: res_text = res_text.split("```json")[1].split("```")[0].strip()
                elif "```" in res_text: res_text = res_text.split("```")[1].split("```")[0].strip()
                
                start = res_text.find('{')
                end = res_text.rfind('}')
                if start != -1 and end != -1:
                    extracted = json.loads(res_text[start:end+1])
            except Exception as e:
                print(f"LLM Extraction failed: {e}")

        if not extracted:
            extracted = self._fallback_regex_extraction(text)

        # 1. Document-Specific Robust Date Extraction (Independent for each case)
        robust_dates = self._extract_dates_robustly(text)
        
        # STRICT OVERRIDE: Filing Date MUST come only from the keyword-driven robust extractor. 
        # This prevents the LLM from grabbing random dates from cited cases or statutes.
        extracted["filing_date"] = robust_dates["filing_date"]
        
        # Fallback for judgment/hearing if LLM failed
        for k in ["judgment_date", "hearing_date"]:
            if not re.match(r'\d{4}-\d{2}-\d{2}', str(extracted.get(k, ""))):
                extracted[k] = robust_dates[k]

        # 2. Filename fallback for title
        if not extracted.get("case_title") or "available" in str(extracted.get("case_title")).lower():
            extracted["case_title"] = file_name.replace(".pdf", "").replace("_", " ").title()

        extracted.update({
            "extraction_method": method,
            "extracted_length": len(text),
            "full_text": text
        })

        return self._ensure_metadata_integrity(extracted, text)

    def _extract_dates_robustly(self, text: str) -> Dict[str, str]:
        """High-fidelity date extraction for filing, judgment, and hearing dates."""
        dates = {"filing_date": "Not Available", "judgment_date": "Not Available", "hearing_date": "Not Available"}
        
        # 1. Advanced Regex Patterns
        full_date_pattern = r'(\b\d{1,2}(?:\s+|[-/])(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2})(?:\s+|[-/])\d{4}\b|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b)'
        
        # 2. Contextual Search for Judgment Date
        judgment_contexts = [r'judgment\s+on\s+', r'dated\s+the\s+', r'decided\s+on\s+', r'dated\s+this\s+']
        for kw in judgment_contexts:
            match = re.search(kw + full_date_pattern, text, re.IGNORECASE)
            if match:
                dates["judgment_date"] = match.group(1).strip()
                break

        # 3. Contextual Search for Filing/Institution Date
        # Strictly limited to filing-specific contexts to prevent precedent date leakage
        filing_contexts = [
            r'filing\s+date\s*', r'filed\s+on\s*', r'date\s+of\s+filing\s*', 
            r'institution\s+date\s*', r'date\s+of\s+institution\s*', 
            r'presented\s+on\s*', r'instituted\s+on\s*', 
            r'appeal\s+filed\s*'
        ]
        for kw in filing_contexts:
            match = re.search(kw + r'[:\-]?\s*' + full_date_pattern, text, re.IGNORECASE)
            if match:
                dates["filing_date"] = match.group(1).strip()
                break

        # 4. Hearing Date
        hearing_match = re.search(r'hearing\s+on\s*' + full_date_pattern, text, re.IGNORECASE)
        if hearing_match: dates["hearing_date"] = hearing_match.group(1).strip()

        # 5. Normalize to YYYY-MM-DD (No fallback years or fuzzy logic allowed)
        import dateparser
        for k, v in dates.items():
            if v and v != "Not Available":
                try:
                    parsed = dateparser.parse(
                        str(v), 
                        settings={
                            'STRICT_PARSING': True,
                            'REQUIRE_PARTS': ['day', 'month', 'year'],
                            'PREFER_DAY_OF_MONTH': 'first'
                        }
                    )
                    if parsed: dates[k] = parsed.strftime("%Y-%m-%d")
                    else: dates[k] = "Not Available" # Discard partial/guessed dates
                except: pass
                
        return dates

    def _extract_legal_outcome(self, text: str) -> str:
        """Extracts the final legal outcome using targeted regex and keyword analysis."""
        # Focus on the last 3000 characters where orders/conclusions usually reside
        conclusion_text = text[-3000:] if len(text) > 3000 else text
        
        outcome_patterns = [
            (r'\b(?:Appeal|Petition|Application|Bail)\s+(?:is\s+)?allowed\b', "Allowed"),
            (r'\b(?:Appeal|Petition|Application|Bail)\s+(?:is\s+)?dismissed\b', "Dismissed"),
            (r'\b(?:Appeal|Petition|Application|Bail)\s+(?:is\s+)?rejected\b', "Rejected"),
            (r'\b(?:Bail|Relief)\s+(?:is\s+)?granted\b', "Granted"),
            (r'\b(?:Bail|Relief)\s+(?:is\s+)?refused\b', "Refused"),
            (r'\b(?:Conviction|Order)\s+(?:is\s+)?upheld\b', "Conviction Upheld"),
            (r'\b(?:Conviction|Order)\s+(?:is\s+)?set\s+aside\b', "Set Aside"),
            (r'\b(?:Accused|Petitioner)\s+(?:is\s+)?acquitted\b', "Acquitted"),
            (r'\b(?:Case|Matter)\s+(?:is\s+)?remanded\b', "Case Remanded"),
            (r'\b(?:Matter|Petition)\s+(?:is\s+)?disposed\s+of\b', "Matter Disposed"),
            (r'\b(?:Interim\s+relief|Stay)\s+(?:is\s+)?vacated\b', "Stay Vacated"),
            (r'\b(?:Cost|Penalty)\s+(?:is\s+)?imposed\b', "Penalty Imposed")
        ]

        # 1. Search for specific combinations
        for pattern, label in outcome_patterns:
            if re.search(pattern, conclusion_text, re.IGNORECASE):
                # Try to get the full phrase for context
                match = re.search(r'([A-Z][^.]*?' + pattern + r'[^.]*?\.)', conclusion_text, re.IGNORECASE)
                if match: return match.group(1).strip()
                return label

        # 2. Heuristic search for concluding keywords
        order_keywords = ["ORDER", "CONCLUSION", "HELD", "PRONOUNCED"]
        for kw in order_keywords:
            if kw in conclusion_text.upper():
                # Extract text after this keyword
                parts = re.split(kw, conclusion_text, flags=re.IGNORECASE)
                if len(parts) > 1:
                    snippet = parts[-1][:200].strip()
                    if snippet: return snippet

        return "Outcome Pending Review"

    def _fallback_regex_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback extraction using regex directly from raw text."""
        data = {
            "case_title": "", "petitioner": "Not Available", "respondent": "Not Available", "court_name": "Not Available",
            "case_type_inferred": "Legal Matter", "filing_date": "Not Available", "relief_sought": "Not Available",
            "core_legal_issue": "Not Available", "acts": [], "sections": [], "citations": [], "summary": "Not Available",
            "case_number_extracted": "Not Available", "legal_outcome": "Outcome Pending Review", "bench": "Not Available"
        }
        
        # Extract Dates Robustly
        robust_dates = self._extract_dates_robustly(text)
        data.update(robust_dates)

        # Extract Outcome
        data["legal_outcome"] = self._extract_legal_outcome(text)

        # Indian Case Patterns: W.P. No. 123 of 2023, etc.
        case_patterns = [
            r'(?:Case|W\.P\.|Crl\.A\.|O\.S\.|M\.A\.)\s*No\.?\s*([A-Z0-9\-/]+(?:\s*of\s*\d{4})?)',
            r'(?:No\.?)\s*([A-Z0-9\-/]+\s*of\s*\d{4})',
            r'([A-Z]+\s*/\s*\d+\s*/\s*\d{4})'
        ]
        for pattern in case_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["case_number_extracted"] = match.group(1).strip()
                break

        # Petitioner vs Respondent
        vs_match = re.search(r'([A-Z][^\n]+(?:vs\.?|v\.?|AND ANR|AND OTHERS)[^\n]+)', text, re.IGNORECASE)
        if vs_match:
            title_line = vs_match.group(1).strip()
            data["case_title"] = title_line
            parts = re.split(r'\b(?:vs\.?|v\.?)\b', title_line, flags=re.IGNORECASE)
            if len(parts) >= 2:
                data["petitioner"] = parts[0].strip()
                data["respondent"] = parts[1].strip()

        # Court Detection
        court_match = re.search(r'(IN THE[^\n]*COURT[^\n]*)', text, re.IGNORECASE)
        if court_match:
            data["court_name"] = court_match.group(1).strip()
        
        # Bench Detection
        bench_match = re.search(r'CORAM:\s*([^\n]+)', text, re.IGNORECASE)
        if bench_match:
            data["bench"] = bench_match.group(1).strip()

        return data




    def _robust_extract_text(self, content: bytes, file_name: str) -> tuple[str, str]:
        """Tries Fitz, then pdfplumber, then Tesseract OCR."""
        text = ""
        method = "None"
        if not file_name.lower().endswith(".pdf"):
            text = self._extract_from_image(content)
            method = "Tesseract OCR (Image)"
            return text, method

        # Stage 1: PyMuPDF (Fitz) - Fast and layout aware
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            method = "PyMuPDF"
            if len(text.strip()) > 1000:
                return text, "PyMuPDF (Fast)"
        except: pass

        # Stage 2: pdfplumber fallback (Selective - First 10 pages)
        if len(text.strip()) < 500:
            text = ""
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    pages = pdf.pages[:10] # Limit to first 10 pages
                    for page in pages:
                        text += page.extract_text() or ""
                method = "pdfplumber (Selective)"
            except: pass

        # Stage 3: OCR Fallback (First 5 pages only)
        if len(text.strip()) < 300:
            text = ""
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    pages = pdf.pages[:5] # Critical metadata is usually in first few pages
                    for page in pages:
                        img = page.to_image(resolution=150).original
                        text += pytesseract.image_to_string(img) + "\n"
                method = "Tesseract OCR (Meta-Only)"
            except: pass
            
        return text, method

    def _clean_text(self, text: str) -> str:
        """Removes headers, footers, excessive whitespace, and normalize fragments."""
        # Remove repeated whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove common court headers/footers (regex patterns)
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'Court No\..*?\n', '', text)
        return text.strip()

    def _sanitize_field(self, value: Any, field_type: str = "general") -> str:
        """Internal sanitizer to prevent raw text leakage into metadata."""
        if not value or str(value).lower() in ["none", "null", "", "nan", "not available"]:
            return "Not Available"
        
        v = str(value).strip()
        # Remove URLs and excessive noise
        v = re.sub(r'https?://\S+', '', v)
        v = re.sub(r'\s+on\s+\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^,]*\d{4}', '', v, flags=re.IGNORECASE)
        v = re.sub(r'Equivalent citations.*$', '', v, flags=re.IGNORECASE)
        v = re.sub(r'\.{3,}', '', v).strip()

        limits = {"court": 120, "case_id": 60, "party": 150, "bench": 150, "title": 200, "general": 255}
        limit = limits.get(field_type, 255)
        
        # If it's a paragraph or too long, it's invalid metadata
        if len(v) > limit or v.count('\n') > 1 or v.count('.') > 2:
            return "Not Available"
            
        triggers = ["judgment", "appeal", "section", "article", "court observed", "held"]
        if any(t in v.lower() for t in triggers) and len(v) > 50:
            return "Not Available"
            
        return v

    def _ensure_metadata_integrity(self, data: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        """Final check to prevent hallucination or empty fields."""
        if not data: data = {}
        
        # 1. Strictly Sanitize All Metadata Fields
        data["case_title"] = self._sanitize_field(data.get("case_title"), "title")
        data["case_number_extracted"] = self._sanitize_field(data.get("case_number_extracted"), "case_id")
        data["petitioner"] = self._sanitize_field(data.get("petitioner"), "party")
        data["respondent"] = self._sanitize_field(data.get("respondent"), "party")
        data["court_name"] = self._sanitize_field(data.get("court_name"), "court")
        data["bench"] = self._sanitize_field(data.get("bench"), "bench")
        
        # 2. Extract Legal Outcome if missing
        if not data.get("legal_outcome") or data.get("legal_outcome") == "Not Available" or len(str(data.get("legal_outcome"))) > 300:
            data["legal_outcome"] = self._extract_legal_outcome(raw_text)

        # 3. Ensure Summary is reasonable
        summary = data.get("summary", "")
        if not summary or "pending full summarization" in str(summary).lower() or len(str(summary)) < 30:
            data["summary"] = "Not Available"
        elif len(str(summary)) > 2000:
            data["summary"] = str(summary)[:2000] + "..."

        # 4. Standardize Case Type
        if not data.get("case_type_inferred") or data.get("case_type_inferred") == "Not Available":
             data["case_type_inferred"] = "General"

        # 5. Date Parsing & Chronological Validation
        date_fields = ["filing_date", "judgment_date", "hearing_date"]
        parsed_dates = {}
        for df in date_fields:
            d_val = data.get(df, "")
            if re.match(r'\d{4}-\d{2}-\d{2}', str(d_val)):
                try:
                    from datetime import datetime
                    parsed_dates[df] = datetime.strptime(str(d_val), "%Y-%m-%d")
                except: pass
            else:
                data[df] = "Not Available"

        # Validate: Filing Date cannot be later than Judgment Date, 
        # and cannot be unusually far earlier (> 50 years, likely a cited historical case).
        if parsed_dates.get("filing_date") and parsed_dates.get("judgment_date"):
            if parsed_dates["filing_date"] > parsed_dates["judgment_date"]:
                data["filing_date"] = "Not Available"
                print(f"Discarding invalid filing date (later than judgment): {data['filing_date']}")
            elif (parsed_dates["judgment_date"].year - parsed_dates["filing_date"].year) > 50:
                data["filing_date"] = "Not Available"
                print(f"Discarding invalid filing date (too old, >50 yrs anomaly): {data['filing_date']}")

        # Recalculate Urgency if missing or generic
        current_urgency = data.get("urgency_score", 0)
        if not current_urgency or current_urgency == 0 or current_urgency == 50:
            # Expanded heuristics for Indian Legal Context
            heuristics = {
                "death penalty": 98, "capital punishment": 98, "habeas corpus": 95,
                "bail": 85, "anticipatory bail": 88, "quashing": 75,
                "interim stay": 80, "injunction": 78, "eviction": 72,
                "senior citizen": 65, "pension": 60, "matrimonial": 55,
                "service matter": 45, "taxation": 40, "commercial": 35
            }
            score = 30 # Base score for general matters
            text_lower = raw_text.lower()
            for kw, s in heuristics.items():
                if kw in text_lower: score = max(score, s)
            
            # Boost if urgent keywords found
            if any(w in text_lower for w in ["urgent", "emergency", "immediate", "expedite"]):
                score = min(score + 10, 100)
                
            data["urgency_score"] = score

        return data


    def _extract_from_image(self, content: bytes) -> str:
        try:
            return pytesseract.image_to_string(Image.open(io.BytesIO(content)))
        except: return ""

    async def summarize_cluster(self, summaries: List[str]) -> Dict[str, Any]:
        prompt = f"Summarize these legal cases into a theme: {summaries[:5]}. Return JSON with 'label' (short name), 'reason' (description), and 'legal_tags' (list of 3 strings)."
        try:
            res = self.llm.invoke(prompt)
            res_str = res.content if hasattr(res, 'content') else str(res)
            return json.loads(res_str)
        except: return {"label": "Semantic Cluster", "reason": "Cases grouped by legal similarity.", "legal_tags": ["Legal", "Matter"]}

intelligence_engine = IntelligenceEngine()
