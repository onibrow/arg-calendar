from __future__ import print_function
import datetime
import readline
import pickle
import os.path
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from timezones import Pacific
import copy

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def rlinput(prompt, prefill=''):
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt)
    finally:
        readline.set_startup_hook()
        
def yes_no(prompt):
    user_input = None
    while (user_input is None):
        user_input = input(prompt).lower()
        if (user_input != 'y' and user_input != 'n'):
            user_input = None
            print("Invalid input. [Y] or [N] (case insensitive)")
    return user_input == 'y'

def int_prompt(prompt, lower_bound=0, upper_bound=10000):
    user_input = None
    while (user_input is None):
        try:
            user_input = int(input(prompt))
            if (user_input < lower_bound or user_input > upper_bound):
                user_input = None
                raise ValueError
        except ValueError:
            print("Invalid input. ({},{}) inclusive".format(lower_bound, upper_bound))
    return user_input
        

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
    
def load_calendars():
    cal_dict = {}
    with open('calendars.csv', 'r') as fp:
        line = fp.readline().split(',')
        while (line[0] != ''):
            cal_dict[line[0]] = line[1].strip()
            line = fp.readline().split(',')
    return cal_dict

def get_datetime_obj(day, month, year):
    return datetime.datetime(year, month, day).isoformat() + 'Z'

def get_datetime_now():
    return datetime.datetime.combine(datetime.datetime.now(tz=Pacific).date(), 
                                     datetime.datetime.min.time()).isoformat() + 'Z'

def get_datetime_2_week_ago():
    return datetime.datetime.combine((datetime.datetime.now(tz=Pacific).date()  - datetime.timedelta(days=14)), 
                                     datetime.datetime.min.time()).isoformat() + 'Z'

def datetime_to_api_format(dt, dur):
    dt_copy = datetime.datetime(dt.year, dt.month, dt.day, hour=dt.hour, minute=dt.minute, tzinfo=Pacific)
    return [dt_copy.isoformat(), (dt_copy + dur).isoformat()]

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

def extract_datetime(query):
    match = re.search('^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):\d{2}-.*$', query)
    if (match is None):
        print("No datetime found")
    return datetime.datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)),
                             hour=int(match.group(4)), minute=int(match.group(5)))

def get_event_type(summary):
    match = re.search('^.*\[(.*?)\].*$', summary)
    if (match is None):
        return None
    return match.group(1)

def list_all_research_events(start_date, creds, service, cal='primary'):
    events_result = service.events().list(calendarId=cal, timeMin=start_date,
                                        maxResults=None, singleEvents=True,
                                        orderBy='startTime', timeZone='US/Pacific').execute()
    events = events_result.get('items', [])

    events_info_list = []
    if not events:
        print('No upcoming events found.')
    for event in events:
        event_type = get_event_type(event['summary'])
        if (event_type is not None):
            try:
                day = extract_day(event['start'].get('dateTime', event['start'].get('date')))
                start_time = extract_time(event['start'].get('dateTime', event['start'].get('date')))
                end_time   = extract_time(event['end'].get('dateTime', event['end'].get('date')))
                dur   = end_time - start_time
                event_name = re.search('^.*\[.*\]\s*?(\S.*)$', event['summary']).group(1)
                events_info_list += [Event(event_name, event_type, day, dur)]
            except AttributeError:
                print("AttributeError: {}".format(event['summary']))
    return events_info_list

class Event(object):
    def __init__(self, name, event_type, date, duration):
        self.name = name
        self.event_type = event_type
        self.date = date
        self.dura = duration

    def __str__(self):
        return "{} type [{}] on {} for {}".format(self.name, self.event_type, self.date, self.dura)
    
class GM_Event(Event):
    def __init__(self,  index, datetime, duration, names):
        self.index = index
        self.date = datetime
        self.dura = duration
        self.names = names
        self.title = self.gen_event_name()
    
    def gen_event_name(self):
        if (self.names[1] == 'None'):
            return "{}, Group Meeting".format(self.names[0])
        else:
            return "{} and {}, Group Meeting".format(self.names[0], self.names[1])
        
    def update_index(self, i):
        self.index = i
    
    def update_names(self, n):
        if (n[0] == 'None'):
            n = n[::-1]
        self.names = n
        self.title = self.gen_event_name()
        
    def update_datetime(self, dt):
        self.date = copy.copy(dt)
        
    def swap_names(self):
        self.names = self.names[::-1]
        
        
class Group_Meetings(object):
    def __init__(self):
        (self.creds, self.service) = get_creds_service()
        self.api_calendar = load_calendars()['Research Test']
        (self.events, self.api_events) = self.list_all_group_meetings()
        self.og_events = copy.deepcopy(self.events)
        self.all_names = self.enumerate_all_names()
        self.refresh()
        
    def reinit(self):
        (self.events, self.api_events) = self.list_all_group_meetings()
        self.og_events = copy.deepcopy(self.events)
        self.all_names = self.enumerate_all_names()
        self.refresh()
        
    def list_all_group_meetings(self):
        start_date = get_datetime_2_week_ago()
        events_result = self.service.events().list(calendarId=self.api_calendar, timeMin=start_date,
                                            maxResults=None, singleEvents=True,
                                            orderBy='startTime', timeZone='US/Pacific').execute()
        events = events_result.get('items', [])

        events_info_list = []
        api_events = []
        if not events:
            print('No upcoming events found.')
        index = 0
        for event in events:
            match = re.search('^.*?Group Meeting.*?$', event['summary'])
            if (match is not None):
                try:
                    day = extract_datetime(event['start'].get('dateTime', event['start'].get('date')))
                    start_time = extract_time(event['start'].get('dateTime', event['start'].get('date')))
                    end_time   = extract_time(event['end'].get('dateTime', event['end'].get('date')))
                    dur   = end_time - start_time
                    names = Group_Meetings.extract_names(event['summary'])
                    events_info_list += [GM_Event(index, day, dur, names)]
                    api_events += [event['id']]
                    index += 1
                except AttributeError:
                    print("AttributeError: {}".format(event['summary']))
        return (events_info_list, api_events)
    
    def pretty_print(self, events_list=True):
        if (events_list is True):
            events_list = self.events
        longest_event = max(events_list, key=lambda event: (len(event.title) + len(str(event.index)) + 3))
        width = len(longest_event.title) + len(str(longest_event.index)) + 3
        to_print = ""
        for event in events_list:
            to_print += "+{}+\n| [{}] {} |\n| {} |\n| {} |\n+{}+\n".format("-" * (width+2), 
                    event.index,
                    event.title + " " * (width - len(event.title) - len(str(event.index)) - 3), 
                    str(event.date.date()) + " " * (width - len(str(event.date.date()))),
                    str(event.date.time()) + " " * (width - len(str(event.date.time()))),
                    "-" * (width+2))
        return to_print
    
    def extract_names(summary):
        names = []
        match = re.search("^(.*)\sand\s(.*),\sGroup Meeting", summary)
        if (match is not None):
            names += [match.group(1), match.group(2)]

        if (match is None):
            match = re.search("^(.*),\sGroup Meeting", summary)
            if (match is not None):
                names += [match.group(1), 'None']
        return names

    def refresh(self):
        for i in range(len(self.events)):
            if (self.events[i].names == ['None', 'None']):
                self.events.remove(self.events[i])
            i -= 1
        self.all_names = self.enumerate_all_names()
        self.renumerate()
        
    def enumerate_all_names(self):
        names = []
        for x in self.events:
            for n in x.names:
                names += [n]
        return names

    def print_names(self):
        i = 0
        for n in self.all_names:
            print("[{}] {}".format(i, n))
            i += 1
            if (i % 2 == 0 and i != len(self.all_names)):
                print("---------")
            
    def renumerate(self):
        for i in range(len(self.events)):
            self.events[i].update_index(i)
    
    def delay_event(self):
        print(self.pretty_print())
        i = int_prompt("\nInput event index to delay: ", lower_bound=0, upper_bound=(len(self.events)-1))
        new_events = copy.deepcopy(self.events)
        while (i < len(new_events) - 1):
            new_events[i].update_datetime(self.events[i+1].date)
            i += 1
        new_events[i].update_datetime(self.events[i].date + datetime.timedelta(days=7))
        print("\nPreview:\n")
        print(self.pretty_print(events_list=new_events))
        if (yes_no("Proceed? [Y/N]: ")):
              self.events = new_events
    
    def split_event(self):
        print(self.pretty_print())
        i = int_prompt("\nWhich meeting gets split? (input [#]): ", lower_bound=0, upper_bound=(len(self.events)-1))
        name_split = self.events[i].names
        j = int_prompt("\nWhich person gets pushed back?\n[0] {}\n[1] {}\nInput index (0 or 1): ".format(name_split[0], name_split[1]), 
                       lower_bound=0, upper_bound=1)
        print("\nPreview:\n")
        new_names = copy.copy(self.all_names)
        if (j == 0):
            first = new_names[i*2]
            new_names[i*2] = new_names[i*2 + 1]
            new_names[i*2 + 1] = first
        new_names.insert(i * 2 + 1, 'None')
        if (len(new_names) % 2 == 1):
            new_names += ['None']           
        i = 0
        for n in new_names:
            print("[{}] {}".format(i, n))
            i += 1
            if (i % 2 == 0 and i != len(new_names)):
                print("---------")
        if (yes_no("Proceed? [Y/N]: ")):
            self.events += [GM_Event(len(self.events), self.events[-1].date + datetime.timedelta(days=7), self.events[-1].dura, ['None', 'None'])]
            event_index = 0
            while (event_index < len(self.events)):
                to_add_names = new_names[event_index * 2: event_index * 2 + 2]
                self.events[event_index].update_names(to_add_names)
                event_index += 1
            self.refresh()
        
    def trash_changes(self):
        self.events = copy.deepcopy(self.og_events)
        
    def gm_event_to_api_event(self, gm_event):
        times = datetime_to_api_format(gm_event.date, gm_event.dura)
        event = {'summary': gm_event.title,
                 'start': {
                     'dateTime': times[0],
                     'timeZone': 'UTC'},
                 'end': {
                     'dateTime': times[1],
                     'timeZone': 'UTC'}}
        return event

                                   
    def delete_old_revision(self):
        for x in self.api_events:
            self.service.events().delete(calendarId=self.api_calendar, eventId=x).execute()                            
        
    def publish_changes(self):
        for event in self.events:
            api_event = self.gm_event_to_api_event(event)
            self.service.events().insert(calendarId=self.api_calendar, body=api_event).execute()
        self.delete_old_revision()
        self.reinit()
        print("Published Changes.")