# Iceland Trip

Photo album + slideshow page, wired into the FastAPI backend (`backend/app/routes/iceland.py`)
so photos live on the server instead of the browser — accessible from any device on the
network, not just the one you uploaded from.

## Run it

It's served by the same backend as the health app:

```bash
./start.sh            # from the repo root
```

Then open http://127.0.0.1:8000/iceland-trip/

(Or in dev mode: `cd backend && uvicorn app.main:app --reload` and open
http://127.0.0.1:8000/iceland-trip/ directly — this page isn't part of the Vite dev server.)

## Notes

- Passphrase: `ICELAND_TRIP_PASSWORD` in `.env` (defaults to `vatnajokull`). Checked
  server-side; a signed cookie remembers you're unlocked. Separate from the health
  app's per-patient login.
- Photos are stored under `data/iceland_photos/` (gitignored, content-addressed by
  sha256) with metadata in the `trip_photo` table of the same SQLite DB as the health
  app — a separate table, untouched by anything health-related.
- Deleting a photo removes its DB row; the file is left on disk (same convention as
  the health app's document store), so re-uploading the same photo won't re-save it.
