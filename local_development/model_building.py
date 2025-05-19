from google.cloud import bigquery
import pandas as pd
import numpy as np
import os
import holidays
import datetime

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

# Function to collapse road_closure column in aggregation
def collapse_road_closure(values):
    return "true" if "yes" in values.values else "false"

def most_frequent_weather(series):
    mode = series.mode()
    if len(mode) == 1:
        return mode.iloc[0]

    # Get time from index or fallback if not accessible
    try:
        # assumes '08:00' or '16:00' appear in the index (multiindex with time)
        full_group = cleaned_df.loc[series.index]
        if "08:00" in full_group["time"].values:
            middle_time = "08:00"
        elif "16:00" in full_group["time"].values:
            middle_time = "16:00"
        else:
            middle_time = full_group["time"].values[len(full_group) // 2]

        match = full_group[full_group["time"] == middle_time]
        return match["weather_main"].iloc[0] if not match.empty else None
    except:
        return None

grouped_df = cleaned_df.groupby(
    ["date", "rush_hour_period"], as_index=False
).agg({
#    "current_speed": "mean",                         
    "free_flow_speed": "mean",                      
#    "current_travel_time": "mean",                 
#    "free_flow_travel_time": "mean",      
#    "road_closure": collapse_road_closure,      
    "weather_main": most_frequent_weather,
    "weather_description": most_frequent_weather,
    "temperature": "mean",
    "feels_like": "mean",
    "humidity_percent": "mean",
    "visibility": "mean",
    "wind_speed": "mean",
    "cloudiness_percent": "mean"
 })



# Create a new column where the date is converted to datetime
grouped_df['date_dt'] = pd.to_datetime(grouped_df['date'])
# Get all years that are present in the dataframe
years = grouped_df['date_dt'].dt.year.unique()

# Get all Danish holidays from the holidays library
dk_holidays = holidays.Denmark(years=years)

# Add date and name of custom holidays
# (only add those which have the same date each year)
custom_holidays_dict = {
    (12, 31): "New Years Eve",
    (12, 24): "Christmas Eve"  
}

# Empty list for custom holidays
custom_holidays = {}
# Loop to include the custom holidays for all relevant years
for year in years:
    for (month, day), name in custom_holidays_dict.items():
        custom_holidays[datetime.date(year, month, day)] = name

# Update dk_holidays with custom holidays
dk_holidays.update(custom_holidays)

# Map holidays into dataframe
holiday_map = {date: name for date, name in dk_holidays.items()}
grouped_df['holiday_name'] = grouped_df['date_dt'].map(holiday_map)
# Drop column
grouped_df = grouped_df.drop("date_dt", axis='columns')

# Create dummy columns for each holiday
holiday_dummies = pd.get_dummies(grouped_df['holiday_name'], prefix = 'holiday_', drop_first=True)
grouped_df = pd.concat([grouped_df, holiday_dummies], axis=1)
grouped_df = grouped_df.drop("holiday_name", axis = "columns")

# Create dummy columns for each category in weather_main column
weather_main_dummies = pd.get_dummies(grouped_df['weather_main'], prefix = 'weather_main_', drop_first=True)
grouped_df = pd.concat([grouped_df, weather_main_dummies], axis=1)
grouped_df = grouped_df.drop("weather_main", axis = "columns")

# Create dummy columns for each category in weather_description column
weather_description_dummies = pd.get_dummies(grouped_df['weather_description'], prefix = 'weather_description_', drop_first=True)
grouped_df = pd.concat([grouped_df, weather_description_dummies], axis=1)
grouped_df = grouped_df.drop("weather_description", axis = "columns")

########################### SPLIT DATA ###########################

# Split dataframe into morning and afternoon
morning_df = grouped_df[grouped_df["rush_hour_period"] == "morning"].copy()
afternoon_df = grouped_df[grouped_df["rush_hour_period"] == "afternoon"].copy()

# Convert all boolean columns to 1/0
morning_df[morning_df.select_dtypes(bool).columns] = morning_df.select_dtypes(bool).astype(int)
afternoon_df[afternoon_df.select_dtypes(bool).columns] = afternoon_df.select_dtypes(bool).astype(int)

# Drop rush_hour_period, date and holiday columns for the morning since they are the same as for afternoon
morning_features = morning_df.drop(columns=["rush_hour_period"] + [col for col in morning_df.columns if col in holiday_dummies.columns])
# Add prefix for morning features
morning_features = morning_features.add_prefix("morning_") 
# Rename date column
morning_features = morning_features.rename(columns={"morning_date": "date"})

# Merge afternoon_df with morning_features
afternoon_df = pd.merge(
    afternoon_df,
    morning_features,
    how="left",
    on="date"
)

# Drop rush_hour_period and date column for both dataframes
morning_df = morning_df.drop(["rush_hour_period", "date"], axis = "columns")
afternoon_df = afternoon_df.drop(["rush_hour_period", "date"], axis = "columns")

# Drop all rows with missing values
morning_df = morning_df.dropna(axis=0)
afternoon_df = afternoon_df.dropna(axis=0)

########################### CORRELATION ###########################

# Function to check for mulitcollinearity and reduction where relevant
def corr_matrix(df, target_column, corr_percentage = 0.8):
    # Drop target column
    X_df = df.drop(columns=[target_column])

    # Generate correlation matrix
    corr_matrix = X_df.corr(numeric_only=True).abs()
    # Get the upper triangle of the correlation matrix
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

    # Find columns with high correlation
    to_drop_corr = [column for column in upper.columns if any(upper[column] > corr_percentage)]
    # Drop the higly correlated columns
    df_reduced = X_df.drop(columns=to_drop_corr)

    # Convert all columns to float64
    df_reduced = df_reduced.astype('float64')

    return df_reduced

morning_reduced = corr_matrix(morning_df, "free_flow_speed")
afternoon_reduced = corr_matrix(afternoon_df, "free_flow_speed")

from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant

vif = pd.DataFrame()
afternoon_reduced = add_constant(afternoon_reduced) 
vif["feature"] = afternoon_reduced.columns
vif["VIF"] = [variance_inflation_factor(afternoon_reduced.values, i) for i in range(afternoon_reduced.shape[1])]

print(vif)

