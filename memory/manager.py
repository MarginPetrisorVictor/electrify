import os
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

class MemoryManager:
    def __init__(self):
        # Assumes local MongoDB instances by default
        mongo_uri = os.getenv("MONGO_URI", os.getenv("MONGO_CONN_STRING"))
        self.client = MongoClient(mongo_uri)
        self.db = self.client["electrify_memory"]
        self.sessions = self.db["sessions"]

    def get_all_sessions(self):
        """Retrieve all sessions ordered by last updated (descending)."""
        return list(self.sessions.find({}, {"_id": 1, "name": 1, "updated_at": 1}).sort("updated_at", -1))

    def create_session(self, name: str) -> str:
        """Create a new session and return its ID."""
        session_doc = {
            "name": name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "history": [],
            "artifacts": {}
        }
        result = self.sessions.insert_one(session_doc)
        return str(result.inserted_id)

    def get_session(self, session_id: str) -> dict:
        """Retrieve a full session document by its ID."""
        return self.sessions.find_one({"_id": ObjectId(session_id)})

    def save_to_session(self, session_id: str, role: str, content: str, workflow_results: dict = None):
        """Save a new chat turn in the session and optionally update workflow artifacts."""
        update_data = {
            "$push": {
                "history": {
                    "role": role, 
                    "content": content, 
                    "timestamp": datetime.utcnow()
                }
            },
            "$set": {
                "updated_at": datetime.utcnow()
            }
        }
        
        if workflow_results:
            for key, value in workflow_results.items():
                update_data["$set"][f"artifacts.{key}"] = value
                
        self.sessions.update_one({"_id": ObjectId(session_id)}, update_data)
