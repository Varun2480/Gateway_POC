from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
import os
import requests
from typing import Optional

app = FastAPI(
    title="API Gateway",
    description="API Gateway with Keycloak Authentication",
    version="1.0.0",
    middleware=[
        Middleware(SessionMiddleware, secret_key="your-secret-key")  # Replace with a strong secret key
    ]
)

# Keycloak Configuration (Environment Variables)
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")  # Keycloak base URL
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "your-realm")  # Your Keycloak realm
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "your-client-id")  # Your Keycloak client ID
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "your-client-secret") # Your Keycloak client secret
GATEWAY_REDIRECT_URI = os.environ.get("GATEWAY_REDIRECT_URI", "http://localhost:8000/callback")  # Redirect URI after login
TARGET_API_URL = os.environ.get("TARGET_API_URL", "http://localhost:8001") # Your backend api url

# Security Scheme
security = HTTPBearer()

# Keycloak Endpoints
KEYCLOAK_AUTH_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
KEYCLOAK_USERINFO_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo"

def get_token_from_keycloak(code: str) -> Optional[str]:
    """
    Exchanges the authorization code for an access token from Keycloak.
    """
    try:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": GATEWAY_REDIRECT_URI,
            "client_id": KEYCLOAK_CLIENT_ID,
            "client_secret": KEYCLOAK_CLIENT_SECRET,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(KEYCLOAK_TOKEN_URL, data=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        token_data = response.json()
        return token_data.get("access_token")
    except requests.exceptions.RequestException as e:
        print(f"Error getting token from Keycloak: {e}")
        return None

def get_user_info(access_token: str) -> Optional[dict]:
    """
    Retrieves user information from Keycloak using the access token.
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(KEYCLOAK_USERINFO_URL, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting user info from Keycloak: {e}")
        return None

async def authenticate_user(request: Request, token: HTTPAuthorizationCredentials = Depends(security)):
    """
    Authenticates the user by validating the access token with Keycloak.
    """
    access_token = token.credentials
    user_info = get_user_info(access_token)

    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")

    request.session["user_info"] = user_info
    return user_info

@app.get("/login")
async def login(request: Request):
    """
    Redirects the user to Keycloak for authentication.
    """
    auth_url = f"{KEYCLOAK_AUTH_URL}?client_id={KEYCLOAK_CLIENT_ID}&redirect_uri={GATEWAY_REDIRECT_URI}&response_type=code&scope=openid"
    return RedirectResponse(url=auth_url)

@app.get("/callback")
async def callback(request: Request, code: str):
    """
    Handles the redirect from Keycloak after successful authentication.
    """
    access_token = get_token_from_keycloak(code)
    if not access_token:
        raise HTTPException(status_code=401, detail="Authentication failed")

    user_info = get_user_info(access_token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Authentication failed")

    request.session["user_info"] = user_info
    return RedirectResponse(url="/protected")  # Redirect to a protected route

@app.get("/protected")
async def protected(request: Request, user_info: dict = Depends(authenticate_user)):
    """
    A protected route that requires authentication.
    """
    return {"message": "Hello, authenticated user!", "user": user_info}

@app.get("/proxy/{path:path}")
async def proxy_request(path: str, request: Request, user_info: dict = Depends(authenticate_user)):
    """
    Proxy all requests to the target API after authentication.
    """
    target_url = f"{TARGET_API_URL}/{path}"
    try:
        headers = dict(request.headers)
        del headers["host"]
        response = requests.get(target_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error proxying request: {e}")

# Add other proxy methods like POST, PUT, DELETE as needed.