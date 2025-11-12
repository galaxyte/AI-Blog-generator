# AI Blog Generator

AI Blog Generator is an end-to-end FastAPI web application that produces SEO-ready blog articles from simple prompts. Supply up to ten topics, select an optional tone, and the platform will craft long-form content using OpenAI, persist each article to SQLite, and present them within an elegant Tailwind-powered dashboard.

🔗 **Live Demo:** [https://ai-blog-generator-p06n.onrender.com/](https://ai-blog-generator-p06n.onrender.com/)

## Features

- Bulk-generate 600–800 word blog posts from up to ten titles in a single batch.
- Choose the voice of your article (Neutral, Formal, Conversational, Technical).
- Auto-save every blog to SQLite with regeneration and download options.
- Modern UI with live previews, modal reading experience, and CTA shortcuts.
- Graceful error handling for missing API keys or OpenAI request issues.

## Tech Stack

- **Backend:** FastAPI (async)
- **Frontend:** Jinja2 + Tailwind (via CDN)
- **Database:** SQLite (`sqlalchemy` + `aiosqlite`)
- **AI Provider:** OpenAI Responses API (`gpt-4o-mini` by default)
- **Config:** `python-dotenv`
- **Runtime:** Python 3.11+, `uvicorn`

## Project Structure

```
ai_blog_generator/
├── app/
│   ├── main.py
│   ├── models/
│   │   └── blog_model.py
│   ├── routes/
│   │   └── blog_routes.py
│   ├── services/
│   │   └── ai_service.py
│   ├── static/
│   │   └── style.css
│   ├── templates/
│   │   ├── blogs.html
│   │   └── index.html
│   └── utils.py
├── env.example
├── requirements.txt
└── README.md
```

> ℹ️ `.env` files are ignored in this environment. Copy `env.example` → `.env` and update the secrets before running the app.

## Getting Started

### 1. Create virtual environment (optional but recommended)

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the template and update values:

```powershell
copy env.example .env
```

`.env` contents:

```env
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite+aiosqlite:///./blogs.db
```

### 4. Run the FastAPI server

```powershell
uvicorn app.main:app --reload
```

Visit <http://127.0.0.1:8000/> to begin generating content.

## Usage Walkthrough

1. Open the home page, paste up to ten topics (one per line) and optionally pick a tone.
2. Click **Generate Blogs** – the app calls OpenAI for each title, stores results, and redirects to the library.
3. On `/blogs`, each card shows a preview with actions:
   - **Read More** – opens the full article in a modal.
   - **Regenerate** – re-queries OpenAI and overwrites the article.
   - **Download** – streams a `.txt` export.
4. Return to the homepage at any time to add new topics.

### Example Input

```
Emerging AI trends for midsize retailers
How to build a productivity stack for remote teams
Sustainable packaging strategies for D2C brands
```

### Example Output (excerpt)

```
# Emerging AI Trends for Midsize Retailers

## Introduction
Artificial intelligence is no longer reserved for enterprise giants...

## AI-Powered Demand Forecasting
...
```

## Testing the AI Flow

The app defaults to `gpt-4o-mini`. To minimise costs during demos you can switch to a cheaper model by adjusting `OPENAI_MODEL` in `.env`. All OpenAI calls are wrapped with error handling; the UI will surface meaningful alerts if a request fails.



