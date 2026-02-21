# YouTube Downloader (React + FastAPI)

Simple full-stack YouTube downloader using `yt-dlp`.

Features
- Paste YouTube URL
- Attempts 4K download if available
- Shows download progress via WebSocket
- Enforces 2GB file size limit
- Docker-ready (backend + frontend)

Quick start (Docker):

```bash
# from project root
docker compose build
docker compose up -d
```

Frontend will be at http://localhost:3000 and backend at http://localhost:8000.

API
- POST /api/download  - JSON {"url":"..."} -> returns `{job_id}`
- WebSocket /ws/{job_id} - receives progress messages
- GET /api/file/{job_id} - download file when ready

Deploying to Render (one-click public URL)

1. Push this repository to GitHub.
2. Create a free account at https://render.com and go to "New" → "Import from GitHub".
3. Select this repository. Render will read `render.yaml` and propose two services:
	- `yt-downloader-backend` (Docker web service) — uses `backend/Dockerfile` and listens on port 8000
	- `yt-downloader-frontend` (Static site) — builds the frontend and serves `/dist`
4. Click "Create" (or "Create and deploy"). Render will start a build and provide a public URL for each service.

Notes
- The backend stores downloads in the container; for production you should attach persistent volumes or use object storage.
- For secure production use: add authentication, rate limiting, and persistent job storage. Clean-up policy for stored downloads is recommended.
