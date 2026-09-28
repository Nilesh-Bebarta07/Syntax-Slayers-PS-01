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


    