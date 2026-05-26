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
| AI             | Any OpenAI-API-compatible LLM (OpenAI, Groq, Gemini, Ollama, OpenRouter) — JSON mode for quizzes |
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

### 3. Choose a MongoDB backend

**Option A — Local (fastest):**

```bash
brew install mongodb-community
brew services start mongodb-community

# or with Docker
docker run -d --name synapse-mongo -p 27017:27017 mongo:7
```

**Option B — MongoDB Atlas (recommended for prod):** see
[Atlas setup](#mongodb-atlas-setup) below.

### 4. Configure environment

```bash
cp backend/.env.example backend/.env
# then edit backend/.env with your real values
```

Minimum required keys:

```env
OPENAI_API_KEY=<your-llm-provider-key>
OPENAI_BASE_URL=<provider-base-url>      # leave blank for OpenAI itself
OPENAI_MODEL=<model-name>
MONGO_URI=mongodb://localhost:27017      # or mongodb+srv://... for Atlas
DB_NAME=synapse
```

#### LLM provider options

Synapse uses the OpenAI Python SDK, which is compatible with multiple
providers. Pick whichever you have access to:

| Provider     | Free? | `OPENAI_BASE_URL`                                            | Example model              |
|--------------|-------|--------------------------------------------------------------|----------------------------|
| **OpenAI**   | Paid  | *(leave empty — SDK default)*                                | `gpt-4o`                   |
| **Groq**     | Free  | `https://api.groq.com/openai/v1`                             | `llama-3.3-70b-versatile`  |
| **Gemini**   | Free  | `https://generativelanguage.googleapis.com/v1beta/openai/`   | `gemini-1.5-flash`         |
| **Ollama**   | Free (local) | `http://localhost:11434/v1`                            | `llama3.2`                 |
| **OpenRouter** | Free + paid mix | `https://openrouter.ai/api/v1`                     | `meta-llama/llama-3.3-70b-instruct:free` |

Where to get keys:

- OpenAI → <https://platform.openai.com/api-keys>  *(billing required)*
- Groq → <https://console.groq.com/keys>  *(no credit card)*
- Gemini → <https://aistudio.google.com/apikey>  *(no credit card)*
- Ollama → no key — `brew install ollama && ollama pull llama3.2`
- OpenRouter → <https://openrouter.ai/keys>

> **Never** commit `.env` — it is in `.gitignore`. Always commit `.env.example`
> with placeholders so contributors know which vars are required.

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

### Atlas Admin API endpoints (optional)

Thin pass-through to [MongoDB Atlas Admin API v2](https://www.mongodb.com/docs/api/doc/atlas-admin-api-v2/).
Require `ATLAS_API_PUBLIC_KEY`, `ATLAS_API_PRIVATE_KEY`, `ATLAS_PROJECT_ID` env
vars. Return raw Atlas JSON.

| Method | Path                              | Atlas operation             |
|--------|-----------------------------------|-----------------------------|
| GET    | `/atlas/projects`                 | `GET /groups`               |
| GET    | `/atlas/project`                  | `GET /groups/{id}`          |
| GET    | `/atlas/clusters`                 | `GET /groups/{id}/clusters` |
| GET    | `/atlas/clusters/{name}`          | `GET /groups/{id}/clusters/{name}` |
| GET    | `/atlas/database-users`           | `GET /groups/{id}/databaseUsers` |
| GET    | `/atlas/network-access`           | `GET /groups/{id}/accessList` |
| GET    | `/atlas/orgs/{org_id}`            | `GET /orgs/{orgId}`         |

Interactive docs: <http://localhost:8000/docs>

---

## MongoDB Atlas Setup

Two independent pieces of config — both are optional but recommended for
production:

### A. Atlas as your data store (`MONGO_URI`)

1. Sign up: <https://www.mongodb.com/cloud/atlas/register>
2. **Create a project** (any name).
3. **Build a Database** → pick the **Free (M0)** tier in any region near you.
4. While the cluster spins up (1–3 min), set two access things:
   - **Database Access** → "Add New Database User" → username + password
     (autogenerate, save it).
   - **Network Access** → "Add IP Address" → either your current IP or
     `0.0.0.0/0` for "allow anywhere" (fine for dev — restrict later).
5. Once the cluster is "Active": click **Connect → Drivers**.
6. Choose **Python**, version **3.12 or later**. Copy the SRV string. Looks
   like `mongodb+srv://USER:<password>@cluster-xxx.xxxxx.mongodb.net/?retryWrites=true&w=majority`.
7. Replace `<password>` with the password from step 4.
8. Paste into `backend/.env`:

   ```env
   MONGO_URI=mongodb+srv://USER:REAL_PASSWORD@cluster-xxx.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```

9. Restart uvicorn. Motor auto-handles TLS + SRV resolution.

### B. Atlas Admin API (`/atlas/*` endpoints)

Only needed if you want the app to read/manage Atlas infrastructure (list
clusters, users, etc.) at runtime.

1. **Find your Project ID:** Atlas → Project → **Settings**. Copy the 24-char
   hex ID (e.g. `5e3f1a2b9c4d3e1f0a1b2c3d`).
2. **Create an API key:** Atlas → **Access Manager** (top-right org switcher
   → Access Manager) → **API Keys** tab → **Create Organization API Key**.
   - Description: `synapse-admin`
   - Permission: `Organization Read Only` (or higher if you need writes).
3. Atlas shows the **public key** (short) and **private key** (UUID-style).
   Copy both. The private key is shown **once** — store it now.
4. **Add the API key to your Project**: still in Access Manager → Projects
   tab → your project → Add the key → grant project-level access.
5. **Add your IP to the API access list** for the key (Access Manager →
   API Keys → click your key → API Access List).
6. Paste into `backend/.env`:

   ```env
   ATLAS_API_PUBLIC_KEY=abcdwxyz
   ATLAS_API_PRIVATE_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ATLAS_PROJECT_ID=5e3f1a2b9c4d3e1f0a1b2c3d
   ```

7. Restart uvicorn. Test:

   ```bash
   curl http://localhost:8000/atlas/clusters
   ```

   Returns Atlas JSON with cluster list. 401 = bad keys. 403 = key lacks
   project access. 404 = wrong project ID.

> **Security:** the API private key has cluster-management power. Treat it
> like a root password. Never commit. Rotate periodically.

---

## Folder Structure

```
synapse/
├── backend/
│   ├── main.py              # FastAPI app, lifespan, static mount
│   ├── routes/
│   │   ├── chat.py          # /chat, /quiz/generate, /quiz/submit
│   │   ├── sessions.py      # /sessions/{id} GET + DELETE
│   │   └── atlas.py         # /atlas/* — Atlas Admin API v2 pass-through
│   ├── services/
│   │   ├── ai.py            # OpenAI client + error mapping
│   │   ├── quiz.py          # Quiz persistence + grading
│   │   └── atlas.py         # httpx + Digest auth Atlas Admin client
│   ├── db/
│   │   └── mongo.py         # Motor async client (local or Atlas SRV)
│   ├── models/
│   │   └── schemas.py       # Pydantic v2 request/response models
│   ├── .env.example         # template (tracked in git)
│   └── .env                 # real secrets (gitignored)
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
