import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import func
from app.database import SessionLocal
from app.models import ProcessData
from app.services.kpi_service import KPIService


def run_daily_kpi():
    db = SessionLocal()
    service = KPIService(db)

    dates = (
        db.query(func.date(ProcessData.timestamp))
        .distinct()
        .order_by(func.date(ProcessData.timestamp))
        .all()
    )

    for (report_date,) in dates:
        service.calculate_daily_kpi(report_date)

    db.close()
    print("Daily KPI generation completed successfully")


if __name__ == "__main__":
    run_daily_kpi()
