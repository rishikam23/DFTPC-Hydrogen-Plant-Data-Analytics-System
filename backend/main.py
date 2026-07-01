from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.routes import (
    auth_routes,
    data_routes,
    report_routes,
    lab_routes,
    dashboard_routes,
    kpi_routes,
)

from config import settings
from app.services.scheduler import run_scheduler

import threading
import time
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_DIR_LOCAL = os.path.join(PROJECT_ROOT, "frontend")   
FRONTEND_DIR_DOCKER = os.path.join(BASE_DIR, "frontend")       

FRONTEND_DIR = FRONTEND_DIR_LOCAL if os.path.isdir(FRONTEND_DIR_LOCAL) else FRONTEND_DIR_DOCKER

STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")

print(f"Frontend directory: {FRONTEND_DIR}")
print(f"Static directory exists: {os.path.exists(STATIC_DIR)}")
print(f"Templates directory exists: {os.path.exists(TEMPLATES_DIR)}")

# Scheduler startup with DB delay
def start_scheduler_with_delay():
    """
    Wait for DB container to be ready
    before starting scheduler jobs.
    """
    time.sleep(10)
    try:
        run_scheduler()
    except Exception as e:
        print(f"Scheduler failed to start: {e}")

# Lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    try:
        from app.database import init_db
        init_db()
    except Exception as e:
        print(f"DB init warning: {e}")

    threading.Thread(
        target=start_scheduler_with_delay,
        daemon=True
    ).start()

    yield

    print("Application shutdown.")

# FastAPI app init
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static + Templates
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    print(f"WARNING: Static directory not found: {STATIC_DIR}")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Routers
app.include_router(auth_routes.router,      prefix="/api/auth",      tags=["Authentication"])
app.include_router(data_routes.router,      prefix="/api/data",      tags=["Data"])
app.include_router(report_routes.router,    prefix="/api/reports",   tags=["Reports"])
app.include_router(lab_routes.router,       prefix="/api/lab",       tags=["Lab Analysis"])
app.include_router(dashboard_routes.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(kpi_routes.router)

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/daily")
async def daily_report(request: Request):
    return templates.TemplateResponse("daily_report.html", {"request": request})


@app.get("/monthly")
async def monthly_report(request: Request):
    return templates.TemplateResponse("monthly_report.html", {"request": request})


@app.get("/lab")
async def lab_report(request: Request):
    return templates.TemplateResponse("lab_report.html", {"request": request})


@app.get("/pap")
async def pap_events(request: Request):
    return templates.TemplateResponse("pap_events.html", {"request": request})


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
    }

if __name__ == "__main__":
    import uvicorn  # type: ignore

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )