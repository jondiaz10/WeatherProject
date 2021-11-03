# This is a sample Python script.

import requests as request
import os
import time as time
import sendgrid
from sendgrid.helpers.mail import *


email = ''
zip = ''


class Weather_Caller:

    def __init__(self):
        self.api_key = os.getenv('weather_api_key')
        self.url = ''
        self.units = 'imperial'
        self.zip = '30097'
        self.longitude = ''
        self.latitude = ''
        self.current = ''
        self.current_desc = ''
        self.temp = ''
        self.feels_like = ''
        self.temp_low = ''
        self.temp_high = ''
        self.pressure = ''
        self.humidity = ''
        self.wind_speed = ''
        self.wind_dir = ''
        self.wind_gust = ''
        self.wind_gust = ''
        self.sunrise = ''
        self.sunset = ''
        self.country = ''
        self.city = ''

    def get_current_weather(self, zip, units='imperial'):
        self.zip = zip
        self.units = units
        self.url = Url_Generator(self.zip, self.units).generate().url
        response = request.get(self.url).json()
        self.longitude = response['coord']['lon']
        self.latitude = response['coord']['lat']
        self.current = response['weather'][0]['main']
        self.current_desc = response['weather'][0]['description']
        self.temp = response['main']['temp']
        self.feels_like = response['main']['temp']
        self.temp_low = response['main']['temp_min']
        self.temp_high = response['main']['temp_max']
        self.pressure = response['main']['pressure']
        self.humidity = response['main']['humidity']
        self.wind_speed = response['wind']['speed']
        self.wind_dir = response['wind']['deg']
        #self.wind_gust = response['wind']['gust']
        self.sunrise = time.strftime("%H:%M", time.localtime(int(response['sys']['sunrise'])))
        self.sunset = time.strftime("%H:%M", time.localtime(int(response['sys']['sunset'])))
        self.country = response['sys']['country']
        self.city = response['name']
        return self


class Url_Generator:

    def __init__(self, zip='30097', units='imperial'):
        self.base_url = 'https://api.openweathermap.org/data/2.5/weather?'
        self.api_key = os.getenv('weather_api_key')
        self.zip = zip
        self.units = units

    def generate(self):
        self.url = f'{self.base_url}zip={self.zip},us&units={self.units}&appid={self.api_key}'
        return self


class Emailer:
    def __init__(self):
        self.weather = Weather_Caller()
        self.email_key = os.getenv('email_api_key')
        self.from_email = os.getenv('emailer_address')
        self.subject = f'Current Weather data for {self.weather.zip}'
        self.to_email = ''
        self.content = ''

    def send_email(self, to_email,zip):
        self.to_email = to_email
        self.zip = zip
        self.weather.get_current_weather(self.zip)

        self.content = Content("text/html",  f'<h1> <b>Current Weather for {self.weather.city} ({self.weather.zip}):</b></h1><br>'
                                             f' Current Condition: {self.weather.current}<br>'
                                             f' Expanded Description: {self.weather.current_desc}<br>'
                                             f' Current Temperature: {self.weather.temp}<br>'
                                             f' Feels like: {self.weather.feels_like}<br>'
                                             f' Low for Today: {self.weather.temp_low}<br>'
                                             f' High for Today: {self.weather.temp_high}<br>'
                                             f' Current Pressure: {self.weather.pressure}<br>'
                                             f' Humidity Outside: {self.weather.humidity}<br>'
                                             f' Current Wind: {self.weather.wind_speed}<br>'
                                             f' Wind Direction: {self.weather.wind_dir}<br>'
                                             #f' Wind Gusts: {self.weather.wind_gust}<br>'
                                             f' Sunrise: {self.weather.sunrise}<br>'
                                             f' Sunset: {self.weather.sunset}<br>')
        try:
            sg = sendgrid.SendGridAPIClient(api_key=self.email_key)
            mail = Mail(self.from_email, self.to_email, self.subject, self.content)
            sg.client.mail.send.post(request_body=mail.get())
        except Exception as e:
            print(e.message)

weather_call = Weather_Caller()
email_call = Emailer()
weather_call.get_current_weather(zip=zip)
email_call.send_email(to_email=email,zip=zip)


