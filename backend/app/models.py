from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # Operator, Engineer, Admin
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)

    # Relationships
    lab_analyses = relationship("LabAnalysis", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

class ProcessData(Base):
    __tablename__ = "process_data"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    tag_name = Column(String(100), nullable=False, index=True)
    tag_value = Column(Float)
    tag_unit = Column(String(20))
    data_quality = Column(String(20), default="GOOD")  # GOOD, BAD, UNCERTAIN
    source = Column(String(50), default="external")  # external, manual, calculated

    __table_args__ = (
        Index('idx_tag_timestamp', 'tag_name', 'timestamp'),
    )

class ProcessTag(Base):
    __tablename__ = "process_tags"

    id = Column(Integer, primary_key=True, index=True)

    parameter = Column(String(200), nullable=True)

    tag_name = Column(String(100), nullable=True)

    uom = Column(String(50), nullable=True)

class LabAnalysis(Base):
    __tablename__ = "lab_analysis"

    id = Column(Integer, primary_key=True, index=True)
    analysis_date = Column(DateTime, nullable=False, index=True)
    sample_point = Column(String(100), nullable=False)  # SalesGas, Reformer, HPSA, MBU
    component = Column(String(50), nullable=False)  # H2, N2, CO, CO2, CH4, etc.
    value_mol_percent = Column(Float, nullable=False)
    tag_name = Column(String(100))  # Reference to analyzer tag
    entered_by = Column(Integer, ForeignKey("users.id"))
    entry_timestamp = Column(DateTime, default=func.now())
    modified_at = Column(DateTime, onupdate=func.now())
    remarks = Column(Text)

    # Relationships
    user = relationship("User", back_populates="lab_analyses")

    __table_args__ = (
        Index('idx_lab_date_sample', 'analysis_date', 'sample_point'),
    )

class PAPEvent(Base):
    __tablename__ = "pap_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(20), nullable=False, index=True)  # DSQm, FEPPm, PEPPm, ROGPPm, PACm
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime)
    duration_minutes = Column(Integer)
    trigger_condition = Column(Text)
    trigger_value = Column(Float)
    threshold_value = Column(Float)
    shortfall_quantity = Column(Float)
    penalty_amount = Column(Float)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, RESOLVED, ACKNOWLEDGED
    remarks = Column(Text)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_event_time_type', 'start_time', 'event_type'),
    )

class DailyKPI(Base):
    __tablename__ = "daily_kpis"

    id = Column(Integer, primary_key=True)
    kpi_date = Column(DateTime, unique=True, nullable=False, index=True)

    # Plant Operations
    plant_load_percent = Column(Float)
    operation_hours = Column(Float)

    # Sales Gas
    sales_gas_flow_tday = Column(Float)
    sales_gas_to_feed_tday = Column(Float)
    sales_gas_to_fuel_tday = Column(Float)
    sales_gas_molecular_weight = Column(Float)
    sales_gas_hhv_btuscf = Column(Float)

    # Energy
    sales_gas_feed_energy_mmbtu = Column(Float)
    sales_gas_fuel_energy_mmbtu = Column(Float)
    total_sales_gas_energy_mmbtu = Column(Float)

    # Hydrogen Production
    hmu_h2_outlet_tday = Column(Float)
    psa_outlet_tday = Column(Float)
    mbu_residue_gas_nm3hr = Column(Float)
    pure_h2_product_tday = Column(Float)

    # Recovery
    psa_recovery_percent = Column(Float)
    mbu_recovery_percent = Column(Float)

    # Utilities
    hp_steam_export_tday = Column(Float)
    total_bfw_flow_tday = Column(Float)
    total_power_mw = Column(Float)

    # Temperatures (key points)
    smr_inlet_temp_c = Column(Float)
    smr_outlet_temp_c = Column(Float)
    methanator_inlet_temp_c = Column(Float)

    # Pressures
    h2_outlet_pressure_barg = Column(Float)

    created_at = Column(DateTime, default=func.now())

class MonthlyTotal(Base):
    __tablename__ = "monthly_totals"

    id = Column(Integer, primary_key=True)
    month_year = Column(DateTime, unique=True, nullable=False, index=True)

    # Production
    noh_mt = Column(Float)  # Net Output Hydrogen
    xoh_mt = Column(Float)  # Export Hydrogen
    toh_mt = Column(Float)  # Total Output Hydrogen

    # Energy
    af_salesgas_mmbtu = Column(Float)
    ng_consumption_mmbtu = Column(Float)
    rfg_consumption_mmbtu = Column(Float)

    # Power
    total_power_mwh = Column(Float)
    power_excludes_co2_mwh = Column(Float)

    # Utilities
    hp_steam_output_mt = Column(Float)
    total_bfw_mt = Column(Float)

    # Events
    force_majeure = Column(Boolean, default=False)
    startup_shutdown_hours = Column(Float, default=0)

    # Penalties
    total_pap_penalties = Column(Float, default=0)

    created_at = Column(DateTime, default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)  # LOGIN, DATA_ENTRY, CONFIG_CHANGE, etc.
    entity_type = Column(String(50))  # USER, LAB_ANALYSIS, PAP_EVENT, etc.
    entity_id = Column(Integer)
    old_value = Column(Text)
    new_value = Column(Text)
    ip_address = Column(String(45))

    # Relationships
    user = relationship("User", back_populates="audit_logs")

class TagMapping(Base):
    __tablename__ = "tag_mapping"

    id = Column(Integer, primary_key=True)
    tag_name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    unit = Column(String(20))
    data_type = Column(String(20))  # FLOAT, INTEGER, BOOLEAN, STRING
    normal_range_min = Column(Float)
    normal_range_max = Column(Float)
    category = Column(String(50))  # FLOW, TEMPERATURE, PRESSURE, COMPOSITION, etc.
    source_tag = Column(String(100))  # Original tag name from external system
    is_calculated = Column(Boolean, default=False)
    calculation_formula = Column(Text)