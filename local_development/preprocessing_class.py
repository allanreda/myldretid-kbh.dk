import os
import holidays
import pandas as pd
from astral.sun import sun
from astral import LocationInfo
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PreProcessing:
    def __init__(self, bq_client, openweather_api_key):
        self.bq_client
        self.openweather_api_key
    
    # Function to fetch historical weather and traffic data from BigQuery
    def pull_historical_data(self, sql_query):
        try:
            # Define SQL query
            query = sql_query

            # Run the query and fetch data from BigQuery
            query_job = self.bq_client.query(query)

            # Convert to DataFrame
            raw_df = query_job.to_dataframe()

            # Ensure dataframe exists and actually contains data
            if len(raw_df) > 10000:
                logger.info(f"Succesfully fetched {len(raw_df)} rows of historical data from BigQuery")
                return raw_df
            
        except Exception as e:
            logger.error(f"Error occured when fetching historical data from BigQuery: {e}")
            return None
    

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

        try:
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

            logger.info("Preprocessing: Succesfully grouped data by rush hour")
            return grouped_df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in grouping data by rush hour period: {e}")
            return None

    # Function to include holidays in the dataframe
    def include_holidays(self, df, manual_holidays):
        try:
            # Convert date column to datetime 
            df['date'] = pd.to_datetime(df['date'])
            # Get all years that are present in the dataframe
            years = df['date'].dt.year.unique()

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

            # Create binary column: 1 if date is a holiday, 0 if not
            df['is_holiday'] = df['date'].dt.date.isin(all_holiday_dates).astype(int)
            
            logger.info("Preprocessing: Succesfully included holidays into dataframe.")
            return df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in including holidays in dataframe: {e}")
            return None

    # Function to create dummy columns
    def create_dummies(self, df, column, prefix):
        try:

            # Create dummy variables for day names
            dummies = pd.get_dummies(df[column], prefix=prefix, drop_first=True)
            
            # Concatenate dummy columns to dataframe
            df = pd.concat([df, dummies], axis=1)
            
            # Drop column
            df = df.drop(column, axis = "columns")
            
            logger.info(f"Preprocessing: Succesfully created dummy-columns for column {column}.")
            return df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in creating dummies for column '{column}': {e}")
            return None
        
    def create_dayname_dummies(self, df):
        try:
            # Convert date column to datetime 
            df['date'] = pd.to_datetime(df['date'])
            # Extract day name 
            df['day_name'] = df['date'].dt.day_name()
            # Create day name dummies
            df = self.create_dummies(df, 'day_name', 'day')

            return df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in creating day name dummies: {e}")
            return None

    # Calculate sunrise and sunset for each date
    def get_cph_sun_times(self, date):
        # Define location
        city = LocationInfo("Copenhagen", "Denmark", "Europe/Copenhagen")
        
        s = sun(city.observer, date=date, tzinfo=city.timezone)
        return pd.Series({"sunrise": s["sunrise"].hour + s["sunrise"].minute/60,
                        "sunset": s["sunset"].hour + s["sunset"].minute/60})


    # Map sunrise and sunset for each date into dataframe
    def map_sun_times(self, df):
        try:
            # Apply get_sun_times function to each row in dataframe
            df[['sunrise', 'sunset']] = df['date'].apply(self.get_cph_sun_times)

            logger.info("Preprocessing: Succesfully mapped sun times into dataframe.")
            return df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in mapping sun times: {e}")
            return None
    
    # Function to calculate travel time lag by x amount of days
    def calculate_travel_time_lag(self, df, lag, column_name):
        try:
            # Sort values based on date and rush_hour_period
            df = df.sort_values(["rush_hour_period", "date"])

            # Calculate lag and input in dataframe
            df[column_name] = df.groupby("rush_hour_period")["current_travel_time"].shift(lag)

            logger.info(f"Preprocessing: Succesfully calculated and mapped {lag} day lag.")
            return df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in calculating and mapping {lag} day lag: {e}")
            return None

    # Function to calculate rolling average of travel time by x amount of time
    def calculate_rolling_avg(self, df, window, column_name):
        try:
            # Set multi-index with rush_hour_period and date
            df_indexed = df.set_index(["rush_hour_period", "date"])
            # Perform rolling within each rush hour group
            rolling_avg = (
                df_indexed.groupby(level=0)["current_travel_time"]
                .rolling(window=window, min_periods=1)
                .mean()
                .reset_index(level=0, drop=True)  # Remove rush_hour_period from index after rolling
            )

            # Add the result as a new column
            df[column_name] = rolling_avg.values

            logger.info(f"Preprocessing: Succesfully calculated and mapped {window} day rolling average.")
            return df

        except Exception as e:
            logger.error(f"Preprocessing: Error occured in calculating and mapping {window} day rolling average: {e}")
            return None


    def minor_transformations(self, df):
        try:
            # Convert all boolean columns to 1/0
            df[df.select_dtypes(bool).columns] = df.select_dtypes(bool).astype(int)
            # Drop all rows with missing values
            df = df.dropna(axis=0)

            logger.info(f"Preprocessing: Succesfully performed minor data transformations.")
            return df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in performing minor data transformations: {e}")
            return None

    def training_preprocessing(self, raw_df, manual_holidays):

        df = self.group_by_rush_hour(raw_df)

        df = self.include_holidays(df, manual_holidays)

        df = self.create_dummies(df, 'weather_main', 'weather_main')

        df = self.create_dayname_dummies(df)

        df = self.map_sun_times(df)

        df = self.calculate_travel_time_lag(df, 1, 'lag_1day')
        df = self.calculate_travel_time_lag(df, 7, 'lag_7day')

        df = self.calculate_rolling_avg(df, 7, 'rolling_avg_7day')






