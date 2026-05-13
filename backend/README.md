# Backend

FastAPI backend for AI Fancut Demo.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Install FFmpeg separately and make sure `ffmpeg` is available in PATH.

Optional environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`, default `gpt-4o-mini`

The server writes project files and intermediate JSON into `../storage`.
