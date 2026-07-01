"""
Calculation Engine for DFTPC System
Implements KPI calculations and PAP event logic
Based strictly on SASREF Excel (Previous Tag driven)
"""

from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import ProcessData, PAPEvent, DailyKPI, ProcessTag
from config import settings
import logging

logger = logging.getLogger(__name__)  # Calculation Engine logger


class CalculationEngine:

    def __init__(self, db: Session):
        self.db = db
        self.design_capacity = settings.PLANT_DESIGN_CAPACITY  # MT/hr

    # ==========================================================
    # TAG HELPERS (PREVIOUS TAG ONLY)
    # ==========================================================

    def get_tag_by_parameter(self, parameter_name: str) -> Optional[str]:
        tag = (
            self.db.query(ProcessTag)
            .filter(ProcessTag.parameter == parameter_name)
            .first()
        )
        return tag.tag_name if tag else None

    def get_tag_average(self, tag_name, start, end):
        if not tag_name:
            return None

        value = (
            self.db.query(func.avg(ProcessData.tag_value))
            .filter(
                ProcessData.tag_name == tag_name,
                ProcessData.timestamp >= start,
                ProcessData.timestamp < end,
                ProcessData.data_quality == "GOOD"
            )
            .scalar()
        )

        return float(value) if value is not None else None

    def get_tag_value(self, tag_name, timestamp):
        if not tag_name:
            return None

        row = (
            self.db.query(ProcessData)
            .filter(
                ProcessData.tag_name == tag_name,
                ProcessData.timestamp == timestamp,
                ProcessData.data_quality == "GOOD"
            )
            .first()
        )
        return row.tag_value if row else None

    # ==========================================================
    # KPI FORMULAS
    # ==========================================================

    def calculate_plant_load(self, h2_mt_hr: float) -> float:
        if self.design_capacity == 0:
            return 0
        return (h2_mt_hr / self.design_capacity) * 100

    def calculate_energy_rate(self, flow_tday: float, hhv: float) -> float:
        return flow_tday * hhv * 0.001

    def calculate_psa_recovery(self, outlet: float, inlet: float) -> float:
        if not inlet:
            return 0
        return (outlet / inlet) * 100

    def calculate_feedstock_efficiency(self, actual: float, target: float) -> float:
        if not target:
            return 0
        return ((actual / target) - 1) * 100

    def calculate_power_efficiency(self, power: float, h2: float) -> float:
        if not h2:
            return 0
        return power / h2

    # ==========================================================
    # DAILY KPI CALCULATION
    # ==========================================================

    def calculate_daily_kpis(self, date: datetime) -> DailyKPI:

        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        # EXTEND window for timezone mismatch
        start = start - timedelta(hours=6)
        end = end + timedelta(hours=6)


        # -------- TAG MAPPING FROM EXCEL --------

        sales_gas = self.get_tag_by_parameter("Sales gas from battery limit")
        sales_feed = self.get_tag_by_parameter("Sales gas to feed")
        sales_fuel = self.get_tag_by_parameter("Sales gas to fuel")

        hmu_h2 = self.get_tag_by_parameter("HMU H2 outlet")
        psa_outlet = self.get_tag_by_parameter("PSA outlet")
        psa_inlet = self.get_tag_by_parameter("PSA inlet flow")
        h2_pressure = self.get_tag_by_parameter("HMU H2 outlet pressure")

        power_tag = self.get_tag_by_parameter("Electricity excluding K-6006")
        steam_tag = self.get_tag_by_parameter("HP Steam Export")
        bfw_tag = self.get_tag_by_parameter("Total BFW flow")
        smr_inlet = self.get_tag_by_parameter("SMR Inlet Temperature")
        smr_outlet = self.get_tag_by_parameter("SMR Outlet Temperature")
        methanator_inlet = self.get_tag_by_parameter("Methanator Inlet Temperature")

        raw_psa_outlet = self.get_tag_average(psa_outlet, start, end)
        psa_outlet_tday = raw_psa_outlet * 0.00215712 if raw_psa_outlet is not None else None

        kpi = {
            "kpi_date": start,
            "operation_hours": 24.0,

            "sales_gas_flow_tday": self.get_tag_average(sales_gas, start, end),
            "sales_gas_to_feed_tday": self.get_tag_average(sales_feed, start, end),
            "sales_gas_to_fuel_tday": self.get_tag_average(sales_fuel, start, end),

            "hmu_h2_outlet_tday": self.get_tag_average(hmu_h2, start, end),
            "psa_outlet_tday": psa_outlet_tday,
            "h2_outlet_pressure_barg": self.get_tag_average(h2_pressure, start, end),

            "total_power_mw": self.get_tag_average(power_tag, start, end),
            "hp_steam_export_tday": self.get_tag_average(steam_tag, start, end),
            "total_bfw_flow_tday": self.get_tag_average(bfw_tag, start, end),

            "smr_inlet_temp_c": self.get_tag_average(smr_inlet, start, end),
            "smr_outlet_temp_c": self.get_tag_average(smr_outlet, start, end),
            "methanator_inlet_temp_c": self.get_tag_average(methanator_inlet, start, end),
        }

        # -------- DERIVED KPIs --------

        if kpi["hmu_h2_outlet_tday"] is not None:
            h2_mt_hr = kpi["hmu_h2_outlet_tday"] / 24
            kpi["plant_load_percent"] = self.calculate_plant_load(h2_mt_hr)

        if kpi["sales_gas_flow_tday"] is not None:
            hhv = 35799.45
            kpi["sales_gas_feed_energy_mmbtu"] = self.calculate_energy_rate(
                kpi["sales_gas_flow_tday"], hhv
            )

        psa_in_avg = self.get_tag_average(psa_inlet, start, end)
        if kpi["psa_outlet_tday"] is not None and psa_in_avg:
            kpi["psa_recovery_percent"] = self.calculate_psa_recovery(
                kpi["psa_outlet_tday"], psa_in_avg
            )

        existing = (
            self.db.query(DailyKPI)
            .filter(DailyKPI.kpi_date == start)
            .first()
        )

        if existing:
            for k, v in kpi.items():
                if v is not None:
                    setattr(existing, k, v)
            self.db.commit()
            return existing

        record = DailyKPI(**kpi)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
    
    def evaluate_kpi_status(self, daily: DailyKPI) -> dict:
        status = {}

        # Plant Load
        if daily.plant_load_percent is not None:
            if daily.plant_load_percent >= 95:
                status["plant_load"] = "GREEN"
            elif daily.plant_load_percent >= 90:
                status["plant_load"] = "AMBER"
            else:
                status["plant_load"] = "RED"
                
        # PSA Recovery
        if daily.psa_recovery_percent is not None:
            if daily.psa_recovery_percent >= 85:
                status["psa_recovery"] = "GREEN"
            elif daily.psa_recovery_percent >= 80:
                status["psa_recovery"] = "AMBER"
            else:
                status["psa_recovery"] = "RED"

        # Power efficiency
        if daily.total_power_mw and daily.hmu_h2_outlet_tday:
            efficiency = daily.total_power_mw / daily.hmu_h2_outlet_tday
            if efficiency <= 0.53:
                status["power_efficiency"] = "GREEN"
            elif efficiency <= 0.56:
                status["power_efficiency"] = "AMBER"
            else:
                status["power_efficiency"] = "RED"

        # H2 pressure
        if daily.h2_outlet_pressure_barg is not None:
            if daily.h2_outlet_pressure_barg >= 22.5:
                status["h2_pressure"] = "GREEN"
            elif daily.h2_outlet_pressure_barg >= 21:
                status["h2_pressure"] = "AMBER"
            else:
                status["h2_pressure"] = "RED"

        return status


    # ==========================================================
    # MONTHLY REPORT
    # ==========================================================

    def generate_monthly_report(self, year: int, month: int):

        start = datetime(year, month, 1, tzinfo=timezone.utc)

        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        records = (
            self.db.query(DailyKPI)
            .filter(
                DailyKPI.kpi_date >= start,
                DailyKPI.kpi_date < end
            )
            .all()
        )

        if not records:
            return {"message": "No data available"}

        total_h2 = sum(r.hmu_h2_outlet_tday or 0 for r in records)
        total_power = sum(r.total_power_mw or 0 for r in records)
        total_feed = sum(r.sales_gas_flow_tday or 0 for r in records)
        total_steam = sum(r.hp_steam_export_tday or 0 for r in records)
        total_bfw = sum(r.total_bfw_flow_tday or 0 for r in records)

        avg_load = sum(r.plant_load_percent or 0 for r in records) / len(records)

        return {
            "month": month,
            "year": year,
            "total_h2_production_mt": round(total_h2, 2),
            "average_plant_load_percent": round(avg_load, 2),
            "total_feedstock_tday": round(total_feed, 2),
            "total_power_mwh": round(total_power, 2),
            "total_hp_steam_tday": round(total_steam, 2),
            "total_bfw_tday": round(total_bfw, 2),
            "status": "Monthly report generated successfully"
        }

    # ==========================================================
    # PAP SUMMARY
    # ==========================================================

    def get_pap_event_summary(self, start_date, end_date):

        events = self.db.query(PAPEvent).filter(
            PAPEvent.start_time >= start_date,
            PAPEvent.start_time <= end_date
        ).all()

        summary = {
            "DSQm": [],
            "FEPPm": [],
            "PEPPm": [],
            "total_penalty": 0
        }

        for e in events:
            summary[e.event_type].append({
                "id": e.id,
                "start_time": e.start_time,
                "end_time": e.end_time,
                "duration_minutes": e.duration_minutes,
                "shortfall_quantity": e.shortfall_quantity,
                "penalty_amount": e.penalty_amount,
                "status": e.status
            })

            if e.penalty_amount:
                summary["total_penalty"] += e.penalty_amount

        summary["total_penalty"] = round(summary["total_penalty"], 2)
        return summary

    def get_tag_sum(self, tag_name: str, start: datetime, end: datetime) -> Optional[float]:
        if not tag_name:
            return None
        value = (
            self.db.query(func.sum(ProcessData.tag_value))
            .filter(
                ProcessData.tag_name == tag_name,
                ProcessData.timestamp >= start,
                ProcessData.timestamp < end,
                ProcessData.data_quality == "GOOD"
            )
            .scalar()
        )
        return float(value) if value is not None else None

    def calculate_dsqm_penalty(self, shortfall_mt: float) -> float:
        return shortfall_mt * settings.DSQM_PENALTY_RATE

    def calculate_feppm_penalty(self, excess_feedstock: float) -> float:
        return excess_feedstock * 50.0

    def calculate_peppm_penalty(self, excess_power: float) -> float:
        return excess_power * 75.0

    def detect_feppm_event(self, actual_feedstock: float, target_feedstock: float) -> tuple[bool, dict]:
        if not target_feedstock:
            return False, {}
        deviation = ((actual_feedstock / target_feedstock) - 1) * 100
        is_event = deviation > settings.FEPPM_DEVIATION_PERCENT
        event_data = {}
        if is_event:
            excess = actual_feedstock - target_feedstock
            penalty = self.calculate_feppm_penalty(excess)
            event_data = {
                "deviation_percent": deviation,
                "excess_quantity": excess,
                "penalty_amount": penalty
            }
        return is_event, event_data

    def detect_peppm_event(self, actual_power: float, h2_output: float) -> tuple[bool, dict]:
        target_power = settings.PEPPM_TARGET_MWH_PER_MT * h2_output
        upper_limit = target_power * (1 + settings.PEPPM_ALLOWABLE_DEVIATION)
        is_event = actual_power > upper_limit
        event_data = {}
        if is_event:
            excess = actual_power - target_power
            penalty = self.calculate_peppm_penalty(excess)
            event_data = {
                "excess_power": excess,
                "penalty_amount": penalty
            }
        return is_event, event_data