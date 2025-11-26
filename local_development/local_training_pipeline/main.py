import sys
sys.path.append('C:/Users/allan/Desktop/Personlige projekter/cph-traffic-predictor/local_development/local_training_pipeline')

from google.cloud import bigquery, storage, secretmanager
from multicollinearity_reduction_class import MulticollinearityReducer
from machine_learning_class import MachineLearning
from cloud_utils_class import CloudUtils
from preprocessing_class import PreProcessing

import importlib
importlib.reload(sys.modules['preprocessing_class'])
importlib.reload(sys.modules['multicollinearity_reduction_class'])
importlib.reload(sys.modules['machine_learning_class'])
importlib.reload(sys.modules['cloud_utils_class'])

from zoneinfo import ZoneInfo 
from datetime import datetime
import time
import os
import json
from pathlib import Path

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/hyggeskyen_service_account.json'

# Initialize clients
bq_client = bigquery.Client()
storage_client = storage.Client()
sm_client = secretmanager.SecretManagerServiceClient()

# Define SQL query to fetch historical data from Bigquery
query = """
SELECT 
    traffic.current_travel_time,
    traffic.date,
    traffic.time,
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
WHERE 
    DATE(traffic.date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 YEAR)
"""

# Load JSON file
base_path = Path(__file__).parent if "__file__" in globals() else Path('C:/Users/allan/Desktop/Personlige projekter/cph-traffic-predictor/local_development/local_training_pipeline')
with open(base_path / "holidays.json", encoding="utf-8") as f:
    manual_holidays = json.load(f)

# Instantiate CloudUtils class
cloud_utils = CloudUtils(bq_client, storage_client, sm_client)
# Import OpenWeather API key from Secret Manager in 'hyggeskyen' GCP
openweather_api_key = cloud_utils.get_secret('OPENWEATHER_API_KEY', 'sylvan-mode-413619')

# Instantiate PreProcessing class
preprocesser = PreProcessing(openweather_api_key)
# Instantiate Reducer class
reducer = MulticollinearityReducer(target_column = "current_travel_time")
# Instantiate MachineLearning class
machinelearning = MachineLearning(target_column = "current_travel_time")

# Pull historical traffic and weather data from bigquery
#historical_data = cloud_utils.pull_historical_data(query)

# Run the preprocessing pipeline for the historical data
morning_df, afternoon_df, _, _ = preprocesser.execute_preprocessing_1_day(historical_data, manual_holidays)

# Run the multicollinearity reduction pipeline on both dataframes
morning_df = reducer.execute_reduction(morning_df, 'morning_df')
afternoon_df = reducer.execute_reduction(afternoon_df, 'afternoon_df')


#_____________________ Model Definition _______________________
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
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
import numpy as np
import pandas as pd

df = afternoon_df

# X = features, y = target
X = df.drop(columns=['current_travel_time'])
y = df['current_travel_time']

# Define models to try
models = {
    'Linear Regression': LinearRegression(),
    'Ridge Regression': Ridge(),
    'Lasso Regression': Lasso(),
    'Decision Tree': DecisionTreeRegressor(),
    'Random Forest': RandomForestRegressor(),
    'Gradient Boosting': GradientBoostingRegressor(),
    'XGBoost': xgb.XGBRegressor(),
    'Support Vector Regressor': SVR(),
    'ElasticNet': ElasticNet(),
    'KNN': KNeighborsRegressor(),
    'Extra Trees': ExtraTreesRegressor(),
    'CatBoost': CatBoostRegressor(verbose=0)
}

#_____________________ KFold Cross Validation _______________________

# Cross-validation setup
cv = KFold(n_splits=10, shuffle=True, random_state=42)

results = []

for name, model in models.items():
    y_true_all = []
    y_pred_all = []

    for train_idx, test_idx in cv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]


        # Scale features using training data only
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Fit and predict
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)

        # Collect predictions and true values
        y_true_all.extend(y_test)
        y_pred_all.extend(y_pred)

    # Evaluate on all combined predictions
    mse = mean_squared_error(y_true_all, y_pred_all)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true_all, y_pred_all)
    r2 = r2_score(y_true_all, y_pred_all)

    results.append({
        'Model': name,
        'MSE': mse,
        'RMSE': rmse,
        'MAE': mae,
        'R²': r2
    })

# Display results
results_df = pd.DataFrame(results).sort_values(by='RMSE')
print(results_df)


#_____________________ Hyperparameter Tuning _______________________

df = afternoon_df

# X = features, y = target
X = df.drop(columns=['current_travel_time'])
y = df['current_travel_time']

# Pipeline: scaling + model
pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("model", ExtraTreesRegressor())
])

# Parameter grid
param_grid = {
    "model__n_estimators": [200, 400, 600],
    "model__max_depth": [None, 10, 20, 30],
    "model__min_samples_split": [2, 5, 10],
    "model__min_samples_leaf": [1, 2, 4],
    "model__max_features": ["sqrt", "log2"]
}

# param_grid = {
#     "model__n_estimators": [1500, 2000],
#     "model__max_depth": [None, 200, 300, 400],
#     "model__min_samples_split": [2, 5],
#     "model__min_samples_leaf": [1, 2],
#     "model__max_features": ["sqrt", "log2", 0.7, 0.9]
# }



grid = GridSearchCV(
    estimator=pipeline,
    param_grid=param_grid,
    cv=10,
    scoring="neg_mean_squared_error",
    n_jobs=-1,
    verbose=2
)

grid.fit(X, y)

print("Best params:", grid.best_params_)
print("Best CV MSE:", -grid.best_score_)


#________________ Single model test setup __________________

# Cross-validation setup
cv = KFold(n_splits=10, shuffle=True, random_state=42)

mse_scores, rmse_scores, mae_scores, r2_scores = [], [], [], []

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
    # model = ExtraTreesRegressor(max_depth=None,
    #                             max_features='log2',
    #                             min_samples_leaf=1,
    #                             min_samples_split=2,
    #                             n_estimators=400
    #                         )
    
    model = ExtraTreesRegressor()

    model.fit(X_train_scaled, y_train)
    # Predict on test data
    y_pred = model.predict(X_test_scaled)

    # Get performance metrics
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    # Append performance metrics to list
    mse_scores.append(mse)
    rmse_scores.append(rmse)
    mae_scores.append(mae)
    r2_scores.append(r2)

print(np.mean(mse_scores))
print(np.mean(rmse_scores))
print(np.mean(mae_scores))
print(np.mean(r2_scores))


#_____________________ Residual Analysis _______________________
import matplotlib.pyplot as plt

# Get predictions and residuals
y_pred = model.predict(X_test_scaled)
residuals = y_test - y_pred

# Count positive and negative residuals
num_positive = (residuals > 0).sum()   # actual > predicted
num_negative = (residuals < 0).sum()   # actual < predicted
num_zero = (residuals == 0).sum()      # exact predictions

# Plot Residual Distribution
plt.figure(figsize=(10, 5))
plt.hist(residuals, bins=30, edgecolor='black', alpha=0.7)
plt.axvline(0, color='red', linestyle='--', linewidth=2)

plt.title("Residual Distribution", fontsize=14)
plt.xlabel("Residual (Actual - Predicted)", fontsize=12)
plt.ylabel("Frequency", fontsize=12)

plt.grid(axis='y', linestyle='--', alpha=0.4)
plt.tight_layout()
plt.show()


# Residuals vs Predicted Values
plt.figure(figsize=(10,5))
plt.scatter(y_pred, residuals, alpha=0.4)
plt.axhline(0, color='red', linestyle='--')
plt.xlabel("Predicted Travel Time")
plt.ylabel("Residual")
plt.title("Residuals vs Predicted Values")
plt.show()


# ___________ Descriptive Analysis of Target Variable ___________

# Morning
y = morning_df['current_travel_time']
y.skew()
y.var()
y.describe()

plt.hist(y, bins=30)
plt.xlabel('Travel time (seconds)')
plt.ylabel('Frequency')
plt.title('Distribution of Travel Time')
plt.show()

# Afternoon
y = afternoon_df['current_travel_time']
y.skew()
y.var()
y.describe()

plt.hist(y, bins=30)
plt.xlabel('Travel time (seconds)')
plt.ylabel('Frequency')
plt.title('Distribution of Travel Time')
plt.show()