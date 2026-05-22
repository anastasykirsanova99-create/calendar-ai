from flask import Flask, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Google credentials из Render Environment
info = json.loads(os.environ["GOOGLE_CREDENTIALS"])

credentials = service_account.Credentials.from_service_account_info(
    info,
    scopes=SCOPES
)

service = build('calendar', 'v3', credentials=credentials)

CALENDAR_ID = '0114e94607dcd860a84c1fe451c94861d283136be270a76f1e3373108dca2fec@group.calendar.google.com'


@app.route('/create-event', methods=['POST'])
def create_event():
    data = request.json

    name = data.get('name')
    phone = data.get('phone')
    service_name = data.get('service')
    date = data.get('date')
    time = data.get('time')

    # start time
    start_dt = datetime.fromisoformat(f"{date}T{time}:00")
    end_dt = start_dt + timedelta(hours=1)

    event = {
        'summary': f'{service_name} - {name}',
        'description': f'Телефон: {phone}',
        'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': 'Europe/Kyiv',
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': 'Europe/Kyiv',
        },
    }

    service.events().insert(
        calendarId=CALENDAR_ID,
        body=event
    ).execute()

    return {"success": True}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
