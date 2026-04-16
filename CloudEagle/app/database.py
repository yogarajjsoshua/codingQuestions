"""MongoDB database connection and management."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import structlog
from app.config import settings

logger = structlog.get_logger()


class MongoDB:
    """MongoDB connection manager using Motor (async driver)."""
    
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls):
        """Establish MongoDB connection and setup indexes."""
        try:
            logger.info("mongodb_connecting", connection_string=settings.mongodb_connection_string[:20] + "...")
            
            cls.client = AsyncIOMotorClient(
                settings.mongodb_connection_string,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000
            )
            
            cls.database = cls.client[settings.mongodb_database_name]
            
            # Test connection
            await cls.client.admin.command('ping')
            
            # Setup indexes for performance
            await cls._setup_indexes()
            
            logger.info("mongodb_connected", database=settings.mongodb_database_name)
            
        except Exception as e:
            logger.error("mongodb_connection_error", error=str(e))
            raise
    
    @classmethod
    async def _setup_indexes(cls):
        """Create indexes for efficient queries."""
        collection = cls.database[settings.context_collection_name]
        
        # Index on session_id for fast lookups
        await collection.create_index("session_id", unique=True)
        
        # Index on last_accessed for cleanup queries
        await collection.create_index("last_accessed")
        
        # Compound index for session + timestamp queries
        await collection.create_index([
            ("session_id", 1),
            ("conversations.timestamp", -1)
        ])
        
        logger.info("mongodb_indexes_created")
    
    @classmethod
    async def close(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            logger.info("mongodb_disconnected")
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if cls.database is None:
            raise RuntimeError("Database not initialized. Call connect() first.")
        return cls.database
    
    @classmethod
    def get_collection(cls, collection_name: str):
        """Get a specific collection."""
        return cls.get_database()[collection_name]
