import requests
import json
import pandas as pd
from pathlib import Path

# OpenWeather API - current
# Provides realtime data
# https://openweathermap.org/current

api_key = Path("C:/Users/allan/Desktop/Personlige projekter/openweather_api_key.txt").read_text()

response = requests.get(f'https://api.openweathermap.org/data/2.5/forecast?q=Copenhagen,DK&appid={api_key}')
print(response.content)


# Assume you already have the `response` from the API
data = json.loads(response.content)

# Extract the forecast list
forecast_list = data['list']

# Normalize the nested structure
df = pd.json_normalize(forecast_list)

df['weather'] = [entry['weather'][0]['main'] for entry in forecast_list]

df = df.drop(['main.temp_kf','main.temp_min', 'main.temp_max', 'main.pressure',"dt","pop","wind.deg","main.grnd_level","main.sea_level","wind.gust","rain.3h","sys.pod"], axis="columns")

# Rename relevant columns for clarity
df = df.rename(columns={
    'weather': "weather_main", 
    'dt_txt': "datetime", 
    'main.temp': "temperature", 
    'main.feels_like': "feels_like",
    'main.humidity': "humidity_percent", 
    'clouds.all': "cloudiness_percent", 
    'wind.speed': "wind_speed"
})


# Convert datetime to pandas datetime object
df['datetime'] = pd.to_datetime(df['datetime'])
