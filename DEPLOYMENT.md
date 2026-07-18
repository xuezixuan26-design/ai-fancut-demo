# Deployment Guide

This project has two deployable parts:

- `frontend`: Vite/React web app, suitable for Vercel.
- `backend`: FastAPI + OpenCV + FFmpeg render service, suitable for a container host such as Render, Railway, Fly.io, ECS, or a VM.

Vercel can host the frontend, but the current video rendering backend should not be treated as a normal static/serverless Vercel app because it needs large uploads, FFmpeg, temporary files, and longer-running jobs.

## 1. Backend

Deploy `backend/` as a Docker service.

Recommended quick path: use Render Blueprint from `render.yaml`.

```text
Render Dashboard -> New -> Blueprint -> connect GitHub repo -> select ai-fancut-demo
```

Required environment variables:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
CORS_ORIGINS=https://your-vercel-app.vercel.app
OUTPUT_FPS=30
MAX_UPLOAD_MB=800
```

Recommended production settings:

- Attach persistent disk or object storage for `storage/`.
- Put the service behind HTTPS.
- Set upload/body-size limits on the platform or reverse proxy.
- Keep FFmpeg available in the container.

Health check:

```text
GET /health
```

## 2. Frontend on Vercel

Set Vercel project root to `frontend/`.

Build settings:

```text
Install command: npm install
Build command: npm run build
Output directory: dist
```

Required environment variable:

```env
VITE_API_BASE=https://your-backend-domain.example.com
```

For local development, leave `VITE_API_BASE` empty or set it to:

```env
VITE_API_BASE=http://127.0.0.1:8000
```

## 3. GitHub Sync Checklist

Before pushing:

```bash
cd frontend
npm run build
cd ..
python -m compileall backend/app
git status
```

Do not commit user-generated files:

- `storage/raw_videos`
- `storage/bgm`
- `storage/reference`
- `storage/outputs`
- `storage/projects`
- `storage/knowledge_base`
- `.env`

## 4. Engineering Work Still Needed For Public Sharing

Minimum shareable version:

- Frontend on Vercel.
- Backend on a container host.
- `VITE_API_BASE` points to backend.
- Backend `CORS_ORIGINS` includes the Vercel URL.
- Persistent storage or object storage is configured.

Production-grade version:

- Job queue for analyze/render tasks.
- Per-job status and cancellation.
- Upload size/type validation.
- User sessions or project access tokens.
- Automatic cleanup/retention policy for videos.
- Render history browser and deletion.
- Error logging and observability.
- Regression harness for each template/skill.
- Rate limiting and abuse protection.
