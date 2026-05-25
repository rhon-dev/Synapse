# ⚡ Synapse — Virtual AI Study Partner

Synapse is a production-ready, AI-powered study platform. Students pick a
subject, ask questions, and get clear, scoped answers from GPT-4o. They can
also generate dynamic 5-question multiple-choice quizzes at Easy / Medium /
Hard difficulty and have their results graded instantly with explanations.

All chat messages and quiz results are persisted per-session in MongoDB so
history survives reloads.

---

## Features

- **Study Q&A (Chat Mode)** — pick a subject, ask anything, get an answer
  scoped to that subject by GPT-4o.
- **Dynamic Quiz Mode** — generate 5 MCQs at chosen difficulty via OpenAI
  JSON mode. Answer one at a time. Instant scoring + per-question
  explanations.
- **Session History** — each browser session gets a UUID stored in
  `localStorage`. All events are retrievable / clearable via the API.
- **Dark single-page UI** — vanilla HTML/CSS/JS, no framework.

---

## Tech Stack

| Layer          | Tech                                             |
|----------------|--------------------------------------------------|
| Backend        | Python 3.10+, FastAPI, async                     |
| AI             | OpenAI API (GPT-4o), JSON mode for quizzes       |
| Database       | MongoDB (local or Atlas) via **Motor** (async)   |
| Validation     | Pydantic v2                                      |
| Frontend       | Vanilla HTML / CSS / JS (single page)            |
| Dev tooling    | `python-dotenv`, `uvicorn`                       |

---

## Setup

### 1. Clone

```bash
git clone <your-repo-url> synapse
cd synapse
```

### 2. Create a virtualenv & install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Start MongoDB

Either run locally:

```bash
# macOS (Homebrew)
brew services start mongodb-community

# or with Docker
docker run -d --name synapse-mongo -p 27017:27017 mongo:7
```

…or use a MongoDB Atlas connection string.

### 4. Configure environment

Edit `backend/.env`:

```env
OPENAI_API_KEY=sk-your-real-key-here
MONGO_URI=mongodb://localhost:27017
DB_NAME=synapse
OPENAI_MODEL=gpt-4o
```

> **Never** commit `.env` — it is already in `.gitignore`.

### 5. Run

From the project root:

```bash
uvicorn backend.main:app --reload --port 8000
```

Open <http://localhost:8000> in your browser.

---

## API Reference

Base URL: `http://localhost:8000`

### `POST /chat`

Send a question, get an AI answer.

Request body:
```json
{
  "session_id": "uuid-string",
  "subject": "Biology",
  "question": "What is mitosis?"
}
```

Response:
```json
{
  "session_id": "uuid-string",
  "subject": "Biology",
  "question": "What is mitosis?",
  "answer": "Mitosis is …",
  "timestamp": "2026-05-26T10:00:00Z"
}
```

### `POST /quiz/generate`

Generate a 5-question quiz.

Request body:
```json
{
  "session_id": "uuid-string",
  "subject": "Python",
  "difficulty": "Medium"
}
```

Response:
```json
{
  "quiz_id": "uuid",
  "session_id": "uuid-string",
  "subject": "Python",
  "difficulty": "Medium",
  "questions": [
    {
      "question": "…",
      "options": ["…", "…", "…", "…"],
      "answer": "B",
      "explanation": "…"
    }
  ]
}
```

> `difficulty` must be exactly `Easy`, `Medium`, or `Hard`.

### `POST /quiz/submit`

Submit answers, get score + per-question explanations.

Request body:
```json
{
  "session_id": "uuid-string",
  "quiz_id": "uuid",
  "answers": ["A", "C", "B", "D", "A"]
}
```

Response:
```json
{
  "quiz_id": "uuid",
  "session_id": "uuid-string",
  "score": 4,
  "total": 5,
  "results": [
    {
      "question": "…",
      "your_answer": "A",
      "correct_answer": "A",
      "correct": true,
      "explanation": "…"
    }
  ]
}
```

### `GET /sessions/{session_id}`

Return the full event history for a session (chats + quizzes + submissions).

### `DELETE /sessions/{session_id}`

Clear all events for a session. Returns `404` if no events exist.

### `GET /healthz`

Liveness check: `{"status": "ok"}`.

Interactive docs: <http://localhost:8000/docs>

---

## Folder Structure

```
synapse/
├── backend/
│   ├── main.py              # FastAPI app, lifespan, static mount
│   ├── routes/
│   │   ├── chat.py          # /chat, /quiz/generate, /quiz/submit
│   │   └── sessions.py      # /sessions/{id} GET + DELETE
│   ├── services/
│   │   ├── ai.py            # OpenAI client + error mapping
│   │   └── quiz.py          # Quiz persistence + grading
│   ├── db/
│   │   └── mongo.py         # Motor async client + lifecycle
│   ├── models/
│   │   └── schemas.py       # Pydantic v2 request/response models
│   └── .env                 # secrets (gitignored)
├── frontend/
│   ├── index.html           # Two-tab single page UI
│   ├── style.css            # Dark theme
│   └── app.js               # fetch() calls, session UUID, render
├── .gitignore
├── requirements.txt
└── README.md
```

---

## MongoDB Schema

All events live in a single `events` collection:

```jsonc
{
  "_id": ObjectId(...),
  "session_id": "uuid-string",
  "timestamp": ISODate("..."),
  "type": "chat" | "quiz_generated" | "quiz_submitted",
  "payload": { /* type-specific fields */ }
}
```

Indexed on `(session_id, timestamp)` for fast per-session retrieval.

---

## Error Handling

OpenAI failures map to proper HTTP statuses:

| OpenAI exception        | HTTP status |
|-------------------------|-------------|
| `AuthenticationError`   | 401         |
| `RateLimitError`        | 429         |
| `APITimeoutError`       | 504         |
| `APIConnectionError`    | 502         |
| `APIError`              | 502         |
| Anything else           | 500         |

Pydantic validation errors return 422 automatically.

---

## License

MIT — do whatever you want with it.
