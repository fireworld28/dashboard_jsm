# 🚀 Guide de Déploiement — Dashboard KITO

Stack : **Streamlit Cloud** (app) + **GitHub Actions** (sync quotidienne) + **Turso Cloud** (base de données)

---

## Structure du projet

```
dashboard_jsm/
├── .github/
│   └── workflows/
│       └── sync_turso.yml        ← GitHub Actions : sync quotidienne Spotify → Turso
├── .streamlit/
│   ├── config.toml               ← Thème "Studio Nuit" pour Streamlit Cloud
│   └── secrets.toml              ← LOCAL UNIQUEMENT, jamais committé
├── scripts/
│   └── sync_spotify_to_turso.py  ← Script Python de collecte
├── app.py
├── database.py
├── spotify_service.py
├── config.py
├── requirements.txt
└── .gitignore
```

---

## Étape 1 — Préparer les secrets GitHub

Dans ton dépôt GitHub : **Settings → Secrets and variables → Actions → New repository secret**

Ajouter ces 5 secrets :

| Nom du secret          | Valeur                                         |
|------------------------|------------------------------------------------|
| `SPOTIFY_CLIENT_ID`    | Depuis developer.spotify.com/dashboard         |
| `SPOTIFY_CLIENT_SECRET`| Depuis developer.spotify.com/dashboard         |
| `TURSO_DATABASE_URL`   | `libsql://ton-projet-TON_ORG.turso.io`        |
| `TURSO_AUTH_TOKEN`     | Token depuis app.turso.tech → Settings         |
| `ARTIST_SPOTIFY_ID`    | `0T4d2alRNWD29IME6Yb142` (KITO)              |

> **Comment trouver ton TURSO_DATABASE_URL :**
> app.turso.tech → ton projet → Settings → Database URL
>
> **Comment générer un TURSO_AUTH_TOKEN :**
> app.turso.tech → ton projet → Settings → Create Token → "Full Access"

---

## Étape 2 — Déployer sur Streamlit Cloud

1. Push le projet sur GitHub (branche `main`)
2. Aller sur **share.streamlit.io** → "New app"
3. Sélectionner le dépôt, branche `main`, fichier principal `app.py`
4. Dans **Advanced settings → Secrets**, coller le contenu suivant en remplaçant les valeurs :

```toml
SPOTIFY_CLIENT_ID     = "ton_client_id"
SPOTIFY_CLIENT_SECRET = "ton_client_secret"
TURSO_DATABASE_URL    = "libsql://ton-projet-TON_ORG.turso.io"
TURSO_AUTH_TOKEN      = "eyJhbGciOiJFZERTQS..."
ARTIST_SPOTIFY_ID     = "0T4d2alRNWD29IME6Yb142"
```

5. Cliquer "Deploy" → l'app est en ligne en 2-3 minutes

---

## Étape 3 — Vérifier la sync GitHub Actions

La sync s'exécute automatiquement tous les jours à **06h00 UTC** (08h00 Paris).

Pour tester immédiatement :
1. GitHub → onglet **Actions**
2. Sélectionner "Sync Spotify → Turso Cloud"
3. Cliquer **"Run workflow"** → laisser `force_upsert` sur `false`
4. Vérifier les logs : tu dois voir `Sync terminée en X.XXs [action=inserted]`

---

## Étape 4 — Test local du script de sync

```bash
# Copier le template de secrets
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
# Éditer .streamlit/secrets.toml avec tes vraies valeurs

# Installer les dépendances légères
pip install spotipy libsql-experimental python-dotenv

# Lancer la sync
python scripts/sync_spotify_to_turso.py
```

Résultat attendu :
```
2025-01-15 07:00:01  INFO      ═══ Démarrage sync Spotify → Turso [2025-01-15] ═══
2025-01-15 07:00:01  INFO      Connexion à Turso Cloud : libsql://...
2025-01-15 07:00:02  INFO      Schéma vérifié
2025-01-15 07:00:02  INFO      Connexion à l'API Spotify…
2025-01-15 07:00:03  INFO      Données récupérées → KITO | Followers : 34821 | Popularité : 46/100
2025-01-15 07:00:03  INFO      Enregistrement inserted → date=2025-01-15 artist=KITO
2025-01-15 07:00:03  INFO      ═══ Sync terminée en 2.14s [action=inserted] ═══
```

---

## Fonctionnement du pipeline complet

```
06h00 UTC chaque jour
        │
        ▼
GitHub Actions (ubuntu-latest)
        │
        ├── pip install spotipy libsql-experimental
        │
        ├── sync_spotify_to_turso.py
        │       ├── sp.artist(ARTIST_SPOTIFY_ID)     → followers, popularity
        │       └── INSERT OR REPLACE INTO historique_artistes
        │
        └── Turso Cloud (libSQL)
                └── historique_artistes + 1 ligne/jour
                        │
                        ▼
              Streamlit Cloud (app.py)
                      └── get_artist_history_full() → cache 1h
                              └── filter_history() → filtrage mémoire
```

---

## Maintenance & dépannage

**La sync échoue avec "Variable d'environnement manquante"**
→ Vérifier que les 5 secrets GitHub sont bien définis (Settings → Secrets → Actions)

**La sync tourne mais l'app n'affiche pas les nouvelles données**
→ Le cache Streamlit est de 1h (`@st.cache_data(ttl=3600)`). Attendre ou redémarrer l'app depuis share.streamlit.io

**Forcer un re-sync du jour (ex: données incorrectes)**
→ GitHub Actions → "Run workflow" → mettre `force_upsert` sur `true`

**Vérifier le contenu de la DB directement**
→ app.turso.tech → ton projet → Shell → `SELECT * FROM historique_artistes ORDER BY date_enregistrement DESC LIMIT 10;`

**Ajouter un deuxième artiste**
1. Ajouter `ARTIST_SPOTIFY_ID_2` dans les secrets GitHub
2. Dupliquer le bloc de collecte dans `sync_spotify_to_turso.py`
3. Modifier `config.py` pour exposer le sélecteur multi-artiste (roadmap)

---

## Coûts estimés

| Service          | Plan       | Coût       |
|------------------|------------|------------|
| Streamlit Cloud  | Community  | Gratuit    |
| GitHub Actions   | Free tier  | Gratuit (2000 min/mois — le job dure ~30s) |
| Turso Cloud      | Free tier  | Gratuit (500 MB, 1 Md reads/mois)          |
| Spotify API      | Free       | Gratuit (Client Credentials)               |

**Total : 0 €/mois** pour un usage mono-artiste.
