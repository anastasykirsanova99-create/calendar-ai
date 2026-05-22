from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from num2words import num2words
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


# =========================
# CREATE EVENT
# =========================
@app.route('/create-event', methods=['POST'])
def create_event():
    data = request.json

    name = data.get('name')
    phone = data.get('phone')
    service_name = data.get('service')
    date = data.get('date')
    time = data.get('time')

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

    return jsonify({"success": True})


# =========================
# AVAILABILITY
# =========================
@app.route('/availability', methods=['GET'])
def availability():
    now = datetime.utcnow()
    end = now + timedelta(days=5)

    body = {
        "timeMin": now.isoformat() + "Z",
        "timeMax": end.isoformat() + "Z",
        "timeZone": "Europe/Kyiv",
        "items": [{"id": CALENDAR_ID}]
    }

    result = service.freebusy().query(body=body).execute()

    busy = result["calendars"][CALENDAR_ID]["busy"]

    months_ua = {
        1: "січня",
        2: "лютого",
        3: "березня",
        4: "квітня",
        5: "травня",
        6: "червня",
        7: "липня",
        8: "серпня",
        9: "вересня",
        10: "жовтня",
        11: "листопада",
        12: "грудня"
    }

    busy_slots = []

    for slot in busy:
        start_dt = datetime.fromisoformat(slot["start"])
        end_dt = datetime.fromisoformat(slot["end"])

        # День словами
        day_text = num2words(start_dt.day, lang='uk')

        # Рік словами
        year_text = num2words(start_dt.year, lang='uk')

        # Години словами
        start_hour = num2words(start_dt.hour, lang='uk')
        end_hour = num2words(end_dt.hour, lang='uk')

        formatted = (
            f"{day_text} "
            f"{months_ua[start_dt.month]} "
            f"{year_text} року "
            f"з {start_hour} "
            f"до {end_hour}"
        )

        busy_slots.append(formatted)

    return jsonify({
        "busy_slots": busy_slots
    })


# =========================
# RUN SERVER (Render)
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
