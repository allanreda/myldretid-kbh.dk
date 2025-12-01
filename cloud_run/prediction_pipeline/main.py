from google.cloud import bigquery, storage, secretmanager
from PredictionPipeline import PredictionPipeline
from shared.PreProcessing import PreProcessing
from shared.CloudUtils import CloudUtils
import numpy as np
from datetime import date, datetime
import io
from zoneinfo import ZoneInfo 
from datetime import datetime
import time
from flask import Request, Response
import functions_framework
import base64
import os
import json
from pathlib import Path

@functions_framework.http
def predict(request: Request):
    """Triggered from a Pub/Sub message via HTTP."""
    try:
        # Define the time zone
        cet_timezone = ZoneInfo('Europe/Copenhagen')

        # Get the current date and time
        current_datetime = datetime.now(cet_timezone)
        current_date = current_datetime.strftime('%Y-%m-%d')
        current_time = current_datetime.strftime('%H:%M')
        
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

        # Load holidays file
        with open(Path(__file__).parent / "shared" / "holidays.json", encoding="utf-8") as f:
            manual_holidays = json.load(f)

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
                                                                                                    f"{bucket_name}-models",
                                                                                                    '1_day_prediction_model')

        # Predict the next 8 rush hours after the first 2 and compare to average traveltime
        next_4_mornings_traffic, next_4_afternoons_traffic = predict.predict_next_8_rush_hour_periods_wrapper(historical_df, 
                                                                                                            forecast_df, 
                                                                                                            manual_holidays,
                                                                                                            f"{bucket_name}-models",
                                                                                                            '2_day_prediction_model')


        # Concatenate all dates
        all_morning_predictions = np.concatenate([next_morning_traffic, next_4_mornings_traffic])
        all_afternoon_predictions = np.concatenate([next_afternoon_traffic, next_4_afternoons_traffic])
        # Define and map dates to predictions
        json_predictions = predict.define_dates_and_convert_json(all_morning_predictions, all_afternoon_predictions, cet_timezone)

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

        return Response("Prediction completed successfully", 200)

    except Exception as e:
        print(f"Error: {e}")
        return Response(f"Error occurred, but acknowledged to prevent retry: {e}", status=200)