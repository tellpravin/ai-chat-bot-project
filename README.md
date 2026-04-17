# AI Chat Bot Project

A Python-based AI chatbot with Meta (Facebook) account integration, powered by Claude.

## Features

- AI-powered conversational responses via Claude (claude-sonnet-4-6)
- Meta (Facebook/Messenger) account connection
- Facebook Pages and Ad Account access
- Real-time Messenger chat processing
- GitHub integration with Claude Code

## Meta Account Connection

Connect your Meta account at:
**https://onboard.windsor.ai/app/facebook**

After connecting, copy your Meta access token and set it as an environment variable.

## Getting Started

Clone this repository and install dependencies:

```bash
git clone https://github.com/tellpravin/ai-chat-bot-project.git
cd ai-chat-bot-project
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file or export these variables:

```bash
export ANTHROPIC_API_KEY=your_anthropic_api_key
export META_ACCESS_TOKEN=your_meta_access_token
```

### Run the Bot

```bash
python chatbot.py
```

This will connect to your Meta account, display connected Pages and Ad Accounts,
and start the AI chatbot ready to handle Messenger events.

## Project Structure

| File | Description |
|------|-------------|
| `chatbot.py` | Main chatbot with Claude + Meta integration |
| `meta_connector.py` | Meta Graph API connector |
| `requirements.txt` | Python dependencies |

## License

MIT License
