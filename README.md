# Arias Research Group Scheduler App

[GCal API Documentation](https://google-api-client-libraries.appspot.com/documentation/calendar/v3/python/latest/)

## Setup

1. Go to the [Google Calendar Python API website](https://developers.google.com/calendar/quickstart/python) and follow the first **two** steps there.
    1. Make sure that the Google account that you are using is shown in the top right corner - this should be the one that has write access to the group meeting calendar.
    1. When saving the client configuration, make sure to save it as `credentials.json` in this project directory. If you forget to download it, you can click the same button and it will take you there.
    1. Feel free to name the project whatever you deem fit, it will not affect anything.
    1. If you do not have `python` or `pip` installed, Google is your best friend. As of writing this, Python 3.8 is the newest version. Don't forget to follow step two in the link to grab the necessary Google Calendar API packages.
1. Run the scheduling application: `python3 arg_scheduler.py`. It will take your through a first time setup - follow the link and approve the application. This may require you to click around depending on your browser, but the app will not function until you give it permission with your Google account.
    1. If you accidentally choose the wrong calendar during the first time setup, delete the file `calendar_url.txt` and rerun the application.
1. Populate the `people.txt` with the people that you would like to schedule regularly.
1. That's it! After the first time setup, the app will start up, giving you a list of available actions and a short description. If there is anything that goes wrong, feel free to reach out to me.
