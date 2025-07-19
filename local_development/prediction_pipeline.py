import joblib
import sys
import importlib # Remove in prod
import os
from google.cloud import bigquery
from pathlib import Path
import pandas as pd
importlib.reload(sys.modules['local_development.preprocessing_class'])
from local_development.preprocessing_class import PreProcessing

# Initialize the BigQuery client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/hyggeskyen_service_account.json'
bq_client = bigquery.Client()

# Import OpenWeather API key
openweather_api_key = Path("C:/Users/allan/Desktop/Personlige projekter/openweather_api_key.txt").read_text()

# Instantiate PreProcessing class
preprocesser = PreProcessing(bq_client, openweather_api_key)

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

forecast_df = preprocesser.pull_weather_forecast()

# Reorder forecast_df columns to match historical_df (excluding the missing column)
common_columns = [col for col in historical_df.columns if col in forecast_df.columns]
# Add the missing column to forecast_df with NaN values
if 'current_travel_time' not in forecast_df.columns:
    forecast_df['current_travel_time'] = pd.NA
# Reorder columns to match historical_df
forecast_df = forecast_df[historical_df.columns]
# Combine using pd.concat (acts like SQL UNION ALL)
combined_df = pd.concat([historical_df, forecast_df], ignore_index=True)

def calculate_percentage_diff(predicted, average):
    percentage_diff = ((predicted - average) / average) * 100
    return percentage_diff

########## Next DAY ############
# Dataframes to predict the next 1 day only (contains lag_1day and rolling_avg_7day)
morning_df, afternoon_df, _, _ = preprocesser.execute_preprocessing_1_day(combined_df, manual_holidays)

next_morning = morning_df.iloc[[-5]]

# Load joblib files from the training pipeline
one_day_prediction_bundle = joblib.load("1_day_prediction_model.joblib")
one_day_morning_model = one_day_prediction_bundle["morning_model"]
one_day_morning_scaler = one_day_prediction_bundle["morning_scaler"]
one_day_morning_expected_columns = one_day_prediction_bundle["morning_columns"]
avg_morning_traveltime = one_day_prediction_bundle["avg_morning_traveltime"]

# Reindex to match the expected column order from training
# Ensure all expected columns are present (adds missing columns with 0)
next_morning_aligned = next_morning.reindex(columns=one_day_morning_expected_columns, fill_value=0)
next_morning_X_scaled = one_day_morning_scaler.transform(next_morning_aligned)
next_morning_prediction = one_day_morning_model.predict(next_morning_X_scaled)

next_morning_compared_to_avg = calculate_percentage_diff(next_morning_prediction, avg_morning_traveltime)


#TODO Lav næste aften også (skal laves før kl 15)
next_afternoon = afternoon_df.iloc[[-5]]

# Load joblib files from the training pipeline
one_day_prediction_bundle = joblib.load("1_day_prediction_model.joblib")
one_day_afternoon_model = one_day_prediction_bundle["afternoon_model"]
one_day_afternoon_scaler = one_day_prediction_bundle["afternoon_scaler"]
one_day_afternoon_expected_columns = one_day_prediction_bundle["afternoon_columns"]
avg_afternoon_traveltime = one_day_prediction_bundle["avg_afternoon_traveltime"]

# Reindex to match the expected column order from training
# Ensure all expected columns are present (adds missing columns with 0)
next_afternoon_aligned = next_afternoon.reindex(columns=one_day_afternoon_expected_columns, fill_value=0)
next_afternoon_X_scaled = one_day_afternoon_scaler.transform(next_afternoon_aligned)
next_afternoon_prediction = one_day_afternoon_model.predict(next_afternoon_X_scaled)

next_afternoon_compared_to_avg = calculate_percentage_diff(next_afternoon_prediction, avg_afternoon_traveltime)


#______________________
# Dataframes to predict the day after tomorrow and 3 days forwad
two_day_morning_df, two_day_afternoon_df, _, _ = preprocesser.execute_preprocessing_2_day(combined_df, manual_holidays)


next_4_mornings = two_day_morning_df.iloc[-4:]

# Load joblib files from the training pipeline
two_day_prediction_bundle = joblib.load("2_day_prediction_model.joblib")
two_day_morning_model = two_day_prediction_bundle["morning_model"]
two_day_morning_scaler = two_day_prediction_bundle["morning_scaler"]
two_day_morning_expected_columns = two_day_prediction_bundle["morning_columns"]
avg_morning_traveltime = two_day_prediction_bundle["avg_morning_traveltime"]


# Reindex to match the expected column order from training
# Ensure all expected columns are present (adds missing columns with 0)
next_4_mornings_aligned = next_4_mornings.reindex(columns=two_day_morning_expected_columns, fill_value=0)
next_4_mornings_X_scaled = two_day_morning_scaler.transform(next_4_mornings_aligned)
next_4_mornings_prediction = two_day_morning_model.predict(next_4_mornings_X_scaled)

next_4_mornings_compared_to_avg = []
for prediction in next_4_mornings_prediction:
    pred = calculate_percentage_diff(prediction, avg_morning_traveltime)
    next_4_mornings_compared_to_avg.append(pred)


#TODO Lav næste 4 aftener også (skal laves før kl 15)
next_4_afternoons= two_day_afternoon_df.iloc[-4:]

# Load joblib files from the training pipeline
two_day_prediction_bundle = joblib.load("2_day_prediction_model.joblib")
two_day_afternoon_model = two_day_prediction_bundle["afternoon_model"]
two_day_afternoon_scaler = two_day_prediction_bundle["afternoon_scaler"]
two_day_afternoon_expected_columns = two_day_prediction_bundle["afternoon_columns"]

# Reindex to match the expected column order from training
# Ensure all expected columns are present (adds missing columns with 0)
next_4_afternoons_aligned = next_4_mornings.reindex(columns=two_day_afternoon_expected_columns, fill_value=0)
next_4_afternoons_X_scaled = two_day_afternoon_scaler.transform(next_4_afternoons_aligned)
next_4_afternoons_prediction = two_day_afternoon_model.predict(next_4_afternoons_X_scaled)






import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
pio.renderers.default = "browser"

# Your data (converted to float for plotting)
values = [-0.24, -1.72, -7.49, -6.08]

# Create a subplot with 4 gauge charts side by side
fig = make_subplots(
    rows=1, cols=4,
    specs=[[{'type': 'indicator'}]*4],
    subplot_titles=["Day 1", "Day 2", "Day 3", "Day 4"]
)

# Create a gauge for each value
for i, val in enumerate(values):
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=val,
        number={'suffix': '%'},
        delta={'reference': 0, 'relative': False},
        gauge={
            'axis': {'range': [-20, 5], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "royalblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 0
            }
        },
        domain={'row': 0, 'column': i}
    ), row=1, col=i+1)

fig.update_layout(
    title_text="Next 4 Mornings Compared to Avg Travel Time",
    height=300
)

fig.show()