"""
Script pour créer un utilisateur administrateur
"""

from mongodb_manager import MongoDBManager

def create_admin():
    db = MongoDBManager()

    print("=== Création d'un compte Administrateur ===\n")

    email = input("Email : ")
    username = input("Nom d'utilisateur : ")
    password = input("Mot de passe : ")

    # Créer l'utilisateur avec rôle admin directement
    user_id = db.create_user(email, username, password, role='admin')
    
    if user_id:
        print(f"\n✅ Administrateur créé avec succès !")
        print(f"Email: {email}")
        print(f"Username: {username}")
        print(f"Role: admin")
        print(f"User ID: {user_id}")
    else:
        print("\n❌ Erreur : Email ou nom d'utilisateur déjà utilisé")

if __name__ == "__main__":
    create_admin()
