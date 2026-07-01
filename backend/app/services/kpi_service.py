from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.models import ProcessData, DailyKPI, TagMapping


class KPIService:

    def __init__(self, db: Session):
        self.db = db

    def calculate_daily_kpi(self, report_date: date):
        from app.calculations import CalculationEngine
        from datetime import datetime

        # prevent duplicate generation
        existing = (
            self.db.query(DailyKPI)
            .filter(DailyKPI.kpi_date == report_date)
            .first()
        )

        if existing:
            return existing

        calc = CalculationEngine(self.db)
        dt = datetime.combine(report_date, datetime.min.time())
        return calc.calculate_daily_kpis(dt)