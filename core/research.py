import httpx
import json
import os
from typing import List, Dict, Any
from app.config import settings
from core.engine import engine_room

class LegalResearchEngine:
    """
    Handles retrieval of legal precedents and external knowledge.
    Integrates with ChromaDB and (optionally) external Legal APIs.
    """
    
    def __init__(self):
        self.indian_kanoon_base_url = "https://indiankanoon.org/api/"
        # In a real scenario, an API key would be required.
        self.api_key = os.getenv("INDIAN_KANOON_API_KEY", "")

    async def get_context(self, case_text: str) -> str:
        """
        Combines local vector search with external legal knowledge.
        """
        # 1. Local Vector Search (RAG)
        local_results = engine_room.search_similar(case_text[:1000], limit=3)
        
        context = "### Local Judicial Precedents (from Database):\n"
        if local_results and local_results.get("documents"):
            for i, doc in enumerate(local_results["documents"][0]):
                meta = local_results["metadatas"][0][i]
                context += f"- [{meta.get('case_title')}] {doc[:400]}...\n"
        else:
            context += "No direct local precedents found.\n"
            
        # 2. Simulated External Legal Knowledge (Indian Kanoon / eCourts)
        # In a real implementation, this would be an async HTTP call.
        context += "\n### Relevant Statutes & External Legal Knowledge:\n"
        context += self._get_simulated_external_knowledge(case_text)
        
        return context

    def _get_simulated_external_knowledge(self, text: str) -> str:
        """
        Heuristic-based legal knowledge retrieval (to be replaced by real API calls).
        """
        text = text.lower()
        knowledge = ""
        
        if "bail" in text:
            knowledge += "- Section 437/439 CrPC: Provisions for bail in non-bailable offences.\n"
            knowledge += "- State of Rajasthan v. Balchand (1977): 'Bail is the rule, Jail is the exception'.\n"
        
        if "domestic violence" in text:
            knowledge += "- Protection of Women from Domestic Violence Act, 2005 (PWDVA).\n"
            knowledge += "- Lalita Toppo v. State of Jharkhand (2018): Maintenance under PWDVA.\n"
            
        if "habeas corpus" in text:
            knowledge += "- Article 226/32 of the Constitution of India.\n"
            knowledge += "- ADM Jabalpur v. Shivkant Shukla (Overruled by KS Puttaswamy).\n"

        if not knowledge:
            knowledge = "- Generic legal principles under IPC, CrPC, and Indian Evidence Act apply.\n"
            
        return knowledge

legal_research = LegalResearchEngine()
