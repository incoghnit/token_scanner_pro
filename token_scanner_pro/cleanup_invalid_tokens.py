"""
Cleanup Invalid Tokens Script

Removes documents with null address or chain from scanned_tokens collection.
This is required before creating unique indexes on these fields.

Usage:
    python cleanup_invalid_tokens.py
"""

from mongodb_manager import MongoDBManager
from logger import logger
import sys


def cleanup_invalid_tokens():
    """Remove tokens with null address or chain"""

    try:
        db = MongoDBManager()
        logger.info("🧹 Starting cleanup of invalid tokens...")

        # Find invalid documents
        invalid_query = {
            "$or": [
                {"address": None},
                {"chain": None},
                {"address": {"$exists": False}},
                {"chain": {"$exists": False}}
            ]
        }

        # Count invalid documents
        invalid_count = db.scanned_tokens.count_documents(invalid_query)

        if invalid_count == 0:
            logger.info("✅ No invalid documents found - database is clean!")
            return True

        logger.warning(f"⚠️  Found {invalid_count} invalid document(s) in scanned_tokens")

        # Show sample of invalid documents
        logger.info("\n📋 Sample of invalid documents:")
        samples = list(db.scanned_tokens.find(invalid_query).limit(5))
        for i, doc in enumerate(samples, 1):
            logger.info(f"  {i}. _id: {doc.get('_id')} | address: {doc.get('address')} | chain: {doc.get('chain')}")

        # Delete invalid documents
        logger.info(f"\n🗑️  Deleting {invalid_count} invalid document(s)...")
        result = db.scanned_tokens.delete_many(invalid_query)

        logger.info(f"✅ Deleted {result.deleted_count} invalid document(s)")

        # Verify cleanup
        remaining = db.scanned_tokens.count_documents(invalid_query)
        if remaining == 0:
            logger.info("✅ Cleanup successful - no invalid documents remaining")
            return True
        else:
            logger.error(f"❌ Cleanup incomplete - {remaining} invalid documents still exist")
            return False

    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}", exc_info=True)
        return False


def verify_data_integrity():
    """Verify that all remaining documents have valid data"""

    try:
        db = MongoDBManager()
        logger.info("\n🔍 Verifying data integrity...")

        # Count total documents
        total = db.scanned_tokens.count_documents({})
        logger.info(f"📊 Total documents in scanned_tokens: {total}")

        # Count documents with valid address and chain
        valid = db.scanned_tokens.count_documents({
            "address": {"$ne": None, "$exists": True},
            "chain": {"$ne": None, "$exists": True}
        })
        logger.info(f"✅ Valid documents (address + chain): {valid}")

        if total == valid:
            logger.info("✅ All documents are valid!")
            return True
        else:
            logger.warning(f"⚠️  {total - valid} document(s) still have invalid data")
            return False

    except Exception as e:
        logger.error(f"❌ Error verifying data: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MongoDB Data Cleanup Script")
    print("=" * 60 + "\n")

    # Run cleanup
    cleanup_success = cleanup_invalid_tokens()

    if cleanup_success:
        # Verify integrity
        verify_success = verify_data_integrity()

        if verify_success:
            print("\n" + "=" * 60)
            print("✅ Cleanup completed successfully!")
            print("=" * 60 + "\n")

            print("NEXT STEPS:")
            print("1. Run: python add_mongodb_indexes.py")
            print("2. The unique index creation should now succeed")
            print("\n")

            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("⚠️  Cleanup succeeded but data integrity issues remain")
            print("=" * 60 + "\n")
            sys.exit(1)
    else:
        print("\n" + "=" * 60)
        print("❌ Cleanup failed!")
        print("=" * 60 + "\n")
        sys.exit(1)
