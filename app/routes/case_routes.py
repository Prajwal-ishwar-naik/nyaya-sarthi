from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.case_model import Case
from core.engine import engine_room
from core.intelligence import intelligence_engine
from typing import List, Optional
import numpy as np

router = APIRouter()

@router.get("/")
def get_cases(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    priority_only: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Case).filter(Case.is_active == True)
    if status:
        query = query.filter(Case.status == status)
    if priority_only:
        query = query.filter(Case.urgency_score > 70)
        
    cases = query.order_by(Case.urgency_score.desc()).offset(skip).limit(limit).all()
    return cases

@router.get("/{case_id}")
def get_case_details(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id, Case.is_active == True).first()
    if not case:
        return {"error": "Case not found"}
    return case

@router.post("/cluster")
async def cluster_pending_cases(db: Session = Depends(get_db)):
    """Groups cases by existing semantic clusters or triggers a re-cluster."""
    cases = db.query(Case).filter(Case.status == "Processed", Case.is_active == True).all()
    if not cases:
        return {"message": "No cases to cluster"}

    # Group by cluster_id stored in DB
    clusters_map = {}
    for c in cases:
        cid = c.cluster_id or "UC-01"
        if cid not in clusters_map:
            clusters_map[cid] = []
        clusters_map[cid].append(c)
        
    formatted_clusters = []
    for cid, member_cases in clusters_map.items():
        case_list = []
        for c in member_cases:
            case_list.append({
                "id": c.id, 
                "case_number": c.case_number, 
                "title": c.title,
                "court": c.court_name,
                "year": c.filing_date.strftime("%Y") if c.filing_date else "N/A",
                "similarity": 85, # Mocked
                "summary": c.summary,
                "urgency": c.urgency_score,
                "priority": c.priority_level
            })
            
        formatted_clusters.append({
            "cluster_id": cid,
            "topic": member_cases[0].cluster_label or "Legal Cluster",
            "reason": "Semantically grouped by legal features.",
            "total_cases": len(member_cases),
            "cases": case_list
        })
        
    return formatted_clusters

