# DFTPC Hydrogen Plant Analytics System
**Exhaustive Project Documentation**

## 1. Executive Summary
The DFTPC (Data from Third Party Contractor) system is a full-stack, data-intensive web application built to monitor, analyze, and enforce the operational performance of an outsourced Hydrogen Production Plant. The system ingests raw time-series data from process tags (sensors) logged every minute, mathematically aggregates this data into daily and monthly Key Performance Indicators (KPIs), tracks manual chemical laboratory analysis, and monitors operations for contractual Performance Assessment Penalty (PAP) events. 

The application ensures that plant stakeholders can cryptographically and operationally verify whether the contractor is meeting their obligations regarding Hydrogen delivery, feedstock consumption, and power efficiency as outlined in the SASREF contract.

---

## 2. Exhaustive Technology Stack

### Backend (Core Logic & API)
*   **Language:** Python 3.12+
*   **Framework:** FastAPI
    *   Used for its immense speed (via Starlette) and automated OpenAPI (Swagger) generation. Handles asynchronous route definitions (`async def`).
*   **Data Processing:** Pandas & NumPy
    *   The `CalculationEngine` relies entirely on Pandas DataFrames to perform vectorized calculations (averaging, min/max aggregations, integrations over time) on thousands of rows of time-series sensor data from the `process_data` table.
*   **Authentication & Security:** 
    *   `python-jose` for generating and verifying JSON Web Tokens (JWT).
    *   `passlib[bcrypt]` for securely hashing user passwords before database storage.
    *   Implements the OAuth2 Password Bearer flow.
*   **Server / Runtime:** Uvicorn (ASGI web server) running locally in a Windows MSYS64 (ucrt64) environment. Standard `pip` C-extensions were avoided in favor of pre-compiled binaries via `pacman` to bypass MSYS64 compiler limitations.

### Database Layer
*   **Database:** PostgreSQL
    *   Robust relational database capable of handling large volumes of time-series tag data.
*   **ORM (Object-Relational Mapper):** SQLAlchemy
    *   Abstracts raw SQL, allowing interaction with the PostgreSQL database using Python classes. Used for all CRUD operations, including complex joins across tables.
*   **Validation:** Pydantic
    *   Defines schemas (`schemas.py`) to validate incoming POST/PUT request bodies and safely serialize outgoing database models into JSON (e.g., hiding password hashes).

### Frontend (User Interface)
*   **Templating:** Jinja2
    *   Integrated directly via FastAPI `TemplateResponse`. HTML templates are rendered server-side, meaning no separate Node.js/React build step is required.
*   **Styling:** Bootstrap 5 (via CDN)
    *   Provides utility classes (`d-flex`, `col-md-8`, `bg-primary`) to create a responsive, dark/light themed UI without writing custom CSS.
*   **Interactivity / Logic:** Vanilla JavaScript (ES6+)
    *   Embedded within the HTML templates or loaded via `static/js`. Uses the native browser `fetch()` API for asynchronous network requests.
    *   Authentication is handled by storing JWTs in `localStorage` and dynamically attaching them to the `Authorization: Bearer <token>` header of every API request.
*   **Charting:** Chart.js (via CDN)
    *   Used on the dashboard to visualize 30-day operational trends, specifically tracking Hydrogen Production vs. Power Consumption in an interactive canvas element.

---

## 3. Database Schema (SQLAlchemy Models)

Defined in `backend/app/models.py`, the database structure is highly normalized:

*   **`User`**: Stores authentication data (`username`, `hashed_password`, `role`).
*   **`ProcessData`**: The massive time-series table. Stores `tag_name` (e.g., `60FQI001`), `tag_value` (float), `data_quality` (e.g., 'GOOD'), and `timestamp`.
*   **`ProcessTag`**: The dictionary mapping. Links physical tags (`tag_name`) to human-readable names (`parameter`, e.g., 'Natural Gas Flow') and units (`uom`, e.g., 'kg/hr').
*   **`DailyKPI`**: Stores the output of the Calculation Engine for a specific day. Columns include `plant_load_percent`, `hmu_h2_outlet_tday`, `psa_recovery_percent`, `total_power_mw`, etc.
*   **`MonthlyKPI`**: Stores the monthly aggregated equivalents of the DailyKPIs.
*   **`LabAnalysis`**: Stores manual entries of chemical composition (e.g., H2 Purity %, CO ppm) tagged by `analysis_date`.
*   **`PAPEvent`**: Logs contractual violations. Tracks `event_type` (DSQm, FEPPm, etc.), `start_time`, `duration_minutes`, `shortfall_quantity`, `penalty_amount`, and `status` (ACTIVE, RESOLVED).

---

## 4. In-Depth Business Logic & Calculation Engine

Located in `backend/app/calculations.py`, the `CalculationEngine` processes raw data into actionable intelligence.

### A. Plant Capacity Constraints
The system hardcodes two distinct capacity metrics in `config.py`:
1.  **Contractual Design Capacity (`PLANT_DESIGN_CAPACITY = 10.33 MT/hr`)**: Used strictly as the baseline for performance penalties. If delivery drops below this, penalties are assessed.
2.  **Operational Max Capacity (`PLANT_MAX_CAPACITY = 13.5 MT/hr`)**: Used for operational safety and equipment stress monitoring. The UI reflects plant load against this realistic ceiling so operators don't see false "129% load" warnings.

### B. Specific Metric Calculations
*   **Plant Load %:** `(Daily Avg H2 Output / 10.33) * 100`
*   **PSA Recovery %:** `(H2 Product Out / H2 Feed In) * 100`. Measures the efficiency of the Pressure Swing Adsorption unit.
*   **Total Power Consumption:** Averages the MW readings across the day.
*   **Energy Rate:** Incorporates Higher Heating Value (HHV) formulas to convert Tonnes/Day of feed gas into MMBTU/Day.

### C. Automated PAP (Performance Assessment Penalty) Detection
The `pap_monitor.py` service scans the incoming data for strict contract violations:
*   **DSQm (Delivery Shortfall):** Triggers if H2 delivery drops below 8.5 MT/hr for >15 consecutive minutes, OR if delivery pressure drops below 22.5 barg.
*   **FEPPm (Feedstock Excess):** Triggers if feedstock consumption > 715.8 T/day + 2.5% buffer.
*   **PEPPm (Power Excess):** Triggers if power consumption > 0.53 MWh/MT of H2 + 5% buffer.
*   **ROGPPm (Refinery Off-Gas):** Assesses penalties if off-gas recovery efficiency drops.
*   **PACm (Plant Availability):** Tracks general unplanned downtime.

---

## 5. Exhaustive API Endpoint Mapping

The FastAPI backend exposes the following RESTful routes:

### Authentication (`routes/auth_routes.py`)
*   `POST /api/auth/login`: Accepts form-data (`username`, `password`). Returns `{ "access_token": "...", "token_type": "bearer" }`.

### Dashboard (`routes/dashboard_routes.py`)
*   `GET /api/dashboard/summary`: Returns the `DailyKPI` row for a requested date, calculates status colors (GREEN/AMBER/RED) based on thresholds, and counts active PAP events.
*   `GET /api/dashboard/trends`: Returns 30-day arrays of H2 output, Power, and Plant Load specifically formatted for Chart.js injection.
*   `GET /api/dashboard/latest-date`: Returns the most recent date available in the database to automatically populate calendar inputs on the UI.
*   `GET /api/dashboard/tags`: Queries `process_tags` to return all ~80 known sensors with their descriptions and units of measure.

### Reporting & Actions (`routes/report_routes.py`)
*   `GET /api/reports/daily`: Fetches the precise `DailyKPI` row for a given date.
*   `GET /api/reports/daily/export`: Streams the `DailyKPI` data as an automatically generated `.csv` file attachment.
*   `GET /api/reports/monthly`: Fetches the `MonthlyKPI` row for a given month/year.
*   `GET /api/reports/monthly/export`: Streams the `MonthlyKPI` data as a `.csv` file.
*   `GET / POST /api/reports/lab`: Fetches or creates new `LabAnalysis` entries (validating that values are between 0 and 100).
*   `GET / POST /api/reports/pap-events`: Fetches all PAP events or creates a new manual event.
*   `PATCH /api/reports/pap-events/{id}`: Used exclusively to flip an event's status from ACTIVE to RESOLVED.

---

## 6. System Architecture Map (Exhaustive Directory Structure)

```text
dftpc_project/
│
├── backend/
│   ├── main.py                  # Core execution file. Initializes FastAPI, mounts templates/static, defines HTML template routes (/, /dashboard, /daily, /pap).
│   ├── config.py                # Pydantic BaseSettings loading from `.env`. Holds hardcoded contract variables (10.33 MT/hr) and threshold limits.
│   ├── .env                     # Local environment variables (DB strings, external hosts).
│   ├── requirements.txt         # Python dependencies (fastapi, sqlalchemy, pandas, uvicorn, etc).
│   │
│   ├── app/
│   │   ├── auth.py              # JWT encoding/decoding and bcrypt password hashing.
│   │   ├── database.py          # SQLAlchemy `create_engine` and `sessionmaker`. Provides `get_db` dependency injection.
│   │   ├── models.py            # Complete PostgreSQL schema classes.
│   │   ├── schemas.py           # Pydantic schemas mapping request/response bodies (e.g., `LabAnalysisCreate`, `PAPEventResponse`).
│   │   ├── calculations.py      # The `CalculationEngine` holding all complex plant thermodynamics and contract math.
│   │   │
│   │   ├── routes/              
│   │   │   ├── auth_routes.py       
│   │   │   ├── dashboard_routes.py  
│   │   │   ├── data_routes.py       # (Legacy/System) endpoints for ingesting raw JSON sensor payloads.
│   │   │   ├── kpi_routes.py        # Endpoints to manually trigger the CalculationEngine.
│   │   │   └── report_routes.py     
│   │   │
│   │   └── services/
│   │       ├── pap_monitor.py       # Background logic scanning for contract breaches.
│   │       ├── kpi_service.py       # Orchestrator coordinating DB queries with the CalculationEngine.
│   │       └── scheduler.py         # APScheduler implementation intended to run daily/monthly calculations automatically.
│   │
│   ├── data/
│   │   ├── SASREF Data...xlsx   # The original raw export data from the plant DCS.
│   │   ├── analysis_data...csv  # Historical lab entries.
│   │   └── operational...csv    # Initial tag mappings.
│   │
│   └── scripts/                 # Crucial bootstrap and execution scripts.
│       ├── setup_db.py               # Creates all PostgreSQL tables from models.py (replaces old SQL scripts).
│       ├── seed_users.py             # Creates the initial 'admin' user with bcrypt hashed password.
│       ├── import_dcs_data.py        # Parses the massive Excel file, maps it to tags, and pumps it into the `process_data` table.
│       ├── import_analysis_csv.py    # Pumps CSV lab data into the `lab_analysis` table.
│       ├── import_tag_mapping_csv.py # Pumps CSV mapping data into `process_tags`.
│       └── run_daily_kpi.py          # CLI script to forcefully run the CalculationEngine for a specific date range.
│
├── frontend/
│   ├── static/                  
│   │   ├── css/style.css        # Custom overrides (minimal, heavily relies on Bootstrap).
│   │   └── js/dashboard.js      # Contains Chart.js logic, fetch() calls to /api/dashboard/trends, and DOM updates.
│   │
│   └── templates/               # Server-rendered HTML
│       ├── base.html             # The master shell containing the Bootstrap CDN links and global top Navbar.
│       ├── login.html            # The authentication gateway.
│       ├── dashboard.html        # The main hub featuring the 30-day Chart.js graph and Top 4 KPI summary cards.
│       ├── daily_report.html     # Shows 13+ operational metrics for a specific date with a CSV export button.
│       ├── monthly_report.html   # Shows aggregated totals (Total H2, Total Feedstock) for a specific month with CSV export.
│       ├── lab_report.html       # A table of chemical impurities and a strict entry form.
│       └── pap_events.html       # The contractual penalty management UI, split between an entry form and a status board.
│
├── .env                         # A secondary/legacy environment file from early development. 
└── README.md                    # Standard markdown summary.
```

## 7. Operational Workflow (How the App Runs)

1.  **Bootstrap:** When deployed, the database is created via `backend/scripts/setup_db.py`. The admin user is created via `seed_users.py`. Raw DCS history is bulk-loaded via `import_dcs_data.py`. Finally, `run_daily_kpi.py` is executed to aggregate all the raw data into `DailyKPI` rows so the UI has instant access to summaries without calculating them on the fly.
2.  **Server Launch:** The administrator executes `uvicorn main:app --reload` within the `backend/` directory.
3.  **Authentication Guard:** A user navigates to `http://localhost:8000/`. Because their browser's `localStorage.getItem("access_token")` is empty, JavaScript intercepts the page load and redirects them to the login screen.
4.  **Token Issuance:** The user logs in. The backend validates the hashed password and returns a JWT signed with `SECRET_KEY`.
5.  **Data Fetching:** The user navigates to the Dashboard. The embedded Vanilla JavaScript executes a `fetch()` request to `/api/dashboard/trends`, attaching the JWT.
6.  **Data Rendering:** The backend verifies the JWT. It queries the `DailyKPI` table for the last 30 days of data and returns JSON. The JavaScript passes this JSON into the `Chart.js` initialization function, rendering the graph.
7.  **CSV Export Workflow:** When a user clicks "Download CSV" on a report page, a JavaScript function fires a `fetch()` request to the backend export endpoint (with the JWT). The backend uses Pandas or standard Python `csv` tools to format the requested `DailyKPI` row into a raw string, returning it as a blob. The JavaScript generates a hidden `<a>` tag, creates an Object URL from the blob, simulates a click, and immediately removes the tag, prompting the browser's native file download dialogue.
8.  **PAP Monitoring:** As new data streams into the system (or is processed daily), the `CalculationEngine` runs its detection logic. If H2 delivery was <8.5 MT/hr, it creates a new `PAPEvent` row marked `ACTIVE`. The user sees this on the `/pap` page, investigates the physical plant issue, negotiates the penalty, and clicks "Resolve", which triggers a `PATCH` request to flip the status to `RESOLVED` in the database.
