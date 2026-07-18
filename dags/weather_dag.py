"""
Apache Airflow DAG Module
=========================
Orchestrates and schedules the Weather ETL Pipeline to run automatically on 
an hourly basis. Includes error handling, retry configurations, and environment-safe imports.
"""

import os
import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Dynamic path resolution to ensure the 'src' package is importable
# inside Airflow worker processes.
DAG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DAG_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def run_weather_etl() -> None:
    """
    Python callable task that instantiates and executes the main ETL orchestrator.
    Raises an exception if the run fails so Airflow registers a task failure.
    """
    from src.pipeline import WeatherETLPipeline
    
    pipeline = WeatherETLPipeline()
    success = pipeline.run()
    
    if not success:
        raise ValueError(
            "ETL Pipeline execution returned failure status. "
            "Inspect logs/pipeline.log for details."
        )


# Default arguments applied to all tasks in the DAG
default_args = {
    "owner": "data_engineering_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    # In case of transient failure (e.g. rate limit / network drop), retry twice
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# Instantiate the DAG
with DAG(
    dag_id="weather_etl_automation",
    default_args=default_args,
    description="Automated hourly ingestion pipeline for OpenWeather metrics.",
    # Schedule interval: Cron syntax for 'hourly, at minute 0'
    schedule_interval="0 * * * *",
    # Start date in the past to activate scheduling
    start_date=datetime(2026, 7, 1),
    # catchup=False: Prevent Airflow from running back-logged tasks since the start_date
    catchup=False,
    # Max active runs: limit concurrent runs of this DAG to 1
    max_active_runs=1,
    tags=["weather", "etl", "postgresql"],
) as dag:

    # 1. Define the task executing our python ETL pipeline
    run_etl_task = PythonOperator(
        task_id="execute_weather_etl",
        python_callable=run_weather_etl,
    )

    # Document the task for the Airflow Web UI
    run_etl_task.doc_md = """
    #### Task Description
    Runs the Weather ETL Pipeline which fetches data from OpenWeather API, 
    validates the metrics, transforms them, and loads them into PostgreSQL.
    
    *Reads logs at:* `logs/pipeline.log`
    """
