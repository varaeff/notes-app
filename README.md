# Notes

A personal Markdown notes app. Keep notes, tag them, search them, and pin some to a date so you can browse them on a calendar.

Each user has their own private space. Every note is a Markdown document with a live preview while editing.

## What's inside

- Log in / register (single-user-per-account - no sharing).
- CRUD for notes with Markdown preview.
- Tags with filtering.
- Full-text search across title and body.
- Optional date on a note + a calendar view.
- Telegram reminders for dated notes, with per-user linking, notification toggle, timezone, and reminder time.

## Run it

Requirements: Docker with Compose.

```bash
make up          # start db + backend + frontend
make seed        # (optional) create a demo user with a few notes
```

Then open <http://localhost:5173>.

Demo credentials (after `make seed`):

- **username:** `demo`
- **password:** `demo1234`

### Telegram reminders

Telegram setup is optional. If `TELEGRAM_BOT_TOKEN` and `TELEGRAM_BOT_USERNAME` are not set, the app still works and the Telegram settings block is hidden.

To enable reminders locally:

1. Create a bot with BotFather.
2. Put the bot credentials into `backend/.env`:

```bash
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_BOT_USERNAME=your_bot_username
```

3. Start or restart the stack with `make up`.
4. Open Settings, generate a connection code, send it to the bot, then enable reminder notifications.

## Common commands

```bash
make help        # list all targets
make logs        # tail logs
make test        # run backend tests
make down        # stop the stack
make clean       # stop and wipe the database volume
```

## Layout

- `backend/` - FastAPI + SQLAlchemy + Alembic, talks to Postgres.
- `frontend/` - React + Vite.
- `docker-compose.yml` - db + backend + frontend + optional Telegram bot runner.
