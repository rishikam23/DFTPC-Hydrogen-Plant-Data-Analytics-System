from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from app.database import get_db
from app.models import DailyKPI
from app.services.kpi_service import KPIService

router = APIRouter(prefix="/api/kpi", tags=["KPI"])


@router.get("/daily")
def get_daily_kpi(
    report_date: date,
    db: Session = Depends(get_db)
):
    service = KPIService(db)

    # generate if not exists
    service.calculate_daily_kpi(report_date)

    kpi = (
        db.query(DailyKPI)
        .filter(DailyKPI.kpi_date == report_date)
        .first()
    )

    if not kpi:
        return {"message": "No data for selected date"}

    return kpi
