@echo off
REM One-command launcher (Windows): set up if needed, build the frontend, then
REM serve the whole app from http://127.0.0.1:8000
setlocal
cd /d "%~dp0"

if not exist .venv (
  echo Creating Python virtualenv and installing deps...
  python -m venv .venv
  call .venv\Scripts\pip install --quiet --upgrade pip
  call .venv\Scripts\pip install --quiet -r requirements.txt
)
call .venv\Scripts\activate

if not exist frontend\dist (
  echo Building frontend...
  pushd frontend
  if not exist node_modules call npm install
  call npm run build
  popd
)

echo Serving at http://127.0.0.1:8000  (Ctrl+C to stop)
start "" http://127.0.0.1:8000
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
