from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.case_model import Case
from datetime import datetime, timedelta
from typing import List

router = APIRouter()

@router.post("/generate")
def generate_optimized_cause_list(
    court_date: str = Query(..., description="ISO format date"),
    db: Session = Depends(get_db)
):
    """
    Generates a realistic daily cause list:
    1. Critical cases first.
    2. Batches similar clusters together.
    3. Enforces daily capacity.
    """
    # Fetch all pending cases
    cases = db.query(Case).filter(Case.status == "Pending").order_by(Case.urgency_score.desc()).all()
    
    if not cases:
        return {"message": "No cases to schedule", "total_scheduled": 0, "cause_list": []}

    cause_list = []
    current_time = datetime.strptime(f"{court_date} 09:30", "%Y-%m-%d %H:%M")
    daily_limit_minutes = 360 # 6 hours of active court time
    total_minutes = 0
    
    # Simple cluster batching logic (Group by case_type as a proxy if clusters aren't pre-computed)
    # Sort by priority first, then by type to keep clusters together
    sorted_cases = sorted(cases, key=lambda x: (x.priority_level == "Critical", x.urgency_score, x.case_type), reverse=True)

    judges = ["Hon'ble Justice A. Sharma", "Hon'ble Justice B. Verma", "Hon'ble Justice C. Gupta"]

    for i, case in enumerate(sorted_cases):
        duration = 20 # Default 20 mins
        if case.priority_level == "Critical": duration = 30
        
        if total_minutes + duration > daily_limit_minutes:
            break
            
        hearing_order = i + 1
        slot_end = current_time + timedelta(minutes=duration)
        
        cause_list.append({
            "order": hearing_order,
            "time_slot": f"{current_time.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}",
            "case_id": case.id,
            "title": case.title,
            "case_number": case.case_number,
            "priority_level": case.priority_level,
            "urgency_score": case.urgency_score,
            "estimated_duration": f"{duration} mins",
            "judge": judges[i % len(judges)],
            "cluster_tag": case.case_type
        })
        
        current_time = slot_end
        total_minutes += duration

    return {
        "date": court_date,
        "total_scheduled": len(cause_list),
        "total_time_allocated": f"{total_minutes} mins",
        "cause_list": cause_list
    }
