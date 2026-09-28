import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi

# Load environment variables
env_path = Path(__file__).resolve().parent / "test.env"
load_dotenv(env_path)

# Get MongoDB URL
MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise ValueError("MONGO_URL not found in test.env")

# Connect to MongoDB Atlas
client = MongoClient(
    MONGO_URL,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=15000
)

db = client["ps_01"]

# Test connection
try:
    client.admin.command("ping")
    print("MongoDB Atlas connected successfully!")

except Exception as e:
    print("Connection failed:", e)


from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
import bcrypt  # pip install bcrypt

users = db["users"]
counters = db["counters"]

# One-time setup: enforce unique email and unique uid
users.create_index("email", unique=True)
users.create_index("uid", unique=True)


def get_next_uid():
    """Atomically increments and returns the next uid (1, 2, 3, ...)."""
    doc = counters.find_one_and_update(
        {"_id": "user_uid"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["seq"]


def create_user(email, name, password, is_admin=False):
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    user = {
        "uid": get_next_uid(),
        "email": email.strip().lower(),
        "name": name,
        "password": hashed,      # never store plain text
        "is_admin": is_admin,
    }
    try:
        users.insert_one(user)
        return user["uid"]
    except DuplicateKeyError:
        raise ValueError("A user with this email already exists")


def verify_login(email, password):
    user = users.find_one({"email": email.strip().lower()})
    if user and bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return user
    return None


