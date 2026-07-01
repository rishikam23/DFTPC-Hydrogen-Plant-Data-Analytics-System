from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import PAPEvent
from app.calculations import CalculationEngine
from config import settings
import logging

logger = logging.getLogger(__name__)


class PAPMonitor:

    def __init__(self, db: Session):
        self.db = db
        self.calc = CalculationEngine(db)

    # ======================================================
    # DSQm — Hydrogen Shortfall Event
    # ======================================================

    def check_dsqm(self, timestamp: datetime):

        pressure_tag = self.calc.get_tag_by_parameter("HMU H2 outlet pressure")
        flow_tag = self.calc.get_tag_by_parameter("HMU H2 outlet")

        pressure = self.calc.get_tag_value(pressure_tag, timestamp)
        available_h2 = self.calc.get_tag_value(flow_tag, timestamp)

        if pressure is None or available_h2 is None:
            return

        # CONTRACT VALUES
        required_h2 = settings.DSQM_REQUIRED_H2_MT_HR
        pressure_limit = settings.DSQM_PRESSURE_THRESHOLD

        if pressure >= pressure_limit:
            return

        if available_h2 >= required_h2:
            return

        # check past 15 minutes
        start_time = timestamp - timedelta(minutes=15)

        history = self.db.query(PAPEvent).filter(
            PAPEvent.event_type == "DSQm",
            PAPEvent.status == "ACTIVE"
        ).first()

        if history:
            return

        event = PAPEvent(
            event_type="DSQm",
            start_time=start_time,
            shortfall_quantity=required_h2 - available_h2,
            penalty_amount=(required_h2 - available_h2) * settings.DSQM_PENALTY_RATE,
            status="ACTIVE"
        )

        self.db.add(event)
        self.db.commit()

        logger.warning("DSQm event created")
        
    def close_dsqm_if_recovered(self, timestamp: datetime):

        active = self.db.query(PAPEvent).filter(
            PAPEvent.event_type == "DSQm",
            PAPEvent.status == "ACTIVE"
        ).first()

        if not active:
            return

        pressure_tag = self.calc.get_tag_by_parameter("HMU H2 outlet pressure")
        pressure = self.calc.get_tag_value(pressure_tag, timestamp)

        if pressure and pressure >= settings.DSQM_PRESSURE_THRESHOLD:

            active.end_time = timestamp
            active.duration_minutes = int(
                (timestamp - active.start_time).total_seconds() / 60
            )
            active.status = "CLOSED"

            self.db.commit()

            logger.info("DSQm event closed")
    
    def check_feppm(self, year: int, month: int):

        from datetime import datetime

        start_date = datetime(year, month, 1)

        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # FEEDSTOCK TAG FROM EXCEL (Previous Tag mapping)
        feedstock_tag = self.calc.get_tag_by_parameter(
            "Sales gas from battery limit"
        )

        if not feedstock_tag:
            return

        actual_feedstock = self.calc.get_tag_sum(
            feedstock_tag, start_date, end_date
        )

        if not actual_feedstock:
            return

        # TARGET FROM CONTRACT / EXCEL
        target_per_day = settings.FEPPM_TARGET_FEEDSTOCK_TDAY
        days = (end_date - start_date).days
        target_feedstock = target_per_day * days

        deviation = self.calc.calculate_feedstock_efficiency(
            actual_feedstock, target_feedstock
        )

        if deviation <= settings.FEPPM_DEVIATION_PERCENT:
            return

        penalty = self.calc.calculate_feppm_penalty(
            actual_feedstock - target_feedstock
        )

        # avoid duplicate event
        existing = self.db.query(PAPEvent).filter(
            PAPEvent.event_type == "FEPPm",
            PAPEvent.start_time == start_date
        ).first()

        if existing:
            return

        event = PAPEvent(
            event_type="FEPPm",
            start_time=start_date,
            end_time=end_date,
            duration_minutes=days * 24 * 60,
            shortfall_quantity=actual_feedstock - target_feedstock,
            penalty_amount=penalty,
            status="CLOSED",
            remarks=f"Feedstock deviation {round(deviation,2)}%"
        )

        self.db.add(event)
        self.db.commit()
