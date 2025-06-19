# memory/reminders.py

import os
import json
import threading
import time
import re
from datetime import datetime
import dateparser

REMINDER_FILE = os.path.join(os.path.dirname(__file__), "reminders.json")

class ReminderManager:
    def __init__(self):
        os.makedirs(os.path.dirname(REMINDER_FILE), exist_ok=True)
        self.reminders = self._load()
        self.lock = threading.Lock()

    def _load(self):
        if os.path.exists(REMINDER_FILE):
            try:
                with open(REMINDER_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    def _save(self):
        with open(REMINDER_FILE, "w") as f:
            json.dump(self.reminders, f, indent=2)

    def add_reminder(self, task: str, when: str, tag: str = None):
        parsed_time = dateparser.parse(when)
        if not parsed_time:
            return False

        entry = {
            "task": task.strip(),
            "time": parsed_time.isoformat(),
            "triggered": False,
            "tag": tag or "general"
        }
        with self.lock:
            self.reminders.append(entry)
            self._save()
        return True

    def check_and_trigger(self, callback):
        now = datetime.now()  # Use local time
        with self.lock:
            for reminder in self.reminders:
                if not reminder["triggered"]:
                    remind_time = datetime.fromisoformat(reminder["time"])
                    if remind_time <= now:
                        callback(reminder["task"], reminder["time"])
                        reminder["triggered"] = True
            self._save()

    def list_reminders(self, include_triggered=False):
        with self.lock:
            return [r for r in self.reminders if include_triggered or not r["triggered"]]
