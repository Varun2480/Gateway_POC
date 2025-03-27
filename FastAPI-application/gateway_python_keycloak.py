from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakAuthenticationError
from pydantic import BaseModel
from typing import Optional, List
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()

# Keycloak Configuration (replace with your actual values)
KEYCLOAK_SERVER_URL = "http://localhost:8080/auth/"
KEYCLOAK_REALM_NAME = "myrealm"
KEYCLOAK_CLIENT_ID = "my-fastapi-client"
KEYCLOAK_CLIENT_SECRET = "your-client-secret"
KEYCLOAK_SSL_VERIFY = False

keycloak_openid = KeycloakOpenID(
    server_url=KEYCLOAK_SERVER_URL,
    realm_name=KEYCLOAK_REALM_NAME,
    client_id=KEYCLOAK_CLIENT_ID,
    client_secret_key=KEYCLOAK_CLIENT_SECRET,
    verify=KEYCLOAK_SSL_VERIFY,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

# New Restaurant Models
class Restaurant(BaseModel):
    id: int
    name: str
    cuisine: str
    rating: float

# Restaurant Data (replace with your database or data source)
restaurants_data = [
    Restaurant(id=1, name="Italian Delight", cuisine="Italian", rating=4.5),
    Restaurant(id=2, name="Spicy Curry House", cuisine="Indian", rating=4.2),
    Restaurant(id=3, name="Sushi Heaven", cuisine="Japanese", rating=4.8),
]

# Restaurant API Endpoint (protected)
@app.get("/restaurants", response_model=List[Restaurant])
async def get_restaurants(current_user: User = Depends(get_current_user)):
    """Returns a list of restaurants."""
    return restaurants_data

@app.post("/token", response_model=Token)
async def login(username: str, password: str):
    try:
        token = keycloak_openid.token(username, password)
        return Token(access_token=token["access_token"], token_type=token["token_type"])
    except KeycloakAuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        user_info = keycloak_openid.decode_token(token)
        return User(
            username=user_info["preferred_username"],
            email=user_info.get("email"),
            first_name=user_info.get("given_name"),
            last_name=user_info.get("family_name"),
        )
    except Exception as e:
        print(f"Token decoding error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
  return {"message": f"Hello, {current_user.username}! This is a protected route."}

@app.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    try:
        token = keycloak_openid.refresh_token(refresh_token)
        return Token(access_token=token["access_token"], token_type=token["token_type"])
    except Exception as e:
        print(f"Refresh token error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token",
        )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
        headers=exc.headers,
    )