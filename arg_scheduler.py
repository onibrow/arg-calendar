from cal_helper import *
import datetime
import time
import readline
import pickle
import os.path
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from timezones import Pacific
import copy

calendar_name = 'Arias Group Meeting'

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
        self.api_calendar = load_calendars()[calendar_name]
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
        self.events.sort(key=lambda event: event.date)
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
        new_events = copy.deepcopy(self.events)
        new_events += [GM_Event(len(new_events), new_events[-1].date + datetime.timedelta(days=7), new_events[-1].dura, ['None', 'None'])]
        event_index = 0
        while (event_index < len(new_events)):
            to_add_names = new_names[event_index * 2: event_index * 2 + 2]
            new_events[event_index].update_names(to_add_names)
            event_index += 1
        print(self.pretty_print(events_list=new_events))

        if (yes_no("Proceed? [Y/N]: ")):
            self.events = new_events
            self.refresh()

    def remove_person(self):
        print(self.pretty_print())
        i = int_prompt("\nWhich meeting? (input [#]): ", lower_bound=0, upper_bound=(len(self.events)-1))
        name_split = self.events[i].names
        j = int_prompt("\nWhich person gets removed?\n[0] {}\n[1] {}\nInput index (0 or 1): ".format(name_split[0], name_split[1]),
                       lower_bound=0, upper_bound=1)
        print("\nPreview:\n")
        new_names = copy.copy(self.all_names)
        del new_names[i * 2 + j]
        if (len(new_names) % 2 == 1):
            new_names += ['None']
        i = 0
        new_events = copy.deepcopy(self.events)
        event_index = 0
        while (event_index < len(new_events)):
            to_add_names = new_names[event_index * 2: event_index * 2 + 2]
            new_events[event_index].update_names(to_add_names)
            event_index += 1
        print(self.pretty_print(events_list=new_events))

        if (yes_no("Proceed? [Y/N]: ")):
            self.events = new_events
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
        print("Saving changes to Google Calendar...\n")
        for event in self.events:
            api_event = self.gm_event_to_api_event(event)
            self.service.events().insert(calendarId=self.api_calendar, body=api_event).execute()
        self.delete_old_revision()
        self.reinit()
        print("Published Changes.")

    def schedule_meetings(self):
        first_date = None
        while(first_date is None):
            mont = int_prompt("Month (0:12): ", lower_bound=0, upper_bound=12)
            day  = int_prompt("Date (0:31): ", lower_bound=0, upper_bound=31)
            year = int_prompt("Year: ")
            hour = int_prompt("Hour (0:24): ", lower_bound=0, upper_bound=23)
            minu = int_prompt("Minute (0:60): ", lower_bound=0, upper_bound=59)
            try:
                first_date = datetime.datetime(year, mont, day, hour=hour, minute=minu)
            except ValueError:
                first_date = None
                print("Invalid Date/Time Format.")
        dura = datetime.timedelta(minutes=int_prompt("Duration (minutes): ", lower_bound=0))
        people_list = []
        with open("people.txt", 'r') as fp:
            line = fp.readline()
            while (line != ''):
                people_list += [line.strip()]
                line = fp.readline()
        if (len(people_list) % 2 == 1):
            people_list += ['None']
        new_event_list = []
        for i in range(len(people_list) // 2):
            new_event_list += [GM_Event(0, first_date, dura, [people_list[i*2], people_list[i*2 + 1]])]
            first_date += datetime.timedelta(days=7)
        print(self.pretty_print(events_list=new_event_list))
        if (yes_no("Proceed? [Y/N]: ")):
            self.events += new_event_list
            self.refresh()

    def preview_changes(self):
        print(self.pretty_print())
        input("Press Enter to continue ")

def load_actions(actions, desc):
    print("Available Actions\n(Press Control+C to exit at anytime):\n")
    for i in range(len(actions)):
        print("[{}] {}\n({})\n".format(i, actions[i], desc[i]))
    return int_prompt("Select an option [#]: ", lower_bound=0, upper_bound=(len(actions)-1))

def main():
    print("+------------------------------------+\n"\
          "| Arias Group Meeting Scheduling App |\n"\
          "+------------------------------------+")
    group_meetings = Group_Meetings()
    actions_to_functions = [group_meetings.delay_event,
               group_meetings.split_event,
               group_meetings.remove_person,
               group_meetings.schedule_meetings,
               group_meetings.trash_changes,
               group_meetings.preview_changes,
               group_meetings.publish_changes]
    actions = ['Delay Event', 'Split Event', 'Remove Presenter', 'Schedule Meetings', 'Discard Changes', 'Preview Changes', 'Publish Changes']
    desc    = ['Push back all events from a chosen date',
               'Split a meeting from two people to one. Pushes back all names',
               'Remove one presentor and pull people forwards',
               'Schedule future group meetings',
               'Discard changes and revert to posted calendar',
               'Preview edits that have been made',
               'Publish changes to Google Calendar']
    while (True):
        actions_to_functions[load_actions(actions, desc)]()
        time.sleep(2)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExitting...")
