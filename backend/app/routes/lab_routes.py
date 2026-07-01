from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import LabAnalysis, User, PAPEvent
from app.schemas import LabAnalysisCreate, LabAnalysisResponse, LabAnalysisUpdate
from app.calculations import CalculationEngine

router = APIRouter()

@router.post("/", response_model=LabAnalysisResponse)
def create_lab_analysis(
    analysis: LabAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Operator", "Engineer", "Admin"]))
):
    # Check for duplicate entry
    existing = db.query(LabAnalysis).filter(
        LabAnalysis.analysis_date == analysis.analysis_date,
        LabAnalysis.sample_point == analysis.sample_point,
        LabAnalysis.component == analysis.component
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Entry already exists for this date/sample/component")

    db_analysis = LabAnalysis(
        **analysis.dict(),
        entered_by=current_user.id
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)
    return db_analysis

@router.get("/", response_model=List[LabAnalysisResponse])
def get_lab_analyses(
    date: datetime = None,
    sample_point: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(LabAnalysis)
    if date:
        query = query.filter(LabAnalysis.analysis_date == date)
    if sample_point:
        query = query.filter(LabAnalysis.sample_point == sample_point)
    return query.order_by(LabAnalysis.analysis_date.desc()).limit(500).all()

@router.put("/{analysis_id}", response_model=LabAnalysisResponse)
def update_lab_analysis(
    analysis_id: int,
    analysis: LabAnalysisUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Engineer", "Admin"]))
):
    db_analysis = db.query(LabAnalysis).filter(LabAnalysis.id == analysis_id).first()
    if not db_analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    for key, value in analysis.dict(exclude_unset=True).items():
        setattr(db_analysis, key, value)

    db.commit()
    db.refresh(db_analysis)
    return db_analysis

@router.post("/run-pap-check")
def run_pap_check(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["Engineer", "Admin"]))
):
    """Manually trigger a PAP event check"""
    from app.services.pap_monitor import PAPMonitor
    monitor = PAPMonitor(db)
    now = datetime.utcnow()
    monitor.check_dsqm(now)
    return {"checked_at": now.isoformat(), "message": "PAP check completed"}