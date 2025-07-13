import os
from google.cloud import bigquery
from pathlib import Path
from local_development.preprocessing_class import PreProcessing

# Initialize the BigQuery client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/hyggeskyen_service_account.json'
bq_client = bigquery.Client()

# Import OpenWeather API key
openweather_api_key = Path("C:/Users/allan/Desktop/Personlige projekter/openweather_api_key.txt").read_text()

# Instantiate PreProcessing class
PreProcessing = PreProcessing(bq_client, openweather_api_key)

# Define SQL query to fetch historical data from Bigquery
query = """
SELECT 
      traffic.*,
      weather.weather_main,
      weather.temperature,
      weather.feels_like,
      weather.humidity_percent,
      weather.visibility,
      weather.wind_speed,
      weather.cloudiness_percent
FROM 
    `sylvan-mode-413619.copenhagen_data.weather_table` AS weather
INNER JOIN 
    `sylvan-mode-413619.copenhagen_data.traffic_table` AS traffic
ON 
    weather.geo_name = traffic.geo_name 
    AND weather.time = traffic.time
    AND weather.date = traffic.date
WHERE 
    DATE(traffic.date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 YEAR)
"""

