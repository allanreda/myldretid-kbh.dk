from google.cloud import bigquery
import pandas as pd
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/hyggeskyen_service_account.json'

# Initialize the BigQuery client
bq_client = bigquery.Client()

# Define SQL query
query = """
SELECT 
      traffic.*,
      weather.weather_main,
      weather.weather_description,
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
"""

# Run the query and convert to DataFrame
query_job = bq_client.query(query)
raw_df = query_job.to_dataframe()

########################### DATA HANDLING ###########################

