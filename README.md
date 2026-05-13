# Automation Engine

Production-oriented foundation for an industrial IoT automation backend built with Python, FastAPI, Supabase, APScheduler, and dotenv configuration.

## Project Structure

```text
automation_engine/
├── app/
│   ├── main.py
│   ├── config/
│   │   └── settings.py
│   ├── database/
│   │   ├── supabase_client.py
│   │   └── queries.py
│   ├── automations/
│   ├── services/
│   ├── scheduler/
│   │   └── scheduler.py
│   └── models/
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your local environment file:

```bash
copy .env.example .env
```

Update `.env` with your Supabase credentials.

## Run

```bash
uvicorn app.main:app --reload
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

## Notes

- Configuration is centralized in `app/config/settings.py`.
- Supabase access is centralized in `app/database/supabase_client.py`.
- Database operations belong in `app/database/queries.py`.
- APScheduler is started and stopped through the FastAPI lifespan hook.
- Business logic should live in `app/services/`.
- Automation definitions and orchestration logic should live in `app/automations/`.
