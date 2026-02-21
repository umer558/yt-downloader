import asyncio
import os
import uuid
from yt_dlp import YoutubeDL

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'downloads')
os.makedirs(os.path.abspath(DOWNLOAD_DIR), exist_ok=True)

SIZE_LIMIT_BYTES = 2 * 1024 * 1024 * 1024  # 2GB


async def start_download(job_id: str, url: str, queue: asyncio.Queue):
    loop = asyncio.get_event_loop()
    # run blocking download in threadpool
    def _download():
        info = {}

        def progress_hook(d):
            try:
                status = d.get('status')
                if status == 'downloading':
                    downloaded = d.get('downloaded_bytes') or d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate')
                    if total and total > SIZE_LIMIT_BYTES:
                        # communicate error and raise to stop
                        queue.put_nowait({'type': 'error', 'message': 'File exceeds 2GB limit.'})
                        raise Exception('File too large')
                    percent = None
                    if total and downloaded is not None:
                        percent = float(downloaded) / float(total) * 100.0
                    queue.put_nowait({'type': 'progress', 'downloaded': downloaded, 'total': total, 'percent': percent, 'speed': d.get('speed')})
                elif status == 'finished':
                    # finished processing (may be postprocessing)
                    queue.put_nowait({'type': 'info', 'message': 'Download finished, processing...'})
                elif status == 'error':
                    queue.put_nowait({'type': 'error', 'message': 'Download error.'})
            except Exception as e:
                # if queue is full or closed, ignore
                try:
                    queue.put_nowait({'type': 'error', 'message': str(e)})
                except Exception:
                    pass
                raise

        ydl_opts = {
            'outtmpl': os.path.join(os.path.abspath(DOWNLOAD_DIR), f'{job_id}.%(ext)s'),
            'format': 'bestvideo[height>=2160]+bestaudio/best/best',
            'noplaylist': True,
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                res = ydl.extract_info(url, download=True)
                # find output filename
                out_ext = res.get('ext') or 'mp4'
                out_name = os.path.join(os.path.abspath(DOWNLOAD_DIR), f"{job_id}.{out_ext}")
                return {'path': out_name, 'title': res.get('title'), 'id': res.get('id')}
        except Exception as e:
            raise

    try:
        queue.put_nowait({'type': 'info', 'message': 'Queued download.'})
    except Exception:
        pass

    try:
        result = await loop.run_in_executor(None, _download)
        await queue.put({'type': 'done', 'path': result['path'], 'title': result.get('title')})
    except Exception as e:
        try:
            await queue.put({'type': 'error', 'message': str(e)})
        except Exception:
            pass
