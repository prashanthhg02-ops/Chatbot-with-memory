import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

if not hasattr(time, "clock"):
    time.clock = time.perf_counter

import aiml
from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "memory.db"
AIML_FILE = BASE_DIR / "aiml" / "chatbot.aiml"

app = Flask(__name__)
kernel = aiml.Kernel()
kernel.learn(str(AIML_FILE))


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                favorite TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'bot')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def now():
    return datetime.now(timezone.utc).isoformat()


def ensure_profile(user_id):
    timestamp = now()
    with get_db() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO profiles (user_id, created_at, updated_at) VALUES (?, ?, ?)",
            (user_id, timestamp, timestamp),
        )


def profile_for(user_id):
    ensure_profile(user_id)
    with get_db() as connection:
        profile = connection.execute(
            "SELECT name, favorite FROM profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
    return dict(profile)


def remember(user_id, role, content):
    with get_db() as connection:
        connection.execute(
            "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, now()),
        )
        connection.execute(
            "UPDATE profiles SET updated_at = ? WHERE user_id = ?", (now(), user_id)
        )


def history_for(user_id):
    with get_db() as connection:
        rows = connection.execute(
            "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 20",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def update_memory(user_id, message):
    normalized = message.strip()
    lowered = normalized.lower()
    name = None
    favorite = None

    if lowered.startswith("my name is "):
        name = normalized[11:].strip(" .,!?")[:80]
    elif lowered.startswith("call me "):
        name = normalized[8:].strip(" .,!?")[:80]

    if lowered.startswith("my favorite is "):
        favorite = normalized[15:].strip(" .,!?")[:120]

    if name or favorite:
        fields = []
        values = []
        if name:
            fields.append("name = ?")
            values.append(name)
        if favorite:
            fields.append("favorite = ?")
            values.append(favorite)
        fields.append("updated_at = ?")
        values.append(now())
        values.append(user_id)
        with get_db() as connection:
            connection.execute(
                f"UPDATE profiles SET {', '.join(fields)} WHERE user_id = ?", values
            )


def response_for(user_id, message):
    update_memory(user_id, message)
    profile = profile_for(user_id)
    if message.strip().lower() in {"what do you remember", "what do you know about me"}:
        remembered = []
        if profile["name"]:
            remembered.append(f"your name is {profile['name']}")
        if profile["favorite"]:
            remembered.append(f"your favorite is {profile['favorite']}")
        return "I remember " + " and ".join(remembered) + "." if remembered else "I do not know anything about you yet."

    response = kernel.respond(message, user_id).strip()
    if not response:
        response = "I am still learning. Try telling me your name or favorite thing."
    if message.strip().lower().startswith(("my name is ", "call me ", "my favorite is ")):
        response += " I will remember that for next time."
    return response


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    user_id = str(payload.get("user_id", "")).strip() or str(uuid.uuid4())
    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400
    ensure_profile(user_id)
    remember(user_id, "user", message)
    response = response_for(user_id, message)
    remember(user_id, "bot", response)
    return jsonify({"user_id": user_id, "response": response, "profile": profile_for(user_id)})


@app.get("/api/history/<user_id>")
def history(user_id):
    return jsonify({"user_id": user_id, "messages": history_for(user_id), "profile": profile_for(user_id)})


@app.post("/api/reset/<user_id>")
def reset(user_id):
    with get_db() as connection:
        connection.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
    return jsonify({"ok": True})


initialize_database()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", "5000")))
