"""
Load Module
===========
Responsible for loading the transformed weather data from a Pandas DataFrame 
into the database. Implements database-agnostic insert logic that queries 
existing records to prevent constraint violations.
"""

import time
from datetime import datetime
import pandas as pd
from sqlalchemy import and_

from src.database import db_manager, WeatherData
from src.logger import logger


class WeatherLoader:
    """Handles loading tabular DataFrame rows into the database."""

    def __init__(self) -> None:
        self.db = db_manager
        # Initialize tables on loader startup
        self.db.init_db()

    def load_dataframe(self, df: pd.DataFrame) -> tuple[int, int]:
        """
        Loads a Pandas DataFrame of transformed weather data into PostgreSQL or SQLite.
        Prevents duplicate insertions by pre-filtering records already in the database.
        
        Args:
            df: Transformed clean Pandas DataFrame.
            
        Returns:
            A tuple of (inserted_count, skipped_count).
        """
        if df.empty:
            logger.warning("Empty DataFrame provided to loader. Database load skipped.")
            return 0, 0

        session = self.db.get_session()
        start_time = time.time()
        
        inserted_count = 0
        skipped_count = 0
        
        try:
            logger.info(f"Starting database load of {len(df)} records...")

            # 1. Fetch existing records from database to perform pre-filter deduplication.
            # We query the DB for the cities and timestamps present in our incoming batch.
            cities_in_batch = df["city"].unique().tolist()
            min_timestamp = pd.to_datetime(df["timestamp"]).min()
            max_timestamp = pd.to_datetime(df["timestamp"]).max()

            # Query existing records in this time-window/city subset
            existing_records = session.query(WeatherData.city, WeatherData.timestamp).filter(
                and_(
                    WeatherData.city.in_(cities_in_batch),
                    WeatherData.timestamp >= min_timestamp,
                    WeatherData.timestamp <= max_timestamp
                )
            ).all()

            # Create a set of (city, timestamp_str) tuples currently in the DB
            # We format timestamp to string matches because ORM timestamps return as datetime objects
            db_records_set = {
                (row.city.lower(), row.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
                for row in existing_records
            }

            # 2. Iterate through DataFrame rows and prepare insertions
            objects_to_insert = []
            for _, row in df.iterrows():
                row_city = row["city"]
                row_timestamp = row["timestamp"]
                
                # Create match key
                match_key = (row_city.lower(), str(row_timestamp))

                if match_key in db_records_set:
                    logger.debug(f"Record for {row_city} at {row_timestamp} already exists in DB. Skipping.")
                    skipped_count += 1
                else:
                    # Map dataframe row to SQLAlchemy ORM object
                    weather_record = WeatherData(
                        city=row["city"],
                        country=row["country"],
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                        temperature=float(row["temperature"]),
                        feels_like=float(row["feels_like"]),
                        humidity=int(row["humidity"]),
                        pressure=int(row["pressure"]),
                        wind_speed=float(row["wind_speed"]),
                        visibility=int(row["visibility"]),
                        weather=row["weather"],
                        description=row["description"],
                        cloudiness=int(row["cloudiness"]),
                        # Parse strings back into datetime objects for SQLAlchemy mapping
                        sunrise=datetime.strptime(row["sunrise"], "%Y-%m-%d %H:%M:%S"),
                        sunset=datetime.strptime(row["sunset"], "%Y-%m-%d %H:%M:%S"),
                        timestamp=datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
                        temp_category=row["temp_category"],
                        humidity_category=row["humidity_category"],
                        wind_category=row["wind_category"]
                    )
                    objects_to_insert.append(weather_record)

            # 3. Perform bulk bulk-save-objects for production performance
            if objects_to_insert:
                session.bulk_save_objects(objects_to_insert)
                session.commit()
                inserted_count = len(objects_to_insert)
                logger.info(f"Bulk-inserted {inserted_count} new records into the database.")
            else:
                logger.info("No new records to insert. Database is up to date.")

            elapsed_time = time.time() - start_time
            logger.info(
                f"Database load completed in {elapsed_time:.2f}s. "
                f"Status: {inserted_count} inserted, {skipped_count} skipped."
            )
            
            return inserted_count, skipped_count

        except Exception as e:
            session.rollback()
            logger.error(f"Transaction failed, database rolled back: {e}")
            raise e
            
        finally:
            session.close()


if __name__ == "__main__":
    # Integration Dry Run
    from src.validate import WeatherValidator
    from src.transform import WeatherTransformer

    # 1. Validate raw files
    validator = WeatherValidator()
    valid_data = validator.validate_raw_files()

    # 2. Transform into DataFrame
    transformer = WeatherTransformer()
    processed_df = transformer.transform_records(valid_data)

    # 3. Load into database
    loader = WeatherLoader()
    loader.load_dataframe(processed_df)
