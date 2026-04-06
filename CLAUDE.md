# Marco AI — Project Overview & Developer Guidelines

## 🎯 What is it?

Marco AI is a personal, local-first AI assistant designed to centralize and simplify digital life. It is an **action agent** (not just a chatbot) capable of interacting with external APIs and local databases.

**CRITICAL CONSTRAINT:** This application must be highly optimized to run on low-power hardware, specifically a **Raspberry Pi 3 (1GB RAM)**. Memory efficiency and low idle CPU usage are top priorities.

## 🛠️ Tech Stack

| Layer                       | Technology                                                                                                                                                                       |
| :-------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LLM APIs**                | **Groq** (Llama 3.3), **OpenRouter** (Llama 3.3), **Gemini** (Gemini 2.0 Flash) — focusing on ultra-fast, millisecond tool-calling.                                              |
| **Backend**                 | **Python 3.11+ with FastAPI** — Async, lightweight, and native to AI tooling.                                                                                                    |
| **Frontend**                | Must be a clean, minimalist, friendly, and lightweight build that executes in the browser. I want a main visual dashboard, concrete views for each domain, and a chat interface. |
| **Database & Vector Store** | **SQLite + `sqlite-vec`** — Single-file database handling both relational tables (finances, habits) and vector embeddings (RAG) to avoid heavy database containers.              |
| **Auth**                    | **Google OAuth 2.0** — Handled cleanly via FastAPI middleware.                                                                                                                   |
| **Tunnel / Access**         | **Cloudflare Tunnel (`cloudflared`)** — For secure HTTPS access outside the home network.                                                                                        |
| **Deployment**              | **Docker / Docker Compose** — Maximize sharing of base images; keep container count to an absolute minimum (ideally 1-2 containers max).                                         |

## 🏗️ Architecture Design: Modular Monolith

Due to the Raspberry Pi 3's hardware limits, **do not use a microservices architecture.** Use a **Modular Monolith**. The application should be a single FastAPI server with strictly segregated domain folders (e.g., `/calendar`, `/finance`, `/habits`, `/agent`).

**Agent Pattern:** Avoid multi-agent/sub-agent swarms to prevent hitting free-tier LLM rate limits and high latency. Use a **Single-Agent Tool-Calling (ReAct)** pattern. The LLM will receive a user prompt, select the appropriate Python tool/function, execute it, and return the result as if it were a friendly human doing the task

## 🧠 Agent Capabilities & Tools

The agent must natively understand and execute functions across these domains:

- **📅 Calendar (Google API):** `list_events`, `create_event`, `modify_event`, `delete_event`.
- **📧 Email (Gmail API):** `read_emails`, `send_email`, `organize_labels`.
- **💰 Finance:** Log monthly and punctual expenses and income, andcalculate monthly balances. Store locally in SQLite.
- **🧘 Habits:** Track binary habits with custom frequencies (daily, specific weekdays). Automatically reset at midnight. Calculate streaks via SQLite queries.
- **🍱 Food & Shopping:** Manage a dynamic shopping list and a weekly meal plan matrix.
- **🎮 Leisure:** Log future events (concerts, dates, etc). Scrape/track game deals (Title, Store, Price, Discount) using lightweight web requests.
- **🧠 RAG Memory:** Semantic search over past conversations and user preferences using `sqlite-vec` for isolated, per-user memory retrieval.

## 🔒 Key Design Decisions

1. **Local-first Data:** All data (except LLM inference and Google API data) is persisted locally on the Pi's 512GB SD card.
2. **User Isolation:** All RAG and database tables must include a `user_id` to ensure strict separation of memory and data.
3. **Graceful Degradation:** If an LLM API fails or hits a rate limit, the system should gracefully fall back to the next API in the rotation.

## 🚀 Quick Start

```bash
git clone [https://github.com/marquito3012/marcoai.git](https://github.com/marquito3012/marcoai.git)
cd marcoai
cp .env.example .env        # Fill in API keys & Google OAuth credentials
docker compose up -d --build
# App is served at http://localhost:8000
```
