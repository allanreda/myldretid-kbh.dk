import joblib
import importlib # Remove in prod
import local_development.preprocessing_class  # Remove in prod
importlib.reload(local_development.preprocessing_class)  # Remove in prod
from local_development.preprocessing_class import PreProcessing
import os
from google.cloud import bigquery
from pathlib import Path

# Initialize the BigQuery client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/hyggeskyen_service_account.json'
bq_client = bigquery.Client()

# Import OpenWeather API key
openweather_api_key = Path("C:/Users/allan/Desktop/Personlige projekter/openweather_api_key.txt").read_text()

# Instantiate PreProcessing class
preprocesser = PreProcessing(bq_client, openweather_api_key)

fetched_df = preprocesser.pull_weather_forecast()


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

morning_df, afternoon_df = preprocesser.training_preprocessing(fetched_df, manual_holidays)









# Load joblib files from the training pipeline
morning_bundle = joblib.load("morning_model.joblib")
model = morning_bundle["model"]
scaler = morning_bundle["scaler"]
expected_columns = morning_bundle["columns"]






# When using new data:
new_data = new_df[expected_columns]
scaled_data = scaler.transform(new_data)
predictions = model.predict(scaled_data)
