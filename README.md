# DFTPC (Data For Total Payment Calculations) System

## Overview
Web-based hydrogen plant monitoring system for SASREF facility. Automates data collection, KPI calculations, PAP event detection, and comprehensive reporting.

## System Architecture

### Technology Stack
- **Backend**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL 14+ with TimescaleDB
- **Frontend**: HTML5, Bootstrap 5, Chart.js
- **Task Queue**: Celery + Redis
- **Containerization**: Docker

### Key Features
1. **Real-time Dashboard** - Live KPIs, trends, alerts
2. **PAP Event Detection** - Automated penalty calculation (DSQm, FEPPm, PEPPm)
3. **Report Generation** - Daily, Monthly, Finance, Lab Analysis
4. **Manual Data Entry** - Lab analysis form with validation
5. **Role-based Access** - Operator, Engineer, Admin roles
6. **Audit Logging** - Complete traceability

## How It Works

### Data Flow
```
Third-Party DB → Data Loader → PostgreSQL → Calculation Engine → Reports
                                    ↓
                              Dashboard API ← Frontend
```

- **Calculation**: Total power consumption vs. target
- **Allowable**: ±5% band

### Report Formats

#### Daily Operations Report
- **Frequency**: Daily aggregation
- **Sections**: 
  - Plant operations (load, hours, flows)
  - Process parameters (T, P, compositions)
  - Production data (H2, recoveries)
  - Utilities (steam, BFW, power)
- **Export**: Excel, PDF
- **Source**: Tables `daily_kpis`, `process_data`

#### Lab Analysis Report
- **Manual Entry**: Operator inputs via web form
- **Components**: H2, N2, CO, CO2, CH4, C2-C5
- **Sample Points**: Sales Gas, Reformer, HPSA, MBU
- **Validation**: Range checks (0-100%), sum validation
- **Storage**: `lab_analysis` table

#### Monthly Finance Report
- **Auto-generation**: 1st of each month
- **KPIs**:
  - Total Sales Gas Energy (MMBTU)
  - Pure H2 Product (MT)
  - Power consumption (MWh)
  - NG/RFG consumption
  - Force Majeure events
- **Distribution**: Auto-email to stakeholders

#### PAP Event Summary
- **Real-time**: Updates as events detected
- **Filters**: Event type, date range, status
- **Penalties**: Calculated per contractual rates
- **Export**: Excel with event details

## Database Schema

### Core Tables

**process_data** - Time-series process measurements
- Partitioned by day for performance
- Indexed on (tag_name, timestamp)
- ~150 tags × 1440 records/day = 216K records/day

**lab_analysis** - Manual lab entries
- Foreign key to users (audit trail)
- Unique constraint on (analysis_date, sample_point, component)

**pap_events** - PAP event records
- Triggers: Database function checks on insert
- Status: ACTIVE/RESOLVED

**daily_kpis** - Aggregated daily metrics
- Materialized view refreshed at midnight
- Pre-calculated for fast reporting

**users** - Authentication
- Password: bcrypt hashed
- Roles: Operator/Engineer/Admin

## Security

### Authentication
- JWT tokens (1-hour expiry)
- Refresh tokens (7-day expiry)
- Password policy: min 8 chars, upper+lower+digit

### Authorization
- Role-based access control (RBAC)
- Endpoint decorators check permissions
- Database row-level security for multi-tenancy

### Audit Trail
- All CRUD operations logged
- User action tracking (login, data entry, config changes)
- Retention: 2 years

## Performance Optimizations

1. **TimescaleDB Hypertables** - Automatic partitioning for time-series
2. **Redis Caching** - Dashboard data cached (5-min TTL)
3. **Materialized Views** - Pre-aggregated KPIs
4. **Index Strategy** - Covering indexes on common queries
5. **Connection Pooling** - SQLAlchemy pool (max 20 connections)

## Monitoring

- **Health Endpoint**: `/api/health` - DB connectivity, Redis status
- **Metrics**: Prometheus-compatible `/metrics`
- **Logs**: Structured JSON logging to `/logs/app.log`

## Testing

```bash
# Unit tests
pytest tests/test_calculations.py -v

# Integration tests
pytest tests/test_api.py -v

# Coverage
pytest --cov=app --cov-report=html
```

## License
Internal use only - SASREF Hydrogen Plant
