import joblib
import sys
import os
from google.cloud import bigquery
from pathlib import Path
import pandas as pd
import importlib # Remove in prod
importlib.reload(sys.modules['local_development.preprocessing_class'])
importlib.reload(sys.modules['local_development.prediction_pipeline_class'])
importlib.reload(sys.modules['local_development.traffic_plotter_class'])
from local_development.preprocessing_class import PreProcessing
from local_development.prediction_pipeline_class import PredictionPipeline
from local_development.traffic_plotter_class import TrafficGaugePlotter
import numpy as np
from datetime import date, datetime

# Initialize the BigQuery client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/hyggeskyen_service_account.json'
bq_client = bigquery.Client()

# Import OpenWeather API key
openweather_api_key = Path("C:/Users/allan/Desktop/Personlige projekter/openweather_api_key.txt").read_text()

# Instantiate PreProcessing class
preprocesser = PreProcessing(bq_client, openweather_api_key)
# Instantiate PredictionPipeline class
predict = PredictionPipeline()
# Instantiate TrafficGaugePlotter class
plotter = TrafficGaugePlotter()

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


# Pull historical data from bigquery
historical_df = preprocesser.pull_historical_data(query)
# Pull weather forecast for next 5 days
forecast_df = preprocesser.pull_weather_forecast()

# Combine historical data with forecast data
combined_df = predict.combine_historical_with_forecast(historical_df, forecast_df)

# Dataframes to predict the next 1 day only (contains lag_1day and rolling_avg_7day)
morning_df, afternoon_df, _, _ = preprocesser.execute_preprocessing_1_day(combined_df, manual_holidays)

# Get next days values
next_morning = morning_df.iloc[[-5]]
next_afternoon = afternoon_df.iloc[[-5]]

# Calculate avg morning travel time for next_afternoon, but only if its before 9 or after 15
# This will make it possible to run the 1_day_prediction_model that has both lag_1_day and rolling_avg variables.
# 1_day_prediction_model requires the morning_travel_time variable
if datetime.now().hour <= 8 or datetime.now().hour > 15:
    next_afternoon['morning_travel_time'] = morning_df['current_travel_time'].dropna().mean()

# Predict next mornings traveltime and compare to average traveltime
next_morning_traffic = predict.predict_next_rush_hour_period('1_day_prediction_model', 'morning', next_morning)
# Predict next afternoons traveltime and compare to average traveltime
# Note: Should ideally be run before 15 but after 9 to get the correct morning_traveltime value included.
next_afternoon_traffic = predict.predict_next_rush_hour_period('1_day_prediction_model', 'afternoon', next_afternoon)

                  
# Dataframes to predict the day after tomorrow and 3 days forward
next_4_morning_df, next_4_afternoon_df, _, _ = preprocesser.execute_preprocessing_2_day(combined_df, manual_holidays)

# Get values for the next 4 days
next_4_mornings = next_4_morning_df.iloc[-4:]
next_4_afternoons = next_4_afternoon_df.iloc[-4:]

# Predict next 4 days traveltime and compare to average traveltime
next_4_mornings_traffic = predict.predict_next_4_rush_hour_periods('2_day_prediction_model', 'morning', next_4_mornings)
next_4_afternoons_traffic = predict.predict_next_4_rush_hour_periods('2_day_prediction_model', 'afternoon', next_4_afternoons)

# Concatenate all dates
all_morning_predictions = np.concatenate([next_morning_traffic, next_4_mornings_traffic])
all_afternoon_predictions = np.concatenate([next_afternoon_traffic, next_4_afternoons_traffic])

# Define and map dates to predictions
morning_prediction_dict, afternoon_prediction_dict = predict.define_dates(all_morning_predictions, all_afternoon_predictions)

# Plot predictions for both PC and mobile devices
plotter.plot_gauges(morning_prediction_dict, afternoon_prediction_dict)
plotter.plot_gauges_mobile(morning_prediction_dict, afternoon_prediction_dict)