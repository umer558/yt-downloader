# YouTube Downloader - Quick Deploy to Render
# This script will push your repo to GitHub and import it in Render

$RENDER_API_KEY = "rnd_qiSlN1SlitZYwArg0ZiMjSmTPVgc"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "YouTube Downloader - Render Deploy Setup" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

# Step 1: Initialize git and push to GitHub
$GitHubUsername = Read-Host "Enter your GitHub username"
$RepoName = Read-Host "Enter repo name (default: yt-downloader)"
if (-not $RepoName) { $RepoName = "yt-downloader" }

Write-Host "`n[Step 1] Initializing Git repository..." -ForegroundColor Yellow
git init
git add .
git commit -m "Initial commit: YouTube downloader app"
git remote add origin "https://github.com/$GitHubUsername/$RepoName.git"
git branch -M main

Write-Host "[Step 2] Pushing to GitHub (authenticate when prompted)..." -ForegroundColor Yellow
git push -u origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Git push failed. Make sure:" -ForegroundColor Red
    Write-Host "  1. Repository exists on GitHub" -ForegroundColor Red
    Write-Host "  2. You have push access" -ForegroundColor Red
    exit 1
}

Write-Host "`nSUCCESS: Repository pushed!" -ForegroundColor Green
Write-Host "URL: https://github.com/$GitHubUsername/$RepoName" -ForegroundColor Green

# Step 2: Manual import instructions
Write-Host "`n===============================================" -ForegroundColor Cyan
Write-Host "NEXT: Import to Render" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan

Write-Host @"

1. Open https://dashboard.render.com
2. Click New (top right) => Import from GitHub
3. Authorize GitHub if needed
4. Select the repository: $RepoName
5. Render will detect render.yaml and create two services:
   - yt-downloader-backend (Web Service)
   - yt-downloader-frontend (Static Site)
6. Click Create / Deploy for both
7. Wait 5-10 minutes for builds to complete
8. You will get public URLs

Frontend will be at: https://<your-frontend-name>.onrender.com
Backend will be at: https://<your-backend-name>.onrender.com

Questions during Render import?
- For backend: Uses Docker, port 8000 (auto-detected from Dockerfile)
- For frontend: Build cmd is 'cd frontend && npm ci && npm run build'
- Publish path is 'frontend/dist'

"@ -ForegroundColor Cyan

Read-Host "Press Enter once you have imported in Render"

# Step 3: Setup env var for frontend
Write-Host "`n[Step 3] Configure frontend environment variable..." -ForegroundColor Yellow
$BackendUrl = Read-Host "Enter your backend public URL (e.g., https://yt-downloader-backend.onrender.com)"

Write-Host @"
Go to Render dashboard -> yt-downloader-frontend -> Environment
Add this variable:
  Key: VITE_API_URL
  Value: $BackendUrl

Then redeploy the frontend (Manual Deploy button).

Press Enter when done...
"@ -ForegroundColor Yellow
Read-Host

# Step 4: Final instructions
Write-Host "`n===============================================" -ForegroundColor Cyan
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan

Write-Host @"

Your YouTube Downloader is now live!

Frontend URL: (from Render dashboard)
Backend URL: $BackendUrl

To test:
1. Open the frontend URL in your browser
2. Paste a YouTube link (e.g., https://www.youtube.com/watch?v=BaW_jenozKc)
3. Click Download and watch the progress bar

Troubleshooting:
- Check backend logs in Render if you get errors
- Verify VITE_API_URL matches your backend URL exactly
- Make sure yt-dlp downloads (may need ffmpeg)

Repository: https://github.com/$GitHubUsername/$RepoName
Dashboard: https://dashboard.render.com

"@ -ForegroundColor Green

Write-Host "`nPress Enter to close..."
Read-Host
