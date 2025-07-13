import numpy as np
import pandas as pd
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MulticollinearityReducer:
    def __init__(self, target_column, corr_threshold=0.7, vif_threshold=10):
        self.target_column = target_column
        self.corr_threshold = corr_threshold
        self.vif_threshold = vif_threshold

    # Function to check for mulitcollinearity and reduce where relevant
    def reduce_by_correlation(self, df):
        try:
            # Drop target column
            X_df = df.drop(columns=[self.target_column])

            # Generate correlation matrix
            corr_matrix = X_df.corr(numeric_only=True).abs()
            # Get the upper triangle of the correlation matrix
            upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

            # Find columns with high correlation
            to_drop_corr = [column for column in upper.columns if any(upper[column] > self.corr_threshold)]

            # Drop the higly correlated columns
            df = df.drop(columns=to_drop_corr)

            # Convert all columns to float64
            df = df.astype('float64')

            logger.info(f"Multicollinearity Reduction: Successfully dropped following columns due to high correlation: {to_drop_corr}")
            return df
        
        except Exception as e:
            logger.error(f"Multicollinearity Reduction: Error occured when reducing variables by correlation: {e}")
            return None
        

    # Function to calculate VIF
    def calculate_vif(self, df):
        try:
            # Drop constant columns (columns with on 0's)
            df = df.loc[:, df.nunique() > 1]
            # Create empty dataframe for VIF
            vif = pd.DataFrame()
            # Add constant variable to the dataframe
            df = add_constant(df) 
            # Get all columns names into VIF table
            vif["feature"] = df.columns
            # Calculate VIF for each variable
            vif["VIF"] = [variance_inflation_factor(df.values, i) for i in range(df.shape[1])]
            return vif
        
        except Exception as e:
            logger.error(f"Multicollinearity Reduction: Error occured when calculating VIF: {e}")
            return None
    
    # Function to check VIF and drop where relevant
    def reduce_by_vif(self, df):
        try:
            # Drop target column
            X_df = df.drop(columns=[self.target_column])

            # While loop that keeps running until all the values are below the threshold
            while True:
                # Calculate VIF for all the variables
                vif = self.calculate_vif(X_df)
                # Drop the const value
                vif = vif[vif["feature"] != "const"]
                # Get the variable with the highest VIF
                max_vif = vif["VIF"].max()

                # If the highest VIF is below the threshold then break
                if max_vif < self.vif_threshold:
                    break
                # Else, get the name 
                feature_to_drop = vif.sort_values("VIF", ascending=False)["feature"].iloc[0]
                # and drop it from the dataframe
                try:
                    X_df = X_df.drop(columns=[feature_to_drop])
                    logger.info(f"Dropping '{feature_to_drop}' with VIF = {max_vif:.2f}")
                except Exception as e:
                    logger.error(f"Could not drop feature in {df} because of the error: {e}")
            
            # Merge target column back into the original dataframe
            X_df[self.target_column] = df[self.target_column]
            
            logger.info(f"Multicollinearity Reduction: Successfully finished VIF reduction.")
            return X_df
        
        except Exception as e:
            logger.error(f"Multicollinearity Reduction: Error occured when reducing with VIF: {e}")
            return None
    
    # Wrapper function to run the reduction pipeline
    def execute_reduction(self, df):
        try:
            df = self.reduce_by_correlation(df)
            df = self.reduce_by_vif(df)

            logger.info("Multicollinearity Reduction: Successfully completed multicollinearity reduction pipeline.")
            return df
        
        except Exception as e:
            logger.error(f"Multicollinearity reduction pipeline failed: {e}")
            return None