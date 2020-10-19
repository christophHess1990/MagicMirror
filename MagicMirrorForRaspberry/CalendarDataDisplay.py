#!/usr/bin/python
#-*- coding:utf-8 -*-

from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from Tkinter import *
import requests
import json
from PIL import Image, ImageTk
from pytz import timezone

#read in data for api
#keys and departure data from txt
f = open("apiData.txt", "r")
fileData = json.loads(f.read())
f.close()

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
#required for weather data
api_key = fileData['weatherAPI']['api_key']
cityID = fileData['weatherAPI']['cityID']
url = "https://api.openweathermap.org/data/2.5/weather?id=%s&appid=%s" % (cityID, api_key)

#setup for departure part of URL (HOME)
departureID = fileData['homeCoordinates']['departureID']
departureLatitude = fileData['homeCoordinates']['departureLatitude']
departureLongitude = fileData['homeCoordinates']['departureLongitude']

#global text
dataList = []
dataListWeather = []
dataPublicTransport = []

#filepath for images
imageDirectory = '/home/pi/MagicMirror/weatherSituation/'

#setup font
fontForApplication = "arial"
fontSizeForApplication = 11

#refreshingTime for API update
thisIsAVariable = 600000

#returns destination part of the request URL
def getURL(stringOfLocationAdress):
    #getting the parameters to request the connections
    #returns an array of location data
    def getLocationParameter(adressString):
        #string gets formatted for request
        def stringFormatter(s):
            #replace important chars for request
            try: resultString = s.replace(" ", "%20")
            except: print("just in case")
            try: resultString = resultString.replace(",", "%2C")
            except: print("no comma")
            #replace special chars
            try: resultString = resultString.replace("ß", "%C3%9F")
            except: print("no ß")
            try: resultString = resultString.replace("Ä", "%C3%84")
            except: print("no Ä")
            try: resultString = resultString.replace("ä", "%C3%A4")
            except: print("no ä")
            try: resultString = resultString.replace("Ö", "%C3%96")
            except: print("no Ö")
            try: resultString = resultString.replace("ö", "%C3%B6")
            except: print("no ö")
            try: resultString = resultString.replace("Ü", "%C3%9C")
            except: print("no Ü")
            try: resultString = resultString.replace("ü", "%C3%BC")
            except: print("no ü")

            return resultString

        #parameters: id, latitude, longitude; name for request gets added later
        parameterArray = []
        #url for location request
        findLocationURL = "https://2.bvg.transport.rest/locations?query="
        locationString = stringFormatter(adressString)
        urlNew = findLocationURL + locationString
        response = requests.get(urlNew)
        locationData = json.loads(response.text)

        #best fit of adress
        locationData = locationData[0]


        return locationData

    #defining destination part for url with all parameters
    def getDestinationURL(stringID, stringName, stringLatitude, stringLongitude):
        destinationURL = "&to.id=%s&to.name=%s&to.latitude=%s&to.longitude=%s" % (stringID, stringName, stringLatitude, stringLongitude)
        return destinationURL

    #defining departure part for url with all parameters
    def getDepartureURL(depID, depName, depLat, depLon):
        departureURL = "https://2.bvg.transport.rest/journeys?from.id=%s&from.name=%s&from.latitude=%s&from.longitude=%s" % (depID, depName, depLat, depLon)
        return departureURL

    dataArray = getLocationParameter(stringOfLocationAdress)
    destinationID = dataArray['id']
    destinationName = "Ziel"
    destinationLatitude = dataArray['latitude']
    destinationLongitude = dataArray['longitude']

    #construct url for request
    url = getDepartureURL(departureID, "Home", departureLatitude, departureLongitude) + getDestinationURL(destinationID, destinationName, destinationLatitude, destinationLongitude)

    return url

#if timeOfArrival empty get next journey
def publicTransportData(adressForRequest, timeOfArrival):
    #dataPublicTransport.clear()
    del dataPublicTransport[:]
    try:
        if(timeOfArrival):
            urlForRequest = getURL(adressForRequest) + "&arrival=" + timeOfArrival
        else:
            urlForRequest = getURL(adressForRequest)
        response = requests.get(urlForRequest)
        data = json.loads(response.text)

        #getting just first result of querry
        travelData = ((data['journeys'])[0])['legs']
        #splitting data
        for step in travelData:
            #in case you have to walk from or to next step
            try:
                helper = step['walking']
                helper = True
            except:
                helper = False
            #message for walking
            if(helper):
                dataPublicTransport.append("zu " + (step['destination'])['name'] + " gehen\n\n")
            else:
                dataPublicTransport.append((step['line'])['name'] + "\n")
                dataPublicTransport.append((step['origin'])['name'] + " nach " + (step['destination'])['name'] + "\n")
                dataPublicTransport.append("in Richtung: " + step['direction'] + "\n")
                dataPublicTransport.append("Abfahrt: " + (((step['departure'].split('T'))[1]).split('+'))[0] + "\n\n")              
    except:
        dataPublicTransport.append("Verbindung zum Server fehlgeschlagen!")


def calendarData():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time

    #getting the next 24hrs for events
    todayTime = datetime.datetime.now()
    tomorrowTime = todayTime + datetime.timedelta(days = 1)
    tomorrowTime = tomorrowTime.replace(microsecond=0)
    tomorrowTime = tomorrowTime.isoformat('T') + '+02:00'

    #maxResults=10, timeMax=tomorrowTime,
    events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=tomorrowTime, maxResults=2, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    #dataList.clear()
    del dataList[:]
    firstEventBoolean = True

    if not events:
        dataList.append("Keine Termine in den nächsten 24 Stunden")
        #print('Nothing to do')
    for event in events:
        #formatting in useable data
        organizerOfEvent = event['organizer'].get('email')
        startDateOfEvent = ((event['start'].get('dateTime')).split('T'))[0]
        startTimeOfEvent = ((((event['start'].get('dateTime')).split('T'))[1]).split('+'))[0]
        endDateOfEvent = ((event['end'].get('dateTime')).split('T'))[0]
        endTimeOfEvent = ((((event['end'].get('dateTime')).split('T'))[1]).split('+'))[0]

        #in case of not set data 'try'
        try: titleOfEvent = event['summary']
        except: titleOfEvent = 'Kein Titel für Termin'
        try: descriptionOfEvent = event['description']
        except: descriptionOfEvent = 'keine Beschreibung'
        try:
            locationOfEvent = event['location']
            if(firstEventBoolean):
                #getting public transport data to event
                publicTransportData(locationOfEvent, startTimeOfEvent)
        except: locationOfEvent = 'kein Ort angegeben'
        try: colorIdOfEvent = event['colorId']
        except: colorIdOfEvent = ''

        if(colorIdOfEvent == ''): colorOfEvent = 'red'
        elif(colorIdOfEvent == '2'): colorOfEvent = 'green'
        elif(colorIdOfEvent == '3'): colorOfEvent = 'purple'
        elif(colorIdOfEvent == '5'): colorOfEvent = 'yellow'
        elif(colorIdOfEvent == '6'): colorOfEvent = 'orange'
        elif(colorIdOfEvent == '7'): colorOfEvent = 'blue'
        else: colorOfEvent = 'unusual'

        #transport data only for first event in querry
        firstEventBoolean = False

        dataList.append("Titel: " + titleOfEvent + "\n")
        dataList.append("Datum: " + startDateOfEvent + "\n")
        dataList.append("Veranstalter: " + organizerOfEvent + "\n")
        dataList.append("Zeit: " + startTimeOfEvent + " - " + endTimeOfEvent + "\n")
        dataList.append("Beschreibung: " + descriptionOfEvent + "\n")
        dataList.append("Ort: " + locationOfEvent + "\n")
        dataList.append("\n")

def weatherData():
    response = requests.get(url)
    data = json.loads(response.text)
    #dataListWeather.clear()
    del dataListWeather[:]

    #process data
    weather_city_name = data['name']
    weather_temperature = data['main']
    weather_temperature = round(weather_temperature['temp']) - 273
    weather_temperature = str(weather_temperature) + " Grad"
    weather_situation = data['weather']
    weather_description = weather_situation[0]['description']
    weather_situation = weather_situation[0]['main']


    dataListWeather.append(weather_city_name)
    dataListWeather.append(weather_situation)
    dataListWeather.append(weather_temperature)
    dataListWeather.append(weather_description)


if __name__ == '__main__':

    #setup GUI
    guiWindow = Tk()
    guiWindow.configure(background="black", cursor='none')
    guiWindow.attributes("-fullscreen", True)
    guiWindow.title("Magic Mirror")
    guiWindow.geometry("600x1024")

    #calendardata in label
    textForLabel = ""
    textLabel = Label(guiWindow, text=textForLabel)
    textLabel.configure(bg="black", fg="white", font=(fontForApplication,fontSizeForApplication), justify="left", wraplength=250)
    textLabel.place(anchor = "nw", relx = 0.05, rely = 0.05)

    #publicTransportData in label
    textPublicTransportLabel = ""
    tranportLabel = Label(guiWindow, text=textForLabel)
    tranportLabel.configure(bg="black", fg="white", font=(fontForApplication,fontSizeForApplication), justify="left", wraplength=250)
    tranportLabel.place(anchor = "nw", relx = 0.05, rely = 0.5)

    #time in label
    current_time = ""
    timeLabel = Label(guiWindow, text=current_time)
    timeLabel.configure(bg="black", fg="white", font=(fontForApplication, 30), justify="left", height = 400)
    timeLabel.place(anchor = "center", relx = 0.8, rely = 0.08)

    #weatherdata in label
    textWeatherLabel = ""
    img = ImageTk.PhotoImage(Image.open(imageDirectory + 'initial.png'))
    imageLabel = Label(guiWindow, image=img)
    weatherLabel = Label(imageLabel, text=textWeatherLabel)
    imageLabel.configure(bg="black", fg="white", font=(fontForApplication, 14), justify="center", height = 350)
    weatherLabel.configure(bg="black", fg="white", font=(fontForApplication, 14), justify="center", wraplength=300)
    imageLabel.place(anchor = "center", relx = 0.8, rely = 0.4)
    weatherLabel.place(anchor = "center", relx = 0.5, rely = 0.95)

    #refresh clock
    def clockRefresh():
        try:
            #UTC Time
            my_now_time = datetime.datetime.now().isoformat()
            #my_now_time = my_now_time.astimezone(timezone('Europe/Berlin'))
            current_time = (((my_now_time.split('T'))[1]).split('.'))[0]

            #clock update
            timeLabel["text"] = current_time
            guiWindow.after(1000, clockRefresh)
        except StopIteration:
            guiWindow.destroy()
    #refresh data after time
    def refresh():

        try:
            thisIsAVariable = 0
            calendarData()
            weatherData()
            textForLabel = ""
            for element in dataList:
                textForLabel = textForLabel + element
            textLabel["text"] = textForLabel

            if(dataPublicTransport):
                textPublicTransportLabel = ""
                for element in dataPublicTransport:
                    textPublicTransportLabel = textPublicTransportLabel + element
                tranportLabel["text"] = textPublicTransportLabel

            #image for weather
            weatherImageFromData = ""
            if(dataListWeather[1] == 'Clouds'):
                if(dataListWeather[3] == 'few clouds'):
                    weatherImageFromData = 'cloudy.png'
                else:
                    weatherImageFromData = 'cloud.png'
            elif(dataListWeather[1] == 'Rain'):  weatherImageFromData = 'rainy.png'
            elif(dataListWeather[1] == 'Clear'): weatherImageFromData = 'sun.png'
            else: weatherImageFromData = 'dontknow.png'
            imgRefresh = ImageTk.PhotoImage(Image.open(imageDirectory + weatherImageFromData))
            imageLabel.configure(image=imgRefresh)
            imageLabel.image = imgRefresh

            textWeatherLabel = ""
            #delete unnecessary data from array (detailed weather situation for image choice)
            dataListWeather.pop(3)
            for element in dataListWeather:
                textWeatherLabel = textWeatherLabel + element + "\n"
            weatherLabel["text"] = textWeatherLabel

            #update every 10 Minutes for calendar data
            guiWindow.after(600000, refresh)
        except StopIteration:
            guiWindow.destroy()

    guiWindow.after(60, clockRefresh)
    guiWindow.after(60, refresh)
    #running formular
    guiWindow.mainloop()
