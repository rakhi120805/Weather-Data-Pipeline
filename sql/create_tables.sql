-- DDL Script to create weather_data table
-- Supports both PostgreSQL and SQLite (with minor data type mapping)

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
    
    -- Ingestion logging
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint for city and timestamp to prevent duplicate loads
    CONSTRAINT uq_city_timestamp UNIQUE (city, timestamp)
);

-- Index for optimizing queries filtering by city and date range
CREATE INDEX IF NOT EXISTS idx_weather_city_timestamp ON weather_data (city, timestamp);
