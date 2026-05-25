/* ============================================================
   Synapse — Frontend logic
   - Vanilla JS, no framework
   - Talks to FastAPI backend on same origin
   ============================================================ */

const API_BASE = ""; // same origin

// ---------- Session ID ----------
const SESSION_KEY = "synapse_session_id";

function getSessionId() {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = (crypto.randomUUID && crypto.randomUUID()) || _uuidFallback();
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

function _uuidFallback() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

const SESSION_ID = getSessionId();

// ---------- DOM ----------
const $ = (sel) => document.querySelector(sel);

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".tab-panel");
const sessionLabel = $("#sessionLabel");
const clearBtn = $("#clearBtn");

// Study
const chatWindow = $("#chatWindow");
const chatForm = $("#chatForm");
const chatInput = $("#chatInput");
const sendBtn = $("#sendBtn");
const studySubject = $("#studySubject");

// Quiz
const quizSubject = $("#quizSubject");
const quizDifficulty = $("#quizDifficulty");
const generateBtn = $("#generateBtn");
const quizArea = $("#quizArea");

sessionLabel.textContent = SESSION_ID.slice(0, 8) + "…";

// ---------- Tabs ----------
tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const name = tab.dataset.tab;
    tabs.forEach((t) => t.classList.toggle("active", t === tab));
    panels.forEach((p) =>
      p.classList.toggle("active", p.id === `tab-${name}`)
    );
  });
});

// ---------- API helper ----------
async function api(path, options = {}) {
  const resp = await fetch(API_BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let body;
  const text = await resp.text();
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = { detail: text };
  }
  if (!resp.ok) {
    const msg = body.detail || `HTTP ${resp.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return body;
}

// ============================================================
// STUDY (CHAT) MODE
// ============================================================

function addBubble(text, role) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function showSystemMsg(text) {
  addBubble(text, "system");
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = chatInput.value.trim();
  if (!question) return;

  const subject = studySubject.value;
  addBubble(question, "user");
  chatInput.value = "";
  chatInput.disabled = true;
  sendBtn.disabled = true;

  const loading = addBubble("Synapse is thinking…", "loading");

  try {
    const data = await api("/chat", {
      method: "POST",
      body: JSON.stringify({
        session_id: SESSION_ID,
        subject,
        question,
      }),
    });
    loading.remove();
    addBubble(data.answer, "ai");
  } catch (err) {
    loading.remove();
    addBubble("Error: " + err.message, "error");
  } finally {
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
});

// ============================================================
// QUIZ MODE
// ============================================================

let currentQuiz = null;       // { quiz_id, questions: [...] }
let currentIndex = 0;
let userAnswers = [];          // array of "A".."D" or null

const LETTERS = ["A", "B", "C", "D"];

generateBtn.addEventListener("click", async () => {
  const subject = quizSubject.value;
  const difficulty = quizDifficulty.value;

  generateBtn.disabled = true;
  generateBtn.textContent = "Generating…";
  quizArea.innerHTML = '<p class="placeholder">Generating quiz with AI…</p>';

  try {
    const data = await api("/quiz/generate", {
      method: "POST",
      body: JSON.stringify({
        session_id: SESSION_ID,
        subject,
        difficulty,
      }),
    });
    currentQuiz = data;
    currentIndex = 0;
    userAnswers = new Array(data.questions.length).fill(null);
    renderQuestion();
  } catch (err) {
    quizArea.innerHTML = `<div class="bubble error">Failed to generate quiz: ${escapeHTML(
      err.message
    )}</div>`;
  } finally {
    generateBtn.disabled = false;
    generateBtn.textContent = "Generate Quiz";
  }
});

function renderQuestion() {
  if (!currentQuiz) return;
  const q = currentQuiz.questions[currentIndex];
  const total = currentQuiz.questions.length;

  quizArea.innerHTML = "";

  const progress = document.createElement("div");
  progress.className = "quiz-progress";
  progress.textContent = `Question ${currentIndex + 1} of ${total}`;
  quizArea.appendChild(progress);

  const card = document.createElement("div");
  card.className = "quiz-card";

  const qText = document.createElement("div");
  qText.className = "quiz-q";
  qText.textContent = q.question;
  card.appendChild(qText);

  const opts = document.createElement("div");
  opts.className = "quiz-options";

  q.options.forEach((optText, i) => {
    const letter = LETTERS[i];
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "quiz-option";
    if (userAnswers[currentIndex] === letter) btn.classList.add("selected");
    btn.innerHTML = `<span class="letter">${letter}</span><span class="text"></span>`;
    btn.querySelector(".text").textContent = optText;
    btn.addEventListener("click", () => {
      userAnswers[currentIndex] = letter;
      // Re-render to update selection state
      renderQuestion();
    });
    opts.appendChild(btn);
  });
  card.appendChild(opts);

  const actions = document.createElement("div");
  actions.className = "quiz-actions";

  const prevBtn = document.createElement("button");
  prevBtn.className = "btn btn-ghost";
  prevBtn.textContent = "← Previous";
  prevBtn.disabled = currentIndex === 0;
  prevBtn.addEventListener("click", () => {
    if (currentIndex > 0) {
      currentIndex--;
      renderQuestion();
    }
  });
  actions.appendChild(prevBtn);

  if (currentIndex < total - 1) {
    const nextBtn = document.createElement("button");
    nextBtn.className = "btn btn-primary";
    nextBtn.textContent = "Next →";
    nextBtn.disabled = userAnswers[currentIndex] === null;
    nextBtn.addEventListener("click", () => {
      currentIndex++;
      renderQuestion();
    });
    actions.appendChild(nextBtn);
  } else {
    const submitBtn = document.createElement("button");
    submitBtn.className = "btn btn-primary";
    submitBtn.textContent = "Submit Quiz";
    submitBtn.disabled = userAnswers.includes(null);
    submitBtn.addEventListener("click", submitQuiz);
    actions.appendChild(submitBtn);
  }

  card.appendChild(actions);
  quizArea.appendChild(card);
}

async function submitQuiz() {
  if (!currentQuiz) return;
  if (userAnswers.includes(null)) return;

  quizArea.innerHTML = '<p class="placeholder">Grading…</p>';

  try {
    const data = await api("/quiz/submit", {
      method: "POST",
      body: JSON.stringify({
        session_id: SESSION_ID,
        quiz_id: currentQuiz.quiz_id,
        answers: userAnswers,
      }),
    });
    renderResults(data);
  } catch (err) {
    quizArea.innerHTML = `<div class="bubble error">Submission failed: ${escapeHTML(
      err.message
    )}</div>`;
  }
}

function renderResults(data) {
  const pct = Math.round((data.score / data.total) * 100);
  quizArea.innerHTML = "";

  const wrap = document.createElement("div");
  wrap.className = "quiz-result";

  const score = document.createElement("p");
  score.className = "quiz-score";
  score.textContent = `${data.score} / ${data.total}`;
  wrap.appendChild(score);

  const sub = document.createElement("p");
  sub.className = "sub";
  sub.textContent = `${pct}% — ${verdict(pct)}`;
  wrap.appendChild(sub);

  const list = document.createElement("div");
  list.className = "explanation-list";

  data.results.forEach((r, i) => {
    const item = document.createElement("div");
    item.className = "explanation-item " + (r.correct ? "right" : "wrong");

    const q = document.createElement("div");
    q.className = "q";
    q.textContent = `${i + 1}. ${r.question}`;
    item.appendChild(q);

    const a = document.createElement("div");
    a.className = "a";
    a.textContent = r.correct
      ? `✓ Correct (${r.your_answer})`
      : `✗ Your answer: ${r.your_answer} — Correct: ${r.correct_answer}`;
    item.appendChild(a);

    const e = document.createElement("div");
    e.className = "e";
    e.textContent = r.explanation;
    item.appendChild(e);

    list.appendChild(item);
  });

  wrap.appendChild(list);

  const again = document.createElement("button");
  again.className = "btn btn-primary";
  again.style.marginTop = "20px";
  again.textContent = "Generate Another Quiz";
  again.addEventListener("click", () => {
    currentQuiz = null;
    userAnswers = [];
    currentIndex = 0;
    quizArea.innerHTML = "";
  });
  wrap.appendChild(again);

  quizArea.appendChild(wrap);
}

function verdict(pct) {
  if (pct === 100) return "Perfect! 🎉";
  if (pct >= 80) return "Great work!";
  if (pct >= 60) return "Solid — keep practicing.";
  if (pct >= 40) return "Some gaps — review the explanations.";
  return "Time to study up.";
}

// ============================================================
// CLEAR SESSION
// ============================================================

clearBtn.addEventListener("click", async () => {
  if (!confirm("Clear this session? All chat + quiz history will be removed.")) {
    return;
  }
  try {
    await api(`/sessions/${encodeURIComponent(SESSION_ID)}`, { method: "DELETE" });
  } catch (err) {
    // 404 is fine (already empty); other errors surface
    if (!/404/.test(err.message) && !/no events/i.test(err.message)) {
      alert("Failed to clear session: " + err.message);
      return;
    }
  }
  // Wipe local UI + new session id
  localStorage.removeItem(SESSION_KEY);
  location.reload();
});

// ============================================================
// LOAD HISTORY ON STARTUP
// ============================================================

async function loadHistory() {
  try {
    const data = await api(`/sessions/${encodeURIComponent(SESSION_ID)}`);
    if (!data.events || data.events.length === 0) {
      showSystemMsg("New session started. Pick a subject and ask anything.");
      return;
    }
    data.events
      .filter((e) => e.type === "chat")
      .forEach((e) => {
        addBubble(e.payload.question, "user");
        addBubble(e.payload.answer, "ai");
      });
  } catch (err) {
    if (/404/.test(err.message) || /no events/i.test(err.message)) {
      showSystemMsg("New session started. Pick a subject and ask anything.");
    } else {
      showSystemMsg("Could not load history: " + err.message);
    }
  }
}

function escapeHTML(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

loadHistory();
