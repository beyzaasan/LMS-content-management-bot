import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables (e.g., API keys)
load_dotenv()

# Configure the Gemini API using the provided key
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))


class Agent:
    """
    Base class for chat-based AI agents.
    Provides common functionality for interacting with LLMs (Gemini) via a chat interface.
    """

    def __init__(self, role_instruction: str, model_name: str = "gemini-1.5-flash",
                 generation_config: dict = {"temperature": 0.2, "top_p": 0.60, "top_k": 1, "response_mime_type": "text/plain"}):
        """
        Initialize the agent with its role and model configuration.
        """
        self.role_instruction = role_instruction
        self.model_name = model_name
        self.generation_config = generation_config

        # Initialize the Gemini chat model and chat session
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.role_instruction,
            generation_config=self.generation_config
        )
        self.chat_session = self.model.start_chat(history=[])  # Starts a new chat session
        self.chat_history = [] # To maintain conversation context locally

        # Track token usage for analysis
        self.token_usage = {
            "prompt_tokens": 0,
            "response_tokens": 0,
            "total_tokens": 0
        }


    def chat(self, user_input: str) -> str:
        """
        Engage in a chat with the model based on user input.
        """
        try:
            # Append user input to chat history
            self.chat_history.append({"role": "user", "content": user_input})

            # Send user input to the chat session and get response
            response = self.chat_session.send_message(user_input)

            # Append model's response to chat history
            self.chat_history.append({"role": "assistant", "content": response.text})

            # Update token statistics
            usage = response.usage_metadata
            self.token_usage["prompt_tokens"] += usage.prompt_token_count
            self.token_usage["response_tokens"] += usage.candidates_token_count
            self.token_usage["total_tokens"] += usage.total_token_count

            # Return the model's response
            return response.text

        except Exception as e:
            raise RuntimeError(f"Error during chat interaction: {str(e)}")

    def get_chat_history(self) -> list:
        """
        Retrieve the chat history for the current session.
        """
        return self.chat_history

    def clear_chat_history(self):
        """
        Clear the chat history for the current session.
        """
        self.chat_history = []
        self.chat_session = self.model.start_chat(history=[])  # Reset the chat session

    def get_token_statistics(self) -> dict:
        """
        Retrieve the token usage statistics for the agent.
        """
        return self.token_usage

    def reset_token_statistics(self):
        """
        Reset the token usage statistics to zero.
        """
        self.token_usage = {
            "prompt_tokens": 0,
            "response_tokens": 0,
            "total_tokens": 0
        }

