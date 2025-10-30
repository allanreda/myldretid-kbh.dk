# myldretid-kbh 
## Machine Learning Based Traffic Predictor for Copenhagen Rush Hours
Try out the service live at: https://myldretid-kbh.dk/

## Introduction
Copenhagen is a relatively small city compared to other capitals around the world. In most cases, you are able to drive from one end of the city to the other, in less than 30 minutes - except during rush hours. 
Even though driving through Copenhagen during rush hours will always prolong your travel time, certain conditions will decide whether your drive will take 30 minutes or 60 minutes. At the time of writing this, I live in one end of the city and work on the opposite side of it, meaning I have to drive right through the city center during rush hours. I grew tired of not knowing whether my drive to or from work would take 25 minuttes or over an hour - every drive was a bit of a gamble. "It would be nice to know a day or two in advance, what the traffic levels would look like, so that you could plan ahead" I often thought to myself while being stuck in traffic. This project is the solution to my, and propably a lot of other Copenhageners, problem. It is completely free and publicly available, in hopes that it will make a lot of driving Copenhageners lives a little bit easier.

## Table of Contents

## User Guide and Useful Info
### Color Explanation
### Calculation of Average Travel Time
### Reasoning Behind Update Times

## Project Diagram
<img width="1415" height="1238" alt="myldretid-kbh drawio" src="https://github.com/user-attachments/assets/26fcafd7-beeb-4c99-9762-df9ff7fe85b9" />
This diagram doesn't include the pipeline architecture behind the data ingestion of the traffic and weather data. That was built earlier as a separate project, which you can read about here: https://github.com/allanreda/Copenhagen-Traffic-and-Weather-ETL-Pipeline  

## Machine Learning
### Feature Engineering and Preprocessing
Before the data reaches the models, it goes through a series of functions that prepare the data and creates necessary variables. These are as follows:

- Grouping by rush hours (splitting into morning and afternoon)
- Including public holidays in a binary column
- Create dummy columns from weather data
- Create dummy columns from weekdays
- Calculate sunset and sunrise times for each day
- Add 1 day lag for travel time
- Add 7 day lag for travel time
- Calculate rolling average for the past 7 days
- Convert all boolean values to binary
- Add morning travel time as a predictor variable for the afternoon

It should be noted that two separate pipelines are run: one for predicting the next 2 rush hours, and one for predicting the 8 rush hours after that. 
For the latter, it isn't possible to add a 1-day lag or calculate a rolling average for the past 7 days, simply because the data doesn't exist. 

Each pipeline produces two datasets: one for the morning rush hour and one for the afternoon. This is done because the predictors have different effects on the target variable, based on the rush hour period. Furthermore, the travel time for the morning rush hour proved to be a strong predictor of the afternoon rush hour. Without splitting up into two models, this nuance would have been lost.

### Model Evaluataion and Selection
Multiple algorithms were tested and evaluated using K-fold cross validation to identify the model that performed best in predicting unseen data. 
```python
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
```
The cross validations was run with 10, 5, and 3 folds to ensure that the model performance remained consistent across different data splits and sample sizes. All models were trained and evaluated using the exact same dataset, and performance was compared using RMSE, MSE, MAE, and R². 
The Extra Trees Regressor proved to be the best performer across all evaluation parameters and cross validation setups. Based on these results, it was selected as the final model.  

Seen below is the benchmark for the models trained on the dataset for the morning rush hour to predict the next 2 rush hours.
<img width="516" height="288" alt="image" src="https://github.com/user-attachments/assets/6979acb5-9c82-46e6-bcd1-815aefdbe039" />

### Feature Importances
The feature importances for the latest trained models, at the time of writing this, can be seen below.
<img width="901" height="571" alt="image" src="https://github.com/user-attachments/assets/c31ba9ad-a8bb-4697-8f6f-2f444391d457" />
<img width="810" height="577" alt="image" src="https://github.com/user-attachments/assets/8b7c225c-6139-4324-9ef9-3f23446b8662" />

The "is_holiday" feature has the highest decision power by far on both models. Traffic levels will always be lower on weekends and public holidays, when most people are off from work. 

Also, I think it is worth noting that the "morning_travel_time" feature on the afternoon model has the third-highest decision power. This can probably be explained by the fact that the same people taking the car in the morning also have to take the car home in the afternoon. It makes total sense when you think about it, but is still a fun observation in my opinion. 

Some of the features have minimal impact on the models, yet I have still chosen to include them for now. When I tried removing them, the models only worsened a bit, so no positive impact was proven by removing them. At the time of writing this, there is only a little over a years worth of data available. My hope is that these currently insignificant features will have a greater impact on the models, as more data is collected as time goes by. 

## CI/CD Pipelines
### Dev and Prod Environments
When starting this project out, I knew that the end product would be a tool with real users. Therefore, I wanted to ensure that there would be minimal downtime of the user-facing part of the project while developing. The user-facing part would be the frontend, and the pipeline providing data to it. The best way to ensure that is by setting up separate development and production environments for both, which is what I did. 

I decided to use Github Workflows mainly due to the fact that I was already using Github for version controlling, but also due to its relatively easy integration with both Google Cloud and Firebase.

### Website Pipeline
#### Dev Workflow 
##### Triggers
Runs on pushes to the "dev" branch but only if changes have been made to:  
- 'website/website/**'
- '.github/workflows/firebase.deploy.dev.yml'
##### Steps
- Pull the repository code into the workflow environment
- Install Firebase CLI using 'npm install -g firebase-tools'
- Prepare deployment folder:
  - Navigate to website/website
  - Delete sitemap.xml to prevent search engines indexing on the dev site
  - Replace robots.txt with robots.dev.txt which contains 'Disallow: /' to block search engine crawlers
  - Print out all file names for debugging
  - Print out content of robots.txt for debugging
- Deploy to the dev Firebase hosting site

#### Prod Workflow
##### Triggers
Runs on pushes to the "main" branch but only if changes have been made to:  
- 'website/website/**'
- '.github/workflows/firebase.deploy.prod.yml'
##### Steps
- Pull the repository code into the workflow environment
- Install Firebase CLI using 'npm install -g firebase-tools'
- Prepare deployment folder:
  - Navigate to website/website
  - Replace robots.txt with robots.prod.txt which contains 'Allow: /' to allow search engine to crawl and index site
  - Print out all file names for debugging
  - Print out content of robots.txt for debugging
- Deploy to the prod Firebase hosting site
  

### Cloud Run Pipeline

## IAC (Terraform)
