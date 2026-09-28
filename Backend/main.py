import hashlib, os, secrets
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Allow the frontend page to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to your frontend URL later
    allow_methods=["*"],
    allow_headers=["*"],
)

def hash_pw(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000).hex()

users = {}      # email -> user record
sessions = {}   # token -> email

def add_user(name, email, password, role):
    salt = os.urandom(16)
    users[email] = {
        "id": f"u_{len(users) + 1}",
        "name": name,
        "email": email,
        "role": role,
        "salt": salt,
        "hash": hash_pw(password, salt),
    }

add_user("Campus Admin", "admin@campus.edu", "admin123", "admin")

def public(u):
    return {"id": u["id"], "name": u["name"], "email": u["email"], "role": u["role"]}

class SignupBody(BaseModel):
    name: str
    email: str
    password: str

class LoginBody(BaseModel):
    email: str
    password: str

def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not logged in")
    email = sessions.get(authorization[7:])
    if not email:
        raise HTTPException(401, "Session expired. Log in again.")
    return users[email]

@app.get("/")
def home():
    return {"message": "Welcome to the Authentication System"}

@app.post("/signup")
def signup(body: SignupBody):
    email = body.email.strip().lower()
    if email in users:
        raise HTTPException(409, "An account with this email already exists. Log in instead.")
    if len(body.password) < 6:
        raise HTTPException(400, "Use a password with at least 6 characters.")
    add_user(body.name.strip(), email, body.password, "user")   # signup is always "user"
    token = secrets.token_hex(24)
    sessions[token] = email
    return {"token": token, "user": public(users[email])}

@app.post("/login")
def login(body: LoginBody):
    email = body.email.strip().lower()
    u = users.get(email)
    if not u or hash_pw(body.password, u["salt"]) != u["hash"]:
        raise HTTPException(401, "Email or password is incorrect. Check both and try again.")
    token = secrets.token_hex(24)
    sessions[token] = email
    return {"token": token, "user": public(u)}

@app.get("/me")
def me(user=Depends(current_user)):
    return public(user)