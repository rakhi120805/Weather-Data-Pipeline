# Production-Style Weather Data Engineering Pipeline

[![Live Demo on Render](https://img.shields.io/badge/Render-Live%20Demo-brightgreen?style=for-the-badge&logo=render)](https://weather-data-pipeline-yjfs.onrender.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi)](https://weather-data-pipeline-yjfs.onrender.com/docs)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker)](https://www.docker.com/)

An end-to-end, production-grade ETL (Extract, Transform, Load) data engineering pipeline that pulls real-time weather metrics from the OpenWeather API, validates structural schemas and physical boundaries, transforms data (Kelvin to Celsius, timestamp formatting, feature engineering), and loads the results into a relational database (PostgreSQL / SQLite).

Includes a **FastAPI web service**, an **interactive glassmorphic dark-mode dashboard**, on-demand pipeline execution triggers, REST APIs, and automated scheduling.

🌐 **Live Application URL:** [https://weather-data-pipeline-yjfs.onrender.com](https://weather-data-pipeline-yjfs.onrender.com)  
📖 **Interactive Swagger API Docs:** [https://weather-data-pipeline-yjfs.onrender.com/docs](https://weather-data-pipeline-yjfs.onrender.com/docs)

---

## 1. Project Architecture

The pipeline implements a modular ETL architecture following the industry-standard **Medallion (Bronze -> Silver -> Gold)** pattern:

```text
OpenWeather API (or Mock Mode)
       ↓
[EXTRACT STAGE] (Fetch JSON payloads for configured cities with exponential backoff)
       ↓
  Bronze Layer  (data/raw/ - Storing raw JSON files as single source of truth)
       ↓
[VALIDATE STAGE] (QA validation checking schemas, ranges, and duplicates)
       ↓
[TRANSFORM STAGE] (Normalization, Kelvin-to-Celsius, Date formatting, Feature Engineering)
       ↓
  Silver Layer  (data/processed/ - Cleaned DataFrame exported as CSV)
       ↓
  [LOAD STAGE]  (Database Ingestion: checking duplicates and bulk-saving ORM objects)
       ↓
   Gold Layer   (Relational DB: PostgreSQL / SQLite with unique constraints)
       ↓
FastAPI Web Dashboard & Power BI Analytical Reports
```

---

## 2. Project Folder Structure

```text
Weather-Data-Pipeline/
├── data/
│   ├── raw/                 # Bronze Layer: raw unmodified API JSON files
│   └── processed/           # Silver Layer: cleaned, transformed tabular CSV files
│
├── logs/
│   └── pipeline.log         # Rotating execution log file (max 5MB, 3 backups)
│
├── dashboard/
│   └── README.md            # Power BI connection guidelines and DAX measures
│
├── dags/
│   └── weather_dag.py       # Apache Airflow hourly DAG orchestration
│
├── sql/
│   ├── create_tables.sql    # DDL schema definition script
│   └── analytics.sql        # Analytical reporting and aggregation queries
│
├── src/
│   ├── app.py               # FastAPI application & embedded web dashboard
│   ├── config.py            # Environment configuration parser (auto-detects DATABASE_URL)
│   ├── logger.py            # Logger initialization (Stream & Rotating File handlers)
│   ├── extract.py           # API data fetcher with retry loop and mock mode
│   ├── validate.py          # Data quality checks for schema structure and ranges
│   ├── transform.py         # Unit converters, derived categories, and CSV saving
│   ├── database.py          # SQLAlchemy ORM model mappings and SessionManager
│   ├── load.py              # Deduplicated bulk save data loader
│   └── pipeline.py          # ETL Main Orchestrator CLI entrypoint
│
├── main.py                  # Web application entrypoint for local execution
├── app.py                   # Root ASGI export for PaaS platforms
├── Procfile                 # Process configuration for Render web services
├── render.yaml              # Render blueprint deployment specification
├── Dockerfile               # Production container image definition
├── docker-compose.yml       # Multi-container setup with PostgreSQL
├── docker-entrypoint.sh     # Container startup script with DB health check
├── requirements.txt         # Python library dependencies
├── .env.example             # Template for configuration settings
└── .gitignore               # Excludes virtual envs, secrets, raw data, and logs
```

---

## 3. Database Schema

The relational database layer is created using the following DDL script (`sql/create_tables.sql`):

```sql
CREATE TABLE IF NOT EXISTS weather_data (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(10) NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    temperature REAL NOT NULL,
    feels_like REAL NOT NULL,
    humidity INTEGER NOT NULL,
    pressure INTEGER NOT NULL,
    wind_speed REAL NOT NULL,
    visibility INTEGER NOT NULL,
    weather VARCHAR(50) NOT NULL,
    description VARCHAR(255) NOT NULL,
    cloudiness INTEGER NOT NULL,
    sunrise TIMESTAMP NOT NULL,
    sunset TIMESTAMP NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- Feature engineered derived columns
    temp_category VARCHAR(10) NOT NULL,
    humidity_category VARCHAR(15) NOT NULL,
    wind_category VARCHAR(10) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_city_timestamp UNIQUE (city, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_weather_city_timestamp ON weather_data (city, timestamp);
```

---

## 4. REST API Endpoints

The deployed service provides full REST endpoints for integration with external dashboards, data lakes, or monitoring tools:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Interactive glassmorphic dark-mode web control center |
| `GET` | `/health` | Health check (reports database connection and record count) |
| `POST` | `/api/pipeline/run` | Triggers the ETL pipeline asynchronously and refreshes data |
| `GET` | `/api/weather/latest` | Returns the most recent observations for all configured cities |
| `GET` | `/api/analytics` | Summary metrics: averages, min/max, condition & category breakdowns |
| `GET` | `/api/weather/history` | Historical observations (supports `?city=London&limit=50`) |
| `GET` | `/docs` | Interactive Swagger UI API documentation |
| `GET` | `/redoc` | ReDoc API documentation |

---

## 5. Installation & Getting Started

### Prerequisites
* Python 3.11+
* Git
* (Optional) PostgreSQL database (otherwise defaults to SQLite file database automatically).

### Step 1: Clone and Set Up Workspace
```bash
git clone https://github.com/rakhi120805/Weather-Data-Pipeline.git
cd Weather-Data-Pipeline
```

### Step 2: Initialize Virtual Environment
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On Linux/macOS
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Settings
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Inside `.env`:
* Enter your `OPENWEATHER_API_KEY` (sign up at [openweathermap.org](https://openweathermap.org/) to get one).
* *Note*: If you leave the default placeholder API key, the pipeline automatically toggles **MOCK Mode**, generating realistic weather observations for testing.
* Set `DB_TYPE=sqlite` for zero-setup local database, or `DB_TYPE=postgresql` to load into a real PostgreSQL server.

---

## 6. Running Locally

### Option A: Run the Web Dashboard & API (Recommended)
```bash
uvicorn src.app:app --reload --host 127.0.0.1 --port 8000
# Or:
python main.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to access the control center.

### Option B: Run the CLI Batch Pipeline
```bash
python -m src.pipeline
```

### Option C: Run with Docker Compose
To spin up a local PostgreSQL database container and the pipeline:
```bash
docker compose up --build
```

---

## 7. Deploying to Render

This repository is pre-configured with a `render.yaml` blueprint and a `Procfile` for one-click deployment on [Render](https://render.com):

1. Create a new **Web Service** on Render and connect this GitHub repository.
2. Configure settings:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn src.app:app --host 0.0.0.0 --port $PORT`
3. Environment Variables (optional):
   - `OPENWEATHER_API_KEY`: *(Your API key, or omit for mock mode)*
   - `CITIES`: `New York,London,Tokyo,Delhi,Sydney,Paris,Cairo`
   - `DB_TYPE`: `sqlite` *(or connect a Render PostgreSQL database)*
4. Once deployed, your web application will be live at your designated `.onrender.com` URL.

---

## 8. Analytical SQL Queries

Sample queries are located in [`sql/analytics.sql`](sql/analytics.sql):
* **Temperature Statistics:** Average, maximum, and minimum temperatures per city.
* **City Humidity Rankings:** Identify the most humid locations.
* **Wind & Condition Distribution:** Classify wind velocities and weather occurrences.
* **Daily & Monthly Trends:** Time-series aggregations grouped by calendar intervals.
