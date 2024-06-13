import os.path
import datetime as dt

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_events():
    creds = None
    result = ""

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        now = dt.datetime.now().isoformat() + "Z"

        event_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = event_result.get("items", [])

        if not events:
            result = "No uncoming events coming"
            return result
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            result = result + str(start, event["summary"]) + "\n"

    except HttpError as e:
        result = result + "An error occurred: " + str(e)
    return result


def create_event():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": "Python test",
            "location": "Home",
            "description": "Details",
            "colorId": 6,
            "start": {
                "dateTime": "2024-06-13T15:00:00+02:00",
                "timeZone": "Europe/Vienna",
            },
            "end": {
                "dateTime": "2024-06-13T16:00:00+02:00",
                "timeZone": "Europe/Vienna",
            },
            "reccurrence": ["RRULE:FREQ=DAILY;COUNT=3"],
            "attendees": [{"email": "timofiyj@gmail.com"}],
        }

        event = service.events().insert(calendarId="primary", body=event).execute()
        print(f"Event created {event.get('htmlLink')}")

    except HttpError as e:
        print("An error occurred: ", e)


if __name__ == "__main__":
    create_event()
