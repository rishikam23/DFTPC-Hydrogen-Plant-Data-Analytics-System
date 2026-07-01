from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import timedelta, date, datetime, timezone

from app.database import get_db
from app.auth import get_current_user
from app.calculations import CalculationEngine
from app.models import DailyKPI, PAPEvent, ProcessTag

router = APIRouter(tags=["Dashboard"])


@router.get("/summary")
def dashboard_summary(
    report_date: date,
    db: Session = Depends(get_db),
):
    """Get KPI summary for a specific date"""
    calc = CalculationEngine(db)

    # Calculate (or retrieve cached) KPIs for the date
    dt = datetime.combine(report_date, datetime.min.time())
    calc.calculate_daily_kpis(dt)

    daily = (
        db.query(DailyKPI)
        .filter(DailyKPI.kpi_date >= dt)
        .filter(DailyKPI.kpi_date < dt + timedelta(days=1))
        .first()
    )

    if not daily:
        return {
            "date": str(report_date),
            "message": "No KPI data available for this date"
        }

    pap_events = db.query(PAPEvent).filter(
        PAPEvent.status == "ACTIVE"
    ).count()

    status = calc.evaluate_kpi_status(daily)

    return {
        "date": str(report_date),
        "plant_load_percent": daily.plant_load_percent,
        "h2_production_tday": daily.hmu_h2_outlet_tday,
        "psa_recovery_percent": daily.psa_recovery_percent,
        "total_power_mw": daily.total_power_mw,
        "hp_steam_export_tday": daily.hp_steam_export_tday,
        "h2_outlet_pressure_barg": daily.h2_outlet_pressure_barg,
        "sales_gas_flow_tday": daily.sales_gas_flow_tday,
        "active_pap_events": pap_events,
        "status": status
    }


@router.get("/trends")
def dashboard_trends(
    db: Session = Depends(get_db),
):
    """Get 7-day trend data for H2 production and power"""
    latest_kpi = db.query(DailyKPI).order_by(DailyKPI.kpi_date.desc()).first()
    if latest_kpi:
        end_date = latest_kpi.kpi_date
    else:
        end_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    start_date = end_date - timedelta(days=29)  # last 30 days

    records = (
        db.query(DailyKPI)
        .filter(
            DailyKPI.kpi_date >= start_date,
            DailyKPI.kpi_date <= end_date
        )
        .order_by(DailyKPI.kpi_date)
        .all()
    )

    return {
        "dates": [r.kpi_date.strftime("%d-%b") for r in records],
        "h2": [round(r.hmu_h2_outlet_tday or 0, 2) for r in records],
        "power": [round(r.total_power_mw or 0, 2) for r in records],
        "plant_load": [round(r.plant_load_percent or 0, 2) for r in records],
    }


@router.get("/latest-date")
def get_latest_date(db: Session = Depends(get_db)):
    """Get the most recent date that has KPI data"""
    latest = db.query(DailyKPI).order_by(DailyKPI.kpi_date.desc()).first()
    if not latest:
        return {"latest_date": None}
    return {"latest_date": latest.kpi_date.strftime("%Y-%m-%d")}

@router.get("/tags")
def get_all_tags(db: Session = Depends(get_db)):
    """Get all process tags with descriptions and units"""
    tags = db.query(ProcessTag).order_by(ProcessTag.parameter).all()
    return [
        {
            "tag_name": t.tag_name,
            "description": t.parameter,
            "unit": t.uom
        }
        for t in tags if t.tag_name
    ]