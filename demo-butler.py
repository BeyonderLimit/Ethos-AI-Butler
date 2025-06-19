# demo-butler.py

#!/usr/bin/env python3

import os
import shutil
import json
import time
import threading
from datetime import datetime
import dateparser
import spacy
import subprocess
import sys
import parsedatetime as pdt

cal = pdt.Calendar()

# Load small spaCy model
nlp = spacy.load("en_core_web_sm")

# Simple intent detection keywords
INTENT_KEYWORDS = {
    "reminder": ["remind", "reminder", "alert", "notify"],
    "move_file": ["move", "relocate", "archive"],
    "list_reminders": ["list reminders", "show reminders"]
}

REMINDER_FILE = "memory/reminders.json"


def speak(text):
    subprocess.run(["python3", "scripts/say.py", text])
    print(f"[SAY] {text}")
    # Replace with subprocess to your TTS if desired:
    # subprocess.run(["python3", "scripts/say.py", text])


def save_reminder(task, when):
    if not os.path.exists("memory"):
        os.makedirs("memory")
    reminders = []
    if os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE) as f:
            try:
                reminders = json.load(f)
            except:
                pass
    reminders.append({
        "task": task,
        "time": when,
        "created": datetime.now().isoformat()
    })
    with open(REMINDER_FILE, "w") as f:
        json.dump(reminders, f, indent=2)
    speak(f"Reminder set: {task} at {when}")


def check_reminders_loop():
    while True:
        now = datetime.now()
        if os.path.exists(REMINDER_FILE):
            with open(REMINDER_FILE) as f:
                try:
                    reminders = json.load(f)
                except:
                    reminders = []
            due = []
            for r in reminders:
                r_time = dateparser.parse(r["time"])
                if r_time and r_time <= now:
                    due.append(r)
            if due:
                for r in due:
                    speak(f"Reminder: {r['task']}")
                # Remove triggered reminders
                reminders = [r for r in reminders if r not in due]
                with open(REMINDER_FILE, "w") as f:
                    json.dump(reminders, f, indent=2)
        time.sleep(10)


def detect_intent(text):
    text_lower = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        for k in keywords:
            if k in text_lower:
                return intent
    return "unknown"


def handle_reminder(text):
    doc = nlp(text)
    time_struct, parse_status = cal.parse(text)
    if parse_status == 0:
        speak("Sorry, I couldn't detect a time for the reminder.")
        return

    when = datetime(*time_struct[:6])
    if when < datetime.now():
        speak("The time you gave is in the past. Please try again.")
        return

    when_str = when.strftime("%Y-%m-%d %H:%M")
    task = text  # Could enhance to strip out the time phrase if needed
    save_reminder(task, when_str)


def handle_move_file(text):
    # naive example: "move file.txt to archive"
    tokens = text.split()
    try:
        src = next(tok for tok in tokens if os.path.isfile(tok))
        dest_index = tokens.index("to") + 1
        dest = tokens[dest_index]
        if not os.path.exists(dest):
            os.makedirs(dest)
        shutil.move(src, dest)
        speak(f"Moved {src} to {dest}")
    except Exception as e:
        speak(f"Could not complete file move: {str(e)}")


def handle_list_reminders():
    if not os.path.exists(REMINDER_FILE):
        speak("No reminders found.")
        return
    with open(REMINDER_FILE) as f:
        reminders = json.load(f)
    if not reminders:
        speak("No reminders scheduled.")
        return
    speak(f"You have {len(reminders)} reminders:")
    for r in reminders:
        print(f" • {r['task']} @ {r['time']}")
        speak(f"{r['task']} at {r['time']}")


def main():
    threading.Thread(target=check_reminders_loop, daemon=True).start()
    speak("Butler ready. How can I help?")
    while True:
        try:
            user_input = input("> ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            intent = detect_intent(user_input)
            if intent == "reminder":
                handle_reminder(user_input)
            elif intent == "move_file":
                handle_move_file(user_input)
            elif intent == "list_reminders":
                handle_list_reminders()
            else:
                speak("Sorry, I didn't understand. Could you clarify?")
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
