"""
AI Chat Bot using Claude API (claude-opus-4-6)
A conversational chatbot with multi-turn conversation support.
"""

import os
from dotenv import load_dotenv
import anthropic

load_dotenv()


def create_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return anthropic.Anthropic(api_key=api_key)


def chat(client: anthropic.Anthropic, messages: list, user_input: str) -> str:
    """Send a message and get a streaming response from Claude."""
    messages.append({"role": "user", "content": user_input})

    full_response = ""
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=1024,
        system="You are a helpful AI assistant. Be concise, friendly, and informative.",
        messages=messages,
        thinking={"type": "adaptive"},
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_response += text

    print()  # newline after streaming
    messages.append({"role": "assistant", "content": full_response})
    return full_response


def main():
    print("AI Chat Bot (powered by Claude)")
    print("Type 'quit' or 'exit' to stop, 'clear' to reset conversation")
    print("-" * 50)

    client = create_client()
    messages = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break
        if user_input.lower() == "clear":
            messages = []
            print("Conversation cleared.")
            continue

        print("\nAssistant: ", end="", flush=True)
        try:
            chat(client, messages, user_input)
        except anthropic.AuthenticationError:
            print("Error: Invalid API key. Check your ANTHROPIC_API_KEY.")
            break
        except anthropic.RateLimitError:
            print("Error: Rate limit reached. Please wait and try again.")
        except anthropic.APIError as e:
            print(f"API error: {e}")


if __name__ == "__main__":
    main()
