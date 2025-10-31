"""
MongoDB Index Creation Script

Run this script to add performance indexes to MongoDB collections.
This significantly improves query performance.

Usage:
    python add_mongodb_indexes.py
"""

from mongodb_manager import MongoDBManager
from logger import logger
import sys


def create_index_safe(collection, keys, **kwargs):
    """
    Create an index safely, handling existing indexes with different names.

    Args:
        collection: MongoDB collection
        keys: Index keys (string or list of tuples)
        **kwargs: Additional index options (unique, name, expireAfterSeconds, etc.)

    Returns:
        bool: True if index was created or already exists, False otherwise
    """
    try:
        index_name = kwargs.get('name', 'unnamed_index')

        # Get existing indexes
        existing_indexes = list(collection.list_indexes())
        existing_names = [idx['name'] for idx in existing_indexes]

        # Check if index with this name already exists
        if index_name in existing_names:
            logger.info(f"⏭️  Index '{index_name}' already exists - skipping")
            return True

        # Try to create the index
        collection.create_index(keys, **kwargs)
        return True

    except Exception as e:
        error_msg = str(e)

        # Handle "Index already exists with a different name" error
        if "Index already exists with a different name" in error_msg or "IndexOptionsConflict" in error_msg:
            # Extract the existing index name from error message
            if "different name:" in error_msg:
                existing_name = error_msg.split("different name:")[1].split(",")[0].strip()
                logger.warning(f"⚠️  Index on same field already exists as '{existing_name}' - using existing index")
                return True

        # For other errors, re-raise
        logger.error(f"❌ Failed to create index '{index_name}': {e}")
        return False


def create_indexes():
    """Create all necessary MongoDB indexes"""

    try:
        db = MongoDBManager()
        logger.info("📊 Creating MongoDB indexes...")

        created_count = 0
        skipped_count = 0
        failed_count = 0

        # ==================== USERS COLLECTION ====================
        # Index on email (unique)
        if create_index_safe(db.users, "email", unique=True, name="idx_email_unique"):
            logger.info("✅ Created index: users.email (unique)")
            created_count += 1
        else:
            failed_count += 1

        # Index on username (unique)
        if create_index_safe(db.users, "username", unique=True, name="idx_username_unique"):
            logger.info("✅ Created index: users.username (unique)")
            created_count += 1
        else:
            failed_count += 1

        # Index on role (for admin queries)
        if create_index_safe(db.users, "role", name="idx_role"):
            logger.info("✅ Created index: users.role")
            created_count += 1
        else:
            failed_count += 1

        # Index on created_at (for sorting)
        if create_index_safe(db.users, [("created_at", -1)], name="idx_created_at_desc"):
            logger.info("✅ Created index: users.created_at (desc)")
            created_count += 1
        else:
            failed_count += 1

        # ==================== FAVORITES COLLECTION ====================
        # Compound index on user_id + token_address (for quick lookups)
        if create_index_safe(db.favorites, [("user_id", 1), ("token_address", 1)], unique=True, name="idx_user_token_unique"):
            logger.info("✅ Created index: favorites.user_id + token_address (unique)")
            created_count += 1
        else:
            failed_count += 1

        # Index on user_id (for user's favorites list)
        if create_index_safe(db.favorites, "user_id", name="idx_user_id"):
            logger.info("✅ Created index: favorites.user_id")
            created_count += 1
        else:
            failed_count += 1

        # Index on token_chain (for filtering)
        if create_index_safe(db.favorites, "token_chain", name="idx_chain"):
            logger.info("✅ Created index: favorites.token_chain")
            created_count += 1
        else:
            failed_count += 1

        # Index on added_at (for sorting)
        if create_index_safe(db.favorites, [("added_at", -1)], name="idx_added_at_desc"):
            logger.info("✅ Created index: favorites.added_at (desc)")
            created_count += 1
        else:
            failed_count += 1

        # ==================== SCANNED_TOKENS COLLECTION ====================
        # Compound index on token_address + token_chain (unique)
        if create_index_safe(db.scanned_tokens, [("token_address", 1), ("token_chain", 1)], unique=True, name="idx_address_chain_unique"):
            logger.info("✅ Created index: scanned_tokens.token_address + token_chain (unique)")
            created_count += 1
        else:
            failed_count += 1

        # Index on scanned_at (for FIFO rotation and recent queries)
        if create_index_safe(db.scanned_tokens, [("scanned_at", -1)], name="idx_scanned_at_desc"):
            logger.info("✅ Created index: scanned_tokens.scanned_at (desc)")
            created_count += 1
        else:
            failed_count += 1

        # Index on token_chain (for filtering)
        if create_index_safe(db.scanned_tokens, "token_chain", name="idx_chain_scanned"):
            logger.info("✅ Created index: scanned_tokens.token_chain")
            created_count += 1
        else:
            failed_count += 1

        # Index on is_safe (for filtering safe tokens)
        if create_index_safe(db.scanned_tokens, "is_safe", name="idx_is_safe"):
            logger.info("✅ Created index: scanned_tokens.is_safe")
            created_count += 1
        else:
            failed_count += 1

        # Index on risk_score (for sorting by risk)
        if create_index_safe(db.scanned_tokens, [("risk_score", 1)], name="idx_risk_score_asc"):
            logger.info("✅ Created index: scanned_tokens.risk_score (asc)")
            created_count += 1
        else:
            failed_count += 1

        # Index on is_pump_dump_suspect (for filtering)
        if create_index_safe(db.scanned_tokens, "is_pump_dump_suspect", name="idx_pump_dump"):
            logger.info("✅ Created index: scanned_tokens.is_pump_dump_suspect")
            created_count += 1
        else:
            failed_count += 1

        # TTL Index: Auto-delete tokens older than 48 hours
        if create_index_safe(db.scanned_tokens, "scanned_at", expireAfterSeconds=172800, name="idx_ttl_48h"):
            logger.info("✅ Created TTL index: scanned_tokens.scanned_at (48h auto-delete)")
            created_count += 1
        else:
            failed_count += 1

        # ==================== SCAN_HISTORY COLLECTION ====================
        # Index on user_id (for user's scan history)
        if create_index_safe(db.scan_history, "user_id", name="idx_user_id_history"):
            logger.info("✅ Created index: scan_history.user_id")
            created_count += 1
        else:
            failed_count += 1

        # Index on scan_date (for recent scans)
        if create_index_safe(db.scan_history, [("scan_date", -1)], name="idx_scan_date_desc"):
            logger.info("✅ Created index: scan_history.scan_date (desc)")
            created_count += 1
        else:
            failed_count += 1

        # Compound index on user_id + scan_date (for user's recent scans)
        if create_index_safe(db.scan_history, [("user_id", 1), ("scan_date", -1)], name="idx_user_scan_date"):
            logger.info("✅ Created index: scan_history.user_id + scan_date")
            created_count += 1
        else:
            failed_count += 1

        # ==================== ALERTS COLLECTION ====================
        # Index on user_id (for user's alerts)
        if create_index_safe(db.alerts, "user_id", name="idx_user_id_alerts"):
            logger.info("✅ Created index: alerts.user_id")
            created_count += 1
        else:
            failed_count += 1

        # Index on is_active (for active alerts only)
        if create_index_safe(db.alerts, "is_active", name="idx_is_active"):
            logger.info("✅ Created index: alerts.is_active")
            created_count += 1
        else:
            failed_count += 1

        # Compound index on user_id + is_active (for user's active alerts)
        if create_index_safe(db.alerts, [("user_id", 1), ("is_active", 1)], name="idx_user_active_alerts"):
            logger.info("✅ Created index: alerts.user_id + is_active")
            created_count += 1
        else:
            failed_count += 1

        # Index on token_address (for alerts on specific token)
        if create_index_safe(db.alerts, "token_address", name="idx_token_address_alerts"):
            logger.info("✅ Created index: alerts.token_address")
            created_count += 1
        else:
            failed_count += 1

        # Index on created_at (for sorting)
        if create_index_safe(db.alerts, [("created_at", -1)], name="idx_created_at_alerts_desc"):
            logger.info("✅ Created index: alerts.created_at (desc)")
            created_count += 1
        else:
            failed_count += 1

        # ==================== POSITIONS COLLECTION ====================
        # Compound index on user_id + token_address (unique)
        if create_index_safe(db.positions, [("user_id", 1), ("token_address", 1)], unique=True, name="idx_user_token_position_unique"):
            logger.info("✅ Created index: positions.user_id + token_address (unique)")
            created_count += 1
        else:
            failed_count += 1

        # Index on user_id (for user's positions)
        if create_index_safe(db.positions, "user_id", name="idx_user_id_positions"):
            logger.info("✅ Created index: positions.user_id")
            created_count += 1
        else:
            failed_count += 1

        # Index on is_open (for open positions)
        if create_index_safe(db.positions, "is_open", name="idx_is_open"):
            logger.info("✅ Created index: positions.is_open")
            created_count += 1
        else:
            failed_count += 1

        # Index on entry_date (for sorting)
        if create_index_safe(db.positions, [("entry_date", -1)], name="idx_entry_date_desc"):
            logger.info("✅ Created index: positions.entry_date (desc)")
            created_count += 1
        else:
            failed_count += 1

        # ==================== TOKENS_CACHE COLLECTION ====================
        # Index on token_address (for lookups)
        if create_index_safe(db.tokens_cache, "token_address", name="idx_token_address_cache"):
            logger.info("✅ Created index: tokens_cache.token_address")
            created_count += 1
        else:
            failed_count += 1

        # Index on cached_at (for cache expiration)
        if create_index_safe(db.tokens_cache, [("cached_at", -1)], name="idx_cached_at_desc"):
            logger.info("✅ Created index: tokens_cache.cached_at (desc)")
            created_count += 1
        else:
            failed_count += 1

        # TTL Index: Auto-delete cached data older than 1 hour
        if create_index_safe(db.tokens_cache, "cached_at", expireAfterSeconds=3600, name="idx_ttl_1h_cache"):
            logger.info("✅ Created TTL index: tokens_cache.cached_at (1h auto-delete)")
            created_count += 1
        else:
            failed_count += 1

        # ==================== SUMMARY ====================
        logger.info("=" * 60)
        logger.info(f"📊 Index Creation Summary:")
        logger.info(f"   • Created: {created_count}")
        logger.info(f"   • Skipped (already exist): {skipped_count}")
        logger.info(f"   • Failed: {failed_count}")
        logger.info("=" * 60)

        if failed_count == 0:
            logger.info("✅ All indexes created or already exist!")
        else:
            logger.warning(f"⚠️  {failed_count} index(es) failed to create - check logs above")

        # List all indexes for verification
        logger.info("\n📋 Indexes Summary:\n")

        collections = [
            'users', 'favorites', 'scanned_tokens', 'scan_history',
            'alerts', 'positions', 'tokens_cache'
        ]

        for collection_name in collections:
            collection = getattr(db, collection_name)
            indexes = list(collection.list_indexes())
            logger.info(f"\n{collection_name.upper()} ({len(indexes)} indexes):")
            for idx in indexes:
                logger.info(f"  • {idx['name']}: {idx.get('key', {})}")

        # Return True if all indexes were created or already exist, False if any failed
        return failed_count == 0

    except Exception as e:
        logger.error(f"❌ Critical error creating indexes: {e}", exc_info=True)
        return False


def verify_indexes():
    """Verify that all indexes exist"""
    try:
        db = MongoDBManager()
        logger.info("\n🔍 Verifying indexes...\n")

        required_indexes = {
            'users': ['idx_email_unique', 'idx_username_unique', 'idx_role'],
            'favorites': ['idx_user_token_unique', 'idx_user_id', 'idx_chain'],
            'scanned_tokens': ['idx_address_chain_unique', 'idx_scanned_at_desc', 'idx_chain_scanned', 'idx_ttl_48h'],
            'scan_history': ['idx_user_id_history', 'idx_scan_date_desc'],
            'alerts': ['idx_user_id_alerts', 'idx_is_active', 'idx_user_active_alerts'],
            'positions': ['idx_user_token_position_unique', 'idx_user_id_positions'],
            'tokens_cache': ['idx_token_address_cache', 'idx_ttl_1h_cache']
        }

        all_ok = True

        for collection_name, expected_indexes in required_indexes.items():
            collection = getattr(db, collection_name)
            existing_indexes = [idx['name'] for idx in collection.list_indexes()]

            missing = set(expected_indexes) - set(existing_indexes)

            if missing:
                logger.warning(f"⚠️  {collection_name}: Missing indexes {missing}")
                all_ok = False
            else:
                logger.info(f"✅ {collection_name}: All indexes present")

        return all_ok

    except Exception as e:
        logger.error(f"❌ Error verifying indexes: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MongoDB Index Creation Script")
    print("=" * 60 + "\n")

    # Create indexes
    success = create_indexes()

    if success:
        print("\n" + "=" * 60)
        print("Verifying indexes...")
        print("=" * 60 + "\n")

        # Verify indexes
        verify_indexes()

        print("\n" + "=" * 60)
        print("✅ Index creation completed successfully!")
        print("=" * 60 + "\n")

        print("NEXT STEPS:")
        print("1. Restart your Flask application")
        print("2. Monitor query performance with explain()")
        print("3. Check index usage stats with db.collection.stats()")
        print("\n")

        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ Index creation failed!")
        print("=" * 60 + "\n")
        sys.exit(1)
