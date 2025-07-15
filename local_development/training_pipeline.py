import os
from google.cloud import bigquery
from pathlib import Path
from sklearn.ensemble import ExtraTreesRegressor
import importlib # Remove in prod
import local_development.preprocessing_class  # Remove in prod
importlib.reload(local_development.preprocessing_class)  # Remove in prod
from local_development.preprocessing_class import PreProcessing
from local_development.multicollinearity_reduction_class import MulticollinearityReducer
from local_development.machine_learning_class import MachineLearning
import joblib

# Initialize the BigQuery client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/hyggeskyen_service_account.json'
bq_client = bigquery.Client()

# Import OpenWeather API key
openweather_api_key = Path("C:/Users/allan/Desktop/Personlige projekter/openweather_api_key.txt").read_text()

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

# Instantiate PreProcessing class
preprocesser = PreProcessing(bq_client, openweather_api_key)
# Instantiate Reducer class
reducer = MulticollinearityReducer(target_column = "current_travel_time")
# Instantiate MachineLearning class
machinelearning = MachineLearning(model = ExtraTreesRegressor(), target_column = "current_travel_time")

# Pull historical data from bigquery
raw_df = preprocesser.pull_historical_data(query)
# Run the preprocessing pipeline for the historical data
morning_df, afternoon_df = preprocesser.training_preprocessing(raw_df, manual_holidays)

# Run the multicollinearity reduction pipeline on both dataframes
morning_df = reducer.execute_reduction(morning_df)
afternoon_df = reducer.execute_reduction(afternoon_df)

# Validate model performance on both dataframes
morning_results = machinelearning.validate_model(morning_df, "morning_df")
afternoon_results = machinelearning.validate_model(afternoon_df, "afternoon_df")
# Train models on full data of both dataframes
morning_model, morning_scaler, morning_columns = machinelearning.train_model(morning_df, "morning_df")
afternoon_model, afternoon_scaler, afternoon_columns = machinelearning.train_model(afternoon_df, "afternoon_df")

# Save model, scaler, and columns to joblib files
joblib.dump({
    "model": morning_model,
    "scaler": morning_scaler,
    "columns": morning_columns
}, "morning_model.joblib")

joblib.dump({
    "model": afternoon_model,
    "scaler": afternoon_scaler,
    "columns": afternoon_columns
}, "afternoon_model.joblib")