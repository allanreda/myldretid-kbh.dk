from google.cloud import bigquery, storage, secretmanager
from multicollinearity_reduction_class import MulticollinearityReducer
from machine_learning_class import MachineLearning
from training_pipeline_class import TrainingPipeline
from shared.cloud_utils_class import CloudUtils
from shared.preprocessing_class import PreProcessing
from zoneinfo import ZoneInfo 
from datetime import datetime
import time
from flask import Request, Response
import functions_framework
import base64
import os
import json
from pathlib import Path

# Define the time zone
cet_timezone = ZoneInfo('Europe/Copenhagen')

# Get the current date and time
current_datetime = datetime.now(cet_timezone)
current_date = current_datetime.strftime('%Y-%m-%d')
current_time = current_datetime.strftime('%H:%M')

@functions_framework.http
def train_models(request: Request):
    """Triggered from a Pub/Sub message via HTTP."""
    try:
        print(f" ----------------------------------------------------- \n ----------------------------------------------------- \n ----------------------------------------------------- \n Script execution started on {current_date} at {current_time} \n ----------------------------------------------------- \n ----------------------------------------------------- \n -----------------------------------------------------")
        # Start timer
        start_time = time.time()
        
        # Decode the message, even if not used
        envelope = request.get_json()
        if not envelope or 'message' not in envelope:
            return ("Bad Request: No message", 400)

        message = envelope['message']
        data = base64.b64decode(message.get('data', '')).decode('utf-8')
        print(f"Received pubsub data: {data}")

        # Initialize clients
        bq_client = bigquery.Client()
        storage_client = storage.Client()
        sm_client = secretmanager.SecretManagerServiceClient()

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

        # Load holidays file
        with open(Path(__file__).parent / "shared" / "holidays.json", encoding="utf-8") as f:
            manual_holidays = json.load(f)

        # Instantiate CloudUtils class
        cloud_utils = CloudUtils(bq_client, storage_client, sm_client)
        # Import OpenWeather API key from Secret Manager in 'hyggeskyen' GCP
        openweather_api_key = cloud_utils.get_secret('OPENWEATHER_API_KEY', 'sylvan-mode-413619')

        # Instantiate PreProcessing class
        preprocesser = PreProcessing(openweather_api_key)
        # Instantiate Reducer class
        reducer = MulticollinearityReducer(target_column = "current_travel_time")
        # Instantiate MachineLearning class
        machinelearning = MachineLearning(target_column = "current_travel_time")
        # Instantiate TrainingPipeline class
        training = TrainingPipeline(reducer, preprocesser, machinelearning, cloud_utils)

        # Pull historical traffic and weather data from bigquery
        historical_data = cloud_utils.pull_historical_data(query)

        # Get bucket name from environment
        bucket_name = os.environ.get("MODEL_BUCKET")

        # Run training for 1-day and 2-day models
        training.run_training_pipeline(historical_data, 
                                    manual_holidays,
                                    'execute_preprocessing_1_day',
                                    f"{bucket_name}-models",
                                    'training',
                                    '1_day_prediction_model',
                                    'joblib',
                                    'application/octet-stream')

        training.run_training_pipeline(historical_data, 
                                    manual_holidays,
                                    'execute_preprocessing_2_day',
                                    f"{bucket_name}-models",
                                    'training',
                                    '2_day_prediction_model',
                                    'joblib',
                                    'application/octet-stream')
        
        # End timer
        end_time = time.time()
        # Calculate execution time
        total_time = end_time - start_time

        print(f" ----------------------------------------------------- \n ----------------------------------------------------- \n ----------------------------------------------------- \n Script execution finnished for {current_date} at {current_time} \n ----------------------------------------------------- \n -----------------------------------------------------")

        print(f"-----------------------------------------------------\n Total execution time: {total_time/60} minutes \n-----------------------------------------------------")


        return Response("Training completed successfully", 200)

    except Exception as e:
        print(f"Error: {e}")
        return Response(f"Error occurred, but acknowledged to prevent retry: {e}", status=200)