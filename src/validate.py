"""
Validation Module
=================
Validates raw weather JSON payloads against schema structure, value boundaries,
and logical rules (e.g., no future timestamps, no negative pressure). Generates 
a validation summary report.
"""

import os
import json
import time
from typing import Dict, Any, List, Tuple, Optional
from src.config import config
from src.logger import logger


class WeatherValidator:
    """Validates raw weather data payloads and outputs quality reports."""

    def __init__(self) -> None:
        self.raw_dir = os.path.join(config.base_dir, "data", "raw")

    def validate_record(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates a single raw weather record against schema and range rules.
        
        Args:
            data: Raw weather JSON payload as a dictionary.
            
        Returns:
            A tuple of (is_valid, list_of_errors).
        """
        errors = []

        # 1. Structural Checks: Verify presence of critical fields
        required_paths = {
            "name": str,
            "dt": int,
            "main": dict,
            "weather": list,
            "sys": dict,
            "coord": dict,
            "wind": dict,
            "clouds": dict,
        }

        for field_name, expected_type in required_paths.items():
            if field_name not in data:
                errors.append(f"Missing root key: '{field_name}'")
            elif not isinstance(data[field_name], expected_type):
                errors.append(
                    f"Type mismatch: '{field_name}' expected {expected_type.__name__}, "
                    f"got {type(data[field_name]).__name__}"
                )

        if errors:
            # If structure is broken, we cannot perform range validation safely
            return False, errors

        # Safely parse nested fields
        main = data["main"]
        weather = data["weather"]
        sys = data["sys"]
        coord = data["coord"]
        wind = data["wind"]
        clouds = data["clouds"]

        # Ensure weather array is not empty
        if not weather or not isinstance(weather[0], dict):
            errors.append("Invalid or empty 'weather' list structure.")

        # 2. Value Range & Boundary Checks
        # Temperature: kelvin range (180K to 340K / -93C to 67C)
        temp_keys = ["temp", "feels_like", "temp_min", "temp_max"]
        for key in temp_keys:
            if key in main:
                val = main[key]
                if not isinstance(val, (int, float)):
                    errors.append(f"Temperature '{key}' is not numeric.")
                elif val < 180.0 or val > 340.0:
                    errors.append(f"Temperature '{key}' out of physical range: {val}K")
            else:
                errors.append(f"Missing temperature key: 'main.{key}'")

        # Humidity: 0% to 100%
        if "humidity" in main:
            humidity = main["humidity"]
            if not isinstance(humidity, (int, float)):
                errors.append("Humidity is not numeric.")
            elif humidity < 0 or humidity > 100:
                errors.append(f"Humidity outside 0-100% range: {humidity}%")
        else:
            errors.append("Missing humidity key: 'main.humidity'")

        # Atmospheric Pressure: must be positive (> 0)
        if "pressure" in main:
            pressure = main["pressure"]
            if not isinstance(pressure, (int, float)):
                errors.append("Pressure is not numeric.")
            elif pressure <= 0:
                errors.append(f"Negative or zero atmospheric pressure: {pressure} hPa")
        else:
            errors.append("Missing pressure key: 'main.pressure'")

        # Wind Speed: must be non-negative
        if "speed" in wind:
            wind_speed = wind["speed"]
            if not isinstance(wind_speed, (int, float)):
                errors.append("Wind speed is not numeric.")
            elif wind_speed < 0:
                errors.append(f"Negative wind speed: {wind_speed} m/s")
        else:
            errors.append("Missing wind speed key: 'wind.speed'")

        # Clouds: 0% to 100%
        if "all" in clouds:
            cloudiness = clouds["all"]
            if not isinstance(cloudiness, (int, float)):
                errors.append("Cloudiness is not numeric.")
            elif cloudiness < 0 or cloudiness > 100:
                errors.append(f"Cloudiness outside 0-100% range: {cloudiness}%")

        # Latitude & Longitude bounds
        if "lat" in coord and "lon" in coord:
            lat, lon = coord["lat"], coord["lon"]
            if not (-90.0 <= lat <= 90.0):
                errors.append(f"Latitude out of bounds [-90, 90]: {lat}")
            if not (-180.0 <= lon <= 180.0):
                errors.append(f"Longitude out of bounds [-180, 180]: {lon}")
        else:
            errors.append("Missing coordinates: 'coord.lat' or 'coord.lon'")

        # Country code checking
        if "country" not in sys or not sys["country"]:
            errors.append("Missing or empty country code: 'sys.country'")

        # 3. Timestamp Validity Checks
        dt = data["dt"]
        current_time = time.time()
        # dt shouldn't be in the future (with 1-hour timezone/buffer tolerance)
        if dt > current_time + 3600:
            errors.append(f"Timestamp is in the future: dt={dt} (current={int(current_time)})")
        # dt shouldn't be older than 24 hours for this pipeline
        elif current_time - dt > 86400:
            errors.append(f"Timestamp is too old (> 24 hours): dt={dt} (age={int((current_time - dt)/3600)}h)")

        return len(errors) == 0, errors

    def validate_raw_files(self) -> List[Dict[str, Any]]:
        """
        Scans data/raw/ directory, validates all JSON files, flags duplicates, 
        and outputs a report.
        
        Returns:
            A list of validated, clean dictionaries ready for transformation.
        """
        logger.info("Starting validation of raw weather data files...")
        
        if not os.path.exists(self.raw_dir):
            logger.error(f"Raw directory does not exist: {self.raw_dir}")
            return []

        json_files = [f for f in os.listdir(self.raw_dir) if f.endswith(".json")]
        if not json_files:
            logger.warning("No JSON files found in data/raw to validate.")
            return []

        valid_records: List[Dict[str, Any]] = []
        unique_keys = set()  # To track (city, dt) combinations for duplicates
        
        total_count = 0
        valid_count = 0
        rejected_count = 0
        duplicate_count = 0

        for file_name in json_files:
            total_count += 1
            file_path = os.path.join(self.raw_dir, file_name)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read/parse {file_name}: {e}")
                rejected_count += 1
                continue

            # 1. Check validations
            is_valid, errors = self.validate_record(data)
            
            if not is_valid:
                logger.warning(f"File {file_name} failed validation. Errors: {errors}")
                rejected_count += 1
                continue

            # 2. Check for Duplicates in this batch (City Name + Timestamp 'dt')
            city = data["name"]
            dt = data["dt"]
            uniq_key = (city.lower(), dt)

            if uniq_key in unique_keys:
                logger.info(f"Duplicate record ignored for: {city} at timestamp {dt} (file: {file_name})")
                duplicate_count += 1
                continue
                
            unique_keys.add(uniq_key)
            valid_records.append(data)
            valid_count += 1

        # Validation Summary Report
        logger.info("=========================================")
        logger.info("         DATA VALIDATION REPORT          ")
        logger.info("=========================================")
        logger.info(f"Total Raw Files Processed : {total_count}")
        logger.info(f"Valid Records Accepted    : {valid_count}")
        logger.info(f"Rejected Records (Failed) : {rejected_count}")
        logger.info(f"Duplicate Records Skipped : {duplicate_count}")
        logger.info("=========================================")

        return valid_records


if __name__ == "__main__":
    validator = WeatherValidator()
    validator.validate_raw_files()
