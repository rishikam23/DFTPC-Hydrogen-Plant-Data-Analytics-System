from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, date
import csv
import io

from app.database import get_db
from app.auth import get_current_user, require_role
from app.calculations import CalculationEngine
from app.models import PAPEvent, DailyKPI
from config import settings

router = APIRouter(tags=["Reports"])

# =============================================================
# DAILY REPORT
# =============================================================

@router.get("/daily")
def get_daily_report(
    report_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Daily Operations KPI Report"""

    engine = CalculationEngine(db)
    kpi = engine.calculate_daily_kpis(
        datetime.combine(report_date, datetime.min.time())
    )

    if not kpi:
        raise HTTPException(status_code=404, detail="No data found for this date")

    status = engine.evaluate_kpi_status(kpi)

    # Operational load % = production vs sustained operational ceiling
    h2_mt_hr = (kpi.hmu_h2_outlet_tday or 0) / 24
    operational_load_percent = (
        (h2_mt_hr / settings.PLANT_MAX_CAPACITY) * 100
        if settings.PLANT_MAX_CAPACITY > 0 else None
    )

    return {
        "status": "success",
        "report_date": report_date,
        "data": {
            "plant_load_percent": kpi.plant_load_percent,          # vs PAP contract minimum (10.33 MT/hr)
            "operational_load_percent": round(operational_load_percent, 2) if operational_load_percent else None,  # vs operational max (13.5 MT/hr)
            "operation_hours": kpi.operation_hours,
            "sales_gas_flow_tday": kpi.sales_gas_flow_tday,
            "sales_gas_to_feed_tday": kpi.sales_gas_to_feed_tday,
            "sales_gas_to_fuel_tday": kpi.sales_gas_to_fuel_tday,
            "sales_gas_feed_energy_mmbtu": kpi.sales_gas_feed_energy_mmbtu,
            "hmu_h2_outlet_tday": kpi.hmu_h2_outlet_tday,
            "psa_outlet_tday": kpi.psa_outlet_tday,
            "psa_recovery_percent": kpi.psa_recovery_percent,
            "h2_outlet_pressure_barg": kpi.h2_outlet_pressure_barg,
            "total_power_mw": kpi.total_power_mw,
            "hp_steam_export_tday": kpi.hp_steam_export_tday,
            "total_bfw_flow_tday": kpi.total_bfw_flow_tday,
            "smr_inlet_temp_c": kpi.smr_inlet_temp_c,
            "smr_outlet_temp_c": kpi.smr_outlet_temp_c,
        },
        "kpi_status": status
    }


# =============================================================
# DAILY REPORT — CSV EXPORT
# =============================================================

@router.get("/daily/export")
def export_daily_report_csv(
    report_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Download Daily Operations KPI Report as CSV"""

    engine = CalculationEngine(db)
    kpi = engine.calculate_daily_kpis(
        datetime.combine(report_date, datetime.min.time())
    )

    if not kpi:
        raise HTTPException(status_code=404, detail="No data found for this date")

    status = engine.evaluate_kpi_status(kpi)
    h2_mt_hr = (kpi.hmu_h2_outlet_tday or 0) / 24
    operational_load = (
        round((h2_mt_hr / settings.PLANT_MAX_CAPACITY) * 100, 2)
        if settings.PLANT_MAX_CAPACITY > 0 else ""
    )

    def fmt(v):
        return round(v, 4) if v is not None else ""

    rows = [
        ["SASREF Hydrogen Plant — Daily Operations Report"],
        ["Date", str(report_date)],
        ["Generated", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
        [],
        ["Parameter", "Value", "Unit", "Status"],
        ["Plant Load (vs PAP Contract Min)", fmt(kpi.plant_load_percent), "%", status.get("plant_load", "")],
        ["Plant Load (vs Operational Max)", operational_load, "%", ""],
        ["Operation Hours", fmt(kpi.operation_hours), "hrs", ""],
        ["H2 Production (HMU Outlet)", fmt(kpi.hmu_h2_outlet_tday), "T/day", ""],
        ["PSA Outlet Flow", fmt(kpi.psa_outlet_tday), "T/day", ""],
        ["PSA Recovery", fmt(kpi.psa_recovery_percent), "%", status.get("psa_recovery", "")],
        ["Power Consumption", fmt(kpi.total_power_mw), "MW", status.get("power_efficiency", "")],
        ["Sales Gas to Feed", fmt(kpi.sales_gas_to_feed_tday), "T/day", ""],
        ["Sales Gas to Fuel", fmt(kpi.sales_gas_to_fuel_tday), "T/day", ""],
        ["Sales Gas Flow", fmt(kpi.sales_gas_flow_tday), "T/day", ""],
        ["HP Steam Export", fmt(kpi.hp_steam_export_tday), "T/day", ""],
        ["BFW Consumption", fmt(kpi.total_bfw_flow_tday), "T/day", ""],
        ["H2 Outlet Pressure", fmt(kpi.h2_outlet_pressure_barg), "barg", status.get("h2_pressure", "")],
        ["SMR Inlet Temperature", fmt(kpi.smr_inlet_temp_c), "°C", ""],
        ["SMR Outlet Temperature", fmt(kpi.smr_outlet_temp_c), "°C", ""],
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    output.seek(0)

    filename = f"daily_report_{report_date}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# =============================================================
# MONTHLY REPORT
# =============================================================

@router.get("/monthly")
def get_monthly_report(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["Engineer", "Admin"]))
):
    """Monthly Performance Summary"""

    engine = CalculationEngine(db)
    report = engine.generate_monthly_report(year, month)

    return {
        "status": "success",
        "year": year,
        "month": month,
        "data": report
    }


# =============================================================
# MONTHLY REPORT — CSV EXPORT
# =============================================================

@router.get("/monthly/export")
def export_monthly_report_csv(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["Engineer", "Admin"]))
):
    """Download Monthly Performance Summary as CSV"""

    engine = CalculationEngine(db)
    report = engine.generate_monthly_report(year, month)

    if "message" in report and report["message"] == "No data available":
        raise HTTPException(status_code=404, detail="No data available for this month")

    import calendar
    month_name = calendar.month_name[month]

    def fmt(v):
        return round(v, 4) if v is not None else ""

    rows = [
        ["SASREF Hydrogen Plant — Monthly Performance Summary"],
        ["Period", f"{month_name} {year}"],
        ["Generated", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
        [],
        ["Parameter", "Value", "Unit"],
        ["Total H2 Production", fmt(report.get("total_h2_production_mt")), "MT"],
        ["Average Plant Load (vs Contract Min)", fmt(report.get("average_plant_load_percent")), "%"],
        ["Total Feedstock Used", fmt(report.get("total_feedstock_tday")), "T"],
        ["Total Power Consumption", fmt(report.get("total_power_mwh")), "MWh"],
        ["Total HP Steam Export", fmt(report.get("total_hp_steam_tday")), "T"],
        ["Total BFW Consumption", fmt(report.get("total_bfw_tday")), "T"],
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    output.seek(0)

    filename = f"monthly_report_{year}_{month:02d}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# =============================================================
# PAP EVENTS — GET ALL
# =============================================================

@router.get("/pap-events")
def get_pap_events(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get all PAP events ordered by start time descending"""
    events = db.query(PAPEvent).order_by(PAPEvent.start_time.desc()).limit(200).all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "start_time": e.start_time.isoformat() if e.start_time else None,
            "end_time": e.end_time.isoformat() if e.end_time else None,
            "duration_minutes": e.duration_minutes,
            "trigger_condition": e.trigger_condition,
            "trigger_value": e.trigger_value,
            "threshold_value": e.threshold_value,
            "shortfall_quantity": e.shortfall_quantity,
            "penalty_amount": e.penalty_amount,
            "status": e.status,
            "remarks": e.remarks,
        }
        for e in events
    ]


# =============================================================
# PAP EVENTS — CREATE
# =============================================================

@router.post("/pap-events")
def create_pap_event(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["Engineer", "Admin"]))
):
    """Manually create a PAP event"""

    # Parse datetimes
    def parse_dt(s):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None

    start = parse_dt(payload.get("start_time"))
    end = parse_dt(payload.get("end_time"))

    if not start:
        raise HTTPException(status_code=400, detail="start_time is required")

    duration = None
    if start and end:
        duration = int((end - start).total_seconds() / 60)

    event = PAPEvent(
        event_type=payload.get("event_type", "DSQm"),
        start_time=start,
        end_time=end,
        duration_minutes=duration,
        trigger_condition=payload.get("trigger_condition", ""),
        trigger_value=float(payload.get("trigger_value", 0) or 0),
        threshold_value=float(payload.get("threshold_value", 0) or 0),
        shortfall_quantity=float(payload.get("shortfall_quantity", 0) or 0),
        penalty_amount=float(payload.get("penalty_amount", 0) or 0),
        status=payload.get("status", "ACTIVE"),
        remarks=payload.get("remarks", ""),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return {
        "id": event.id,
        "message": "PAP event created successfully",
        "event_type": event.event_type,
        "status": event.status,
        "duration_minutes": event.duration_minutes,
        "penalty_amount": event.penalty_amount,
    }


# =============================================================
# PAP EVENTS — UPDATE STATUS
# =============================================================

@router.patch("/pap-events/{event_id}")
def update_pap_event_status(
    event_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["Engineer", "Admin"]))
):
    """Update PAP event status or remarks"""
    event = db.query(PAPEvent).filter(PAPEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if "status" in payload:
        event.status = payload["status"]
    if "remarks" in payload:
        event.remarks = payload["remarks"]

    db.commit()
    return {"id": event.id, "status": event.status, "message": "Updated"}


# =============================================================
# PAP SUMMARY REPORT (existing)
# =============================================================

@router.get("/pap-summary")
def get_pap_summary(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["Engineer", "Admin"]))
):
    """PAP Events Summary Report"""

    engine = CalculationEngine(db)
    summary = engine.get_pap_event_summary(
        datetime.combine(start_date, datetime.min.time()),
        datetime.combine(end_date, datetime.min.time())
    )

    return {
        "status": "success",
        "from": start_date,
        "to": end_date,
        "data": summary
    }