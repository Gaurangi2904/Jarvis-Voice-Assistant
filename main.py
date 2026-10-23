
import os
import subprocess
import urllib.parse
import urllib.request
import json
import webbrowser
import winreg
from datetime import datetime

# Keep this DLL directory available for your microphone on Windows.
_DLL_DIRECTORY = os.add_dll_directory(
    r"C:\vcpkg\installed\x64-windows\bin"
)

import speech_recognition as sr
import pyttsx3


# ---------- VOICE ----------

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.9

engine = pyttsx3.init()
engine.setProperty("rate", 170)


def speak(text):
    print(f"\nJARVIS: {text}\n")
    engine.say(text)
    engine.runAndWait()


# ---------- FIND CHROME ----------

def find_chrome():
    paths = [
        os.path.expandvars(
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
        ),
        os.path.expandvars(
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
        ),
    ]

    # Check Windows registry for Chrome's registered installation path.
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    paths.insert(0, winreg.QueryValue(key, None))
            except OSError:
                pass
    except Exception:
        pass

    for path in paths:
        if path and os.path.isfile(path):
            return path

    return None


CHROME = find_chrome()


def open_url(url):
    try:
        if CHROME:
            subprocess.Popen([CHROME, url], close_fds=True)
        else:
            speak("Chrome was not found. I'll try your default browser.")
            webbrowser.open_new_tab(url)
    except Exception as error:
        print("Browser error:", error)
        speak("Sorry, I couldn't open that website.")


# ---------- MICROPHONE ----------

def listen(timeout=None, phrase_limit=8):
    try:
        with sr.Microphone() as source:
            print("Listening...")
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_limit
            )

        words = recognizer.recognize_google(
            audio, language="en-IN"
        ).lower().strip()

        print("YOU SAID:", words)
        return words

    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        print("Speech was not clear.")
        return ""
    except sr.RequestError as error:
        print("Recognition error:", error)
        speak("Please check your internet connection.")
        return ""
    except Exception as error:
        print("Microphone error:", error)
        return ""


# ---------- YOUTUBE ----------

def play_youtube(query):
    if not query:
        speak("Which song or video should I play?")
        query = listen(timeout=8)

    if not query:
        speak("I didn't catch the name.")
        return

    speak("Searching YouTube for " + query)

    url = (
        "https://www.youtube.com/results?search_query="
        + urllib.parse.quote_plus(query)
    )
    open_url(url)
    speak("Choose the video to start playback.")


# ---------- ONLINE ANSWERS ----------

def answer_question(question):
    url = (
        "https://en.wikipedia.org/w/api.php?action=query"
        "&list=search&format=json&srlimit=1&srsearch="
        + urllib.parse.quote_plus(question)
    )

    headers = {"User-Agent": "JarvisAssistant/1.0"}

    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = data.get("query", {}).get("search", [])
        if not results:
            return None

        title = results[0]["title"]
        summary_url = (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + urllib.parse.quote(title.replace(" ", "_"), safe="")
        )

        request = urllib.request.Request(
            summary_url, headers=headers
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))

        return data.get("extract", "").strip()[:900] or None

    except Exception as error:
        print("Question lookup error:", error)
        return None


# ---------- COMMANDS ----------

def process_command(text):
    command = text.lower().strip(" .,!?")

    # Remove a wake word if one was recognized.
    for wake in ("hey jarvis", "okay jarvis", "ok jarvis", "jarvis", "jar"):
        if command == wake:
            speak("Yes? What can I do for you?")
            return True
        if command.startswith(wake + " "):
            command = command[len(wake):].strip(" .,!?")
            break

    if not command:
        speak("Yes? I'm listening.")
        return True

    # Stop
    if any(x in command for x in [
        "stop jarvis", "exit jarvis", "quit jarvis",
        "goodbye jarvis"
    ]):
        speak("Goodbye!")
        return False

    # Conversation
    if "how are you" in command:
        speak("I'm doing great! How are you?")
        return True

    if command in ("hello", "hi", "hey"):
        speak("Hello! How can I help you?")
        return True

    if "who are you" in command:
        speak("I'm Jarvis, your personal voice assistant.")
        return True

    if "thank you" in command or "thanks" in command:
        speak("You're welcome!")
        return True

    # Websites
    websites = {
        "youtube": "https://www.youtube.com/",
        "linkedin": "https://www.linkedin.com/",
        "github": "https://github.com/",
        "google": "https://www.google.com/",
        "chatgpt": "https://chatgpt.com/",
    }

    for name, url in websites.items():
        if command in (f"open {name}", f"go to {name}"):
            speak("Opening " + name)
            open_url(url)
            return True

    # Music and videos
    if command.startswith("play "):
        query = command[5:].strip()
        for prefix in ("music ", "video ", "a song "):
            if query.startswith(prefix):
                query = query[len(prefix):].strip()
        play_youtube(query)
        return True

    if command in ("play music", "play a song", "play a video"):
        play_youtube("")
        return True

    # Time and date
    if "time" in command:
        speak("The time is " + datetime.now().strftime("%I:%M %p"))
        return True

    if "date" in command:
        speak("Today is " + datetime.now().strftime("%d %B %Y"))
        return True

    # General questions
    speak("Let me find an answer.")
    answer = answer_question(command)

    if answer:
        speak(answer)
    else:
        speak("I couldn't find an answer. I'll search the web.")
        open_url(
            "https://www.google.com/search?q="
            + urllib.parse.quote_plus(command)
        )

    return True


# ---------- MAIN LOOP ----------

def main():
    speak("Jarvis is ready. Tell me what you need.")

    while True:
        command = listen(timeout=None, phrase_limit=8)

        if not command:
            continue

        # Execute recognized commands even if "Jarvis" was missed.
        if not process_command(command):
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nJarvis stopped.")
    finally:
        engine.stop()
