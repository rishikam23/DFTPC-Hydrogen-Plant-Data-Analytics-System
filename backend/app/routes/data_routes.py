from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from app.database import get_db
from app.auth import get_current_user
from app.models import ProcessData, DailyKPI
from app.schemas import ProcessDataResponse, DailyKPIResponse
from app.calculations import CalculationEngine

router = APIRouter()  # Data routes router

@router.get("/dashboard", dependencies=[Depends(get_current_user)])
def get_dashboard_data(db: Session = Depends(get_db)):
    # Get latest KPIs
    latest_kpi = db.query(DailyKPI).order_by(DailyKPI.kpi_date.desc()).first()
    
    # Get active PAP events count
    from app.models import PAPEvent
    active_events = db.query(PAPEvent).filter(PAPEvent.status == "ACTIVE").count()
    
    from app.models import LabAnalysis
    latest_h2 = db.query(LabAnalysis).filter(LabAnalysis.component == "H2").order_by(LabAnalysis.analysis_date.desc()).first()
    h2_purity = latest_h2.value_mol_percent if latest_h2 else 99.9
    
    return {
        "plant_load": latest_kpi.plant_load_percent if latest_kpi else 0,
        "h2_purity": h2_purity,
        "psa_recovery": latest_kpi.psa_recovery_percent if latest_kpi else 0,
        "power_consumption": latest_kpi.total_power_mw if latest_kpi else 0,
        "active_alarms": active_events
    }

@router.get("/trends/{tag_name}")
def get_trend_data(tag_name: str, hours: int = 24, db: Session = Depends(get_db)):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    data = db.query(ProcessData).filter(
        ProcessData.tag_name == tag_name,
        ProcessData.timestamp >= start_time,
        ProcessData.timestamp <= end_time
    ).order_by(ProcessData.timestamp).all()
    
    return {
        "timestamps": [d.timestamp.isoformat() for d in data],
        "values": [d.tag_value for d in data],
        "tag_name": tag_name,
        "unit": data[0].tag_unit if data else ""
    }