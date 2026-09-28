
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Temporary user storage
users = {
    "admin": "password"
}


# Request model
class User(BaseModel):
    username: str
    password: str


# Home route
@app.get("/")
def home():
    return {"message": "Welcome to the Authentication System"}


# LOGIN
@app.post("/login")
def login(user: User):

    if user.username in users and users[user.username] == user.password:
        return {
            "message": f"Welcome back, {user.username}!"
        }

    raise HTTPException(
        status_code=401,
        detail="Invalid username or password"
    )


# SIGNUP
@app.post("/signup")
def signup(user: User):

    if user.username in users:
        raise HTTPException(
            status_code=409,
            detail="Username already exists"
        )

    users[user.username] = user.password

    return {
        "message": f"User {user.username} registered successfully!"
    }

