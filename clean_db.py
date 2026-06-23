import sqlite3

DB_NAME = "music_manager.db"

print(f"📦 Ouverture du fichier '{DB_NAME}'...")
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# 1. On applique ton nettoyage de données habituel
print("🧼 Harmonisation des artistes (Kito -> KITO)...")
cursor.execute("UPDATE historique_artistes SET artiste_name = UPPER(artiste_name);")
conn.commit()

# 2. On exécute la commande PRAGMA que tu as demandée
print("⚙️ Configuration du mode de journalisation...")
cursor.execute("PRAGMA journal_mode = WAL;")
mode_actuel = cursor.fetchone()[0]

conn.close()

print(f"\n✨ Configuration réussie ! Le mode est maintenant : {mode_actuel}")
print(f"👉 Tu peux retenter l'upload de ton fichier '{DB_NAME}' sur Turso.")