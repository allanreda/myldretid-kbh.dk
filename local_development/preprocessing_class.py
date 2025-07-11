import os
import holidays
import datetime
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
    def most_frequent_weather(self, series):
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
    

    def group_by_rush_hour(self, df):

        # Define rush our times
        rush_hours = ["07:00", "08:00", "09:00", "15:00", "16:00", "17:00"]
        # Exctract the rush hour rows and remove the rest
        df = df[df["time"].isin(rush_hours)]

        # Apply function row by row, to define morning and afternoon rush hour periods
        df["rush_hour_period"] = df["time"].apply(self.rush_hour_period)

        # Group the dataframe by rush_hour_period and aggregate columns
        grouped_df = df.groupby(
            ["date", "rush_hour_period"], as_index=False
        ).agg({                    
            "current_travel_time": "mean",                
            "weather_main": self.most_frequent_weather,
            "temperature": "mean",
            "feels_like": "mean",
            "humidity_percent": "mean",
            "visibility": "mean",
            "wind_speed": "mean",
            "cloudiness_percent": "mean"
        })

        return grouped_df
