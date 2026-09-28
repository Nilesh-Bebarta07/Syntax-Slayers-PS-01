import re
from datetime import timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import (
    UPLOAD_DIR,
    create_complaint,
    create_session,
    create_user,
    delete_session,
    get_all_complaints,
    get_complaint,
    get_user_by_token,
    get_user_complaints,
    seed_admin,
    update_complaint,
    verify_login,
)

app = FastAPI()

# Allow the frontend page to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your frontend URL before deploying
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded photos at /uploads/<filename>
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Make sure the demo admin exists
seed_admin()

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB per photo


# ---------------------------------------------------------------
# Request models
# ---------------------------------------------------------------
class SignupBody(BaseModel):
    name: str
    email: str
    password: str


class LoginBody(BaseModel):
    email: str
    password: str


class ComplaintUpdate(BaseModel):
    status: Optional[str] = None
    department: Optional[str] = None


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def public_user(u):
    """The shape the frontend expects. Never includes the password hash."""
    return {
        "id": str(u["uid"]),
        "name": u["name"],
        "email": u["email"],
        "role": "admin" if u.get("is_admin") else "user",
    }


def public_complaint(c, request: Request):
    """The shape the frontend expects for a complaint."""
    created = c["created_at"]
    if created.tzinfo is None:  # MongoDB returns naive UTC datetimes
        created = created.replace(tzinfo=timezone.utc)

    base = str(request.base_url)  # ends with "/"
    photos = [f"{base}uploads/{name}" for name in (c.get("photos") or [])]

    return {
        "id": str(c["cid"]),
        "userId": str(c["uid"]),
        "userName": c.get("user_name", "Unknown"),
        "title": c["title"],
        "description": c["description"],
        "category": c["category"],
        "location": c["location"],
        "status": c["status"],
        "department": c.get("department", ""),
        "photo": photos[0] if photos else "",
        "photos": photos,
        "createdAt": int(created.timestamp() * 1000),  # milliseconds
    }


def get_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not logged in")
    return authorization[7:]


def current_user(token: str = Depends(get_token)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired. Log in again.")
    return user


def admin_only(user=Depends(current_user)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admins only")
    return user


# ---------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------
@app.get("/")
def home():
    return {"message": "Welcome to the Authentication System"}


@app.post("/signup")
def signup(body: SignupBody):
    name = body.name.strip()
    email = body.email.strip().lower()

    if not name:
        raise HTTPException(status_code=400, detail="Enter your full name.")
    if not re.match(r"^\S+@\S+\.\S+$", email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Use a password with at least 6 characters.")
    if len(body.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Use a password of 72 bytes or fewer.")

    try:
        # Sign-ups are always regular users (is_admin stays False)
        uid = create_user(email, name, body.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    token = create_session(uid)
    user = get_user_by_token(token)
    return {"token": token, "user": public_user(user)}


@app.post("/login")
def login(body: LoginBody):
    user = verify_login(body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email or password is incorrect. Check both and try again.",
        )
    token = create_session(user["uid"])
    return {"token": token, "user": public_user(user)}


@app.get("/me")
def me(user=Depends(current_user)):
    return public_user(user)


@app.post("/logout")
def logout(token: str = Depends(get_token)):
    delete_session(token)
    return {"message": "Logged out"}


# ---------------------------------------------------------------
# Complaint routes
# ---------------------------------------------------------------
@app.post("/complaints")
async def submit_complaint(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    description: str = Form(...),
    photos: Optional[List[UploadFile]] = File(None),
    user=Depends(current_user),
):
    """Any logged-in user. The uid comes from the token, never from the form."""
    images = []
    for f in photos or []:
        if not f.filename:
            continue  # empty file input
        if not (f.content_type or "").startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files can be uploaded.")
        data = await f.read()
        if not data:
            continue
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail="Each photo must be 5 MB or smaller.")
        images.append((data, f.filename))

    try:
        cid = create_complaint(user["uid"], title, category, location, description, images)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return public_complaint(get_complaint(cid), request)


@app.get("/complaints/mine")
def my_complaints(request: Request, user=Depends(current_user)):
    return [public_complaint(c, request) for c in get_user_complaints(user["uid"])]


@app.get("/complaints")
def all_complaints(request: Request, admin=Depends(admin_only)):
    return [public_complaint(c, request) for c in get_all_complaints()]


@app.patch("/complaints/{cid}")
def change_complaint(cid: int, body: ComplaintUpdate, request: Request, admin=Depends(admin_only)):
    try:
        updated = update_complaint(cid, body.status, body.department)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return public_complaint(updated, request)