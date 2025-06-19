# memory/agenda.py

#!/usr/bin/env python3

import asyncio
import subprocess
import json
import os
import requests
import feedparser
from datetime import date, datetime
from open_meteo import OpenMeteo
from open_meteo.models import DailyParameters
from babel.dates import format_date

# ✅ Config
LAT, LON = 41.27, -72.97  # West Haven, CT
REMINDER_FILE = "memory/reminders.json"
NEWS_FEEDS = [
    "http://feeds.bbci.co.uk/news/rss.xml",
    "http://feeds.arstechnica.com/arstechnica/index",
    "https://www.theverge.com/rss/index.xml"
]
BIBLE_API = "https://labs.bible.org/api/?passage=votd&type=json"

# 📢 Use TTS
def speak(text):
    subprocess.run(["python3", "scripts/say.py", text])

def c_to_f(c): return round(c * 9 / 5 + 32, 1)

def clothing_recommend(temp_f, rain_mm, wind_kph):
    if temp_f < 50:
        return "Wear a coat and scarf."
    elif temp_f < 65:
        return "Light jacket recommended."
    elif temp_f > 85:
        return "It’s hot — dress cool and stay hydrated."
    else:
        return "T-shirt and pants or a light dress should be fine."

def fetch_news():
    headlines = []
    for feed_url in NEWS_FEEDS:
        feed = feedparser.parse(feed_url)
        headlines += [e.title for e in feed.entries[:2]]
    return headlines[:5]

def fetch_bible_quote():
    try:
        resp = requests.get(BIBLE_API)
        if resp.ok:
            j = resp.json()[0]
            return f"{j['verse']} — {j['text']}"
    except:
        pass
    return "Bible quote unavailable."

def fetch_today_reminders():
    if not os.path.exists(REMINDER_FILE):
        return []
    with open(REMINDER_FILE) as f:
        try:
            reminders = json.load(f)
        except json.JSONDecodeError:
            return []

    today_str = date.today().isoformat()
    return [
        r["task"]
        for r in reminders
        if not r.get("triggered") and r.get("time", "").startswith(today_str)
    ]

async def agenda_task():
    speak("Good morning! Here is your agenda for today.")
    print("\n⏰ Good morning! Here's your agenda for today:\n")

    # ☁️ Weather
    async with OpenMeteo() as om:
        forecast = await om.forecast(
            latitude=LAT,
            longitude=LON,
            daily=[
                DailyParameters.TEMPERATURE_2M_MAX,
                DailyParameters.PRECIPITATION_SUM,
                DailyParameters.WIND_SPEED_10M_MAX,
                DailyParameters.WEATHER_CODE,
            ],
            timezone="auto"
        )
        daily = forecast.daily

        max_c = daily.temperature_2m_max[0]
        rain_mm = daily.precipitation_sum[0]
        wind_kph = daily.wind_speed_10m_max[0]
        max_f = c_to_f(max_c)

        print(f"🌡️ High: {max_f}°F")
        print(f"🌧️ Rain: {rain_mm} mm")
        print(f"🌬️ Wind: {wind_kph} km/h")
        suggestion = clothing_recommend(max_f, rain_mm, wind_kph)
        print(f"🧥 Suggestion: {suggestion}\n")

        speak(f"The high will be {max_f} degrees Fahrenheit. {suggestion}")

    # 📰 News
    print("📰 Today's top news:")
    headlines = fetch_news()
    for headline in headlines:
        print(" •", headline)
    speak("Here are the top news headlines.")

    # ✝️ Bible Verse
    bible = fetch_bible_quote()
    print("\n📖 Bible Verse:")
    print(bible)
    speak("Here is your Bible verse of the day.")
    speak(bible)

    # 🗓 Events
    reminders = fetch_today_reminders()
    if reminders:
        print("\n📌 Today's Reminders:")
        for r in reminders:
            print(" •", r)
        speak(f"You have {len(reminders)} reminders today.")
    else:
        print("\n✅ No scheduled reminders for today.")
        speak("You have no scheduled reminders for today.")

    print("\n✅ Agenda complete.\n")

# ✅ Agenda loop (no schedule, no threads)
async def agenda_loop():
    print("🗓️ Async agenda running... waiting for 06:30...")
    already_triggered_today = False

    while True:
        now = datetime.now()

        # Reset trigger flag after midnight
        if now.hour == 0 and now.minute == 0:
            already_triggered_today = False

        # Trigger at 6:30am
        if now.hour == 6 and now.minute == 30 and not already_triggered_today:
            await agenda_task()
            already_triggered_today = True

        await asyncio.sleep(30)


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        print("🧪 Running agenda task once (test mode)...")
        try:
            asyncio.run(agenda_task())
        except Exception as e:
            print(f"❌ Test run failed: {e}")
        else:
            print("✅ Test run complete.")
    else:
        try:
            asyncio.run(agenda_loop())
        except KeyboardInterrupt:
            print("🛑 Agenda stopped by user.")

