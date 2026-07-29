import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ.get('DB_NAME', 'lume_veritas')
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash')
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret')
JWT_ALG = 'HS256'
JWT_EXPIRE_DAYS = 30
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'Lume Veritas <onboarding@resend.dev>')
PUBLIC_APP_URL = os.environ.get('PUBLIC_APP_URL', '')
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
