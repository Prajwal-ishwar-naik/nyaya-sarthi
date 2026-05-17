from typing import Dict, Any, List
import re

class AnalyticsEngine:
    def __init__(self):
        # Weighted Priority Formula
        self.weights = {
            "urgency": 0.60,       # Life, Liberty, Emergency
            "backlog": 0.30,       # Age, Inactivity
            "humanitarian": 0.10   # Senior citizens, vulnerable groups
        }

    def calculate_priority_score(self, metadata: Dict[str, Any], raw_text: str = "") -> Dict[str, Any]:
        """
        Final Priority Score = 0.60*Urgency + 0.30*Backlog + 0.10*Humanitarian
        """
        # 1. Urgency Score (0-100)
        # Often pre-calculated by LLM, but we verify with heuristics
        u_val = metadata.get("urgency_score", 30)
        try:
            # Extract digits if it's a string like "Score 85" or "85%"
            if isinstance(u_val, str):
                nums = re.findall(r'\d+', u_val)
                urgency_score = float(nums[0]) if nums else 30.0
            else:
                urgency_score = float(u_val)
        except:
            urgency_score = 30.0
        
        # 2. Backlog Score (0-100)
        backlog_score = self.compute_backlog_score(metadata)
        
        # 3. Humanitarian Boost
        h_boost = 0
        h_indicators = ["senior citizen", "child", "disabled", "poverty", "legal aid"]
        for ind in h_indicators:
            if ind in str(metadata).lower() or ind in raw_text.lower():
                h_boost = min(h_boost + 20, 100)

        # Final Score
        final_score = (
            (urgency_score * self.weights["urgency"]) +
            (backlog_score * self.weights["backlog"]) +
            (h_boost * self.weights["humanitarian"])
        )
        
        # Cap at 100
        final_score = round(min(final_score, 100), 2)

        # Categorization
        if final_score >= 90: level = "Critical"
        elif final_score >= 70: level = "High"
        elif final_score >= 40: level = "Medium"
        else: level = "Low"

        return {
            "score": final_score,
            "level": level,
            "urgency": urgency_score,
            "backlog": backlog_score,
            "humanitarian_boost": h_boost,
            "explanation": self.generate_explanation(metadata, final_score, level, urgency_score, h_boost)
        }

    def compute_backlog_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate backlog score based on age and inactivity."""
        age_days = metadata.get("case_age_days", 0)
        inactivity_days = metadata.get("inactivity_days", 0)
        adjournments = metadata.get("adjournment_count", 0)

        # Age component (max 50 points if case > 5 years)
        age_score = min((age_days / (365 * 5)) * 50, 50)
        
        # Inactivity component (max 30 points if > 1 year)
        inactivity_score = min((inactivity_days / 365) * 30, 30)
        
        # Adjournment penalty (max 20 points)
        adjournment_score = min(adjournments * 5, 20)

        return round(age_score + inactivity_score + adjournment_score, 2)

    def generate_explanation(self, metadata: Dict[str, Any], final_score: float, level: str, urgency: float, h_boost: float) -> str:
        """Generates a human-readable reason for the priority."""
        # Use LLM reasoning if available and high quality
        llm_reasoning = metadata.get("priority_reasoning_summary")
        if llm_reasoning and len(llm_reasoning) > 20:
            return llm_reasoning

        reasons = []
        if urgency > 80:
            reasons.append("Critical urgency due to immediate legal/humanitarian threat.")
        elif urgency > 50:
            reasons.append("High urgency identified from case content.")
            
        if h_boost > 0:
            reasons.append("Priority boost for humanitarian/vulnerability factors.")
            
        if metadata.get("case_age_days", 0) > 365 * 3:
            reasons.append(f"Significant backlog delay ({metadata.get('case_age_days') // 365} years).")

        if not reasons:
            reasons.append("Standard priority based on baseline case features.")

        return " ".join(reasons)

    def evaluate_humanitarian(self, data: Dict[str, Any]) -> bool:
        indicators = ["bail", "detention", "senior citizen", "medical", "domestic violence", "custody", "rape", "sexual", "child"]
        text = str(data).lower()
        return any(ind in text for ind in indicators)

analytics_engine = AnalyticsEngine()


analytics_engine = AnalyticsEngine()
