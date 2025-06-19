# nlu.py

import re
import spacy
import json
import requests
import dateparser
from dateparser import parse as parse_date

nlp = spacy.load("en_core_web_sm")

INTENT_PATTERNS = {
    "reminder": [r"\bremind me\b", r"\bset a reminder\b", r"\balert me\b"],
    "schedule": [r"\bschedule\b", r"\bbook (a )?(meeting|appointment)\b", r"\badd (an )?event\b"],
    "list_reminders": [r"\blist (my )?reminders\b", r"\bwhat (are|do i have) (any )?reminders\b"],
    "delete_reminder": [r"\bdelete (a )?reminder\b", r"\bremove reminder\b"],
    "agenda": [r"\bwhat('?s| is)? (my )?(agenda|schedule)\b", r"\bmy day\b"],
    "weather": [r"\bweather\b", r"\bforecast\b", r"\btemperature\b"],
}

def detect_intent_local(text: str) -> str:
    text_lower = text.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return intent
    return "unknown"

def extract_time(text: str) -> str:
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ["DATE", "TIME"]:
            return ent.text
    return ""

def normalize_time(text: str) -> str:
    parsed = parse_date(text)
    if parsed:
        return parsed.isoformat()
    return ""

def remove_time_from_task(task: str, time_str: str) -> str:
    if time_str and time_str in task:
        return task.replace(time_str, "").strip(",. ")
    return task

def ask_llm_fallback(text: str, model="qwen2.5:1.5b-instruct"):
    try:
        url = "http://localhost:11434/api/generate"
        prompt = f"""You are an NLU engine. Extract the user's intent and time if mentioned.

Input: "{text}"

Respond in JSON format like:
{{
  "intent": "reminder" | "agenda" | "weather" | "unknown",
  "task": "...",
  "time": "..."  // ISO8601 if possible
}}"""

        response = requests.post(
            url,
            json={"model": model, "prompt": prompt, "max_tokens": 200, "temperature": 0.2},
            timeout=10,
        )
        for line in response.iter_lines():
            if line:
                json_line = json.loads(line)
                if "response" in json_line:
                    try:
                        return json.loads(json_line["response"])
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"[LLM Fallback Error] {e}")
    return {
        "intent": "unknown",
        "task": text,
        "time": ""
    }

def extract_intent_entities(text: str) -> dict:
    doc = nlp(text.lower())
    intent = None

    if "remind me" in text:
        intent = "reminder"
    elif any(phrase in text for phrase in ["do i have reminders", "any reminders", "upcoming reminders"]):
        intent = "query_reminders"    
    elif "agenda" in text or "schedule" in text:
        intent = "agenda"
    elif "do i have" in text and "reminder" in text:
        intent = "query_reminders"
    elif text.strip().lower() in ["hi", "hello", "good morning"]:
        intent = "greeting"

    parsed_time = dateparser.parse(text, settings={'PREFER_DATES_FROM': 'future'})
    time_phrase = ""
    if parsed_time:
        time_phrase = parsed_time.isoformat()

    return {
        "intent": intent or "unknown",
        "task": text,
        "time": time_phrase
    }
