from google.cloud import bigquery
import pandas as pd
import numpy as np
import os
import holidays
import datetime
from astral.sun import sun
from astral import LocationInfo
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
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
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV


os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C:/Users/allan/Desktop/Personlige projekter/hyggeskyen_service_account.json'

# Initialize the BigQuery client
bq_client = bigquery.Client()

# Define SQL query
query = """
SELECT 
      traffic.*,
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
"""

# Run the query and fetch data from BigQuery
query_job = bq_client.query(query)
# Convert to DataFrame
raw_df = query_job.to_dataframe()

########################### DATA HANDLING ###########################

# Copy raw dataframe to another one for cleaning 
cleaned_df = raw_df.copy()

# Define rush our times
rush_hours = ["07:00", "08:00", "09:00", "15:00", "16:00", "17:00"]
# Exctract the rush hour rows and remove the rest
cleaned_df = cleaned_df[cleaned_df["time"].isin(rush_hours)]

# Function to define morning and afternoon rush hours
def rush_hour_period(time_column):
    if time_column in ["07:00", "08:00", "09:00"]:
        return "morning"
    else:
        return "afternoon"
# Apply function row by row
cleaned_df["rush_hour_period"] = cleaned_df["time"].apply(rush_hour_period)

# Function to collapse road_closure column in aggregation
def collapse_road_closure(values):
    return "true" if "yes" in values.values else "false"

def most_frequent_weather(series):
    mode = series.mode()
    if len(mode) == 1:
        return mode.iloc[0]

    # Get time from index or fallback if not accessible
    try:
        # assumes '08:00' or '16:00' appear in the index (multiindex with time)
        full_group = cleaned_df.loc[series.index]
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

grouped_df = cleaned_df.groupby(
    ["date", "rush_hour_period"], as_index=False
).agg({
    #"current_speed": "mean",                         
    #"free_flow_speed": "mean",                      
    "current_travel_time": "mean",                 
#    "free_flow_travel_time": "mean",      
#    "road_closure": collapse_road_closure,      
    "weather_main": most_frequent_weather,
#    "weather_description": most_frequent_weather,
    "temperature": "mean",
    "feels_like": "mean",
    "humidity_percent": "mean",
    "visibility": "mean",
    "wind_speed": "mean",
    "cloudiness_percent": "mean"
 })



# Create a new column where the date is converted to datetime
grouped_df['date_dt'] = pd.to_datetime(grouped_df['date'])
# Get all years that are present in the dataframe
years = grouped_df['date_dt'].dt.year.unique()

# Get all Danish holidays from the holidays library
dk_holidays = holidays.Denmark(years=years)

# Add date and name of custom holidays
# (only add those which have the same date each year)
custom_holidays_dict = {
    (12, 31): "New Years Eve",
    (12, 24): "Christmas Eve"  
}

# Empty list for custom holidays
custom_holidays = {}
# Loop to include the custom holidays for all relevant years
for year in years:
    for (month, day), name in custom_holidays_dict.items():
        custom_holidays[datetime.date(year, month, day)] = name

# Update dk_holidays with custom holidays
dk_holidays.update(custom_holidays)

# Map holidays into dataframe
holiday_map = {date: name for date, name in dk_holidays.items()}
grouped_df['holiday_name'] = grouped_df['date_dt'].map(holiday_map)

# Create a binary holiday column: 1 if holiday, 0 otherwise
grouped_df['is_holiday'] = grouped_df['holiday_name'].notna().astype(int)
# Drop columns
grouped_df = grouped_df.drop(["date_dt", "holiday_name"], axis='columns')

# Create dummy columns for each holiday
# holiday_dummies = pd.get_dummies(grouped_df['holiday_name'], prefix = 'holiday_', drop_first=True)
# grouped_df = pd.concat([grouped_df, holiday_dummies], axis=1)
# grouped_df = grouped_df.drop("holiday_name", axis = "columns")

# Create dummy columns for each category in weather_main column
weather_main_dummies = pd.get_dummies(grouped_df['weather_main'], prefix = 'weather_main_', drop_first=True)
grouped_df = pd.concat([grouped_df, weather_main_dummies], axis=1)
grouped_df = grouped_df.drop("weather_main", axis = "columns")

# Create dummy columns for each category in weather_description column
# weather_description_dummies = pd.get_dummies(grouped_df['weather_description'], prefix = 'weather_description_', drop_first=True)
# grouped_df = pd.concat([grouped_df, weather_description_dummies], axis=1)
# grouped_df = grouped_df.drop("weather_description", axis = "columns")

# Convert date column to datetime 
grouped_df['date'] = pd.to_datetime(grouped_df['date'])
# Extract day name 
grouped_df['day_name'] = grouped_df['date'].dt.day_name()
# Create dummy variables for day names
day_dummies = pd.get_dummies(grouped_df['day_name'], prefix='day', drop_first=True)
# Concatenate dummy columns to dataframe
grouped_df = pd.concat([grouped_df, day_dummies], axis=1)
# Drop column
grouped_df = grouped_df.drop("day_name", axis = "columns")


# Define location
city = LocationInfo("Copenhagen", "Denmark", "Europe/Copenhagen")

# Calculate sunrise and sunset for each date
def get_sun_times(date):
    s = sun(city.observer, date=date, tzinfo=city.timezone)
    return pd.Series({"sunrise": s["sunrise"].hour + s["sunrise"].minute/60,
                      "sunset": s["sunset"].hour + s["sunset"].minute/60})

grouped_df[['sunrise', 'sunset']] = grouped_df['date'].apply(get_sun_times)


# Sort values based on date and rush_hour_period
grouped_df = grouped_df.sort_values(["rush_hour_period", "date"])
# Get 1 and 7 day lags
grouped_df["lag_1day"] = grouped_df.groupby("rush_hour_period")["current_travel_time"].shift(1)
grouped_df["lag_7day"] = grouped_df.groupby("rush_hour_period")["current_travel_time"].shift(7)


########################### SPLIT DATA ###########################

# Split dataframe into morning and afternoon
morning_df = grouped_df[grouped_df["rush_hour_period"] == "morning"].copy()
afternoon_df = grouped_df[grouped_df["rush_hour_period"] == "afternoon"].copy()

# Convert all boolean columns to 1/0
morning_df[morning_df.select_dtypes(bool).columns] = morning_df.select_dtypes(bool).astype(int)
afternoon_df[afternoon_df.select_dtypes(bool).columns] = afternoon_df.select_dtypes(bool).astype(int)

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

# # Drop rush_hour_period, date and holiday columns for the morning since they are the same as for afternoon
# morning_features = morning_df.drop(columns=["rush_hour_period", "is_holiday", "sunrise", "sunset"] + [col for col in morning_df.columns if col in day_dummies.columns])
# # Add prefix for morning features
# morning_features = morning_features.add_prefix("morning_") 
# # Rename date column
# morning_features = morning_features.rename(columns={"morning_date": "date"})

# # Merge afternoon_df with morning_features
# afternoon_df = pd.merge(
#     afternoon_df,
#     morning_features,
#     how="left",
#     on="date"
# )

# Drop rush_hour_period and date column for both dataframes
morning_df = morning_df.drop(["rush_hour_period", "date"], axis = "columns")
afternoon_df = afternoon_df.drop(["rush_hour_period", "date"], axis = "columns")

# Drop all rows with missing values
morning_df = morning_df.dropna(axis=0)
afternoon_df = afternoon_df.dropna(axis=0)

########################### MULTICOLLINEARITY CHECK ###########################

# Function to check for mulitcollinearity and reduction where relevant
def corr_matrix(df, target_column, corr_percentage = 0.7):
    # Drop target column
    X_df = df.drop(columns=[target_column])

    # Generate correlation matrix
    corr_matrix = X_df.corr(numeric_only=True).abs()
    # Get the upper triangle of the correlation matrix
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

    # Find columns with high correlation
    to_drop_corr = [column for column in upper.columns if any(upper[column] > corr_percentage)]
    
    print(f"Dropping following columns: {to_drop_corr}")

    # Drop the higly correlated columns
    df = df.drop(columns=to_drop_corr)

    # Convert all columns to float64
    df = df.astype('float64')

    return df

morning_reduced = corr_matrix(morning_df, "current_travel_time")
afternoon_reduced = corr_matrix(afternoon_df, "current_travel_time")


# Function to calculate VIF
def calculate_vif(df):
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


def drop_with_vif(df, target_column, threshold = 10):
    # Drop target column
    X_df = df.drop(columns=[target_column])

    # While loop that keeps running until all the values are below the threshold
    while True:
        
        # Calculate VIF for all the variables
        vif = calculate_vif(X_df)
        # Drop the const value
        vif = vif[vif["feature"] != "const"]
        # Get the variable with the highest VIF
        max_vif = vif["VIF"].max()

        # If the highest VIF is below the threshold then break
        if max_vif < threshold:
            break
        # Else, get the name 
        feature_to_drop = vif.sort_values("VIF", ascending=False)["feature"].iloc[0]
        # and drop it from the dataframe
        try:
            X_df = X_df.drop(columns=[feature_to_drop])
            print(f"Dropping '{feature_to_drop}' with VIF = {max_vif:.2f}")
        except Exception as e:
            print(f"Could not drop feature in {df} because of the error: {e}")
    
    # Merge target column back into the original dataframe
    X_df[target_column] = df[target_column]
    return X_df
 

morning_reduced = drop_with_vif(morning_reduced, "current_travel_time")
afternoon_reduced = drop_with_vif(afternoon_reduced, "current_travel_time")

###################### MACHINE LEARNING #############################

df = morning_reduced

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
    rmse = np.sqrt(mean_squared_error(y_true_all, y_pred_all))
    mae = mean_absolute_error(y_true_all, y_pred_all)
    r2 = r2_score(y_true_all, y_pred_all)

    results.append({
        'Model': name,
        'RMSE': rmse,
        'MAE': mae,
        'R²': r2
    })

# Display results
results_df = pd.DataFrame(results).sort_values(by='RMSE')
print(results_df)

#__________________ Hyper Parameter Tuning ________________________


def hyper_parameter_tuning(df, paramgrid, model_name):

    # X = features, y = target
    X = df.drop(columns=['current_travel_time'])
    y = df['current_travel_time']

    # Scale X variables
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Create Ridge model
    model = model_name()

    # Grid search with CV
    grid = RandomizedSearchCV(estimator=model,
                        param_distributions=paramgrid,
                        cv=5,
                        scoring='r2') 

    grid.fit(X_scaled, y)

    # Evaluate final model 
    best_model = model_name(**grid.best_params_)
    best_model.fit(X_scaled, y)

    # Handle coefficients or feature importances
    if hasattr(best_model, 'coef_'):
        values = pd.Series(best_model.coef_, index=X.columns)
        values = values.sort_values(ascending=False)
    elif hasattr(best_model, 'feature_importances_'):
        values = pd.Series(best_model.feature_importances_, index=X.columns)
        values = values.sort_values(ascending=False)
    else:
        values = "No coefficients or feature importances available"

    return grid.best_params_, grid.best_score_, values

#________________ Ridge Hyperparameter Tuning ________________

# Define parameter grid for Ridge model
ridge_param_grid = {
    'alpha': [0.01, 0.1, 1, 2, 3, 10, 100],
    'solver': ['auto', 'svd', 'cholesky', 'lsqr', 'sparse_cg']
}

ridge_best_params, ridge_best_score, ridge_coefs = hyper_parameter_tuning(
    morning_reduced, 
    ridge_param_grid, 
    Ridge
)

# Print best results
print("Best params:", ridge_best_params)
print("Best R²:", ridge_best_score)
print("Coefficients:", ridge_coefs)

#________________ Extra Trees Hyperparameter Tuning ________________

# Define parameter grid for Extra Trees model
extra_trees_param_grid = {
    'n_estimators': [100, 200, 300],      # More trees is fine
    'max_depth': [None, 30, 40],          # Allow fully grown trees or deep trees
    'min_samples_split': [2, 5],          # 2 is default, 5 is mild regularization
    'min_samples_leaf': [1, 2],           # Avoid 4 unless small datasets
    'max_features': [1.0, 0.8],           # Stick to using most features
    'bootstrap': [False],                 # Keep it False for ExtraTrees
    'criterion': ['squared_error'],       # Skip 'absolute_error' unless needed
}



extra_trees_best_params, extra_trees_best_score, extra_trees_feature_importance = hyper_parameter_tuning(
    afternoon_reduced, 
    extra_trees_param_grid, 
    ExtraTreesRegressor
)

# Print best results
print("Best params:", extra_trees_best_params)
print("Best R²:", extra_trees_best_score)
print("Feature importance:", extra_trees_feature_importance)







scores = cross_val_score(
    Ridge(random_state=42),
    X, y,
    cv=KFold(n_splits=10, shuffle=True, random_state=42),
    scoring='r2'
)

print(f"Cross-validated R² scores: {scores}")
print(f"Mean R²: {scores.mean():.4f}")
print(f"Std R²: {scores.std():.4f}")

model = Ridge()
print(model.get_params())
