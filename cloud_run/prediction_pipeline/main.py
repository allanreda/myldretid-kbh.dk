from google.cloud import bigquery, storage, secretmanager
from prediction_pipeline_class import PredictionPipeline
from shared.preprocessing_class import PreProcessing
from shared.cloud_utils_class import CloudUtils
import numpy as np
from datetime import date, datetime
import io
from zoneinfo import ZoneInfo 
from datetime import datetime
import time
from flask import Request
import functions_framework
import base64
import os

# Define the time zone
cet_timezone = ZoneInfo('Europe/Copenhagen')

# Get the current date and time
current_datetime = datetime.now(cet_timezone)
current_date = current_datetime.strftime('%Y-%m-%d')
current_time = current_datetime.strftime('%H:%M')

@functions_framework.http
def predict(request: Request):
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

        # Instantiate CloudUtils class
        cloud_utils = CloudUtils(bq_client, storage_client, sm_client)
        # Import OpenWeather API key from Secret Manager in 'hyggeskyen' GCP
        openweather_api_key = cloud_utils.get_secret('OPENWEATHER_API_KEY', 'sylvan-mode-413619')

        # Instantiate PreProcessing class
        preprocesser = PreProcessing(openweather_api_key)
        # Instantiate PredictionPipeline class
        predict = PredictionPipeline(cloud_utils, preprocesser)

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
        
        # Get bucket name from environment
        bucket_name = os.environ.get("MODEL_BUCKET")

        # Predict next 2 rush hours and compare to average traveltime
        next_morning_traffic, next_afternoon_traffic = predict.predict_next_rush_hour_periods_wrapper(historical_df, 
                                                                                                    forecast_df, 
                                                                                                    manual_holidays,
                                                                                                    'training',
                                                                                                    '1_day_prediction_model')

        # Predict the next 8 rush hours after the first 2 and compare to average traveltime
        next_4_mornings_traffic, next_4_afternoons_traffic = predict.predict_next_8_rush_hour_periods_wrapper(historical_df, 
                                                                                                            forecast_df, 
                                                                                                            manual_holidays,
                                                                                                            'training',
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
            bucket_name=f"{bucket_name}-predictions",
            gcs_folder_name="predictions",
            filename="json_predictions",
            filetype="json",
            content_type="application/json"
        )

        # End timer
        end_time = time.time()
        # Calculate execution time
        total_time = end_time - start_time

        print(f" ----------------------------------------------------- \n ----------------------------------------------------- \n ----------------------------------------------------- \n Script execution finnished for {current_date} at {current_time} \n ----------------------------------------------------- \n -----------------------------------------------------")

        print(f"-----------------------------------------------------\n Total execution time: {total_time/60} minutes \n-----------------------------------------------------")

        return ("Prediction completed successfully", 200)

    except Exception as e:
        print(f"Error: {e}")
        return (f"Internal server error: {e}", 500)