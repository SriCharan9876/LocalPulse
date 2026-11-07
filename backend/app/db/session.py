import asyncio
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    is_mock: bool = False

db_manager = DatabaseManager()

async def connect_to_mongo():
    """Connect to MongoDB or fallback to in-memory mongomock if unavailable."""
    uri = settings.MONGODB_URI.strip()
    use_mock = False

    # Check if URI is default placeholder
    if not uri or uri.startswith("your_") or "replace_with" in uri:
        logger.warning("MONGODB_URI is unconfigured or a placeholder. Using in-memory MongoMock database.")
        use_mock = True
    else:
        try:
            logger.info(f"Attempting connection to MongoDB at {uri.split('@')[-1]}...")
            client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            # Test connection with strict 3s timeout to prevent hanging on unreachable hosts
            await asyncio.wait_for(client.admin.command('ping'), timeout=3.0)
            db_manager.client = client
            db_manager.db = client[settings.DATABASE_NAME]
            db_manager.is_mock = False
            logger.info(f"Successfully connected to MongoDB database '{settings.DATABASE_NAME}'")
        except Exception as e:
            logger.warning(f"Failed to connect to MongoDB ({e}). Falling back to in-memory MongoMock database.")
            use_mock = True

    if use_mock:
        from mongomock_motor import AsyncMongoMockClient
        db_manager.client = AsyncMongoMockClient()
        db_manager.db = db_manager.client[settings.DATABASE_NAME]
        db_manager.is_mock = True
        logger.info("Initialized in-memory MongoMock database.")

    # Create indexes for optimal queries
    await create_indexes()

async def create_indexes():
    """Create indexes for frequent merchant, product, and date queries."""
    if db_manager.db is None:
        return
    db = db_manager.db
    try:
        # Merchants
        await db.merchants.create_index("merchant_id", unique=True)
        await db.merchants.create_index("email", unique=True)

        # Products
        await db.products.create_index([("merchant_id", 1), ("product_id", 1)], unique=True)
        await db.products.create_index([("merchant_id", 1), ("category", 1)])

        # Sales
        await db.sales.create_index([("merchant_id", 1), ("product_id", 1), ("date", 1)], unique=True)
        await db.sales.create_index([("merchant_id", 1), ("date", 1)])

        # Inventory movements
        await db.inventory_movements.create_index([("merchant_id", 1), ("product_id", 1), ("created_at", -1)])

        # Collaborations
        await db.collaborations.create_index("proposal_id", unique=True)
        await db.collaborations.create_index([("initiator_merchant_id", 1), ("partner_merchant_id", 1)])

        # Campaigns
        await db.campaigns.create_index("campaign_id", unique=True)
        await db.campaigns.create_index([("merchant_id", 1), ("status", 1)])

        # Redemptions
        await db.campaign_redemptions.create_index([("campaign_id", 1), ("redeemed_at", -1)])

        # Copilot conversations
        await db.copilot_conversations.create_index([("merchant_id", 1), ("updated_at", -1)])

        logger.info("MongoDB indexes verified successfully.")
    except Exception as e:
        logger.warning(f"Index creation notice: {e}")

async def close_mongo_connection():
    """Close MongoDB connection gracefully."""
    if db_manager.client:
        db_manager.client.close()
        logger.info("MongoDB connection closed.")

async def get_database() -> AsyncIOMotorDatabase:
    """Dependency for obtaining the database instance."""
    if db_manager.db is None:
        await connect_to_mongo()
    return db_manager.db
