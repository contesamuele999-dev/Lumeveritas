import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ.get('DB_NAME', 'lume_veritas')
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash')
# Fallback quando Gemini è sovraccarico (503/429). Opzionale: se la chiave manca,
# il fallback resta disattivato e il comportamento è identico a prima.
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
GROQ_MODEL_FALLBACK = os.environ.get('GROQ_MODEL_FALLBACK', 'llama-3.1-8b-instant')
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret')
JWT_ALG = 'HS256'
JWT_EXPIRE_DAYS = 30
MAILEROO_API_KEY = os.environ.get('MAILEROO_API_KEY', '')
# SENDER_EMAIL accetta sia "nome@dominio" sia il vecchio formato "Nome <nome@dominio>"
_sender = os.environ.get('SENDER_EMAIL', 'noreply@example.com').strip()
if '<' in _sender:
    SENDER_NAME, SENDER_EMAIL = _sender.split('<')[0].strip(), _sender.split('<')[1].rstrip('>').strip()
else:
    SENDER_NAME, SENDER_EMAIL = os.environ.get('SENDER_NAME', 'Lume Veritas'), _sender
PUBLIC_APP_URL = os.environ.get('PUBLIC_APP_URL', '')
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
