Outils :
- Python version 3.12
- WSL2 + Docker Desktop
- Ollama (GPU)
- Tesseract
- PgAdmin (PostgreSql)
- n8n
- Docling (CPU)
- Streamlit

Installation :
# py -3.12 -m venv .venv312
# Set-ExecutionPolicy RemoteSigned -Scope Process
# .\.venv312\Scripts\Activate.ps1
# docker compose up -d
# docker compose down (stop service et supprime conteneur)
# docker compose stop (arrete tout)
# docker compose start
# docker compose ps (voir conteneur)
# ollama pull llama3.2:3b (qwen2.5:3b ou llama3.2:3b) 
# ollama run llama3.2:3b
/bye
# ollama ps
# Telecharger Tesseract OCR (UB-Mannheim Tesseract sur GitHub)
# pip install fastapi uvicorn[standard] python-multipart pydantic-settings psycopg[binary,pool] docling pytesseract httpx streamlit pandas pytest reportlab Pillow Faker
Test :
# python evaluation/generate_test_files.py

Demarrage serveur :
# docker compose start
# docker compose ps
# uvicorn app.main:app --reload --reload-dir app --port 8000

# Factures IA

Automatisation intelligente du traitement des factures fournisseurs (OCR + IA + workflow n8n).
Mini-projet de Master 1 Informatique, n°2 : « Automatisation intelligente du traitement des factures ».

Auteurs : à compléter

## Objectif

Déposer une facture (PDF ou image) dans un dossier déclenche son traitement : réception, OCR,
extraction des champs (fournisseur, numéro, date, montant HT, TVA, TTC), contrôles de cohérence,
détection des doublons, puis enregistrement ou validation humaine des cas incertains.

## Architecture

```
inbox/ -> n8n (orchestration) -> API FastAPI -> PostgreSQL
                                   |-> OCR (Docling, Tesseract)
                                   |-> extraction (règles puis LLM Ollama)
Streamlit : consultation, correction et validation
```

## État d'avancement

- [x] Configuration, connexion PostgreSQL, route `/health`
- [x] Réception des documents (`POST /documents`), hash SHA-256, doublon exact, stockage
- [x] Relecture d'un document (`GET /documents/{id}`)
- [ ] Workflow n8n (dossier surveillé)
- [ ] OCR (Docling, Tesseract en repli)
- [ ] Extraction des champs (règles, LLM)
- [ ] Contrôles métier et doublons métier
- [ ] Interface Streamlit
- [ ] Évaluation (précision par champ, doublons, temps manuel contre automatisé)

## Prérequis

- Windows 11 (testé), Python 3.12, Git
- Docker Desktop (PostgreSQL et n8n)
- Plus tard : Tesseract 5, Ollama

## Installation

```powershell
git clone <url-du-depot>
cd factures-ia
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Modifie `.env` (au minimum `FACTURES_POSTGRES_PASSWORD`), puis démarre les services :

```powershell
docker compose up -d
docker compose ps
```

PostgreSQL doit être `healthy`. Le schéma (`sql/schema.sql`) est créé au premier démarrage.

## Lancer l'API

```powershell
uvicorn app.main:app --reload --reload-dir app --port 8000
```

- Documentation interactive : http://127.0.0.1:8000/docs
- État de santé : http://127.0.0.1:8000/health

## Tests

```powershell
pytest -v
```

Les tests utilisent la vraie base PostgreSQL mais annulent leurs écritures (aucune donnée conservée).

## Structure du dépôt

```
app/            API FastAPI : config, db (repositories), services, api (routes)
sql/            schéma PostgreSQL
tests/          tests pytest
data/tests/     fichiers de test techniques
evaluation/     scripts de génération et d'évaluation
inbox/          dossier surveillé par n8n
storage/        documents reçus (non versionné)
```

## Choix techniques

- Variables d'environnement préfixées `FACTURES_` pour éviter les conflits avec d'autres projets.
- Port PostgreSQL local 5434 pour ne pas entrer en conflit avec une instance déjà installée.
- SQL écrit à la main (psycopg 3), architecture en couches routes / services / repositories.
- Doublon exact détecté par le hash SHA-256 et la contrainte d'unicité de la base.