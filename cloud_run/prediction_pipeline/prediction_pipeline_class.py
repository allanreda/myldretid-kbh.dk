import json
import logging
import sys
import pandas as pd
from datetime import date, datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PredictionPipeline:
    def __init__(self, cloud_utils_class, preprocessing_class):
        self.cloud_utils = cloud_utils_class
        self.preprocesser = preprocessing_class

    def combine_historical_with_forecast(self, historical_df, forecast_df):
        try:
            # Add the missing column to forecast_df with NaN values
            if 'current_travel_time' not in forecast_df.columns:
                forecast_df['current_travel_time'] = pd.NA
            
            # Reorder columns to match historical_df
            forecast_df = forecast_df[historical_df.columns]
            
            # Combine using pd.concat (acts like SQL UNION ALL)
            combined_df = pd.concat([historical_df, forecast_df], ignore_index=True)

            logger.info("Successfully combined last 8 days data with the 5 day forecast")
            return combined_df
        except Exception as e:
            logger.error(f"Failed to combine last 8 days data with the 5 day forecast: {e}")
            return None
        
    def calculate_percentage_diff(self, predicted, average):
        percentage_diff = ((predicted - average) / average) * 100
        return percentage_diff
    
    def calculate_percentage_diff_4_days(self, predictions, average):
        percentage_diff_list = []
        for prediction in predictions:
            pred = self.calculate_percentage_diff(prediction, average)
            percentage_diff_list.append(pred)
        return percentage_diff_list

    # Function to predict a rush hour period 
    def predict(self, X_values, model, scaler, expected_columns, rush_hour_period):
        try:
            # Reindex to match the expected column order from training
            # Also removes columns that are not existing in expected_columns
            X_aligned = X_values.reindex(columns=expected_columns, fill_value=0)
            
            # Scale X columns and predict
            X_scaled = scaler.transform(X_aligned)
            prediction = model.predict(X_scaled)

            logger.info(f"Successfully predicted next {rush_hour_period}")
            return prediction
        
        except Exception as e:
            logger.error(f"Error occured when predicting for next {rush_hour_period}: {e}")
            return None
    
    # Function to run prediction pipeline for the next rush hour period
    def predict_next_rush_hour_period(self, bucket_name, joblib_filename, rush_hour_period, X_values):
        try:
            logger.info(f"Started prediction pipeline for next {rush_hour_period}.")
            # Load elements from joblib file
            model, scaler, expected_columns, avg_traveltime = self.cloud_utils.load_model_from_gcs(bucket_name, joblib_filename, rush_hour_period)
            # Predict next rush hour period
            prediction = self.predict(X_values, model, scaler, expected_columns, rush_hour_period)
            # Calculate how many percent prediction differs from average
            percentage_diff = self.calculate_percentage_diff(prediction, avg_traveltime)
            
            logger.info(f"Successfully finished prediction pipeline for next {rush_hour_period}.")
            return percentage_diff
        
        except Exception as e:
            logger.error(f"Error occured in prediction pipeline for next {rush_hour_period}: {e}")
            return None
    
    # Wrapper function to run prediction pipelines for both next morning and afternoon
    def predict_next_rush_hour_periods_wrapper(self, historical_df, forecast_df, manual_holidays, gcs_bucket, filename):
        try:
            logger.info("Started prediction pipeline for both next morning and afternoon.")
            # Combine historical data with forecast data
            combined_df = self.combine_historical_with_forecast(historical_df, forecast_df)

            # Dataframes to predict the next 1 day only (contains lag_1day and rolling_avg_7day)
            morning_df, afternoon_df, _, _ = self.preprocesser.execute_preprocessing_1_day(combined_df, manual_holidays)

            # Get next days values
            next_morning = morning_df.iloc[[-5]]
            next_afternoon = afternoon_df.iloc[[-5]]

            # Calculate avg morning travel time for next_afternoon, but only if its before 9 or after 15
            # This will make it possible to run the 1_day_prediction_model that has both lag_1_day and rolling_avg variables.
            # 1_day_prediction_model requires the morning_travel_time variable
            if datetime.now().hour <= 8 or datetime.now().hour > 15:
                next_afternoon['morning_travel_time'] = morning_df['current_travel_time'].dropna().mean()

            # Predict next mornings traveltime and compare to average traveltime
            next_morning_traffic = self.predict_next_rush_hour_period(gcs_bucket,
                                                                        filename, 
                                                                        'morning', 
                                                                        next_morning)
            # Predict next afternoons traveltime and compare to average traveltime
            # Note: Should ideally be run before 15 but after 9 to get the correct morning_traveltime value included.
            next_afternoon_traffic = self.predict_next_rush_hour_period(gcs_bucket,
                                                                        filename, 
                                                                        'afternoon', 
                                                                        next_afternoon)
            logger.info("Finished prediction pipeline for both next morning and afternoon.")
            return next_morning_traffic, next_afternoon_traffic
        
        except Exception as e:
            logger.error(f"Error occured in prediction pipeline for both next morning and afternoon: {e}")
            return None, None

    def predict_next_4_rush_hour_periods(self, bucket_name, joblib_filename, rush_hour_period, X_values):
        try:
            logger.info(f"Started prediction pipeline for next 4 {rush_hour_period}.")
            # Load elements from joblib file
            model, scaler, expected_columns, avg_traveltime = self.cloud_utils.load_model_from_gcs(bucket_name, joblib_filename, rush_hour_period)
            # Predict next rush hour period
            prediction = self.predict(X_values, model, scaler, expected_columns, rush_hour_period)
            # Calculate how many percent prediction differs from average
            percentage_diff_list = self.calculate_percentage_diff_4_days(prediction, avg_traveltime)
            
            logger.info(f"Successfully finished prediction pipeline for next 4 {rush_hour_period}.")
            return percentage_diff_list
        
        except Exception as e:
            logger.error(f"Error occured in prediction pipeline for next 4 {rush_hour_period}: {e}")
            return None
        
    # Wrapper function to run prediction pipelines for the next 8 rush hours after the first 2
    def predict_next_8_rush_hour_periods_wrapper(self, historical_df, forecast_df, manual_holidays, gcs_bucket, filename):
        try:
            logger.info("Started prediction pipeline for next 8 rush hours")
            # Combine historical data with forecast data
            combined_df = self.combine_historical_with_forecast(historical_df, forecast_df)

            # Dataframes to predict the next 1 day only (contains lag_1day and rolling_avg_7day)
            next_4_morning_df, next_4_afternoon_df, _, _ = self.preprocesser.execute_preprocessing_2_day(combined_df, manual_holidays)

            # Get values for the next 4 days
            next_4_mornings = next_4_morning_df.iloc[-4:]
            next_4_afternoons = next_4_afternoon_df.iloc[-4:]

            # Predict next 4 days traveltime and compare to average traveltime
            next_4_mornings_traffic = self.predict_next_4_rush_hour_periods(gcs_bucket,
                                                                            filename, 
                                                                            'morning', 
                                                                            next_4_mornings)
            next_4_afternoons_traffic = self.predict_next_4_rush_hour_periods(gcs_bucket,
                                                                              filename,
                                                                              'afternoon', 
                                                                              next_4_afternoons)
            
            logger.info("Finished prediction pipeline for next 8 rush hours.")
            return next_4_mornings_traffic, next_4_afternoons_traffic
        
        except Exception as e:
            logger.error(f"Error occured in prediction pipeline for next 8 rush hours: {e}")
            return None, None

    def define_dates_and_convert_json(self, all_morning_predictions, all_afternoon_predictions, cet_timezone):
        try:
            # Get todays date + 4 next dates
            today = date.today()
            dates = [today + timedelta(days=i) for i in range(5)]

            # Get the hour of right now
            hour = datetime.now(cet_timezone).hour

            # If the time is between 9 and 15, then add 1 day to the dates for the morning predictions only
            if hour >= 9 and hour < 15:
                morning_prediction_dict = dict(zip([d + timedelta(days=1) for d in dates], all_morning_predictions))
                afternoon_prediction_dict = dict(zip(dates, all_afternoon_predictions))
            # If the time is above 15, then add 1 day to the dates of both the morning and afternoon predictions
            elif hour >=15:
                morning_prediction_dict = dict(zip([d + timedelta(days=1) for d in dates], all_morning_predictions))
                afternoon_prediction_dict = dict(zip([d + timedelta(days=1) for d in dates], all_afternoon_predictions))
            else:
                morning_prediction_dict = dict(zip(dates, all_morning_predictions))
                afternoon_prediction_dict = dict(zip(dates, all_afternoon_predictions))

            # Convert to json dict
            result = {
                "morning_predictions": {
                    str(k): round(float(v), 2) for k, v in morning_prediction_dict.items()
                },
                "afternoon_predictions": {
                    str(k): round(float(v), 2) for k, v in afternoon_prediction_dict.items()
                }
            }

            # Convert the dict to a json string
            json_string = json.dumps(result, indent=2)

            logger.info("Succesfully defined and mapped dates to predictions.")
            return json_string
        
        except Exception as e:
            logger.error(f"Error occured in defining and mapping dates to predictions: {e}")
            return None
        
