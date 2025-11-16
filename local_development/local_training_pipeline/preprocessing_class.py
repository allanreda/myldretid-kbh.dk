import holidays
import pandas as pd
pd.options.mode.chained_assignment = None  # Turn off warning
from astral.sun import sun
from astral import LocationInfo
import logging
import sys
import json
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PreProcessing:
    def __init__(self, openweather_api_key):
        self.openweather_api_key = openweather_api_key
    
    # Function to validate each step of the pipeline
    def validate_step(self, df, step_name):
        if df is None:
            raise ValueError(f"Step '{step_name}' failed and returned None.")
        return df

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
            group_keys = ["date", "rush_hour_period"]
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

            # Build aggregation dict
            agg_dict = {}

            for col in df.columns:
                if col in group_keys or col == "time":
                    continue
                elif col == "weather_main":
                    agg_dict[col] = lambda x: self.most_frequent_weather(df, x)
                elif col in numeric_cols:
                    agg_dict[col] = "mean"

            # Group and aggregate
            grouped_df = df.groupby(group_keys, as_index=False).agg(agg_dict)

            logger.info("Preprocessing: Succesfully grouped data by rush hour")
            return grouped_df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in grouping data by rush hour period: {e}", exc_info=True)
            raise

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

            # Mark weekends as holidays too
            is_weekend = df['date'].dt.weekday >= 5  # 5 = Saturday, 6 = Sunday
            is_holiday = df['date'].dt.date.isin(all_holiday_dates)
            # Create binary column: 1 if date is a holiday, 0 if not
            df['is_holiday'] = ((is_holiday) | (is_weekend)).astype(int)
            
            # Get all days that arent holidays
            non_holiday_df = df[df['is_holiday'] == 0]
            # Calculate average traveltime for weekdays only
            avg_morning = non_holiday_df.loc[non_holiday_df['rush_hour_period'] == 'morning', 'current_travel_time'].mean()
            avg_afternoon = non_holiday_df.loc[non_holiday_df['rush_hour_period'] == 'afternoon', 'current_travel_time'].mean()
            
            logger.info("Preprocessing: Succesfully included holidays into dataframe.")
            return df, avg_morning, avg_afternoon
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in including holidays in dataframe: {e}", exc_info=True)
            raise

    # Function to create dummy columns
    def create_dummies(self, df, column, prefix, dummy_to_drop = None):
        try:

            # Create dummy variables for day names
            dummies = pd.get_dummies(df[column], prefix=prefix, drop_first=False)
            
            # Concatenate dummy columns to dataframe
            df = pd.concat([df, dummies], axis=1)
            
            # Drop main column
            df = df.drop(column, axis = "columns")

            # Drop specific dummy column if specified
            if dummy_to_drop:
                df = df.drop(prefix + "_" + dummy_to_drop, axis = "columns")
            
            logger.info(f"Preprocessing: Succesfully created dummy-columns for column {column}.")
            return df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in creating dummies for column '{column}': {e}", exc_info=True)
            raise
        
    def create_dayname_dummies(self, df):
        try:
            # Convert date column to datetime 
            df['date'] = pd.to_datetime(df['date'])
            # Extract day name 
            df['day_name'] = df['date'].dt.day_name()
            # Create day name dummies
            df = self.create_dummies(df, 'day_name', 'day', "Saturday")

            return df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in creating day name dummies: {e}", exc_info=True)
            raise
    
    # Function to merge all dummy weather columns about rain type weather into one
    def merge_rainy_columns(self, df):
        try:
            required_cols = ["weather_main_Drizzle", "weather_main_Mist", "weather_main_Rain"]

            # Skip function if any required column is missing
            if not all(col in df.columns for col in required_cols):
                logger.info("Preprocessing: Skipped merging rainy columns because one or more columns are missing.")
                return df

            # Merge columns
            df["weather_main_Rain"] = df[required_cols].max(axis=1)
            logger.info(f"Preprocessing: Succesfully merged rain type columns into a single column.")
            return df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in merging rain type columns into a single column': {e}", exc_info=True)
            raise

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
            logger.error(f"Preprocessing: Error occured in mapping sun times: {e}", exc_info=True)
            raise
    
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
            logger.error(f"Preprocessing: Error occured in calculating and mapping {lag} day lag: {e}", exc_info=True)
            raise
    
    # Function to replace the 1 day for mondays with the 7 day lag.
    # This is to ensure that the monday predictions is not distorted by the sunday travel times
    def calculate_monday_lag(self, df):
        try:
            # Replace lag_1day with lag_7day where Monday = 1
            df.loc[df["day_Monday"] == 1, "lag_1day"] = df.loc[df["day_Monday"] == 1, "lag_7day"]

            logger.info(f"Preprocessing: Succesfully calculated monday 1 day lag.")
            return df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in calculating monday 1 day lag: {e}", exc_info=True)
            raise


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
            logger.error(f"Preprocessing: Error occured in calculating and mapping {window} day rolling average: {e}", exc_info=True)
            raise


    def convert_booleans(self, df):
        try:
            # Convert all boolean columns to 1/0
            df[df.select_dtypes(bool).columns] = df.select_dtypes(bool).astype(int)

            logger.info(f"Preprocessing: Succesfully converted boolean columns.")
            return df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured when converting boolean columns: {e}", exc_info=True)
            raise
    
    # Function to split dataframe into morning and afternoon dataframes
    def split_data(self, df):
        try:
            # Split dataframe by the rush_hour_period column
            morning_df = df[df["rush_hour_period"] == "morning"].copy()
            afternoon_df = df[df["rush_hour_period"] == "afternoon"].copy()

            # Extract morning travel times
            morning_travel_time = morning_df[['date', 'current_travel_time']].rename(
                columns={'current_travel_time': 'morning_travel_time'}
            )

            # Merge morning travel times with afternoon_df
            afternoon_df = pd.merge(
                afternoon_df,
                morning_travel_time,
                on='date',
                how='left'
            )

            # Drop rush_hour_period and date column for both dataframes
            morning_df = morning_df.drop(["rush_hour_period", "date"], axis = "columns")
            afternoon_df = afternoon_df.drop(["rush_hour_period", "date"], axis = "columns")

            logger.info("Preprocessing: Successfully split dataframe")
            return morning_df, afternoon_df
        
        except Exception as e:
            logger.error(f"Preprocessing: Error occured in splitting dataframe: {e}", exc_info=True)
            raise
        
    def pull_weather_forecast(self):
        try:
            response = requests.get(f'https://api.openweathermap.org/data/2.5/forecast?q=Copenhagen,DK&appid={self.openweather_api_key}')

            if response.status_code == 200:
                # Transform json response
                data = json.loads(response.content)
                # Extract the forecast list
                forecast_list = data['list']
                # Normalize the nested structure
                df = pd.json_normalize(forecast_list)

                # Convert datetime column to datetime object and split
                df['dt_txt'] = pd.to_datetime(df['dt_txt'])
                df['date'] = df['dt_txt'].dt.date
                df['time'] = df['dt_txt'].dt.strftime("%H:%M")
                # Transform nested weather column
                df['weather'] = [entry['weather'][0]['main'] for entry in forecast_list]
                
                # Drop irrelevant columns
                cols_to_drop = [
                    'dt_txt','main.temp_kf','main.temp_min','main.temp_max','main.pressure',
                    'dt','pop','wind.deg','main.grnd_level','main.sea_level','wind.gust',
                    'rain.3h','sys.pod'
                ]
                df = df.drop(columns=cols_to_drop, errors='ignore')

                # Rename relevant columns for clarity
                df = df.rename(columns={
                    'weather': "weather_main", 
                    'main.temp': "temperature", 
                    'main.feels_like': "feels_like",
                    'main.humidity': "humidity_percent", 
                    'clouds.all': "cloudiness_percent", 
                    'wind.speed': "wind_speed"
                })

                # Convert Kelvin to Celcius
                df['temperature'] = df['temperature'] - 273.15 
                df['feels_like'] = df['feels_like'] - 273.15

                logger.info("Successfully fetched weather forecast data")
                return df
            else:
                logger.error("Fetching weather forecast data failed")
        
        except Exception as e:
            logger.error(f"Error occured when fetching and normalizing weather forecast: {e}", exc_info=True)
            raise

    # Wrapper function for training pipeline
    # Can be used to train models to predict 1 day in the future
    def execute_preprocessing_1_day(self, raw_df, manual_holidays):
        try:
            df = self.validate_step(self.group_by_rush_hour(raw_df), "group_by_rush_hour")
            df, avg_morning, avg_afternoon = self.validate_step(self.include_holidays(df, manual_holidays), "include_holidays")
            df = self.validate_step(self.create_dummies(df, 'weather_main', 'weather_main', 'Clouds'), "create_dummies") 
            df = self.validate_step(self.create_dayname_dummies(df), "create_dayname_dummies")
            df = self.validate_step(self.merge_rainy_columns(df), "merge_rainy_columns")
            df = self.validate_step(self.map_sun_times(df), "map_sun_times")
            df = self.validate_step(self.calculate_travel_time_lag(df, 1, 'lag_1day'), "calculate_travel_time_lag_1")
            df = self.validate_step(self.calculate_travel_time_lag(df, 7, 'lag_7day'), "calculate_travel_time_lag_7")
            df = self.validate_step(self.calculate_monday_lag(df), "calculate_monday_lag")
            df = self.validate_step(self.calculate_rolling_avg(df, 7, 'rolling_avg_7day'), "calculate_rolling_avg")
            morning_df, afternoon_df = self.split_data(df)
            if morning_df is None or afternoon_df is None:
                raise ValueError("split_data failed")

            morning_df = self.validate_step(self.convert_booleans(morning_df), "convert_booleans")
            afternoon_df = self.validate_step(self.convert_booleans(afternoon_df), "convert_booleans")

            #morning_df = self.validate_step(self.remove_outliers_5pct(morning_df, 'current_travel_time'), "remove_outliers_morning")
            #afternoon_df = self.validate_step(self.remove_outliers_5pct(afternoon_df, 'current_travel_time'), "remove_outliers_afternoon")


            logger.info("Preprocessing: Successfully completed full training pipeline.")
            return morning_df, afternoon_df, avg_morning, avg_afternoon

        except Exception as e:
            logger.error(f"Preprocessing pipeline failed: {e}")
            return None, None

    # Wrapper function for prediction pipeline
    # Can be used to train models to predict 2 days and more in the future
    def execute_preprocessing_2_day(self, raw_df, manual_holidays):
        try:
            df = self.validate_step(self.group_by_rush_hour(raw_df), "group_by_rush_hour")
            df, avg_morning, avg_afternoon = self.validate_step(self.include_holidays(df, manual_holidays), "include_holidays")
            df = self.validate_step(self.create_dummies(df, 'weather_main', 'weather_main', 'Clouds'), "create_dummies") 
            df = self.validate_step(self.create_dayname_dummies(df), "create_dayname_dummies")
            df = self.validate_step(self.merge_rainy_columns(df), "merge_rainy_columns")
            df = self.validate_step(self.map_sun_times(df), "map_sun_times")
            #df = self.validate_step(self.calculate_travel_time_lag(df, 1, 'lag_1day'), "calculate_travel_time_lag_1")
            df = self.validate_step(self.calculate_travel_time_lag(df, 7, 'lag_7day'), "calculate_travel_time_lag_7")
            #df = self.validate_step(self.calculate_rolling_avg(df, 7, 'rolling_avg_7day'), "calculate_rolling_avg")

            morning_df, afternoon_df = self.split_data(df)
            if morning_df is None or afternoon_df is None:
                raise ValueError("split_data failed")

            morning_df = self.validate_step(self.convert_booleans(morning_df), "convert_booleans")
            afternoon_df = self.validate_step(self.convert_booleans(afternoon_df), "convert_booleans")

            #morning_df = self.validate_step(self.remove_outliers_5pct(morning_df, 'current_travel_time'), "remove_outliers_morning")
            #afternoon_df = self.validate_step(self.remove_outliers_5pct(afternoon_df, 'current_travel_time'), "remove_outliers_afternoon")

            logger.info("Preprocessing: Successfully completed full training pipeline.")
            return morning_df, afternoon_df, avg_morning, avg_afternoon

        except Exception as e:
            logger.error(f"Preprocessing pipeline failed: {e}")
            return None, None