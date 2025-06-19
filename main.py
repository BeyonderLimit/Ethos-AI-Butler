import argparse
import json
import re
import subprocess
import sys
import threading
import time
import requests
from datetime import datetime
from dateutil import parser as dtparser
import logging
from rich.logging import RichHandler
from rich.console import Console

from memory.mnemosyne import MemoryManager
from memory.reminders import ReminderManager
from nlu import extract_intent_entities

# === Logging & Console ===
console = Console()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console)]
)
log = logging.getLogger("ethos")

# === Managers ===
memory = MemoryManager("memory/memory_store.json")
reminder_manager = ReminderManager()


def speak(text):
    subprocess.run(["python3", "scripts/say.py", text], stderr=subprocess.DEVNULL)


def ask_ollama(prompt, max_tokens=200, temperature=1.0, stream=True) -> str:
    try:
        response = ""
        first_token = True
        token_count = 0

        url = "http://localhost:11434/api/generate"
        data = {
            "model": "qwen2.5:1.5b-instruct",
            "prompt": prompt.strip(),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        with requests.post(url, json=data, stream=stream) as r:
            for line in r.iter_lines():
                if line:
                    json_response = json.loads(line)
                    token = json_response.get("response", "")
                    if token:
                        if first_token:
                            sys.stdout.write("\r" + " " * 50 + "\r")
                            first_token = False
                        print(token, end="", flush=True)
                        response += token
                        token_count += 1
                        if token_count >= max_tokens:
                            break
                    elif first_token:
                        sys.stdout.write("\r" + " " * 50 + "\r")
                        sys.stdout.write("Thinking... " + "|/-\\"[int(time.time() * 4) % 4])
                        sys.stdout.flush()
        return response or "[Sorry sir, I don't have a response]"
    except Exception:
        log.exception("Error in ask_ollama()")
        return "[ERROR] LLM failed."


def trigger_action(task, time_str):
    log.info(f"🔔 Reminder triggered: {task} @ {time_str}")
    speak(f"Reminder: {task}")


def reminder_thread():
    while True:
        reminder_manager.check_and_trigger(trigger_action)
        time.sleep(10)

def add_reminder(self, task, when, tag=None):
    try:
        if isinstance(when, str):
            when = dtparser.parse(when)
        # validate datetime
        if not when:
            return False

        self.reminders.append({
            "task": task,
            "time": when.isoformat(),
            "tag": tag,
        })
        self.save()
        return True
    except Exception as e:
        print(f"[ReminderManager] Error adding reminder: {e}")
        return False

def extract_tag(text: str):
    match = re.search(r"\[tag:\s*(.*?)\s*\]", text, re.IGNORECASE)
    if match:
        tag = match.group(1).strip()
        cleaned_text = re.sub(r"\[tag:.*?\]", "", text).strip()
        return cleaned_text, tag
    return text, None


# === Dispatcher Functions ===

def handle_reminder(nlu_result, args):
    task, tag = extract_tag(nlu_result["task"])
    log.debug(f"Attempting to schedule: {task} @ {nlu_result['time']}")

    parsed_dt = parse_date(nlu_result["time"], settings={'PREFER_DATES_FROM': 'future'}) if nlu_result["time"] else None

    if not parsed_dt:
        log.info("[🤖 Fallback] Asking LLM to extract time...")
        prompt = f"Extract just the reminder time (like '6pm', 'tomorrow at noon') from: '{nlu_result['task']}'"
        llm_response = ask_ollama(prompt, max_tokens=50).strip()
        log.debug(f"[LLM fallback] Raw: {llm_response}")

        # Extract probable time string using regex or strip quotes/markdown
        match = re.search(r'([0-9]{1,2}\s*(am|pm)|tonight|this evening|tomorrow|next week|in \d+ (minutes|hours|days))', llm_response, re.IGNORECASE)
        if match:
            extracted_time = match.group(0)
            log.debug(f"[LLM fallback] Extracted time string: {extracted_time}")
            parsed_dt = parse_date(extracted_time, settings={'PREFER_DATES_FROM': 'future'})
        else:
            log.warning("❌ Could not extract a valid time from LLM fallback response.")

    if parsed_dt:
        success = reminder_manager.add_reminder(task=task, when=parsed_dt.isoformat(), tag=tag)
        msg = f"✅ Reminder saved: '{task}' at '{parsed_dt.strftime('%A %I:%M %p')}'" if success else "❌ Failed to schedule reminder."
    else:
        msg = "❌ Still could not extract a valid time."

    log.info(msg)
    if not args.silent:
        speak(msg)


def handle_query_reminders(nlu_result, args=None):
    handle_list_reminders(args=args) 


def handle_list_reminders(*_, args=None):
    reminders = reminder_manager.list_reminders()
    if not reminders:
        console.print("[yellow]📭 No upcoming reminders.[/]")
        if not args.silent:
            speak("You have no reminders.")
    else:
        console.print("[bold cyan]📅 Your Reminders:[/]")
        for i, r in enumerate(reminders, 1):
            tag = f"[{r['tag']}]" if r.get("tag") else ""
            console.print(f"  {i}. {r['task']} @ {r['time']} {tag}")
        if not args.silent:
            speak(f"You have {len(reminders)} reminders.")


def handle_delete_reminder(user_input, *_, args=None):
    match = re.search(r"delete reminder (\d+)", user_input.lower())
    if match:
        index = int(match.group(1)) - 1
        success = reminder_manager.delete_reminder(index)
        msg = f"🗑️ Reminder {index + 1} deleted." if success else "❌ Invalid reminder number."
    else:
        msg = "❌ Usage: delete reminder <number>"

    log.info(msg)
    if not args.silent:
        speak(msg)


def handle_agenda(*_, args=None):
    subprocess.Popen(["python3", "memory/agenda.py"], stdout=subprocess.DEVNULL)
    if not args.silent:
        speak("Here is your agenda.")


def handle_weather(*_, args=None):
    subprocess.run(["python3", "scripts/weather.py"])
    if not args.silent:
        speak("Here is today’s weather forecast.")


def handle_help(*_, args=None):
    help_text = (
        "[bold green]💡 You can say things like:[/]\n"
        "• Remind me to call Sam at 6pm\n"
        "• What's my agenda today?\n"
        "• What's the weather like?\n"
        "• List reminders\n"
        "• Delete reminder 1\n"
        "• Exit"
    )
    console.print(help_text)
    if not args.silent:
        speak("Here’s what I can help you with.")


def handle_exit(*_, args=None):
    console.print("[bold red]Goodbye![/]")
    if not args.silent:
        speak("Goodbye.")
    sys.exit(0)


# === Dispatcher Routing ===

dispatch = {
    "reminder": handle_reminder,
    "list_reminders": handle_list_reminders,
    "query_reminders": handle_query_reminders,
    "delete_reminder": handle_delete_reminder,
    "agenda": handle_agenda,
    "weather": handle_weather,
    "help": handle_help,
    "exit": handle_exit,
}


# === MAIN LOOP ===

def main():
    parser = argparse.ArgumentParser(description="Ethos Butler")
    parser.add_argument("--silent", action="store_true", help="Disable TTS")
    parser.add_argument("--memory-off", action="store_true", help="Disable memory logging")
    parser.add_argument("--voice", action="store_true", help="Enable voice input")
    parser.add_argument("--nlu-off", action="store_true", help="Disable natural language processing")
    args = parser.parse_args()

    console.print("[bold magenta]🎙️ Ethos is listening...[/]")

    if not args.nlu_off:
        threading.Thread(target=reminder_thread, daemon=True).start()

    while True:
        try:
            if args.voice:
                user_input = subprocess.check_output(["python3", "scripts/listen.py"]).decode().strip()
                if "press ctrl+c to stop" in user_input.lower():
                    continue
                console.print(f"You said: [cyan]{user_input}[/]")
            else:
                user_input = input("\n> ").strip()

            if not user_input:
                continue

            if not args.nlu_off:
                nlu_result = extract_intent_entities(user_input)
                log.debug(f"NLU: {nlu_result}")
                intent = nlu_result.get("intent")
                if intent in dispatch:
                    dispatch[intent](nlu_result, args=args)
                    continue

            # Manual fallback for explicit commands
            if user_input.lower().startswith("list reminders"):
                handle_list_reminders(args=args)
                continue
            elif user_input.lower().startswith("delete reminder"):
                handle_delete_reminder(user_input, args=args)
                continue
            elif user_input.lower() in ("exit", "quit"):
                handle_exit(args=args)
                continue

            # Fallback to LLM
            console.print("\n[bold yellow]Ethos:[/]")
            print("\nEthos: ", end="", flush=True)
            response = ask_ollama(user_input)

            print()
            if not args.memory_off:
                memory.save_interaction(
                    content=f"USER: {user_input}\nETHOS: {response}",
                    metadata={"timestamp": datetime.now().isoformat()},
                )

            if not args.silent:
                speak(response)

        except KeyboardInterrupt:
            console.print("\n[red]❌ Interrupted. Exiting.[/]")
            break
        except Exception:
            log.exception("Unhandled error in main loop.")


if __name__ == "__main__":
    main()
