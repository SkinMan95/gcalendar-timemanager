from __future__ import print_function
import datetime
import pickle
import os.path
import argparse
import re
from settings import *
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def parse_cli_parameters():
    """
    parses command line parameters and sets it in a settings singleton instance
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--credentials", type=str, default="credentials.json",
                        help="location of JSON credentials file (default: credentials.json)")
    
    parser.add_argument("startdate", type=str,
                        help="checking start date (format: 'yyyy/mm/dd')")
    
    parser.add_argument("calendars", nargs="+", type=str,
                        help="calendars to get the information from, at least one")

    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    settings = Settings()
    settings.setSetting("debug", args.verbose)
    settings.setSetting("credentials", args.credentials)
    settings.setSetting("calendars", args.calendars)
    settings.setSetting("startdate", args.startdate)

def procdate(s) -> datetime:
    r = re.match(r'(\d{4})/(\d{1,2})/(\d{1,2})', s)
    y, m, d = [int(i) for i in [r.group(1), r.group(2), r.group(3)]]
    date = datetime.datetime(y, m, d)
    return date

def date_from_isoformat(s) -> datetime:
    d=datetime.datetime(*map(int, re.split('[^\d]', s)[:-1]))
    return d
    
class GCalendarTMException(Exception):
    """GCalendarTMException"""
    
class GCalendarTM(object):
    class __GCalendarTM(object):
        def setCredentials(self, cred):
            if cred and cred.valid:
                self.cred = cred
                self.service = build('calendar', 'v3', credentials=self.cred)
            else:
                raise GCalendarTMException("no valid credentials")

        def check(self):
            if not self.cred or not self.cred.valid:
                raise GCalendarTMException("no valid credentials")
            if not self.service:
                raise GCalendarTMException("no service instantiated")
            
        def example(self):
            # Call the Calendar API
            now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
            print('Getting the upcoming 10 events')
            events_result = self.service.events().list(calendarId='primary', timeMin=now,
                                                  maxResults=10, singleEvents=True,
                                                  orderBy='startTime').execute()
            events = events_result.get('items', [])

            if not events:
                print('No upcoming events found.')
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(start, event['summary'])
                
        def getCalendars(self):
            calendars = self.service.calendarList().list().execute()

            Utilities().lprint(calendars['items'])

            calendarList = []
            for e in calendars["items"]:
                cal_id = e.get("id")
                cal = e.get('summaryOverride', e.get('summary'))
                Utilities().lprint("Calendar name: '{}'".format(cal))
                assert cal is not None, "should not be None: {}".format(cal)
                calendarList.append((cal_id, cal))
                
            return calendarList

        def getListOfEvents(self, calendar_id, startdate):
            page_token = None
            events = []
            startdate = startdate.isoformat() + 'Z'
            condition = True
            while condition:
                events_result = self.service.events().list(calendarId=calendar_id,
                                                           timeMin=startdate,
                                                           pageToken=page_token).execute()

                Utilities().lprint("Events petition:", events_result)
                events.extend(events_result.get('items', []))

                page_token = events_result.get('nextPageToken')
                condition = bool(page_token)

            return events
        
        def getEventsFrom(self, calendar_id, startdate):
            events = self.getListOfEvents(calendar_id, startdate)

            filteredEvents = [event for event in events if event.get('start', dict()).get('dateTime') is not None]

            finalEvents = []
            
            if not filteredEvents:
                Utilities().lprint('No events found.')
            for event in filteredEvents:
                start = date_from_isoformat(event['start'].get('dateTime'))
                end   = date_from_isoformat(event['end'].get('dateTime'))
                Utilities().lprint(start, event['summary'])
                delta = end - start

                e = (event['summary'], str(start), delta.total_seconds() / 3600)
                Utilities().lprint(e)
                finalEvents.append(e)

            return finalEvents

    instance = None
    def __init__(self):
        if not GCalendarTM.instance:
            GCalendarTM.instance = GCalendarTM.__GCalendarTM()

    def __getattr__(self, name):
        Utilities().lprint(">>> Method called: '%s'" % (name))
        if name != 'setCredentials':
            assert self.instance, "no instance instantiated"
            self.instance.check()
        return getattr(self.instance, name)

def print_dedication_table(dedication):
    hours_length = len(str(sum(dedication.values()))) +1
    subject_length = max([len(k) for k in dedication.keys()]) +1

    string_format = "%{}s |%{}.1f".format(subject_length, hours_length)
    for k in dedication.keys():
        print(string_format % (k, dedication[k]))

    print()
    print(string_format % ("TOTAL", sum(dedication.values())))
    
def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    parse_cli_parameters()
    
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
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    settings = Settings()
    
    startdate = procdate(settings.getSetting('startdate'))
            
    GCalendarTM().setCredentials(creds)
    calendars = GCalendarTM().getCalendars()


    calendarFilter = settings.getSetting("calendars")
    assert isinstance(calendarFilter, list), type(calendarFilter)
    assert all([cal in map(lambda x: x[-1], calendars) for cal in calendarFilter]), "not all calendar filters are in user account"

    Utilities().lprint("startdate: {}".format(startdate))
    Utilities().lprint("calendar filters: {}".format(calendarFilter))
    cals = [cal for cal in calendars if cal[-1] in calendarFilter]

    dedication = dict()
    
    for cal in cals:
        Utilities().lprint("Getting events from: {}".format(cal))
        events = GCalendarTM().getEventsFrom(cal[0], startdate)
        for event in events:
            dedication[event[0]] = dedication.get(event[0], 0) + event[-1]

    print_dedication_table(dedication)
    
if __name__ == '__main__':
    main()
