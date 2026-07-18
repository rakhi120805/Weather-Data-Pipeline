"""
Extract Module
==============
Handles fetching weather data from the OpenWeather API (or generating realistic 
mock data if no API key is provided) and saving it to the data/raw/ folder.
"""

import os
import json
import time
import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import requests

from src.config import config
from src.logger import logger

# Base URL for OpenWeather API
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherExtractor:
    """Handles weather data retrieval from OpenWeather API with retry logic."""

    def __init__(self) -> None:
        self.api_key = config.api_key
        self.cities = config.cities
        self.raw_dir = os.path.join(config.base_dir, "data", "raw")
        os.makedirs(self.raw_dir, exist_ok=True)
        
        # Check if API Key is set to dummy placeholder or empty
        self.is_mock_mode = (
            not self.api_key 
            or self.api_key == "your_openweather_api_key_here"
        )
        if self.is_mock_mode:
            logger.warning(
                "No valid OpenWeather API key found. Running in MOCK Mode."
            )

    def _generate_mock_data(self, city: str) -> Dict[str, Any]:
        """
        Generates a realistic mock OpenWeather JSON response for testing.
        Useful for local runs without an active internet connection or API key.
        """
        # Dictionary of coordinates and country codes
        city_meta = {
            "New York": {"lat": 40.7128, "lon": -74.0060, "country": "US"},
            "London": {"lat": 51.5074, "lon": -0.1278, "country": "GB"},
            "Tokyo": {"lat": 35.6762, "lon": 139.6503, "country": "JP"},
            "Delhi": {"lat": 28.6139, "lon": 77.2090, "country": "IN"},
            "Sydney": {"lat": -33.8688, "lon": 151.2093, "country": "AU"},
            "Paris": {"lat": 48.8566, "lon": 2.3522, "country": "FR"},
            "Cairo": {"lat": 30.0444, "lon": 31.2357, "country": "EG"},
        }
        
        meta = city_meta.get(city, {"lat": 0.0, "lon": 0.0, "country": "XX"})
        
        # Simulating raw OpenWeather output
        weather_states = [
            {"id": 800, "main": "Clear", "description": "clear sky"},
            {"id": 801, "main": "Clouds", "description": "few clouds"},
            {"id": 803, "main": "Clouds", "description": "broken clouds"},
            {"id": 500, "main": "Rain", "description": "light rain"},
            {"id": 501, "main": "Rain", "description": "moderate rain"},
            {"id": 600, "main": "Snow", "description": "light snow"},
            {"id": 701, "main": "Mist", "description": "mist"},
        ]
        
        state = random.choice(weather_states)
        temp_k = round(random.uniform(260.0, 315.0), 2)  # -13C to 42C
        feels_like_k = temp_k + random.uniform(-3.0, 1.0)
        
        # Simulating coordinates with a tiny bit of noise
        return {
            "coord": {
                "lon": round(meta["lon"] + random.uniform(-0.01, 0.01), 4),
                "lat": round(meta["lat"] + random.uniform(-0.01, 0.01), 4)
            },
            "weather": [
                {
                    "id": state["id"],
                    "main": state["main"],
                    "description": state["description"],
                    "icon": "01d"
                }
            ],
            "base": "stations",
            "main": {
                "temp": temp_k,
                "feels_like": round(feels_like_k, 2),
                "temp_min": round(temp_k - random.uniform(0.5, 2.0), 2),
                "temp_max": round(temp_k + random.uniform(0.5, 2.0), 2),
                "pressure": random.randint(980, 1030),
                "humidity": random.randint(0, 100)
            },
            "visibility": random.randint(1000, 10000),
            "wind": {
                "speed": round(random.uniform(0.0, 15.0), 2),
                "deg": random.randint(0, 360)
            },
            "clouds": {
                "all": random.randint(0, 100)
            },
            "dt": int(time.time()),
            "sys": {
                "type": 1,
                "id": random.randint(1000, 9999),
                "country": meta["country"],
                "sunrise": int(time.time()) - 20000,
                "sunset": int(time.time()) + 20000
            },
            "timezone": random.randint(-43200, 50400),
            "id": random.randint(1000000, 9999999),
            "name": city,
            "cod": 200
        }

    def fetch_city_weather(self, city: str, max_retries: int = 3, backoff_factor: float = 2.0) -> Optional[Dict[str, Any]]:
        """
        Fetches weather data for a single city from the API with retries and exponential backoff.
        
        Args:
            city: Name of the city to query.
            max_retries: Maximum number of times to retry a failed request.
            backoff_factor: Multiplier for exponential backoff delay.
            
        Returns:
            JSON payload as a dictionary, or None if extraction failed.
        """
        if self.is_mock_mode:
            logger.info(f"Generating mock data for: {city}")
            return self._generate_mock_data(city)

        params = {
            "q": city,
            "appid": self.api_key
        }

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Fetching weather for: {city} (Attempt {attempt}/{max_retries})")
                response = requests.get(BASE_URL, params=params, timeout=10)
                
                # Check for HTTP errors (e.g. 404, 401, 500)
                response.raise_for_status()
                
                logger.info(f"Successfully fetched weather for: {city}")
                return response.json()

            except requests.exceptions.HTTPError as http_err:
                status_code = response.status_code
                logger.error(f"HTTP error for {city} (Status {status_code}): {http_err}")
                
                # If it's a client error (e.g. invalid city name or invalid key), do not retry
                if 400 <= status_code < 500:
                    if status_code == 401:
                        logger.critical("Unauthorized API key. Please check your OpenWeather credentials.")
                    elif status_code == 404:
                        logger.error(f"City '{city}' not found in OpenWeather database.")
                    break
                
            except requests.exceptions.RequestException as err:
                logger.warning(f"Request exception for {city}: {err}")
            
            # If we haven't broken/returned and have retries remaining, wait with backoff
            if attempt < max_retries:
                sleep_time = backoff_factor ** attempt
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)

        logger.error(f"Failed to fetch weather data for: {city} after {max_retries} attempts.")
        return None

    def save_raw_data(self, city: str, data: Dict[str, Any]) -> Optional[str]:
        """
        Saves the raw JSON weather payload to the data/raw folder.
        
        Args:
            city: Name of the city.
            data: Raw weather JSON payload.
            
        Returns:
            The file path where the JSON was saved, or None if saving failed.
        """
        # Format filename using city name and UTC timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_city = city.lower().replace(" ", "_")
        filename = f"weather_{safe_city}_{timestamp}.json"
        filepath = os.path.join(self.raw_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logger.info(f"Saved raw JSON payload to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save raw JSON for {city}: {e}")
            return None

    def extract_all(self) -> int:
        """
        Runs the extraction pipeline for all configured cities.
        
        Returns:
            The number of successfully extracted and saved records.
        """
        logger.info(f"Starting weather data extraction for {len(self.cities)} cities...")
        success_count = 0

        for city in self.cities:
            data = self.fetch_city_weather(city)
            if data:
                saved_path = self.save_raw_data(city, data)
                if saved_path:
                    success_count += 1
            
            # Tiny sleep to respect API limits (60 calls/minute for free tier)
            if not self.is_mock_mode:
                time.sleep(1.0)

        logger.info(f"Extraction completed. Successfully saved {success_count}/{len(self.cities)} raw files.")
        return success_count


if __name__ == "__main__":
    extractor = WeatherExtractor()
    extractor.extract_all()
