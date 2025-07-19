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
        
    def calculate_percentage_diff(predicted, average):
        percentage_diff = ((predicted - average) / average) * 100
        return percentage_diff

    def one_day_load_model_bundle(self, joblib_filename, rush_hour_period):
        try:
            # Load joblib file
            prediction_bundle = joblib.load(f"{joblib_filename}.joblib")
            # Load relevant elements of the joblib file
            model = prediction_bundle[f"{rush_hour_period}_model"]
            scaler = prediction_bundle[f"{rush_hour_period}_scaler"]
            expected_columns = prediction_bundle[f"{rush_hour_period}_columns"]
            avg_traveltime = prediction_bundle[f"{rush_hour_period}_traveltime"]

            logger.info(f"Successfully loaded file {joblib_filename}.joblib and relevant elements")
            return model, scaler, expected_columns, avg_traveltime
        
        except Exception as e:
            logger.error(f"Error occured when loading file {joblib_filename}.joblib and relevant elements: {e}")