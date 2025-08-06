"""Database configuration and connection management."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from pymongo import MongoClient
    from pymongo.database import Database
except ImportError:
    print("PyMongo not installed. Please run: pip install pymongo")
    raise


class DatabaseConfig:
    """Configuration class for database settings."""
    
    def __init__(self):
        self.mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.target_db_name = os.getenv("TARGET_DB_NAME", "normalize_data")
    
    def get_connection_string(self) -> str:
        """Get MongoDB connection string."""
        return self.mongodb_uri
    
    def get_database_name(self) -> str:
        """Get target database name."""
        return self.target_db_name


class DatabaseConnection:
    """Database connection manager."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._client: Optional[MongoClient] = None
        self._database: Optional[Database] = None
    
    def connect(self) -> Database:
        """Establish connection to MongoDB database."""
        if self._client is None:
            self._client = MongoClient(self.config.get_connection_string())
        
        if self._database is None:
            if self._client is not None:
                self._database = self._client[self.config.get_database_name()]
        
        if self._database is None:
            raise RuntimeError("Failed to establish database connection")
            
        return self._database
    
    def close(self):
        """Close database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
    
    def __enter__(self):
        """Context manager entry."""
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
