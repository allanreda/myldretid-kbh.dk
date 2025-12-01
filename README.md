# myldretid-kbh 
## Machine Learning Based Traffic Predictor for Copenhagen Rush Hours
Try out the service live at: https://myldretid-kbh.dk/    

<p align="center">
  <img width="300" alt="image" src="https://github.com/user-attachments/assets/e7181920-dbb4-43a1-b87c-00b87937ba2f" />
</p>  

## Introduction
Copenhagen is a relatively small city compared to other capitals around the world. In most cases, you are able to drive from one end of the city to the other in less than 30 minutes - except during rush hours. 
Even though driving through Copenhagen during rush hours will always prolong your travel time, certain conditions will decide whether your drive will take 30 minutes or 60 minutes. At the time of writing this, I live in one end of the city and work on the opposite side of it, meaning I have to drive right through the city center during rush hours. I grew tired of not knowing whether my drive to or from work would take 25 minutes or over an hour - every drive was a bit of a gamble. *"It would be nice to know a day or two in advance what the traffic levels would look like, so that you could plan ahead"* I often thought to myself while being stuck in traffic. This project is the solution to my, and probably a lot of other Copenhageners', problem. It is completely free and publicly available, in hopes that it will make a lot of driving Copenhageners' lives a little bit easier.

## Table of Contents

- [Introduction](#introduction)
- [User Guide and Useful Info](#user-guide-and-useful-info)
  - [Gauge Color Explanation](#gauge-color-explanation)
  - [Calculation of Average Travel Time](#calculation-of-average-travel-time)
  - [Reasoning Behind Update Times](#reasoning-behind-update-times)
  - [Data Sources](#data-sources)
- [Project Diagram](#project-diagram)
- [Machine Learning](#machine-learning)
  - [Target Variable](#target-variable)
    - [Descriptive Statistics and Distribution Plots](#descriptive-statistics-and-distribution-plots)
      - [Morning Travel Time](#morning-travel-time)
      - [Afternoon Travel Time](#afternoon-travel-time)
  - [Feature Engineering and Preprocessing](#feature-engineering-and-preprocessing)
  - [Model Evaluation and Selection](#model-evaluation-and-selection)
  - [Feature Importances](#feature-importances)
  - [Residual Analysis](#residual-analysis)
    - [Residual Distribution – Morning Rush Hours](#morning-rush-hours)
    - [Residual Distribution – Afternoon Rush Hours](#afternoon-rush-hours)
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
- [Final Notes](#final-notes)


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
The calculation uses the historical travel times captured in all the 20 chosen geographical locations of Copenhagen during rush hours. The rush hours are defined as 7, 8, and 9 AM for the morning and 3, 4 and 5 PM for the afternoon. The geographical locations can be seen in the list below this section.  
It's important to mention that the average travel time is calculated using only data from the weekdays and thereby excluding the weekends. The main intended use of this service is on weekdays when Copenhageners are driving to/from work or school during the rush hours. Therefore, it would make more sense if the predictions were relative to the weekdays rather than the weekends. Including the weekend in the calculation would also significantly lower the average, which would not be ideal in this case. 

### Reasoning Behind Update Times
The predictions currently run twice every day: at 10 AM and 6 PM.  
These specific times were chosen because they occur after each rush hour period, when the ETL pipeline has collected the latest data. This ensures that the latest data is ready to be used for generating lag variables for the upcoming predictions.

### Data Sources
The TomTom Traffic API and OpenWeather API are used to collect traffic and weather data from 20 specific geographical locations in Copenhagen, which are listed in the section below. You can read more about the ETL pipeline that collects this data, in this repository: https://github.com/allanreda/Copenhagen-Traffic-and-Weather-ETL-Pipeline. The pipeline has been running since the **21st of September 2024**.  
Furthermore, this project also uses the official website of Copenhagen Municipality as a reliable source of information for past and upcoming school and public holidays.

#### Geographical Locations 
- Bispeengbuen/Aagade
- Aaboulevarden/Rosenoerns Allé
- H.C. Andersens Boulevard/Rådhuspladsen
- Amagerbrogade/Vermlandsgade
- Nørrebros Runddel
- Vesterbrogade/Roskildevej
- Vesterbrogade/Platanvej
- Kongens Nytorv
- Gothersgade/Adelgade
- Sydhavnsgade
- Enghavevej/Vigerslev Allé
- Kalvebod Brygge
- Frederiksborggade/Nørre Farimagsgade
- Østerbrogade/Strandboulevarden
- Lyngbyvej/Rovsingsgade
- Tagensvej/Jagtvej
- Vejlands Allé/Ørestads Boulevard
- Vibenhus Runddel
- Gammel Køge Landevej/Folehaven
- Borups Allé/Hulgårdvej

## Project Diagram
<img width="1415" height="1238" alt="myldretid-kbh project diagram" src="https://github.com/user-attachments/assets/26fcafd7-beeb-4c99-9762-df9ff7fe85b9" />
This diagram doesn't include the pipeline architecture behind the data ingestion of the traffic and weather data. That was built earlier as a separate project, which you can read about here: https://github.com/allanreda/Copenhagen-Traffic-and-Weather-ETL-Pipeline  

## Machine Learning

### Target Variable
Before diving into the different aspects of the ML process, it's important to clarify what we are actually trying to predict here. The target variable is named "current_travel_time" and is an average of all the historical travel times captured across the 20 chosen geographical locations of Copenhagen during rush hours. **The variable is measured in seconds**. 

#### Descriptive Statistics and Distribution Plots
We will be looking into the statistics and distribution of the target variable for both the morning and afternoon rush hours separately, since they essentially cover two different models. 

##### Morning Travel Time  

| Statistic | Value   |
|-----------|---------|
| Count     | 412     |
| Mean      | 91.266  |
| Std       | 16.525  |
| Min       | 71.750  |
| 25%       | 74.954  |
| 50%       | 90.817  |
| 75%       | 102.467 |
| Max       | 217.800 |

<img width="500" alt="image" src="https://github.com/user-attachments/assets/893d9f83-251a-45cb-808d-34dce87a377e" />  

When looking at the plot, it looks like most of the values are centered around the lower end of the spectrum, between 80 and 110 seconds. The quartiles and the relatively low standard deviation of 16.5 confirm this. In practice, this means that the travel time in the morning is relatively predictable most of the time, except for a few extreme outliers. I didn't remove these outliers from the dataset, because those are the days we are most interested in predicting. They represent the days when the traffic is worst during rush hours. 

##### Afternoon Travel Time  

| Statistic | Value   |
|-----------|---------|
| Count     | 413     |
| Mean      | 110.621 |
| Std       | 22.605  |
| Min       | 75.233  |
| 25%       | 91.500  |
| 50%       | 107.267 |
| 75%       | 124.767 |
| Max       | 199.850 |

<img width="500" alt="image" src="https://github.com/user-attachments/assets/c273084d-f6a0-4e09-acbb-179dacbfbd08" />  

The values for the afternoon rush hours have a noticeably larger spread compared to the morning. The largest concentration appears between 90 and 120, a bit higher than where the values are centered around in the morning. Contrary to the morning, a sizable amount of the values of the afternoon are larger than 120, indicating more frequent high travel times. This is supported by the mean value being 110 and the standard deviation of 22. Based on these findings, one could assume that the model trained on the afternoon data would be better at predicting higher travel times than the model trained on the morning travel times.

### Feature Engineering and Preprocessing
Before the data reaches the models, it goes through several preprocessing and feature-engineering steps:

- Group by rush hour (morning/afternoon)
- Add public holidays as a binary column
- Create dummy columns from weather data
- Create dummy columns from weekdays
- Calculate sunset and sunrise times for each day
- Add 1 day lag for travel time
- Add 7 day lag for travel time
- Compute a 7-day rolling average
- Convert all boolean values to binary
- Add morning travel time as a predictor variable for the afternoon

It should be noted that two separate pipelines are run: one for predicting the next 2 rush hours, and one for predicting the 8 rush hours after that. 
For the latter, 1-day lags and rolling averages cannot be calculated, simply because the required future data does not yet exist 

Each pipeline produces two datasets: one for the morning rush hour and one for the afternoon. This is done because the predictors have different effects on the target variable, based on the rush hour period. Furthermore, the travel time for the morning rush hour proved to be a strong predictor of the afternoon rush hour. Without splitting up into two models, this nuance would have been lost.

### Model Evaluation and Selection
Multiple algorithms were tested and evaluated using K-fold cross-validation to identify the model that performed best in predicting unseen data. 
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

Example: The benchmark for the models trained on the dataset for the afternoon rush hour to predict the next two rush hours.   
<img width="700" alt="image" src="https://github.com/user-attachments/assets/5022ea88-00a2-4520-8e80-7c4775972cd9" />

### Feature Importances
The feature importances for the latest trained models, for the prediction of the next two rush hour periods, at the time of writing this, can be seen below.  
<img width="700" alt="feature importances morning model" src="https://github.com/user-attachments/assets/19ec19ec-bb94-45f7-82be-dfff63a6ac1b" />  
<img width="700" alt="feature importances afternoon model" src="https://github.com/user-attachments/assets/add4bd8b-be44-4e1b-a672-39bd73c62282" />  

The "is_holiday" feature has the highest decision power by far on both models. Traffic levels will always be lower on weekends and public holidays, when most people are off work. 

Also, it's worth noting that the "morning_travel_time" feature on the afternoon model has the third-highest decision power. This can probably be explained by the fact that the same people commuting by car in the morning also have to drive home in the afternoon. It makes total sense when you think about it, but is still a fun observation. 

Some features currently have minimal impact, but I’ve chosen to keep them **for now**. When I tried removing them, model performance slightly worsened - no positive impact was proven by removing them. At the time of writing this, there is only a little over a year's worth of data available. My hope is that these currently insignificant features will have a greater impact on the models, as more data accumulates over time. 

### Residual Analysis
I thought it would be informative to look into whether my model currently over- or underpredicts, and by how much (in actual values). At the time of writing this, the dataset is still quite small (a little over a year) so the analysis was done on a sample set of **41 predictions**. The predictions are all from one of the folds of a cross validation done with 10 folds. I chose the 10 fold-cross validation, because that is what is used in production to validate and log model performance.

#### Residual Distribution

#### Morning Rush Hours
<img width="700" alt="image" src="https://github.com/user-attachments/assets/85d7ae46-6380-4b3a-9313-f0ae5f53186e" />  

Most of the residuals are centered around the middle, which is a sign of strong prediction power. Though there are a few predictions that are way off. 

<img width="700" alt="image" src="https://github.com/user-attachments/assets/004d75fd-5993-402f-9490-5931260dc804" />  

When looking at the residuals plotted against the predicted travel times, it can clearly be seen that the large errors occur on the higher side of the predicted travel times. This shows that the model tends to become more uncertain when travel times are higher. Also, it should be noted that the issue seems to be biggest in regards of underpredicting, meaning that the model is more likely to predict a lower travel time when the real travel time is actually higher. 


#### Afternoon Rush Hours
<img width="700" alt="image" src="https://github.com/user-attachments/assets/22022557-3721-42f5-af0d-6d26a9e19d96" />  

Of the 41 samples, 13 were underpredicted while 28 were overpredicted, which shows a tendency to overpredict. In this case, that means that the model is more likely to assume slower traffic compared to reality. The plot above also shows the residual values, but it would be more informative if we looked into those with a plot where predicted values are also shown.  

<img width="700" alt="image" src="https://github.com/user-attachments/assets/b4d3a6fc-e282-4818-a01d-f9a2bdc577b4" />  

The first thing that becomes apparent when looking at the plot is how the larger residuals, both negative and positive ones, appear on the larger predicted values. When looking at the lower predicted values, no major residuals are present, but as we move above 120, some large residuals occur. As with the morning model, this suggests that the model's uncertainty increases when predicting higher travel times. The ability to forecast high travel times is one of the most important features of this tool. Therefore, this is certainly something worth monitoring as data grows, and try to improve in the future.

## IAC (Terraform)
The GCP infrastructure is fully managed with Terraform to ensure that it stays consistent and reproducible across both dev and prod environments. This is especially important since both the dev and prod infrastructure live within the same Google Cloud project. The primary difference between them is the suffix of the created resources, which are based on the Terraform workspace in use (which are either 'dev' or 'prod'). Example:  
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
- Deploy updated prediction image to 'prediction-afternoon-dev' Cloud Run service

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

## Final Notes
This project started as a personal frustration with unpredictable rush-hour traffic. It has since turned into a fully automated, production-ready forecasting system powered by real-time data, machine learning, and cloud infrastructure.  

I hope it helps make your commute through Copenhagen a little more predictable.

If you have any questions about the project, collaboration inquiries, or suggestions for improvements, feel free to reach out at allanreda99@gmail.com.

Thanks you for taking the time to read the Readme and for your interest in the project.  
**-Allan Fattah Reda**
