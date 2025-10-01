"""
Script pour créer un utilisateur administrateur
"""

from database import Database

def create_admin():
    db = Database()
    
    print("=== Création d'un compte Administrateur ===\n")
    
    email = input("Email : ")
    username = input("Nom d'utilisateur : ")
    password = input("Mot de passe : ")
    
    # Créer l'utilisateur
    user_id = db.create_user(email, username, password)
    
    if user_id:
        # Le mettre en admin
        success = db.update_user_role(user_id, 'admin')
        
        if success:
            print(f"\n✅ Administrateur créé avec succès !")
            print(f"Email: {email}")
            print(f"Username: {username}")
            print(f"Role: admin")
        else:
            print("\n❌ Erreur lors de l'attribution du rôle admin")
    else:
        print("\n❌ Erreur : Email ou nom d'utilisateur déjà utilisé")

if __name__ == "__main__":
    create_admin()
