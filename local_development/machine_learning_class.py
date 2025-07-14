import numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MachineLearning:
    def __init__(self, model, target_column):
        self.model = model
        self.target_column = target_column
    
    def validate_model(self, df):
        # X = features, y = target
        X = df.drop(columns=[self.target_column])
        y = df[self.target_column]

        # Scale the features (optional but fine for Extra Trees)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Cross-validation setup
        cv = KFold(n_splits=10, shuffle=True, random_state=42)

        mse_scores = []
        mae_scores = []
        r2_scores = []
        
        # Fold counter
        fold = 1
        
        # Loop through each split
        for train_index, test_index in cv.split(X_scaled):
            # Split data in traning and test
            X_train, X_test = X_scaled[train_index], X_scaled[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]

            # Initiate and fit model
            model = self.model
            model.fit(X_train, y_train)
            # Predict on test data
            y_pred = model.predict(X_test)

            # Get performance metrics
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            # Append performance metrics to list
            mse_scores.append(mse)
            mae_scores.append(mae)
            r2_scores.append(r2)

            logger.info(f"Fold {fold}: MSE = {mse:.2f}, MAE = {mae:.2f}, R² = {r2:.2f}")
            fold += 1
        
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