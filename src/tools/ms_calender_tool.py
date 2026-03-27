from langchain_core.tools import tool
import requests
import os
from msal import ConfidentialClientApplication
from datetime import datetime, timedelta
from src.api.config import settings

TENANT_ID = settings.AZURE_TENANT_ID
CLIENT_ID = settings.AZURE_CLIENT_ID
CLIENT_SECRET = settings.AZURE_CLIENT_SECRET

def get_graph_token():
    """Get Microsoft Graph API token"""
    
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=authority,
        client_credential=CLIENT_SECRET
    )

    token = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    return token["access_token"]


@tool
def get_calendar_meetings(days: float = 1) -> str:
    """
    Fetch meetings from Microsoft Outlook Calendar for the next given days.
    """
    
    token = get_graph_token()

    start = datetime.utcnow().isoformat() + "Z"
    # Ensure days is float or int
    days_float = float(days)
    end = datetime.utcnow() + timedelta(days=days_float)

    url = f"https://graph.microsoft.com/v1.0/me/calendarView"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    params = {
        "startDateTime": start,
        "endDateTime": end.isoformat() + "Z"
    }

    response = requests.get(url, headers=headers, params=params)

    events = response.json().get("value", [])

    if not events:
        return "No meetings found."

    meeting_list = []

    for e in events:
        subject = e.get("subject")
        start_time = e["start"]["dateTime"]
        organizer = e["organizer"]["emailAddress"]["name"]

        meeting_list.append(
            f"{subject} at {start_time} (Organizer: {organizer})"
        )

    return "\n".join(meeting_list)
