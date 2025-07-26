import os
from google.cloud import bigquery, storage
from pathlib import Path
import sys
import importlib # Remove in prod
importlib.reload(sys.modules['local_development.preprocessing_class'])
importlib.reload(sys.modules['local_development.multicollinearity_reduction_class'])
importlib.reload(sys.modules['local_development.machine_learning_class'])
importlib.reload(sys.modules['local_development.training_pipeline_class'])
importlib.reload(sys.modules['local_development.cloud_utils_class'])

from local_development.preprocessing_class import PreProcessing
from local_development.multicollinearity_reduction_class import MulticollinearityReducer
from local_development.machine_learning_class import MachineLearning
from local_development.training_pipeline_class import TrainingPipeline
from local_development.cloud_utils_class import CloudUtils


# Initialize the BigQuery client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/myldretid-kbh-test_service_account.json'
bq_client = bigquery.Client()
storage_client = storage.Client()

# Import OpenWeather API key
openweather_api_key = Path("C:/Users/allan/Desktop/Personlige projekter/openweather_api_key.txt").read_text()

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
preprocesser = PreProcessing(openweather_api_key)
# Instantiate Reducer class
reducer = MulticollinearityReducer(target_column = "current_travel_time")
# Instantiate MachineLearning class
machinelearning = MachineLearning(target_column = "current_travel_time")
# Instantiate CloudUtils class
cloud_utils = CloudUtils(bq_client, storage_client)
# Instantiate TrainingPipeline class
training = TrainingPipeline(reducer, preprocesser, machinelearning, cloud_utils)

# Pull historical traffic and weather data from bigquery
historical_data = cloud_utils.pull_historical_data(query)


training.run_training_pipeline(historical_data, 
                               manual_holidays,
                               'execute_preprocessing_1_day',
                               'myldretid-kbh-test',
                               'prediction_models',
                               '1_day_prediction_model',
                               'joblib',
                               'application/octet-stream')

training.run_training_pipeline(historical_data, 
                               manual_holidays,
                               'execute_preprocessing_2_day',
                               'myldretid-kbh-test',
                               'prediction_models',
                               '2_day_prediction_model',
                               'joblib',
                               'application/octet-stream')