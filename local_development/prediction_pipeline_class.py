import joblib
import logging
import sys
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TrainingPipeline:
    def __init__(self, preprocesser_class):
        self.preprocesser = preprocesser_class

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

    # Function to load elements from joblib created by training pipeline
    def load_model_bundle(self, joblib_filename, rush_hour_period):
        try:
            # Load joblib file
            prediction_bundle = joblib.load(f"{joblib_filename}.joblib")
            # Load relevant elements of the joblib file
            model = prediction_bundle[f"{rush_hour_period}_model"]
            scaler = prediction_bundle[f"{rush_hour_period}_scaler"]
            expected_columns = prediction_bundle[f"{rush_hour_period}_columns"]
            avg_traveltime = prediction_bundle[f"{rush_hour_period}_traveltime"]

            logger.info(f"Successfully loaded file {joblib_filename}.joblib and relevant elements for {rush_hour_period} period")
            return model, scaler, expected_columns, avg_traveltime
        
        except Exception as e:
            logger.error(f"Error occured when loading file {joblib_filename}.joblib and relevant elements for {rush_hour_period} period: {e}")
            return None, None, None, None

    # Function to predict a rush hour period 
    def predict(self, X_values, model, scaler, expected_columns, rush_hour_period):
        try:
            # Reindex to match the expected column order from training
            X_aligned = X_values.reindex(columns=expected_columns, fill_value=0)
            
            # Scale X columns and predict
            X_scaled = scaler.transform(X_aligned)
            prediction = model.predict(X_scaled)

            logger.info(f"Successfully predicted next {rush_hour_period}")
            return prediction
        
        except Exception as e:
            logger.error(f"Error occured when predicting for next {rush_hour_period}: {e}")
            return None
        
    def predict_next_rush_hour_period(self, joblib_filename, rush_hour_period, X_values)
        try:
            logger.info(f"Started prediction pipeline for next {rush_hour_period}.")
            # Load elements from joblib file
            model, scaler, expected_columns, avg_traveltime = self.load_model_bundle(joblib_filename, rush_hour_period)
            # Predict next rush hour period
            prediction = self.predict(X_values, model, scaler, expected_columns, rush_hour_period)
            # Calculate how many percent prediction differs from average
            percentage_diff = self.calculate_percentage_diff(prediction, avg_traveltime)
            
            logger.info(f"Successfully finished prediction pipeline for next {rush_hour_period}.")
            return percentage_diff
        
        except Exception as e:
            logger.error(f"Error occured in prediction pipeline for next {rush_hour_period}: {e}")
            return None
        
    
    def predict_next_4_rush_hour_periods(self, joblib_filename, rush_hour_period, X_values)
        try:
            logger.info(f"Started prediction pipeline for next {rush_hour_period}.")
            # Load elements from joblib file
            model, scaler, expected_columns, avg_traveltime = self.load_model_bundle(joblib_filename, rush_hour_period)
            # Predict next rush hour period
            prediction = self.predict(X_values, model, scaler, expected_columns, rush_hour_period)
            # Calculate how many percent prediction differs from average
            percentage_diff_list = self.calculate_percentage_diff_4_days(prediction, avg_traveltime)
            
            logger.info(f"Successfully finished prediction pipeline for next {rush_hour_period}.")
            return percentage_diff_list
        
        except Exception as e:
            logger.error(f"Error occured in prediction pipeline for next {rush_hour_period}: {e}")
            return None