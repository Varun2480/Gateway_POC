from fastapi import FastAPI, Depends, Form, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from fastapi.security import OAuth2PasswordBearer
import requests
from jwt import PyJWT, PyJWKClient
import os


app = FastAPI()

# Keycloak Configuration (replace with your actual values)
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:30000/auth")
KEYCLOAK_REALM_NAME = os.getenv("KEYCLOAK_REALM_NAME", "gateway")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "gatewaypoc")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "XOeXRDP271rWhm85UVYgT7FBHEqf6tU6")
KEYCLOAK_SSL_VERIFY = False # Change to True in production!
KEYCLAK_JWKS_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM_NAME}/protocol/openid-connect/certs"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM_NAME}/protocol/openid-connect/token"
CALL_BACK_URL = f"/callback"

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

class Restaurant(BaseModel):
    id: int
    name: str
    cuisine: str
    rating: float

class TokenRequest(BaseModel):
    username: str = Field(..., description="Username for login")
    password: str = Field(..., description="Password for login")

restaurants_data = [
    Restaurant(id=1, name="Italian Delight", cuisine="Italian", rating=4.5),
    Restaurant(id=2, name="Spicy Curry House", cuisine="Indian", rating=4.2),
    Restaurant(id=3, name="Sushi Heaven", cuisine="Japanese", rating=4.8),
]

jwt_client = PyJWKClient(KEYCLAK_JWKS_URL)
jwt_instance = PyJWT()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        signing_key = jwt_client.get_signing_key_from_jwt(token).key
        payload = jwt_instance.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=KEYCLOAK_CLIENT_ID,
            issuer=f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM_NAME}",
        )
        return User(
            username=payload["preferred_username"],
            email=payload.get("email"),
            first_name=payload.get("given_name"),
            last_name=payload.get("family_name"),
        )
    except Exception as e:
        print(f"Token verification error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@app.post("/token", response_model=Token)
async def login(token_request: TokenRequest):
    """
    curl -H "Content-Type: application/json" -X POST http://localhost:8000/token -d "{\"username\":\"varun\",\"password\":\"varun\"}"

    """
    data = {
        "grant_type": "autorization_code",
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET,
        "code": code
        "redirect_uri": CALL_BACK_URL,
    }
    try:
        response = requests.post(KEYCLOAK_TOKEN_URL, data=data, verify=KEYCLOAK_SSL_VERIFY)
        response.raise_for_status()
        token_data = response.json()
        return Token(**token_data)
    except requests.exceptions.RequestException as e:
        print(f"Token request error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

@app.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
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

@app.get("/restaurants", response_model=List[Restaurant])
async def get_restaurants(current_user: User = Depends(get_current_user)):
    return restaurants_data

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello, {current_user.username}! This is a protected route."}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
        headers=exc.headers,
    )