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

It should be noted that two separate datasets are being prepared: one for predicting the next 2 rush hours, and one for predicting the 8 rush hours after that. 
For the latter, it isn't possible to add a 1 day lag or calculate a rolling average for the past 7 days, simply because the data doesn't exist. 

### Model Choice
Upon testing multiple models, the Extra Trees Regressor proved to be the best performer across all parameters. 
<img width="516" height="288" alt="image" src="https://github.com/user-attachments/assets/6979acb5-9c82-46e6-bcd1-815aefdbe039" />

A K-fold cross validation was used here, and was run with both 10, 5, and 3 folds - the Extra Trees Regressor performed best in all three cases.

### Performance

## CI/CD Pipelines
### Dev and Prod Environments
### Website Pipeline
### Cloud Run Pipeline

## IAC (Terraform)
