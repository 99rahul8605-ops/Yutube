#🇳‌🇮‌🇰‌🇭‌🇮‌🇱‌
# Add your details here and then deploy by clicking on HEROKU Deploy button
import os
from pymongo import MongoClient

API_ID    = os.environ.get("API_ID", "")
API_HASH  = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "") 

#WEBHOOK = True  # Don't change this
#PORT = int(os.environ.get("PORT", 8080))  # Default to 8000 if not set

# MongoDB connection details
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://tmglcd:kI1UijMr2jJXyOXY@cluster0.unjzi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'bot_database')
MONGO_COLLECTION_NAME = os.environ.get('MONGO_COLLECTION_NAME', 'users')

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]

def save_user_id(user_id):
    """
    Saves the user ID to persistent storage.
    """
    try:
        # Example: Save to MongoDB
        db.collection.insert_one({"user_id": user_id})
        print(f"User ID {user_id} saved to the database.")
    except Exception as e:
        print(f"Error saving user ID {user_id}: {e}")
        
def remove_user_id(user_id):
    """
    Removes the user ID from persistent storage.
    """
    try:
        # Example: Remove from MongoDB
        db.collection.delete_one({"user_id": user_id})
        print(f"User ID {user_id} removed from the database.")
    except Exception as e:
        print(f"Error removing user ID {user_id}: {e}")

def get_all_user_ids():
    """
    Fetches all user IDs from persistent storage.
    """
    try:
        # Example: Fetch from MongoDB
        user_ids = db.collection.find({}, {"_id": 0, "user_id": 1})
        return [user["user_id"] for user in user_ids]
    except Exception as e:
        print(f"Error fetching user IDs: {e}")
        return []
        
# Example usage
if __name__ == "__main__":
    save_user_id(123456789)
    print(get_all_user_ids())
