import joblib
import sys
import os
from google.cloud import bigquery, storage
from pathlib import Path
import pandas as pd
import importlib # Remove in prod
importlib.reload(sys.modules['local_development.preprocessing_class'])
importlib.reload(sys.modules['local_development.prediction_pipeline_class'])
importlib.reload(sys.modules['local_development.traffic_plotter_class'])
importlib.reload(sys.modules['local_development.cloud_utils_class'])
from local_development.preprocessing_class import PreProcessing
from local_development.prediction_pipeline_class import PredictionPipeline
from local_development.cloud_utils_class import CloudUtils
from local_development.traffic_plotter_class import TrafficGaugePlotter
import numpy as np
from datetime import date, datetime
import io

# Initialize the BigQuery client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/myldretid-kbh-test_service_account.json'
bq_client = bigquery.Client()
storage_client = storage.Client()

# Import OpenWeather API key
openweather_api_key = Path("C:/Users/allan/Desktop/Personlige projekter/openweather_api_key.txt").read_text()

# Instantiate CloudUtils class
cloud_utils = CloudUtils(bq_client, storage_client)
# Instantiate PreProcessing class
preprocesser = PreProcessing(openweather_api_key)
# Instantiate PredictionPipeline class
predict = PredictionPipeline(cloud_utils, preprocesser)
# Instantiate TrafficGaugePlotter class
plotter = TrafficGaugePlotter(cloud_utils)

# Create manual holiday date ranges
manual_holidays = [
    ("2024-07-01", "2024-08-09"),
    ("2024-10-14", "2024-10-18"),
    ("2024-12-23", "2025-01-02"),
    ("2025-02-10", "2025-02-14"),
    ("2025-04-14", "2025-04-21"),
    ("2025-05-01", "2025-05-01"),
    ("2025-05-29", "2025-05-30"),
    ("2025-06-05", "2025-06-05"),
    ("2025-06-09", "2025-06-09"),
    ("2025-06-30", "2025-08-08"),
    ("2025-10-13", "2025-10-17"),
    ("2025-11-18", "2025-11-18"),
    ("2025-12-24", "2026-01-02"),
    ("2026-02-09", "2026-02-13"),
    ("2026-03-30", "2026-04-06"),
    ("2026-05-01", "2026-05-01"),
    ("2026-05-14", "2026-05-15"),
    ("2026-05-24", "2026-05-25"),
    ("2026-06-05", "2026-06-05"),
    ("2026-06-29", "2026-08-10")
]

# Define SQL query to fetch historical data from Bigquery
query = """
SELECT 
      traffic.current_travel_time,
      traffic.date,
      traffic.time,
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
    DATE(traffic.date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 8 DAY)
ORDER BY traffic.date, traffic.time DESC

"""


# Pull historical traffic and weather data from bigquery
historical_df = cloud_utils.pull_historical_data(query)
# Pull weather forecast for next 5 days
forecast_df = preprocesser.pull_weather_forecast()

# Predict next 2 rush hours and compare to average traveltime
next_morning_traffic, next_afternoon_traffic = predict.predict_next_rush_hour_periods_wrapper(historical_df, 
                                                                                              forecast_df, 
                                                                                              manual_holidays,
                                                                                              'myldretid-kbh-test',
                                                                                              '1_day_prediction_model')

# Predict the next 8 rush hours after the first 2 and compare to average traveltime
next_4_mornings_traffic, next_4_afternoons_traffic = predict.predict_next_8_rush_hour_periods_wrapper(historical_df, 
                                                                                                      forecast_df, 
                                                                                                      manual_holidays,
                                                                                                      'myldretid-kbh-test',
                                                                                                      '2_day_prediction_model')


# Concatenate all dates
all_morning_predictions = np.concatenate([next_morning_traffic, next_4_mornings_traffic])
all_afternoon_predictions = np.concatenate([next_afternoon_traffic, next_4_afternoons_traffic])
# Define and map dates to predictions
json_predictions = predict.define_dates_and_convert_json(all_morning_predictions, all_afternoon_predictions)

# Write the string to buffer
buffer = io.BytesIO()
buffer.write(json_predictions.encode('utf-8'))

# Upload to GCS
cloud_utils.upload_to_gcs(
    buffer=buffer,
    bucket_name="myldretid-kbh-predictions-test",
    gcs_folder_name="predictions",
    filename="json_predictions",
    filetype="json",
    content_type="application/json"
)

