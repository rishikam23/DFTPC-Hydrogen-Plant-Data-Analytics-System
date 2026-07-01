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

### Calculation Implementations

#### 1. Plant Load
```python
Plant Load (%) = (Actual H2 Production / 10.33 MT/hr) × 100
```
- **Source**: HMU H2 outlet flow (tag: 30FQI026)
- **Update Frequency**: Real-time (1-min avg)

#### 2. Energy Rate
```python
Sales Gas Energy (MMBTU/Day) = Flow (T/Day) × HHV (BTU/nm³) × 0.001
```
- **Tags**: 60FQI001 (flow), 927QR119 (HHV)
- **Used for**: Feedstock efficiency calculation

#### 3. Pure H2 Product (NOHm)
```python
NOHm = HPSA Output + MBU Output - Recycle + Imports - Exports
```
- **Components**:
  - HPSA: 61FQI902 (purity ≥99.9%)
  - MBU: 170FQI175 (residue gas recovery)
  - Recycle: 60FQI006
  - Import: 170FQQI220

#### 4. PAP Event Detection

**DSQm (Shortfall Event)**
```python
if (H2_pressure < 22.5 barg) AND (available_h2 < required_h2):
    if duration >= 15 minutes:
        penalty = shortfall_quantity × deduction_factor
```
- **Tags**: 30PR026 (pressure), 30FQI026 (flow)
- **Evaluation**: 1-min intervals, 15-min moving average

**FEPPm (Feedstock Efficiency)**
```python
if (actual_feedstock / target_feedstock - 1) > 2.5%:
    penalty = excess_consumption × rate
```
- **Tag**: 60FQI001 (sales gas flow)
- **Evaluation**: Monthly aggregate

**PEPPm (Power Efficiency)**
```python
target_power = 0.53 MWh/MT × net_h2_output
if actual_power > target_power × 1.05:
    penalty = (actual - target) × rate
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

## Deployment

### Production Checklist
- [ ] Set strong SECRET_KEY in .env
- [ ] Configure SMTP for email reports
- [ ] Set up SSL certificates
- [ ] Configure firewall (port 8000)
- [ ] Enable database backups (daily)
- [ ] Set up monitoring (Grafana/Prometheus)

### Scaling
- Horizontal: Multiple Gunicorn workers
- Vertical: Increase PostgreSQL resources
- Caching: Redis cluster for high availability

## Troubleshooting

**Issue**: Dashboard not loading
- Check Redis: `redis-cli ping`
- Check logs: `docker-compose logs web`

**Issue**: PAP events not detecting
- Verify Celery worker: `celery -A scripts.celery_tasks inspect active`
- Check data quality in `process_data` table

**Issue**: Report generation slow
- Refresh materialized views: `REFRESH MATERIALIZED VIEW mv_daily_kpis`
- Check PostgreSQL performance: `EXPLAIN ANALYZE` on slow queries

## Support

For issues, contact: dftpc-support@example.com

## License
Internal use only - SASREF Hydrogen Plant
