"""
Transformation & Feature Engineering Module
===========================================
Flattens validated raw weather records, renames columns, normalizes values 
(Kelvin to Celsius, Epoch to Datetime), applies feature engineering categories, 
and saves the resulting dataset to a CSV file.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd

from src.config import config
from src.logger import logger


class WeatherTransformer:
    """Transforms raw weather dicts into clean, flat Pandas DataFrames with engineered features."""

    def __init__(self) -> None:
        self.processed_dir = os.path.join(config.base_dir, "data", "processed")
        os.makedirs(self.processed_dir, exist_ok=True)

    def _kelvin_to_celsius(self, kelvin: float) -> float:
        """Converts Kelvin to Celsius, rounded to 2 decimal places."""
        return round(kelvin - 273.15, 2)

    def _epoch_to_datetime(self, epoch: int) -> str:
        """Converts Unix epoch timestamp to UTC ISO 8601 string format (YYYY-MM-DD HH:MM:SS)."""
        return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def _get_temp_category(self, temp_c: float) -> str:
        """Categorizes temperature into Cold, Warm, or Hot."""
        if temp_c < 10.0:
            return "Cold"
        elif 10.0 <= temp_c <= 25.0:
            return "Warm"
        else:
            return "Hot"

    def _get_humidity_category(self, humidity: float) -> str:
        """Categorizes humidity into Dry, Comfortable, or Sticky."""
        if humidity < 30.0:
            return "Dry"
        elif 30.0 <= humidity <= 60.0:
            return "Comfortable"
        else:
            return "Sticky"

    def _get_wind_category(self, wind_speed: float) -> str:
        """Categorizes wind speed into Calm, Breezy, or Windy."""
        if wind_speed < 3.0:
            return "Calm"
        elif 3.0 <= wind_speed <= 8.0:
            return "Breezy"
        else:
            return "Windy"

    def flatten_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts and flattens nested fields from raw JSON payload.
        
        Args:
            data: Raw weather JSON payload.
            
        Returns:
            A single-level dictionary representing a flat row.
        """
        # Temperature unit conversions
        temp_c = self._kelvin_to_celsius(data["main"]["temp"])
        feels_like_c = self._kelvin_to_celsius(data["main"]["feels_like"])

        # Timestamp formatting
        timestamp_dt = self._epoch_to_datetime(data["dt"])
        sunrise_dt = self._epoch_to_datetime(data["sys"]["sunrise"])
        sunset_dt = self._epoch_to_datetime(data["sys"]["sunset"])

        # Feature engineering derived columns
        temp_category = self._get_temp_category(temp_c)
        humidity_category = self._get_humidity_category(data["main"]["humidity"])
        wind_category = self._get_wind_category(data["wind"]["speed"])

        # Flattened key-value mapping
        return {
            "city": data["name"],
            "country": data["sys"]["country"],
            "latitude": round(data["coord"]["lat"], 4),
            "longitude": round(data["coord"]["lon"], 4),
            "temperature": temp_c,
            "feels_like": feels_like_c,
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": round(data["wind"]["speed"], 2),
            "visibility": data.get("visibility", 10000),  # Handle potential missing visibility
            "weather": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "cloudiness": data["clouds"]["all"],
            "sunrise": sunrise_dt,
            "sunset": sunset_dt,
            "timestamp": timestamp_dt,
            "temp_category": temp_category,
            "humidity_category": humidity_category,
            "wind_category": wind_category
        }

    def transform_records(self, valid_records: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Transforms multiple validated dicts into a structured Pandas DataFrame.
        
        Args:
            valid_records: A list of clean validated weather dictionaries.
            
        Returns:
            A clean, formatted Pandas DataFrame.
        """
        logger.info(f"Starting transformation of {len(valid_records)} records...")
        
        if not valid_records:
            logger.warning("No records to transform. Returning empty DataFrame.")
            return pd.DataFrame()

        flat_records = [self.flatten_record(rec) for rec in valid_records]
        df = pd.DataFrame(flat_records)

        # Defensive deduplication (based on city and timestamp combination)
        initial_len = len(df)
        df.drop_duplicates(subset=["city", "timestamp"], keep="first", inplace=True)
        final_len = len(df)
        
        if final_len < initial_len:
            logger.info(f"Deduplicated DataFrame: removed {initial_len - final_len} duplicate rows.")

        logger.info(f"Successfully transformed data into DataFrame with shape: {df.shape}")
        return df

    def save_to_csv(self, df: pd.DataFrame) -> Optional[str]:
        """
        Saves the processed DataFrame to the data/processed directory as a CSV.
        
        Args:
            df: Cleaned Pandas DataFrame.
            
        Returns:
            The file path where the CSV was saved, or None if saving failed.
        """
        if df.empty:
            logger.warning("Attempted to save an empty DataFrame. CSV not generated.")
            return None

        # Filename includes current run timestamp
        run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"weather_processed_{run_timestamp}.csv"
        filepath = os.path.join(self.processed_dir, filename)

        try:
            df.to_csv(filepath, index=False, encoding="utf-8")
            logger.info(f"Saved processed dataset to CSV: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save CSV file: {e}")
            return None


if __name__ == "__main__":
    # Integration check: Run validation first, then transformation
    from src.validate import WeatherValidator
    
    validator = WeatherValidator()
    valid_data = validator.validate_raw_files()
    
    transformer = WeatherTransformer()
    processed_df = transformer.transform_records(valid_data)
    transformer.save_to_csv(processed_df)
