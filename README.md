# 📧 AI-Powered Gmail Intelligence System

> **Intelligent email triage powered by GPT-4o-mini** — Automatically fetches unread Gmail messages, classifies their importance, extracts actionable insights, and delivers concise summaries to Telegram in real-time.

---

## 📋 Table of Contents

- [About](#about)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Disclaimer](#disclaimer)


---

## 📖 About

Managing a busy inbox is time-consuming. This system acts as your **AI email assistant** — it continuously monitors your Gmail inbox, uses GPT-4o-mini to evaluate each email's importance, extracts key information (deadlines, action items, sender context), filters out junk and promotions, and sends you a clean, prioritized summary via Telegram.

**Key Problem Solved:** Eliminate inbox noise and never miss an important email again.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Secure OAuth 2.0** | Gmail authentication with automatic token refresh and caching |
| 🤖 **LLM-Powered Analysis** | GPT-4o-mini classifies importance, extracts summaries, and detects deadlines |
| 🗑️ **Junk Filtering** | AI-driven filtering of promotions, newsletters, and spam |
| 📊 **Structured Output** | Pydantic-validated JSON extraction for reliable data handling |
| 💬 **Telegram Alerts** | Beautifully formatted Markdown notifications delivered instantly |
| 🗄️ **PostgreSQL Persistence** | Deduplication via message ID tracking — no email is processed twice |
| 🔄 **Continuous Polling** | Configurable polling loop with graceful error recovery |
| 📝 **Colored Logging** | Rich, color-coded console logs for easy debugging |

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Gmail API   │────▶│  Orchestrator │────▶│  LangChain AI    │
│  (OAuth 2.0) │     │  (main.py)    │     │  (GPT-4o-mini)   │
└─────────────┘     └──────┬───────┘     └────────┬────────┘
                           │                       │
                           ▼                       ▼
                    ┌──────────────┐     ┌─────────────────┐
                    │  PostgreSQL   │     │  Telegram Bot    │
                    │  (Dedup/Log)  │     │  (Notifications) │
                    └──────────────┘     └─────────────────┘
```

**Flow:**
1. **Fetch** — Poll Gmail for unread messages via the Gmail API.
2. **Deduplicate** — Check each `message_id` against PostgreSQL to skip already-processed emails.
3. **Analyze** — Send email content to GPT-4o-mini for importance classification and data extraction.
4. **Notify** — Format the AI's structured output and send it to Telegram.
5. **Persist** — Log the processed email in the database and mark it as read in Gmail.
6. **Repeat** — Sleep for the configured interval and poll again.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.10+ |
| **LLM Framework** | LangChain (LCEL) |
| **AI Model** | OpenAI GPT-4o-mini |
| **Email** | Gmail API (OAuth 2.0) |
| **Database** | PostgreSQL |
| **ORM** | SQLAlchemy |
| **Notifications** | Telegram Bot API |
| **Config** | python-dotenv |

---

## 📁 Project Structure

```
email-agent/
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── main.py               # Application entry point & orchestrator
└── src/
    ├── __init__.py
    ├── config.py          # Centralized configuration loader
    ├── database/
    │   ├── __init__.py
    │   ├── models.py      # SQLAlchemy ORM models
    │   └── handler.py     # Database operations (check/log)
    ├── gmail/
    │   ├── __init__.py
    │   ├── auth.py        # OAuth 2.0 authentication flow
    │   └── service.py     # Fetch & manage emails
    ├── ai/
    │   ├── __init__.py
    │   ├── schemas.py     # Pydantic output schemas
    │   └── analyzer.py    # LangChain email analysis chain
    └── telegram/
        ├── __init__.py
        ├── formatter.py   # Message formatting
        └── notifier.py    # Telegram Bot API integration
```

---

## 🚀 Setup & Installation

### Prerequisites

- **Python 3.10+**
- **PostgreSQL** installed and running
- **Gmail API credentials** from [Google Cloud Console](https://console.cloud.google.com/)
- **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/email-agent.git
cd email-agent
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
# Open .env and fill in all required values
```

### 5. Set Up Gmail API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select existing).
3. Enable the **Gmail API**.
4. Create **OAuth 2.0 Client ID** credentials (Desktop App).
5. Download the JSON file and save it as `credentials.json` in the project root.

### 6. Set Up PostgreSQL Database

```bash
# Connect to PostgreSQL and create the database
psql -U postgres
CREATE DATABASE email_agent;
\q
```

> The application will automatically create the required tables on first run.

### 7. Run the Application

```bash
python main.py
```

On first run, a browser window will open for Gmail OAuth authorization. After granting access, a `token.json` file will be cached for subsequent runs.

---

## ⚙️ Configuration

All configuration is managed via the `.env` file. See [`.env.example`](.env.example) for the full list of variables.

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key | — |
| `OPENAI_MODEL` | Model to use for analysis | `gpt-4o-mini` |
| `GMAIL_MAX_RESULTS` | Emails to fetch per cycle | `5` |
| `POLLING_INTERVAL` | Seconds between polling cycles | `60` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

## ⚠️ Disclaimer

- This project is for **educational and personal productivity purposes only**.
- The Gmail API usage must comply with [Google's API Terms of Service](https://developers.google.com/terms).
- **Never commit** your `.env`, `credentials.json`, or `token.json` files to version control.
- AI-generated summaries may not be 100% accurate — always verify critical information.
- The authors are not responsible for missed emails, incorrect classifications, or any consequences arising from the use of this software.



---

<p align="center">
  Built with ❤️ using LangChain, OpenAI, and the Gmail API
</p>
