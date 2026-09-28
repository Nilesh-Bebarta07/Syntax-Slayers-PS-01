import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError

# ---------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------
env_path = Path(__file__).resolve().parent / "test.env"
load_dotenv(env_path)

MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise ValueError("MONGO_URL not found in test.env")

# ---------------------------------------------------------------
# Connect to MongoDB Atlas
# ---------------------------------------------------------------
client = MongoClient(
    MONGO_URL,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=15000,
)

db = client["ps_01"]

try:
    client.admin.command("ping")
    print("MongoDB Atlas connected successfully!")
except Exception as e:
    print("Connection failed:", e)

# ---------------------------------------------------------------
# Collections
# ---------------------------------------------------------------
users = db["users"]
counters = db["counters"]
sessions = db["sessions"]
complaints = db["complaints"]

SESSION_DAYS = 7

# ---------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------
users.create_index("email", unique=True)
users.create_index("uid", unique=True)

sessions.create_index("token", unique=True)
sessions.create_index(
    "created_at",
    expireAfterSeconds=SESSION_DAYS * 24 * 60 * 60,
)

complaints.create_index("cid", unique=True)
complaints.create_index("uid")

# ---------------------------------------------------------------
# Allowed values
# ---------------------------------------------------------------
CATEGORIES = [
    "Electrical",
    "Water & Plumbing",
    "Cleanliness",
    "Network & IT",
    "Furniture & Equipment",
    "Other",
]

STATUSES = [
    "Submitted",
    "Assigned",
    "In progress",
    "Resolved",
]

DEPARTMENTS = [
    "Electrical",
    "Plumbing",
    "Housekeeping",
    "IT Services",
    "Maintenance",
]

# ---------------------------------------------------------------
# Upload configuration
# ---------------------------------------------------------------
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


# ---------------------------------------------------------------
# Counters
# ---------------------------------------------------------------
def get_next_id(name):
    """Atomically increment and return the next ID."""
    doc = counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["seq"]


def get_next_uid():
    """Atomically return the next user UID."""
    return get_next_id("user_uid")


# ---------------------------------------------------------------
# Users
# ---------------------------------------------------------------
def create_user(email, name, password, is_admin=False):
    """Create a user and return their UID."""
    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    )

    user = {
        "uid": get_next_uid(),
        "email": email.strip().lower(),
        "name": name.strip(),
        "password": hashed,
        "is_admin": is_admin,
    }

    try:
        users.insert_one(user)
        return user["uid"]
    except DuplicateKeyError:
        raise ValueError("A user with this email already exists")


def verify_login(email, password):
    """Return the user if credentials are valid, otherwise None."""
    user = users.find_one(
        {"email": email.strip().lower()}
    )

    if not user:
        return None

    try:
        if bcrypt.checkpw(
            password.encode("utf-8"),
            user["password"],
        ):
            return user
    except (ValueError, TypeError):
        # bcrypt has a 72-byte password limit.
        pass

    return None


def get_user_by_uid(uid):
    """Return a user by UID."""
    return users.find_one({"uid": uid})


def seed_admin():
    """Create the demo admin once. Safe to call on every startup."""
    email = "admin@campus.edu"

    if users.find_one({"email": email}):
        return

    password = os.getenv("ADMIN_PASSWORD", "admin123")

    try:
        create_user(
            email,
            "Campus Admin",
            password,
            is_admin=True,
        )
        print("Demo admin created:", email)
    except ValueError:
        # Another process may have created it first.
        pass


# ---------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------
def create_session(uid):
    """Create a login token for a user."""
    token = secrets.token_hex(24)

    sessions.insert_one(
        {
            "token": token,
            "uid": uid,
            "created_at": datetime.now(timezone.utc),
        }
    )

    return token


def get_user_by_token(token):
    """Return the user associated with a valid session token."""
    if not token:
        return None

    session = sessions.find_one({"token": token})

    if not session:
        return None

    return get_user_by_uid(session["uid"])


def delete_session(token):
    """Delete a login session."""
    sessions.delete_one({"token": token})


# ---------------------------------------------------------------
# Complaints - Images
# ---------------------------------------------------------------
def save_image(file_bytes, original_filename):
    """Save an image to uploads/ and return its stored filename."""
    ext = Path(original_filename).suffix.lower()

    if ext not in ALLOWED_EXT:
        raise ValueError(
            "Photos must be .jpg, .jpeg, .png or .webp files."
        )

    filename = f"{uuid.uuid4().hex}{ext}"

    (UPLOAD_DIR / filename).write_bytes(file_bytes)

    return filename


# ---------------------------------------------------------------
# Complaints - Create
# ---------------------------------------------------------------
def create_complaint(
    uid,
    title,
    category,
    location,
    description,
    images=None,
):
    """
    Create a complaint.

    images:
        List of (file_bytes, original_filename) tuples, or None.

    Returns:
        New complaint ID (cid).
    """

    user = users.find_one({"uid": uid})

    if not user:
        raise ValueError("User does not exist")

    title = title.strip()
    location = location.strip()
    description = description.strip()

    if not title or not location or not description:
        raise ValueError(
            "Fill in the title, location and description."
        )

    if category not in CATEGORIES:
        raise ValueError("Choose a valid category.")

    images = images or []

    # Validate all files BEFORE saving any of them.
    for _, filename in images:
        if Path(filename).suffix.lower() not in ALLOWED_EXT:
            raise ValueError(
                "Photos must be .jpg, .jpeg, .png or .webp files."
            )

    photo_names = [
        save_image(data, filename)
        for data, filename in images
    ]

    now = datetime.now(timezone.utc)

    complaint = {
        "cid": get_next_id("complaint_cid"),
        "uid": uid,
        "user_name": user["name"],
        "title": title,
        "category": category,
        "location": location,
        "description": description,
        "photos": photo_names,
        "status": "Submitted",
        "department": "",
        "created_at": now,
        "updated_at": now,
    }

    complaints.insert_one(complaint)

    return complaint["cid"]


# ---------------------------------------------------------------
# Complaints - Read
# ---------------------------------------------------------------
def get_complaint(cid):
    """Return a complaint by CID."""
    return complaints.find_one(
        {"cid": cid},
        {"_id": 0},
    )


def get_user_complaints(uid):
    """Return all complaints belonging to a user."""
    return list(
        complaints.find(
            {"uid": uid},
            {"_id": 0},
        ).sort(
            "created_at",
            -1,
        )
    )


def get_all_complaints():
    """Return all complaints, newest first."""
    return list(
        complaints.find(
            {},
            {"_id": 0},
        ).sort(
            "created_at",
            -1,
        )
    )


# ---------------------------------------------------------------
# Complaints - Update
# ---------------------------------------------------------------
def update_complaint(
    cid,
    status=None,
    department=None,
):
    """
    Update complaint status and/or department.

    Returns:
        Updated complaint, or None if complaint does not exist.

    Raises:
        ValueError for invalid values or empty updates.
    """

    complaint = complaints.find_one({"cid": cid})

    if not complaint:
        return None

    changes = {}

    if status is not None:
        if status not in STATUSES:
            raise ValueError("Invalid status.")

        changes["status"] = status

    if department is not None:
        if (
            department != ""
            and department not in DEPARTMENTS
        ):
            raise ValueError("Invalid department.")

        changes["department"] = department

        # Assigning a department automatically moves
        # a newly submitted complaint to Assigned.
        if (
            department
            and status is None
            and complaint.get("status") == "Submitted"
        ):
            changes["status"] = "Assigned"

    if not changes:
        raise ValueError("Nothing to update.")

    changes["updated_at"] = datetime.now(timezone.utc)

    return complaints.find_one_and_update(
        {"cid": cid},
        {"$set": changes},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
