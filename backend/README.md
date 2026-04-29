# Backend README

The FastAPI backend lives in this directory. The current source of truth for setup, environment variables, usage examples, and Markov deployment steps is the root [README.md](../README.md).

Quick reference:

- Install: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Config: create `backend/.env` from `backend/.env.example`
- Run: `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000`
- Docs: `http://127.0.0.1:8000/docs`
- Tests: `DATABASE_URL=sqlite:///./test.db ALLOW_DB_RESET_FOR_TESTS=1 python -m pytest tests`
