import os
import holidays
import datetime
import pandas as pd
from astral.sun import sun
from astral import LocationInfo
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
from sklearn.model_selection import train_test_split, KFold, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.svm import SVR
import xgboost as xgb
from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import ExtraTreesRegressor
from catboost import CatBoostRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV


class PreProcessing:
    def __init__(self, bq_client, openweather_api_key):
        self.bq_client
        self.openweather_api_key
    
    # Function to fetch historical weather and traffic data from BigQuery
    def pull_historical_data(self):
        # Define SQL query
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
        """

        # Run the query and fetch data from BigQuery
        query_job = self.bq_client.query(query)
        # Convert to DataFrame
        raw_df = query_job.to_dataframe()

        return raw_df
    

    # Function to define morning and afternoon rush hours
    def rush_hour_period(self, time_column):
        if time_column in ["07:00", "08:00", "09:00"]:
            return "morning"
        else:
            return "afternoon"
    

    # Function to find most frequent weather in a rush hour period 
    def most_frequent_weather(self, df, series):
        mode = series.mode()
        if len(mode) == 1:
            return mode.iloc[0]

        # Get time from index or fallback if not accessible
        try:
            # assumes '08:00' or '16:00' appear in the index (multiindex with time)
            full_group = df.loc[series.index]
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
    

    def group_by_rush_hour(self, df):

        # Define rush our times
        rush_hours = ["07:00", "08:00", "09:00", "15:00", "16:00", "17:00"]
        # Exctract the rush hour rows and remove the rest
        df = df[df["time"].isin(rush_hours)]

        # Apply function row by row, to define morning and afternoon rush hour periods
        df["rush_hour_period"] = df["time"].apply(self.rush_hour_period)

        # Group the dataframe by rush_hour_period and aggregate columns
        grouped_df = df.apply(lambda g: pd.Series({
            "current_travel_time": g["current_travel_time"].mean(),
            "weather_main": self.most_frequent_weather(df, g["weather_main"]),
            "temperature": g["temperature"].mean(),
            "feels_like": g["feels_like"].mean(),
            "humidity_percent": g["humidity_percent"].mean(),
            "visibility": g["visibility"].mean(),
            "wind_speed": g["wind_speed"].mean(),
            "cloudiness_percent": g["cloudiness_percent"].mean()
        })).reset_index()

        return grouped_df

    # Function to include holidays in the dataframe
    def include_holidays(self, df, manual_holidays):
        # Create a new column where the date is converted to datetime
        df['date_dt'] = pd.to_datetime(df['date'])
        # Get all years that are present in the dataframe
        years = df['date_dt'].dt.year.unique()

        # Get all Danish holidays from the holidays library
        dk_holidays = holidays.Denmark(years=years)

        # Create set from public holidays
        public_holiday_dates = set(dk_holidays.keys())

        # Convert manual holidays into a set of dates
        manual_holiday_dates = set()

        # Get the date range for each holiday
        for start_str, end_str in manual_holidays:
            start = pd.to_datetime(start_str)
            end = pd.to_datetime(end_str)
            date_range = pd.date_range(start, end)
            # Add each date in the date range to manual_holiday_dates
            for date in date_range:
                manual_holiday_dates.add(date.date())

        # Combine both public and manual holidays into one set
        all_holiday_dates = public_holiday_dates.union(manual_holiday_dates)

        # Make sure date column is datetime
        df['date'] = pd.to_datetime(df['date'])

        # Create binary column: 1 if date is a holiday, 0 if not
        df['is_holiday'] = df['date'].dt.date.isin(all_holiday_dates).astype(int)

        # Drop date_dt column
        df = df.drop("date_dt", axis = "columns")

        return df
    

