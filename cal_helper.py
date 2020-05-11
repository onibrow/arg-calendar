from __future__ import print_function
import datetime
import pickle
import os.path
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_creds_service():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
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
    return (creds, service)

def list_calendars(creds, service):
    list_cals = service.calendarList().list().execute()
    for x in list_cals.get('items'):
        print("{}: {}".format(x.get("summary"), x.get("id")))

def get_datetime_obj(day, month, year):
    blah = datetime.datetime(year, month, day).isoformat() + 'Z'
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    #print("Now: {} Blah: {}".format(now, blah))
    return blah

def extract_day(query):
    match = re.search('^(\d{4})-(\d{2})-(\d{2})T.*$', query)
    if (match is None):
        print("No day found")
    return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

def extract_time(query):
    match = re.search('^.*T(\d{2}):(\d{2}):\d{2}-.*$', query)
    if (match is None):
        print("No time found")
    return datetime.timedelta(hours=int(match.group(1)), minutes=int(match.group(2)))

def get_event_type(summary):
    match = re.search('^.*\[(.*?)\].*$', summary)
    if (match is None):
        return None
    return match.group(1)

def list_all_events(start_date, creds, service, cal='primary'):
    events_result = service.events().list(calendarId=cal, timeMin=start_date,
                                        maxResults=10, singleEvents=True,
                                        orderBy='startTime', timeZone='US/Pacific').execute()
    events = events_result.get('items', [])

    events_info_list = []
    if not events:
        print('No upcoming events found.')
    for event in events:
        event_type = get_event_type(event['summary'])
        if (event_type is not None):
            day = extract_day(event['start'].get('dateTime', event['start'].get('date')))
            start_time = extract_time(event['start'].get('dateTime', event['start'].get('date')))
            end_time   = extract_time(event['end'].get('dateTime', event['end'].get('date')))
            dur   = end_time - start_time
            event_name = re.search('^.*\[.*\]\s*?(\S.*)$', event['summary']).group(1)
            events_info_list += [Event(event_name, event_type, day, dur)]
    return events_info_list

class Event(object):
    def __init__(self, name, event_type, date, duration):
        self.name = name
        self.event_type = event_type
        self.date = date
        self.dura = duration

    def __str__(self):
        return "{} type [{}] on {} for {}".format(self.name, self.event_type, self.date, self.dura)

def main():
    (creds, service) = get_creds_service()
    start_date = get_datetime_obj(26, 8, 2019)
    events = list_ten_events(start_date, creds, service, cal=research_cal)
    for x in events:
        print(x)
    #get_datetime_obj(1,2,2020)

if __name__ == '__main__':
    main()