import os

from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///sales_assistant.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # DeepSeek / OpenAI
    HF_TOKEN = os.getenv('DEEPSEEK_API_KEY')

    # Gmail OAuth2
    GMAIL_CLIENT_ID = os.getenv('GMAIL_CLIENT_ID')
    GMAIL_CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET')
    GMAIL_REDIRECT_URI = os.getenv('GMAIL_REDIRECT_URI')  # e.g. http://localhost:5000/oauth2callback
