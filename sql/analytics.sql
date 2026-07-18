-- Weather Data Pipeline - Analytics Queries
-- Mapped for PostgreSQL (Production) and commented for SQLite (Local testing)

-- =====================================================================
-- 1. General Temperature Statistics (Average, Max, Min)
-- =====================================================================
SELECT 
    city,
    country,
    ROUND(AVG(temperature)::numeric, 2) as avg_temp_c,
    ROUND(MAX(temperature)::numeric, 2) as max_temp_c,
    ROUND(MIN(temperature)::numeric, 2) as min_temp_c,
    COUNT(id) as total_observations
FROM weather_data
GROUP BY city, country
ORDER BY avg_temp_c DESC;

-- SQLite equivalent:
-- SELECT city, country, ROUND(AVG(temperature), 2) as avg_temp_c, ROUND(MAX(temperature), 2) as max_temp_c, ROUND(MIN(temperature), 2) as min_temp_c, COUNT(id) as total_observations FROM weather_data GROUP BY city, country ORDER BY avg_temp_c DESC;


-- =====================================================================
-- 2. Most Humid City (with associated date and weather details)
-- =====================================================================
-- Find the city with the highest average humidity
SELECT 
    city,
    country,
    ROUND(AVG(humidity)::numeric, 1) as avg_humidity_pct
FROM weather_data
GROUP BY city, country
ORDER BY avg_humidity_pct DESC
LIMIT 1;


-- =====================================================================
-- 3. Average Wind Speed by Wind Category
-- =====================================================================
SELECT 
    wind_category,
    COUNT(id) as count,
    ROUND(AVG(wind_speed)::numeric, 2) as avg_wind_speed_ms,
    ROUND(MAX(wind_speed)::numeric, 2) as max_wind_speed_ms
FROM weather_data
GROUP BY wind_category
ORDER BY avg_wind_speed_ms DESC;


-- =====================================================================
-- 4. Weather Condition Distribution
-- =====================================================================
-- Count occurrences of weather classifications (e.g. Clear, Rain, Clouds)
SELECT 
    weather,
    description,
    COUNT(id) as occurrence_count,
    ROUND((COUNT(id) * 100.0 / (SELECT COUNT(*) FROM weather_data))::numeric, 2) as percentage
FROM weather_data
GROUP BY weather, description
ORDER BY occurrence_count DESC;


-- =====================================================================
-- 5. Daily Trend Analysis (PostgreSQL)
-- =====================================================================
-- Casts timestamps to DATE to group by calendar day
SELECT 
    timestamp::date as observation_date,
    COUNT(id) as total_records,
    ROUND(AVG(temperature)::numeric, 2) as avg_temp,
    ROUND(AVG(humidity)::numeric, 2) as avg_humidity,
    ROUND(AVG(wind_speed)::numeric, 2) as avg_wind_speed
FROM weather_data
GROUP BY timestamp::date
ORDER BY observation_date ASC;

-- SQLite equivalent:
-- SELECT 
--     date(timestamp) as observation_date,
--     COUNT(id) as total_records,
--     ROUND(AVG(temperature), 2) as avg_temp,
--     ROUND(AVG(humidity), 2) as avg_humidity,
--     ROUND(AVG(wind_speed), 2) as avg_wind_speed
-- FROM weather_data
-- GROUP BY date(timestamp)
-- ORDER BY observation_date ASC;


-- =====================================================================
-- 6. Monthly Trend Analysis (PostgreSQL)
-- =====================================================================
-- Formats dates to Year-Month groupings
SELECT 
    TO_CHAR(timestamp, 'YYYY-MM') as observation_month,
    COUNT(id) as total_records,
    ROUND(AVG(temperature)::numeric, 2) as avg_temp,
    ROUND(AVG(humidity)::numeric, 2) as avg_humidity
FROM weather_data
GROUP BY TO_CHAR(timestamp, 'YYYY-MM')
ORDER BY observation_month ASC;

-- SQLite equivalent:
-- SELECT 
--     strftime('%Y-%m', timestamp) as observation_month,
--     COUNT(id) as total_records,
--     ROUND(AVG(temperature), 2) as avg_temp,
--     ROUND(AVG(humidity), 2) as avg_humidity
-- FROM weather_data
-- GROUP BY strftime('%Y-%m', timestamp)
-- ORDER BY observation_month ASC;
