# Power BI Weather Dashboard Guide

This guide details how to build a professional-grade Power BI dashboard utilizing the output of the Weather Data Engineering Pipeline.

---

## 1. Connecting Power BI to the Data Sources

Power BI can connect to the pipeline through two primary methods:

### Option A: PostgreSQL Database (Recommended for Production)
1. Open Power BI Desktop.
2. Click **Get Data** > **PostgreSQL database**.
3. Enter the connection details:
   - **Server**: `localhost` (or your remote host)
   - **Database**: `weather_db`
4. Choose **Import** or **DirectQuery**.
   - *Import* loads a snapshot of the data into Power BI RAM (fastest performance).
   - *DirectQuery* queries the database in real-time as users interact with visuals.
5. Provide your database credentials (`postgres` username and password) and select the `weather_data` table.

### Option B: Local CSV Folder (Zero Setup fallback)
1. Click **Get Data** > **Folder**.
2. Browse and select the directory: `D:\downloads\Weather-Data-Pipeline\data\processed\`
3. Click **Combine** > **Combine & Transform Data**.
4. Power BI will automatically combine all historical processed CSV files in this folder into a single table.

---

## 2. Data Modeling & DAX Measures

Once the table is loaded, rename it to `WeatherData` in the model view. To make the dashboard interview-ready, create a new table called `_Measures` and write these custom DAX formulas:

* **Total Observations**:
  ```dax
  Total Observations = COUNT(WeatherData[id])
  ```
* **Average Temperature (°C)**:
  ```dax
  Average Temperature = AVERAGE(WeatherData[temperature])
  ```
* **Max Temperature (°C)**:
  ```dax
  Max Temperature = MAX(WeatherData[temperature])
  ```
* **Average Humidity (%)**:
  ```dax
  Average Humidity = AVERAGE(WeatherData[humidity])
  ```
* **Average Wind Speed (m/s)**:
  ```dax
  Average Wind Speed = AVERAGE(WeatherData[wind_speed])
  ```

---

## 3. Recommended Dashboard Layout & Visuals

A clean, executive-style dashboard layout should fit on a single responsive screen (16:9 canvas):

### Section 1: KPI Header Card (Top Row)
* **Visual**: Multi-row card or 4 individual Card visuals.
* **Fields**: `Average Temperature`, `Average Humidity`, `Average Wind Speed`, and `Total Observations`.
* **Design**: Minimalist formatting, dark mode tiles with bold numbers.

### Section 2: Trend & Distribution (Middle Row)
* **Left: Temperature Trend**:
  * *Visual*: Line Chart.
  * *X-Axis*: `timestamp` (drill down by Date/Hour).
  * *Y-Axis*: `Average Temperature`.
  * *Legend*: `city`.
* **Right: Weather Conditions**:
  * *Visual*: Donut Chart or Treemap.
  * *Legend*: `weather`.
  * *Values*: `Total Observations` (show as percentage of total).

### Section 3: Comparisons & Location Map (Bottom Row)
* **Left: City Humidity Comparison**:
  * *Visual*: Clustered Bar Chart.
  * *Y-Axis*: `city`.
  * *X-Axis*: `Average Humidity`.
  * *Color Formatting*: Add conditional formatting (color gradient) mapping dry to humid.
* **Right: Weather Map**:
  * *Visual*: Bubble Map or ArcGIS Map.
  * *Latitude*: `latitude`.
  * *Longitude*: `longitude`.
  * *Bubble Size*: `Average Temperature`.
  * *Tooltips*: `city`, `weather`, `humidity`.

### Section 4: Filters (Right/Left Sidebar)
* **Visual**: Slicer panels.
* **Fields**:
  - `city` (Dropdown check)
  - `temp_category` (Tile style)
  - `humidity_category` (Tile style)

---

## 4. Automatic Dashboard Refresh
If using **PostgreSQL Import Mode**:
1. Publish the dashboard to the **Power BI Service**.
2. Configure an **On-Premises Data Gateway** on the host machine running PostgreSQL.
3. Schedule automatic refreshes (e.g. daily or hourly) to pull new records added by the Airflow or python execution.
