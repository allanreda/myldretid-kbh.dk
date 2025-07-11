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
