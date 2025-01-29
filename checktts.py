import pyttsx3
import json
import time
import webbrowser
import urllib.parse
import urllib.request
from threading import Thread
from typing import Generator, List


class ChatBot:
    def __init__(self):
        self.chat_history: List[dict] = []
        self.api_url: str = "http://127.0.0.1:11434"
        self.ai_message = ""
        self.engine = pyttsx3.init()
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
            self.ai_message = ""
            for response_chunk in self.fetch_chat_stream_result(message):  # Pass user message
                print(response_chunk, end="", flush=True)  # Print the response chunk
                self.ai_message += response_chunk

            if not self.ai_message.strip():
                self.ai_message = "I couldn't generate a meaningful response. Please try asking differently."

            self.chat_history.append({"role": "assistant", "content": self.ai_message})
            print("\nAI Response generation complete.")

            # Speak the response
            self.speak()
        except Exception as e:
            print(f"Error while generating AI response: {e}")
            self.ai_message = "An error occurred while generating the response."

    def speak(self):
        """
        Use pyttsx3 to speak the AI message.
        """
        try:
            self.engine.setProperty("rate", 150)  # Set speaking rate
            voices = self.engine.getProperty("voices")
            self.engine.setProperty("voice", voices[1].id if len(voices) > 1 else voices[0].id)  # Use a female voice if available
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


# Main logic
if __name__ == "__main__":
    chatbot = ChatBot()

    try:
        # Initialize message
        message = ""

        # Start the conversation loop
        while message != "/bye":
            # Get user input
            message = input("\nEnter Prompt: ").strip()

            # Check for termination condition
            if message == "/bye":
                print("Goodbye! Ending the conversation.")
                break

            # Validate user input
            if not message:
                print("Prompt cannot be empty. Please enter a valid input.")
            else:
                # Append user message to chat history
                chatbot.chat_history.append({"role": "user", "content": message})

                # Start AI response generation in a thread
                response_thread = Thread(
                    target=chatbot.generate_ai_response,
                    args=(message,),  # Pass user message
                    daemon=True,
                )
                response_thread.start()

                print("\nGenerating AI response... Please wait.")

                # Do not wait for the thread to finish, continue to prompt for new input

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"Unexpected error in main logic: {e}")