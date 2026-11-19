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

Demarrage serveur :
# docker compose start
# docker compose ps
# uvicorn app.main:app --reload --reload-dir app --port 8000