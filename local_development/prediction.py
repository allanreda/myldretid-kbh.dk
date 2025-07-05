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

# Optional: Rename relevant columns for clarity
df = df.rename(columns={
    'dt_txt': 'datetime',
    'main.temp': 'temp',
    'main.feels_like': 'feels_like',
    'main.pressure': 'pressure',
    'main.humidity': 'humidity',
    'weather[0].main': 'weather_main',
    'weather[0].description': 'weather_description',
    'wind.speed': 'wind_speed',
    'wind.deg': 'wind_deg',
    'clouds.all': 'cloudiness_percent',
    'rain.3h': 'rain_3h'
})

# Convert datetime to pandas datetime object
df['datetime'] = pd.to_datetime(df['datetime'])
