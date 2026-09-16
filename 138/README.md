# Memo: AIML Chatbot With Memory

A small Flask chatbot that uses AIML rules for responses and SQLite for persistent memory.

## Run it

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

Try: `My name is Alex`, `My favorite is jazz`, then `What do you remember`.

Memory is stored locally in `memory.db`. The browser stores a local user ID so returning to the app restores the same conversation.
