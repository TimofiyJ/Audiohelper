import os.path
import datetime as dt
from typing_extensions import Annotated
from typing import List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/calendar"]


def create_event(
    summary: Annotated[str, "Summary of the event or how should it be called"],
    location: Annotated[str, "Location of the event"],
    description: Annotated[str, "Description of the event"],
    start: Annotated[
        str,
        "Start time of the event. Has to be in this format: \
                                  yyyy-mm-ddThh:mm:ss+02:00 \
                                  where y is for year, m for month, d for day, h for hour, m for minute \
                                  s for second",
    ],
    end: Annotated[
        str,
        "End time of the event. Has to be in this format: \
                                  yyyy-mm-ddThh:mm:ss+02:00 \
                                  where y is for year, m for month, d for day, h for hour, m for minute \
                                  s for second",
    ],
    attendees: Annotated[str, "Email of attendee"],
) -> dict:
    creds = None
    response = {}
    response["code"] = 0
    result = ""

    if summary == "" or start == "" or end =="":
        result = "Not enough parameters provided"
        response["code"] = 500

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
            "summary": summary,
            "colorId": 6,
            "start": {
                "dateTime": start,
                "timeZone": "Europe/Vienna",
            },
            "end": {
                "dateTime": end,
                "timeZone": "Europe/Vienna",
            }
        }

        if location != "":
            event["location"] = location
        
        if description != "":
            event["description"] = description

        event = service.events().insert(calendarId="primary", body=event).execute()
    except HttpError as e:
        result = "An error occurred: " + str(e)
        response["code"] = 500

    response["text"] = result
    if response["code"] != 500:
        response["code"] = 200
    return response


if __name__ == "__main__":
    create_event(
        summary="supper",
        start="2024-06-21T10:00:00+02:00",
        end="2024-06-21T11:00:00+02:00",
        location="Home",
        description="aboba",
        attendees="",
    )
