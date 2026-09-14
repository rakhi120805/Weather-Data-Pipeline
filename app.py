"""
Production Weather Data Engineering Pipeline - Web Service & API
================================================================
FastAPI application that wraps the Weather ETL Pipeline.
Provides an interactive web dashboard, on-demand pipeline execution,
health check endpoints, and REST APIs for downstream analytics.
"""

import os
import time
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, desc

from src.config import config
from src.database import db_manager, WeatherData
from src.pipeline import WeatherETLPipeline
from src.logger import logger

app = FastAPI(
    title="Weather Data Engineering Pipeline API",
    description="Automated ETL Data Pipeline (Bronze -> Silver -> Gold) with Real-Time Analytics and Power BI Integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for flexible dashboard and client integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure database tables exist at application startup
@app.on_event("startup")
async def startup_event():
    try:
        db_manager.init_db()
        logger.info("FastAPI startup: Database schema verified.")
        
        # Check if database is empty. If so, seed initial data in background
        session = db_manager.get_session()
        count = session.query(WeatherData).count()
        session.close()
        
        if count == 0:
            logger.info("Database is empty. Triggering initial ETL run in background...")
            asyncio.create_task(run_pipeline_async())
    except Exception as e:
        logger.error(f"FastAPI startup error: {e}")


async def run_pipeline_async() -> Dict[str, Any]:
    """Runs the ETL pipeline asynchronously without blocking the web event loop."""
    start_time = time.time()
    pipeline = WeatherETLPipeline()
    success = await asyncio.to_thread(pipeline.run)
    elapsed = round(time.time() - start_time, 2)
    return {
        "success": success,
        "elapsed_seconds": elapsed,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }


# =====================================================================
# REST API Endpoints
# =====================================================================

@app.get("/health", summary="Health Check for Render & Monitoring")
def health_check():
    """Returns service health status and database connectivity."""
    try:
        session = db_manager.get_session()
        record_count = session.query(WeatherData).count()
        session.close()
        return {
            "status": "healthy",
            "service": "weather-data-pipeline",
            "database": "connected",
            "total_records": record_count,
            "cities_monitored": config.cities,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "database_error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@app.post("/api/pipeline/run", summary="Trigger ETL Pipeline (POST)")
async def trigger_pipeline_post():
    """Executes extraction, validation, transformation, and database loading."""
    result = await run_pipeline_async()
    return result


@app.get("/api/pipeline/run", summary="Trigger ETL Pipeline (GET shortcut)")
async def trigger_pipeline_get():
    """Convenience endpoint to trigger pipeline run directly from browser."""
    result = await run_pipeline_async()
    return result


@app.get("/api/weather/latest", summary="Get Latest Weather for All Cities")
def get_latest_weather():
    """Returns the most recent observation for each configured city."""
    session = db_manager.get_session()
    try:
        latest_records = []
        for city in config.cities:
            rec = session.query(WeatherData).filter(
                WeatherData.city.ilike(city)
            ).order_by(desc(WeatherData.timestamp)).first()
            
            if rec:
                latest_records.append({
                    "id": rec.id,
                    "city": rec.city,
                    "country": rec.country,
                    "latitude": rec.latitude,
                    "longitude": rec.longitude,
                    "temperature": rec.temperature,
                    "feels_like": rec.feels_like,
                    "humidity": rec.humidity,
                    "pressure": rec.pressure,
                    "wind_speed": rec.wind_speed,
                    "visibility": rec.visibility,
                    "weather": rec.weather,
                    "description": rec.description,
                    "cloudiness": rec.cloudiness,
                    "temp_category": rec.temp_category,
                    "humidity_category": rec.humidity_category,
                    "wind_category": rec.wind_category,
                    "timestamp": rec.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                })
        return {
            "count": len(latest_records),
            "records": latest_records
        }
    finally:
        session.close()


@app.get("/api/analytics", summary="Aggregated Analytical Metrics")
def get_analytics():
    """Provides aggregated weather analytics matching sql/analytics.sql."""
    session = db_manager.get_session()
    try:
        total_obs = session.query(WeatherData).count()
        if total_obs == 0:
            return {"total_observations": 0, "message": "No data yet. Trigger the pipeline first."}

        # Temperature statistics
        stats = session.query(
            func.avg(WeatherData.temperature).label("avg_temp"),
            func.max(WeatherData.temperature).label("max_temp"),
            func.min(WeatherData.temperature).label("min_temp"),
            func.avg(WeatherData.humidity).label("avg_humidity"),
            func.avg(WeatherData.wind_speed).label("avg_wind_speed")
        ).first()

        # City breakdown
        city_rows = session.query(
            WeatherData.city,
            WeatherData.country,
            func.round(func.avg(WeatherData.temperature), 2).label("avg_temp"),
            func.round(func.avg(WeatherData.humidity), 1).label("avg_humidity"),
            func.round(func.avg(WeatherData.wind_speed), 2).label("avg_wind"),
            func.count(WeatherData.id).label("observations")
        ).group_by(WeatherData.city, WeatherData.country).order_by(desc("avg_temp")).all()

        # Weather condition breakdown
        cond_rows = session.query(
            WeatherData.weather,
            func.count(WeatherData.id).label("count")
        ).group_by(WeatherData.weather).order_by(desc("count")).all()

        # Category breakdowns
        temp_cats = session.query(
            WeatherData.temp_category,
            func.count(WeatherData.id).label("count")
        ).group_by(WeatherData.temp_category).all()

        return {
            "summary": {
                "total_observations": total_obs,
                "avg_temperature_c": round(float(stats.avg_temp or 0), 2),
                "max_temperature_c": round(float(stats.max_temp or 0), 2),
                "min_temperature_c": round(float(stats.min_temp or 0), 2),
                "avg_humidity_pct": round(float(stats.avg_humidity or 0), 1),
                "avg_wind_speed_ms": round(float(stats.avg_wind_speed or 0), 2),
            },
            "by_city": [
                {
                    "city": r.city,
                    "country": r.country,
                    "avg_temp_c": float(r.avg_temp),
                    "avg_humidity_pct": float(r.avg_humidity),
                    "avg_wind_speed_ms": float(r.avg_wind),
                    "observations": r.observations
                }
                for r in city_rows
            ],
            "conditions": [
                {"weather": r.weather, "count": r.count, "percentage": round((r.count / total_obs) * 100, 1)}
                for r in cond_rows
            ],
            "temp_categories": {r.temp_category: r.count for r in temp_cats}
        }
    finally:
        session.close()


@app.get("/api/weather/history", summary="Recent Observations History")
def get_history(
    city: Optional[str] = Query(None, description="Filter by city name"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return")
):
    """Returns historical observations ordered by timestamp descending."""
    session = db_manager.get_session()
    try:
        query = session.query(WeatherData)
        if city:
            query = query.filter(WeatherData.city.ilike(city))
        records = query.order_by(desc(WeatherData.timestamp)).limit(limit).all()
        return [
            {
                "id": r.id,
                "city": r.city,
                "country": r.country,
                "temperature": r.temperature,
                "feels_like": r.feels_like,
                "humidity": r.humidity,
                "pressure": r.pressure,
                "wind_speed": r.wind_speed,
                "weather": r.weather,
                "description": r.description,
                "temp_category": r.temp_category,
                "humidity_category": r.humidity_category,
                "wind_category": r.wind_category,
                "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
            for r in records
        ]
    finally:
        session.close()


# =====================================================================
# Interactive Web Dashboard (GET /)
# =====================================================================

@app.get("/", response_class=HTMLResponse, summary="Interactive Control Center Dashboard")
def serve_dashboard():
    """Serves a sleek, modern, glassmorphic dark-mode web dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weather Data Engineering Pipeline | Control Center</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #090d16;
            --bg-card: rgba(18, 26, 43, 0.75);
            --bg-card-hover: rgba(26, 38, 64, 0.9);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-highlight: rgba(56, 189, 248, 0.3);
            --accent-cyan: #38bdf8;
            --accent-blue: #6366f1;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(56, 189, 248, 0.07) 0%, transparent 40%),
                radial-gradient(circle at 85% 85%, rgba(99, 102, 241, 0.07) 0%, transparent 40%);
            background-attachment: fixed;
        }

        header {
            border-bottom: 1px solid var(--border-color);
            background: rgba(9, 13, 22, 0.85);
            backdrop-filter: blur(16px);
            position: sticky;
            top: 0;
            z-index: 50;
            padding: 1.25rem 2rem;
        }

        .header-container {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }

        .logo-icon {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            box-shadow: 0 4px 20px rgba(56, 189, 248, 0.35);
        }

        .brand-title {
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(to right, #ffffff, #93c5fd);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-subtitle {
            font-size: 0.75rem;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.25rem 0.65rem;
            border-radius: 9999px;
            font-size: 0.72rem;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.12);
            color: var(--accent-emerald);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .pulse-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: var(--accent-emerald);
            box-shadow: 0 0 10px var(--accent-emerald);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
        }

        .nav-actions {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.6rem 1.1rem;
            border-radius: 10px;
            font-size: 0.85rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
        }

        .btn-outline {
            background: rgba(255, 255, 255, 0.04);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }

        .btn-outline:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: var(--border-highlight);
            transform: translateY(-1px);
        }

        .btn-primary {
            background: linear-gradient(135deg, #0284c7, #4f46e5);
            color: #ffffff;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
        }

        .btn-primary:hover {
            box-shadow: 0 6px 20px rgba(2, 132, 199, 0.5);
            transform: translateY(-1px);
        }

        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        main {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
            flex: 1;
            width: 100%;
        }

        /* Banner Notification */
        #alert-box {
            display: none;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            font-size: 0.9rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            animation: fadeIn 0.3s ease;
        }

        .alert-success {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.35);
            color: #6ee7b7;
        }

        .alert-info {
            background: rgba(56, 189, 248, 0.15);
            border: 1px solid rgba(56, 189, 248, 0.35);
            color: #bae6fd;
        }

        /* KPI Section */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2.5rem;
        }

        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.4rem;
            backdrop-filter: blur(12px);
            transition: all 0.25s ease;
            position: relative;
            overflow: hidden;
        }

        .kpi-card:hover {
            border-color: var(--border-highlight);
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
        }

        .kpi-title {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            font-weight: 600;
            margin-bottom: 0.6rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .kpi-value {
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            color: #ffffff;
        }

        .kpi-sub {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.3rem;
        }

        /* Architecture Flow Ribbon */
        .architecture-ribbon {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1rem 1.5rem;
            margin-bottom: 2.5rem;
            display: flex;
            align-items: center;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 1rem;
            font-size: 0.85rem;
        }

        .arch-step {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            color: var(--text-secondary);
        }

        .arch-badge {
            width: 26px;
            height: 26px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.72rem;
            font-weight: 700;
        }

        .badge-bronze { background: #b45309; color: #fef3c7; }
        .badge-silver { background: #64748b; color: #f1f5f9; }
        .badge-gold { background: #eab308; color: #422006; }
        .badge-app { background: #0284c7; color: #ffffff; }

        .arch-arrow {
            color: var(--text-muted);
            font-weight: 700;
        }

        /* Section Headings */
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 1.25rem;
        }

        .section-title {
            font-size: 1.35rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        .section-desc {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        /* City Grid */
        .city-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }

        .city-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 18px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            transition: all 0.25s ease;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .city-card:hover {
            background: var(--bg-card-hover);
            border-color: var(--border-highlight);
            transform: translateY(-3px);
            box-shadow: 0 12px 28px rgba(0, 0, 0, 0.4);
        }

        .city-head {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .city-name {
            font-size: 1.35rem;
            font-weight: 700;
            color: #ffffff;
        }

        .city-country {
            font-size: 0.75rem;
            padding: 0.15rem 0.5rem;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-secondary);
            font-weight: 600;
            margin-left: 0.4rem;
        }

        .weather-emoji {
            font-size: 2rem;
        }

        .temp-row {
            display: flex;
            align-items: baseline;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }

        .current-temp {
            font-size: 2.5rem;
            font-weight: 800;
            letter-spacing: -0.04em;
        }

        .feels-like {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .weather-condition {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--accent-cyan);
            text-transform: capitalize;
            margin-bottom: 1rem;
        }

        .tag-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-bottom: 1.25rem;
        }

        .pill-tag {
            font-size: 0.7rem;
            font-weight: 600;
            padding: 0.2rem 0.55rem;
            border-radius: 6px;
        }

        .tag-cold { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
        .tag-warm { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
        .tag-hot { background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }
        .tag-category { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3); }

        .metrics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
            border-top: 1px solid var(--border-color);
            padding-top: 1rem;
            margin-bottom: 1rem;
        }

        .metric-item {
            display: flex;
            flex-direction: column;
        }

        .metric-label {
            font-size: 0.72rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .metric-value {
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .card-footer {
            font-size: 0.72rem;
            color: var(--text-muted);
            border-top: 1px solid rgba(255, 255, 255, 0.04);
            padding-top: 0.75rem;
            display: flex;
            justify-content: space-between;
        }

        footer {
            border-top: 1px solid var(--border-color);
            padding: 1.75rem 2rem;
            background: rgba(9, 13, 22, 0.95);
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        .footer-container {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .footer-links {
            display: flex;
            gap: 1.25rem;
        }

        .footer-links a {
            color: var(--text-secondary);
            text-decoration: none;
            transition: color 0.2s ease;
        }

        .footer-links a:hover {
            color: var(--accent-cyan);
        }

        .spinner {
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-left-color: #ffffff;
            border-radius: 50%;
            width: 16px;
            height: 16px;
            animation: spin 0.8s linear infinite;
            display: none;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-6px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>

    <header>
        <div class="header-container">
            <div class="brand">
                <div class="logo-icon">⛅</div>
                <div>
                    <h1 class="brand-title">Weather Data Pipeline</h1>
                    <div class="brand-subtitle">
                        <span>Production Medallion ETL Architecture</span>
                        <div class="status-pill">
                            <div class="pulse-dot"></div>
                            <span>ONLINE</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="nav-actions">
                <a href="/docs" target="_blank" class="btn btn-outline">
                    <span>📖 API Docs</span>
                </a>
                <a href="/api/analytics" target="_blank" class="btn btn-outline">
                    <span>📊 Analytics JSON</span>
                </a>
                <button id="run-btn" class="btn btn-primary" onclick="triggerPipeline()">
                    <div class="spinner" id="btn-spinner"></div>
                    <span id="btn-text">⚡ Run Pipeline Now</span>
                </button>
            </div>
        </div>
    </header>

    <main>
        <div id="alert-box" class="alert-info">
            <span id="alert-msg">Pipeline initialized. Ready to trigger data refreshes.</span>
            <button onclick="document.getElementById('alert-box').style.display='none'" style="background:none; border:none; color:inherit; cursor:pointer; font-size:1.1rem;">&times;</button>
        </div>

        <!-- Architecture Banner -->
        <div class="architecture-ribbon">
            <div class="arch-step">
                <div class="arch-badge badge-bronze">1</div>
                <div><strong>Bronze Layer:</strong> Raw API JSONs (data/raw/)</div>
            </div>
            <div class="arch-arrow">➔</div>
            <div class="arch-step">
                <div class="arch-badge badge-silver">2</div>
                <div><strong>Silver Layer:</strong> Cleaned & Categorized CSVs</div>
            </div>
            <div class="arch-arrow">➔</div>
            <div class="arch-step">
                <div class="arch-badge badge-gold">3</div>
                <div><strong>Gold Layer:</strong> Deduplicated SQL Database</div>
            </div>
            <div class="arch-arrow">➔</div>
            <div class="arch-step">
                <div class="arch-badge badge-app">4</div>
                <div><strong>FastAPI & Power BI:</strong> Real-Time Dashboards</div>
            </div>
        </div>

        <!-- KPIs -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">
                    <span>Total Observations</span>
                    <span>📦</span>
                </div>
                <div class="kpi-value" id="kpi-total">--</div>
                <div class="kpi-sub">Records in SQL Gold Layer</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">
                    <span>Average Temp</span>
                    <span>🌡️</span>
                </div>
                <div class="kpi-value" id="kpi-avg-temp">--°C</div>
                <div class="kpi-sub">Across all monitored cities</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">
                    <span>Max Temperature</span>
                    <span>🔥</span>
                </div>
                <div class="kpi-value" id="kpi-max-temp">--°C</div>
                <div class="kpi-sub">Highest recorded peak</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">
                    <span>Average Humidity</span>
                    <span>💧</span>
                </div>
                <div class="kpi-value" id="kpi-avg-humidity">--%</div>
                <div class="kpi-sub">Global relative humidity</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">
                    <span>Average Wind</span>
                    <span>💨</span>
                </div>
                <div class="kpi-value" id="kpi-avg-wind">-- m/s</div>
                <div class="kpi-sub">Wind velocity index</div>
            </div>
        </div>

        <!-- City Live Weather Cards -->
        <div class="section-header">
            <div>
                <h2 class="section-title">Live Monitored Cities</h2>
                <div class="section-desc">Real-time metrics ingested, validated, and normalized from OpenWeather</div>
            </div>
        </div>

        <div class="city-grid" id="city-container">
            <!-- Populated dynamically via JS -->
            <div style="color: var(--text-muted); padding: 2rem;">Loading weather metrics...</div>
        </div>
    </main>

    <footer>
        <div class="footer-container">
            <div>
                Built for High-Reliability Data Ingestion • OpenWeather ETL Architecture
            </div>
            <div class="footer-links">
                <a href="/health" target="_blank">Health Check</a>
                <a href="/docs" target="_blank">Swagger Docs</a>
                <a href="/api/weather/latest" target="_blank">Latest API</a>
                <a href="https://github.com" target="_blank">GitHub</a>
            </div>
        </div>
    </footer>

    <script>
        function getWeatherEmoji(condition) {
            const cond = (condition || '').toLowerCase();
            if (cond.includes('clear')) return '☀️';
            if (cond.includes('cloud')) return '⛅';
            if (cond.includes('rain')) return '🌧️';
            if (cond.includes('snow')) return '❄️';
            if (cond.includes('thunder')) return '⛈️';
            if (cond.includes('mist') || cond.includes('fog')) return '🌫️';
            return '🌡️';
        }

        async function fetchAnalytics() {
            try {
                const res = await fetch('/api/analytics');
                const data = await res.json();
                if (data.summary) {
                    document.getElementById('kpi-total').innerText = data.summary.total_observations.toLocaleString();
                    document.getElementById('kpi-avg-temp').innerText = data.summary.avg_temperature_c + '°C';
                    document.getElementById('kpi-max-temp').innerText = data.summary.max_temperature_c + '°C';
                    document.getElementById('kpi-avg-humidity').innerText = data.summary.avg_humidity_pct + '%';
                    document.getElementById('kpi-avg-wind').innerText = data.summary.avg_wind_speed_ms + ' m/s';
                }
            } catch (err) {
                console.error('Failed to load analytics:', err);
            }
        }

        async function fetchLatestWeather() {
            try {
                const res = await fetch('/api/weather/latest');
                const data = await res.json();
                const container = document.getElementById('city-container');
                
                if (!data.records || data.records.length === 0) {
                    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-secondary);">
                        No weather records currently in the database. Click <strong>"⚡ Run Pipeline Now"</strong> above to trigger the initial ETL run!
                    </div>`;
                    return;
                }

                container.innerHTML = data.records.map(rec => {
                    const emoji = getWeatherEmoji(rec.weather);
                    const tempClass = rec.temp_category === 'Cold' ? 'tag-cold' : (rec.temp_category === 'Hot' ? 'tag-hot' : 'tag-warm');
                    
                    return `
                        <div class="city-card">
                            <div>
                                <div class="city-head">
                                    <div>
                                        <span class="city-name">${rec.city}</span>
                                        <span class="city-country">${rec.country}</span>
                                    </div>
                                    <div class="weather-emoji">${emoji}</div>
                                </div>
                                <div class="temp-row">
                                    <span class="current-temp">${rec.temperature}°C</span>
                                    <span class="feels-like">Feels like ${rec.feels_like}°C</span>
                                </div>
                                <div class="weather-condition">${rec.description}</div>
                                <div class="tag-row">
                                    <span class="pill-tag ${tempClass}">${rec.temp_category}</span>
                                    <span class="pill-tag tag-category">${rec.humidity_category}</span>
                                    <span class="pill-tag tag-category">${rec.wind_category}</span>
                                </div>
                                <div class="metrics-grid">
                                    <div class="metric-item">
                                        <span class="metric-label">Humidity</span>
                                        <span class="metric-value">${rec.humidity}%</span>
                                    </div>
                                    <div class="metric-item">
                                        <span class="metric-label">Wind Speed</span>
                                        <span class="metric-value">${rec.wind_speed} m/s</span>
                                    </div>
                                    <div class="metric-item">
                                        <span class="metric-label">Pressure</span>
                                        <span class="metric-value">${rec.pressure} hPa</span>
                                    </div>
                                    <div class="metric-item">
                                        <span class="metric-label">Visibility</span>
                                        <span class="metric-value">${(rec.visibility / 1000).toFixed(1)} km</span>
                                    </div>
                                </div>
                            </div>
                            <div class="card-footer">
                                <span>Observed: ${rec.timestamp}</span>
                                <span>lat/lon: ${rec.latitude}, ${rec.longitude}</span>
                            </div>
                        </div>
                    `;
                }).join('');

            } catch (err) {
                console.error('Failed to load latest weather:', err);
            }
        }

        async function triggerPipeline() {
            const btn = document.getElementById('run-btn');
            const spinner = document.getElementById('btn-spinner');
            const btnText = document.getElementById('btn-text');
            const alertBox = document.getElementById('alert-box');
            const alertMsg = document.getElementById('alert-msg');

            btn.disabled = true;
            spinner.style.display = 'inline-block';
            btnText.innerText = 'Running ETL Pipeline...';

            alertBox.style.display = 'flex';
            alertBox.className = 'alert-info';
            alertMsg.innerText = 'Extracting live weather data, validating schemas, transforming units, and loading to database...';

            try {
                const res = await fetch('/api/pipeline/run', { method: 'POST' });
                const result = await res.json();

                if (result.success) {
                    alertBox.className = 'alert-success';
                    alertMsg.innerText = `Pipeline executed successfully in ${result.elapsed_seconds}s! Database updated with latest observations.`;
                } else {
                    alertBox.className = 'alert-info';
                    alertMsg.innerText = `Pipeline run finished in ${result.elapsed_seconds}s.`;
                }

                // Refresh cards and KPIs
                await fetchAnalytics();
                await fetchLatestWeather();

            } catch (err) {
                alertBox.className = 'alert-info';
                alertMsg.innerText = 'Pipeline triggered. Refreshing data...';
                await fetchAnalytics();
                await fetchLatestWeather();
            } finally {
                btn.disabled = false;
                spinner.style.display = 'none';
                btnText.innerText = '⚡ Run Pipeline Now';
            }
        }

        // Initial Load
        fetchAnalytics();
        fetchLatestWeather();
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server directly on port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
