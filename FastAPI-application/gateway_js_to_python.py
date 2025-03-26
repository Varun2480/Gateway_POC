from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
import os
import requests
from typing import Optional
from urllib.parse import urlencode
from datetime import datetime, timedelta

app = FastAPI(
    title="API Gateway",
    description="API Gateway with Keycloak Authentication",
    version="1.0.0",
    middleware=[
        Middleware(SessionMiddleware, secret_key="your-secret-key")  # Replace with a strong secret key
    ]
)

# Keycloak Configuration (Environment Variables)
KEYCLOAK_BASE_URL = os.environ.get("KEYCLOAK_BASE_URL", "http://localhost:8080")  # Keycloak base URL
REALM = os.environ.get("REALM", "your-realm")  # Your Keycloak realm
CLIENT_ID = os.environ.get("CLIENT_ID", "your-client-id")  # Your Keycloak client ID
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "your-client-secret")  # Your Keycloak client secret
CALLBACK_URL = os.environ.get("CALLBACK_URL", "http://localhost:3000/callback")  # Redirect URI after login
UI_URL = os.environ.get("UI_URL", "http://localhost:4200")  # Your UI URL
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")  # Your backend api url
PORT = int(os.environ.get("PORT", 3000))

# Keycloak Endpoints
KEYCLOAK_AUTH_URL = f"{KEYCLOAK_BASE_URL}/realms/{REALM}/protocol/openid-connect/auth"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_BASE_URL}/realms/{REALM}/protocol/openid-connect/token"

# Security Scheme
security = HTTPBearer()


def is_token_valid(request: Request) -> bool:
    """Checks if the token in the session is valid."""
    token_data = request.session.get("token_data")
    if not token_data:
        return False
    expiry = token_data.get("expiry")
    if not expiry:
        return False
    return datetime.now() < expiry


async def refresh_token(request: Request) -> bool:
    """Refreshes the access token using the refresh token."""
    refresh_token_val = request.session.get("refresh_token")
    if not refresh_token_val:
        print("No refresh token available.")
        return False
    try:
        payload = {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token_val,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(KEYCLOAK_TOKEN_URL, data=payload, headers=headers)
        response.raise_for_status()
        token_data = response.json()
        request.session["token_data"] = {
            "access_token": token_data["access_token"],
            "expiry": datetime.now() + timedelta(seconds=token_data["expires_in"]),
        }
        request.session["refresh_token"] = token_data["refresh_token"]
        print("Token refreshed successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error refreshing token: {e}")
        return False


async def authenticate_user(request: Request, token: HTTPAuthorizationCredentials = Depends(security)):
    """Authenticates the user by validating the access token."""
    if not is_token_valid(request):
        if not await refresh_token(request):
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    access_token = request.session["token_data"]["access_token"]
    return access_token


@app.middleware("http")
async def check_token_middleware(request: Request, call_next):
    """Middleware to check token validity and redirect if needed."""
    if request.url.path.startswith("/api/backend"):
        if not is_token_valid(request):
            print("API request but token invalid, returning 401")
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        response = await call_next(request)
        return response

    if request.url.path == "/callback":
        response = await call_next(request)
        return response

    if not is_token_valid(request):
        print("Token expired, attempting refresh...")
        if not await refresh_token(request):
            print("Redirecting to Keycloak for authentication...")
            auth_url = f"{KEYCLOAK_AUTH_URL}?client_id={CLIENT_ID}&response_type=code&redirect_uri={CALLBACK_URL}"
            return RedirectResponse(url=auth_url)
    
    response = await call_next(request)
    return response


@app.get("/callback")
async def callback(request: Request, code: str):
    """Handles the redirect from Keycloak after successful authentication."""
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing")

    try:
        payload = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": CALLBACK_URL,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(KEYCLOAK_TOKEN_URL, data=payload, headers=headers)
        response.raise_for_status()
        token_data = response.json()

        request.session["token_data"] = {
            "access_token": token_data["access_token"],
            "expiry": datetime.now() + timedelta(seconds=token_data["expires_in"]),
        }
        request.session["refresh_token"] = token_data["refresh_token"]
        print("User authenticated successfully. Redirecting to UI.")
        return RedirectResponse(url="/")
    except requests.exceptions.RequestException as e:
        print(f"Token exchange failed: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@app.get("/api/backend/{path:path}")
async def proxy_backend_request(path: str, request: Request, access_token: str = Depends(authenticate_user)):
    """Proxies API requests to the backend."""
    target_url = f"{BACKEND_URL}/{path}"
    try:
        headers = dict(request.headers)
        headers["Authorization"] = f"Bearer {access_token}"
        del headers["host"]
        response = requests.request(method=request.method, url=target_url, headers=headers, data=await request.body())
        response.raise_for_status()
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except requests.exceptions.RequestException as e:
        print(f"Proxy Error: {e}")
        raise HTTPException(status_code=500, detail=f"Proxy Error: {e}")

@app.get("/{path:path}")
async def proxy_ui_request(path: str, request: Request):
    """Proxies requests to the UI."""
    target_url = f"{UI_URL}/{path}"
    try:
        response = requests.get(target_url)
        response.raise_for_status()
        return JSONResponse(content=response.content, status_code=response.status_code)
    except requests.exceptions.RequestException as e:
        print(f"Proxy Error: {e}")
        raise HTTPException(status_code=500, detail=f"Proxy Error: {e}")

@app.get("/")
async def root():
    return RedirectResponse(url=f"{UI_URL}/")
