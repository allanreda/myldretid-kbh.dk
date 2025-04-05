from google.cloud import bigquery
import pandas as pd
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/hyggeskyen_service_account.json'

# Initialize the BigQuery client
bq_client = bigquery.Client()

# Define SQL query
query = """
SELECT 
      traffic.*,
      weather.weather_main,
      weather.weather_description,
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
"""

# Run the query and fetch data from BigQuery
query_job = bq_client.query(query)
# Convert to DataFrame
raw_df = query_job.to_dataframe()

########################### DATA HANDLING ###########################

# Copy raw dataframe to another one for cleaning 
cleaned_df = raw_df.copy()

# Define rush our times
rush_hours = ["07:00", "08:00", "09:00", "15:00", "16:00", "17:00"]
# Exctract the rush hour rows and remove the rest
cleaned_df = cleaned_df[cleaned_df["time"].isin(rush_hours)]

# Function to define morning and afternoon rush hours
def rush_hour_period(time_column):
    if time_column in ["07:00", "08:00", "09:00"]:
        return "morning"
    else:
        return "afternoon"
# Apply function row by row
cleaned_df["rush_hour_period"] = cleaned_df["time"].apply(rush_hour_period)


def collapse_road_closure(values):
    return "true" if "yes" in values.values else "false"

def most_frequent_weather(values):
    return values.mode().iloc[0] if not values.mode().empty else None

def most_frequent_weather(values):
    weather = values["weather_main"]
    times = values["time"]

    mode = weather.mode()

    # If there's a single mode → return it
    if len(mode) == 1:
        return mode.iloc[0]
    
    # Tie: return the weather from the middle hour
    # Define middle hours for each rush period
    if "08:00" in times.values:
        middle_time = "08:00"
    elif "16:00" in times.values:
        middle_time = "16:00"
    else:
        middle_time = times.values[len(times) // 2]  # fallback

    # Find the weather at the middle time
    try:
        return weather[times == middle_time].values[0]
    except IndexError:
        return None


test_df = cleaned_df.groupby(["geo_name", "date", "rush_hour_period"])["weather_main"].apply(most_frequent_weather)
