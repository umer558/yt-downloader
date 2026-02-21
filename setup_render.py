#!/usr/bin/env python3
"""
Auto-setup script: Create Render services, get IDs, add GitHub secrets, and trigger deploy.
Usage: python setup_render.py <github-username> <github-repo> <render-api-key>
"""
import sys
import subprocess
import json
import time
import requests

RENDER_API_KEY = "rnd_qiSlN1SlitZYwArg0ZiMjSmTPVgc"
GITHUB_REPO_URL = None  # Will be set after user input

def run_cmd(cmd, shell=False):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e.stderr}")
        return None

def create_render_service(name, svc_type, dockerfile_path=None, build_cmd=None, publish_path=None):
    """Create a Render service via API."""
    url = "https://api.render.com/v1/services"
    headers = {"Authorization": f"Bearer {RENDER_API_KEY}", "Content-Type": "application/json"}
    
    if svc_type == "web":
        payload = {
            "name": name,
            "type": "web_service",
            "envSpecId": "docker",
            "repo": GITHUB_REPO_URL,
            "branch": "main",
            "buildCommand": "",
            "startCommand": "",
            "plan": "starter",
            "envVars": []
        }
    elif svc_type == "static":
        payload = {
            "name": name,
            "type": "static_site",
            "repo": GITHUB_REPO_URL,
            "branch": "main",
            "buildCommand": build_cmd,
            "publicPath": publish_path,
            "plan": "free",
            "envVars": [
                {"key": "VITE_API_URL", "value": ""}  # Will be filled later
            ]
        }
    
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code == 201:
        service = resp.json()
        return service.get("service", {}).get("id"), service
    else:
        print(f"Failed to create {name}: {resp.status_code} {resp.text}")
        return None, None

def get_service_info(service_id):
    """Get service details by ID."""
    url = f"https://api.render.com/v1/services/{service_id}"
    headers = {"Authorization": f"Bearer {RENDER_API_KEY}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json().get("service", {})
    return None

def add_github_secret(github_token, repo_owner, repo_name, secret_name, secret_value):
    """Add a GitHub secret to a repository."""
    import base64
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    
    # Get public key for repo
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/public-key"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to get public key: {resp.status_code} {resp.text}")
        return False
    
    key_data = resp.json()
    key_id = key_data.get("key_id")
    public_key = key_data.get("key")
    
    # Encrypt secret
    from nacl import public, utils
    pk = public.PublicKey(public_key, encoder=serialization.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(secret_value.encode())
    encrypted_value = base64.b64encode(sealed).decode()
    
    # Create/update secret
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/{secret_name}"
    payload = {"encrypted_value": encrypted_value, "key_id": key_id}
    resp = requests.put(url, json=payload, headers=headers)
    return resp.status_code in [201, 204]

def main():
    print("=" * 60)
    print("YouTube Downloader: Render Auto-Deploy Setup")
    print("=" * 60)
    
    # Get GitHub repo info
    global GITHUB_REPO_URL
    github_username = input("\nGitHub username: ").strip()
    github_repo = input("GitHub repo name (e.g., yt-downloader): ").strip()
    github_token = input("GitHub Personal Access Token (PAT): ").strip()
    
    GITHUB_REPO_URL = f"https://github.com/{github_username}/{github_repo}"
    
    print(f"\n📌 Using Render API key: {RENDER_API_KEY[:20]}...")
    print(f"📌 GitHub repo: {GITHUB_REPO_URL}")
    
    # Step 1: Create backend service
    print("\n▶ Creating backend service on Render...")
    backend_id, backend_svc = create_render_service(
        name="yt-downloader-backend",
        svc_type="web",
        dockerfile_path="backend/Dockerfile"
    )
    if not backend_id:
        print("❌ Failed to create backend service. Check API key and repo access.")
        return
    print(f"✓ Backend service created: {backend_id}")
    
    # Step 2: Create frontend service
    print("\n▶ Creating frontend service on Render...")
    frontend_id, frontend_svc = create_render_service(
        name="yt-downloader-frontend",
        svc_type="static",
        build_cmd="cd frontend && npm ci && npm run build",
        publish_path="frontend/dist"
    )
    if not frontend_id:
        print("❌ Failed to create frontend service.")
        return
    print(f"✓ Frontend service created: {frontend_id}")
    
    # Step 3: Wait a bit for services to initialize
    print("\n⏳ Waiting for services to initialize (30s)...")
    time.sleep(30)
    
    # Step 4: Get service URLs
    print("\n▶ Fetching service details...")
    backend_info = get_service_info(backend_id)
    frontend_info = get_service_info(frontend_id)
    
    backend_url = backend_info.get("serviceDetails", {}).get("url") if backend_info else None
    frontend_url = frontend_info.get("serviceDetails", {}).get("url") if frontend_info else None
    
    print(f"✓ Backend URL: {backend_url or 'pending...'}")
    print(f"✓ Frontend URL: {frontend_url or 'pending...'}")
    
    # Step 5: Add GitHub secrets
    print("\n▶ Adding GitHub secrets...")
    secrets = {
        "RENDER_API_KEY": RENDER_API_KEY,
        "RENDER_SERVICE_ID_BACKEND": backend_id,
        "RENDER_SERVICE_ID_FRONTEND": frontend_id,
    }
    
    for secret_name, secret_value in secrets.items():
        if add_github_secret(github_token, github_username, github_repo, secret_name, secret_value):
            print(f"✓ Added secret: {secret_name}")
        else:
            print(f"❌ Failed to add secret: {secret_name}")
    
    # Step 6: Trigger deploy via GitHub push
    print("\n▶ Ready to trigger deployment. Push to main to start auto-deploy:")
    print(f"   git push origin main")
    
    print("\n" + "=" * 60)
    print("✓ Setup complete!")
    print("=" * 60)
    print(f"\nBackend Service ID: {backend_id}")
    print(f"Frontend Service ID: {frontend_id}")
    print(f"\nWatch deployment at:")
    print(f"  - Render: https://dashboard.render.com")
    print(f"  - GitHub Actions: https://github.com/{github_username}/{github_repo}/actions")
    print(f"\nOnce deployed, your app will be at: {frontend_url or '(check Render dashboard)'}")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
