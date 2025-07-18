import joblib
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TrainingPipeline:
    def __init__(self, reducer_class, preprocesser_class, machinelearning_class):
        self.reducer = reducer_class
        self.preprocesser = preprocesser_class
        self.machinelearning = machinelearning_class

    def run_training_pipeline(self, historical_weather_data, manual_holidays, joblib_filename, preprocesser_pipeline):
        try:
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Started training pipeline for {joblib_filename} on {current_datetime}.")
            # Run the preprocessing pipeline for the historical data
            morning_df, afternoon_df = preprocesser_pipeline(historical_weather_data, manual_holidays)

            # Run the multicollinearity reduction pipeline on both dataframes
            morning_df = self.reducer.execute_reduction(morning_df, 'morning_df')
            afternoon_df = self.reducer.execute_reduction(afternoon_df, 'afternoon_df')

            # Validate model performance on both dataframes
            morning_results = self.machinelearning.validate_model(morning_df, "morning_df")
            afternoon_results = self.machinelearning.validate_model(afternoon_df, "afternoon_df")
            # Train models on full data of both dataframes
            morning_model, morning_scaler, morning_columns = self.machinelearning.train_model(morning_df, "morning_df")
            afternoon_model, afternoon_scaler, afternoon_columns = self.machinelearning.train_model(afternoon_df, "afternoon_df")

            # Save model, scaler, and columns to joblib file
            joblib.dump({
                "morning_model": morning_model,
                "morning_scaler": morning_scaler,
                "morning_results": morning_results,
                "morning_columns": morning_columns,
                "afternoon_model": afternoon_model,
                "afternoon_scaler": afternoon_scaler,
                "afternoon_results": afternoon_results,
                "afternoon_columns": afternoon_columns
            }, f"{joblib_filename}.joblib")

            logger.info(f"Successfully completed training pipeline for {joblib_filename}.")

        except Exception as e:
            logger.error(f"Error occured in training pipeline for {joblib_filename}: {e}")

