from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums
class UserRole(str, Enum):
    OPERATOR = "Operator"
    ENGINEER = "Engineer"
    ADMIN = "Admin"

class EventType(str, Enum):
    DSQM = "DSQm"
    FEPPM = "FEPPm"
    PEPPM = "PEPPm"
    ROGPPM = "ROGPPm"
    PACM = "PACm"

class DataQuality(str, Enum):
    GOOD = "GOOD"
    BAD = "BAD"
    UNCERTAIN = "UNCERTAIN"

# User Schemas
class UserBase(BaseModel):
    username: str
    role: UserRole

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

# Token Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# Process Data Schemas
class ProcessDataCreate(BaseModel):
    timestamp: datetime
    tag_name: str
    tag_value: float
    tag_unit: str
    data_quality: DataQuality = DataQuality.GOOD

class ProcessDataResponse(ProcessDataCreate):
    id: int
    source: str

    class Config:
        from_attributes = True

# Lab Analysis Schemas
class LabAnalysisCreate(BaseModel):
    analysis_date: datetime
    sample_point: str
    component: str
    value_mol_percent: float = Field(..., ge=0, le=100)
    tag_name: Optional[str] = None
    remarks: Optional[str] = None

    @validator('value_mol_percent')
    def validate_percentage(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Percentage must be between 0 and 100')
        return v

class LabAnalysisUpdate(BaseModel):
    value_mol_percent: Optional[float] = Field(None, ge=0, le=100)
    remarks: Optional[str] = None

class LabAnalysisResponse(BaseModel):
    """Response schema for lab analysis — does NOT inherit the strict validator from LabAnalysisCreate."""
    id: int
    analysis_date: datetime
    sample_point: str
    component: str
    value_mol_percent: float
    tag_name: Optional[str] = None
    remarks: Optional[str] = None
    entered_by: Optional[int] = None        # NULL for CSV-imported rows
    entry_timestamp: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# PAP Event Schemas
class PAPEventCreate(BaseModel):
    event_type: EventType
    start_time: datetime
    trigger_condition: str
    trigger_value: float
    threshold_value: float
    shortfall_quantity: Optional[float] = 0

class PAPEventUpdate(BaseModel):
    end_time: Optional[datetime]
    status: Optional[str]
    remarks: Optional[str]

class PAPEventResponse(BaseModel):
    id: int
    event_type: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    trigger_condition: str
    trigger_value: float
    threshold_value: float
    shortfall_quantity: Optional[float]
    penalty_amount: Optional[float]
    status: str

    class Config:
        from_attributes = True

# Daily KPI Schemas
class DailyKPIResponse(BaseModel):
    kpi_date: datetime
    plant_load_percent: Optional[float]
    operation_hours: Optional[float]
    sales_gas_flow_tday: Optional[float]
    pure_h2_product_tday: Optional[float]
    total_power_mw: Optional[float]

    class Config:
        from_attributes = True

# Report Schemas
class DailyReportRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    export_format: str = "json"  # json, excel, pdf

class MonthlyReportRequest(BaseModel):
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2020)
    export_format: str = "json"

# Dashboard Schemas
class DashboardKPI(BaseModel):
    plant_load: float
    h2_purity: float
    psa_recovery: float
    power_consumption: float
    active_alarms: int

class TrendData(BaseModel):
    timestamps: List[datetime]
    values: List[float]
    tag_name: str
    unit: str

# Health Check
class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    timestamp: datetime
