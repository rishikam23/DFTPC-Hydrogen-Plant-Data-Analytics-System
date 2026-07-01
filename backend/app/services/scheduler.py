from datetime import datetime, timezone, timedelta
from app.database import SessionLocal
from app.services.pap_monitor import PAPMonitor
from app.calculations import CalculationEngine
import time
import logging

logger = logging.getLogger(__name__)


def run_scheduler():
    """
    Unified Scheduler
    - KPI: once per day at 00:05
    - DSQm: every minute
    - FEPPm: once per day
    """

    last_kpi_date = None

    while True:
        db = SessionLocal()

        try:
            now = datetime.now(timezone.utc)

            # ======================================
            # DAILY KPI CALCULATION (00:05 AM)
            # ======================================

            if now.hour == 0 and now.minute == 5:
                kpi_date = (now - timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

                if last_kpi_date != kpi_date:
                    calc = CalculationEngine(db)
                    calc.calculate_daily_kpis(kpi_date)
                    last_kpi_date = kpi_date

                    logger.info(f"Daily KPI calculated for {kpi_date.date()}")

            # ======================================
            # PAP MONITORING (every minute)
            # ======================================

            monitor = PAPMonitor(db)

            # DSQm – continuous monitoring
            monitor.check_dsqm(now)
            monitor.close_dsqm_if_recovered(now)

            # FEPPm – daily check
            if now.hour == 0 and now.minute == 10:
                monitor.check_feppm(now.year, now.month)

        except Exception as e:
            logger.error(f"Scheduler error: {str(e)}")

        finally:
            db.close()

        time.sleep(60)