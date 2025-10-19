import numpy as np
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.ensemble import ExtraTreesRegressor
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MachineLearning:
    def __init__(self, target_column):
        self.target_column = target_column
    
    def validate_model(self, df, df_name):
        try:
            logger.info(f"Validating model {df_name}")
            # X = features, y = target
            X = df.drop(columns=[self.target_column])
            y = df[self.target_column]

            # Cross-validation setup
            cv = KFold(n_splits=10, shuffle=True, random_state=42)

            mse_scores = []
            mae_scores = []
            r2_scores = []
            
            # Loop through each split
            for train_index, test_index in cv.split(X):
                # Split data in traning and test
                X_train, X_test = X.iloc[train_index], X.iloc[test_index]
                y_train, y_test = y.iloc[train_index], y.iloc[test_index]
                
                # Scale the features 
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)

                # Initiate and fit model
                model = ExtraTreesRegressor()
                model.fit(X_train_scaled, y_train)
                # Predict on test data
                y_pred = model.predict(X_test_scaled)

                # Get performance metrics
                mse = mean_squared_error(y_test, y_pred)
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)

                # Append performance metrics to list
                mse_scores.append(mse)
                mae_scores.append(mae)
                r2_scores.append(r2)
            
            logger.info("Average performance across all folds:")
            logger.info(f"Average MSE: {np.mean(mse_scores):.2f}")
            logger.info(f"Average MAE: {np.mean(mae_scores):.2f}")
            logger.info(f"Average R²:  {np.mean(r2_scores):.2f}")

            return {
                "avg_mse": np.mean(mse_scores),
                "avg_mae": np.mean(mae_scores),
                "avg_r2": np.mean(r2_scores),
                "all_mse": mse_scores,
                "all_mae": mae_scores,
                "all_r2": r2_scores
            }
        except Exception as e:
            logger.error(f"Error occured when validating model on {df_name}: {e}")
            return None
        
    # Function to train the model on the full dataset
    def train_model(self, df, df_name):
        try:
            logger.info(f"Training model on {df_name}")
            # X = features, y = target
            X = df.drop(columns=[self.target_column])
            y = df[self.target_column]
            # Scale the features 
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            # Initiate and fit model
            model = ExtraTreesRegressor()
            model.fit(X_scaled, y)

            # Get and sort feature importances
            importances = model.feature_importances_
            feature_names = X.columns
            sorted_importances = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)

            logger.info(f"Feature importances for model trained on {df_name}:")
            for feature, importance in sorted_importances:
                logger.info(f"  {feature}: {importance:.4f}")

            feature_importance = dict(sorted_importances)
            
            return model, scaler, X.columns.tolist(), feature_importance
        
        except Exception as e:
            logger.error(f"Error occured when training model on {df_name}: {e}")
            return None, None, None, None
