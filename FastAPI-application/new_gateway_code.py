from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWT, PyJWKClient
import os
from urllib.parse import urlencode
import requests

app = FastAPI()


# Keycloak Configuration (using environment variables)
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:30000")
KEYCLOAK_REALM_NAME = os.getenv("KEYCLOAK_REALM_NAME", "gateway")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "gatewaypoc")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "71C95mDIu4ZPeDoL9Yggs65N5frIG4CG")
KEYCLOAK_SSL_VERIFY = False  # Change to True in production!
KEYCLAK_JWKS_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM_NAME}/protocol/openid-connect/certs"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM_NAME}/protocol/openid-connect/token"
KEYCLOAK_AUTHORIZE_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM_NAME}/protocol/openid-connect/auth"
CALL_BACK_URL = os.getenv("CALL_BACK_URL", "http://localhost:8000/callback")
KEYCLOAK_USERINFO_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM_NAME}/protocol/openid-connect/userinfo"

# In-memory token storage (for demonstration purposes only)
token_storage = {}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

jwt_client = PyJWKClient(KEYCLAK_JWKS_URL)
jwt_instance = PyJWT()

def get_current_user(token: str):
    """
    Verifies the JWT token and extracts user information.
    """
    # import pdb; pdb.set_trace()
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(KEYCLOAK_USERINFO_URL, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting user info from Keycloak: {e}")
        return None

def initiate_login():
    """
    Constructs the Keycloak authorization URL and returns it.
    """
    params = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "response_type": "code",
        "scope": "openid",
        "redirect_uri": CALL_BACK_URL,
    }
    auth_url = f"{KEYCLOAK_AUTHORIZE_URL}?{urlencode(params)}"
    return auth_url

def exchange_code_for_token(code: str):
    """
    Exchanges the authorization code for an access token.
    """
    data = {
        "grant_type": "authorization_code",
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET,
        "code": code,
        "redirect_uri": CALL_BACK_URL,
    }
    try:
        response = requests.post(KEYCLOAK_TOKEN_URL, data=data, verify=KEYCLOAK_SSL_VERIFY)
        response.raise_for_status()
        token_data = response.json()
        return Token(**token_data)
    except requests.exceptions.RequestException as e:
        print(f"Token request error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to exchange code for token")

def refresh_access_token(refresh_token: str):
    """
    Exchanges the refresh token for a new access token and refresh token.
    """
    data = {
        "grant_type": "refresh_token",
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    try:
        response = requests.post(KEYCLOAK_TOKEN_URL, data=data, verify=KEYCLOAK_SSL_VERIFY)
        response.raise_for_status()
        token_data = response.json()
        return Token(**token_data)
    except requests.exceptions.RequestException as e:
        print(f"Refresh token error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")
    

@app.get("/login")
async def login():
    """
    Redirects the user to Keycloak for authentication.
    """
    import pdb; pdb.set_trace()
    auth_url = initiate_login()
    # return RedirectResponse(url="http://localhost:30000")
    return RedirectResponse(url=auth_url)

@app.get("/callback", response_model=Token)
async def callback(code: str = Query(...)):
    """
    Handles the callback from Keycloak after successful authentication.
    Exchanges the authorization code for an access token and stores it.
    """
    # import pdb; pdb.set_trace()
    token = exchange_code_for_token(code)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication Failed")
    token_storage["tokens"] = {
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
    }  # Store the token in memory
    
    # return token
    return RedirectResponse(url="/protected")

@app.get("/refresh", response_model=Token)
async def refresh(request: Request):
    """
    Refreshes the access token using the refresh token.
    """
    tokens = token_storage.get("tokens")
    if not tokens or "refresh_token" not in tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated or no refresh token found")

    refresh_token = tokens["refresh_token"]
    new_token = refresh_access_token(refresh_token)
    token_storage["tokens"] = {
        "access_token": new_token.access_token,
        "refresh_token": new_token.refresh_token,
    }
    return new_token

@app.get("/protected")
async def protected_route(request: Request):
    """
    A protected route that demonstrates token validation.
    """
    import pdb; pdb.set_trace()
    tokens = token_storage.get("tokens")
    if not tokens or "access_token" not in tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    access_token = tokens["access_token"]
    user = get_current_user(access_token)
    return {"message": f"Hello, {user}! This is a protected route."}
    # return {"message": f"Hello, This is a protected route."}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
        headers=exc.headers,
    )
