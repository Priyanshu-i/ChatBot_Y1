import pyttsx3
import json
import time
import sys
import msvcrt
import webbrowser
import urllib.parse
import urllib.request
from threading import Thread, Event
from typing import Generator, List


class ChatBot:
    def __init__(self):
        self.chat_history: List[dict] = []
        self.api_url: str = "http://127.0.0.1:11434"
        self.ai_message = ""
        self.engine = pyttsx3.init()
        self.response_ready = Event()  # Event to signal when the response is ready
        self.is_generating_response = False  # Flag to track if a response is being generated
        self.current_response_thread = None  # Track the current response thread
        self.refresh_models()

    def fetch_chat_stream_result(self, message: str) -> Generator[str, None, None]:
        """
        Fetch the chat stream results from the API.
        Yields chunks of AI-generated responses.
        """
        try:
            request = urllib.request.Request(
                urllib.parse.urljoin(self.api_url, "/api/chat"),
                data=json.dumps(
                    {
                        "model": "deepseek-r1:1.5b",
                        "stream": True,
                        "messages": self.chat_history + [{"role": "user", "content": message}],  # Include chat history
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(request) as resp:
                for line in resp:
                    data = json.loads(line.decode("utf-8"))
                    if "message" in data:
                        time.sleep(0.01)
                        yield data["message"]["content"]
        except urllib.error.URLError as e:
            print(f"Error: Unable to reach the API. {e}")
            yield "I couldn't fetch a response due to a connection issue."
        except json.JSONDecodeError as e:
            print(f"Error: Failed to decode the response. {e}")
            yield "I couldn't process the response. Please try again later."
        except Exception as e:
            print(f"Unexpected error: {e}")
            yield "An unexpected error occurred while fetching the response."

    def generate_ai_response(self, message: str):
        """
        Generate the AI response in a separate thread and append it to chat history.
        """
        try:
            self.is_generating_response = True  # Set the flag to indicate response generation is in progress
            self.ai_message = ""
            self.response_ready.clear()  # Reset the event

            for response_chunk in self.fetch_chat_stream_result(message):  # Pass user message
                print(response_chunk, end="", flush=True)  # Print the response chunk
                self.ai_message += response_chunk

            if not self.ai_message.strip():
                self.ai_message = "I couldn't generate a meaningful response. Please try asking differently."

            self.chat_history.append({"role": "assistant", "content": self.ai_message})
            print("\nAI Response generation complete.\n")

            if ask == 'Y' or ask == 'y':
                # Signal that the response is ready
                self.response_ready.set()

                # Speak the response
                self.speak()

        except Exception as e:
            print(f"Error while generating AI response: {e}")
            self.ai_message = "An error occurred while generating the response."
            self.response_ready.set()  # Signal even if there's an error
        finally:
            self.is_generating_response = False  # Reset the flag after response generation is complete

    def speak(self):
        """
        Use pyttsx3 to speak the AI message.
        """
        try:
            self.response_ready.wait()  # Wait until the response is ready

            # Stop the engine if it's already running
            if self.engine._inLoop:
                self.engine.endLoop()

            # Reinitialize the engine
            self.engine = pyttsx3.init()

            # Configure the engine
            self.engine.setProperty("rate", 150)  # Set speaking rate
            voices = self.engine.getProperty("voices")
            self.engine.setProperty("voice", voices[1].id if len(voices) > 1 else voices[0].id)  # Use a female voice if available

            # Speak the message
            self.engine.say(self.ai_message)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Error during text-to-speech: {e}")
            print("I couldn't speak the response, but you can read it above.")

    def update_host(self):
        """
        Open the API URL in the browser to ensure the server is running.
        """
        print(f"Checking API availability at {self.api_url}...")
        try:
            with urllib.request.urlopen(self.api_url) as resp:
                if resp.status == 200:
                    print("API is running.")
        except urllib.error.URLError:
            print("API is not reachable. Attempting to open the server URL in the browser...")
            webbrowser.open(self.api_url)

    def update_model_select(self):
        """
        Mock method for model selection. This is placeholder functionality.
        """
        print("Refreshing model list (placeholder).")

    def refresh_models(self):
        """
        Refresh models and ensure the server is accessible.
        """
        self.update_host()
        Thread(target=self.update_model_select, daemon=True).start()

    def stop(self):
        if ask == 'Y' or ask == 'y':
            self.engine.stop()

    @staticmethod
    def get_multiline_input_with_quotes(prompt: str = "Enter Prompt (use ''' or \"\"\" for multiline input): ", placeholder="\nPaste or type here..."):
        """
        Get multiline input from the user using triple quotes (''' or \"\"\") as delimiters.
        Supports pasting multi-line input and removes the placeholder upon typing.
        """
        sys.stdout.flush()
        sys.stdout.write(f"\033[90m{placeholder}\033[0m\n")  # Light gray placeholder
        sys.stdout.flush()
        lines = []
        first_line = ""

        # Read first line
        while True:
            key = msvcrt.getch().decode("utf-8", errors="ignore")  # Ignore invalid UTF-8 characters
            if key == "\r":  # Enter key
                print()
                break
            elif key == "\b":  # Backspace key
                if first_line:
                    first_line = first_line[:-1]
                    sys.stdout.write("\b \b")  # Remove last character
                    sys.stdout.flush()
            elif key in ("\x00", "\xe0"):  # Ignore special keys (arrows, etc.)
                msvcrt.getch()  # Skip the next character (part of the special key sequence)
            else:
                if not first_line:
                    # Clear placeholder on first key press
                    sys.stdout.write("\r" + " " * len(placeholder) + "\r")
                    sys.stdout.flush()
                sys.stdout.write(key)
                sys.stdout.flush()
                first_line += key

        first_line = first_line.strip()

        # Check if the input starts with triple quotes
        if first_line.startswith("'''") or first_line.startswith('"""'):
            delimiter = first_line[:3]  # Get the delimiter (''' or """)
            lines.append(first_line[3:])  # Remove the starting delimiter

            # Read multiline input
            while True:
                try:
                    line = input()
                    if line.strip().endswith(delimiter):  # Check for ending delimiter
                        lines.append(line[:-3])  # Remove the ending delimiter
                        break
                    lines.append(line)
                except KeyboardInterrupt:  # Handle Ctrl+C
                    break
            return "\n".join(lines)  # Combine lines into a single string
        else:
            return first_line  # Single-line input


def greeting():
    engine = pyttsx3.init()
    engine.setProperty("rate", 150)
    voices = engine.getProperty("voices")
    engine.setProperty("voice", voices[1].id if len(voices) > 1 else voices[0].id)
    greet = "Hello Sir, How can i help you Today!"
    engine.say(greet)
    engine.runAndWait()


# Main logic
if __name__ == "__main__":
    ask = input("Speaking allowed (Y/N) : ")
    if ask == 'Y' or ask == 'y':
        time.sleep(1)
        greeting()

    chatbot = ChatBot()

    try:
        # Initialize message
        message = ""

        # Start the conversation loop
        while message != "/bye":
            # Get user input
            message = chatbot.get_multiline_input_with_quotes().strip()

            # Check for termination condition
            if message == "/bye":
                print("Goodbye! Ending the conversation.")
                chatbot.stop()
                break

            if message == "/stop":
                chatbot.stop()
                ask = input("Speaking allowed (Y/N) : ")

            if message == "/":
                print("\n/bye : for ending the conversation.")
                print("/stop : To stop voice, Change mode.")
                print("''' or \"\"\" for multiline input\n")

            # Validate user input
            if not message:
                print("Prompt cannot be empty. Please enter a valid input.")
            elif message[0] != '/':
                # Append user message to chat history
                chatbot.chat_history.append({"role": "user", "content": message})

                # If a response is already being generated, stop it
                if chatbot.is_generating_response and chatbot.current_response_thread:
                    chatbot.current_response_thread.join(timeout=0.1)  # Wait for the thread to finish

                # Start AI response generation in a thread
                chatbot.current_response_thread = Thread(
                    target=chatbot.generate_ai_response,
                    args=(message,),  # Pass user message
                    daemon=True,
                )
                chatbot.current_response_thread.start()

                print("\nGenerating AI response... Please wait.")

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"Unexpected error in main logic: {e}")

    # Add this line to keep the window open
    input("\nPress Enter to exit")