"""
Script de Migration MongoDB - Correction Urgente Index

Ce script corrige le problème critique d'index avec mauvais noms de champs.

PROBLÈME:
- Index actuel: (address, chain)
- Champs stockés: (token_address, token_chain)
- Résultat: Tous les inserts échouent avec E11000 duplicate key error

SOLUTION:
1. Supprimer l'ancien index incorrect
2. Nettoyer les documents avec address/chain null
3. Créer le nouvel index correct

Usage:
    python fix_mongodb_index_migration.py
"""

from mongodb_manager import MongoDBManager
from logger import logger
import sys


def fix_index_migration():
    """Migration complète pour corriger les index"""

    try:
        db = MongoDBManager()
        logger.info("=" * 70)
        logger.info("🔧 MIGRATION MONGODB - CORRECTION INDEX CRITIQUE")
        logger.info("=" * 70)

        # ==================== ÉTAPE 1: LISTER LES INDEX ACTUELS ====================
        logger.info("\n📋 ÉTAPE 1: Liste des index actuels sur scanned_tokens")

        existing_indexes = list(db.scanned_tokens.list_indexes())
        logger.info(f"Nombre d'index: {len(existing_indexes)}")

        for idx in existing_indexes:
            logger.info(f"  • {idx['name']}: {idx.get('key', {})}")

        # ==================== ÉTAPE 2: SUPPRIMER ANCIEN INDEX INCORRECT ====================
        logger.info("\n🗑️  ÉTAPE 2: Suppression des index incorrects")

        indexes_to_drop = []

        for idx in existing_indexes:
            idx_name = idx['name']
            idx_key = idx.get('key', {})

            # Ignorer l'index _id_ (obligatoire)
            if idx_name == '_id_':
                continue

            # Vérifier si l'index utilise les mauvais noms de champs
            if 'address' in idx_key and 'token_address' not in idx_key:
                logger.warning(f"⚠️  Index incorrect détecté: {idx_name} (utilise 'address' au lieu de 'token_address')")
                indexes_to_drop.append(idx_name)

            if 'chain' in idx_key and 'token_chain' not in idx_key:
                logger.warning(f"⚠️  Index incorrect détecté: {idx_name} (utilise 'chain' au lieu de 'token_chain')")
                if idx_name not in indexes_to_drop:
                    indexes_to_drop.append(idx_name)

        # Supprimer les index incorrects
        for idx_name in indexes_to_drop:
            try:
                logger.info(f"🗑️  Suppression de l'index: {idx_name}")
                db.scanned_tokens.drop_index(idx_name)
                logger.info(f"✅ Index {idx_name} supprimé")
            except Exception as e:
                logger.error(f"❌ Erreur suppression {idx_name}: {e}")

        if not indexes_to_drop:
            logger.info("✅ Aucun index incorrect trouvé")

        # ==================== ÉTAPE 3: NETTOYER DOCUMENTS INVALIDES ====================
        logger.info("\n🧹 ÉTAPE 3: Nettoyage des documents invalides")

        # Requête pour trouver documents avec address/chain/token_address/token_chain null
        invalid_query = {
            "$or": [
                {"token_address": None},
                {"token_chain": None},
                {"token_address": {"$exists": False}},
                {"token_chain": {"$exists": False}},
                {"address": None},
                {"chain": None}
            ]
        }

        invalid_count = db.scanned_tokens.count_documents(invalid_query)

        if invalid_count > 0:
            logger.warning(f"⚠️  {invalid_count} document(s) invalide(s) trouvé(s)")

            # Afficher échantillon
            samples = list(db.scanned_tokens.find(invalid_query).limit(3))
            logger.info("\n📋 Échantillon de documents invalides:")
            for i, doc in enumerate(samples, 1):
                logger.info(f"  {i}. _id: {doc.get('_id')}")
                logger.info(f"     token_address: {doc.get('token_address')}")
                logger.info(f"     token_chain: {doc.get('token_chain')}")
                logger.info(f"     address: {doc.get('address')}")
                logger.info(f"     chain: {doc.get('chain')}")

            # Supprimer
            logger.info(f"\n🗑️  Suppression de {invalid_count} document(s) invalide(s)...")
            result = db.scanned_tokens.delete_many(invalid_query)
            logger.info(f"✅ {result.deleted_count} document(s) supprimé(s)")
        else:
            logger.info("✅ Aucun document invalide trouvé")

        # ==================== ÉTAPE 4: CRÉER NOUVEL INDEX CORRECT ====================
        logger.info("\n🔨 ÉTAPE 4: Création du nouvel index correct")

        try:
            # Créer index unique sur (token_address, token_chain)
            logger.info("Création de l'index: (token_address, token_chain) UNIQUE")
            db.scanned_tokens.create_index(
                [("token_address", 1), ("token_chain", 1)],
                unique=True,
                name="idx_token_address_chain_unique"
            )
            logger.info("✅ Index idx_token_address_chain_unique créé avec succès")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("⏭️  Index idx_token_address_chain_unique existe déjà")
            else:
                logger.error(f"❌ Erreur création index: {e}")
                raise

        # Créer les autres index importants
        logger.info("\n🔨 Création des index supplémentaires...")

        # Index sur scanned_at (pour tri chronologique)
        try:
            db.scanned_tokens.create_index(
                [("scanned_at", -1)],
                name="idx_scanned_at_desc"
            )
            logger.info("✅ Index idx_scanned_at_desc créé")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("⏭️  Index idx_scanned_at_desc existe déjà")

        # Index sur token_chain (pour filtrage)
        try:
            db.scanned_tokens.create_index(
                "token_chain",
                name="idx_token_chain"
            )
            logger.info("✅ Index idx_token_chain créé")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("⏭️  Index idx_token_chain existe déjà")

        # Index sur is_safe (pour filtrage)
        try:
            db.scanned_tokens.create_index(
                "is_safe",
                name="idx_is_safe"
            )
            logger.info("✅ Index idx_is_safe créé")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("⏭️  Index idx_is_safe existe déjà")

        # ==================== ÉTAPE 5: VÉRIFICATION FINALE ====================
        logger.info("\n✅ ÉTAPE 5: Vérification finale")

        final_indexes = list(db.scanned_tokens.list_indexes())
        logger.info(f"\n📊 Index finaux sur scanned_tokens ({len(final_indexes)} index):")

        for idx in final_indexes:
            idx_name = idx['name']
            idx_key = idx.get('key', {})
            is_unique = idx.get('unique', False)
            unique_str = " [UNIQUE]" if is_unique else ""
            logger.info(f"  ✅ {idx_name}: {idx_key}{unique_str}")

        # Vérifier qu'aucun index incorrect ne reste
        has_incorrect = False
        for idx in final_indexes:
            idx_key = idx.get('key', {})
            if idx['name'] != '_id_':  # Ignorer _id_
                if 'address' in idx_key and 'token_address' not in idx_key:
                    logger.error(f"❌ Index incorrect toujours présent: {idx['name']}")
                    has_incorrect = True
                if 'chain' in idx_key and 'token_chain' not in idx_key:
                    logger.error(f"❌ Index incorrect toujours présent: {idx['name']}")
                    has_incorrect = True

        if not has_incorrect:
            logger.info("\n✅ Aucun index incorrect restant")

        # Compter les documents valides
        valid_count = db.scanned_tokens.count_documents({})
        logger.info(f"\n📊 Documents dans scanned_tokens: {valid_count}")

        logger.info("\n" + "=" * 70)
        logger.info("✅ MIGRATION TERMINÉE AVEC SUCCÈS !")
        logger.info("=" * 70)

        logger.info("\n📋 PROCHAINES ÉTAPES:")
        logger.info("1. Redémarrez votre application Flask")
        logger.info("2. Les nouveaux tokens devraient s'insérer sans erreur E11000")
        logger.info("3. Vérifiez les logs: '💾 X/20 tokens stockés dans la BDD' (X devrait être proche de 20)")

        return True

    except Exception as e:
        logger.error(f"❌ Erreur critique durant la migration: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔧 MIGRATION MONGODB - CORRECTION INDEX CRITIQUE")
    print("=" * 70)
    print("\nCe script va:")
    print("1. Supprimer les index incorrects (address, chain)")
    print("2. Nettoyer les documents invalides")
    print("3. Créer les nouveaux index corrects (token_address, token_chain)")
    print("\n⚠️  L'application doit être ARRÊTÉE pendant la migration!")
    print("=" * 70)

    response = input("\nContinuer? (oui/non): ").strip().lower()

    if response not in ['oui', 'yes', 'o', 'y']:
        print("❌ Migration annulée")
        sys.exit(0)

    print("\n🚀 Démarrage de la migration...\n")

    success = fix_index_migration()

    if success:
        print("\n" + "=" * 70)
        print("✅ MIGRATION RÉUSSIE !")
        print("=" * 70)
        print("\nVous pouvez maintenant redémarrer votre application.")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("❌ MIGRATION ÉCHOUÉE !")
        print("=" * 70)
        print("\nVérifiez les logs ci-dessus pour plus de détails.")
        sys.exit(1)
