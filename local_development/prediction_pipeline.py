import joblib
import sys
import os
from google.cloud import bigquery
from pathlib import Path
import pandas as pd
import importlib # Remove in prod
importlib.reload(sys.modules['local_development.preprocessing_class'])
importlib.reload(sys.modules['local_development.prediction_pipeline_class'])
from local_development.preprocessing_class import PreProcessing
from local_development.prediction_pipeline_class import PredictionPipeline
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta
import numpy as np

# Initialize the BigQuery client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/hyggeskyen_service_account.json'
bq_client = bigquery.Client()

# Import OpenWeather API key
openweather_api_key = Path("C:/Users/allan/Desktop/Personlige projekter/openweather_api_key.txt").read_text()

# Instantiate PreProcessing class
preprocesser = PreProcessing(bq_client, openweather_api_key)
# Instantiate PredictionPipeline class
predict = PredictionPipeline()

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

# Calculate avg morning travel time for next_afternoon, but only if its before 9
# This will make it possible to run the 1_day_prediction_model that has both lag_1_day and rolling_avg variables.
# 1_day_prediction_model requires the morning_travel_time variable
if datetime.now().hour < 9:
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

# Get todays date + 4 next dates
today = date.today()
dates = [today + timedelta(days=i) for i in range(5)]

# If the time is between 9 and 15, then add 1 day to the dates for the morning predictions only
if datetime.now().hour >= 9 and datetime.now().hour < 15:
    morning_prediction_dict = dict(zip([d + timedelta(days=1) for d in dates], all_morning_predictions))
    afternoon_prediction_dict = dict(zip(dates, all_afternoon_predictions))
# If the time is above 15, then add 1 day to the dates of both the morning and afternoon predictions
elif datetime.now().hour >=15:
    morning_prediction_dict = dict(zip([d + timedelta(days=1) for d in dates], all_morning_predictions))
    afternoon_prediction_dict = dict(zip([d + timedelta(days=1) for d in dates], all_afternoon_predictions))
else:
    morning_prediction_dict = dict(zip(dates, all_morning_predictions))
    afternoon_prediction_dict = dict(zip(dates, all_afternoon_predictions))


def plot_gauges(morning_prediction_dict, afternoon_prediction_dict):
    # Define weekday and month translations from English to Danish
    weekdays = {
        "Monday": "Mandag", "Tuesday": "Tirsdag", "Wednesday": "Onsdag",
        "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lørdag", "Sunday": "Søndag"
    }
    months = {
        "January": "Januar", "February": "Februar", "March": "Marts", "April": "April",
        "May": "Maj", "June": "Juni", "July": "Juli", "August": "August",
        "September": "September", "October": "Oktober", "November": "November", "December": "December"
    }

    # Convert a date to a Danish-formatted string
    def to_danish_date(d):
        english = d.strftime("%A, %d. %B %Y")
        for en, dk in weekdays.items():
            english = english.replace(en, dk)
        for en, dk in months.items():
            english = english.replace(en, dk)
        return english

    # Create a label for the gauge including icon and Danish date
    def format_label(d, period):
        icon = "🌅" if period == "morning" else "🌇"
        label = "Morgen" if period == "morning" else "Eftermiddag"
        return f"{icon} {to_danish_date(d)} {label}"

    # Choose color based on how much faster/slower traffic is
    def get_color_gradient(val):
        if val < -15:
            return "#05f545"  
        elif val < -10:
            return "#1abc9c"  
        elif val < -5:
            return "#37c477"  
        elif val < 5:
            return "#f4f4f4"  
        elif val < 10:
            return "#f39c12"  
        elif val < 15:
            return "#e67e22" 
        else:
            return "#f70525" 


    # Generate a text description based on the value
    def get_description(val):
        if val < -15:
            return "🚀 Meget hurtigere end normalt"
        elif val < -10:
            return "🚗 Hurtigere end normalt"
        elif val < -5:
            return "👍 En smule hurtigere end normalt"
        elif val < 5:
            return "👌 Omtrent som normalt"
        elif val < 10:
            return "⚠️ En smule langsommere end normalt"
        elif val < 15:
            return "🛑 Langsommere end normalt"
        else:
            return "🪦 Meget langsommere end normalt"

    # Combine all into one list with (date, period, value)
    combined = [(d, "morning", v) for d, v in morning_prediction_dict.items()] + \
               [(d, "afternoon", v) for d, v in afternoon_prediction_dict.items()]

    # Sort by date first
    combined_sorted = sorted(combined, key=lambda x: (x[0], 0 if x[1] == "morning" else 1))

    # First row: next two predictions
    first_two = combined_sorted[:2]

    # Separate remaining morning and afternoon predictions
    remaining_mornings = [x for x in combined_sorted if x[1] == "morning" and x not in first_two][:4]
    remaining_afternoons = [x for x in combined_sorted if x[1] == "afternoon" and x not in first_two][:4]

    # Combine all for plotting
    all_predictions = first_two + remaining_mornings + remaining_afternoons

    # Extract values and labels for the plot
    values = [v for _, _, v in all_predictions]
    labels = [format_label(d, p) for d, p, _ in all_predictions]

    # Layout: 2 gauges on top row, 4 per row below
    specs = [
        [None, {"type": "indicator"}, {"type": "indicator"}, None],
        [{"type": "indicator"} for _ in range(4)],
        [{"type": "indicator"} for _ in range(4)]
    ]

    fig = make_subplots(rows=3, cols=4, specs=specs, subplot_titles=[""] * 10)

    # Place each gauge in its correct subplot cell
    for i, (val, label) in enumerate(zip(values, labels)):
        if i == 0:
            row, col = 1, 2
        elif i == 1:
            row, col = 1, 3
        elif 2 <= i <= 5:
            row, col = 2, i - 1
        else:
            row, col = 3, i - 5

        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=val,
            title={
                "text": f"{label}<br><span style='font-size:14px;color:gray'>{get_description(val)}</span>",
                "font": {"size": 17}
            },
            number={"suffix": "%", "font": {"size": 28, "color": "#2c3e50"}},
            gauge={
                'axis': {'range': [-30, 30], 'tickwidth': 2},
                'bar': {'color': get_color_gradient(val)},
                'threshold': {
                    'line': {'color': "#34495e", 'width': 2},
                    'value': 0
                },
                'bgcolor': "#f9f9f9",
                'bordercolor': "#e0e0e0",
                'borderwidth': 1
            }
        ), row=row, col=col)

    # Define layout
    fig.update_layout(
        height=320 * 3,
        margin=dict(t=140, l=40, r=40, b=40),
        paper_bgcolor='#f0f6ff',
        plot_bgcolor='#f0f6ff',
        font=dict(family="Poppins, Segoe UI, sans-serif", color="#2c3e50")
    )

    fig.show()

plot_gauges(morning_prediction_dict, afternoon_prediction_dict)


def plot_gauges_mobile(morning_prediction_dict, afternoon_prediction_dict):
    # Define weekday and month translations from English to Danish
    weekdays = {
        "Monday": "Mandag", "Tuesday": "Tirsdag", "Wednesday": "Onsdag",
        "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lørdag", "Sunday": "Søndag"
    }
    months = {
        "January": "Januar", "February": "Februar", "March": "Marts", "April": "April",
        "May": "Maj", "June": "Juni", "July": "Juli", "August": "August",
        "September": "September", "October": "Oktober", "November": "November", "December": "December"
    }

    # Convert a date to a Danish-formatted string
    def to_danish_date(d):
        english = d.strftime("%A, %d. %B %Y")
        for en, dk in weekdays.items():
            english = english.replace(en, dk)
        for en, dk in months.items():
            english = english.replace(en, dk)
        return english

    # Create a label for the gauge including icon and Danish date
    def format_label(d, period):
        icon = "🌅" if period == "morning" else "🌇"
        label = "Morgen" if period == "morning" else "Eftermiddag"
        return f"{icon} {to_danish_date(d)} {label}"

    # Choose color based on how much faster/slower traffic is
    def get_color_gradient(val):
        if val < -15:
            return "#05f545"  
        elif val < -10:
            return "#1abc9c"  
        elif val < -5:
            return "#37c477"  
        elif val < 5:
            return "#f4f4f4"  
        elif val < 10:
            return "#f39c12"  
        elif val < 15:
            return "#e67e22" 
        else:
            return "#f70525" 


    # Generate a text description based on the value
    def get_description(val):
        if val < -15:
            return "🚀 Meget hurtigere end normalt"
        elif val < -10:
            return "🚗 Hurtigere end normalt"
        elif val < -5:
            return "👍 En smule hurtigere end normalt"
        elif val < 5:
            return "👌 Omtrent som normalt"
        elif val < 10:
            return "⚠️ En smule langsommere end normalt"
        elif val < 15:
            return "🛑 Langsommere end normalt"
        else:
            return "🪦 Meget langsommere end normalt"

    # Combine all into one list with (date, period, value)
    combined = [(d, "morning", v) for d, v in morning_prediction_dict.items()] + \
               [(d, "afternoon", v) for d, v in afternoon_prediction_dict.items()]

    # Sort by date first
    combined_sorted = sorted(combined, key=lambda x: (x[0], 0 if x[1] == "morning" else 1))

    # Take all 10 sorted predictions chronologically
    all_predictions = combined_sorted[:10]

    # Extract values and formatted labels
    values = [v for _, _, v in all_predictions]
    labels = [format_label(d, p) for d, p, _ in all_predictions]

    # Determine number of rows (2 gauges per row)
    rows = (len(values) + 1) // 2
    specs = [[{"type": "indicator"}, {"type": "indicator"}] for _ in range(rows)]

    fig = make_subplots(rows=rows, cols=2, specs=specs, subplot_titles=[""] * len(values))

    # Add each gauge
    for i, (val, label) in enumerate(zip(values, labels)):
        row = i // 2 + 1
        col = i % 2 + 1

        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=val,
            title={
                "text": f"{label}<br><span style='font-size:14px;color:gray'>{get_description(val)}</span>",
                "font": {"size": 16}
            },
            number={"suffix": "%", "font": {"size": 26, "color": "#2c3e50"}},
            gauge={
                'axis': {'range': [-30, 30], 'tickwidth': 2},
                'bar': {'color': get_color_gradient(val)},
                'threshold': {
                    'line': {'color': "#34495e", 'width': 2},
                    'value': 0
                },
                'bgcolor': "#f9f9f9",
                'bordercolor': "#e0e0e0",
                'borderwidth': 1
            }
        ), row=row, col=col)

    # Define layout
    fig.update_layout(
        height=350 * rows,
        margin=dict(t=140, l=30, r=30, b=40),
        paper_bgcolor='#f0f6ff',
        plot_bgcolor='#f0f6ff',
        font=dict(family="Poppins, Segoe UI, sans-serif", color="#2c3e50"),
    )

    fig.show()

plot_gauges_mobile(morning_prediction_dict, afternoon_prediction_dict)