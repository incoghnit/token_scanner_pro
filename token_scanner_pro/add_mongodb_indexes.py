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


def create_indexes():
    """Create all necessary MongoDB indexes"""

    try:
        db = MongoDBManager()
        logger.info("📊 Creating MongoDB indexes...")

        # ==================== USERS COLLECTION ====================
        # Index on email (unique)
        db.users.create_index("email", unique=True, name="idx_email_unique")
        logger.info("✅ Created index: users.email (unique)")

        # Index on username (unique)
        db.users.create_index("username", unique=True, name="idx_username_unique")
        logger.info("✅ Created index: users.username (unique)")

        # Index on role (for admin queries)
        db.users.create_index("role", name="idx_role")
        logger.info("✅ Created index: users.role")

        # Index on created_at (for sorting)
        db.users.create_index([("created_at", -1)], name="idx_created_at_desc")
        logger.info("✅ Created index: users.created_at (desc)")

        # ==================== FAVORITES COLLECTION ====================
        # Compound index on user_id + token_address (for quick lookups)
        db.favorites.create_index(
            [("user_id", 1), ("token_address", 1)],
            unique=True,
            name="idx_user_token_unique"
        )
        logger.info("✅ Created index: favorites.user_id + token_address (unique)")

        # Index on user_id (for user's favorites list)
        db.favorites.create_index("user_id", name="idx_user_id")
        logger.info("✅ Created index: favorites.user_id")

        # Index on chain (for filtering)
        db.favorites.create_index("chain", name="idx_chain")
        logger.info("✅ Created index: favorites.chain")

        # Index on added_at (for sorting)
        db.favorites.create_index([("added_at", -1)], name="idx_added_at_desc")
        logger.info("✅ Created index: favorites.added_at (desc)")

        # ==================== SCANNED_TOKENS COLLECTION ====================
        # Compound index on address + chain (unique)
        db.scanned_tokens.create_index(
            [("address", 1), ("chain", 1)],
            unique=True,
            name="idx_address_chain_unique"
        )
        logger.info("✅ Created index: scanned_tokens.address + chain (unique)")

        # Index on scanned_at (for FIFO rotation and recent queries)
        db.scanned_tokens.create_index([("scanned_at", -1)], name="idx_scanned_at_desc")
        logger.info("✅ Created index: scanned_tokens.scanned_at (desc)")

        # Index on chain (for filtering)
        db.scanned_tokens.create_index("chain", name="idx_chain_scanned")
        logger.info("✅ Created index: scanned_tokens.chain")

        # Index on is_safe (for filtering safe tokens)
        db.scanned_tokens.create_index("is_safe", name="idx_is_safe")
        logger.info("✅ Created index: scanned_tokens.is_safe")

        # Index on risk_score (for sorting by risk)
        db.scanned_tokens.create_index([("risk_score", 1)], name="idx_risk_score_asc")
        logger.info("✅ Created index: scanned_tokens.risk_score (asc)")

        # Index on is_pump_dump_suspect (for filtering)
        db.scanned_tokens.create_index("is_pump_dump_suspect", name="idx_pump_dump")
        logger.info("✅ Created index: scanned_tokens.is_pump_dump_suspect")

        # TTL Index: Auto-delete tokens older than 48 hours
        db.scanned_tokens.create_index(
            "scanned_at",
            expireAfterSeconds=172800,  # 48 hours = 172800 seconds
            name="idx_ttl_48h"
        )
        logger.info("✅ Created TTL index: scanned_tokens.scanned_at (48h auto-delete)")

        # ==================== SCAN_HISTORY COLLECTION ====================
        # Index on user_id (for user's scan history)
        db.scan_history.create_index("user_id", name="idx_user_id_history")
        logger.info("✅ Created index: scan_history.user_id")

        # Index on scan_date (for recent scans)
        db.scan_history.create_index([("scan_date", -1)], name="idx_scan_date_desc")
        logger.info("✅ Created index: scan_history.scan_date (desc)")

        # Compound index on user_id + scan_date (for user's recent scans)
        db.scan_history.create_index(
            [("user_id", 1), ("scan_date", -1)],
            name="idx_user_scan_date"
        )
        logger.info("✅ Created index: scan_history.user_id + scan_date")

        # ==================== ALERTS COLLECTION ====================
        # Index on user_id (for user's alerts)
        db.alerts.create_index("user_id", name="idx_user_id_alerts")
        logger.info("✅ Created index: alerts.user_id")

        # Index on is_active (for active alerts only)
        db.alerts.create_index("is_active", name="idx_is_active")
        logger.info("✅ Created index: alerts.is_active")

        # Compound index on user_id + is_active (for user's active alerts)
        db.alerts.create_index(
            [("user_id", 1), ("is_active", 1)],
            name="idx_user_active_alerts"
        )
        logger.info("✅ Created index: alerts.user_id + is_active")

        # Index on token_address (for alerts on specific token)
        db.alerts.create_index("token_address", name="idx_token_address_alerts")
        logger.info("✅ Created index: alerts.token_address")

        # Index on created_at (for sorting)
        db.alerts.create_index([("created_at", -1)], name="idx_created_at_alerts_desc")
        logger.info("✅ Created index: alerts.created_at (desc)")

        # ==================== POSITIONS COLLECTION ====================
        # Compound index on user_id + token_address (unique)
        db.positions.create_index(
            [("user_id", 1), ("token_address", 1)],
            unique=True,
            name="idx_user_token_position_unique"
        )
        logger.info("✅ Created index: positions.user_id + token_address (unique)")

        # Index on user_id (for user's positions)
        db.positions.create_index("user_id", name="idx_user_id_positions")
        logger.info("✅ Created index: positions.user_id")

        # Index on is_open (for open positions)
        db.positions.create_index("is_open", name="idx_is_open")
        logger.info("✅ Created index: positions.is_open")

        # Index on entry_date (for sorting)
        db.positions.create_index([("entry_date", -1)], name="idx_entry_date_desc")
        logger.info("✅ Created index: positions.entry_date (desc)")

        # ==================== TOKENS_CACHE COLLECTION ====================
        # Index on token_address (for lookups)
        db.tokens_cache.create_index("token_address", name="idx_token_address_cache")
        logger.info("✅ Created index: tokens_cache.token_address")

        # Index on cached_at (for cache expiration)
        db.tokens_cache.create_index([("cached_at", -1)], name="idx_cached_at_desc")
        logger.info("✅ Created index: tokens_cache.cached_at (desc)")

        # TTL Index: Auto-delete cached data older than 1 hour
        db.tokens_cache.create_index(
            "cached_at",
            expireAfterSeconds=3600,  # 1 hour = 3600 seconds
            name="idx_ttl_1h_cache"
        )
        logger.info("✅ Created TTL index: tokens_cache.cached_at (1h auto-delete)")

        # ==================== SUMMARY ====================
        logger.info("=" * 60)
        logger.info("✅ All indexes created successfully!")
        logger.info("=" * 60)

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

        return True

    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}", exc_info=True)
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
