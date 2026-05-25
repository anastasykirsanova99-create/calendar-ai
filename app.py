from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone
import json
import os
import traceback

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']

info = json.loads(os.environ["GOOGLE_CREDENTIALS"])

credentials = service_account.Credentials.from_service_account_info(
    info,
    scopes=SCOPES
)

service = build('calendar', 'v3', credentials=credentials)

CALENDAR_ID = '0114e94607dcd860a84c1fe451c94861d283136be270a76f1e3373108dca2fec@group.calendar.google.com'

TIMEZONE = 'Europe/Kyiv'
WORK_START_HOUR = 9
WORK_END_HOUR = 18
SLOT_DURATION_HOURS = 1
DAYS_AHEAD = 5


def parse_google_dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def format_date(dt):
    return dt.strftime("%d.%m.%Y")


def format_time(dt):
    return dt.strftime("%H:%M")


def is_working_day(dt):
    return dt.weekday() < 5


def slot_overlaps_busy(slot_start, slot_end, busy_start, busy_end):
    return slot_start < busy_end and slot_end > busy_start


@app.route('/create-event', methods=['POST'])
def create_event():
    try:
        data = request.json

        name = data.get('name')
        phone = data.get('phone')
        service_name = data.get('service')
        date = data.get('date')
        time = data.get('time')

        start_dt = datetime.strptime(
            f"{date} {time}",
            "%d.%m.%Y %H:%M"
        )

        end_dt = start_dt + timedelta(hours=1)

        event = {
            'summary': f'{service_name} - {name}',
            'description': f'Телефон: {phone}',
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': TIMEZONE,
            },
        }

        service.events().insert(
            calendarId=CALENDAR_ID,
            body=event
        ).execute()

        return jsonify({
            "success": True,
            "message": "Appointment created"
        })

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/availability', methods=['GET'])
def availability():
    try:
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=DAYS_AHEAD)

        body = {
            "timeMin": now.isoformat(),
            "timeMax": end.isoformat(),
            "timeZone": TIMEZONE,
            "items": [{"id": CALENDAR_ID}]
        }

        result = service.freebusy().query(body=body).execute()
        busy = result["calendars"][CALENDAR_ID].get("busy", [])

        busy_by_date = {}
        suggested_free_slots = []

        busy_intervals = []

        for slot in busy:
            busy_start = parse_google_dt(slot["start"])
            busy_end = parse_google_dt(slot["end"])

            date_key = format_date(busy_start)
            busy_by_date.setdefault(date_key, []).append([
                format_time(busy_start),
                format_time(busy_end)
            ])

            busy_intervals.append((busy_start, busy_end))

        current_day = datetime.now().date()

        checked_days = 0
        day_offset = 0

        while checked_days < DAYS_AHEAD:
            day = current_day + timedelta(days=day_offset)
            day_dt = datetime.combine(day, datetime.min.time())

            day_offset += 1

            if not is_working_day(day_dt):
                continue

            checked_days += 1

            for hour in range(WORK_START_HOUR, WORK_END_HOUR):
                slot_start = datetime(
                    day.year,
                    day.month,
                    day.day,
                    hour,
                    0,
                    tzinfo=timezone.utc
                )

                slot_end = slot_start + timedelta(hours=SLOT_DURATION_HOURS)

                is_busy = False

                for busy_start, busy_end in busy_intervals:
                    if slot_overlaps_busy(slot_start, slot_end, busy_start, busy_end):
                        is_busy = True
                        break

                if not is_busy:
                    suggested_free_slots.append(
                        f"{slot_start.strftime('%d.%m.%Y')} {slot_start.strftime('%H:%M')}"
                    )

        response_data = {
            "working_hours": "09:00-18:00",
            "slot_duration_minutes": 60,
            "has_busy_slots": len(busy_by_date) > 0,
            "busy_by_date": busy_by_date,
            "suggested_free_slots": suggested_free_slots[:20]
        }

        return app.response_class(
            response=json.dumps(response_data, ensure_ascii=False),
            mimetype='application/json'
        )

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
