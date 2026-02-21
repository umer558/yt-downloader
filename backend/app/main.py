import asyncio
import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict
from .download import start_download

app = FastAPI(title="YouTube Downloader")

# Allow all origins for simplicity; in production restrict this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# mount files
app.mount('/files', StaticFiles(directory=DOWNLOAD_DIR), name='files')

# in-memory job registry
jobs: Dict[str, Dict] = {}


@app.post('/api/download')
async def api_download(payload: Dict):
    url = payload.get('url')
    if not url:
        raise HTTPException(status_code=400, detail='Missing url')
    job_id = uuid.uuid4().hex
    queue: asyncio.Queue = asyncio.Queue()

    # start background task
    task = asyncio.create_task(start_download(job_id, url, queue))
    jobs[job_id] = {'queue': queue, 'task': task, 'file': None}

    return JSONResponse({'job_id': job_id})


@app.websocket('/ws/{job_id}')
async def websocket_endpoint(ws: WebSocket, job_id: str):
    await ws.accept()
    if job_id not in jobs:
        await ws.send_json({'type': 'error', 'message': 'Job not found'})
        await ws.close()
        return
    queue: asyncio.Queue = jobs[job_id]['queue']
    try:
        while True:
            msg = await queue.get()
            await ws.send_json(msg)
            if msg.get('type') == 'done' or msg.get('type') == 'error':
                # store file path on done
                if msg.get('type') == 'done':
                    jobs[job_id]['file'] = msg.get('path')
                break
    except WebSocketDisconnect:
        return
    finally:
        try:
            await ws.close()
        except Exception:
            pass


@app.get('/api/file/{job_id}')
async def get_file(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    path = job.get('file')
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail='File not ready')
    return FileResponse(path, filename=os.path.basename(path))


@app.get('/api/status/{job_id}')
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    task = job.get('task')
    state = 'running'
    if task.done():
        state = 'done'
    return {'job_id': job_id, 'state': state}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app.main:app', host='0.0.0.0', port=8000, reload=False)
