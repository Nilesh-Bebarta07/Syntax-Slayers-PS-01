from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv("test.env")

MONGO_URL = os.getenv("MONGO_URL")

client = MongoClient(MONGO_URL)

db = client["mydatabase"]

try:
    client.admin.command("ping")
    print("MongoDB connected successfully!")
except Exception as e:
    print("Connection failed:", e)