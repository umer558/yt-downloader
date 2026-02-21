import React, { useState, useRef } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`

export default function App() {
  const [url, setUrl] = useState('')
  const [job, setJob] = useState(null)
  const [percent, setPercent] = useState(0)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)
  const [downloadUrl, setDownloadUrl] = useState(null)
  const wsRef = useRef(null)

  const start = async () => {
    setError(null)
    setStatus('starting')
    setPercent(0)
    setDownloadUrl(null)
    try {
      const res = await fetch(`${API_BASE}/api/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to start')
      setJob(data.job_id)
      setStatus('started')
      openSocket(data.job_id)
    } catch (e) {
      setError(e.message)
      setStatus('error')
    }
  }

  const openSocket = (jobId) => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${protocol}://${window.location.hostname}:8000/ws/${jobId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'progress' && msg.percent != null) {
          setPercent(Number(msg.percent).toFixed(2))
          setStatus('downloading')
        } else if (msg.type === 'info') {
          setStatus('processing')
        } else if (msg.type === 'done') {
          setStatus('done')
          setDownloadUrl(`${API_BASE}/api/file/${jobId}`)
          ws.close()
        } else if (msg.type === 'error') {
          setStatus('error')
          setError(msg.message || 'Download failed')
          ws.close()
        }
      } catch (e) {
        console.error(e)
      }
    }
    ws.onclose = () => {}
    ws.onerror = (e) => {
      setError('WebSocket error')
      setStatus('error')
    }
  }

  return (
    <div className="container">
      <div className="card">
        <h1>YouTube Downloader</h1>
        <p className="muted">Paste a YouTube link and download in best-available 4K</p>
        <input value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://youtube.com/watch?v=..." />
        <button onClick={start} disabled={!url || status==='downloading' || status==='processing'}>Download</button>

        <div className="status">
          <div>Status: <strong>{status}</strong></div>
          {status==='downloading' || status==='processing' ? (
            <div className="progress">
              <div className="bar" style={{width: `${percent}%`}} />
            </div>
          ) : null}
          {percent>0 && <div className="percent">{percent}%</div>}
          {error && <div className="error">Error: {error}</div>}
          {downloadUrl && <a className="download-link" href={downloadUrl}>Download File</a>}
        </div>
      </div>
    </div>
  )
}
