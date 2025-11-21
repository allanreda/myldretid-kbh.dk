# myldretid-kbh 
## Machine Learning Based Traffic Predictor for Copenhagen Rush Hours
Try out the service live at: https://myldretid-kbh.dk/    

<p align="center">
  <img width="300" alt="image" src="https://github.com/user-attachments/assets/8e742179-e9f1-42b8-baa1-1f3b045ade36" />
</p>  

## Introduction
Copenhagen is a relatively small city compared to other capitals around the world. In most cases, you are able to drive from one end of the city to the other, in less than 30 minutes - except during rush hours. 
Even though driving through Copenhagen during rush hours will always prolong your travel time, certain conditions will decide whether your drive will take 30 minutes or 60 minutes. At the time of writing this, I live in one end of the city and work on the opposite side of it, meaning I have to drive right through the city center during rush hours. I grew tired of not knowing whether my drive to or from work would take 25 minuttes or over an hour - every drive was a bit of a gamble. "It would be nice to know a day or two in advance, what the traffic levels would look like, so that you could plan ahead" I often thought to myself while being stuck in traffic. This project is the solution to my, and propably a lot of other Copenhageners, problem. It is completely free and publicly available, in hopes that it will make a lot of driving Copenhageners lives a little bit easier.

## Table of Contents

- [Introduction](#introduction)
- [User Guide and Useful Info](#user-guide-and-useful-info)
  - [Gauge Color Explanation](#gauge-color-explanation)
  - [Calculation of Average Travel Time](#calculation-of-average-travel-time)
  - [Reasoning Behind Update Times](#reasoning-behind-update-times)
  - [Data Sources](#data-sources)
- [Project Diagram](#project-diagram)
- [Machine Learning](#machine-learning)
  - [Feature Engineering and Preprocessing](#feature-engineering-and-preprocessing)
  - [Model Evaluation and Selection](#model-evaluation-and-selection)
  - [Feature Importances](#feature-importances)
- [IAC (Terraform)](#iac-terraform)
  - [Modules](#modules)
- [CI/CD Pipelines](#cicd-pipelines)
  - [Dev and Prod Environments](#dev-and-prod-environments)
  - [Website Pipeline](#website-pipeline)
    - [Dev Workflow](#dev-workflow)
      - [Triggers](#triggers)
      - [Steps](#steps)
    - [Prod Workflow](#prod-workflow)
      - [Triggers](#triggers-1)
      - [Steps](#steps-1)
  - [Cloud Run Pipeline](#cloud-run-pipeline)
    - [Dev Workflow](#dev-workflow-1)
      - [Triggers](#triggers-2)
      - [Steps](#steps-2)
    - [Prod Workflow](#prod-workflow-1)
      - [Triggers](#triggers-3)
      - [Steps](#steps-3)

## User Guide and Useful Info
### Gauge Color Explanation

| Color             | Meaning                                                        |
| :---------------- | :------------------------------------------------------------- |
| **Bright green**  | A lot faster than average (positive deviation ≥ **15%**)       |
| **Turquoise**     | Faster than average (positive deviation **10–15%**)            |
| **Dark green**    | A bit faster than average (positive deviation **5–10%**)       |
| **Yellow**        | Around average (deviation **–5% to +5%**)                      |
| **Bright orange** | A bit slower than average (negative deviation **–10% to –5%**) |
| **Dark orange**   | Slower than average (negative deviation **–15% to –10%**)      |
| **Red**           | A lot slower than average (negative deviation ≤ **–15%**)      |

### Calculation of Average Travel Time
The calculation uses the historical travel times of the rush hours captured in all the 20 chosen geographical locations of Copenhagen. The rush hours are defined as 7, 8, and 9 AM for the morning and 3, 4 and 5 PM for the afternoon.  
It's important to mention that the average travel time is calculated using only data from the weekdays and thereby excluding the weekends. The main intended use of this service is in the weekdays where Copenhageners are driving to/from work or school during the rush hours. Therefore it would make more sense if the predictions were relative to the weekdays rather than the weekends. Including the weekend in the calculation would also significantly lower the average, which would not be ideal in this case. 

### Reasoning Behind Update Times
The predictions currently runs twice every day: at 10 AM and 6 PM.  
These specific times were chosen because they occur after each rush hour period, when the ETL pipeline has collected the latest data. This ensures that the latest data is ready to be used for generating lag variables for the upcoming predictions.

### Data Sources
The TomTom Traffic API and OpenWeather API are used to collect traffic and weather data from 20 specific geograpical locations in Copenhagen. You can read more about the ETL pipeline that collects this data, in this repository: https://github.com/allanreda/Copenhagen-Traffic-and-Weather-ETL-Pipeline. The pipeline has been running since the **21st of September 2024**.  
Furthermore, this project also uses the official website of Copenhagen Municipality as a reliable source of information for past and upcoming school and public holidays.

## Project Diagram
<img width="1415" height="1238" alt="myldretid-kbh project diagram" src="https://github.com/user-attachments/assets/26fcafd7-beeb-4c99-9762-df9ff7fe85b9" />
This diagram doesn't include the pipeline architecture behind the data ingestion of the traffic and weather data. That was built earlier as a separate project, which you can read about here: https://github.com/allanreda/Copenhagen-Traffic-and-Weather-ETL-Pipeline  

## Machine Learning

### Target Variable
Before diving into the different aspects of the ML-process, one should have a clear idea of what it is we are actually trying to predict here. The target variable is named "current_travel_time" and is an 

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

### Model Evaluation and Selection
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
The cross validations were run with 10, 5, and 3 folds to ensure that the model performance remained consistent across different data splits and sample sizes. All models were trained and evaluated using the exact same dataset, and performance was compared using RMSE, MSE, MAE, and R². 
The **Extra Trees Regressor** proved to be the best overall performer across all evaluation parameters and cross validation setups. Based on these results, it was selected as the final model.  

Seen below is the benchmark for the models trained on the dataset for the afternoon rush hour to predict the next two rush hours.   
<img width="700" alt="image" src="https://github.com/user-attachments/assets/5022ea88-00a2-4520-8e80-7c4775972cd9" />

### Feature Importances
The feature importances for the latest trained models, for the prediction of the next two rush hour periods, at the time of writing this, can be seen below.  
<img width="700" alt="feature importances morning model" src="https://github.com/user-attachments/assets/19ec19ec-bb94-45f7-82be-dfff63a6ac1b" />  
<img width="700" alt="feature importances afternoon model" src="https://github.com/user-attachments/assets/add4bd8b-be44-4e1b-a672-39bd73c62282" />  

The "is_holiday" feature has the highest decision power by far on both models. Traffic levels will always be lower on weekends and public holidays, when most people are off from work. 

Also, I think it is worth noting that the "morning_travel_time" feature on the afternoon model has the third-highest decision power. This can probably be explained by the fact that the same people taking the car in the morning also have to take the car home in the afternoon. It makes total sense when you think about it, but is still a fun observation in my opinion. 

Some of the features have minimal impact on the models, yet I have still chosen to include them **for now**. When I tried removing them, the models only worsened a bit, so no positive impact was proven by removing them. At the time of writing this, there is only a little over a years worth of data available. My hope is that these currently insignificant features will have a greater impact on the models, as more data is collected as time goes by. 

### Residual Analysis
I thought it would be informative to look into whether my model currently over- or underpredicts, and by how much (in actual values). At the time of writing this, the dataset is still quite small (a little over a year) so the analysis was done on a sample set of **41 predictions**. The predictions are all from one of the folds of a cross validation done with 10 folds. I chose the 10 fold-cross validation, because that is what is used in production to validate and log model performance.

#### Residual Distribution
<img width="700" alt="image" src="https://github.com/user-attachments/assets/22022557-3721-42f5-af0d-6d26a9e19d96" />  

Of the 41 samples, 13 were underpredicted while 28 were overpredicted, which shows a tendency to overpredict. In this case, that means that the model is more likely to assume slower traffic compared to reality. The plot above also shows the residual values, but it would be more informative if we looked into those with a plot where predicted values are also shown.  

<img width="700" alt="image" src="https://github.com/user-attachments/assets/b4d3a6fc-e282-4818-a01d-f9a2bdc577b4" />  

The first thing that becomes apparent when looking at the plot is how the larger residuals, both negative and positive ones, appear on the larger predicted values. When looking at the lower predicted values, no major residuals are present, but as we move above 120, some large residuals occur. In general, this suggests that the model's uncertainty increases when predicting higher travel times. The ability to forecast high travel times is one of the most important features of this tool. Therefore, this is certainly something worth monitoring as data grows, and try to improve in the future.

## IAC (Terraform)
The GCP infrastructure is fully managed with Terraform, to ensure that it stays consistent and reproducible, across both dev and prod environments. This is especially important since both the dev and prod infrastructure lives within the same Google Cloud project. Differences between them are the suffix of the created ressources, which are based on the Terraform workspace in use (which are either 'dev' or 'prod'). Example:  
```
repository_id = "myldretid-kbh-${terraform.workspace}"
```
### Modules

| Module                       | Depends on       | Description                                                         |
|------------------------------|------------------|----------------------------------------------------------------------|
| **enable_apis**              | none             | Enable all required APIs in the project                              |
| **permissions**              | enable_apis      | Grant service accounts required permissions                          |
| **models_bucket**            | permissions      | Create bucket to store trained models                                |
| **predictions_bucket**       | permissions      | Create bucket to store prediction files                              |
| **pipeline_repo (resource)** | permissions      | Create Artifact Registry repository                                  |
| **training_pipeline**        | pipeline_repo    | Create training pipeline including Cloud Run, Pub/Sub, and Scheduler |
| **prediction_pipeline_morning** | pipeline_repo | Create morning prediction pipeline including Cloud Run, Pub/Sub, and Scheduler |
| **prediction_pipeline_afternoon** | pipeline_repo | Create afternoon prediction pipeline including Cloud Run, Pub/Sub, and Scheduler |
| **dns_setup (prod workspace only)** | pipeline_repo | Set up DNS for custom domain on prod site                            |

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
- '.github/workflows/cloud_run.deploy.prod.yml'
  
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
#### Dev Workflow
##### Triggers
Runs on pushes to the "dev" branch but only if changes have been made to:  
- 'cloud_run/**'
- '.github/workflows/cloud_run.deploy.dev.yml'

##### Steps
- Pull the repository code into the workflow environment
- Authenticate to Google Cloud using service account key
- Setup Google Cloud CLI with GCP project ID
- Configure Docker for Artifact Registry
- Build and push training image
- Build and push prediction image
- Deploy updated training image to 'training-dev' Cloud Run service
- Deploy updated prediction image to 'prediction-morning-dev' Cloud Run service
- Deploy updated prediction image to 'prediction-afternoon-prod' Cloud Run service

#### Prod Workflow
##### Triggers
Runs on pushes to the "main" branch but only if changes have been made to:  
- 'cloud_run/**'
- '.github/workflows/cloud_run.deploy.prod.yml'

##### Steps
- Pull the repository code into the workflow environment
- Authenticate to Google Cloud using service account key
- Setup Google Cloud CLI with GCP project ID
- Configure Docker for Artifact Registry
- Build and push training image
- Build and push prediction image
- Deploy updated training image to 'training-prod' Cloud Run service
- Deploy updated prediction image to 'prediction-morning-prod' Cloud Run service
- Deploy updated prediction image to 'prediction-afternoon-prod' Cloud Run service

