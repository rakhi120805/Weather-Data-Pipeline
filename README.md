# Production-Style Weather Data Engineering Pipeline

An end-to-end, robust ETL (Extract, Transform, Load) data engineering pipeline that pulls real-time weather metrics from the OpenWeather API, validates structural schemas and logical boundaries, transforms data (flattening, normalising units, feature engineering), and loads the results into a relational database (PostgreSQL / SQLite) for SQL analytics and Power BI reporting.

---

## 1. Project Architecture

The pipeline implements a modular ETL architecture following the standard **Medallion (Bronze -> Silver -> Gold)** pattern:

```text
OpenWeather API 
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
   Gold Layer   (Relational DB Tables: indexes, constraints, views)
       ↓
  SQL Analytics & Power BI Dashboard Reports
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
├── sql/
│   ├── create_tables.sql    # DDL schema definition script
│   └── analytics.sql        # Analytical reporting and aggregation queries
│
├── src/
│   ├── config.py            # Environment configuration parser and validator
│   ├── logger.py            # Logger initialization (Stream & Rotating File handlers)
│   ├── extract.py           # API data fetcher with retry loop and mock mode
│   ├── validate.py          # Data quality checks for schema structure and ranges
│   ├── transform.py         # Unit converters, derived categories, and CSV saving
│   ├── database.py          # SQLAlchemy ORM model mappings and SessionManager
│   ├── load.py              # Deduplicated bulk save data loader
│   └── pipeline.py          # ETL Main Orchestrator CLI entrypoint
│
├── requirements.txt         # Python library dependencies
├── .env                     # Local configuration secrets (ignored by Git)
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

## 4. Installation & Getting Started

### Prerequisites
* Python 3.11+
* Git
* (Optional) PostgreSQL database (otherwise, the pipeline defaults to SQLite file database automatically).

### Step 1: Clone and Set Up Workspace
```bash
git clone <your-repository-url>
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
Copy `.env.example` to `.env` and adjust the variables:
```bash
copy .env.example .env
```
Inside `.env`:
* Enter your `OPENWEATHER_API_KEY` (sign up at [openweathermap.org](https://openweathermap.org/) to get one).
* *Note*: If you leave the default placeholder API key, the pipeline automatically toggles **MOCK Mode**, generating realistic weather outputs so you can test the entire workflow with zero setup.
* Set `DB_TYPE=sqlite` for zero-setup local database, or `DB_TYPE=postgresql` to load into a real PostgreSQL server.

---

## 5. Running the Pipeline

To run the end-to-end pipeline:
```bash
python -m src.pipeline
```

### Sample Ingestion Log Output:
```text
[2026-07-19 00:39:30] [INFO] [weather_pipeline:36] - Initializing Database connection pool to: sqlite
[2026-07-19 00:39:30] [INFO] [weather_pipeline:28] - =========================================
[2026-07-19 00:39:30] [INFO] [weather_pipeline:29] -      STARTING WEATHER ETL PIPELINE      
[2026-07-19 00:39:30] [INFO] [weather_pipeline:30] - =========================================
[2026-07-19 00:39:30] [INFO] [weather_pipeline:34] - >>> [STAGE 1] Ingestion: Extracting Raw JSON from OpenWeather...
[2026-07-19 00:39:30] [INFO] [weather_pipeline:209] - Starting weather data extraction for 7 cities...
[2026-07-19 00:39:30] [INFO] [weather_pipeline:133] - Generating mock data for: New York
[2026-07-19 00:39:30] [INFO] [weather_pipeline:196] - Saved raw JSON payload to: D:\downloads\Weather-Data-Pipeline\data\raw\weather_new_york_20260718_190930.json
...
[2026-07-19 00:39:30] [INFO] [weather_pipeline:223] - Extraction completed. Successfully saved 7/7 raw files.
[2026-07-19 00:39:30] [INFO] [weather_pipeline:41] - >>> [STAGE 2] Quality Assurance: Validating Raw Payloads...
[2026-07-19 00:39:30] [INFO] [weather_pipeline:157] - Starting validation of raw weather data files...
[2026-07-19 00:39:30] [INFO] [weather_pipeline:211] - =========================================
[2026-07-19 00:39:30] [INFO] [weather_pipeline:212] -          DATA VALIDATION REPORT          
[2026-07-19 00:39:30] [INFO] [weather_pipeline:213] - =========================================
[2026-07-19 00:39:30] [INFO] [weather_pipeline:214] - Total Raw Files Processed : 21
[2026-07-19 00:39:30] [INFO] [weather_pipeline:215] - Valid Records Accepted    : 21
[2026-07-19 00:39:30] [INFO] [weather_pipeline:216] - Rejected Records (Failed) : 0
[2026-07-19 00:39:30] [INFO] [weather_pipeline:217] - Duplicate Records Skipped : 7
[2026-07-19 00:39:30] [INFO] [weather_pipeline:218] - =========================================
[2026-07-19 00:39:30] [INFO] [weather_pipeline:47] - >>> [STAGE 3] Processing: Transforming Units & Categorizing...
[2026-07-19 00:39:30] [INFO] [weather_pipeline:117] - Starting transformation of 14 records...
[2026-07-19 00:39:30] [INFO] [weather_pipeline:134] - Successfully transformed data into DataFrame with shape: (14, 19)
[2026-07-19 00:39:30] [INFO] [weather_pipeline:158] - Saved processed dataset to CSV: D:\downloads\Weather-Data-Pipeline\data\processed\weather_processed_20260718_190930.csv
[2026-07-19 00:39:30] [INFO] [weather_pipeline:55] - >>> [STAGE 4] Storage: Loading Transformed Dataset into Database...
[2026-07-19 00:39:30] [INFO] [weather_pipeline:48] - Starting database load of 14 records...
[2026-07-19 00:39:30] [INFO] [weather_pipeline:120] - Database load completed in 0.04s. Status: 0 inserted, 14 skipped.
[2026-07-19 00:39:30] [INFO] [weather_pipeline:59] - =========================================
[2026-07-19 00:39:30] [INFO] [weather_pipeline:60] -     WEATHER ETL PIPELINE SUCCESS        
[2026-07-19 00:39:30] [INFO] [weather_pipeline:61] - =========================================
[2026-07-19 00:39:30] [INFO] [weather_pipeline:62] - Total Processing Time    : 0.12 seconds
[2026-07-19 00:39:30] [INFO] [weather_pipeline:63] - Cities Configured        : 7
[2026-07-19 00:39:30] [INFO] [weather_pipeline:64] - Raw Files Written        : 7
[2026-07-19 00:39:30] [INFO] [weather_pipeline:65] - Validated JSONs Accepted : 14
[2026-07-19 00:39:30] [INFO] [weather_pipeline:66] - Database Rows Inserted   : 0
[2026-07-19 00:39:30] [INFO] [weather_pipeline:67] - Database Rows Skipped    : 14
[2026-07-19 00:39:30] [INFO] [weather_pipeline:68] - =========================================
```

---

## 6. Future Scale Improvements

* **Orchestration with Apache Airflow**: Package the pipeline execution inside an Airflow DAG. Run the extraction hourly or daily on a Cron schedule, managing execution statuses via Airflow's metadata database.
* **Cloud Storage (Bronze/Silver)**: Replace local file saving with an **AWS S3** bucket (using the `boto3` library in Python) or Azure Blob Storage to build a scalable data lake.
* **Containerization (Docker)**: Build a Dockerfile for the Python environment and database. Run the entire infrastructure (`PostgreSQL`, `Airflow`, `Python pipeline`) using a single `docker-compose.yml` file for zero-config production deployments.
