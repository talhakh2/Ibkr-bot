from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
mongo_uri = os.getenv("MONGO_URI")

# Ensure MONGO_URI is set
if not mongo_uri:
    raise ValueError("MONGO_URI is missing from environment variables.")

# Establish connection when the server starts
try:
    mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)  # 5-second timeout
    mongo_client.server_info()  # Test connection
    print("Connected to MongoDB successfully!")
except Exception as e:
    raise ConnectionError(f"Failed to connect to MongoDB: {e}")

# Get database and collection
mongo_db = mongo_client["trade_activity"]
trades_collection = mongo_db["trades"]  # This is the collection to be used elsewhere