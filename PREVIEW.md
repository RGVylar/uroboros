# Preview Setup

## Quick Start

The preview uses local development servers with demo data. No external database required.

### Start Servers

```bash
# From project root, start both servers:
npm run dev --workspace=frontend    # Frontend on http://localhost:5173+
python -m uvicorn app.main:app --host localhost --port 8000 --cwd backend  # Backend on http://localhost:8000
```

Or use the launch configuration in Claude Code:
- `.claude/launch.json` defines both servers
- Preview tool will start them automatically

### Demo Credentials

```
Email: demo@demo.com
Password: demo1234
```

This account is auto-seeded with demo data (products, exercises, etc.) on first startup.

## Configuration

### Frontend
- **`.env.local`** in `frontend/` directory:
  ```
  VITE_API_URL=http://localhost:8000/api
  ```
- Vite dev server auto-rebuilds on file changes
- May start on port 5174/5175 if 5173 is busy

### Backend
- **`.env`** in `backend/` directory:
  ```
  DEMO_MODE=true
  ```
- Uses SQLite in temp directory (auto-cleaned on restart)
- No PostgreSQL needed for preview
- Uvicorn hot-reload enabled

## Database

In demo mode:
- SQLite database created at system temp: `{tempdir}/uroboros_demo.db`
- Fresh database on each startup (auto-deletes old file)
- Demo data seeded on initialization
- All migrations applied automatically

## Important Notes

- **Demo Mode Only**: Set `DEMO_MODE=true` in backend `.env` for SQLite
- **Circular Import Fix**: Database imports from submodules directly to avoid import cycles
- **Migration Compatibility**: Migrations are dialect-aware (SQLite doesn't support PostgreSQL ENUMs)
- **localStorage**: Supplement tracker uses `supplements_enabled` flag in browser storage
